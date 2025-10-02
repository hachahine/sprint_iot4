import tkinter as tk
from tkinter import ttk, messagebox
import json
import time
from datetime import datetime
from decouple import config
from setup import setup_ui, setup_oracle_connection, setup_mqtt

class DashboardIoT:
    def __init__(self):
        # Configurar dotenv
        self.ORACLE_USER = config("ORACLE_USER")
        self.ORACLE_PASS = config("ORACLE_PASS")
        self.ORACLE_DSN = config("ORACLE_DSN")
        
        # config MQTT
        self.broker = 'test.mosquitto.org'
        self.port = 1883
        self.topic_status = "iot/vaga/status"
        self.client_id = f"DashboardClient-{int(time.time())}"
        self.connected = False
        self.motos_data = {}
        self.last_save_time = {}


        setup_ui(self)
        setup_oracle_connection(self)
        setup_mqtt(self)



    def on_connect(self, client, userdata, flags, rc, properties=None):
        """
        Callback ao conectar no MQTT
        """
        if rc == 0:
            self.connected = True
            self.connection_label.config(text="Status MQTT: Conectado", foreground="green")
            client.subscribe(self.topic_status)
        else:
            self.connected = False
            self.connection_label.config(text=f"Status MQTT: Erro ({rc})", foreground="red")



    def on_disconnect(self, client, userdata, rc, properties=None):
        """
        Callback ao desconectar no MQTT
        """
        self.connected = False
        self.connection_label.config(text="Status MQTT: Desconectado", foreground="red")
    


    def on_message(self, client, userdata, msg):
        """
        Callback ao receber msg no MQTT
        """
        try:
            if msg.topic == self.topic_status:
                payload = msg.payload.decode()
                self.process_and_persist_message(payload)
        except Exception as e:
            print(f"Erro ao processar mensagem: {str(e)}")



    def process_and_persist_message(self, payload):
        """
        processa a mensagem, atualiza a UI e persiste no banco
        """
        try:
            data = json.loads(payload)
            id_moto = data.get('id_moto', 'moto_desconhecida')
            status = data.get('status', 'unknown')
            distancia = data.get('distancia', 0)
            
            # Atualiza a UI 
            self.motos_data[id_moto] = {
                "status": status,
                "distancia": distancia,
                "timestamp": datetime.now().strftime("%H:%M:%S")
            }
            self.update_moto_tree()

            # Lógica para a escrita no banco
            current_time = time.time()
            save_interval = 5.0

            last_saved = self.last_save_time.get(id_moto, 0)
            if current_time - last_saved < save_interval:
                return

            # Persiste no banco se o intervalo tiver passado
            if self.db_conn:
                self.db_cursor.execute(
                    "INSERT INTO SPRINT_IOT_HISTORICO_MOTOS (ID_MOTO, STATUS, DISTANCIA) VALUES (:1, :2, :3)",
                    (id_moto, status, distancia)
                )
                self.db_conn.commit()
                print(f"Dados de {id_moto} persistidos no Oracle")
                self.last_save_time[id_moto] = current_time
            
        except json.JSONDecodeError:
            print(f"Payload não é um JSON válido: {payload}")
        except Exception as e:
            print(f"Erro em process_and_persist_message: {e}")



    def update_moto_tree(self):
        """
        Atualiza a tabela (Treeview) com os dados mais recentes.
        """
        for moto_id, data in self.motos_data.items():
            tag_name = 'disponivel_tag' if data['status'] == 'disponivel' else 'ocupada_tag'
            
            if self.moto_tree.exists(moto_id):
                self.moto_tree.item(
                    moto_id,
                    values=(data['status'], f"{data['distancia']:.1f}", data['timestamp']),
                    tags=(tag_name,)
                )
            else:
                self.moto_tree.insert(
                    "", tk.END, iid=moto_id, text=moto_id,
                    values=(data['status'], f"{data['distancia']:.1f}", data['timestamp']),
                    tags=(tag_name,)
                )



    def enviar_comando_especifico(self, comando):
        """
        Envia um comando para o dispositivo selecionado na tabela.
        """
        if not self.connected:
            messagebox.showwarning("Aviso", "Não conectado ao broker MQTT!")
            return
        selecionados = self.moto_tree.selection()
        if not selecionados:
            messagebox.showwarning("Aviso", "Nenhum dispositivo selecionado na tabela!")
            return
        id_moto_selecionada = selecionados[0]
        target_topic = f"iot/motos/{id_moto_selecionada}/comando"
        try:
            result = self.client.publish(target_topic, comando)
            if result.rc == 0:
                print(f"Comando '{comando}' enviado para '{target_topic}'")
            else:
                messagebox.showerror("Erro", f"Falha ao enviar comando para {id_moto_selecionada}!")
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao publicar comando: {e}")
    


    def run(self):
        """
        começa o loop principal da aplicação
        """
        self.app.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.app.mainloop()



    def on_closing(self):
        """
        Função chamada ao fechar a janela
        """
        if self.connected:
            self.client.loop_stop()
            self.client.disconnect()
        if self.db_conn:
            self.db_conn.close()
            print("Conexão com Oracle DB fechada.")
        self.app.destroy()

if __name__ == "__main__":
    dashboard = DashboardIoT()
    dashboard.run()

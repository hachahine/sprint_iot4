import tkinter as tk
from tkinter import ttk, messagebox
import oracledb
import paho.mqtt.client as mqtt_client

def setup_ui(self):
    """
    Config UI da aplicação 
    """
    self.app = tk.Tk()
    self.app.title("Dashboard IoT - Monitoramento de Motos (Oracle DB)")
    self.app.geometry("700x650")
    
    main_frame = ttk.Frame(self.app, padding="10")
    main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
    
    self.connection_label = ttk.Label(main_frame, text="Status MQTT: Desconectado", font=("Arial", 10))
    self.connection_label.grid(row=0, column=0, columnspan=2, sticky=tk.W, pady=(0, 5))

    self.db_connection_label = ttk.Label(main_frame, text="Status Oracle DB: Desconectado", font=("Arial", 10))
    self.db_connection_label.grid(row=1, column=0, columnspan=2, sticky=tk.W, pady=(0, 10))
    
    ttk.Label(main_frame, text="Status das Motos:", font=("Arial", 12, "bold")).grid(
        row=2, column=0, columnspan=2, sticky=tk.W, pady=(10, 5)
    )
    
    tree_frame = ttk.Frame(main_frame)
    tree_frame.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)
    
    self.moto_tree = ttk.Treeview(
        tree_frame,
        columns=("status", "distancia", "timestamp"),
        show="tree headings"
    )
    self.moto_tree.heading("#0", text="ID Moto")
    self.moto_tree.heading("status", text="Status")
    self.moto_tree.heading("distancia", text="Distância (cm)")
    self.moto_tree.heading("timestamp", text="Última Leitura")
    
    self.moto_tree.column("#0", width=120)
    self.moto_tree.column("status", width=100)
    self.moto_tree.column("distancia", width=120)
    self.moto_tree.column("timestamp", width=150)
    
    self.moto_tree.tag_configure('disponivel_tag', foreground='green')
    self.moto_tree.tag_configure('ocupada_tag', foreground='red')

    tree_scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.moto_tree.yview)
    self.moto_tree.configure(yscrollcommand=tree_scrollbar.set)
    
    self.moto_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    tree_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    
    ttk.Separator(main_frame, orient='horizontal').grid(row=4, column=0, columnspan=2, sticky="ew", pady=10)
    ttk.Label(main_frame, text="Comandos:", font=("Arial", 12, "bold")).grid(
        row=5, column=0, columnspan=2, sticky=tk.W, pady=5)
    
    commands_frame = ttk.Frame(main_frame)
    commands_frame.grid(row=6, column=0, columnspan=2, sticky="ew", pady=5)
    
    ttk.Button(commands_frame, text="Alerta (LED + Buzzer)", command=lambda: self.enviar_comando_especifico("1")).pack(side=tk.LEFT, padx=5)
    ttk.Button(commands_frame, text="LED Verde", command=lambda: self.enviar_comando_especifico("led_verde")).pack(side=tk.LEFT, padx=5)
    ttk.Button(commands_frame, text="LED Vermelho", command=lambda: self.enviar_comando_especifico("led_vermelho")).pack(side=tk.LEFT, padx=5)
    ttk.Button(commands_frame, text="Desligar LED", command=lambda: self.enviar_comando_especifico("led_off")).pack(side=tk.LEFT, padx=5)

    ttk.Separator(main_frame, orient='horizontal').grid(row=7, column=0, columnspan=2, sticky="ew", pady=10)
    
    self.app.columnconfigure(0, weight=1)
    self.app.rowconfigure(0, weight=1)
    main_frame.columnconfigure(0, weight=1)



def setup_oracle_connection(self):
    """
    Instanciar conexão com banco oracle
    """
    try:
        self.db_conn = oracledb.connect(
            user=self.ORACLE_USER, password=self.ORACLE_PASS, dsn=self.ORACLE_DSN
        )
        self.db_cursor = self.db_conn.cursor()
        self.db_connection_label.config(text="Status Oracle DB: Conectado", foreground="green")
        print("Conexão com o Oracle Database estabelecida com sucesso.")
    except Exception as e:
        self.db_conn = None
        self.db_connection_label.config(text=f"Status Oracle DB: Erro", foreground="red")
        messagebox.showerror("Erro de Banco de Dados", f"Não foi possível conectar ao Oracle DB:\n{e}")



def setup_mqtt(self):
    """
    Configura e inicia o cliente MQTT
    """
    try:
        self.client = mqtt_client.Client(mqtt_client.CallbackAPIVersion.VERSION2, client_id=self.client_id)
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.on_disconnect = self.on_disconnect
        self.client.connect(self.broker, self.port, 60)
        self.client.loop_start()
    except Exception as e:
        messagebox.showerror("Erro", f"Erro ao conectar MQTT: {str(e)}")

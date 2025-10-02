#include <WiFi.h>
#include <PubSubClient.h>
#define MQTT_MAX_PACKET_SIZE 256

const char* MOTO_ID = "moto_01"; 

// credenciais mqtt e wifi
const char* ssid = "Wokwi-GUEST";
const char* password = "";
const char* mqtt_server = "test.mosquitto.org";

WiFiClient espClient;
PubSubClient client(espClient);

// pinos
const int rgbLedPinR = 16;
const int rgbLedPinG = 17;
const int rgbLedPinB = 18;
const int trig_pin = 5;
const int echo_pin = 19;
const int buzzer = 21;
const int freq = 5000;
const int resolution = 8;

long duration;
float distance_cm;
unsigned long lastMeasurement = 0;
const unsigned long measurementInterval = 2000;

String last_sent_status = "";
float last_sent_distance = -1.0;
const float DISTANCE_THRESHOLD = 2.0;

char command_topic_buffer[100];


void setup() {
  Serial.begin(115200);
  pinMode(trig_pin, OUTPUT);
  pinMode(echo_pin, INPUT);
  pinMode(buzzer, OUTPUT);
  
  // led rgb
  ledcAttach(rgbLedPinR, freq, resolution);
  ledcAttach(rgbLedPinG, freq, resolution);
  ledcAttach(rgbLedPinB, freq, resolution);
  
  set_color(0, 0, 0);
  
  // conectar WiFi e MQTT
  setup_wifi();
  client.setServer(mqtt_server, 1883);
  client.setCallback(callback);
  
  Serial.println("ESP32 inicializado com sucesso!");
}



void loop() {
  if (!client.connected()) {
    reconnect();
  }
  client.loop();
  
  unsigned long currentTime = millis();
  if (currentTime - lastMeasurement >= measurementInterval) {
    get_distance_and_publish_if_changed();
    lastMeasurement = currentTime;
  }
  
  delay(100);
}


void setup_wifi() {
  delay(10);
  Serial.print("Conectando ao WiFi");
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nWiFi conectado!");
  Serial.print("IP: ");
  Serial.println(WiFi.localIP());
}


void reconnect() {
  while (!client.connected()) {
    Serial.print("Conectando ao MQTT...");
    String client_id = "ESP32Client-" + String(WiFi.macAddress());
    
    if (client.connect(client_id.c_str())) {
      Serial.println(" conectado!");
      
      snprintf(command_topic_buffer, sizeof(command_topic_buffer), "iot/motos/%s/comando", MOTO_ID);
      
      if (client.subscribe(command_topic_buffer)) {
        Serial.println("Subscrito ao tópico de comando específico: " + String(command_topic_buffer));
      } else {
        Serial.println("Falha ao subscrever ao tópico de comando!");
      }
      
    } else {
      Serial.print(" falha, rc=");
      Serial.print(client.state());
      Serial.println(" tentando novamente em 5 segundos");
      delay(5000);
    }
  }
}

void get_distance_and_publish_if_changed() {
  digitalWrite(trig_pin, LOW);
  delayMicroseconds(2);
  digitalWrite(trig_pin, HIGH);
  delayMicroseconds(10);
  digitalWrite(trig_pin, LOW);
  
  duration = pulseIn(echo_pin, HIGH, 30000);
  
  if (duration > 0) {
    distance_cm = duration * 0.034 / 2;
    String current_status = (distance_cm < 50) ? "ocupada" : "disponivel";
    
    if (current_status != last_sent_status || abs(distance_cm - last_sent_distance) > DISTANCE_THRESHOLD) {
      Serial.printf("Mudança detectada! Enviando dados. Dist: %.1f cm, Status: %s\n", distance_cm, current_status.c_str());

      String payload = "{\"id_moto\":\"" + String(MOTO_ID) + 
                       "\",\"status\":\"" + current_status + 
                       "\",\"distancia\":" + String(distance_cm) + "}";
      
      client.publish("iot/vaga/status", payload.c_str());

      last_sent_status = current_status;
      last_sent_distance = distance_cm;
    }
    
  } else {
    Serial.println("Erro na leitura do sensor ultrassônico");
  }
}

void set_color(int vermelho, int verde, int azul) {
  vermelho = 255 - vermelho;
  verde = 255 - verde;
  azul = 255 - azul;
  ledcWrite(rgbLedPinR, vermelho);
  ledcWrite(rgbLedPinG, verde);
  ledcWrite(rgbLedPinB, azul);
}

void buzzer_beep(int frequency, int duration_ms, int repetitions) {
  for (int i = 0; i < repetitions; i++) {
    ledcAttach(buzzer, frequency, 8);
    ledcWrite(buzzer, 128); 
    delay(duration_ms);
    ledcWrite(buzzer, 0);
    if (i < repetitions - 1) {
      delay(200);
    }
  }
  ledcDetach(buzzer);
}



void callback(char* topic, byte* payload, unsigned int length) {
  String comando = "";
  for (unsigned int i = 0; i < length; i++) {
    comando += (char)payload[i];
  }

  Serial.println("-- Comando recebido --");
  Serial.println("Tópico: " + String(topic));
  Serial.println("Comando: " + comando);
  Serial.println("------------------------------------");


  // processa o comando recebido
  if (comando == "1") {
    Serial.println("Executando comando 1: LED amarelo + buzzer");
    set_color(255, 255, 0); // Amarelo
    buzzer_beep(800, 500, 3);
    set_color(0, 0, 0); // desliga
  } else if (comando == "led_verde") {
    set_color(0, 255, 0);
  } else if (comando == "led_vermelho") {
    set_color(255, 0, 0);
  } else if (comando == "led_off") {
    set_color(0, 0, 0);
  } else {
    Serial.println("Comando não reconhecido.");
  }
}



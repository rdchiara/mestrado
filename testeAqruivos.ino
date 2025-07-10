#include <WiFi.h>
#include <WiFiUdp.h>

// ====== CONFIGURAÇÕES DE REDE ======
const char* ssid = "FSIRG-WS2 8660";
const char* password = "teste123";

// ====== CONFIGURAÇÕES DE COMUNICAÇÃO ======
const char* hostIP = "192.168.137.1"; // IP do seu PC (para onde o ESP32 envia dados)
const int hostPort = 4210;            // Porta que o Python está escutando (para o ESP32 enviar)
const int espListenPort = 4211;       // Porta que o ESP32 vai escutar por comandos do Python

WiFiUDP udpSend;    // Objeto UDP para ENVIAR dados (ESP32 -> PC)
WiFiUDP udpReceive; // Objeto UDP para RECEBER comandos (PC -> ESP32)

// ====== VARIÁVEIS DE ESTADO E DADOS SIMULADOS ======
bool acquisitionActive = false; // Flag para controlar se a aquisição está ATIVA
unsigned long acquisitionStartTime; // Tempo em millis() que a aquisição começou
unsigned long acquisitionEndTime;   // Tempo em millis() que a aquisição deve parar

float tensao = 12.0;
float corrente = 1.5;
int rotacao = 1500;

void setup() {
  Serial.begin(115200);

  // Conectar ao WiFi
  WiFi.begin(ssid, password);
  Serial.print("Conectando-se ao WiFi");
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nConectado! IP local: " + WiFi.localIP().toString());

  // Iniciar a escuta UDP para RECEBER comandos na nova porta
  udpReceive.begin(espListenPort);
  Serial.println("ESP32 escutando comandos UDP na porta: " + String(espListenPort));

  // Inicializa o gerador de números aleatórios
  randomSeed(analogRead(0));
}

void loop() {
  // --- Parte 1: Escutar por comandos do PC ---
  int packetSize = udpReceive.parsePacket();
  if (packetSize) {
    char incomingPacket[255];
    int len = udpReceive.read(incomingPacket, 255);
    if (len > 0) {
      incomingPacket[len] = 0; // Null-terminate a string
    }
    String command = String(incomingPacket);
    Serial.print("Comando UDP recebido: ");
    Serial.println(command);

    if (command.startsWith("START_ACQUISITION:")) {
      // Extrai a duração do comando
      int colonIndex = command.indexOf(':');
      if (colonIndex != -1) {
        String durationStr = command.substring(colonIndex + 1);
        unsigned long durationMs = durationStr.toInt();

        if (durationMs > 0) {
          acquisitionActive = true;
          acquisitionStartTime = millis(); // O contador de tempo para os dados começa aqui
          acquisitionEndTime = acquisitionStartTime + durationMs;
          Serial.print("Comando 'START_ACQUISITION' com duração de ");
          Serial.print(durationMs);
          Serial.println("ms recebido. Iniciando aquisição de dados.");
        } else {
          Serial.println("Duração inválida recebida no comando START_ACQUISITION.");
        }
      } else {
        Serial.println("Formato de comando START_ACQUISITION inválido. Esperado 'START_ACQUISITION:DURACAO_MS'");
      }
    } else if (command == "STOP_ACQUISITION") {
      acquisitionActive = false;
      Serial.println("Comando 'STOP_ACQUISITION' recebido. Parando aquisição de dados.");
    }
  }

  // --- Parte 2: Enviar dados SE a aquisição estiver ativa e dentro do tempo ---
  if (acquisitionActive) {
    if (millis() < acquisitionEndTime) { // Verifica se o tempo de aquisição não terminou
      // Atualizar os valores (aqui estamos só simulando com variação aleatória)
      tensao = 12.0 + random(-50, 50) / 100.0;     // Ex: 11.50 a 12.50 V
      corrente = 1.5 + random(-20, 20) / 100.0;    // Ex: 1.30 a 1.70 A
      rotacao = 1500 + random(-100, 100);          // Ex: 1400 a 1600 RPM

      // Calcular o tempo decorrido desde o início em milissegundos
      unsigned long elapsedTime = millis() - acquisitionStartTime;

      // Montar mensagem com o timestamp do ESP32
      String mensagem = "Tempo_ms:" + String(elapsedTime)
                        + ", Tensao:" + String(tensao, 2)
                        + ", Corrente:" + String(corrente, 2)
                        + ", Rotacao:" + String(rotacao) + ",\n";

      // Enviar via UDP (usando udpSend)
      udpSend.beginPacket(hostIP, hostPort);
      udpSend.print(mensagem);
      udpSend.endPacket();

      // Serial.print("Enviado: "); // Comentei para não sobrecarregar o Serial Monitor
      // Serial.print(mensagem);

      delay(10); // Envia a cada 10 milissegundos para 100Hz
    } else {
      // Tempo de aquisição esgotado
      acquisitionActive = false;
      Serial.println("Tempo de aquisição esgotado. Parando envio de dados.");
      // Opcional: Enviar um comando STOP de volta para o PC ou uma mensagem de "finalizado"
      // para que o PC saiba que a aquisição terminou.
    }
  } else {
    delay(500); // Se não estiver aquisitando, espera um pouco para não sobrecarregar
  }
}
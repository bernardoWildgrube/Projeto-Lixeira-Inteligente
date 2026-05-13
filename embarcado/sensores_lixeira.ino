// Codigo para Arduino: sensor ultrassonico + tampa + LEDs + buzzer.
// Envia pela serial no formato: nivel;tampa
// Exemplo: 72.5;fechada

#include <Arduino.h>

const int TRIG_PIN = 3;
const int ECHO_PIN = 4;
const int TAMPA_PIN = 5;
const int LED_VERDE = 9;
const int LED_AMARELO = 10;
const int LED_VERMELHO = 11;
const int BUZZER = 12;

const float DISTANCIA_VAZIA_CM = 35.0;
const float DISTANCIA_CHEIA_CM = 5.0;
const unsigned long TEMPO_TAMPA_ALERTA_MS = 120000;
const unsigned long TIMEOUT_ULTRASSONICO_US = 30000;

unsigned long tampaAbertaDesde = 0;

void setup() {
  Serial.begin(9600);

  pinMode(TRIG_PIN, OUTPUT);
  pinMode(ECHO_PIN, INPUT);
  pinMode(TAMPA_PIN, INPUT_PULLUP);
  pinMode(LED_VERDE, OUTPUT);
  pinMode(LED_AMARELO, OUTPUT);
  pinMode(LED_VERMELHO, OUTPUT);
  pinMode(BUZZER, OUTPUT);

  digitalWrite(TRIG_PIN, LOW);
  digitalWrite(LED_VERDE, LOW);
  digitalWrite(LED_AMARELO, LOW);
  digitalWrite(LED_VERMELHO, LOW);
  digitalWrite(BUZZER, LOW);
}

float medirDistanciaCm() {
  digitalWrite(TRIG_PIN, LOW);
  delayMicroseconds(2);
  digitalWrite(TRIG_PIN, HIGH);
  delayMicroseconds(10);
  digitalWrite(TRIG_PIN, LOW);

  unsigned long duracao = pulseIn(ECHO_PIN, HIGH, TIMEOUT_ULTRASSONICO_US);

  if (duracao == 0) {
    return DISTANCIA_VAZIA_CM;
  }

  return (duracao * 0.0343) / 2.0;
}

float limitar(float valor, float minimo, float maximo) {
  if (valor < minimo) return minimo;
  if (valor > maximo) return maximo;
  return valor;
}

float calcularNivelOcupacao(float distanciaCm) {
  float faixaUtil = DISTANCIA_VAZIA_CM - DISTANCIA_CHEIA_CM;
  float ocupado = DISTANCIA_VAZIA_CM - distanciaCm;
  float nivel = (ocupado / faixaUtil) * 100.0;
  return limitar(nivel, 0.0, 100.0);
}

void atualizarLeds(float nivel) {
  if (nivel >= 85.0) {
    digitalWrite(LED_VERDE, LOW);
    digitalWrite(LED_AMARELO, LOW);
    digitalWrite(LED_VERMELHO, HIGH);
  } else if (nivel >= 65.0) {
    digitalWrite(LED_VERDE, LOW);
    digitalWrite(LED_AMARELO, HIGH);
    digitalWrite(LED_VERMELHO, LOW);
  } else {
    digitalWrite(LED_VERDE, HIGH);
    digitalWrite(LED_AMARELO, LOW);
    digitalWrite(LED_VERMELHO, LOW);
  }
}

void atualizarBuzzer(bool tampaAberta) {
  if (tampaAberta) {
    if (tampaAbertaDesde == 0) {
      tampaAbertaDesde = millis();
    }

    if (millis() - tampaAbertaDesde >= TEMPO_TAMPA_ALERTA_MS) {
      tone(BUZZER, 1000, 250);
    }
  } else {
    tampaAbertaDesde = 0;
    noTone(BUZZER);
  }
}

void loop() {
  float distancia = medirDistanciaCm();
  float nivel = calcularNivelOcupacao(distancia);
  bool tampaAberta = digitalRead(TAMPA_PIN) == LOW;

  atualizarLeds(nivel);
  atualizarBuzzer(tampaAberta);

  Serial.print(nivel, 1);
  Serial.print(";");
  if (tampaAberta) {
    Serial.println("aberta");
  } else {
    Serial.println("fechada");
  }

  delay(5000);
}

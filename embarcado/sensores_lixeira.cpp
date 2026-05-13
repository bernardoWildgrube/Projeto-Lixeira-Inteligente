const int TRIG_PIN = 3;
const int ECHO_PIN = 4;
const int TAMPA_PIN = 5;
const int LED_VERDE = 9;
const int LED_AMARELO = 10;
const int LED_VERMELHO = 11;
const int BUZZER = 12;

const int DISTANCIA_VAZIA_CM = 35;
const int DISTANCIA_CHEIA_CM = 5;
const unsigned long TEMPO_TAMPA_ALERTA_MS = 120000;

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
}

long medirDistancia() {
  digitalWrite(TRIG_PIN, LOW);
  delayMicroseconds(2);
  digitalWrite(TRIG_PIN, HIGH);
  delayMicroseconds(10);
  digitalWrite(TRIG_PIN, LOW);
  long duracao = pulseIn(ECHO_PIN, HIGH);
  return duracao * 0.034 / 2;
}

float calcularNivel(long distancia) {
  float faixaUtil = DISTANCIA_VAZIA_CM - DISTANCIA_CHEIA_CM;
  float ocupado = DISTANCIA_VAZIA_CM - distancia;
  float nivel = (ocupado / faixaUtil) * 100.0;
  if (nivel < 0) nivel = 0;
  if (nivel > 100) nivel = 100;
  return nivel;
}

void atualizarAtuadores(float nivel, bool tampaAberta) {
  digitalWrite(LED_VERDE, nivel < 65);
  digitalWrite(LED_AMARELO, nivel >= 65 && nivel < 85);
  digitalWrite(LED_VERMELHO, nivel >= 85);

  if (tampaAberta) {
    if (tampaAbertaDesde == 0) tampaAbertaDesde = millis();
    if (millis() - tampaAbertaDesde > TEMPO_TAMPA_ALERTA_MS) {
      tone(BUZZER, 1000, 250);
    }
  } else {
    tampaAbertaDesde = 0;
    noTone(BUZZER);
  }
}

void loop() {
  long distancia = medirDistancia();
  float nivel = calcularNivel(distancia);
  bool tampaAberta = digitalRead(TAMPA_PIN) == LOW;

  atualizarAtuadores(nivel, tampaAberta);

  Serial.print(nivel);
  Serial.print(";");
  Serial.println(tampaAberta ? "aberta" : "fechada");

  delay(5000);
}

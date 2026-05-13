import random
import time
from datetime import datetime

import requests


URL_API = "http://10.1.25.112:5000/api"
IDENTIFICADOR_LIXEIRA = "LIX-001"

# Ajuste estes valores conforme o sensor ultrassonico usado no prototipo.
ALTURA_LIXEIRA_CM = 40
DISTANCIA_LIXEIRA_VAZIA_CM = 35
DISTANCIA_LIXEIRA_CHEIA_CM = 5
TEMPO_TAMPA_ABERTA_ALERTA = 120


def calcular_nivel_ocupacao(distancia_cm):
    faixa_util = DISTANCIA_LIXEIRA_VAZIA_CM - DISTANCIA_LIXEIRA_CHEIA_CM
    ocupado = DISTANCIA_LIXEIRA_VAZIA_CM - distancia_cm
    percentual = (ocupado / faixa_util) * 100
    return max(0, min(100, round(percentual, 1)))


def ler_sensor_distancia_simulado():
    # Troque por GPIO + sensor ultrassonico HC-SR04 na Raspberry.
    return random.uniform(DISTANCIA_LIXEIRA_CHEIA_CM, DISTANCIA_LIXEIRA_VAZIA_CM)


def ler_tampa_simulada():
    # Troque por botao, reed switch, sensor de inclinacao ou fim de curso.
    return random.choice(["fechada", "fechada", "fechada", "aberta"])


def acionar_atuadores(nivel, tampa_status, tampa_aberta_desde):
    if nivel >= 85:
        print("LED vermelho: lixeira cheia")
    elif nivel >= 65:
        print("LED amarelo: lixeira quase cheia")
    else:
        print("LED verde: espaco disponivel")

    if tampa_status == "aberta" and tampa_aberta_desde:
        aberta_por = (datetime.now() - tampa_aberta_desde).total_seconds()
        if aberta_por >= TEMPO_TAMPA_ABERTA_ALERTA:
            print("Buzzer: tampa aberta por muito tempo")


def enviar_telemetria(nivel, tampa_status, evento):
    payload = {
        "nivel_ocupacao": nivel,
        "tampa_status": tampa_status,
        "evento": evento,
        "mensagem": "Atualizacao enviada pela Raspberry Pi",
    }
    response = requests.post(
        f"{URL_API}/lixeiras/{IDENTIFICADOR_LIXEIRA}/telemetria",
        json=payload,
        timeout=5,
    )
    response.raise_for_status()
    print("Dados enviados:", response.json())


def main():
    ultimo_status_tampa = "fechada"
    tampa_aberta_desde = None

    while True:
        distancia = ler_sensor_distancia_simulado()
        nivel = calcular_nivel_ocupacao(distancia)
        tampa_status = ler_tampa_simulada()

        evento = "telemetria"
        if tampa_status != ultimo_status_tampa:
            evento = "tampa_aberta" if tampa_status == "aberta" else "tampa_fechada"
            tampa_aberta_desde = datetime.now() if tampa_status == "aberta" else None
            ultimo_status_tampa = tampa_status

        acionar_atuadores(nivel, tampa_status, tampa_aberta_desde)

        try:
            enviar_telemetria(nivel, tampa_status, evento)
        except requests.RequestException as erro:
            print("Erro ao enviar dados para API:", erro)

        time.sleep(5)


if __name__ == "__main__":
    main()

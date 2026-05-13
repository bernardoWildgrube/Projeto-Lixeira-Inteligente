import serial
import requests


PORTA_SERIAL = "/dev/ttyACM0"
BAUDRATE = 9600
URL_API = "http://10.1.25.112:5000/api"
IDENTIFICADOR_LIXEIRA = "LIX-001"


def enviar(nivel, tampa_status):
    response = requests.post(
        f"{URL_API}/lixeiras/{IDENTIFICADOR_LIXEIRA}/telemetria",
        json={
            "nivel_ocupacao": nivel,
            "tampa_status": tampa_status,
            "evento": "telemetria_serial",
            "mensagem": "Dados lidos do Arduino pela Raspberry Pi",
        },
        timeout=5,
    )
    response.raise_for_status()
    print("Enviado:", response.json())


with serial.Serial(PORTA_SERIAL, BAUDRATE, timeout=1) as ser:
    while True:
        linha = ser.readline().decode("utf-8").strip()
        if not linha:
            continue

        try:
            nivel_texto, tampa_status = linha.split(";")
            enviar(float(nivel_texto), tampa_status)
        except ValueError:
            print("Linha invalida recebida:", linha)
        except requests.RequestException as erro:
            print("Erro ao enviar para a API:", erro)

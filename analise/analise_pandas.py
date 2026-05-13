import pandas as pd


CSV_URL = "http://10.1.25.112:5000/api/export/logs.csv"


def carregar_logs():
    df = pd.read_csv(CSV_URL)
    df["criado_em"] = pd.to_datetime(df["criado_em"])
    df["data"] = df["criado_em"].dt.date
    return df


def lixeiras_cheias_no_dia(df, data):
    data = pd.to_datetime(data).date()
    cheias = df[(df["data"] == data) & (df["nivel_ocupacao"] >= 85)]
    return cheias[["criado_em", "identificador", "nome", "nivel_ocupacao"]]


def aberturas_por_lixeira_no_dia(df, data):
    data = pd.to_datetime(data).date()
    aberturas = df[(df["data"] == data) & (df["evento"] == "tampa_aberta")]
    return aberturas.groupby(["identificador", "nome"]).size().reset_index(name="aberturas")


def tampas_abertas_em_momento(df, momento):
    momento = pd.to_datetime(momento)
    antes = df[df["criado_em"] <= momento].sort_values("criado_em")
    ultimos = antes.groupby("identificador").tail(1)
    return ultimos[ultimos["tampa_status"] == "aberta"][
        ["criado_em", "identificador", "nome", "tampa_status"]
    ]


if __name__ == "__main__":
    logs = carregar_logs()
    hoje = pd.Timestamp.now().date()

    print("Lixeiras cheias hoje:")
    print(lixeiras_cheias_no_dia(logs, hoje))

    print("\nQuantidade de aberturas hoje:")
    print(aberturas_por_lixeira_no_dia(logs, hoje))

    print("\nLixeiras com tampa aberta agora:")
    print(tampas_abertas_em_momento(logs, pd.Timestamp.now()))

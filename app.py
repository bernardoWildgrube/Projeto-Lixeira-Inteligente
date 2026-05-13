from datetime import datetime, timezone
import csv
import io
import os
import sqlite3

from flask import Flask, jsonify, redirect, request, send_from_directory, Response


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "lixeiras.db")
WEB_DIR = os.path.join(BASE_DIR, "web")
USUARIO = "admin"
SENHA = "senha123"
ALERTA_TAMPA_SEGUNDOS = 120
ALERTA_NIVEL_PERCENTUAL = 85

app = Flask(__name__, static_folder=WEB_DIR, static_url_path="")


def agora_iso():
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def row_to_dict(row):
    return dict(row) if row else None


def init_db():
    conn = get_db()
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS lixeiras (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            identificador TEXT NOT NULL UNIQUE,
            nome TEXT NOT NULL,
            endereco TEXT NOT NULL,
            latitude REAL NOT NULL,
            longitude REAL NOT NULL,
            capacidade_total REAL NOT NULL,
            capacidade_utilizada REAL NOT NULL DEFAULT 0,
            nivel_ocupacao REAL NOT NULL DEFAULT 0,
            tampa_status TEXT NOT NULL DEFAULT 'fechada',
            status_operacional TEXT NOT NULL DEFAULT 'ativa',
            tampa_aberta_desde TEXT,
            ultima_atualizacao TEXT
        );

        CREATE TABLE IF NOT EXISTS logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lixeira_id INTEGER NOT NULL,
            identificador TEXT NOT NULL,
            evento TEXT NOT NULL,
            nivel_ocupacao REAL NOT NULL,
            espaco_livre REAL NOT NULL,
            tampa_status TEXT NOT NULL,
            mensagem TEXT,
            criado_em TEXT NOT NULL,
            FOREIGN KEY (lixeira_id) REFERENCES lixeiras(id)
        );
        """
    )

    colunas = [row["name"] for row in conn.execute("PRAGMA table_info(lixeiras)").fetchall()]
    if "capacidade_utilizada" not in colunas:
        conn.execute("ALTER TABLE lixeiras ADD COLUMN capacidade_utilizada REAL NOT NULL DEFAULT 0")
        conn.execute(
            """
            UPDATE lixeiras
            SET capacidade_utilizada = capacidade_total * (nivel_ocupacao / 100.0)
            """
        )

    total = conn.execute("SELECT COUNT(*) AS total FROM lixeiras").fetchone()["total"]
    if total == 0:
        agora = agora_iso()
        conn.executemany(
            """
            INSERT INTO lixeiras (
                identificador, nome, endereco, latitude, longitude,
                capacidade_total, nivel_ocupacao, tampa_status,
                capacidade_utilizada, status_operacional, ultima_atualizacao
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    "LIX-001",
                    "Lixeira Praca Central",
                    "Praca Central, Centro",
                    -28.2621,
                    -52.4065,
                    100,
                    35,
                    "fechada",
                    35,
                    "ativa",
                    agora,
                ),
                (
                    "LIX-002",
                    "Lixeira Terminal",
                    "Terminal de Onibus",
                    -28.2635,
                    -52.4090,
                    100,
                    78,
                    "fechada",
                    78,
                    "ativa",
                    agora,
                ),
            ],
        )
    conn.commit()
    conn.close()


def registrar_log(conn, lixeira, evento, mensagem=""):
    nivel = float(lixeira["nivel_ocupacao"])
    espaco_livre = max(0, 100 - nivel)
    conn.execute(
        """
        INSERT INTO logs (
            lixeira_id, identificador, evento, nivel_ocupacao,
            espaco_livre, tampa_status, mensagem, criado_em
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            lixeira["id"],
            lixeira["identificador"],
            evento,
            nivel,
            espaco_livre,
            lixeira["tampa_status"],
            mensagem,
            agora_iso(),
        ),
    )


def calcular_nivel(capacidade_total, capacidade_utilizada):
    total = max(1, float(capacidade_total))
    usada = max(0, min(float(capacidade_utilizada), total))
    return round((usada / total) * 100, 2)


def completar_lixeira(item):
    total = max(1, float(item.get("capacidade_total", 100)))
    usada = max(0, min(float(item.get("capacidade_utilizada", 0)), total))
    item["capacidade_utilizada"] = usada
    item["nivel_ocupacao"] = calcular_nivel(total, usada)
    item["capacidade_livre"] = round(total - usada, 2)
    item["espaco_livre"] = round(100 - item["nivel_ocupacao"], 2)
    item["alertas"] = calcular_alertas(item)
    return item


def calcular_alertas(lixeira):
    alertas = []
    nivel = float(lixeira["nivel_ocupacao"])
    if nivel >= ALERTA_NIVEL_PERCENTUAL:
        alertas.append("Lixeira cheia ou proxima da capacidade maxima")

    if lixeira["tampa_status"] == "aberta":
        alertas.append("Tampa aberta")
        aberta_desde = lixeira["tampa_aberta_desde"]
        if aberta_desde:
            try:
                inicio = datetime.fromisoformat(aberta_desde)
                segundos = (datetime.now(inicio.tzinfo) - inicio).total_seconds()
                if segundos >= ALERTA_TAMPA_SEGUNDOS:
                    alertas.append("Tampa aberta ha muito tempo")
            except ValueError:
                pass
    return alertas


@app.after_request
def add_cors_headers(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    response.headers["Access-Control-Allow-Methods"] = "GET,POST,PUT,DELETE,OPTIONS"
    return response


@app.route("/")
def index():
    return send_from_directory(WEB_DIR, "index.html")


@app.route("/entrar", methods=["POST"])
def entrar():
    usuario = request.form.get("usuario", "")
    senha = request.form.get("senha", "")
    if usuario == USUARIO and senha == SENHA:
        return redirect("/painel")
    return redirect("/?erro=login")


@app.route("/painel")
def painel():
    return send_from_directory(WEB_DIR, "painel.html")


@app.route("/api/login", methods=["POST", "OPTIONS"])
def login():
    if request.method == "OPTIONS":
        return ("", 204)
    dados = request.get_json(force=True)
    ok = dados.get("usuario") == USUARIO and dados.get("senha") == SENHA
    return jsonify({"autenticado": ok}), (200 if ok else 401)


@app.route("/api/lixeiras", methods=["GET", "POST", "OPTIONS"])
def lixeiras():
    if request.method == "OPTIONS":
        return ("", 204)
    conn = get_db()
    if request.method == "GET":
        rows = conn.execute("SELECT * FROM lixeiras ORDER BY nome").fetchall()
        resultado = []
        for row in rows:
            item = row_to_dict(row)
            resultado.append(completar_lixeira(item))
        conn.close()
        return jsonify(resultado)

    dados = request.get_json(force=True)
    agora = agora_iso()
    capacidade_total = float(dados.get("capacidade_total", 100))
    capacidade_utilizada = float(dados.get("capacidade_utilizada", 0))
    nivel_ocupacao = calcular_nivel(capacidade_total, capacidade_utilizada)
    conn.execute(
        """
        INSERT INTO lixeiras (
            identificador, nome, endereco, latitude, longitude,
            capacidade_total, capacidade_utilizada, nivel_ocupacao, tampa_status,
            status_operacional, ultima_atualizacao
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            dados["identificador"],
            dados["nome"],
            dados["endereco"],
            float(dados["latitude"]),
            float(dados["longitude"]),
            capacidade_total,
            capacidade_utilizada,
            nivel_ocupacao,
            dados.get("tampa_status", "fechada"),
            dados.get("status_operacional", "ativa"),
            agora,
        ),
    )
    nova = conn.execute(
        "SELECT * FROM lixeiras WHERE identificador = ?", (dados["identificador"],)
    ).fetchone()
    registrar_log(conn, nova, "cadastro", "Lixeira cadastrada")
    conn.commit()
    resposta = completar_lixeira(row_to_dict(nova))
    conn.close()
    return jsonify(resposta), 201


@app.route("/api/lixeiras/<int:lixeira_id>", methods=["PUT", "DELETE", "OPTIONS"])
def lixeira_por_id(lixeira_id):
    if request.method == "OPTIONS":
        return ("", 204)
    conn = get_db()
    atual = conn.execute("SELECT * FROM lixeiras WHERE id = ?", (lixeira_id,)).fetchone()
    if not atual:
        conn.close()
        return jsonify({"erro": "Lixeira nao encontrada"}), 404

    if request.method == "DELETE":
        conn.execute("DELETE FROM lixeiras WHERE id = ?", (lixeira_id,))
        conn.commit()
        conn.close()
        return jsonify({"ok": True})

    dados = request.get_json(force=True)
    capacidade_total = float(dados.get("capacidade_total", 100))
    capacidade_utilizada = float(dados.get("capacidade_utilizada", 0))
    nivel_ocupacao = calcular_nivel(capacidade_total, capacidade_utilizada)
    conn.execute(
        """
        UPDATE lixeiras
        SET identificador = ?, nome = ?, endereco = ?, latitude = ?, longitude = ?,
            capacidade_total = ?, capacidade_utilizada = ?, nivel_ocupacao = ?,
            tampa_status = ?, status_operacional = ?, ultima_atualizacao = ?
        WHERE id = ?
        """,
        (
            dados["identificador"],
            dados["nome"],
            dados["endereco"],
            float(dados["latitude"]),
            float(dados["longitude"]),
            capacidade_total,
            capacidade_utilizada,
            nivel_ocupacao,
            dados.get("tampa_status", "fechada"),
            dados.get("status_operacional", "ativa"),
            agora_iso(),
            lixeira_id,
        ),
    )
    atualizada = conn.execute("SELECT * FROM lixeiras WHERE id = ?", (lixeira_id,)).fetchone()
    registrar_log(conn, atualizada, "edicao", "Dados cadastrais atualizados")
    conn.commit()
    resposta = completar_lixeira(row_to_dict(atualizada))
    conn.close()
    return jsonify(resposta)


@app.route("/api/lixeiras/<identificador>/telemetria", methods=["POST", "OPTIONS"])
def receber_telemetria(identificador):
    if request.method == "OPTIONS":
        return ("", 204)
    dados = request.get_json(force=True)
    tampa_status = dados.get("tampa_status", "fechada")
    agora = agora_iso()

    conn = get_db()
    lixeira = conn.execute(
        "SELECT * FROM lixeiras WHERE identificador = ?", (identificador,)
    ).fetchone()
    if not lixeira:
        conn.close()
        return jsonify({"erro": "Lixeira nao cadastrada"}), 404

    capacidade_total = float(dados.get("capacidade_total", lixeira["capacidade_total"]))
    if "capacidade_utilizada" in dados:
        capacidade_utilizada = float(dados["capacidade_utilizada"])
        nivel = calcular_nivel(capacidade_total, capacidade_utilizada)
    else:
        nivel = max(0, min(100, float(dados["nivel_ocupacao"])))
        capacidade_utilizada = capacidade_total * (nivel / 100)

    tampa_aberta_desde = lixeira["tampa_aberta_desde"]
    if tampa_status == "aberta" and lixeira["tampa_status"] != "aberta":
        tampa_aberta_desde = agora
    if tampa_status == "fechada":
        tampa_aberta_desde = None

    conn.execute(
        """
        UPDATE lixeiras
        SET capacidade_total = ?, capacidade_utilizada = ?, nivel_ocupacao = ?,
            tampa_status = ?, tampa_aberta_desde = ?,
            status_operacional = 'ativa', ultima_atualizacao = ?
        WHERE identificador = ?
        """,
        (capacidade_total, capacidade_utilizada, nivel, tampa_status, tampa_aberta_desde, agora, identificador),
    )
    atualizada = conn.execute(
        "SELECT * FROM lixeiras WHERE identificador = ?", (identificador,)
    ).fetchone()

    mensagem = dados.get("mensagem", "")
    registrar_log(conn, atualizada, dados.get("evento", "telemetria"), mensagem)
    alertas = calcular_alertas(atualizada)
    for alerta in alertas:
        registrar_log(conn, atualizada, "alerta", alerta)

    conn.commit()
    resposta = completar_lixeira(row_to_dict(atualizada))
    resposta["alertas"] = alertas
    conn.close()
    return jsonify(resposta)


@app.route("/api/logs")
def listar_logs():
    conn = get_db()
    rows = conn.execute(
        """
        SELECT logs.*, lixeiras.nome, lixeiras.endereco
        FROM logs
        JOIN lixeiras ON lixeiras.id = logs.lixeira_id
        ORDER BY logs.criado_em DESC
        LIMIT 200
        """
    ).fetchall()
    resposta = [row_to_dict(row) for row in rows]
    conn.close()
    return jsonify(resposta)


@app.route("/api/alertas")
def listar_alertas():
    conn = get_db()
    rows = conn.execute("SELECT * FROM lixeiras ORDER BY nome").fetchall()
    resposta = []
    for row in rows:
        item = row_to_dict(row)
        alertas = calcular_alertas(item)
        if alertas:
            item["alertas"] = alertas
            resposta.append(item)
    conn.close()
    return jsonify(resposta)


@app.route("/api/export/logs.csv")
def exportar_logs_csv():
    conn = get_db()
    rows = conn.execute(
        """
        SELECT logs.criado_em, logs.identificador, lixeiras.nome, lixeiras.endereco,
               logs.evento, logs.nivel_ocupacao, logs.espaco_livre,
               logs.tampa_status, logs.mensagem
        FROM logs
        JOIN lixeiras ON lixeiras.id = logs.lixeira_id
        ORDER BY logs.criado_em ASC
        """
    ).fetchall()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(
        [
            "criado_em",
            "identificador",
            "nome",
            "endereco",
            "evento",
            "nivel_ocupacao",
            "espaco_livre",
            "tampa_status",
            "mensagem",
        ]
    )
    for row in rows:
        writer.writerow([row[col] for col in row.keys()])
    conn.close()
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=logs_lixeiras.csv"},
    )


if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=5000, debug=True)

# Lixeira Inteligente - MVP

Sistema base para o trabalho de lixeiras inteligentes. Ele usa Flask, SQLite,
interface web com mapa, API para a Raspberry Pi, exportacao CSV e analise com
Pandas.

## IP do site

O projeto foi configurado para usar:

```text
http://10.1.25.112:5000
```

Esse IP deve ser o IP da maquina que vai rodar o Flask na rede.

## Como executar

Se `python` ou `pip` nao forem reconhecidos no Windows, instale o Python em
<https://www.python.org/downloads/> e marque a opcao **Add python.exe to PATH**
durante a instalacao.

Entre na pasta do projeto:

```bash
cd lixeira-inteligente
```

Instale as dependencias:

```bash
pip install -r requirements.txt
```

Rode o servidor:

```bash
python app.py
```

Acesse no navegador:

```text
http://10.1.25.112:5000
```

Login:

```text
Usuario: admin
Senha: senha123
```

## O que ja esta pronto

- Login simples com usuario e senha.
- Cadastro, listagem, edicao e exclusao de lixeiras.
- Duas lixeiras cadastradas automaticamente no primeiro uso.
- Mapa em tempo real com latitude e longitude.
- Visualizacao de nivel de ocupacao, espaco livre, tampa e ultima atualizacao.
- Alertas para lixeira cheia ou proxima de cheia.
- Alertas para tampa aberta.
- Logs de atualizacao.
- Exportacao CSV em `/api/export/logs.csv`.
- Script Pandas para responder perguntas da avaliacao.
- Scripts de exemplo para Raspberry Pi e Arduino.

## Principais endpoints da API

```text
POST /api/login
GET  /api/lixeiras
POST /api/lixeiras
PUT  /api/lixeiras/<id>
DELETE /api/lixeiras/<id>
POST /api/lixeiras/<identificador>/telemetria
GET  /api/logs
GET  /api/alertas
GET  /api/export/logs.csv
```

Exemplo de envio da Raspberry:

```json
{
  "nivel_ocupacao": 72,
  "tampa_status": "fechada",
  "evento": "telemetria",
  "mensagem": "Atualizacao enviada pela Raspberry Pi"
}
```

URL:

```text
POST http://10.1.25.112:5000/api/lixeiras/LIX-001/telemetria
```

## Arquivos importantes

- `app.py`: backend Flask, banco SQLite e API.
- `web/index.html`: pagina principal.
- `web/script.js`: consumo da API e atualizacao da tela.
- `web/style.css`: visual do sistema.
- `embarcado/lixeira_pi.py`: exemplo direto para Raspberry Pi.
- `embarcado/sensores_lixeira.cpp`: exemplo para Arduino com sensor ultrassonico.
- `embarcado/serial_para_api.py`: Raspberry lendo serial do Arduino e enviando para API.
- `analise/analise_pandas.py`: analise dos logs com Pandas.

## Observacao para apresentacao

Para demonstrar sem hardware, rode `embarcado/lixeira_pi.py`. Ele simula leituras
de nivel e tampa, enviando atualizacoes para o backend a cada 5 segundos.

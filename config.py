"""
Configurações compartilhadas do projeto.
Cada serviço (publisher, subscriber, dashboard) importa este arquivo.

Observação: o host do broker é lido de variável de ambiente para que o mesmo
código funcione tanto rodando dentro do Docker (host = "mosquitto", nome do
serviço no compose) quanto rodando localmente fora do Docker (host = "localhost").
"""

import os

# -----------------------------------------------------------------------------

# Broker MQTT

MQTT_HOST = os.getenv("MQTT_HOST", "localhost")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))
MQTT_KEEPALIVE = 60


# -----------------------------------------------------------------------------

# Tópicos MQTT

TOPIC_BASE = "industria/tanque"

TOPICS = {
    "temperatura": f"{TOPIC_BASE}/temperatura",
    "nivel":       f"{TOPIC_BASE}/nivel",
    "pressao":     f"{TOPIC_BASE}/pressao",
    "vazao":       f"{TOPIC_BASE}/vazao",
}

# Tópico wildcard para o subscriber assinar todos de uma vez
TOPIC_WILDCARD = f"{TOPIC_BASE}/+"


# -----------------------------------------------------------------------------

# Faixas e unidades dos sensores

SENSORES = {
    "temperatura": {"min": 20.0,  "max": 90.0,  "unidade": "°C",    "inicial": 55.0},
    "nivel":       {"min": 0.0,   "max": 100.0, "unidade": "%",     "inicial": 60.0},
    "pressao":     {"min": 0.0,   "max": 10.0,  "unidade": "bar",   "inicial": 5.0},
    "vazao":       {"min": 0.0,   "max": 200.0, "unidade": "L/min", "inicial": 100.0},
}


# -----------------------------------------------------------------------------

# Frequência de publicação (segundos entre cada envio)

INTERVALO_PUBLICACAO = 1.0


# -----------------------------------------------------------------------------

# Banco de dados

# Caminho do SQLite — em Docker é montado como volume em /data/tanque.db
DB_PATH = os.getenv("DB_PATH", "./database/tanque.db")

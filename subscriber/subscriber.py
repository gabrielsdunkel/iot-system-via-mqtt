"""
Subscriber MQTT do projeto IoT.

Assina o wildcard 'industria/tanque/+' (pega os 4 sensores de uma vez),
parseia o payload JSON e grava cada leitura no SQLite.

Schema da tabela 'leituras':
    id           INTEGER PRIMARY KEY
    timestamp    TEXT     - ISO 8601 do payload (origem da leitura)
    recebido_em  TEXT     - ISO 8601 de quando o subscriber recebeu
    sensor       TEXT     - temperatura | nivel | pressao | vazao
    valor        REAL
    unidade      TEXT
    topico       TEXT     - tópico MQTT completo
"""

import json
import logging
import signal
import sqlite3
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import paho.mqtt.client as mqtt

# Permite importar config.py da raiz
sys.path.insert(0, "/app")
from config import (
    MQTT_HOST,
    MQTT_PORT,
    MQTT_KEEPALIVE,
    TOPIC_WILDCARD,
    DB_PATH,
)

# Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger("subscriber")


# Banco de dados
SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS leituras (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp   TEXT NOT NULL,
    recebido_em TEXT NOT NULL,
    sensor      TEXT NOT NULL,
    valor       REAL NOT NULL,
    unidade     TEXT NOT NULL,
    topico      TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_sensor_ts ON leituras(sensor, timestamp);
CREATE INDEX IF NOT EXISTS idx_recebido_em ON leituras(recebido_em);
"""


def inicializar_db(caminho: str) -> sqlite3.Connection:
    """Cria o banco e a tabela se não existirem, e configura PRAGMAs."""
    Path(caminho).parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(caminho, isolation_level=None, check_same_thread=False)
    # WAL: permite leitura concorrente com escrita (dashboard lê enquanto subscriber escreve)
    conn.execute("PRAGMA journal_mode=WAL;")
    # synchronous=NORMAL é seguro com WAL e mais rápido que FULL
    conn.execute("PRAGMA synchronous=NORMAL;")
    conn.executescript(SCHEMA_SQL)
    log.info(f"Banco inicializado em {caminho}")
    return conn


def inserir_leitura(conn: sqlite3.Connection, dados: dict) -> None:
    """Insere uma leitura na tabela."""
    conn.execute(
        """
        INSERT INTO leituras (timestamp, recebido_em, sensor, valor, unidade, topico)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            dados["timestamp"],
            datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
            dados["sensor"],
            float(dados["valor"]),
            dados["unidade"],
            dados["topico"],
        ),
    )


# Callbacks MQTT
def on_connect(client, userdata, flags, reason_code, properties=None):
    if reason_code == 0:
        log.info(f"Conectado ao broker {MQTT_HOST}:{MQTT_PORT}")
        client.subscribe(TOPIC_WILDCARD, qos=1)
        log.info(f"Inscrito no tópico '{TOPIC_WILDCARD}'")
    else:
        log.error(f"Falha ao conectar: código {reason_code}")


def on_disconnect(client, userdata, flags, reason_code, properties=None):
    log.warning(f"Desconectado do broker (código: {reason_code})")


def on_message(client, userdata, msg):
    """Processa cada mensagem recebida."""
    conn: sqlite3.Connection = userdata["conn"]
    try:
        payload = json.loads(msg.payload.decode("utf-8"))
        inserir_leitura(conn, payload)
        log.info(
            f"← {payload['topico']} = {payload['valor']} {payload['unidade']} "
            f"(salvo, id auto)"
        )
    except json.JSONDecodeError:
        log.error(f"Payload inválido (não-JSON) em {msg.topic}: {msg.payload!r}")
    except KeyError as e:
        log.error(f"Campo obrigatório ausente no payload de {msg.topic}: {e}")
    except sqlite3.Error as e:
        log.error(f"Erro de banco ao salvar leitura de {msg.topic}: {e}")


# Main
def main():
    conn = inicializar_db(DB_PATH)

    client = mqtt.Client(
        mqtt.CallbackAPIVersion.VERSION2,
        client_id="subscriber_db",
        userdata={"conn": conn},
    )
    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    client.on_message = on_message

    # Retry de conexão (broker pode ainda estar subindo)
    while True:
        try:
            client.connect(MQTT_HOST, MQTT_PORT, MQTT_KEEPALIVE)
            break
        except (ConnectionRefusedError, OSError) as e:
            log.warning(f"Broker indisponível ({e}). Nova tentativa em 2s...")
            time.sleep(2)

    # Parada limpa em Ctrl+C / SIGTERM
    def parar(signum, frame):
        log.info("Encerrando subscriber...")
        client.disconnect()

    signal.signal(signal.SIGINT, parar)
    signal.signal(signal.SIGTERM, parar)

    # loop_forever bloqueia e cuida de reconexões automaticamente
    client.loop_forever()

    conn.close()
    log.info("Subscriber finalizado.")


if __name__ == "__main__":
    main()

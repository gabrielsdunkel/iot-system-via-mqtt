"""
Publisher MQTT do projeto IoT.

Inicializa um simulador para cada sensor, gera leituras a cada
INTERVALO_PUBLICACAO segundos e publica cada uma no tópico correspondente.

Payload (JSON):
    {
        "valor": 67.3,
        "unidade": "°C",
        "timestamp": "2026-05-28T12:34:56.789Z",
        "topico": "industria/tanque/temperatura",
        "sensor": "temperatura"
    }
"""

import json
import logging
import signal
import sys
import time
from datetime import datetime, timezone

import paho.mqtt.client as mqtt

# Permite importar config.py da raiz do projeto
sys.path.insert(0, "/app")
from config import (
    MQTT_HOST,
    MQTT_PORT,
    MQTT_KEEPALIVE,
    TOPICS,
    SENSORES,
    INTERVALO_PUBLICACAO,
)
from simulador import SimuladorSensor

# -----------------------------------------------------------------------------
# Logging
# -----------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger("publisher")


# -----------------------------------------------------------------------------
# Callbacks MQTT
# -----------------------------------------------------------------------------
def on_connect(client, userdata, flags, reason_code, properties=None):
    if reason_code == 0:
        log.info(f"Conectado ao broker MQTT em {MQTT_HOST}:{MQTT_PORT}")
    else:
        log.error(f"Falha ao conectar ao broker, código: {reason_code}")


def on_disconnect(client, userdata, flags, reason_code, properties=None):
    log.warning(f"Desconectado do broker (código: {reason_code})")


# -----------------------------------------------------------------------------
# Inicialização dos simuladores
# -----------------------------------------------------------------------------
def criar_simuladores() -> dict[str, SimuladorSensor]:
    """Cria um simulador para cada sensor definido em config.SENSORES."""
    simuladores = {}
    for nome, cfg in SENSORES.items():
        simuladores[nome] = SimuladorSensor(
            nome=nome,
            minimo=cfg["min"],
            maximo=cfg["max"],
            valor_inicial=cfg["inicial"],
        )
    return simuladores


# -----------------------------------------------------------------------------
# Loop principal
# -----------------------------------------------------------------------------
def main():
    simuladores = criar_simuladores()

    client = mqtt.Client(
        mqtt.CallbackAPIVersion.VERSION2,
        client_id="publisher_tanque01",
    )
    client.on_connect = on_connect
    client.on_disconnect = on_disconnect

    # Tenta conectar com retry — útil quando o publisher sobe antes do broker
    while True:
        try:
            client.connect(MQTT_HOST, MQTT_PORT, MQTT_KEEPALIVE)
            break
        except (ConnectionRefusedError, OSError) as e:
            log.warning(f"Broker indisponível ({e}). Nova tentativa em 2s...")
            time.sleep(2)

    client.loop_start()

    # Tratamento de Ctrl+C / SIGTERM para parar de forma limpa
    rodando = {"v": True}

    def parar(signum, frame):
        log.info("Sinal recebido, encerrando publisher...")
        rodando["v"] = False

    signal.signal(signal.SIGINT, parar)
    signal.signal(signal.SIGTERM, parar)

    log.info(f"Publicando a cada {INTERVALO_PUBLICACAO}s nos tópicos: {list(TOPICS.values())}")

    while rodando["v"]:
        agora_iso = datetime.now(timezone.utc).isoformat(timespec="milliseconds")

        for nome, sim in simuladores.items():
            valor = sim.proximo_valor()
            topico = TOPICS[nome]
            payload = {
                "valor": valor,
                "unidade": SENSORES[nome]["unidade"],
                "timestamp": agora_iso,
                "topico": topico,
                "sensor": nome,
            }
            client.publish(topico, json.dumps(payload), qos=1)
            log.info(f"→ {topico} = {valor} {SENSORES[nome]['unidade']}")

        time.sleep(INTERVALO_PUBLICACAO)

    client.loop_stop()
    client.disconnect()
    log.info("Publisher finalizado.")


if __name__ == "__main__":
    main()

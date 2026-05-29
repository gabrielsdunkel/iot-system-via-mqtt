"""
Camada de acesso ao banco para o dashboard.

Conexão em modo read-only para garantir que o dashboard nunca
interfira nas escritas do subscriber.
"""

import sqlite3
from typing import Optional


def conectar_readonly(caminho_db: str) -> sqlite3.Connection:
    """
    Abre uma conexão read-only ao SQLite usando URI.
    Usa o mesmo arquivo WAL do subscriber sem causar locks.
    """
    uri = f"file:{caminho_db}?mode=ro"
    conn = sqlite3.connect(uri, uri=True, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def ultima_leitura_por_sensor(conn: sqlite3.Connection) -> dict[str, dict]:
    """
    Retorna a leitura mais recente de cada sensor.
    Exemplo de saída:
        {
            "temperatura": {"valor": 67.3, "unidade": "°C",
                            "timestamp": "...", "topico": "...",
                            "recebido_em": "..."},
            "nivel": {...},
            ...
        }
    """
    sql = """
        SELECT l.sensor, l.valor, l.unidade, l.timestamp, l.recebido_em, l.topico
        FROM leituras l
        INNER JOIN (
            SELECT sensor, MAX(id) AS max_id
            FROM leituras
            GROUP BY sensor
        ) m ON l.id = m.max_id
    """
    cursor = conn.execute(sql)
    return {row["sensor"]: dict(row) for row in cursor.fetchall()}


def historico(conn: sqlite3.Connection, sensor: str, limite: int = 60) -> list[dict]:
    """
    Últimas `limite` leituras de um sensor, em ordem cronológica (mais antiga primeiro).
    """
    sql = """
        SELECT timestamp, valor
        FROM leituras
        WHERE sensor = ?
        ORDER BY id DESC
        LIMIT ?
    """
    cursor = conn.execute(sql, (sensor, limite))
    linhas = [dict(r) for r in cursor.fetchall()]
    return list(reversed(linhas))  # Devolve em ordem cronológica


def ultimo_recebido_em(conn: sqlite3.Connection) -> Optional[str]:
    """
    Retorna o MAX(recebido_em) da tabela inteira como string ISO 8601,
    ou None se a tabela estiver vazia. Usado para detectar status do broker.
    """
    cursor = conn.execute("SELECT MAX(recebido_em) AS ultimo FROM leituras")
    row = cursor.fetchone()
    return row["ultimo"] if row else None

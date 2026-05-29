"""
Regras de alarme do sistema.

Cada função recebe o valor atual e retorna o nível do alarme:
    "ok"      - tudo certo
    "aviso"   - atenção (amarelo)
    "alarme"  - crítico (vermelho)
"""

# Limites
TEMP_CRITICA = 80.0      # > 80 °C → alarme vermelho
NIVEL_BAIXO = 20.0       # < 20 % → aviso amarelo
PRESSAO_CRITICA = 8.0    # > 8 bar → alarme vermelho + "sonoro" visual


def avaliar_temperatura(valor: float) -> str:
    if valor > TEMP_CRITICA:
        return "alarme"
    return "ok"


def avaliar_nivel(valor: float) -> str:
    if valor < NIVEL_BAIXO:
        return "aviso"
    return "ok"


def avaliar_pressao(valor: float) -> str:
    if valor > PRESSAO_CRITICA:
        return "alarme"
    return "ok"


def avaliar_vazao(valor: float) -> str:
    # Sem regra definida nos requisitos
    return "ok"


def avaliar_todos(leituras: dict) -> dict[str, str]:
    """
    Recebe o dict de últimas leituras (saída de db.ultima_leitura_por_sensor)
    e retorna um dict {sensor: nivel_alarme}.
    """
    avaliadores = {
        "temperatura": avaliar_temperatura,
        "nivel": avaliar_nivel,
        "pressao": avaliar_pressao,
        "vazao": avaliar_vazao,
    }
    resultado = {}
    for sensor, fn in avaliadores.items():
        if sensor in leituras:
            resultado[sensor] = fn(leituras[sensor]["valor"])
        else:
            resultado[sensor] = "ok"
    return resultado

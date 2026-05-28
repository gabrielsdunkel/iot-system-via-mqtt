"""
Simulador de sensores industriais.

Cada sensor mantém um estado interno e evolui com:
  - Random walk: pequenas variações a cada tick
  - Tendência: viés direcional que muda lentamente
  - Picos: eventos aleatórios que causam um salto súbito que decai
"""

import random
from dataclasses import dataclass


@dataclass
class EstadoSensor:
    """Estado interno de um sensor simulado."""
    valor: float
    minimo: float
    maximo: float
    tendencia: float = 0.0           # Viés direcional atual (-1 a +1)
    pico_residual: float = 0.0       # Quanto ainda falta decair do último pico

    @property
    def faixa(self) -> float:
        return self.maximo - self.minimo


class SimuladorSensor:
    """
    Simula um sensor com variação realista.

    Parâmetros:
        nome: nome do sensor (ex: "temperatura")
        minimo, maximo: faixa válida do sensor
        valor_inicial: valor de partida
        ruido_pct: amplitude do random walk como % da faixa (default 1%)
        prob_pico: chance de ocorrer um pico em cada tick (default 2%)
        amplitude_pico_pct: tamanho do pico como % da faixa (default 15%)
        decaimento_pico: fração do pico residual que se dissipa por tick (default 25%)
        prob_mudar_tendencia: chance de mudar a tendência em cada tick (default 5%)
    """

    def __init__(
        self,
        nome: str,
        minimo: float,
        maximo: float,
        valor_inicial: float,
        ruido_pct: float = 0.01,
        prob_pico: float = 0.02,
        amplitude_pico_pct: float = 0.15,
        decaimento_pico: float = 0.25,
        prob_mudar_tendencia: float = 0.05,
    ):
        self.nome = nome
        self.estado = EstadoSensor(valor=valor_inicial, minimo=minimo, maximo=maximo)
        self.ruido_pct = ruido_pct
        self.prob_pico = prob_pico
        self.amplitude_pico_pct = amplitude_pico_pct
        self.decaimento_pico = decaimento_pico
        self.prob_mudar_tendencia = prob_mudar_tendencia

    def proximo_valor(self) -> float:
        """Avança o sensor em 1 tick e retorna o novo valor."""
        st = self.estado
        faixa = st.faixa

        # 1. Atualizar tendência ocasionalmente
        if random.random() < self.prob_mudar_tendencia:
            st.tendencia = random.uniform(-1.0, 1.0)

        # 2. Random walk: ruído + viés da tendência
        ruido = random.uniform(-1.0, 1.0) * self.ruido_pct * faixa
        viés = st.tendencia * self.ruido_pct * faixa * 0.5
        st.valor += ruido + viés

        # 3. Pico ocasional
        if random.random() < self.prob_pico:
            direcao = random.choice([-1.0, 1.0])
            st.pico_residual += direcao * self.amplitude_pico_pct * faixa

        # 4. Aplicar pico residual e decair
        st.valor += st.pico_residual * self.decaimento_pico
        st.pico_residual *= (1.0 - self.decaimento_pico)

        # 5. Limitar à faixa válida (clamp) e refletir tendência se bater no limite
        if st.valor > st.maximo:
            st.valor = st.maximo
            st.tendencia = -abs(st.tendencia)
        elif st.valor < st.minimo:
            st.valor = st.minimo
            st.tendencia = abs(st.tendencia)

        return round(st.valor, 2)

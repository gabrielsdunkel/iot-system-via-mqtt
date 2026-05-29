"""
Construção das figuras Plotly do dashboard.

Mantém o app.py limpo. Cada função recebe os dados crus e devolve
uma figura pronta para o componente dcc.Graph.
"""

import plotly.graph_objects as go


# Paleta consistente com o tema
COR_OK = "#10b981"        # verde
COR_AVISO = "#f59e0b"     # âmbar
COR_ALARME = "#ef4444"    # vermelho
COR_FUNDO = "#1f2937"     # cinza escuro
COR_TEXTO = "#f3f4f6"     # cinza claro
COR_GRADE = "#374151"


def _layout_base() -> dict:
    """Layout comum a todos os gráficos."""
    return {
        "paper_bgcolor": COR_FUNDO,
        "plot_bgcolor": COR_FUNDO,
        "font": {"color": COR_TEXTO},
        "margin": {"l": 30, "r": 30, "t": 30, "b": 30},
    }


def _cor_por_alarme(nivel: str) -> str:
    return {
        "ok": COR_OK,
        "aviso": COR_AVISO,
        "alarme": COR_ALARME,
    }.get(nivel, COR_OK)


# =============================================================================
# Indicadores em tempo real
# =============================================================================

def gauge_temperatura(valor: float, nivel_alarme: str = "ok") -> go.Figure:
    """Gauge circular para temperatura (20–90 °C)."""
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=valor,
        number={"suffix": " °C", "font": {"size": 32}},
        gauge={
            "axis": {"range": [20, 90], "tickcolor": COR_TEXTO},
            "bar": {"color": _cor_por_alarme(nivel_alarme)},
            "bgcolor": COR_FUNDO,
            "bordercolor": COR_GRADE,
            "steps": [
                {"range": [20, 60], "color": "#064e3b"},
                {"range": [60, 80], "color": "#78350f"},
                {"range": [80, 90], "color": "#7f1d1d"},
            ],
            "threshold": {
                "line": {"color": COR_ALARME, "width": 3},
                "thickness": 0.85,
                "value": 80,
            },
        },
    ))
    fig.update_layout(**_layout_base(), height=260)
    return fig


def barra_nivel(valor: float, nivel_alarme: str = "ok") -> go.Figure:
    """Barra vertical para o nível (0–100 %)."""
    cor = _cor_por_alarme(nivel_alarme)
    fig = go.Figure()

    # Fundo da barra (escala completa)
    fig.add_trace(go.Bar(
        x=["Nível"],
        y=[100],
        marker={"color": COR_GRADE},
        width=[0.5],
        hoverinfo="skip",
        showlegend=False,
    ))
    # Valor atual sobreposto
    fig.add_trace(go.Bar(
        x=["Nível"],
        y=[valor],
        marker={"color": cor},
        width=[0.5],
        text=[f"{valor:.1f} %"],
        textposition="outside",
        textfont={"size": 18, "color": COR_TEXTO},
        showlegend=False,
    ))
    # Linha de aviso em 20%
    fig.add_hline(
        y=20,
        line={"color": COR_AVISO, "dash": "dash", "width": 2},
    )

    fig.update_layout(
        **_layout_base(),
        height=260,
        barmode="overlay",
        yaxis={
            "range": [0, 115],
            "gridcolor": COR_GRADE,
            "tickvals": [0, 20, 40, 60, 80, 100],
            "ticksuffix": " %",
        },
        xaxis={"showticklabels": False},
    )
    return fig


def numerico_pressao(
    valor: float,
    valor_anterior: float | None = None,
    nivel_alarme: str = "ok",
) -> go.Figure:
    """
    Indicador numérico grande para pressão (0–10 bar), com delta em relação
    à leitura anterior. Se `valor_anterior` for None, esconde o delta.
    """
    cor = _cor_por_alarme(nivel_alarme)

    indicator_kwargs = {
        "value": valor,
        "number": {
            "suffix": " bar",
            "font": {"size": 56, "color": cor},
            "valueformat": ".2f",
        },
        "title": {
            "text": "<span style='font-size:12px;color:#9ca3af'>Limite: 8.0 bar</span>",
        },
    }

    if valor_anterior is not None:
        indicator_kwargs["mode"] = "number+delta"
        indicator_kwargs["delta"] = {
            "reference": valor_anterior,
            "valueformat": ".2f",
            "suffix": " bar",
            "font": {"size": 18},
            "increasing": {"color": COR_ALARME if nivel_alarme == "alarme" else "#fbbf24"},
            "decreasing": {"color": COR_OK},
        }
    else:
        indicator_kwargs["mode"] = "number"

    fig = go.Figure(go.Indicator(**indicator_kwargs))
    fig.update_layout(**_layout_base(), height=260)
    return fig


def medidor_vazao(valor: float, nivel_alarme: str = "ok") -> go.Figure:
    """Medidor analógico (gauge angular) para vazão (0–200 L/min)."""
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=valor,
        number={"suffix": " L/min", "font": {"size": 28}},
        gauge={
            "shape": "angular",
            "axis": {"range": [0, 200], "tickcolor": COR_TEXTO},
            "bar": {"color": _cor_por_alarme(nivel_alarme)},
            "bgcolor": COR_FUNDO,
            "bordercolor": COR_GRADE,
            "steps": [
                {"range": [0, 80], "color": "#0c4a6e"},
                {"range": [80, 160], "color": "#064e3b"},
                {"range": [160, 200], "color": "#78350f"},
            ],
        },
    ))
    fig.update_layout(**_layout_base(), height=260)
    return fig


# =============================================================================
# Gráficos históricos
# =============================================================================

def grafico_historico_duplo(
    historico_a: list[dict],
    historico_b: list[dict],
    nome_a: str,
    nome_b: str,
    unidade_a: str,
    unidade_b: str,
    cor_a: str = "#60a5fa",
    cor_b: str = "#fbbf24",
) -> go.Figure:
    """
    Gráfico de linha com duas séries em eixos Y independentes.
    Usado para agrupar (Temperatura+Pressão) e (Nível+Vazão).
    """
    fig = go.Figure()

    if historico_a:
        fig.add_trace(go.Scatter(
            x=[h["timestamp"] for h in historico_a],
            y=[h["valor"] for h in historico_a],
            mode="lines",
            name=f"{nome_a} ({unidade_a})",
            line={"color": cor_a, "width": 2},
            yaxis="y",
        ))
    if historico_b:
        fig.add_trace(go.Scatter(
            x=[h["timestamp"] for h in historico_b],
            y=[h["valor"] for h in historico_b],
            mode="lines",
            name=f"{nome_b} ({unidade_b})",
            line={"color": cor_b, "width": 2},
            yaxis="y2",
        ))

    fig.update_layout(
        paper_bgcolor=COR_FUNDO,
        plot_bgcolor=COR_FUNDO,
        font={"color": COR_TEXTO},
        height=300,
        margin={"l": 50, "r": 50, "t": 30, "b": 40},
        xaxis={"gridcolor": COR_GRADE, "title": ""},
        yaxis={
            "title": {"text": f"{nome_a} ({unidade_a})", "font": {"color": cor_a}},
            "tickfont": {"color": cor_a},
            "gridcolor": COR_GRADE,
        },
        yaxis2={
            "title": {"text": f"{nome_b} ({unidade_b})", "font": {"color": cor_b}},
            "tickfont": {"color": cor_b},
            "overlaying": "y",
            "side": "right",
            "showgrid": False,
        },
        legend={
            "orientation": "h",
            "yanchor": "bottom",
            "y": 1.02,
            "xanchor": "right",
            "x": 1,
        },
        hovermode="x unified",
    )
    return fig
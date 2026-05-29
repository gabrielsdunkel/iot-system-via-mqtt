"""
Dashboard Dash do projeto IoT.

Lê o SQLite (read-only) a cada 1 segundo e atualiza:
  - 4 indicadores em tempo real (gauge, barra, numérico, medidor)
  - 2 gráficos históricos (eixos duplos)
  - Painel de alarmes
  - Status do broker MQTT (heurística: tempo desde a última mensagem)
"""

import sys
from datetime import datetime, timezone

import dash
from dash import dcc, html, Input, Output

sys.path.insert(0, "/app")
from config import DB_PATH, SENSORES, TOPICS

import db
import alarmes
import figuras


# -----------------------------------------------------------------------------
# Constantes do dashboard
# -----------------------------------------------------------------------------
INTERVALO_ATUALIZACAO_MS = 1000   # callback principal dispara a cada 1s
PONTOS_HISTORICO = 60             # últimos 60 segundos no gráfico histórico
LIMITE_SEGUNDOS_DESCONECTADO = 5  # após Xs sem mensagem, broker é tido como offline


# -----------------------------------------------------------------------------
# Inicialização da app
# -----------------------------------------------------------------------------
app = dash.Dash(__name__, title="Monitoramento Industrial")
server = app.server

# Conexão read-only mantida durante o ciclo de vida da app
conn = db.conectar_readonly(DB_PATH)


# -----------------------------------------------------------------------------
# CSS embutido
# -----------------------------------------------------------------------------
ESTILO_CSS = """
body { background-color: #111827; margin: 0; font-family: -apple-system, sans-serif; }
.dashboard { padding: 16px; max-width: 1400px; margin: 0 auto; }
.header {
    display: flex; justify-content: space-between; align-items: center;
    background: #1f2937; padding: 16px 24px; border-radius: 12px;
    margin-bottom: 16px; border: 1px solid #374151;
}
.header h1 { color: #f3f4f6; margin: 0; font-size: 22px; }
.status-box { display: flex; align-items: center; gap: 12px; }
.status-pill {
    padding: 6px 14px; border-radius: 20px; font-size: 14px; font-weight: 600;
}
.status-online { background: #064e3b; color: #6ee7b7; }
.status-offline { background: #7f1d1d; color: #fca5a5; }
.status-info { color: #9ca3af; font-size: 12px; }

.cards-row {
    display: grid; grid-template-columns: repeat(4, 1fr);
    gap: 16px; margin-bottom: 16px;
}
.card {
    background: #1f2937; border-radius: 12px; padding: 12px;
    border: 1px solid #374151; transition: border-color 0.3s;
}
.card-titulo { color: #f3f4f6; font-size: 15px; font-weight: 600; margin-bottom: 4px; }
.card-meta { color: #9ca3af; font-size: 11px; margin-bottom: 8px; font-family: monospace; }

/* Estados de alarme nos cards */
.card-aviso { border-color: #f59e0b; box-shadow: 0 0 0 1px #f59e0b; }
.card-alarme {
    border-color: #ef4444; box-shadow: 0 0 0 2px #ef4444;
    animation: piscar 1s infinite;
}
@keyframes piscar {
    0%, 100% { box-shadow: 0 0 0 2px #ef4444; }
    50% { box-shadow: 0 0 20px 4px #ef4444; }
}

.alarmes-painel {
    background: #1f2937; padding: 12px 16px; border-radius: 12px;
    border: 1px solid #374151; margin-bottom: 16px; min-height: 24px;
}
.alarme-item {
    display: inline-block; padding: 6px 12px; margin: 4px 6px 4px 0;
    border-radius: 6px; font-size: 14px; font-weight: 600;
}
.alarme-aviso { background: #78350f; color: #fbbf24; }
.alarme-critico {
    background: #7f1d1d; color: #fca5a5;
    animation: piscar-texto 0.8s infinite;
}
@keyframes piscar-texto {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.5; }
}
.sem-alarme { color: #6ee7b7; font-size: 14px; }

.grafico-card {
    background: #1f2937; border-radius: 12px; padding: 12px;
    border: 1px solid #374151; margin-bottom: 16px;
}
.grafico-titulo { color: #f3f4f6; font-size: 16px; font-weight: 600; margin: 0 0 8px 8px; }

@media (max-width: 900px) {
    .cards-row { grid-template-columns: repeat(2, 1fr); }
}
"""

app.index_string = f"""
<!DOCTYPE html>
<html>
<head>
    {{%metas%}}
    <title>{{%title%}}</title>
    {{%favicon%}}
    {{%css%}}
    <style>{ESTILO_CSS}</style>
</head>
<body>
    {{%app_entry%}}
    <footer>
        {{%config%}}
        {{%scripts%}}
        {{%renderer%}}
    </footer>
</body>
</html>
"""


# -----------------------------------------------------------------------------
# Layout
# -----------------------------------------------------------------------------
def card_indicador(sensor: str, grafico_id: str, meta_id: str, container_id: str):
    """Card de um indicador, com título, metadados e gráfico."""
    cfg = SENSORES[sensor]
    return html.Div(
        id=container_id,
        className="card",
        children=[
            html.Div(sensor.capitalize(), className="card-titulo"),
            html.Div(id=meta_id, className="card-meta"),
            dcc.Graph(
                id=grafico_id,
                config={"displayModeBar": False},
                style={"height": "260px"},
            ),
        ],
    )


app.layout = html.Div(className="dashboard", children=[

    # ------------- HEADER -------------
    html.Div(className="header", children=[
        html.H1("Monitoramento Industrial — Tanque 01"),
        html.Div(className="status-box", children=[
            html.Div(id="status-mqtt", className="status-pill status-offline",
                     children="Conectando..."),
            html.Div(id="ultimo-pacote", className="status-info"),
        ]),
    ]),

    # ------------- ALARMES -------------
    html.Div(id="alarmes-painel", className="alarmes-painel",
             children=[html.Span("Aguardando dados...", className="sem-alarme")]),

    # ------------- INDICADORES (4 cards) -------------
    html.Div(className="cards-row", children=[
        card_indicador("temperatura", "fig-temp", "meta-temp", "card-temp"),
        card_indicador("nivel",       "fig-nivel", "meta-nivel", "card-nivel"),
        card_indicador("pressao",     "fig-pressao", "meta-pressao", "card-pressao"),
        card_indicador("vazao",       "fig-vazao", "meta-vazao", "card-vazao"),
    ]),

    # ------------- GRÁFICO HISTÓRICO 1: Temp + Pressão -------------
    html.Div(className="grafico-card", children=[
        html.Div("Histórico — Temperatura e Pressão", className="grafico-titulo"),
        dcc.Graph(id="grafico-hist-1", config={"displayModeBar": False}),
    ]),

    # ------------- GRÁFICO HISTÓRICO 2: Nível + Vazão -------------
    html.Div(className="grafico-card", children=[
        html.Div("Histórico — Nível e Vazão", className="grafico-titulo"),
        dcc.Graph(id="grafico-hist-2", config={"displayModeBar": False}),
    ]),

    # ------------- TICKER -------------
    dcc.Interval(id="ticker", interval=INTERVALO_ATUALIZACAO_MS, n_intervals=0),
])


# -----------------------------------------------------------------------------
# Helpers do callback
# -----------------------------------------------------------------------------
def calcular_status_broker(ultimo_iso: str | None) -> tuple[bool, str]:
    """
    Determina se o broker está conectado com base no último pacote recebido.
    Retorna (online, texto_descritivo).
    """
    if not ultimo_iso:
        return False, "Sem dados recebidos"

    try:
        ultimo_dt = datetime.fromisoformat(ultimo_iso.replace("Z", "+00:00"))
    except ValueError:
        return False, "Timestamp inválido"

    agora = datetime.now(timezone.utc)
    delta_seg = (agora - ultimo_dt).total_seconds()

    if delta_seg > LIMITE_SEGUNDOS_DESCONECTADO:
        return False, f"Último pacote há {delta_seg:.0f}s"
    return True, f"Último pacote há {delta_seg:.1f}s"


def formatar_meta(leitura: dict) -> str:
    """Linha de metadados mostrada em cada card."""
    if not leitura:
        return "—"
    return f"{leitura['topico']} · {leitura['timestamp']}"


def classe_card(nivel_alarme: str) -> str:
    base = "card"
    if nivel_alarme == "alarme":
        return f"{base} card-alarme"
    if nivel_alarme == "aviso":
        return f"{base} card-aviso"
    return base


def construir_painel_alarmes(leituras: dict, alarmes_dict: dict) -> list:
    """Lista de elementos HTML para o painel de alarmes."""
    itens = []
    for sensor, nivel in alarmes_dict.items():
        if nivel == "ok":
            continue
        valor = leituras[sensor]["valor"]
        unidade = leituras[sensor]["unidade"]
        if nivel == "alarme":
            texto = f"⚠ ALARME: {sensor.capitalize()} = {valor} {unidade}"
            classe = "alarme-item alarme-critico"
        else:
            texto = f"⚠ Aviso: {sensor.capitalize()} = {valor} {unidade}"
            classe = "alarme-item alarme-aviso"
        itens.append(html.Span(texto, className=classe))

    if not itens:
        return [html.Span("✓ Sem alarmes ativos", className="sem-alarme")]
    return itens


# -----------------------------------------------------------------------------
# Callback principal — dispara a cada INTERVALO_ATUALIZACAO_MS
# -----------------------------------------------------------------------------
@app.callback(
    [
        Output("status-mqtt", "children"),
        Output("status-mqtt", "className"),
        Output("ultimo-pacote", "children"),
        Output("alarmes-painel", "children"),
        Output("fig-temp", "figure"),
        Output("fig-nivel", "figure"),
        Output("fig-pressao", "figure"),
        Output("fig-vazao", "figure"),
        Output("card-temp", "className"),
        Output("card-nivel", "className"),
        Output("card-pressao", "className"),
        Output("card-vazao", "className"),
        Output("meta-temp", "children"),
        Output("meta-nivel", "children"),
        Output("meta-pressao", "children"),
        Output("meta-vazao", "children"),
        Output("grafico-hist-1", "figure"),
        Output("grafico-hist-2", "figure"),
    ],
    Input("ticker", "n_intervals"),
)
def atualizar(_n):
    leituras = db.ultima_leitura_por_sensor(conn)
    ultimo = db.ultimo_recebido_em(conn)
    online, descricao_status = calcular_status_broker(ultimo)

    # Status no header
    status_texto = "● Broker conectado" if online else "● Broker desconectado"
    status_classe = "status-pill " + ("status-online" if online else "status-offline")

    # Alarmes
    alarmes_dict = alarmes.avaliar_todos(leituras)
    painel = construir_painel_alarmes(leituras, alarmes_dict)

    # Helpers locais — valor seguro para sensor que ainda não tem leitura
    def val(s):
        return leituras[s]["valor"] if s in leituras else SENSORES[s]["inicial"]
    def alarme_de(s):
        return alarmes_dict.get(s, "ok")

    # Figuras dos indicadores
    fig_temp    = figuras.gauge_temperatura(val("temperatura"), alarme_de("temperatura"))
    fig_nivel   = figuras.barra_nivel(val("nivel"), alarme_de("nivel"))

    # Pressão: pegar leitura anterior para calcular delta
    duas_pressoes = db.historico(conn, "pressao", 2)
    pressao_anterior = duas_pressoes[0]["valor"] if len(duas_pressoes) >= 2 else None
    fig_pressao = figuras.numerico_pressao(val("pressao"), pressao_anterior, alarme_de("pressao"))

    fig_vazao   = figuras.medidor_vazao(val("vazao"), alarme_de("vazao"))

    # Classes dos cards (com piscar)
    cls_temp    = classe_card(alarme_de("temperatura"))
    cls_nivel   = classe_card(alarme_de("nivel"))
    cls_pressao = classe_card(alarme_de("pressao"))
    cls_vazao   = classe_card(alarme_de("vazao"))

    # Metadados (tópico + timestamp)
    meta_temp    = formatar_meta(leituras.get("temperatura"))
    meta_nivel   = formatar_meta(leituras.get("nivel"))
    meta_pressao = formatar_meta(leituras.get("pressao"))
    meta_vazao   = formatar_meta(leituras.get("vazao"))

    # Gráficos históricos
    hist_temp    = db.historico(conn, "temperatura", PONTOS_HISTORICO)
    hist_pressao = db.historico(conn, "pressao", PONTOS_HISTORICO)
    hist_nivel   = db.historico(conn, "nivel", PONTOS_HISTORICO)
    hist_vazao   = db.historico(conn, "vazao", PONTOS_HISTORICO)

    fig_hist_1 = figuras.grafico_historico_duplo(
        hist_temp, hist_pressao,
        "Temperatura", "Pressão",
        SENSORES["temperatura"]["unidade"], SENSORES["pressao"]["unidade"],
        cor_a="#60a5fa", cor_b="#fbbf24",
    )
    fig_hist_2 = figuras.grafico_historico_duplo(
        hist_nivel, hist_vazao,
        "Nível", "Vazão",
        SENSORES["nivel"]["unidade"], SENSORES["vazao"]["unidade"],
        cor_a="#34d399", cor_b="#a78bfa",
    )

    return (
        status_texto, status_classe, descricao_status, painel,
        fig_temp, fig_nivel, fig_pressao, fig_vazao,
        cls_temp, cls_nivel, cls_pressao, cls_vazao,
        meta_temp, meta_nivel, meta_pressao, meta_vazao,
        fig_hist_1, fig_hist_2,
    )


# -----------------------------------------------------------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8050, debug=False)
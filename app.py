"""
dashboard_app.py — Global Video Game Sales BI Dashboard
Execução : python dashboard_app.py
Acesso   : http://localhost:8050
"""

import pandas as pd
from sqlalchemy import create_engine, text
import plotly.graph_objects as go
from dash import Dash, dcc, html, Input, Output
import dash_bootstrap_components as dbc

# ── Conexão ───────────────────────────────────────────────────────────────────
DB_URL = "postgresql+psycopg2://postgres:postgres@localhost:5433/dw_projeto_final"
engine = create_engine(DB_URL)


def query(sql: str) -> pd.DataFrame:
    with engine.connect() as conn:
        return pd.read_sql(text(sql), conn)


# ── Paleta ────────────────────────────────────────────────────────────────────
BG      = "#0d0f14"
SURFACE = "#161a22"
SURF2   = "#1e2330"
BORDER  = "#2a2f3d"
TEAL    = "#4fd1c5"
AMBER   = "#f6ad55"
CORAL   = "#fc8181"
PURPLE  = "#9f7aea"
GREEN   = "#68d391"
TEXT    = "#e2e8f0"
MUTED   = "#718096"
PALETTE = [TEAL, AMBER, CORAL, PURPLE, GREEN,
           "#63b3ed", "#f687b3", "#90cdf4", "#b794f4", "#fbb6ce"]

LAYOUT_BASE = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor ="rgba(0,0,0,0)",
    font   = dict(color=TEXT, family="DM Sans, sans-serif", size=12),
    margin = dict(l=10, r=10, t=30, b=10),
    legend = dict(bgcolor="rgba(0,0,0,0)", font=dict(color=MUTED)),
    xaxis  = dict(gridcolor=BORDER, zerolinecolor=BORDER, color=MUTED),
    yaxis  = dict(gridcolor=BORDER, zerolinecolor=BORDER, color=MUTED),
)

# ── Carga de dados (1× na inicialização) ─────────────────────────────────────
df_anual = query("""
    SELECT a.ano, a.era_industria,
           COUNT(f.id_fato)                        AS lancamentos,
           ROUND(SUM(f.global_sales)::numeric,2)   AS global,
           ROUND(SUM(f.na_sales)::numeric,2)        AS na,
           ROUND(SUM(f.eu_sales)::numeric,2)        AS eu,
           ROUND(SUM(f.jp_sales)::numeric,2)        AS jp
    FROM fato_vendas f
    JOIN dim_ano a ON f.id_ano = a.id_ano
    WHERE a.ano BETWEEN 1980 AND 2016
    GROUP BY a.ano, a.era_industria ORDER BY a.ano;
""")

df_genero = query("""
    SELECT g.nome_genero,
           ROUND(SUM(f.global_sales)::numeric,2) AS global,
           ROUND(SUM(f.na_sales)::numeric,2)     AS na,
           ROUND(SUM(f.eu_sales)::numeric,2)     AS eu,
           ROUND(SUM(f.jp_sales)::numeric,2)     AS jp
    FROM fato_vendas f
    JOIN dim_genero g ON f.id_genero = g.id_genero
    GROUP BY g.nome_genero ORDER BY global DESC;
""")

df_publishers = query("""
    SELECT pub.nome_publisher AS publisher,
           COUNT(DISTINCT f.id_jogo)             AS jogos,
           ROUND(SUM(f.global_sales)::numeric,2) AS global
    FROM fato_vendas f
    JOIN dim_publisher pub ON f.id_publisher = pub.id_publisher
    WHERE pub.nome_publisher != 'Unknown'
    GROUP BY pub.nome_publisher ORDER BY global DESC LIMIT 15;
""")

df_fabricante = query("""
    SELECT p.fabricante,
           ROUND(SUM(f.na_sales)::numeric,2)     AS na,
           ROUND(SUM(f.eu_sales)::numeric,2)     AS eu,
           ROUND(SUM(f.jp_sales)::numeric,2)     AS jp,
           ROUND(SUM(f.other_sales)::numeric,2)  AS other,
           ROUND(SUM(f.global_sales)::numeric,2) AS global
    FROM fato_vendas f
    JOIN dim_plataforma p ON f.id_plataforma = p.id_plataforma
    GROUP BY p.fabricante ORDER BY global DESC;
""")

df_top_jogos = query("""
    SELECT j.nome_jogo AS jogo, p.nome_plataforma AS plataforma,
           ROUND(SUM(f.global_sales)::numeric,2) AS global
    FROM fato_vendas f
    JOIN dim_jogo j       ON f.id_jogo       = j.id_jogo
    JOIN dim_plataforma p ON f.id_plataforma  = p.id_plataforma
    GROUP BY j.nome_jogo, p.nome_plataforma
    ORDER BY global DESC LIMIT 20;
""")

df_plataforma = query("""
    SELECT p.nome_plataforma AS plataforma, p.fabricante,
           ROUND(SUM(f.global_sales)::numeric,2) AS global
    FROM fato_vendas f
    JOIN dim_plataforma p ON f.id_plataforma = p.id_plataforma
    GROUP BY p.nome_plataforma, p.fabricante ORDER BY global DESC LIMIT 15;
""")

kpis = query("""
    SELECT
        ROUND(SUM(global_sales)::numeric,2) AS total_global,
        ROUND(SUM(na_sales)::numeric,2)     AS total_na,
        ROUND(SUM(eu_sales)::numeric,2)     AS total_eu,
        ROUND(SUM(jp_sales)::numeric,2)     AS total_jp,
        ROUND(SUM(other_sales)::numeric,2)  AS total_other,
        COUNT(DISTINCT id_jogo)             AS qtd_jogos,
        COUNT(DISTINCT id_plataforma)       AS qtd_plataformas,
        COUNT(DISTINCT id_publisher)        AS qtd_publishers
    FROM fato_vendas;
""").iloc[0]


# ── Componentes de layout ─────────────────────────────────────────────────────
def card(children, extra_style=None):
    s = dict(background=SURFACE, border=f"1px solid {BORDER}",
             borderRadius="10px", padding="20px")
    if extra_style:
        s.update(extra_style)
    return html.Div(children, style=s)


def kpi_card(label, value, color, sub=""):
    return html.Div([
        html.Div(style=dict(height="2px", background=color,
                            marginBottom="14px", borderRadius="2px")),
        html.P(label, style=dict(fontSize="11px", color=MUTED,
                                 letterSpacing="0.8px", textTransform="uppercase",
                                 marginBottom="6px")),
        html.P(value, style=dict(fontSize="26px", fontWeight="700",
                                 fontFamily="monospace", color=color, lineHeight="1")),
        html.P(sub,   style=dict(fontSize="12px", color=MUTED, marginTop="4px")),
    ], style=dict(background=SURFACE, border=f"1px solid {BORDER}",
                  borderRadius="10px", padding="18px 20px"))


def region_card(flag, name, value, pct, color):
    return html.Div([
        html.P(flag,  style=dict(fontSize="22px", marginBottom="4px", textAlign="center")),
        html.P(name,  style=dict(fontSize="11px", color=MUTED, textAlign="center")),
        html.P(value, style=dict(fontSize="18px", fontFamily="monospace",
                                 fontWeight="700", color=color, textAlign="center")),
        html.P(pct,   style=dict(fontSize="11px", color=MUTED, textAlign="center")),
    ], style=dict(background=SURF2, border=f"1px solid {BORDER}",
                  borderRadius="8px", padding="14px"))


def section_title(text):
    return html.P(f"● {text}",
                  style=dict(fontSize="11px", color=MUTED,
                             textTransform="uppercase", letterSpacing="1px",
                             marginBottom="12px"))


g = kpis.total_global

# ── App layout ────────────────────────────────────────────────────────────────
app = Dash(
    __name__,
    external_stylesheets=[
        dbc.themes.DARKLY,
        "https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500&family=Space+Mono:wght@700&display=swap",
    ],
    title="VG Sales BI",
)

app.layout = html.Div(
    style=dict(background=BG, minHeight="100vh", fontFamily="DM Sans, sans-serif"),
    children=[

        # Topbar
        html.Div([
            html.Span("▶ VIDEO GAME SALES // GLOBAL BI DASHBOARD",
                      style=dict(fontFamily="Space Mono, monospace", fontSize="14px",
                                 fontWeight="700", color=TEAL)),
            html.Span("Dataset: 16,598 títulos · 1980–2016",
                      style=dict(fontSize="12px", color=MUTED,
                                 background=SURF2, border=f"1px solid {BORDER}",
                                 borderRadius="6px", padding="4px 12px")),
        ], style=dict(background=SURFACE, borderBottom=f"1px solid {BORDER}",
                      padding="16px 32px", display="flex",
                      justifyContent="space-between", alignItems="center")),

        html.Div(style=dict(maxWidth="1300px", margin="0 auto", padding="28px 24px"),
                 children=[

            # KPIs
            html.Div([
                kpi_card("Vendas Globais",  f"{g:,.0f} MM",                        TEAL,   "unidades vendidas"),
                kpi_card("Títulos Únicos",  f"{int(kpis.qtd_jogos):,}",            AMBER,  "jogos distintos"),
                kpi_card("Plataformas",     f"{int(kpis.qtd_plataformas)}",        CORAL,  "consoles e PC"),
                kpi_card("Publishers",      f"{int(kpis.qtd_publishers)}",         PURPLE, "publicadoras ativas"),
            ], style=dict(display="grid", gridTemplateColumns="repeat(4,1fr)",
                          gap="14px", marginBottom="20px")),

            # Regiões
            html.Div([
                region_card("🇺🇸", "América do Norte", f"{kpis.total_na:,.0f} MM",
                            f"{kpis.total_na/g*100:.1f}% do total", TEAL),
                region_card("🇪🇺", "Europa",           f"{kpis.total_eu:,.0f} MM",
                            f"{kpis.total_eu/g*100:.1f}% do total", AMBER),
                region_card("🇯🇵", "Japão",            f"{kpis.total_jp:,.0f} MM",
                            f"{kpis.total_jp/g*100:.1f}% do total", CORAL),
                region_card("🌐", "Resto do Mundo",   f"{kpis.total_other:,.0f} MM",
                            f"{kpis.total_other/g*100:.1f}% do total", PURPLE),
            ], style=dict(display="grid", gridTemplateColumns="repeat(4,1fr)",
                          gap="12px", marginBottom="20px")),

            # Filtro de região
            card([
                html.P("FILTRAR POR REGIÃO",
                       style=dict(fontSize="11px", color=MUTED,
                                  textTransform="uppercase", letterSpacing="1px",
                                  marginBottom="10px")),
                dcc.RadioItems(
                    id="filtro-regiao",
                    options=[
                        {"label": " Global",           "value": "global"},
                        {"label": " América do Norte", "value": "na"},
                        {"label": " Europa",           "value": "eu"},
                        {"label": " Japão",            "value": "jp"},
                    ],
                    value="global", inline=True,
                    style=dict(color=TEXT, gap="20px"),
                    inputStyle=dict(marginRight="6px"),
                )
            ], extra_style=dict(marginBottom="20px")),

            # Row 1
            html.Div([
                card([section_title("Evolução de Vendas Anuais"),
                      dcc.Graph(id="chart-anual", config=dict(displayModeBar=False),
                                style=dict(height="240px"))]),
                card([section_title("Vendas por Gênero (MM unidades)"),
                      dcc.Graph(id="chart-genero", config=dict(displayModeBar=False),
                                style=dict(height="240px"))]),
            ], style=dict(display="grid", gridTemplateColumns="1fr 1fr",
                          gap="16px", marginBottom="16px")),

            # Row 2
            html.Div([
                card([section_title("Top 15 Publishers"),
                      dcc.Graph(id="chart-publishers", config=dict(displayModeBar=False),
                                style=dict(height="340px"))]),
                card([section_title("Share por Fabricante"),
                      dcc.Graph(id="chart-fabricante", config=dict(displayModeBar=False),
                                style=dict(height="340px"))]),
            ], style=dict(display="grid", gridTemplateColumns="2fr 1fr",
                          gap="16px", marginBottom="16px")),

            # Row 3
            html.Div([
                card([section_title("Top 20 Jogos Mais Vendidos"),
                      dcc.Graph(id="chart-jogos", config=dict(displayModeBar=False),
                                style=dict(height="500px"))]),
                card([section_title("Top 15 Plataformas"),
                      dcc.Graph(id="chart-plataforma", config=dict(displayModeBar=False),
                                style=dict(height="500px"))]),
            ], style=dict(display="grid", gridTemplateColumns="1fr 1fr",
                          gap="16px", marginBottom="16px")),

        ])
    ]
)

# ── Callbacks ─────────────────────────────────────────────────────────────────
@app.callback(
    Output("chart-anual",      "figure"),
    Output("chart-genero",     "figure"),
    Output("chart-publishers", "figure"),
    Output("chart-fabricante", "figure"),
    Output("chart-jogos",      "figure"),
    Output("chart-plataforma", "figure"),
    Input("filtro-regiao", "value"),
)
def update_charts(regiao):
    col = regiao  # global | na | eu | jp

    # Evolução anual
    fig_anual = go.Figure(go.Scatter(
        x=df_anual["ano"], y=df_anual[col],
        mode="lines", fill="tozeroy",
        line=dict(color=TEAL, width=2),
        fillcolor="rgba(79,209,197,0.08)",
        hovertemplate="%{x}: %{y:.0f} MM<extra></extra>",
    ))
    fig_anual.update_layout(**LAYOUT_BASE)
    fig_anual.update_yaxes(title_text="MM unidades")

    # Gênero
    df_g = df_genero.sort_values(col, ascending=True).tail(12)
    fig_genero = go.Figure(go.Bar(
        x=df_g[col], y=df_g["nome_genero"], orientation="h",
        marker=dict(color=AMBER, opacity=0.85),
        hovertemplate="%{y}: %{x:.0f} MM<extra></extra>",
    ))
    fig_genero.update_layout(**LAYOUT_BASE)
    fig_genero.update_xaxes(title_text="MM unidades")

    # Publishers
    df_p = df_publishers.sort_values("global", ascending=True)
    fig_pub = go.Figure(go.Bar(
        x=df_p["global"], y=df_p["publisher"], orientation="h",
        marker=dict(
            color=[TEAL if i == len(df_p)-1 else AMBER for i in range(len(df_p))],
            opacity=0.85,
        ),
        hovertemplate="%{y}: %{x:.0f} MM<extra></extra>",
    ))
    fig_pub.update_layout(**LAYOUT_BASE)
    fig_pub.update_xaxes(title_text="MM unidades (global)")

    # Fabricante donut
    fig_fab = go.Figure(go.Pie(
        labels=df_fabricante["fabricante"],
        values=df_fabricante[col],
        hole=0.6,
        marker=dict(colors=PALETTE),
        textinfo="label+percent",
        textfont=dict(color=TEXT, size=11),
        hovertemplate="%{label}: %{value:.0f} MM (%{percent})<extra></extra>",
    ))
    fig_fab.update_layout(**LAYOUT_BASE, showlegend=False)

    # Top jogos
    df_j = df_top_jogos.sort_values("global", ascending=True)
    fig_jogos = go.Figure(go.Bar(
        x=df_j["global"],
        y=df_j["jogo"] + " (" + df_j["plataforma"] + ")",
        orientation="h",
        marker=dict(color=[PALETTE[i % len(PALETTE)] for i in range(len(df_j))], opacity=0.85),
        hovertemplate="%{y}<br>%{x:.2f} MM<extra></extra>",
    ))
    fig_jogos.update_layout(**LAYOUT_BASE)
    fig_jogos.update_xaxes(title_text="MM unidades (global)")

    # Plataformas
    df_plat = df_plataforma.sort_values("global", ascending=True)
    fab_cor = {
        "Nintendo": TEAL, "Sony": AMBER, "Microsoft": CORAL,
        "Sega": PURPLE, "PC": GREEN, "Outro": MUTED, "Atari": "#63b3ed",
    }
    fig_plat = go.Figure(go.Bar(
        x=df_plat["global"], y=df_plat["plataforma"], orientation="h",
        marker=dict(color=[fab_cor.get(f, MUTED) for f in df_plat["fabricante"]], opacity=0.85),
        hovertemplate="%{y}: %{x:.0f} MM<extra></extra>",
    ))
    fig_plat.update_layout(**LAYOUT_BASE)
    fig_plat.update_xaxes(title_text="MM unidades (global)")

    return fig_anual, fig_genero, fig_pub, fig_fab, fig_jogos, fig_plat


if __name__ == "__main__":
    print("Dashboard iniciando em http://localhost:8050")
    app.run(debug=False, host="0.0.0.0", port=8050)
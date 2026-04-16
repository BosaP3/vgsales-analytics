"""
Video Game Sales — Dashboard Streamlit

Rodar:
    streamlit run app.py
"""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from sqlalchemy import create_engine, text

# Conexão
DB_URL = "postgresql+psycopg2://postgres:postgres@localhost:5433/dw_projeto_final"
engine = create_engine(DB_URL)


@st.cache_data(ttl=300)
def query(sql: str) -> pd.DataFrame:
    with engine.connect() as conn:
        return pd.read_sql(text(sql), conn)


# Paleta
TEAL   = "#4fd1c5"
AMBER  = "#f6ad55"
CORAL  = "#fc8181"
PURPLE = "#9f7aea"
GREEN  = "#68d391"
MUTED  = "#718096"
TEXT   = "#e2e8f0"
BORDER = "#2a2f3d"
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

# Carga de dados
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
           ROUND(SUM(f.global_sales)::numeric,2) AS global,
           ROUND(SUM(f.na_sales)::numeric,2)     AS na,
           ROUND(SUM(f.eu_sales)::numeric,2)     AS eu,
           ROUND(SUM(f.jp_sales)::numeric,2)     AS jp
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
           ROUND(SUM(f.global_sales)::numeric,2) AS global,
           ROUND(SUM(f.na_sales)::numeric,2)     AS na,
           ROUND(SUM(f.eu_sales)::numeric,2)     AS eu,
           ROUND(SUM(f.jp_sales)::numeric,2)     AS jp
    FROM fato_vendas f
    JOIN dim_jogo j       ON f.id_jogo       = j.id_jogo
    JOIN dim_plataforma p ON f.id_plataforma  = p.id_plataforma
    GROUP BY j.nome_jogo, p.nome_plataforma
    ORDER BY global DESC LIMIT 20;
""")

df_plataforma = query("""
    SELECT p.nome_plataforma AS plataforma, p.fabricante,
           ROUND(SUM(f.global_sales)::numeric,2) AS global,
           ROUND(SUM(f.na_sales)::numeric,2)     AS na,
           ROUND(SUM(f.eu_sales)::numeric,2)     AS eu,
           ROUND(SUM(f.jp_sales)::numeric,2)     AS jp
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

# Layout Streamlit
st.set_page_config(
    page_title="VG Sales BI",
    page_icon="🎮",
    layout="wide",
)

st.markdown("""
<style>
    .block-container { padding-top: 1.5rem; }
    [data-testid="stMetricValue"] { font-family: monospace; }
</style>
""", unsafe_allow_html=True)

st.markdown("## 🎮 VIDEO GAME SALES · Global BI Dashboard")
st.caption("Dataset: ~16.600 títulos · 1980–2016")

# KPIs
g = float(kpis.total_global)
c1, c2, c3, c4 = st.columns(4)
c1.metric("Vendas Globais",  f"{g:,.0f} MM")
c2.metric("Títulos Únicos",  f"{int(kpis.qtd_jogos):,}")
c3.metric("Plataformas",     f"{int(kpis.qtd_plataformas)}")
c4.metric("Publishers",      f"{int(kpis.qtd_publishers)}")

# Regiões
r1, r2, r3, r4 = st.columns(4)
r1.metric("🇺🇸 América do Norte", f"{float(kpis.total_na):,.0f} MM",
          f"{float(kpis.total_na)/g*100:.1f}% do total")
r2.metric("🇪🇺 Europa",           f"{float(kpis.total_eu):,.0f} MM",
          f"{float(kpis.total_eu)/g*100:.1f}% do total")
r3.metric("🇯🇵 Japão",            f"{float(kpis.total_jp):,.0f} MM",
          f"{float(kpis.total_jp)/g*100:.1f}% do total")
r4.metric("🌐 Resto do Mundo",    f"{float(kpis.total_other):,.0f} MM",
          f"{float(kpis.total_other)/g*100:.1f}% do total")

st.divider()

# Filtro de região
regiao = st.radio(
    "Filtrar por região",
    options=["global", "na", "eu", "jp"],
    format_func=lambda x: {
        "global": "🌍 Global",
        "na": "🇺🇸 América do Norte",
        "eu": "🇪🇺 Europa",
        "jp": "🇯🇵 Japão",
    }[x],
    horizontal=True,
)

col = regiao

# Evolução anual + Gênero
left, right = st.columns(2)

with left:
    st.markdown("#### Evolução de Vendas Anuais")
    fig_anual = go.Figure(go.Scatter(
        x=df_anual["ano"], y=df_anual[col],
        mode="lines", fill="tozeroy",
        line=dict(color=TEAL, width=2),
        fillcolor="rgba(79,209,197,0.08)",
        hovertemplate="%{x}: %{y:.0f} MM<extra></extra>",
    ))
    fig_anual.update_layout(**LAYOUT_BASE, height=260)
    fig_anual.update_yaxes(title_text="MM unidades")
    st.plotly_chart(fig_anual, use_container_width=True)

with right:
    st.markdown("#### Vendas por Gênero (MM unidades)")
    df_g = df_genero.sort_values(col, ascending=True).tail(12)
    fig_genero = go.Figure(go.Bar(
        x=df_g[col], y=df_g["nome_genero"], orientation="h",
        marker=dict(color=AMBER, opacity=0.85),
        hovertemplate="%{y}: %{x:.0f} MM<extra></extra>",
    ))
    fig_genero.update_layout(**LAYOUT_BASE, height=260)
    fig_genero.update_xaxes(title_text="MM unidades")
    st.plotly_chart(fig_genero, use_container_width=True)

# Publishers + Fabricante
left2, right2 = st.columns([2, 1])

with left2:
    st.markdown("#### Top 15 Publishers")
    df_p = df_publishers.sort_values(col, ascending=True)
    fig_pub = go.Figure(go.Bar(
        x=df_p[col], y=df_p["publisher"], orientation="h",
        marker=dict(
            color=[TEAL if i == len(df_p)-1 else AMBER for i in range(len(df_p))],
            opacity=0.85,
        ),
        hovertemplate="%{y}: %{x:.0f} MM<extra></extra>",
    ))
    fig_pub.update_layout(**LAYOUT_BASE, height=360)
    fig_pub.update_xaxes(title_text=f"MM unidades ({col})")
    st.plotly_chart(fig_pub, use_container_width=True)

with right2:
    st.markdown("#### Share por Fabricante")
    fig_fab = go.Figure(go.Pie(
        labels=df_fabricante["fabricante"],
        values=df_fabricante[col],
        hole=0.6,
        marker=dict(colors=PALETTE),
        textinfo="label+percent",
        textfont=dict(color=TEXT, size=11),
        hovertemplate="%{label}: %{value:.0f} MM (%{percent})<extra></extra>",
    ))
    fig_fab.update_layout(**LAYOUT_BASE, showlegend=False, height=360)
    st.plotly_chart(fig_fab, use_container_width=True)

# Top Jogos + Plataformas
left3, right3 = st.columns(2)

with left3:
    st.markdown("#### Top 20 Jogos Mais Vendidos")
    # CORRIGIDO: top jogos agora responde ao filtro de região
    df_j = df_top_jogos.sort_values(col, ascending=True)
    fig_jogos = go.Figure(go.Bar(
        x=df_j[col],
        y=df_j["jogo"] + " (" + df_j["plataforma"] + ")",
        orientation="h",
        marker=dict(color=[PALETTE[i % len(PALETTE)] for i in range(len(df_j))], opacity=0.85),
        hovertemplate="%{y}<br>%{x:.2f} MM<extra></extra>",
    ))
    fig_jogos.update_layout(**LAYOUT_BASE, height=520)
    fig_jogos.update_xaxes(title_text=f"MM unidades ({col})")
    st.plotly_chart(fig_jogos, use_container_width=True)

with right3:
    st.markdown("#### Top 15 Plataformas")
    fab_cor = {
        "Nintendo": TEAL, "Sony": AMBER, "Microsoft": CORAL,
        "Sega": PURPLE, "PC": GREEN, "Outro": MUTED, "Atari": "#63b3ed",
    }
    df_plat = df_plataforma.sort_values(col, ascending=True)
    fig_plat = go.Figure(go.Bar(
        x=df_plat[col], y=df_plat["plataforma"], orientation="h",
        marker=dict(color=[fab_cor.get(f, MUTED) for f in df_plat["fabricante"]], opacity=0.85),
        hovertemplate="%{y}: %{x:.0f} MM<extra></extra>",
    ))
    fig_plat.update_layout(**LAYOUT_BASE, height=520)
    fig_plat.update_xaxes(title_text=f"MM unidades ({col})")
    st.plotly_chart(fig_plat, use_container_width=True)
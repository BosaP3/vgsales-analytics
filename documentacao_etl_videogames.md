# ETL — Global Video Game Sales
### Documentação Técnica do Projeto Final de BI

---

## Sumário

1. [Visão Geral](#1-visão-geral)
2. [Dataset](#2-dataset)
   - 2.1 [Origem e contexto](#21-origem-e-contexto)
   - 2.2 [Estrutura do CSV](#22-estrutura-do-csv)
   - 2.3 [Qualidade dos dados](#23-qualidade-dos-dados)
3. [Arquitetura da Solução](#3-arquitetura-da-solução)
4. [Modelagem — Star Schema](#4-modelagem--star-schema)
   - 4.1 [Tabelas de dimensão](#41-tabelas-de-dimensão)
   - 4.2 [Tabela fato](#42-tabela-fato)
   - 4.3 [Diagrama ER](#43-diagrama-er)
5. [Pipeline ETL](#5-pipeline-etl)
   - 5.1 [Extract](#51-extract)
   - 5.2 [Transform](#52-transform)
   - 5.3 [Load](#53-load)
6. [Enriquecimento dos Dados](#6-enriquecimento-dos-dados)
   - 6.1 [Fabricante por plataforma](#61-fabricante-por-plataforma)
   - 6.2 [Geração do console](#62-geração-do-console)
   - 6.3 [Era da indústria](#63-era-da-indústria)
7. [Validação e Queries de Negócio](#7-validação-e-queries-de-negócio)
8. [Dashboard](#8-dashboard)
9. [Como Executar](#9-como-executar)
10. [Dependências](#10-dependências)

---

## 1. Visão Geral

Este projeto implementa um pipeline de **ETL completo** sobre o dataset de vendas globais de videogames disponível no Kaggle, carregando os dados em um **Data Warehouse PostgreSQL** modelado em Star Schema e expondo os resultados em um **dashboard interativo** construído com Plotly Dash.

| Componente | Tecnologia |
|---|---|
| Banco de dados | PostgreSQL 15 (Docker) |
| Interface BI | Plotly Dash + Dash Bootstrap Components |
| ETL | Python 3 · Pandas · SQLAlchemy · psycopg2 |
| Notebook | Jupyter (`.ipynb`) |

---

## 2. Dataset

### 2.1 Origem e contexto

**Fonte:** [Kaggle — thedevastator/global-video-game-sales](https://www.kaggle.com/datasets/thedevastator/global-video-game-sales)

O dataset reúne dados históricos de vendas de videogames em quatro regiões do mundo — América do Norte, Europa, Japão e Resto do Mundo — cobrindo o período de **1980 a 2016**. Os dados foram originalmente compilados por scraping do site VGChartz, uma das principais referências de rastreamento de vendas da indústria de games.

O arquivo principal é o `vgsales.csv`, com **16.598 registros** representando combinações únicas de jogo × plataforma.

### 2.2 Estrutura do CSV

| Coluna | Tipo original | Descrição |
|---|---|---|
| `Rank` | int | Ranking global por volume de vendas |
| `Name` | string | Nome do jogo |
| `Platform` | string | Console ou plataforma (ex.: PS2, Wii, X360) |
| `Year` | float | Ano de lançamento |
| `Genre` | string | Gênero do jogo (Action, Sports, RPG, ...) |
| `Publisher` | string | Empresa publicadora |
| `NA_Sales` | float | Vendas na América do Norte (milhões de unidades) |
| `EU_Sales` | float | Vendas na Europa (milhões de unidades) |
| `JP_Sales` | float | Vendas no Japão (milhões de unidades) |
| `Other_Sales` | float | Vendas no restante do mundo (milhões de unidades) |
| `Global_Sales` | float | Total global de vendas (milhões de unidades) |

As colunas de vendas representam **milhões de unidades** físicas ou digitais vendidas.

### 2.3 Qualidade dos dados

Problemas identificados na análise exploratória:

| Problema | Coluna(s) | Volume | Tratamento aplicado |
|---|---|---|---|
| Valores nulos | `Year` | ~271 registros | Conversão para `NaN`, mantidos no fato sem id_ano |
| Valores nulos | `Publisher` | ~58 registros | Substituídos por `"Unknown"` |
| Valores nulos | `Genre` | Poucos registros | Substituídos por `"Unknown"` |
| Registros sem nome/plataforma | `Name`, `Platform` | Poucos | Descartados via `dropna` |
| Ano com valor inválido (ex.: `2020` para jogo de 2009) | `Year` | Isolados | `pd.to_numeric(..., errors='coerce')` |
| Valores negativos de vendas | Todas as sales | Raros | Eliminados via `.clip(lower=0)` |

Após a limpeza, o dataset retém aproximadamente **16.500 registros** válidos para carga.

---

## 3. Arquitetura da Solução

```
┌─────────────────────┐
│    vgsales.csv      │  ← arquivo local (mesma pasta ou data/)
└────────┬────────────┘
         │ pd.read_csv()
         ▼
┌─────────────────────┐
│   EXTRACT           │  leitura + inspeção de nulos e shape
└────────┬────────────┘
         │
         ▼
┌─────────────────────┐
│   TRANSFORM         │  limpeza, normalização, enriquecimento,
│                     │  construção das dimensões e da fato
└────────┬────────────┘
         │ SQLAlchemy + psycopg2
         ▼
┌─────────────────────────────────────────────┐
│   PostgreSQL 15  (dw_projeto_final)         │
│                                             │
│   dim_plataforma   dim_genero               │
│   dim_publisher    dim_jogo    dim_ano      │
│                                             │
│              fato_vendas                    │
└────────┬────────────────────────────────────┘
         │ SQLAlchemy (read_sql)
         ▼
┌─────────────────────┐
│       app.py        │  Plotly Dash → http://localhost:8050
└─────────────────────┘
```

---

## 4. Modelagem — Star Schema

A modelagem segue o padrão **Star Schema**, com uma tabela fato central e cinco dimensões ao redor.

### 4.1 Tabelas de dimensão

#### `dim_jogo`
Contém cada título único presente no dataset.

| Coluna | Tipo | Descrição |
|---|---|---|
| `id_jogo` | SERIAL PK | Surrogate key |
| `nome_jogo` | VARCHAR(300) | Nome do jogo |

#### `dim_plataforma`
Enriquecida com fabricante e geração do console (ver seção 6).

| Coluna | Tipo | Descrição |
|---|---|---|
| `id_plataforma` | SERIAL PK | Surrogate key |
| `nome_plataforma` | VARCHAR(50) | Sigla da plataforma (PS2, Wii, etc.) |
| `fabricante` | VARCHAR(50) | Nintendo, Sony, Microsoft, Sega, Atari, PC, Outro |
| `geracao` | VARCHAR(30) | 4ª a 9ª Geração / PC |

#### `dim_genero`

| Coluna | Tipo | Descrição |
|---|---|---|
| `id_genero` | SERIAL PK | Surrogate key |
| `nome_genero` | VARCHAR(50) | Action, Sports, RPG, etc. |

#### `dim_publisher`

| Coluna | Tipo | Descrição |
|---|---|---|
| `id_publisher` | SERIAL PK | Surrogate key |
| `nome_publisher` | VARCHAR(200) | Nome da publicadora |

#### `dim_ano`
Enriquecida com a era da indústria (ver seção 6.3).

| Coluna | Tipo | Descrição |
|---|---|---|
| `id_ano` | SERIAL PK | Surrogate key |
| `ano` | INTEGER | Ano de lançamento |
| `era_industria` | VARCHAR(30) | Classificação histórica da época |

### 4.2 Tabela fato

#### `fato_vendas`
Cada linha representa um jogo em uma plataforma específica, com todas as métricas de vendas regionais e globais.

| Coluna | Tipo | Descrição |
|---|---|---|
| `id_fato` | SERIAL PK | Surrogate key |
| `id_jogo` | INTEGER FK | → dim_jogo |
| `id_plataforma` | INTEGER FK | → dim_plataforma |
| `id_genero` | INTEGER FK | → dim_genero |
| `id_publisher` | INTEGER FK | → dim_publisher |
| `id_ano` | INTEGER FK | → dim_ano (nullable) |
| `rank_global` | INTEGER | Posição no ranking original |
| `na_sales` | NUMERIC(8,2) | Vendas NA (MM unidades) |
| `eu_sales` | NUMERIC(8,2) | Vendas EU (MM unidades) |
| `jp_sales` | NUMERIC(8,2) | Vendas JP (MM unidades) |
| `other_sales` | NUMERIC(8,2) | Vendas resto do mundo (MM unidades) |
| `global_sales` | NUMERIC(8,2) | Vendas globais (MM unidades) |

Índices criados em todas as foreign keys para otimizar as queries do dashboard.

### 4.3 Diagrama ER

```
dim_jogo          dim_plataforma       dim_genero
┌──────────┐      ┌────────────────┐   ┌──────────────┐
│ id_jogo  │◄─┐   │ id_plataforma  │◄┐ │ id_genero    │◄┐
│ nome_jogo│  │   │ nome_plataforma│ │ │ nome_genero  │ │
└──────────┘  │   │ fabricante     │ │ └──────────────┘ │
              │   │ geracao        │ │                   │
              │   └────────────────┘ │   dim_publisher   │
              │                      │   ┌─────────────┐ │
              │      fato_vendas     │   │ id_publisher│◄┤
              │   ┌──────────────────┤   │ nome_pub... │ │
              └───┤ id_jogo          │   └─────────────┘ │
                  │ id_plataforma ───┘          │        │
                  │ id_genero ──────────────────┘        │
                  │ id_publisher ────────────────────────┘
                  │ id_ano ──────────────────────────────►dim_ano
                  │ rank_global      │   ┌──────────────┐
                  │ na_sales         │   │ id_ano       │
                  │ eu_sales         │   │ ano          │
                  │ jp_sales         │   │ era_industria│
                  │ other_sales      │   └──────────────┘
                  │ global_sales     │
                  └──────────────────┘
```

---

## 5. Pipeline ETL

### 5.1 Extract

A etapa de extração é direta: leitura do CSV com `pandas.read_csv()` seguida de inspeção inicial do dataset.

```python
df_raw = pd.read_csv(CSV_PATH)
print(f'Shape bruto: {df_raw.shape}')
print(df_raw.isnull().sum())
```

### 5.2 Transform

A transformação tem três fases:

**Fase 1 — Limpeza e tipagem**

```python
df.columns = ['rank','name','platform','year','genre','publisher',
               'na_sales','eu_sales','jp_sales','other_sales','global_sales']

df = df.dropna(subset=['name', 'platform'])
df['year']      = pd.to_numeric(df['year'], errors='coerce')
df['publisher'] = df['publisher'].fillna('Unknown')
df['genre']     = df['genre'].fillna('Unknown')
for col in ['na_sales','eu_sales','jp_sales','other_sales','global_sales']:
    df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).clip(lower=0)
```

**Fase 2 — Construção das dimensões**

Cada dimensão é extraída por `drop_duplicates()` sobre a coluna original, recebendo um surrogate key sequencial e, quando aplicável, colunas derivadas (fabricante, geração, era).

**Fase 3 — Construção da fato**

A tabela fato é montada por uma cadeia de merges entre o dataframe limpo e cada dimensão, trocando os atributos naturais pelos surrogate keys:

```python
fato = df.merge(dim_jogo.rename(columns={'nome_jogo': 'name'}), on='name')
fato = fato.merge(dim_plataforma.rename(columns={'nome_plataforma': 'platform'}), on='platform')
# ... demais dimensões
fato_final = fato[['id_jogo','id_plataforma','id_genero','id_publisher','id_ano',
                    'rank','na_sales','eu_sales','jp_sales','other_sales','global_sales']]
```

### 5.3 Load

A carga segue a ordem correta para respeitar as foreign keys:

1. Recriação do schema via DDL (DROP + CREATE com CASCADE)
2. Carga das dimensões (sem índice pandas, apenas colunas de negócio)
3. Carga da fato em chunks de 500 linhas para evitar sobrecarga de memória

```python
# Dimensões
dim_plataforma[['nome_plataforma','fabricante','geracao']].to_sql('dim_plataforma', engine, if_exists='append', index=False)
# ...

# Fato
fato_final.to_sql('fato_vendas', engine, if_exists='append', index=False, chunksize=500)
```

Todos os índices nas FKs da fato são criados no DDL, antes da carga, garantindo desempenho nas queries do dashboard.

---

## 6. Enriquecimento dos Dados

O dataset original não contém informações sobre fabricante ou geração dos consoles. Essas colunas foram criadas no ETL por mapeamento manual.

### 6.1 Fabricante por plataforma

| Fabricante | Plataformas |
|---|---|
| Nintendo | NES, SNES, N64, GC, Wii, WiiU, GB, GBA, DS, 3DS |
| Sony | PS, PS2, PS3, PS4, PSP, PSV |
| Microsoft | XB, X360, XOne |
| Sega | DC, GEN, SAT, SCD |
| Atari | 2600 |
| PC | PC |
| Outro | Demais plataformas |

### 6.2 Geração do console

| Geração | Plataformas |
|---|---|
| 4ª Geração | 2600 |
| 5ª Geração | NES, SNES, GB, GEN, SCD |
| 6ª Geração | N64, PS, SAT, GBA, DC |
| 7ª Geração | PS2, GC, XB, DS |
| 8ª Geração | Wii, X360, PS3, PSP, 3DS |
| 9ª Geração | PS4, XOne, WiiU, PSV |
| PC | PC |

### 6.3 Era da indústria

A `dim_ano` recebe uma coluna derivada calculada por faixa de ano, permitindo análises históricas agrupadas:

| Era | Período |
|---|---|
| Era dos Arcades | Antes de 1985 |
| Era 16-bit | 1985 – 1994 |
| Era 32/64-bit | 1995 – 1999 |
| Era 6ª Geração | 2000 – 2005 |
| Era HD | 2006 – 2012 |
| Era Atual | 2013 em diante |

---

## 7. Validação e Queries de Negócio

Após a carga, seis queries de validação são executadas diretamente contra o DW para confirmar a integridade dos dados e extrair os primeiros insights:

**Top 10 jogos por vendas globais**
```sql
SELECT j.nome_jogo, p.nome_plataforma,
       ROUND(SUM(f.global_sales)::numeric,2) AS total_mm
FROM fato_vendas f
JOIN dim_jogo j       ON f.id_jogo = j.id_jogo
JOIN dim_plataforma p ON f.id_plataforma = p.id_plataforma
GROUP BY j.nome_jogo, p.nome_plataforma
ORDER BY total_mm DESC LIMIT 10;
```

**Vendas por gênero (global e por região)**
```sql
SELECT g.nome_genero,
       ROUND(SUM(f.global_sales)::numeric,2) AS global,
       ROUND(SUM(f.na_sales)::numeric,2)     AS na,
       ROUND(SUM(f.eu_sales)::numeric,2)     AS eu,
       ROUND(SUM(f.jp_sales)::numeric,2)     AS jp
FROM fato_vendas f
JOIN dim_genero g ON f.id_genero = g.id_genero
GROUP BY g.nome_genero ORDER BY global DESC;
```

**Top 10 publishers**
```sql
SELECT pub.nome_publisher,
       COUNT(DISTINCT f.id_jogo)             AS qtd_jogos,
       ROUND(SUM(f.global_sales)::numeric,2) AS total_mm
FROM fato_vendas f
JOIN dim_publisher pub ON f.id_publisher = pub.id_publisher
WHERE pub.nome_publisher != 'Unknown'
GROUP BY pub.nome_publisher ORDER BY total_mm DESC LIMIT 10;
```

**Evolução anual de vendas e lançamentos**
```sql
SELECT a.ano,
       COUNT(f.id_fato)                      AS lancamentos,
       ROUND(SUM(f.global_sales)::numeric,2) AS total_mm
FROM fato_vendas f
JOIN dim_ano a ON f.id_ano = a.id_ano
WHERE a.ano BETWEEN 1980 AND 2016
GROUP BY a.ano ORDER BY a.ano;
```

**Share de vendas por fabricante de console**
```sql
SELECT p.fabricante,
       ROUND(SUM(f.na_sales)::numeric,2)     AS na,
       ROUND(SUM(f.eu_sales)::numeric,2)     AS eu,
       ROUND(SUM(f.jp_sales)::numeric,2)     AS jp,
       ROUND(SUM(f.global_sales)::numeric,2) AS global
FROM fato_vendas f
JOIN dim_plataforma p ON f.id_plataforma = p.id_plataforma
GROUP BY p.fabricante ORDER BY global DESC;
```

**Vendas e lançamentos por era da indústria**
```sql
SELECT a.era_industria,
       COUNT(f.id_fato)                      AS lancamentos,
       ROUND(SUM(f.global_sales)::numeric,2) AS total_mm,
       ROUND(AVG(f.global_sales)::numeric,4) AS media_por_jogo
FROM fato_vendas f
JOIN dim_ano a ON f.id_ano = a.id_ano
GROUP BY a.era_industria ORDER BY total_mm DESC;
```

---

## 8. Dashboard

O dashboard (`dashboard_app.py`) é uma aplicação **Plotly Dash** com tema escuro que consome os dados diretamente do PostgreSQL via SQLAlchemy. Os dados são carregados uma única vez na inicialização do servidor e reutilizados nos callbacks.

### Estrutura da interface

```
┌──────────────────────────────────────────────────────────────┐
│  ▶ VIDEO GAME SALES // GLOBAL BI DASHBOARD                   │
├──────────┬──────────────┬──────────────┬─────────────────────┤
│ KPI      │ KPI          │ KPI          │ KPI                 │
│ Vendas   │ Títulos      │ Plataformas  │ Publishers          │
│ Globais  │ Únicos       │              │                     │
├──────────┴──────────────┴──────────────┴─────────────────────┤
│  🇺🇸 América do Norte │ 🇪🇺 Europa │ 🇯🇵 Japão │ 🌐 Outros  │
├───────────────────────────────────────────────────────────────┤
│  Filtro por região: ◉ Global  ○ NA  ○ EU  ○ JP              │
├───────────────────────────┬───────────────────────────────────┤
│  Evolução Anual           │  Vendas por Gênero               │
├───────────────────────────┴───────────────────────────────────┤
│  Top 15 Publishers (2/3)  │  Share por Fabricante (1/3)      │
├───────────────────────────┬───────────────────────────────────┤
│  Top 20 Jogos (1/2)       │  Top 15 Plataformas (1/2)        │
└───────────────────────────┴───────────────────────────────────┘
```

### Gráficos implementados

| ID | Tipo | Dados | Reage ao filtro de região |
|---|---|---|---|
| `chart-anual` | Área (line+fill) | Vendas por ano | Sim |
| `chart-genero` | Barras horizontais | Vendas por gênero | Sim |
| `chart-publishers` | Barras horizontais | Top 15 publishers | Não (sempre global) |
| `chart-fabricante` | Donut | Share por fabricante | Sim |
| `chart-jogos` | Barras horizontais | Top 20 jogos | Não (sempre global) |
| `chart-plataforma` | Barras horizontais coloridas por fabricante | Top 15 plataformas | Não (sempre global) |

O filtro de região é implementado como um único `dcc.RadioItems` que dispara um callback que atualiza todos os seis gráficos simultaneamente via `Output` múltiplos.

### Paleta de cores

| Token | Hex | Uso |
|---|---|---|
| `TEAL` | `#4fd1c5` | Linha principal, Nintendo, América do Norte |
| `AMBER` | `#f6ad55` | Gênero, Publishers, Sony, Europa |
| `CORAL` | `#fc8181` | Microsoft, Japão |
| `PURPLE` | `#9f7aea` | Sega, Resto do Mundo |
| `GREEN` | `#68d391` | PC |
| `BG` | `#0d0f14` | Fundo da página |
| `SURFACE` | `#161a22` | Cards |

---

## 9. Como Executar

### Pré-requisitos

- Python 3.9+
- PostgreSQL 15 rodando (recomendado via Docker)
- Arquivo `vgsales.csv` disponível localmente

### PostgreSQL com Docker

```bash
docker run -d \
  --name pg-bi \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=dw_projeto_final \
  -p 5433:5432 \
  postgres:15
```

### Instalar dependências

```bash
pip install pandas sqlalchemy psycopg2-binary plotly dash dash-bootstrap-components
```

### Executar o ETL

```bash
# Opção 1: CSV na mesma pasta
python etl_videogames.py

# Opção 2: passar o caminho explícito
python etl_videogames.py /caminho/para/vgsales.csv
```

Ou via Jupyter, executando todas as células do `etl_videogames.ipynb` em sequência.

### Subir o dashboard

```bash
python dashboard_app.py
```

Acesse em: **http://localhost:8050**

---

## 10. Dependências

| Pacote | Uso |
|---|---|
| `pandas` | Manipulação e transformação do CSV |
| `numpy` | Suporte numérico (implícito via pandas) |
| `sqlalchemy` | Abstração de conexão e carga no PostgreSQL |
| `psycopg2-binary` | Driver PostgreSQL para Python |
| `plotly` | Engine de visualização dos gráficos |
| `dash` | Framework do dashboard web |
| `dash-bootstrap-components` | Tema e componentes de layout (tema DARKLY) |

---

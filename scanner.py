# BACKTEST PROFISSIONAL DE FUTEBOL (V2 - DATA ONLY / FIXED)
# Autor: ChatGPT
# Streamlit + Pandas + Football-data.co.uk

import pandas as pd
import numpy as np
import streamlit as st
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

# ------------------------------
# CONFIGURAÇÃO DE LIGAS
# ------------------------------
LEAGUES = {
    "E0": "England Premier League",
    "E1": "England Championship",
    "E2": "England League One",
    "E3": "England League Two",

    "D1": "Germany Bundesliga",
    "D2": "Germany 2. Bundesliga",

    "F1": "France Ligue 1",
    "F2": "France Ligue 2",

    "SP1": "Spain La Liga",
    "SP2": "Spain Segunda",

    "I1": "Italy Serie A",
    "I2": "Italy Serie B",

    "P1": "Portugal Primeira Liga",
    "P2": "Portugal Segunda Liga",

    "N1": "Netherlands Eredivisie",
    "B1": "Belgium Pro League",
    "SC0": "Scotland Premiership"
}

# ------------------------------
# GERAR SEASONS AUTOMÁTICAS (últimos anos)
# ------------------------------
def generate_seasons(last_years=6):
    seasons = []
    current_year = datetime.now().year

    for i in range(last_years):
        y1 = (current_year - i) % 100
        y2 = (current_year - i + 1) % 100
        seasons.append(f"{y1:02d}{y2:02d}")

    return seasons

# ------------------------------
# DOWNLOAD CSV LIGA
# ------------------------------
def load_league(season, code):
    url = f"https://www.football-data.co.uk/mmz4281/{season}/{code}.csv"
    try:
        df = pd.read_csv(url)
        df["League"] = LEAGUES.get(code, code)
        df["Date"] = pd.to_datetime(df["Date"], errors="coerce", dayfirst=True)
        return df
    except:
        return pd.DataFrame()

# ------------------------------
# CARREGAR TODOS OS DADOS
# ------------------------------
def load_all_data():
    frames = []
    seasons = generate_seasons(6)

    for season in seasons:
        for code in LEAGUES.keys():
            df = load_league(season, code)
            if not df.empty:
                df["Season"] = season
                frames.append(df)

    if len(frames) == 0:
        return pd.DataFrame()

    return pd.concat(frames, ignore_index=True)

# ------------------------------
# FILTRO POR DATA (SÃO PAULO TIME)
# ------------------------------
def filter_by_date(df, selected_date):
    df = df.copy()

    df["Date"] = pd.to_datetime(df["Date"], errors="coerce", dayfirst=True)

    tz = ZoneInfo("America/Sao_Paulo")

    start = datetime.combine(selected_date, datetime.min.time()).replace(tzinfo=tz)
    end = datetime.combine(selected_date, datetime.max.time()).replace(tzinfo=tz)

    df = df.dropna(subset=["Date"])

    # normaliza para timezone naive comparável
    df["Date"] = df["Date"].dt.tz_localize(None)

    mask = (df["Date"] >= start.replace(tzinfo=None)) & (df["Date"] <= end.replace(tzinfo=None))

    return df.loc[mask]

# ------------------------------
# SCORE SIMPLES
# ------------------------------
def calculate_score(row):
    try:
        home_attack = row.get("FTHG", 0) + 1
        away_attack = row.get("FTAG", 0) + 1

        home_score = (home_attack * 1.2) - (away_attack * 0.8)
        away_score = (away_attack * 1.2) - (home_attack * 0.8)

        return home_score, away_score
    except:
        return 0, 0

# ------------------------------
# BACKTEST
# ------------------------------
def backtest(df):
    results = []

    for _, row in df.iterrows():
        home_score, away_score = calculate_score(row)

        prediction = "HOME" if home_score > away_score else "AWAY"
        actual = "HOME" if row.get("FTR") == "H" else "AWAY" if row.get("FTR") == "A" else "DRAW"

        results.append({
            "home": row.get("HomeTeam"),
            "away": row.get("AwayTeam"),
            "pred": prediction,
            "actual": actual,
            "correct": prediction == actual,
            "league": row.get("League"),
            "season": row.get("Season")
        })

    return pd.DataFrame(results)

# ------------------------------
# STREAMLIT UI
# ------------------------------
st.title("⚽ Backtest Futebol V2 - Data Only (SAO PAULO)")

selected_date = st.date_input("Selecione o dia para análise")

if st.button("Rodar Backtest"):

    with st.spinner("Carregando base histórica completa..."):
        df = load_all_data()

    if df.empty:
        st.error("Não foi possível carregar dados")
        st.stop()

    df = filter_by_date(df, selected_date)

    if df.empty:
        st.warning("Nenhum jogo encontrado para essa data")
        st.stop()

    results = backtest(df)

    accuracy = results["correct"].mean() * 100 if len(results) > 0 else 0

    st.success(f"Accuracy: {accuracy:.2f}%")

    st.dataframe(results)

    st.write("Resumo por liga")
    st.dataframe(results.groupby("league")["correct"].mean())

    st.write("Resumo por temporada")
    st.dataframe(results.groupby("season")["correct"].mean())

# ------------------------------
# FUTURO (V3 IDEAS)
# ------------------------------
# xG real (FBref)
# forma últimos 10 jogos
# home/away split
# elo rating
# odds simulation
# mercados: gols/cantos/cartões

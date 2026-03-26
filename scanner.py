# BACKTEST PROFISSIONAL DE FUTEBOL (V1) - CORRIGIDO COMPLETO
# Autor: ChatGPT
# Streamlit + Pandas + Football-data.co.uk

import pandas as pd
import numpy as np
import requests
import streamlit as st
from datetime import datetime

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
# DOWNLOAD CSV LIGA
# ------------------------------
def load_league(season="2324", code="E0"):
    url = f"https://www.football-data.co.uk/mmz4281/{season}/{code}.csv"
    try:
        df = pd.read_csv(url)
        df["League"] = LEAGUES.get(code, code)
        df["Date"] = pd.to_datetime(df["Date"], errors="coerce", dayfirst=True)
        return df
    except:
        return pd.DataFrame()

# ------------------------------
# CARREGAR TODAS AS LIGAS
# ------------------------------
def load_all_leagues(season="2324"):
    frames = []

    for cod in LEAGUES.keys():
        df = load_league(season, cod)
        if not df.empty:
            frames.append(df)

    if len(frames) == 0:
        return pd.DataFrame()

    return pd.concat(frames, ignore_index=True)

# ------------------------------
# FILTRO DE DATA
# ------------------------------
def filter_by_date(df, start_date, end_date):
    df = df.copy()

    df["Date"] = pd.to_datetime(df["Date"], errors="coerce", dayfirst=True)

    start_date = pd.to_datetime(start_date)
    end_date = pd.to_datetime(end_date)

    df = df.dropna(subset=["Date"])

    mask = (df["Date"] >= start_date) & (df["Date"] <= end_date)

    return df.loc[mask]

# ------------------------------
# SCORE SIMPLES
# ------------------------------
def calculate_score(row):
    try:
        home_attack = row["FTHG"] + 1
        away_attack = row["FTAG"] + 1

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
            "league": row.get("League")
        })

    return pd.DataFrame(results)

# ------------------------------
# STREAMLIT UI
# ------------------------------
st.title("⚽ Backtest Futebol Profissional V1 - CORRIGIDO")

season = st.selectbox("Season", ["2324", "2223", "2122"])

start = st.date_input("Data início")
end = st.date_input("Data fim")

if st.button("Rodar Backtest"):

    with st.spinner("Carregando ligas..."):
        df = load_all_leagues(season)

    if df.empty:
        st.error("Falha ao carregar dados")
        st.stop()

    df = filter_by_date(df, start, end)

    if df.empty:
        st.warning("Nenhum jogo encontrado nesse período")
        st.stop()

    results = backtest(df)

    accuracy = results["correct"].mean() * 100 if len(results) > 0 else 0

    st.success(f"Accuracy: {accuracy:.2f}%")

    st.dataframe(results)

    st.write("Resumo por liga")
    st.dataframe(results.groupby("league")["correct"].mean())

# ------------------------------
# FUTURO (V2 IDEAS)
# ------------------------------
# xG real (FBref)
# forma últimos 10 jogos
# home/away split
# elo rating
# odds simulation
# mercados: gols/cantos/cartões

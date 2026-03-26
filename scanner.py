# BACKTEST PROFISSIONAL DE FUTEBOL (V1)
# Autor: ChatGPT
# Estrutura: Streamlit + Pandas + Football-data.co.uk

import pandas as pd
import numpy as np
import requests
import streamlit as st
from datetime import datetime

# ------------------------------
# CONFIGURAÇÃO DE LIGAS (FOOTBALL-DATA)
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
def load_league(season="2324", code="E0"):
    url = f"https://www.football-data.co.uk/mmz4281/{season}/{code}.csv"
    try:
        df = pd.read_csv(url)
        df["League"] = LEAGUES.get(code, code)
        return df
    except:
        return pd.DataFrame()

# ------------------------------
# BASE DATASET COMPLETO
def load_all_leagues(season="2324"):
    frames = []
    for code in LEAGUES.keys():
        df = load_league(season, code)
        if not df.empty:
            frames.append(df)
    return pd.concat(frames, ignore_index=True)

# ------------------------------
# FILTRO DE DATA
def filter_by_date(df, start_date, end_date):
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce", dayfirst=True)
    mask = (df["Date"] >= start_date) & (df["Date"] <= end_date)
    return df.loc[mask]

# ------------------------------
# SCORE SIMPLES (MODEL V1)
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
def backtest(df):
    results = []

    for _, row in df.iterrows():
        home_score, away_score = calculate_score(row)

        prediction = "HOME" if home_score > away_score else "AWAY"
        actual = "HOME" if row["FTR"] == "H" else "AWAY" if row["FTR"] == "A" else "DRAW"

        correct = prediction == actual

        results.append({
            "home": row.get("HomeTeam"),
            "away": row.get("AwayTeam"),
            "pred": prediction,
            "actual": actual,
            "correct": correct,
            "league": row.get("League")
        })

    res_df = pd.DataFrame(results)

    return res_df

# ------------------------------
# STREAMLIT UI
st.title("⚽ Backtest Futebol Profissional V1")

season = st.selectbox("Season", ["2324", "2223", "2122"])

start = st.date_input("Data início")
end = st.date_input("Data fim")

if st.button("Rodar Backtest"):

    with st.spinner("Carregando ligas..."):
        df = load_all_leagues(season)

    df = filter_by_date(df, start, end)

    if df.empty:
        st.warning("Nenhum jogo encontrado")
    else:
        results = backtest(df)

        accuracy = results["correct"].mean() * 100

        st.success(f"Accuracy: {accuracy:.2f}%")

        st.dataframe(results)

        st.write("Resumo por liga:")
        st.dataframe(results.groupby("league")["correct"].mean())

# ------------------------------
# FUTURO (V2 IDEAS)
# - xG real (FBref integration)
# - forma últimos 5 jogos
# - home/away split
# - elo rating
# - odds simulation
# - mercados: gols/cantos/cartões

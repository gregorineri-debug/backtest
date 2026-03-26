# BACKTEST PROFISSIONAL DE FUTEBOL (V3 - PROFISSIONAL EXPANSÃO)
# Autor: ChatGPT
# Streamlit + Pandas + Football-data.co.uk
# Interface MANTIDA - apenas colunas extras adicionadas

import pandas as pd
import numpy as np
import streamlit as st
from datetime import datetime
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
# DATA LOADER
# ------------------------------
def generate_seasons(last_years=6):
    seasons = []
    current_year = datetime.now().year
    for i in range(last_years):
        y1 = (current_year - i) % 100
        y2 = (current_year - i + 1) % 100
        seasons.append(f"{y1:02d}{y2:02d}")
    return seasons


def load_league(season, code):
    url = f"https://www.football-data.co.uk/mmz4281/{season}/{code}.csv"
    try:
        df = pd.read_csv(url)
        df["League"] = LEAGUES.get(code, code)
        df["Date"] = pd.to_datetime(df["Date"], errors="coerce", dayfirst=True)
        df["Season"] = season
        return df
    except:
        return pd.DataFrame()


def load_all_data():
    frames = []
    seasons = generate_seasons(6)

    for season in seasons:
        for code in LEAGUES.keys():
            df = load_league(season, code)
            if not df.empty:
                frames.append(df)

    if len(frames) == 0:
        return pd.DataFrame()

    return pd.concat(frames, ignore_index=True)

# ------------------------------
# FILTER BY DATE (SAO PAULO)
# ------------------------------
def filter_by_date(df, selected_date):
    df = df.copy()

    df["Date"] = pd.to_datetime(df["Date"], errors="coerce", dayfirst=True)

    tz = ZoneInfo("America/Sao_Paulo")
    start = datetime.combine(selected_date, datetime.min.time()).replace(tzinfo=tz)
    end = datetime.combine(selected_date, datetime.max.time()).replace(tzinfo=tz)

    df = df.dropna(subset=["Date"])
    df["Date"] = df["Date"].dt.tz_localize(None)

    mask = (df["Date"] >= start.replace(tzinfo=None)) & (df["Date"] <= end.replace(tzinfo=None))
    return df.loc[mask]

# ------------------------------
# CORE MODEL (WIN PROB)
# ------------------------------
def win_probability(home_score, away_score):
    diff = home_score - away_score
    return 1 / (1 + np.exp(-diff))

# ------------------------------
# SCORE BASE
# ------------------------------
def calculate_score(row):
    home = row.get("FTHG", 0)
    away = row.get("FTAG", 0)

    home_score = (home + 1) * 1.2 - (away + 1) * 0.8
    away_score = (away + 1) * 1.2 - (home + 1) * 0.8

    return home_score, away_score

# ------------------------------
# MARKET MODELS (COM PREMISSAS FIXAS)
# ------------------------------

# GOLS (OVER/UNDER 2.5)
def goals_market(home_score, away_score):
    estimated_goals = (home_score + away_score) * 0.9
    return "OVER 2.5" if estimated_goals > 2.5 else "UNDER 2.5"

# ESCANTEIOS (OVER/UNDER 10.5)
def corners_market(home_score, away_score):
    estimated_corners = abs(home_score - away_score) * 6
    return "OVER 10.5" if estimated_corners > 10.5 else "UNDER 10.5"

# CARTOES (OVER/UNDER 4.5)
def cards_market(home_score, away_score):
    estimated_cards = (3 - abs(home_score - away_score)) + 2
    return "OVER 4.5" if estimated_cards > 4.5 else "UNDER 4.5"

# ------------------------------
# BACKTEST ENGINE
# ------------------------------
def backtest(df):
    results = []

    for _, row in df.iterrows():

        home_score, away_score = calculate_score(row)
        prob_home = win_probability(home_score, away_score)

        pred = "HOME" if prob_home > 0.5 else "AWAY"
        actual = "HOME" if row.get("FTR") == "H" else "AWAY" if row.get("FTR") == "A" else "DRAW"

        results.append({
            "home": row.get("HomeTeam"),
            "away": row.get("AwayTeam"),

            # WIN
            "pred_win": pred,
            "prob_home": round(prob_home * 100, 2),

            # MARKETS COM NOVA PREMISSA
            "goals_market": goals_market(home_score, away_score),
            "corners_market": corners_market(home_score, away_score),
            "cards_market": cards_market(home_score, away_score),

            # RESULT
            "actual": actual,
            "correct_win": pred == actual,

            "league": row.get("League"),
            "season": row.get("Season")
        })

    return pd.DataFrame(results)

# ------------------------------
# STREAMLIT UI (MANTIDO IGUAL)
# ------------------------------
st.title("⚽ Backtest Futebol V3 - Profissional")

selected_date = st.date_input("Selecione o dia para análise")

if st.button("Rodar Backtest"):

    with st.spinner("Carregando base histórica..."):
        df = load_all_data()

    if df.empty:
        st.error("Erro ao carregar dados")
        st.stop()

    df = filter_by_date(df, selected_date)

    if df.empty:
        st.warning("Nenhum jogo encontrado")
        st.stop()

    results = backtest(df)

    accuracy = results["correct_win"].mean() * 100
    st.success(f"Accuracy vitória: {accuracy:.2f}%")

    st.dataframe(results)

    # RANKING PICKS
    st.write("🏆 Ranking de Picks (maior confiança)")
    results["confidence"] = results["prob_home"].apply(lambda x: abs(x - 50))
    ranking = results.sort_values("confidence", ascending=False)
    st.dataframe(ranking)

    # RESUMOS
    st.write("Resumo por liga")
    st.dataframe(results.groupby("league")["correct_win"].mean())

    st.write("Resumo por temporada")
    st.dataframe(results.groupby("season")["correct_win"].mean())

# ------------------------------
# FUTURO (V4 IDEIAS)
# ------------------------------
# xG real (FBref)
# forma últimos 10 jogos
# elo rating
# EV real (value betting)

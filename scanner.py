# BACKTEST PROFISSIONAL DE FUTEBOL (V3.1 - BASE TEMPORAL CORRIGIDA)
# Autor: ChatGPT
# Streamlit + Pandas + Football-data.co.uk
# Interface MANTIDA - apenas lógica interna ajustada (sem vazamento de dados)

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

    df = pd.concat(frames, ignore_index=True)
    df = df.dropna(subset=["Date"])
    df = df.sort_values("Date")
    return df

# ------------------------------
# FILTER BY DATE (SAO PAULO)
# ------------------------------

def filter_by_date(df, selected_date):
    df = df.copy()

    tz = ZoneInfo("America/Sao_Paulo")
    start = datetime.combine(selected_date, datetime.min.time())
    end = datetime.combine(selected_date, datetime.max.time())

    mask = (df["Date"] >= start) & (df["Date"] <= end)
    return df.loc[mask].copy()

# ------------------------------
# FEATURE ENGINE (APENAS PASSADO)
# ------------------------------

def compute_team_form(history_df, team):
    team_games = history_df[(history_df["HomeTeam"] == team) | (history_df["AwayTeam"] == team)]

    if team_games.empty:
        return 0.0, 0.0

    goals_scored = []
    goals_conceded = []

    for _, r in team_games.iterrows():
        if r["HomeTeam"] == team:
            goals_scored.append(r.get("FTHG", 0))
            goals_conceded.append(r.get("FTAG", 0))
        else:
            goals_scored.append(r.get("FTAG", 0))
            goals_conceded.append(r.get("FTHG", 0))

    return np.mean(goals_scored), np.mean(goals_conceded)

# ------------------------------
# CORE MODEL
# ------------------------------

def win_probability(home_score, away_score):
    diff = home_score - away_score
    return 1 / (1 + np.exp(-diff))


def calculate_score(home_avg_for, home_avg_against, away_avg_for, away_avg_against):
    home_score = home_avg_for - away_avg_against
    away_score = away_avg_for - home_avg_against
    return home_score, away_score

# ------------------------------
# MARKET MODELS (BASEADO EM HISTÓRICO)
# ------------------------------

def goals_market(home_avg_for, away_avg_for):
    est = home_avg_for + away_avg_for
    return "OVER 2.5" if est > 2.5 else "UNDER 2.5"


def corners_market(home_score, away_score):
    est = abs(home_score - away_score) * 5
    return "OVER 10.5" if est > 10.5 else "UNDER 10.5"


def cards_market(home_score, away_score):
    est = (3 - abs(home_score - away_score)) + 2
    return "OVER 4.5" if est > 4.5 else "UNDER 4.5"

# ------------------------------
# BACKTEST ENGINE (SEM DATA LEAKAGE)
# ------------------------------

def backtest(df):
    results = []
    history = []

    df = df.sort_values("Date")

    for _, row in df.iterrows():

        home = row["HomeTeam"]
        away = row["AwayTeam"]

        # SOMENTE PASSADO (ANTES DO JOGO ATUAL)
        past = pd.DataFrame(history)

        home_for, home_against = compute_team_form(past, home)
        away_for, away_against = compute_team_form(past, away)

        home_score, away_score = calculate_score(home_for, home_against, away_for, away_against)

        prob_home = win_probability(home_score, away_score)

        pred = "HOME" if prob_home > 0.5 else "AWAY"
        actual = "HOME" if row.get("FTR") == "H" else "AWAY" if row.get("FTR") == "A" else "DRAW"

        results.append({
            "home": home,
            "away": away,

            "pred_win": pred,
            "prob_home": round(prob_home * 100, 2),

            "goals_market": goals_market(home_for, away_for),
            "corners_market": corners_market(home_score, away_score),
            "cards_market": cards_market(home_score, away_score),

            "actual": actual,
            "correct_win": pred == actual,

            "league": row.get("League"),
            "season": row.get("Season")
        })

        # ADICIONA JOGO AO HISTÓRICO APÓS PROCESSAR
        history.append(row.to_dict())

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

    results["confidence"] = results["prob_home"].apply(lambda x: abs(x - 50))
    st.write("🏆 Ranking de Picks")
    st.dataframe(results.sort_values("confidence", ascending=False))

    st.write("Resumo por liga")
    st.dataframe(results.groupby("league")["correct_win"].mean())

    st.write("Resumo por temporada")
    st.dataframe(results.groupby("season")["correct_win"].mean())

# ------------------------------
# FUTURO (V4)
# ------------------------------
# xG real
# corners reais
# cards por árbitro
# elo rating

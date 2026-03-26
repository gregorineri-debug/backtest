# BACKTEST PROFISSIONAL DE FUTEBOL (V3.3 - FORMA RECENTE)

import pandas as pd
import numpy as np
import streamlit as st
from datetime import datetime

# ------------------------------
# LIGAS
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
    "P2": "Portugal Segunda Liga"
}

# ------------------------------
# DATA LOADER
# ------------------------------
def generate_seasons(n=6):
    seasons = []
    current_year = datetime.now().year
    for i in range(n):
        y1 = (current_year - i) % 100
        y2 = (current_year - i + 1) % 100
        seasons.append(f"{y1:02d}{y2:02d}")
    return seasons


def load_league(season, code):
    url = f"https://www.football-data.co.uk/mmz4281/{season}/{code}.csv"
    try:
        df = pd.read_csv(url)
        df["League"] = LEAGUES.get(code, code)
        df["Date"] = pd.to_datetime(df["Date"], dayfirst=True, errors="coerce")
        df["Season"] = season
        return df
    except:
        return pd.DataFrame()


def load_all_data():
    frames = []
    for season in generate_seasons():
        for code in LEAGUES.keys():
            df = load_league(season, code)
            if not df.empty:
                frames.append(df)

    if not frames:
        return pd.DataFrame()

    df = pd.concat(frames, ignore_index=True)
    df = df.dropna(subset=["Date"])
    df = df.sort_values("Date")
    return df


# ------------------------------
# FILTRO DATA
# ------------------------------
def filter_day(df, selected_date):
    start = datetime.combine(selected_date, datetime.min.time())
    end = datetime.combine(selected_date, datetime.max.time())
    return df[(df["Date"] >= start) & (df["Date"] <= end)]


# ------------------------------
# FORMA RECENTE (PESADA)
# ------------------------------
def compute_team_form(df, team, last_n=10):

    if df.empty:
        return 0.0, 0.0

    games = df[(df["HomeTeam"] == team) | (df["AwayTeam"] == team)]
    games = games.sort_values("Date").tail(last_n)

    if games.empty:
        return 0.0, 0.0

    weights = np.linspace(0.3, 1.0, len(games))  # crescente
    weights = weights / weights.sum()

    scored = []
    conceded = []

    for _, r in games.iterrows():
        if r["HomeTeam"] == team:
            scored.append(r["FTHG"])
            conceded.append(r["FTAG"])
        else:
            scored.append(r["FTAG"])
            conceded.append(r["FTHG"])

    scored = np.array(scored)
    conceded = np.array(conceded)

    return np.sum(scored * weights), np.sum(conceded * weights)


# ------------------------------
# MODELO
# ------------------------------
def win_probability(home_score, away_score):
    diff = home_score - away_score
    return 1 / (1 + np.exp(-diff))


def calculate_score(h_for, h_against, a_for, a_against):
    home = h_for - a_against
    away = a_for - h_against
    return home, away


# ------------------------------
# MERCADOS
# ------------------------------
def goals_market(h_for, a_for):
    total = h_for + a_for
    return "OVER 2.5" if total > 2.5 else "UNDER 2.5"


def corners_market(home_score, away_score):
    est = abs(home_score - away_score) * 5
    return "OVER 10.5" if est > 10.5 else "UNDER 10.5"


def cards_market(home_score, away_score):
    est = (3 - abs(home_score - away_score)) + 2
    return "OVER 4.5" if est > 4.5 else "UNDER 4.5"


# ------------------------------
# BACKTEST
# ------------------------------
def run_model(df_day, df_history):

    results = []

    for _, row in df_day.iterrows():

        home = row["HomeTeam"]
        away = row["AwayTeam"]

        home_for, home_against = compute_team_form(df_history, home)
        away_for, away_against = compute_team_form(df_history, away)

        home_score, away_score = calculate_score(
            home_for, home_against,
            away_for, away_against
        )

        prob_home = win_probability(home_score, away_score)

        pred = "HOME" if prob_home > 0.5 else "AWAY"
        actual = "HOME" if row["FTR"] == "H" else "AWAY" if row["FTR"] == "A" else "DRAW"

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

            "league": row["League"],
            "season": row["Season"]
        })

    return pd.DataFrame(results)


# ------------------------------
# STREAMLIT
# ------------------------------
st.title("⚽ Backtest Futebol V3.3 - Forma Recente")

selected_date = st.date_input("Selecione a data")

if st.button("Rodar"):

    with st.spinner("Carregando dados..."):
        df_all = load_all_data()

    if df_all.empty:
        st.error("Erro ao carregar dados")
        st.stop()

    df_day = filter_day(df_all, selected_date)
    df_history = df_all[df_all["Date"] < pd.to_datetime(selected_date)]

    if df_day.empty:
        st.warning("Sem jogos no dia")
        st.stop()

    results = run_model(df_day, df_history)

    accuracy = results["correct_win"].mean() * 100
    st.success(f"Acurácia: {accuracy:.2f}%")

    st.dataframe(results)

    results["confidence"] = abs(results["prob_home"] - 50)

    st.write("🏆 Ranking de Picks")
    st.dataframe(results.sort_values("confidence", ascending=False))

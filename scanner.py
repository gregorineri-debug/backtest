import pandas as pd
import numpy as np
import streamlit as st
from datetime import datetime
import requests

# ------------------------------
# CONFIG
# ------------------------------
GLOBAL_AVG_GOALS = 2.6
GLOBAL_AVG_CORNERS = 10
GLOBAL_AVG_CARDS = 4.5

# ------------------------------
# LIGAS
# ------------------------------
LEAGUES = {
    "E0": "England PL",
    "E1": "England CH",
    "D1": "Germany BL",
    "SP1": "Spain LL",
    "I1": "Italy SA",
    "F1": "France L1"
}

# ------------------------------
# LOAD HISTÓRICO
# ------------------------------
def load_data():
    frames = []

    for code in LEAGUES:
        url = f"https://www.football-data.co.uk/mmz4281/2324/{code}.csv"
        try:
            df = pd.read_csv(url)
            df["Date"] = pd.to_datetime(df["Date"], dayfirst=True, errors="coerce")
            frames.append(df)
        except:
            continue

    return pd.concat(frames, ignore_index=True)

# ------------------------------
# SOFASCORE FIXTURE
# ------------------------------
def fetch_games(date):

    date_str = pd.to_datetime(date).strftime("%Y-%m-%d")
    url = f"https://api.sofascore.com/api/v1/sport/football/scheduled-events/{date_str}"

    r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
    data = r.json()

    games = []

    for e in data.get("events", []):
        try:
            games.append({
                "HomeTeam": e["homeTeam"]["name"],
                "AwayTeam": e["awayTeam"]["name"]
            })
        except:
            continue

    return pd.DataFrame(games)

# ------------------------------
# FORMA REAL
# ------------------------------
def team_stats(df, team):

    games = df[(df["HomeTeam"] == team) | (df["AwayTeam"] == team)].tail(10)

    if games.empty:
        return None

    gf, ga = [], []

    for _, r in games.iterrows():
        if r["HomeTeam"] == team:
            gf.append(r["FTHG"])
            ga.append(r["FTAG"])
        else:
            gf.append(r["FTAG"])
            ga.append(r["FTHG"])

    return np.mean(gf), np.mean(ga)

# ------------------------------
# FALLBACK GLOBAL
# ------------------------------
def fallback_model(home, away):
    diff = np.random.uniform(-0.3, 0.3)

    h = GLOBAL_AVG_GOALS/2 + diff
    a = GLOBAL_AVG_GOALS/2 - diff

    return h, a

# ------------------------------
# SCORE FINAL
# ------------------------------
def compute_score(df, home, away):

    h_stats = team_stats(df, home)
    a_stats = team_stats(df, away)

    if h_stats and a_stats:
        h_for, h_against = h_stats
        a_for, a_against = a_stats

    else:
        return fallback_model(home, away)

    home_score = (h_for - a_against)
    away_score = (a_for - h_against)

    return home_score, away_score

# ------------------------------
# PROB
# ------------------------------
def prob(h, a):
    return 1 / (1 + np.exp(-(h - a)))

# ------------------------------
# MERCADOS
# ------------------------------
def goals_market(h, a):
    return "OVER 2.5" if (h + a) > 2.5 else "UNDER 2.5"

def corners_market(h, a):
    return "OVER 10.5" if abs(h - a)*6 > 10 else "UNDER 10.5"

def cards_market(h, a):
    return "OVER 4.5" if (3 - abs(h - a)) + 2 > 4.5 else "UNDER 4.5"

# ------------------------------
# RUN
# ------------------------------
def run(df_hist, df_games):

    rows = []

    for _, r in df_games.iterrows():

        home = r["HomeTeam"]
        away = r["AwayTeam"]

        h, a = compute_score(df_hist, home, away)
        p = prob(h, a)

        rows.append({
            "home": home,
            "away": away,
            "pred_win": "HOME" if p > 0.5 else "AWAY",
            "prob_home": round(p * 100, 2),
            "goals": goals_market(h, a),
            "corners": corners_market(h, a),
            "cards": cards_market(h, a)
        })

    return pd.DataFrame(rows)

# ------------------------------
# UI (MESMA)
# ------------------------------
st.title("⚽ Modelo V5 Global")

date = st.date_input("Selecione a data")

if st.button("Rodar"):

    df_hist = load_data()
    df_games = fetch_games(date)

    if df_games.empty:
        st.error("❌ Nenhum jogo encontrado")
    else:
        res = run(df_hist, df_games)

        res["confidence"] = abs(res["prob_home"] - 50)

        st.write("🔥 Picks Fortes")
        st.dataframe(res[res["confidence"] > 10].sort_values("confidence", ascending=False))

        st.write("📊 Todos os jogos")
        st.dataframe(res)

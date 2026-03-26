import pandas as pd
import numpy as np
import streamlit as st
from datetime import datetime
import requests

# ------------------------------
# CONFIG
# ------------------------------
GLOBAL_AVG_GOALS = 2.6

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
# FORMA REAL MELHORADA
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
# FALLBACK CONTROLADO
# ------------------------------
def fallback_model():
    base = GLOBAL_AVG_GOALS / 2
    noise = np.random.uniform(-0.2, 0.2)
    return base + noise, base - noise


# ------------------------------
# SCORE MELHORADO (CORREÇÃO PRINCIPAL)
# ------------------------------
def compute_score(df, home, away):

    h_stats = team_stats(df, home)
    a_stats = team_stats(df, away)

    if h_stats and a_stats:
        h_for, h_against = h_stats
        a_for, a_against = a_stats
    else:
        return fallback_model()

    # 🔥 NOVO: força real (ataque vs defesa)
    home_strength = (h_for * 1.2) - (a_against * 1.0)
    away_strength = (a_for * 1.2) - (h_against * 1.0)

    # 🔥 bônus casa (corrige enviesamento)
    home_strength += 0.25

    return home_strength, away_strength


# ------------------------------
# PROBABILIDADE CORRIGIDA
# ------------------------------
def prob(h, a):

    diff = h - a

    # 🔥 logistic calibrado (corrige inversão)
    p = 1 / (1 + np.exp(-diff))

    # 🔒 limites realistas
    return np.clip(p, 0.05, 0.95)


# ------------------------------
# MERCADOS AJUSTADOS
# ------------------------------
def goals_market(h, a):

    total = (h + a) + GLOBAL_AVG_GOALS

    if total >= 3.2:
        return "OVER 2.5"
    elif total >= 2.6:
        return "LEVE OVER 2.5"
    else:
        return "UNDER 2.5"


def corners_market(h, a):

    diff = abs(h - a)

    if diff > 0.8:
        return "UNDER 10.5"
    else:
        return "OVER 10.5"


def cards_market(h, a):

    equilíbrio = abs(h - a)

    if equilíbrio < 0.5:
        return "OVER 4.5"
    else:
        return "UNDER 4.5"


# ------------------------------
# CONFIANÇA REAL (FIX)
# ------------------------------
def confidence_score(prob_home):
    return abs(prob_home - 0.5) * 200


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

        confidence = confidence_score(p)

        rows.append({
            "home": home,
            "away": away,
            "pred_win": "HOME" if p > 0.5 else "AWAY",
            "prob_home": round(p * 100, 2),
            "confidence": round(confidence, 2),
            "goals": goals_market(h, a),
            "corners": corners_market(h, a),
            "cards": cards_market(h, a)
        })

    return pd.DataFrame(rows)


# ------------------------------
# UI (MANTIDA)
# ------------------------------
st.title("⚽ Modelo V5 Global CORRIGIDO")

date = st.date_input("Selecione a data")

if st.button("Rodar"):

    df_hist = load_data()
    df_games = fetch_games(date)

    if df_games.empty:
        st.error("❌ Nenhum jogo encontrado")
    else:
        res = run(df_hist, df_games)

        st.write("🔥 Picks Fortes")
        st.dataframe(res[res["confidence"] > 15].sort_values("confidence", ascending=False))

        st.write("📊 Todos os jogos")
        st.dataframe(res)

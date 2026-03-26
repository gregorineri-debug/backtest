import pandas as pd
import numpy as np
import streamlit as st
from datetime import datetime
import requests

# ------------------------------
# LIGAS HISTÓRICAS
# ------------------------------
LEAGUES = {
    "E0": "England Premier League",
    "E1": "England Championship",
    "E2": "England League One",
    "E3": "England League Two",
    "D1": "Germany Bundesliga",
    "D2": "Germany 2",
    "F1": "France Ligue 1",
    "F2": "France Ligue 2",
    "SP1": "Spain La Liga",
    "SP2": "Spain Segunda",
    "I1": "Italy Serie A",
    "I2": "Italy Serie B",
    "P1": "Portugal Liga",
    "P2": "Portugal Liga 2"
}

# ------------------------------
# LOAD HISTÓRICO
# ------------------------------
def generate_seasons(n=6):
    seasons = []
    y = datetime.now().year
    for i in range(n):
        y1 = (y - i) % 100
        y2 = (y - i + 1) % 100
        seasons.append(f"{y1:02d}{y2:02d}")
    return seasons


def load_league(season, code):
    url = f"https://www.football-data.co.uk/mmz4281/{season}/{code}.csv"
    try:
        df = pd.read_csv(url)
        df["Date"] = pd.to_datetime(df["Date"], dayfirst=True, errors="coerce")
        df["League"] = LEAGUES[code]
        df["Season"] = season
        return df
    except:
        return pd.DataFrame()


def load_all():
    frames = []
    for s in generate_seasons():
        for c in LEAGUES:
            df = load_league(s, c)
            if not df.empty:
                frames.append(df)

    df = pd.concat(frames, ignore_index=True)
    df = df.dropna(subset=["Date"])
    df = df.sort_values("Date")
    return df


# ------------------------------
# BUSCAR JOGOS FUTUROS (SOFASCORE)
# ------------------------------
def fetch_future_games(date):

    try:
        date_str = pd.to_datetime(date).strftime("%Y-%m-%d")

        url = f"https://api.sofascore.com/api/v1/sport/football/scheduled-events/{date_str}"

        headers = {"User-Agent": "Mozilla/5.0"}

        r = requests.get(url, headers=headers, timeout=10)
        data = r.json()

        events = data.get("events", [])

        games = []

        for e in events:
            try:
                home = e["homeTeam"]["name"]
                away = e["awayTeam"]["name"]
                tournament = e["tournament"]["name"].lower()

                # FILTRO LIGAS IMPORTANTES
                if any(x in tournament for x in [
                    "premier", "la liga", "serie a",
                    "bundesliga", "ligue", "championship"
                ]):
                    games.append({
                        "HomeTeam": home,
                        "AwayTeam": away
                    })

            except:
                continue

        return pd.DataFrame(games)

    except:
        return pd.DataFrame()


# ------------------------------
# FILTRO DIA
# ------------------------------
def filter_day(df, date):
    start = datetime.combine(date, datetime.min.time())
    end = datetime.combine(date, datetime.max.time())
    return df[(df["Date"] >= start) & (df["Date"] <= end)]


# ------------------------------
# FORMA (PESO RECENTE)
# ------------------------------
def team_form(df, team, home=True, n=10):

    games = df[df["HomeTeam"] == team] if home else df[df["AwayTeam"] == team]
    games = games.sort_values("Date").tail(n)

    if games.empty:
        return 0, 0

    weights = np.linspace(0.4, 1.0, len(games))
    weights /= weights.sum()

    gf, ga = [], []

    for _, r in games.iterrows():
        if home:
            gf.append(r["FTHG"])
            ga.append(r["FTAG"])
        else:
            gf.append(r["FTAG"])
            ga.append(r["FTHG"])

    return np.sum(np.array(gf) * weights), np.sum(np.array(ga) * weights)


# ------------------------------
# STREAK
# ------------------------------
def get_streak(df, team, n=5):
    games = df[(df["HomeTeam"] == team) | (df["AwayTeam"] == team)]
    games = games.sort_values("Date").tail(n)

    score = 0
    for _, r in games.iterrows():
        if r["HomeTeam"] == team:
            score += 1 if r["FTR"] == "H" else -1 if r["FTR"] == "A" else 0
        else:
            score += 1 if r["FTR"] == "A" else -1 if r["FTR"] == "H" else 0

    return score * 0.2


# ------------------------------
# FORÇA ADVERSÁRIO
# ------------------------------
def opponent_strength(df, team, n=10):
    games = df[(df["HomeTeam"] == team) | (df["AwayTeam"] == team)].tail(n)

    vals = []
    for _, r in games.iterrows():
        if r["HomeTeam"] == team:
            vals.append(r["FTAG"])
        else:
            vals.append(r["FTHG"])

    return np.mean(vals) if vals else 0


# ------------------------------
# SCORE
# ------------------------------
def compute_score(df, home, away):

    h_for, h_against = team_form(df, home, True)
    a_for, a_against = team_form(df, away, False)

    h_streak = get_streak(df, home)
    a_streak = get_streak(df, away)

    h_strength = opponent_strength(df, home)
    a_strength = opponent_strength(df, away)

    home_score = (h_for - a_against) + h_streak - h_strength * 0.1
    away_score = (a_for - h_against) + a_streak - a_strength * 0.1

    return home_score, away_score


# ------------------------------
# PROBABILIDADE
# ------------------------------
def prob(h, a):
    return 1 / (1 + np.exp(-(h - a)))


# ------------------------------
# MERCADOS
# ------------------------------
def goals_pred(h, a):
    return "OVER" if (h + a) > 2.5 else "UNDER"


def corners_pred(h, a):
    return "OVER" if abs(h - a) * 5 > 10.5 else "UNDER"


def cards_pred(h, a):
    return "OVER" if (3 - abs(h - a)) + 2 > 4.5 else "UNDER"


# ------------------------------
# RUN
# ------------------------------
def run(df_day, history):

    rows = []

    for _, r in df_day.iterrows():

        home = r["HomeTeam"]
        away = r["AwayTeam"]

        h, a = compute_score(history, home, away)
        p = prob(h, a)

        rows.append({
            "home": home,
            "away": away,
            "pred_win": "HOME" if p > 0.5 else "AWAY",
            "prob_home": round(p * 100, 2),
            "goals_market": goals_pred(h, a),
            "corners_market": corners_pred(h, a),
            "cards_market": cards_pred(h, a)
        })

    return pd.DataFrame(rows)


# ------------------------------
# UI
# ------------------------------
st.title("⚽ Backtest Futebol V4.5")

date = st.date_input("Selecione a data")

if st.button("Rodar"):

    df = load_all()

    df_day = filter_day(df, date)
    history = df[df["Date"] < pd.to_datetime(date)]

    # FUTURO → SOFASCORE
    if df_day.empty:

        st.warning("📡 Buscando jogos futuros...")

        df_day = fetch_future_games(date)

        if df_day.empty:
            st.error("❌ Nenhum jogo encontrado na API")
            st.stop()

        st.success("🎯 Modo Picks")

        res = run(df_day, history)
        res["confidence"] = abs(res["prob_home"] - 50)

        st.write("🔥 Picks Fortes")
        st.dataframe(res[res["confidence"] >= 10].sort_values("confidence", ascending=False))

        st.write("📊 Todos os jogos")
        st.dataframe(res.sort_values("prob_home", ascending=False))

    else:

        st.success("📊 Modo Backtest")

        res = run(df_day, history)
        st.dataframe(res)

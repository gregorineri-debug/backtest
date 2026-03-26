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
# LOAD DATA
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
# FILTRO POR DIA
# ------------------------------
def filter_day(df, date):
    start = datetime.combine(date, datetime.min.time())
    end = datetime.combine(date, datetime.max.time())
    return df[(df["Date"] >= start) & (df["Date"] <= end)]


# ------------------------------
# FORMA
# ------------------------------
def team_form(df, team, home=True, n=10):

    if home:
        games = df[df["HomeTeam"] == team]
    else:
        games = df[df["AwayTeam"] == team]

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
# MERCADOS (PREVISÃO)
# ------------------------------
def goals_pred(h, a):
    return "OVER" if (h + a) > 2.5 else "UNDER"


def corners_pred(h, a):
    return "OVER" if abs(h - a) * 5 > 10.5 else "UNDER"


def cards_pred(h, a):
    return "OVER" if (3 - abs(h - a)) + 2 > 4.5 else "UNDER"


# ------------------------------
# MERCADOS (REAL)
# ------------------------------
def goals_real(row):
    return "OVER" if (row["FTHG"] + row["FTAG"]) > 2.5 else "UNDER"


def corners_real(row):
    if "HC" in row and "AC" in row:
        try:
            return "OVER" if (float(row["HC"]) + float(row["AC"])) > 10.5 else "UNDER"
        except:
            return None
    return None


def cards_real(row):
    if "HY" in row and "AY" in row:
        try:
            return "OVER" if (float(row["HY"]) + float(row["AY"])) > 4.5 else "UNDER"
        except:
            return None
    return None


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

        pred = "HOME" if p > 0.5 else "AWAY"
        real = "HOME" if r.get("FTR") == "H" else "AWAY" if r.get("FTR") == "A" else None

        g_pred = goals_pred(h, a)
        g_real = goals_real(r) if real else None

        c_pred = corners_pred(h, a)
        c_real = corners_real(r)

        ca_pred = cards_pred(h, a)
        ca_real = cards_real(r)

        rows.append({
            "home": home,
            "away": away,
            "pred_win": pred,
            "prob_home": round(p * 100, 2),

            "goals_market": g_pred,
            "corners_market": c_pred,
            "cards_market": ca_pred,

            "correct_win": (pred == real) if real else None,
            "correct_goals": (g_pred == g_real) if g_real else None,
            "correct_corners": (c_pred == c_real) if c_real else None,
            "correct_cards": (ca_pred == ca_real) if ca_real else None
        })

    return pd.DataFrame(rows)


# ------------------------------
# UI
# ------------------------------
st.title("⚽ Backtest Futebol V4.3")

date = st.date_input("Selecione a data")

if st.button("Rodar"):

    df = load_all()

    df_day = filter_day(df, date)
    history = df[df["Date"] < pd.to_datetime(date)]

    if df_day.empty:
        st.warning("Sem jogos")
        st.stop()

    has_results = df_day["FTR"].notna().any() if "FTR" in df_day else False

    res = run(df_day, history)

    # BACKTEST
    if has_results:

        st.success("📊 Modo Backtest")

        acc_win = res["correct_win"].dropna().mean() * 100
        acc_goals = res["correct_goals"].dropna().mean() * 100
        acc_corners = res["correct_corners"].dropna().mean() * 100
        acc_cards = res["correct_cards"].dropna().mean() * 100

        st.write(f"Win: {acc_win:.2f}%")
        st.write(f"Gols: {acc_goals:.2f}%")
        st.write(f"Cantos: {acc_corners:.2f}%")
        st.write(f"Cartões: {acc_cards:.2f}%")

        st.dataframe(res)

    # PICKS
    else:

        st.success("🎯 Modo Picks (Jogos futuros)")

        res["confidence"] = abs(res["prob_home"] - 50)

        strong = res[res["confidence"] >= 10]

        st.write("🔥 Picks Fortes")
        st.dataframe(strong.sort_values("confidence", ascending=False))

        st.write("📊 Todos os jogos")
        st.dataframe(res.sort_values("prob_home", ascending=False))

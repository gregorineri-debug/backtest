import streamlit as st
import pandas as pd
import numpy as np
import requests
from datetime import datetime
import pytz
from bs4 import BeautifulSoup

# =========================
# TIMEZONE
# =========================
tz = pytz.timezone("America/Sao_Paulo")
now = datetime.now(tz)

st.set_page_config(page_title="xG Multi Scenario Model", layout="wide")
st.title("📊 xG Multi Scenario Model")

st.write(f"🕒 São Paulo: {now.strftime('%Y-%m-%d %H:%M:%S')}")

# =========================
# DATA
# =========================
date = st.date_input("Selecione a data")

# =========================
# BUSCAR JOGOS
# =========================
def get_matches_by_date(date):

    try:
        formatted_date = date.strftime("%Y-%m-%d")
        url = f"https://api.sofascore.com/api/v1/sport/football/scheduled-events/{formatted_date}"

        res = requests.get(url)
        data = res.json()

        events = data.get("events", [])

        games = []

        for e in events:
            try:
                games.append({
                    "home": e["homeTeam"]["name"],
                    "away": e["awayTeam"]["name"]
                })
            except:
                continue

        return games

    except:
        return []

# =========================
# FBREF xG REAL
# =========================
def get_fbref_xg(team_name, n_games=10):

    try:
        search_url = f"https://fbref.com/en/search/search.fcgi?search={team_name.replace(' ', '+')}"
        res = requests.get(search_url, headers={"User-Agent": "Mozilla/5.0"})
        soup = BeautifulSoup(res.text, "html.parser")

        link = soup.find("a", href=True)

        if not link:
            return pd.DataFrame()

        team_url = "https://fbref.com" + link["href"]

        res = requests.get(team_url)
        soup = BeautifulSoup(res.text, "html.parser")

        table = soup.find("table", {"id": "matchlogs_for"})

        if table is None:
            return pd.DataFrame()

        df = pd.read_html(str(table))[0]

        if "xG" not in df.columns or "xGA" not in df.columns:
            return pd.DataFrame()

        df = df[["xG", "xGA", "Venue"]].dropna()

        return df.head(n_games)

    except:
        return pd.DataFrame()

# =========================
# FILTRO HOME/AWAY
# =========================
def filter_home_away(df, venue):
    if df.empty:
        return df
    return df[df["Venue"] == venue]

# =========================
# PREDIÇÃO
# =========================
def predict(df_home, df_away):

    if df_home.empty or df_away.empty:
        return "Sem dados", "Sem dados"

    home_xg = df_home["xG"].mean()
    away_xg = df_away["xG"].mean()

    home_xga = df_home["xGA"].mean()
    away_xga = df_away["xGA"].mean()

    home_score = (home_xg + away_xga) / 2
    away_score = (away_xg + home_xga) / 2

    total = home_score + away_score

    if total == 0:
        return "Sem dados", "Sem dados"

    prob_home = home_score / total
    prob_away = away_score / total

    if prob_home > 0.55:
        pick_v = "🏠 Casa"
    elif prob_away > 0.55:
        pick_v = "✈️ Visitante"
    else:
        pick_v = "⚖️ No Bet"

    pick_g = "Over 2.5" if total > 2.5 else "Under 2.5"

    return pick_v, pick_g

# =========================
# EXECUÇÃO
# =========================
games = get_matches_by_date(date)

if len(games) == 0:
    st.warning("Nenhum jogo encontrado")

results = []

for g in games:

    home = g["home"]
    away = g["away"]

    df_home_10 = get_fbref_xg(home, 10)
    df_away_10 = get_fbref_xg(away, 10)

    df_home_5 = get_fbref_xg(home, 5)
    df_away_5 = get_fbref_xg(away, 5)

    # HOME/AWAY
    df_home_home_10 = filter_home_away(df_home_10, "Home")
    df_away_away_10 = filter_home_away(df_away_10, "Away")

    df_home_home_5 = filter_home_away(df_home_5, "Home")
    df_away_away_5 = filter_home_away(df_away_5, "Away")

    row = {"Jogo": f"{home} vs {away}"}

    # CENÁRIOS
    row["10 Geral - Vitória"], row["10 Geral - Gols"] = predict(df_home_10, df_away_10)
    row["5 Geral - Vitória"], row["5 Geral - Gols"] = predict(df_home_5, df_away_5)

    row["10 H/A - Vitória"], row["10 H/A - Gols"] = predict(df_home_home_10, df_away_away_10)
    row["5 H/A - Vitória"], row["5 H/A - Gols"] = predict(df_home_home_5, df_away_away_5)

    results.append(row)

df = pd.DataFrame(results)

st.subheader("📋 Resultado Completo")

st.dataframe(df, use_container_width=True)

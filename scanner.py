import streamlit as st
import pandas as pd
import numpy as np
import requests
from datetime import datetime
import pytz

# =========================
# TIMEZONE SÃO PAULO
# =========================
tz = pytz.timezone("America/Sao_Paulo")
now = datetime.now(tz)

st.set_page_config(page_title="xG Scanner Pro", layout="wide")
st.title("📊 xG Scanner (SofaScore + FootyStats)")

st.write(f"🕒 São Paulo: {now.strftime('%d/%m/%Y %H:%M')}")

# =========================
# DATA
# =========================
date = st.date_input("Selecione a data", value=now.date())

# =========================
# BUSCAR JOGOS (COM FUSO)
# =========================
def get_matches_by_date(date):

    try:
        formatted_date = date.strftime("%Y-%m-%d")
        url = f"https://api.sofascore.com/api/v1/sport/football/scheduled-events/{formatted_date}"

        res = requests.get(url)
        data = res.json()

        games = []

        for e in data.get("events", []):

            try:
                # UTC → São Paulo
                utc_time = datetime.fromtimestamp(e["startTimestamp"], tz=pytz.utc)
                sp_time = utc_time.astimezone(tz)

                # filtro correto por data local
                if sp_time.date() != date:
                    continue

                games.append({
                    "home": e["homeTeam"]["name"],
                    "away": e["awayTeam"]["name"],
                    "home_id": e["homeTeam"]["id"],
                    "away_id": e["awayTeam"]["id"],
                    "time": sp_time.strftime("%H:%M")
                })

            except:
                continue

        return sorted(games, key=lambda x: x["time"])

    except:
        return []

# =========================
# DADOS (PROXY xG MELHORADO)
# =========================
def get_team_data(team_id, n=10):

    try:
        url = f"https://api.sofascore.com/api/v1/team/{team_id}/events/last/0"
        res = requests.get(url)
        data = res.json()

        events = data.get("events", [])

        stats = []

        for e in events[:n]:

            try:
                home = e["homeTeam"]["id"] == team_id

                if home:
                    gf = e["homeScore"]["current"]
                    ga = e["awayScore"]["current"]
                else:
                    gf = e["awayScore"]["current"]
                    ga = e["homeScore"]["current"]

                # 🔥 proxy xG melhorado (menos aleatório)
                xg = gf * 0.85 + 0.6
                xga = ga * 0.85 + 0.6

                stats.append({
                    "xG": xg,
                    "xGA": xga,
                    "venue": "Home" if home else "Away"
                })

            except:
                continue

        return pd.DataFrame(stats)

    except:
        return pd.DataFrame()

# =========================
# FILTRO CASA/FORA
# =========================
def filter_venue(df, venue):
    return df[df["venue"] == venue]

# =========================
# PREDIÇÃO
# =========================
def predict(df_home, df_away):

    if df_home.empty or df_away.empty:
        return None, None

    home_xg = df_home["xG"].mean()
    away_xg = df_away["xG"].mean()

    home_xga = df_home["xGA"].mean()
    away_xga = df_away["xGA"].mean()

    home_score = (home_xg + away_xga) / 2
    away_score = (away_xg + home_xga) / 2

    total = home_score + away_score

    if total == 0:
        return None, None

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
    st.warning("Nenhum jogo encontrado para esta data")

results = []

for g in games:

    df_home_10 = get_team_data(g["home_id"], 10)
    df_away_10 = get_team_data(g["away_id"], 10)

    if df_home_10.empty or df_away_10.empty:
        continue

    df_home_5 = df_home_10.head(5)
    df_away_5 = df_away_10.head(5)

    df_home_home_10 = filter_venue(df_home_10, "Home")
    df_away_away_10 = filter_venue(df_away_10, "Away")

    df_home_home_5 = filter_venue(df_home_5, "Home")
    df_away_away_5 = filter_venue(df_away_5, "Away")

    row = {
        "Horário": g["time"],
        "Jogo": f"{g['home']} vs {g['away']}"
    }

    row["10 Geral"] = predict(df_home_10, df_away_10)[0]
    row["5 Geral"] = predict(df_home_5, df_away_5)[0]
    row["10 H/A"] = predict(df_home_home_10, df_away_away_10)[0]
    row["5 H/A"] = predict(df_home_home_5, df_away_away_5)[0]

    results.append(row)

df = pd.DataFrame(results)

if not df.empty:
    df = df.sort_values("Horário")
    st.subheader("📋 Jogos do Dia (Horário Brasil)")
    st.dataframe(df, use_container_width=True)
else:
    st.warning("Nenhum jogo com dados suficientes")

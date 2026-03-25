import streamlit as st
import pandas as pd
import numpy as np
import requests
from datetime import datetime
import pytz

# =========================
# TIMEZONE
# =========================
tz = pytz.timezone("America/Sao_Paulo")
now = datetime.now(tz)

st.set_page_config(page_title="xG Scanner PRO", layout="wide")
st.title("📊 xG Scanner PRO")

st.write(f"🕒 São Paulo: {now.strftime('%d/%m/%Y %H:%M')}")

# =========================
# DATA
# =========================
date = st.date_input("Selecione a data", value=now.date())

# =========================
# JOGOS DO DIA
# =========================
def get_matches_by_date(date):

    formatted_date = date.strftime("%Y-%m-%d")
    url = f"https://api.sofascore.com/api/v1/sport/football/scheduled-events/{formatted_date}"

    res = requests.get(url)
    data = res.json()

    games = []

    for e in data.get("events", []):
        try:
            utc_time = datetime.fromtimestamp(e["startTimestamp"], tz=pytz.utc)
            sp_time = utc_time.astimezone(tz)

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

# =========================
# DADOS (PROXY xG)
# =========================
def get_team_data(team_id, n=10):

    url = f"https://api.sofascore.com/api/v1/team/{team_id}/events/last/0"
    res = requests.get(url)
    data = res.json()

    stats = []

    for e in data.get("events", [])[:n]:

        try:
            home = e["homeTeam"]["id"] == team_id

            if home:
                gf = e["homeScore"]["current"]
                ga = e["awayScore"]["current"]
            else:
                gf = e["awayScore"]["current"]
                ga = e["homeScore"]["current"]

            # 🔥 proxy consistente (sem random)
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
# CONSOLIDAÇÃO FINAL
# =========================
def final_pick(picks):

    picks = [p for p in picks if p is not None]

    casa = picks.count("🏠 Casa")
    fora = picks.count("✈️ Visitante")

    if casa >= 3:
        return "🔥 Casa Forte"
    elif fora >= 3:
        return "🔥 Visitante Forte"
    else:
        return "⚖️ Equilibrado"

# =========================
# EXECUÇÃO
# =========================
games = get_matches_by_date(date)

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

    p1, g1 = predict(df_home_10, df_away_10)
    p2, g2 = predict(df_home_5, df_away_5)
    p3, g3 = predict(df_home_home_10, df_away_away_10)
    p4, g4 = predict(df_home_home_5, df_away_away_5)

    results.append({
        "Hora": g["time"],
        "Jogo": f"{g['home']} vs {g['away']}",

        "10G V": p1, "10G G": g1,
        "5G V": p2, "5G G": g2,
        "10H/A V": p3, "10H/A G": g3,
        "5H/A V": p4, "5H/A G": g4,

        "Pick Final": final_pick([p1, p2, p3, p4])
    })

df = pd.DataFrame(results)

if not df.empty:
    df = df.sort_values("Hora")
    st.dataframe(df, use_container_width=True)
else:
    st.warning("Nenhum jogo com dados suficientes")

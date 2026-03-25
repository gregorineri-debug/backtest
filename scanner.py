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

st.set_page_config(page_title="Winner Model PRO", layout="wide")
st.title("🏆 Winner Prediction PRO")

st.write(f"🕒 São Paulo: {now.strftime('%d/%m/%Y %H:%M')}")

# =========================
# DATA
# =========================
date = st.date_input("Selecione a data", value=now.date())

# =========================
# JOGOS
# =========================
def get_matches(date):

    url = f"https://api.sofascore.com/api/v1/sport/football/scheduled-events/{date.strftime('%Y-%m-%d')}"
    res = requests.get(url).json()

    games = []

    for e in res.get("events", []):
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
                "time": sp_time.strftime("%H:%M"),
                "tournament_id": e["tournament"]["uniqueTournament"]["id"]
            })

        except:
            continue

    return games

# =========================
# DADOS TIME
# =========================
def get_team_data(team_id, n=10):

    url = f"https://api.sofascore.com/api/v1/team/{team_id}/events/last/0"
    data = requests.get(url).json()

    xg_list = []
    points = 0

    for e in data.get("events", [])[:n]:

        try:
            home = e["homeTeam"]["id"] == team_id

            if home:
                gf = e["homeScore"]["current"]
                ga = e["awayScore"]["current"]
            else:
                gf = e["awayScore"]["current"]
                ga = e["homeScore"]["current"]

            # proxy xG
            xg = gf * 0.85 + 0.6
            xga = ga * 0.85 + 0.6

            xg_list.append(xg - xga)

            # pontos
            if gf > ga:
                points += 3
            elif gf == ga:
                points += 1

        except:
            continue

    if len(xg_list) == 0:
        return None

    return {
        "xg": np.mean(xg_list),
        "form": points / (n * 3)
    }

# =========================
# TABELA
# =========================
def get_standings(tournament_id):

    try:
        url = f"https://api.sofascore.com/api/v1/unique-tournament/{tournament_id}/standings/total"
        data = requests.get(url).json()

        table = data["standings"][0]["rows"]

        standings = {}

        for row in table:
            standings[row["team"]["id"]] = {
                "position": row["position"],
                "points": row["points"]
            }

        return standings

    except:
        return {}

# =========================
# MOTIVAÇÃO
# =========================
def motivation_score(position, total_teams):

    if position <= 3:
        return 1.0  # título
    elif position <= 6:
        return 0.8  # competições
    elif position >= total_teams - 2:
        return 1.0  # rebaixamento
    elif position >= total_teams - 5:
        return 0.7
    else:
        return 0.3  # meio tabela

# =========================
# SCORE FINAL
# =========================
def calculate_score(team_stats, standing, total_teams):

    if team_stats is None or standing is None:
        return None

    xg_score = team_stats["xg"]
    form_score = team_stats["form"]

    position = standing["position"]

    motivation = motivation_score(position, total_teams)

    return (xg_score * 0.4) + (form_score * 0.3) + ((1 / position) * 0.2) + (motivation * 0.1)

# =========================
# EXECUÇÃO
# =========================
games = get_matches(date)

results = []

for g in games:

    standings = get_standings(g["tournament_id"])

    if not standings:
        continue

    total_teams = len(standings)

    home_stats = get_team_data(g["home_id"])
    away_stats = get_team_data(g["away_id"])

    home_stand = standings.get(g["home_id"])
    away_stand = standings.get(g["away_id"])

    if not home_stats or not away_stats or not home_stand or not away_stand:
        continue

    home_score = calculate_score(home_stats, home_stand, total_teams)
    away_score = calculate_score(away_stats, away_stand, total_teams)

    if home_score is None or away_score is None:
        continue

    if home_score > away_score:
        pick = "🏠 Casa"
    else:
        pick = "✈️ Visitante"

    results.append({
        "Hora": g["time"],
        "Jogo": f"{g['home']} vs {g['away']}",
        "Pick": pick,
        "Score Casa": round(home_score, 2),
        "Score Fora": round(away_score, 2),
        "Pos Casa": home_stand["position"],
        "Pos Fora": away_stand["position"]
    })

df = pd.DataFrame(results)

if not df.empty:
    df = df.sort_values(by="Score Casa", ascending=False)
    st.dataframe(df, use_container_width=True)
else:
    st.warning("Sem dados suficientes")

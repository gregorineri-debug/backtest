import streamlit as st
import requests
from datetime import datetime
import pytz
import pandas as pd

# -------------------------
# CONFIG
# -------------------------
BR_TZ = pytz.timezone("America/Sao_Paulo")

LEAGUE_MODEL = {
    "Brasileirão Betano": ["form", "home_strength", "xg"],
    "Premier League": ["xg", "shots", "form"],
    "La Liga": ["possession", "xg", "form"],
    "Bundesliga": ["shots", "xg", "form"],
    "default": ["form", "xg", "shots"]
}

# -------------------------
# API
# -------------------------

def get_events(date):
    url = f"https://api.sofascore.com/api/v1/sport/football/scheduled-events/{date}"
    return requests.get(url).json().get("events", [])


def get_team_last_matches(team_id):
    url = f"https://api.sofascore.com/api/v1/team/{team_id}/events/last/5"
    data = requests.get(url).json()
    return data.get("events", [])


def get_event_stats(event_id):
    try:
        url = f"https://api.sofascore.com/api/v1/event/{event_id}/statistics"
        data = requests.get(url).json()
        stats = data["statistics"][0]["groups"]

        def find(name):
            for g in stats:
                for s in g["statisticsItems"]:
                    if s["name"] == name:
                        return float(s["home"]), float(s["away"])
            return 0, 0

        return find("Expected goals"), find("Total shots")

    except:
        return (0,0),(0,0)

# -------------------------
# FORMA
# -------------------------

def calculate_form(team_id):
    matches = get_team_last_matches(team_id)

    if not matches:
        return 0.5

    points = 0
    total = 0

    for m in matches:
        try:
            home_id = m["homeTeam"]["id"]
            hs = m["homeScore"]["current"]
            as_ = m["awayScore"]["current"]

            if team_id == home_id:
                if hs > as_:
                    points += 3
                elif hs == as_:
                    points += 1
            else:
                if as_ > hs:
                    points += 3
                elif hs == as_:
                    points += 1

            total += 3
        except:
            continue

    return points / total if total > 0 else 0.5

# -------------------------
# MÉDIAS
# -------------------------

def calculate_averages(team_id):

    matches = get_team_last_matches(team_id)

    xg_total = 0
    shots_total = 0
    count = 0

    for m in matches:
        try:
            (xg_h,xg_a),(s_h,s_a) = get_event_stats(m["id"])

            if m["homeTeam"]["id"] == team_id:
                xg_total += xg_h
                shots_total += s_h
            else:
                xg_total += xg_a
                shots_total += s_a

            count += 1
        except:
            continue

    if count == 0:
        return 1, 10

    return xg_total / count, shots_total / count

# -------------------------
# SCORE
# -------------------------

def calculate_score(home_id, away_id, league):

    criteria = LEAGUE_MODEL.get(league, LEAGUE_MODEL["default"])

    home_form = calculate_form(home_id)
    away_form = calculate_form(away_id)

    home_xg, home_shots = calculate_averages(home_id)
    away_xg, away_shots = calculate_averages(away_id)

    home_score = 0
    away_score = 0

    for c in criteria:

        if c == "form":
            home_score += home_form
            away_score += away_form

        elif c == "xg":
            home_score += home_xg
            away_score += away_xg

        elif c == "shots":
            home_score += home_shots * 0.05
            away_score += away_shots * 0.05

        elif c == "home_strength":
            home_score += 0.3

    return home_score, away_score

# -------------------------
# PREDIÇÃO
# -------------------------

def predict(event):

    league = event["tournament"]["name"]

    home_id = event["homeTeam"]["id"]
    away_id = event["awayTeam"]["id"]

    home_score, away_score = calculate_score(home_id, away_id, league)

    diff = home_score - away_score

    winner = "HOME" if diff > 0 else "AWAY"
    edge = abs(diff)

    return winner, edge

# -------------------------
# UI
# -------------------------

st.title("⚽ Modelo Profissional com Forma Real (Tabela)")

date = st.date_input("Escolha a data")
date_str = date.strftime("%Y-%m-%d")

events = get_events(date_str)

st.write(f"Jogos encontrados: {len(events)}")

# -------------------------
# EXECUÇÃO
# -------------------------

if st.button("Analisar Jogos"):

    results = []

    for e in events:

        try:
            league = e["tournament"]["name"]

            winner, edge = predict(e)

            home = e["homeTeam"]["name"]
            away = e["awayTeam"]["name"]

            utc = datetime.utcfromtimestamp(e["startTimestamp"]).replace(tzinfo=pytz.utc)
            br_time = utc.astimezone(BR_TZ).strftime("%H:%M")

            if edge >= 1.0:
                tag = "ELITE"
            elif edge >= 0.5:
                tag = "BOM"
            else:
                tag = "FRACO"

            results.append({
                "Hora": br_time,
                "Liga": league,
                "Jogo": f"{home} vs {away}",
                "Pick": winner,
                "Edge": round(edge, 2),
                "Classificação": tag
            })

        except:
            continue

    df = pd.DataFrame(results)

    # Ordena pelos melhores
    df = df.sort_values(by="Edge", ascending=False)

    st.dataframe(df, use_container_width=True)

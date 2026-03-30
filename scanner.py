import streamlit as st
import requests
from datetime import datetime
import pytz
import pandas as pd

# -------------------------
# CONFIG
# -------------------------
BR_TZ = pytz.timezone("America/Sao_Paulo")

VALID_LEAGUE_IDS = [
    325,390,17,18,8,54,35,44,23,53,34,182,955,
    155,703,45,38,247,172,11653,11539,11536,
    170,39,808,36,242,185,37,131,192,937,
    11621,11620,20,11540,11541,406,202,
    238,239,152,40,215,52,278
]

LEAGUE_MODEL = {
    325: ["form","home_strength","xg"],  # Brasileirão
    17: ["xg","shots","form"],          # Premier League
    8: ["possession","xg","form"],      # La Liga
    35: ["shots","xg","form"],          # Bundesliga
}

# -------------------------
# API
# -------------------------

def get_events(date):
    url = f"https://api.sofascore.com/api/v1/sport/football/scheduled-events/{date}"
    return requests.get(url).json().get("events", [])

# -------------------------
# FILTROS
# -------------------------

def is_valid_league(event):
    try:
        league_id = event["tournament"]["uniqueTournament"]["id"]
        return league_id in VALID_LEAGUE_IDS
    except:
        return False


def is_same_day_br(event, selected_date):
    utc = datetime.utcfromtimestamp(event["startTimestamp"]).replace(tzinfo=pytz.utc)
    br_time = utc.astimezone(BR_TZ)
    return br_time.date() == selected_date

# -------------------------
# STATS
# -------------------------

def get_team_last_matches(team_id):
    url = f"https://api.sofascore.com/api/v1/team/{team_id}/events/last/5"
    return requests.get(url).json().get("events", [])


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

    points = 0
    total = 0

    for m in matches:
        try:
            hs = m["homeScore"]["current"]
            as_ = m["awayScore"]["current"]

            if m["homeTeam"]["id"] == team_id:
                if hs > as_: points += 3
                elif hs == as_: points += 1
            else:
                if as_ > hs: points += 3
                elif hs == as_: points += 1

            total += 3
        except:
            continue

    return points / total if total else 0.5

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

def calculate_score(home_id, away_id, league_id):

    criteria = LEAGUE_MODEL.get(league_id, ["form","xg","shots"])

    hf = calculate_form(home_id)
    af = calculate_form(away_id)

    hxg, hs = calculate_averages(home_id)
    axg, as_ = calculate_averages(away_id)

    home = 0
    away = 0

    for c in criteria:
        if c == "form":
            home += hf; away += af
        elif c == "xg":
            home += hxg; away += axg
        elif c == "shots":
            home += hs * 0.05; away += as_ * 0.05
        elif c == "home_strength":
            home += 0.3

    return home, away

# -------------------------
# PREDIÇÃO
# -------------------------

def predict(e):
    league_id = e["tournament"]["uniqueTournament"]["id"]

    home_id = e["homeTeam"]["id"]
    away_id = e["awayTeam"]["id"]

    h, a = calculate_score(home_id, away_id, league_id)

    diff = h - a

    return ("HOME" if diff > 0 else "AWAY"), abs(diff)

# -------------------------
# UI
# -------------------------

st.title("⚽ Scanner Profissional (Tabela + IDs)")

date = st.date_input("Escolha a data")

events = get_events(date.strftime("%Y-%m-%d"))

filtered_events = [
    e for e in events
    if is_valid_league(e)
    and is_same_day_br(e, date)
]

st.write(f"Jogos válidos: {len(filtered_events)}")

# -------------------------
# EXECUÇÃO (TABELA)
# -------------------------

if st.button("Analisar Jogos"):

    results = []

    for e in filtered_events:

        winner, edge = predict(e)

        if edge < 0.5:
            continue

        utc = datetime.utcfromtimestamp(e["startTimestamp"]).replace(tzinfo=pytz.utc)
        br_time = utc.astimezone(BR_TZ).strftime("%H:%M")

        home = e["homeTeam"]["name"]
        away = e["awayTeam"]["name"]

        tag = "ELITE" if edge >= 1.0 else "BOM"

        results.append({
            "Hora": br_time,
            "Jogo": f"{home} vs {away}",
            "Pick": winner,
            "Edge": round(edge, 2),
            "Classificação": tag
        })

    if results:

        df = pd.DataFrame(results)

        # 🔥 ordena pelos melhores
        df = df.sort_values(by="Edge", ascending=False)

        st.dataframe(df, use_container_width=True)

        st.write(f"Total de picks relevantes: {len(df)}")

    else:
        st.warning("Nenhuma oportunidade ELITE/BOM encontrada.")

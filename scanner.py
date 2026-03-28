import streamlit as st
import requests
from datetime import datetime
import pytz
import pandas as pd

HEADERS = {"User-Agent": "Mozilla/5.0"}

team_stats_cache = {}
team_matches_cache = {}

# ------------------------------
# PESOS
# ------------------------------
LEAGUE_WEIGHTS = {
    "Premier League": {"xg":0.5,"sot":0.3,"xga":0.2},
    "Bundesliga": {"xg":0.55,"sot":0.25,"xga":0.2},
    "Serie A": {"xg":0.35,"sot":0.25,"xga":0.4},
    "La Liga": {"xg":0.45,"sot":0.25,"xga":0.3},
    "Ligue 1": {"xg":0.4,"sot":0.35,"xga":0.25},
}

DEFAULT_WEIGHTS = {"xg":0.45,"sot":0.3,"xga":0.25}

# ------------------------------
# MATCHES
# ------------------------------
def get_matches_by_date(date):
    date_str = date.strftime("%Y-%m-%d")
    url = f"https://api.sofascore.com/api/v1/sport/football/scheduled-events/{date_str}"
    res = requests.get(url, headers=HEADERS)
    if res.status_code != 200:
        return []
    return res.json().get("events", [])

# ------------------------------
# STATS
# ------------------------------
def get_match_stats(match_id):
    url = f"https://api.sofascore.com/api/v1/event/{match_id}/statistics"
    res = requests.get(url, headers=HEADERS)
    if res.status_code != 200:
        return None
    return res.json()

def extract_stats(data):
    stats = {}
    try:
        groups = data["statistics"][0]["groups"]
        for g in groups:
            for item in g["statisticsItems"]:
                stats[item["name"]] = {
                    "home": item["home"],
                    "away": item["away"]
                }
    except:
        return None
    return stats

def val(x):
    try:
        return float(x)
    except:
        return 0

def convert_stats(stats):

    # tenta pegar xG normal
    home_xg = val(
        stats.get("Expected goals", {}).get("home") or
        stats.get("xG", {}).get("home", 0)
    )

    away_xg = val(
        stats.get("Expected goals", {}).get("away") or
        stats.get("xG", {}).get("away", 0)
    )

    home_sot = val(stats.get("Shots on target", {}).get("home", 0))
    away_sot = val(stats.get("Shots on target", {}).get("away", 0))

    # 🔥 fallback inteligente (se não tiver xG)
    if home_xg == 0 and home_sot > 0:
        home_xg = home_sot * 0.30

    if away_xg == 0 and away_sot > 0:
        away_xg = away_sot * 0.30

    home = {"xg": home_xg, "xga": away_xg, "sot": home_sot}
    away = {"xg": away_xg, "xga": home_xg, "sot": away_sot}

    return home, away

# ------------------------------
# TEAM STATS
# ------------------------------
def get_team_recent_stats(team_id, limit=10):

    if team_id in team_stats_cache:
        return team_stats_cache[team_id]

    url = f"https://api.sofascore.com/api/v1/team/{team_id}/events/last/{limit}"
    res = requests.get(url, headers=HEADERS)

    if res.status_code != 200:
        return None

    events = res.json().get("events", [])

    xg_total = 0
    xga_total = 0
    sot_total = 0
    count = 0

    for e in events:
        if e.get("status", {}).get("type") != "finished":
            continue

        stats_raw = get_match_stats(e["id"])
        if not stats_raw:
            continue

        extracted = extract_stats(stats_raw)
        if not extracted:
            continue

        home, away = convert_stats(extracted)

        if e["homeTeam"]["id"] == team_id:
            xg_total += home["xg"]
            xga_total += home["xga"]
            sot_total += home["sot"]
        else:
            xg_total += away["xg"]
            xga_total += away["xga"]
            sot_total += away["sot"]

        count += 1

    if count < 3:
        return None

    result = {
        "xg": xg_total / count,
        "xga": xga_total / count,
        "sot": sot_total / count
    }

    team_stats_cache[team_id] = result
    return result

# ------------------------------
# SCORE
# ------------------------------
def normalize(val, max_val):
    return max(min(val / max_val, 1), -1)

def calculate_score(home, away, weights):

    xg_diff = normalize(home["xg"] - away["xg"], 2.5)
    sot_diff = normalize(home["sot"] - away["sot"], 8)
    xga_diff = normalize(away["xga"] - home["xga"], 2.5)

    return (
        xg_diff * weights["xg"] +
        sot_diff * weights["sot"] +
        xga_diff * weights["xga"]
    )

def classify(edge):
    if edge >= 0.55:
        return "ELITE"
    elif edge >= 0.25:
        return "BOA"
    else:
        return "EVITAR"

# ------------------------------
# UI
# ------------------------------
st.title("🔥 Scanner V4 PRO")

selected_date = st.date_input("Selecione a data")

if st.button("Buscar Jogos"):

    matches = get_matches_by_date(selected_date)

    results = []

    for match in matches:

        league = match.get("tournament", {}).get("uniqueTournament", {}).get("name", "")

        home_name = match["homeTeam"]["name"]
        away_name = match["awayTeam"]["name"]

        weights = LEAGUE_WEIGHTS.get(league, DEFAULT_WEIGHTS)

        home = get_team_recent_stats(match["homeTeam"]["id"])
        away = get_team_recent_stats(match["awayTeam"]["id"])

        if not home or not away:
            continue

        score = calculate_score(home, away, weights)

        winner = home_name if score > 0 else away_name

        results.append({
            "Liga": league,
            "Jogo": f"{home_name} vs {away_name}",
            "Pick": winner,
            "Edge": round(score, 2),
            "Classificação": classify(abs(score))
        })

    df = pd.DataFrame(results).sort_values(by="Edge", ascending=False)

    st.dataframe(df, use_container_width=True)

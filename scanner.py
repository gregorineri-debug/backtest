import streamlit as st
import requests
from datetime import datetime
import pytz
import pandas as pd

HEADERS = {"User-Agent": "Mozilla/5.0"}

# ------------------------------
# LIGAS PERMITIDAS (SUA LISTA)
# ------------------------------
ALLOWED_LEAGUES = [
    "Premier League","Championship",
    "LaLiga","LaLiga 2",
    "Bundesliga","2. Bundesliga",
    "Serie A","Serie B",
    "Ligue 1","Ligue 2",
    "Brasileirão Série A","Brasileirão Série B",
    "Primeira Liga","Eredivisie","Belgian Pro League"
]

# ------------------------------
# PESOS
# ------------------------------
LEAGUE_WEIGHTS = {
    "Premier League": {"xg":0.5,"sot":0.3,"xga":0.2},
    "Bundesliga": {"xg":0.55,"sot":0.25,"xga":0.2},
    "Serie A": {"xg":0.35,"sot":0.25,"xga":0.4},
    "LaLiga": {"xg":0.45,"sot":0.25,"xga":0.3},
    "Ligue 1": {"xg":0.4,"sot":0.35,"xga":0.25},
}

DEFAULT_WEIGHTS = {"xg":0.45,"sot":0.3,"xga":0.25}

# ------------------------------
# BUSCAR JOGOS
# ------------------------------
def get_matches_by_date(date):
    url = f"https://api.sofascore.com/api/v1/sport/football/scheduled-events/{date.strftime('%Y-%m-%d')}"
    res = requests.get(url, headers=HEADERS)
    if res.status_code != 200:
        return []
    return res.json().get("events", [])

# ------------------------------
# FILTRO SP
# ------------------------------
def filter_matches_sp(matches, selected_date):
    tz_sp = pytz.timezone("America/Sao_Paulo")
    filtered = []

    for m in matches:
        ts = m.get("startTimestamp")
        if not ts:
            continue

        dt = datetime.utcfromtimestamp(ts).replace(tzinfo=pytz.utc).astimezone(tz_sp)

        if dt.date() == selected_date:
            filtered.append(m)

    return filtered

# ------------------------------
# FILTRO LIGAS + MIN 10 JOGOS
# ------------------------------
def is_valid_league(match):

    league_name = match["tournament"]["name"]

    if league_name not in ALLOWED_LEAGUES:
        return False

    tournament_id = match["tournament"]["uniqueTournament"]["id"]

    url = f"https://api.sofascore.com/api/v1/unique-tournament/{tournament_id}/events/last/0"
    res = requests.get(url, headers=HEADERS)

    if res.status_code != 200:
        return False

    data = res.json().get("events", [])

    finished = [e for e in data if e.get("status", {}).get("type") == "finished"]

    return len(finished) >= 10

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
        for g in data["statistics"][0]["groups"]:
            for i in g["statisticsItems"]:
                stats[i["name"]] = {"home": i["home"], "away": i["away"]}
    except:
        pass
    return stats

def convert_stats(stats):
    def v(x):
        try: return float(x)
        except: return 0

    hxg = v(stats.get("Expected goals", {}).get("home", 0))
    axg = v(stats.get("Expected goals", {}).get("away", 0))

    hsot = v(stats.get("Shots on target", {}).get("home", 0))
    asot = v(stats.get("Shots on target", {}).get("away", 0))

    return (
        {"xg":hxg,"xga":axg,"sot":hsot},
        {"xg":axg,"xga":hxg,"sot":asot}
    )

# ------------------------------
# SCORE V4
# ------------------------------
def normalize(v, m): return v/m if m>0 else 0

def calculate_score(home, away, w):
    xg = normalize(home["xg"]-away["xg"],3)
    sot = normalize(home["sot"]-away["sot"],10)
    xga = normalize(away["xga"]-home["xga"],3)

    return xg*w["xg"] + sot*w["sot"] + xga*w["xga"]

def classify(e):
    if e>=0.6: return "ELITE"
    elif e>=0.3: return "BOA"
    return "EVITAR"

# ------------------------------
# UI
# ------------------------------
st.title("🔥 Scanner V4 - Jogos do Dia")

date = st.date_input("Selecione a data")

if st.button("Buscar Jogos"):

    matches = get_matches_by_date(date)
    matches = filter_matches_sp(matches, date)

    results = []

    for m in matches:

        if not is_valid_league(m):
            continue

        league = m["tournament"]["name"]
        weights = LEAGUE_WEIGHTS.get(league, DEFAULT_WEIGHTS)

        stats_raw = get_match_stats(m["id"])
        if not stats_raw:
            continue

        stats = extract_stats(stats_raw)
        if not stats:
            continue

        home, away = convert_stats(stats)

        score = calculate_score(home, away, weights)

        winner = m["homeTeam"]["name"] if score>0 else m["awayTeam"]["name"]

        results.append({
            "Liga": league,
            "Jogo": f"{m['homeTeam']['name']} vs {m['awayTeam']['name']}",
            "Vencedor": winner,
            "Edge": round(score,2),
            "Classificação": classify(abs(score))
        })

    df = pd.DataFrame(results).sort_values(by="Edge", ascending=False)

    filtro = st.selectbox("Filtrar por nível", ["Todos","ELITE","BOA","EVITAR"])

    if filtro != "Todos":
        df = df[df["Classificação"] == filtro]

    st.dataframe(df, use_container_width=True)

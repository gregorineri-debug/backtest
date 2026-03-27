import streamlit as st
import requests
from datetime import datetime
import pytz
import pandas as pd

# ------------------------------
# CONFIG
# ------------------------------
HEADERS = {"User-Agent": "Mozilla/5.0"}

# CACHE
team_matches_cache = {}

# ------------------------------
# 🔥 FILTRO DE LIGAS (OTIMIZADO)
# ------------------------------
ALLOWED_LEAGUES = [
    "Brasileirão Betano","Brasileirão Série B",
    "Premier League","Championship",
    "La Liga","La Liga 2",
    "Bundesliga","2. Bundesliga",
    "Serie A","Serie B",
    "Ligue 1","Ligue 2",
    "Saudi Pro League",
    "Liga Profesional de Fútbol","Primera Nacional",
    "Austrian Bundesliga",
    "Pro League",
    "Parva Liga",
    "Czech First League",
    "Liga de Primera",
    "Primera A, Apertura","Primera A, Finalización",
    "HNL",
    "Danish Superliga",
    "Egyptian Premier League",
    "Scottish Premiership",
    "MLS",
    "Stoiximan Super League",
    "VriendenLoterij Eredivisie","Eerste Divisie",
    "Premier Division",
    "Botola Pro",
    "Liga MX, Apertura","Liga MX, Clausura",
    "Eliteserien",
    "Primera División, Apertura","Primera División, Clausura",
    "Liga 1",
    "Ekstraklasa",
    "Liga Portugal Betclic","Liga Portugal 2",
    "Romanian SuperLiga",
    "Allsvenskan",
    "Swiss Super League",
    "Trendyol Super Lig",
    "Liga AUF Uruguaya"
]

# ------------------------------
# PESOS POR LIGA
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
# BUSCAR JOGOS
# ------------------------------
def get_matches_by_date(date):
    date_str = date.strftime("%Y-%m-%d")
    url = f"https://api.sofascore.com/api/v1/sport/football/scheduled-events/{date_str}"
    res = requests.get(url, headers=HEADERS)

    if res.status_code != 200:
        return []

    return res.json().get("events", [])

# ------------------------------
# FILTRO SP + LIGA
# ------------------------------
def filter_matches(matches, selected_date):
    tz_sp = pytz.timezone("America/Sao_Paulo")
    filtered = []

    for match in matches:
        ts = match.get("startTimestamp")
        if not ts:
            continue

        league = match["tournament"]["name"]

        # 🔥 FILTRO DE LIGA (ANTES DE TUDO)
        if league not in ALLOWED_LEAGUES:
            continue

        utc = datetime.utcfromtimestamp(ts).replace(tzinfo=pytz.utc)
        sp = utc.astimezone(tz_sp)

        if sp.date() == selected_date:
            filtered.append(match)

    return filtered

# ------------------------------
# RODADAS
# ------------------------------
def get_team_matches_played(team_id):

    if team_id in team_matches_cache:
        return team_matches_cache[team_id]

    url = f"https://api.sofascore.com/api/v1/team/{team_id}/events/last/0"
    res = requests.get(url, headers=HEADERS)

    if res.status_code != 200:
        return 0

    events = res.json().get("events", [])
    finished = [e for e in events if e.get("status", {}).get("type") == "finished"]

    count = len(finished)
    team_matches_cache[team_id] = count
    return count

# ------------------------------
# STATS JOGO
# ------------------------------
def get_match_stats(match_id):
    url = f"https://api.sofascore.com/api/v1/event/{match_id}/statistics"
    res = requests.get(url, headers=HEADERS)

    if res.status_code != 200:
        return None

    return res.json()

# ------------------------------
# STATS MÉDIOS (ROBUSTO)
# ------------------------------
def get_team_recent_stats(team_id, limit=5):

    url = f"https://api.sofascore.com/api/v1/team/{team_id}/events/last/{limit}"
    res = requests.get(url, headers=HEADERS)

    if res.status_code != 200:
        return {"xg":1.2,"xga":1.2,"sot":4}

    events = res.json().get("events", [])

    xg_total = 0
    xga_total = 0
    sot_total = 0
    count = 0

    for e in events:
        if e.get("status", {}).get("type") != "finished":
            continue

        try:
            stats = get_match_stats(e["id"])
            if not stats:
                continue

            extracted = extract_stats(stats)
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
        except:
            continue

    if count == 0:
        return {"xg":1.2,"xga":1.2,"sot":4}

    return {
        "xg": xg_total / count,
        "xga": xga_total / count,
        "sot": sot_total / count
    }

# ------------------------------
# EXTRAIR
# ------------------------------
def extract_stats(data):
    stats = {}

    try:
        groups = data["statistics"][0]["groups"]
        for group in groups:
            for item in group["statisticsItems"]:
                stats[item["name"]] = {
                    "home": item["home"],
                    "away": item["away"]
                }
    except:
        pass

    return stats

# ------------------------------
# CONVERTER
# ------------------------------
def convert_stats(stats):
    def val(x):
        try:
            return float(x)
        except:
            return 0

    home_xg = val(stats.get("Expected goals", {}).get("home", 0))
    away_xg = val(stats.get("Expected goals", {}).get("away", 0))

    home_sot = val(stats.get("Shots on target", {}).get("home", 0))
    away_sot = val(stats.get("Shots on target", {}).get("away", 0))

    home = {"xg": home_xg, "xga": away_xg, "sot": home_sot}
    away = {"xg": away_xg, "xga": home_xg, "sot": away_sot}

    return home, away

# ------------------------------
# SCORE
# ------------------------------
def normalize(val, max_val):
    return val / max_val if max_val > 0 else 0

def calculate_score(home, away, weights):
    xg_diff = normalize(home["xg"] - away["xg"], 3)
    sot_diff = normalize(home["sot"] - away["sot"], 10)
    xga_diff = normalize(away["xga"] - home["xga"], 3)

    return (
        xg_diff * weights["xg"] +
        sot_diff * weights["sot"] +
        xga_diff * weights["xga"]
    )

def classify(edge):
    if edge >= 0.6:
        return "ELITE"
    elif edge >= 0.3:
        return "BOA"
    else:
        return "EVITAR"

# ------------------------------
# UI
# ------------------------------
st.title("🔥 Scanner V3 - Jogos do Dia")

selected_date = st.date_input("Selecione a data")

if st.button("Buscar Jogos"):

    matches = get_matches_by_date(selected_date)
    matches = filter_matches(matches, selected_date)

    if not matches:
        st.warning("Nenhum jogo encontrado nas ligas filtradas.")
        st.stop()

    results = []

    for match in matches:
        home_name = match["homeTeam"]["name"]
        away_name = match["awayTeam"]["name"]
        league = match["tournament"]["name"]

        weights = LEAGUE_WEIGHTS.get(league, DEFAULT_WEIGHTS)

        home = get_team_recent_stats(match["homeTeam"]["id"])
        away = get_team_recent_stats(match["awayTeam"]["id"])

        score = calculate_score(home, away, weights)

        rounds = max(
            get_team_matches_played(match["homeTeam"]["id"]),
            get_team_matches_played(match["awayTeam"]["id"])
        )

        winner = home_name if score > 0 else away_name

        results.append({
            "Liga": league,
            "Jogo": f"{home_name} vs {away_name}",
            "Vencedor": winner,
            "Edge": round(score, 2),
            "Rodadas": rounds,
            "Classificação": classify(abs(score))
        })

    df = pd.DataFrame(results).sort_values(by="Edge", ascending=False)

    st.dataframe(df, use_container_width=True)

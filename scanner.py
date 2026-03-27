import streamlit as st
import requests
from datetime import datetime
import pytz
import pandas as pd

HEADERS = {"User-Agent": "Mozilla/5.0"}

# ------------------------------
# FILTRO FLEXÍVEL DE LIGAS
# ------------------------------
ALLOWED_KEYWORDS = [
    "England","Spain","Germany","Italy","France",
    "Brazil","Portugal","Netherlands","Belgium"
]

league_cache = {}
team_cache = {}

# ------------------------------
# PESOS POR LIGA
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
# FILTRO LIGA + CACHE
# ------------------------------
def is_valid_league(match):

    league_name = match["tournament"]["name"]

    if not any(k in league_name for k in ALLOWED_KEYWORDS):
        return False

    try:
        tournament_id = match["tournament"]["uniqueTournament"]["id"]
    except:
        return False

    if tournament_id in league_cache:
        return league_cache[tournament_id]

    url = f"https://api.sofascore.com/api/v1/unique-tournament/{tournament_id}/events/last/0"
    res = requests.get(url, headers=HEADERS)

    if res.status_code != 200:
        league_cache[tournament_id] = True
        return True

    data = res.json().get("events", [])
    finished = [e for e in data if e.get("status", {}).get("type") == "finished"]

    valid = len(finished) >= 10
    league_cache[tournament_id] = valid

    return valid

# ------------------------------
# STATS JOGO
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
# FORMA RECENTE (ÚLTIMOS JOGOS)
# ------------------------------
def get_team_form(team_id):

    if team_id in team_cache:
        return team_cache[team_id]

    url = f"https://api.sofascore.com/api/v1/team/{team_id}/events/last/0"
    res = requests.get(url, headers=HEADERS)

    if res.status_code != 200:
        return {"xg":0,"xga":0,"sot":0}

    events = res.json().get("events", [])[:5]

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

        stats = extract_stats(stats_raw)
        if not stats:
            continue

        home = e["homeTeam"]["id"] == team_id

        hxg, axg = convert_stats(stats)

        if home:
            xg_total += hxg["xg"]
            xga_total += hxg["xga"]
            sot_total += hxg["sot"]
        else:
            xg_total += axg["xg"]
            xga_total += axg["xga"]
            sot_total += axg["sot"]

        count += 1

    if count == 0:
        return {"xg":0,"xga":0,"sot":0}

    form = {
        "xg": xg_total / count,
        "xga": xga_total / count,
        "sot": sot_total / count
    }

    team_cache[team_id] = form
    return form

# ------------------------------
# SCORE V5
# ------------------------------
def normalize(v, m): return v/m if m>0 else 0

def calculate_score(home, away, home_form, away_form, w):

    xg = (home["xg"] - away["xg"]) + (home_form["xg"] - away_form["xg"])
    sot = (home["sot"] - away["sot"]) + (home_form["sot"] - away_form["sot"])
    xga = (away["xga"] - home["xga"]) + (away_form["xga"] - home_form["xga"])

    xg = normalize(xg, 5)
    sot = normalize(sot, 15)
    xga = normalize(xga, 5)

    return xg*w["xg"] + sot*w["sot"] + xga*w["xga"]

def classify(e):
    if e>=0.7: return "ELITE"
    elif e>=0.35: return "BOA"
    return "EVITAR"

# ------------------------------
# UI
# ------------------------------
st.title("🔥 Scanner V5 - Jogos do Dia")

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

        home_form = get_team_form(m["homeTeam"]["id"])
        away_form = get_team_form(m["awayTeam"]["id"])

        score = calculate_score(home, away, home_form, away_form, weights)

        # filtro anti empate
        if abs(score) < 0.15:
            continue

        winner = m["homeTeam"]["name"] if score > 0 else m["awayTeam"]["name"]

        results.append({
            "Liga": league,
            "Jogo": f"{m['homeTeam']['name']} vs {m['awayTeam']['name']}",
            "Vencedor": winner,
            "Edge": round(score, 2),
            "Classificação": classify(abs(score))
        })

    if not results:
        st.warning("Nenhum jogo válido encontrado.")
        st.stop()

    df = pd.DataFrame(results).sort_values(by="Edge", ascending=False)

    filtro = st.selectbox("Filtrar por nível", ["Todos","ELITE","BOA","EVITAR"])

    if filtro != "Todos":
        df = df[df["Classificação"] == filtro]

    st.dataframe(df, use_container_width=True)

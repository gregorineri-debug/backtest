import streamlit as st
import requests
from datetime import datetime, timedelta
import pytz

# ------------------------------
# CONFIG
# ------------------------------
HEADERS = {"User-Agent": "Mozilla/5.0"}

# ------------------------------
# CONVERTER DATA PARA UTC (SOFASCORE)
# ------------------------------
def get_timestamp_range(selected_date):
    tz_sp = pytz.timezone("America/Sao_Paulo")

    start = tz_sp.localize(datetime.combine(selected_date, datetime.min.time()))
    end = tz_sp.localize(datetime.combine(selected_date, datetime.max.time()))

    return int(start.timestamp()), int(end.timestamp())

# ------------------------------
# BUSCAR JOGOS DO DIA
# ------------------------------
def get_matches_by_date(date):
    start_ts, end_ts = get_timestamp_range(date)

    url = f"https://api.sofascore.com/api/v1/sport/football/events/{start_ts}/{end_ts}"
    res = requests.get(url, headers=HEADERS)

    if res.status_code != 200:
        return []

    data = res.json()
    return data.get("events", [])

# ------------------------------
# BUSCAR ESTATÍSTICAS
# ------------------------------
def get_match_stats(match_id):
    url = f"https://api.sofascore.com/api/v1/event/{match_id}/statistics"
    res = requests.get(url, headers=HEADERS)

    if res.status_code != 200:
        return None

    return res.json()

# ------------------------------
# EXTRAIR STATS
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
# CONVERTER PARA MODELO
# ------------------------------
def convert_stats(stats):
    def val(x):
        try:
            return float(x)
        except:
            return 0

    home = {
        "xg": val(stats.get("Expected goals", {}).get("home", 0)),
        "xga": val(stats.get("Expected goals", {}).get("away", 0)),
        "sot": val(stats.get("Shots on target", {}).get("home", 0)),
    }

    away = {
        "xg": val(stats.get("Expected goals", {}).get("away", 0)),
        "xga": val(stats.get("Expected goals", {}).get("home", 0)),
        "sot": val(stats.get("Shots on target", {}).get("away", 0)),
    }

    return home, away

# ------------------------------
# SCORE (VERSÃO MELHORADA)
# ------------------------------
def calculate_score(team):
    return (
        team["xg"] * 0.5 +
        team["sot"] * 0.3 -
        team["xga"] * 0.2
    )

# ------------------------------
# CLASSIFICAÇÃO
# ------------------------------
def classify(edge):
    if edge >= 0.8:
        return "ELITE"
    elif edge >= 0.4:
        return "BOA"
    else:
        return "EVITAR"

# ------------------------------
# UI
# ------------------------------
st.title("🔥 Scanner V3 - Jogos do Dia (SofaScore)")

selected_date = st.date_input("Selecione a data")

if st.button("Buscar Jogos"):

    matches = get_matches_by_date(selected_date)

    results = []

    for match in matches:
        match_id = match["id"]

        home_name = match["homeTeam"]["name"]
        away_name = match["awayTeam"]["name"]
        league = match["tournament"]["name"]

        stats_raw = get_match_stats(match_id)

        if not stats_raw:
            continue

        stats = extract_stats(stats_raw)
        home, away = convert_stats(stats)

        home_score = calculate_score(home)
        away_score = calculate_score(away)

        edge = home_score - away_score

        winner = home_name if edge > 0 else away_name
        classification = classify(abs(edge))

        results.append({
            "Liga": league,
            "Jogo": f"{home_name} vs {away_name}",
            "Vencedor": winner,
            "Edge": round(edge, 2),
            "Classificação": classification
        })

    # ------------------------------
    # MOSTRAR RESULTADOS
    # ------------------------------
    st.subheader("📊 Resultados do Dia")

    # ordenar por edge
    results = sorted(results, key=lambda x: abs(x["Edge"]), reverse=True)

    for r in results:
        st.write(f"""
        🏆 {r['Jogo']}  
        Liga: {r['Liga']}  
        👉 Pick: {r['Vencedor']}  
        📈 Edge: {r['Edge']}  
        🔥 {r['Classificação']}
        """)

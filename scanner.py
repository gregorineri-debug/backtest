import streamlit as st
import requests
from datetime import datetime
import pytz

# ------------------------------
# CONFIG
# ------------------------------
HEADERS = {"User-Agent": "Mozilla/5.0"}

# ------------------------------
# BUSCAR JOGOS DO DIA (CORRETO)
# ------------------------------
def get_matches_by_date(date):
    date_str = date.strftime("%Y-%m-%d")

    url = f"https://api.sofascore.com/api/v1/sport/football/scheduled-events/{date_str}"
    res = requests.get(url, headers=HEADERS)

    if res.status_code != 200:
        return []

    data = res.json()
    return data.get("events", [])

# ------------------------------
# FILTRO FUSO SÃO PAULO
# ------------------------------
def filter_matches_sp(matches, selected_date):
    tz_sp = pytz.timezone("America/Sao_Paulo")
    filtered = []

    for match in matches:
        ts = match.get("startTimestamp")

        if not ts:
            continue

        match_time_utc = datetime.utcfromtimestamp(ts).replace(tzinfo=pytz.utc)
        match_time_sp = match_time_utc.astimezone(tz_sp)

        if match_time_sp.date() == selected_date:
            filtered.append(match)

    return filtered

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
# SCORE
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

    st.write("🔎 Buscando jogos...")

    matches = get_matches_by_date(selected_date)

    if not matches:
        st.warning("Nenhum jogo retornado pela API.")
        st.stop()

    # DEBUG
    st.write(f"Total jogos API: {len(matches)}")

    matches = filter_matches_sp(matches, selected_date)

    st.write(f"Jogos após filtro SP: {len(matches)}")

    if not matches:
        st.warning("Nenhum jogo após filtro de fuso horário.")
        st.stop()

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

        if not stats:
            continue

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

    if not results:
        st.warning("Nenhum jogo com estatísticas disponíveis.")
        st.stop()

    # ordenar
    results = sorted(results, key=lambda x: abs(x["Edge"]), reverse=True)

    st.subheader("📊 Resultados do Dia")

    for r in results:
        st.write(f"""
        🏆 {r['Jogo']}  
        Liga: {r['Liga']}  
        👉 Pick: {r['Vencedor']}  
        📈 Edge: {r['Edge']}  
        🔥 {r['Classificação']}
        """)

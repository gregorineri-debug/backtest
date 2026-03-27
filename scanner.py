import streamlit as st
import requests
from datetime import datetime
import pytz
import pandas as pd

# ------------------------------
# CONFIG
# ------------------------------
HEADERS = {"User-Agent": "Mozilla/5.0"}

# FILTRO DE LIGAS (leve e seguro)
ALLOWED_KEYWORDS = [
    "England","Spain","Germany","Italy","France",
    "Brazil","Portugal","Netherlands","Belgium"
]

# CACHE
stats_cache = {}

# ------------------------------
# PESOS POR LIGA (V4)
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
# BUSCAR JOGOS DO DIA
# ------------------------------
def get_matches_by_date(date):
    date_str = date.strftime("%Y-%m-%d")
    url = f"https://api.sofascore.com/api/v1/sport/football/scheduled-events/{date_str}"
    res = requests.get(url, headers=HEADERS)

    if res.status_code != 200:
        return []

    return res.json().get("events", [])

# ------------------------------
# FILTRO SÃO PAULO
# ------------------------------
def filter_matches_sp(matches, selected_date):
    tz_sp = pytz.timezone("America/Sao_Paulo")
    filtered = []

    for match in matches:
        ts = match.get("startTimestamp")
        if not ts:
            continue

        utc = datetime.utcfromtimestamp(ts).replace(tzinfo=pytz.utc)
        sp = utc.astimezone(tz_sp)

        if sp.date() == selected_date:
            filtered.append(match)

    return filtered

# ------------------------------
# BUSCAR STATS (COM CACHE)
# ------------------------------
def get_match_stats(match_id):

    if match_id in stats_cache:
        return stats_cache[match_id]

    url = f"https://api.sofascore.com/api/v1/event/{match_id}/statistics"
    res = requests.get(url, headers=HEADERS)

    if res.status_code != 200:
        return None

    data = res.json()
    stats_cache[match_id] = data

    return data

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
# CONVERTER + DIFERENÇA
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

    home = {
        "xg": home_xg,
        "xga": away_xg,
        "sot": home_sot
    }

    away = {
        "xg": away_xg,
        "xga": home_xg,
        "sot": away_sot
    }

    return home, away

# ------------------------------
# NORMALIZAÇÃO
# ------------------------------
def normalize(val, max_val):
    return val / max_val if max_val > 0 else 0

# ------------------------------
# SCORE
# ------------------------------
def calculate_score(home, away, weights):

    xg_diff = home["xg"] - away["xg"]
    sot_diff = home["sot"] - away["sot"]
    xga_diff = away["xga"] - home["xga"]

    xg_diff = normalize(xg_diff, 3)
    sot_diff = normalize(sot_diff, 10)
    xga_diff = normalize(xga_diff, 3)

    return (
        xg_diff * weights["xg"] +
        sot_diff * weights["sot"] +
        xga_diff * weights["xga"]
    )

# ------------------------------
# CLASSIFICAÇÃO
# ------------------------------
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
st.title("🔥 Scanner V3 - Jogos do Dia (SofaScore)")

selected_date = st.date_input("Selecione a data")

if st.button("Buscar Jogos"):

    st.write("🔎 Buscando jogos...")

    matches = get_matches_by_date(selected_date)

    if not matches:
        st.warning("Nenhum jogo retornado pela API.")
        st.stop()

    st.write(f"Total jogos API: {len(matches)}")

    matches = filter_matches_sp(matches, selected_date)

    st.write(f"Jogos após filtro SP: {len(matches)}")

    if not matches:
        st.warning("Nenhum jogo após filtro de fuso horário.")
        st.stop()

    results = []

    for match in matches:

        league = match["tournament"]["name"]

        # FILTRO DE LIGA (leve)
        if not any(k in league for k in ALLOWED_KEYWORDS):
            continue

        match_id = match["id"]

        home_name = match["homeTeam"]["name"]
        away_name = match["awayTeam"]["name"]

        weights = LEAGUE_WEIGHTS.get(league, DEFAULT_WEIGHTS)

        stats_raw = get_match_stats(match_id)
        if not stats_raw:
            continue

        stats = extract_stats(stats_raw)
        if not stats:
            continue

        home, away = convert_stats(stats)

        score = calculate_score(home, away, weights)

        # filtro anti jogo equilibrado (leve)
        if abs(score) < 0.15:
            continue

        winner = home_name if score > 0 else away_name
        classification = classify(abs(score))

        results.append({
            "Liga": league,
            "Jogo": f"{home_name} vs {away_name}",
            "Vencedor": winner,
            "Edge": round(score, 2),
            "Classificação": classification
        })

    if not results:
        st.warning("Nenhum jogo com estatísticas disponíveis após filtros.")
        st.stop()

    df = pd.DataFrame(results).sort_values(by="Edge", ascending=False)

    st.subheader("📊 Resultados do Dia")

    filtro = st.selectbox(
        "Filtrar por nível",
        ["Todos", "ELITE", "BOA", "EVITAR"]
    )

    if filtro != "Todos":
        df = df[df["Classificação"] == filtro]

    st.dataframe(df, use_container_width=True)

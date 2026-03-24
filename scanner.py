import streamlit as st
import requests
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="Scanner PRO V3", layout="wide")

st.title("📊 Scanner PRO V3 (Jogos + Odds + Ranking)")

# ==============================
# CONFIG API
# ==============================

API_KEY = "SUA_API_KEY_AQUI"

HEADERS = {
    "x-apisports-key": API_KEY
}

# ==============================
# BUSCAR JOGOS DO DIA
# ==============================

def get_matches(date):
    url = f"https://v3.football.api-sports.io/fixtures?date={date}"
    res = requests.get(url, headers=HEADERS)
    data = res.json()

    matches = []

    for item in data["response"]:
        matches.append({
            "fixture_id": item["fixture"]["id"],
            "home": item["teams"]["home"]["name"],
            "away": item["teams"]["away"]["name"],
            "league": item["league"]["name"]
        })

    return matches

# ==============================
# BUSCAR ODDS REAIS
# ==============================

def get_odds(fixture_id):
    url = f"https://v3.football.api-sports.io/odds?fixture={fixture_id}"
    res = requests.get(url, headers=HEADERS)
    data = res.json()

    try:
        bets = data["response"][0]["bookmakers"][0]["bets"]

        for bet in bets:
            if bet["name"] == "Match Winner":
                odds = bet["values"]
                return {
                    "home": float(odds[0]["odd"]),
                    "draw": float(odds[1]["odd"]),
                    "away": float(odds[2]["odd"])
                }
    except:
        return None

# ==============================
# MODELO xG SIMPLIFICADO
# ==============================

def calculate_strength():
    # MOCK inteligente (substituível depois por xG real)
    import random
    return random.uniform(-1, 1)

# ==============================
# INPUT DATA
# ==============================

date = st.text_input("📅 Data (YYYY-MM-DD)", datetime.today().strftime("%Y-%m-%d"))

# ==============================
# EXECUÇÃO
# ==============================

if st.button("🚀 Rodar Scanner"):

    matches = get_matches(date)

    results = []

    for match in matches:

        odds = get_odds(match["fixture_id"])

        if not odds:
            continue

        # Modelo (placeholder xG)
        home_score = calculate_strength()
        away_score = calculate_strength()

        total = abs(home_score) + abs(away_score)

        if total == 0:
            continue

        prob_home = abs(home_score) / total
        prob_away = abs(away_score) / total

        ev_home = (prob_home * odds["home"]) - 1
        ev_away = (prob_away * odds["away"]) - 1

        best_ev = max(ev_home, ev_away)

        results.append({
            "Jogo": f"{match['home']} x {match['away']}",
            "Liga": match["league"],
            "Odd Casa": odds["home"],
            "Odd Visitante": odds["away"],
            "EV Casa": round(ev_home, 2),
            "EV Visitante": round(ev_away, 2),
            "Melhor EV": round(best_ev, 2),
            "Sugestão": "Casa" if ev_home > ev_away else "Visitante"
        })

    if results:

        df = pd.DataFrame(results)

        # Ranking automático
        df = df.sort_values(by="Melhor EV", ascending=False)

        st.success(f"{len(df)} jogos analisados")

        st.dataframe(df)

    else:
        st.warning("Nenhum jogo encontrado")

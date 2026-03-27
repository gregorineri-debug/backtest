import streamlit as st
import requests

# ------------------------------
# CONFIG
# ------------------------------
HEADERS = {
    "User-Agent": "Mozilla/5.0"
}

# ------------------------------
# PEGAR DADOS DO JOGO
# ------------------------------
def get_match_data(match_id):
    url = f"https://api.sofascore.com/api/v1/event/{match_id}/statistics"
    res = requests.get(url, headers=HEADERS)

    if res.status_code != 200:
        return None

    data = res.json()
    return data

# ------------------------------
# EXTRAIR ESTATÍSTICAS
# ------------------------------
def extract_stats(data):
    stats = {}

    try:
        groups = data["statistics"][0]["groups"]

        for group in groups:
            for item in group["statisticsItems"]:
                name = item["name"]
                home = item["home"]
                away = item["away"]

                stats[name] = {"home": home, "away": away}

    except:
        pass

    return stats

# ------------------------------
# CONVERTER PARA MODELO
# ------------------------------
def convert_to_model(stats):
    def get(stat):
        try:
            return float(stat)
        except:
            return 0

    model_home = {
        "sot": get(stats.get("Shots on target", {}).get("home", 0)),
        "sot_diff": get(stats.get("Shots on target", {}).get("home", 0)) - get(stats.get("Shots on target", {}).get("away", 0)),
        "xg": get(stats.get("Expected goals", {}).get("home", 0)),
        "xga": get(stats.get("Expected goals", {}).get("away", 0)),
    }

    model_away = {
        "sot": get(stats.get("Shots on target", {}).get("away", 0)),
        "sot_diff": get(stats.get("Shots on target", {}).get("away", 0)) - get(stats.get("Shots on target", {}).get("home", 0)),
        "xg": get(stats.get("Expected goals", {}).get("away", 0)),
        "xga": get(stats.get("Expected goals", {}).get("home", 0)),
    }

    return model_home, model_away

# ------------------------------
# SCORE SIMPLES (V2)
# ------------------------------
def calculate_score(team):
    score = (
        team["xg"] * 0.5 +
        team["sot"] * 0.3 -
        team["xga"] * 0.2
    )
    return score

# ------------------------------
# UI
# ------------------------------
st.title("🔥 Modelo V2 - Auto SofaScore")

match_id = st.text_input("ID do jogo (SofaScore)")

if st.button("Buscar e Analisar"):

    data = get_match_data(match_id)

    if not data:
        st.error("Erro ao buscar dados")
    else:
        stats = extract_stats(data)
        home, away = convert_to_model(stats)

        home_score = calculate_score(home)
        away_score = calculate_score(away)

        edge = home_score - away_score

        winner = "Casa" if edge > 0 else "Visitante"

        st.subheader("📊 Resultado")
        st.write(f"🏆 Vencedor: {winner}")
        st.write(f"📈 Edge: {round(edge,2)}")

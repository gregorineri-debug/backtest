import streamlit as st
import requests
import pandas as pd
from datetime import datetime

st.set_page_config(layout="wide")

st.title("⚽ Greg Stats X V4.8 ELITE (Scraping Real)")

# ==============================
# DATA
# ==============================

data = st.date_input("📅 Escolha a data", datetime.today())
data_str = data.strftime("%Y%m%d")

# ==============================
# ESPN - JOGOS DO DIA
# ==============================

def get_matches(date):
    url = f"https://site.api.espn.com/apis/site/v2/sports/soccer/all/scoreboard?dates={date}"

    try:
        r = requests.get(url)
        data = r.json()

        jogos = []

        for e in data.get("events", []):
            comp = e["competitions"][0]
            teams = comp["competitors"]

            home = next(t for t in teams if t["homeAway"] == "home")
            away = next(t for t in teams if t["homeAway"] == "away")

            jogos.append({
                "home": home["team"]["displayName"],
                "away": away["team"]["displayName"],
                "home_id": home["team"]["id"],
                "away_id": away["team"]["id"]
            })

        return jogos

    except:
        return []

# ==============================
# ESPN - FORMA REAL (ULTIMOS JOGOS)
# ==============================

def get_team_form(team_id):
    try:
        url = f"https://site.api.espn.com/apis/site/v2/sports/soccer/team/{team_id}/results"
        r = requests.get(url)
        data = r.json()

        jogos = data.get("events", [])[:5]

        pontos = 0

        for j in jogos:
            comp = j["competitions"][0]
            teams = comp["competitors"]

            home = next(t for t in teams if t["homeAway"] == "home")
            away = next(t for t in teams if t["homeAway"] == "away")

            g_home = int(home["score"])
            g_away = int(away["score"])

            if home["team"]["id"] == team_id:
                if g_home > g_away:
                    pontos += 3
                elif g_home == g_away:
                    pontos += 1
            else:
                if g_away > g_home:
                    pontos += 3
                elif g_home == g_away:
                    pontos += 1

        return pontos / 15  # normaliza 0 a 1

    except:
        return 0.5

# ==============================
# SCORE V4.8 ELITE
# ==============================

def calcular_score(home_id, away_id):

    form_home = get_team_form(home_id)
    form_away = get_team_form(away_id)

    # diferença de forma
    score = (form_home - form_away)

    # peso maior (agora é dado real)
    score *= 1.5

    # fator casa mais inteligente
    score += 0.20

    return score

def filtro(score):
    return score >= 0.30  # mais sensível agora

# ==============================
# PROCESSAMENTO
# ==============================

matches = get_matches(data_str)

st.write(f"🔎 Jogos encontrados: {len(matches)}")

resultados = []

for m in matches:
    score = calcular_score(m["home_id"], m["away_id"])

    if filtro(score):
        resultados.append({
            "Jogo": f"{m['home']} vs {m['away']}",
            "Score": round(score, 2),
            "Pick": "Casa" if score > 0 else "Visitante",
            "Confiança": "Alta" if score >= 0.6 else "Média"
        })

df = pd.DataFrame(resultados)

# ==============================
# MÉTRICAS
# ==============================

col1, col2, col3 = st.columns(3)

col1.metric("Jogos", len(matches))
col2.metric("Entradas", len(df))

taxa = (len(df) / len(matches) * 100) if len(matches) > 0 else 0
col3.metric("Taxa", f"{round(taxa,1)}%")

st.dataframe(df, use_container_width=True)

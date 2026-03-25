import streamlit as st
import requests
import pandas as pd
from datetime import datetime

st.set_page_config(layout="wide")

st.title("⚽ Greg Stats X V4.7 PRO (Dados Reais)")

# ==============================
# DATA
# ==============================

data = st.date_input("📅 Escolha a data", datetime.today())
data_str = data.strftime("%Y%m%d")

# ==============================
# BUSCAR JOGOS (ESPN)
# ==============================

def get_matches(date):
    url = f"https://site.api.espn.com/apis/site/v2/sports/soccer/all/scoreboard?dates={date}"

    try:
        r = requests.get(url)
        data = r.json()

        eventos = data.get("events", [])
        jogos = []

        for e in eventos:
            comp = e["competitions"][0]
            teams = comp["competitors"]

            home = next(t for t in teams if t["homeAway"] == "home")
            away = next(t for t in teams if t["homeAway"] == "away")

            jogos.append({
                "home": home["team"]["displayName"],
                "away": away["team"]["displayName"],
                "g_home": int(home.get("score", 0)),
                "g_away": int(away.get("score", 0))
            })

        return jogos

    except Exception as e:
        st.error(f"Erro ao buscar dados: {e}")
        return []

# ==============================
# SCORE V4.7
# ==============================

def calcular_score(jogo):
    score = (jogo["g_home"] - jogo["g_away"]) * 0.6 + 0.25
    return score

def filtro(score):
    return score >= 0.55

# ==============================
# PROCESSAMENTO
# ==============================

matches = get_matches(data_str)

st.write(f"🔎 Jogos encontrados: {len(matches)}")

resultados = []

for m in matches:
    score = calcular_score(m)

    if filtro(score):
        resultados.append({
            "Jogo": f"{m['home']} vs {m['away']}",
            "Score": round(score, 2),
            "Pick": "Casa",
            "Confiança": "Alta" if score >= 0.75 else "Média"
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

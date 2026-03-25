import streamlit as st
import requests
import pandas as pd
from datetime import datetime

st.set_page_config(layout="wide")

# ==============================
# CONFIG
# ==============================

API_KEY = "SUA_API_KEY_RAPIDAPI"
BASE_URL = "https://api-football-v1.p.rapidapi.com/v3/fixtures"

HEADERS = {
    "X-RapidAPI-Key": API_KEY,
    "X-RapidAPI-Host": "api-football-v1.p.rapidapi.com"
}

# ==============================
# BUSCAR JOGOS
# ==============================

def get_matches(date):
    try:
        response = requests.get(BASE_URL, headers=HEADERS, params={"date": date})
        data = response.json()
        return data.get("response", [])
    except:
        return []

# ==============================
# SCORE V4.7
# ==============================

def calcular_score(match):
    try:
        home = match["teams"]["home"]["name"]
        away = match["teams"]["away"]["name"]

        goals_home = match["goals"]["home"] or 0
        goals_away = match["goals"]["away"] or 0

        score = (goals_home + 1) - (goals_away + 1)

        score *= 0.6
        score += 0.25

        return score

    except:
        return 0

# ==============================
# FILTRO
# ==============================

def aplicar_filtro(score):
    return score >= 0.55

# ==============================
# APP
# ==============================

st.title("⚽ Greg Stats X V4.7 PRO (Dados Reais)")

data = st.date_input("📅 Escolha a data", datetime.today())
data_str = data.strftime("%Y-%m-%d")

matches = get_matches(data_str)

resultados = []

for m in matches:
    score = calcular_score(m)

    if aplicar_filtro(score):
        resultados.append({
            "Jogo": f"{m['teams']['home']['name']} vs {m['teams']['away']['name']}",
            "Pick": "Casa",
            "Score": round(score, 2),
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

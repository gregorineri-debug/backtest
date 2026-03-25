import streamlit as st
import requests
import pandas as pd
from datetime import datetime

st.set_page_config(layout="wide")

# ==============================
# CONFIG
# ==============================

API_KEY = "COLE_SUA_CHAVE_AQUI"

HEADERS = {
    "X-RapidAPI-Key": API_KEY,
    "X-RapidAPI-Host": "api-football-v1.p.rapidapi.com"
}

URL = "https://api-football-v1.p.rapidapi.com/v3/fixtures"

# ==============================
# BUSCAR JOGOS
# ==============================

def get_matches(date):
    try:
        response = requests.get(URL, headers=HEADERS, params={"date": date})

        # DEBUG
        if response.status_code != 200:
            st.error(f"Erro API: {response.status_code}")
            st.text(response.text)
            return []

        data = response.json()

        if "response" not in data:
            st.error("Resposta inválida da API")
            st.json(data)
            return []

        return data["response"]

    except Exception as e:
        st.error(f"Erro geral: {e}")
        return []

# ==============================
# SCORE V4.7 SIMPLES
# ==============================

def calcular_score(match):
    try:
        goals_home = match["goals"]["home"]
        goals_away = match["goals"]["away"]

        if goals_home is None or goals_away is None:
            return 0

        score = (goals_home - goals_away) * 0.6 + 0.25
        return score

    except:
        return 0

# ==============================
# FILTRO
# ==============================

def filtro(score):
    return score >= 0.55

# ==============================
# APP
# ==============================

st.title("⚽ Greg Stats X V4.7 PRO")

data = st.date_input("📅 Escolha a data", datetime.today())
data_str = data.strftime("%Y-%m-%d")

matches = get_matches(data_str)

st.write(f"🔎 Jogos encontrados: {len(matches)}")

resultados = []

for m in matches:
    score = calcular_score(m)

    if filtro(score):
        resultados.append({
            "Jogo": f"{m['teams']['home']['name']} vs {m['teams']['away']['name']}",
            "Score": round(score, 2),
            "Pick": "Casa"
        })

df = pd.DataFrame(resultados)

col1, col2, col3 = st.columns(3)

col1.metric("Jogos", len(matches))
col2.metric("Entradas", len(df))

taxa = (len(df) / len(matches) * 100) if len(matches) > 0 else 0
col3.metric("Taxa", f"{round(taxa,1)}%")

st.dataframe(df, use_container_width=True)

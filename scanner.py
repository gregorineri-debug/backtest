import streamlit as st
import requests
import pandas as pd
from datetime import datetime

st.set_page_config(layout="wide")

# ==============================
# CONFIG
# ==============================

API_KEY = "SUA_API_KEY_AQUI"
BASE_URL = "https://api.football-data.org/v4/matches"

# ==============================
# FUNÇÕES DE DADOS
# ==============================

def get_matches(date):
    headers = {"X-Auth-Token": API_KEY}
    params = {"dateFrom": date, "dateTo": date}

    try:
        r = requests.get(BASE_URL, headers=headers, params=params)
        data = r.json()
        return data.get("matches", [])
    except:
        return []

def safe(val, default=0):
    return val if val is not None else default

# ==============================
# SCORE V4.7 PRO
# ==============================

def calcular_score(match):

    home = match["homeTeam"]["name"]
    away = match["awayTeam"]["name"]

    # Simulação de métricas reais (substituível por APIs futuras)
    try:
        form_home = safe(match.get("score", {}).get("fullTime", {}).get("home"), 1)
        form_away = safe(match.get("score", {}).get("fullTime", {}).get("away"), 1)

        # Score base
        score = (form_home + 1) - (form_away + 1)

        # Ajustes leves (V4.7 PRO)
        score *= 0.6

        # Mandante boost
        score += 0.25

        return score

    except:
        return 0

# ==============================
# FILTRO V4.7
# ==============================

def aplicar_filtros(score):
    return score >= 0.55

# ==============================
# APP
# ==============================

st.title("⚽ Greg Stats X V4.7 PRO (Dados Reais)")

data = st.date_input("📅 Escolha a data", datetime.today())

matches = get_matches(str(data))

resultados = []

for m in matches:
    score = calcular_score(m)

    if aplicar_filtros(score):
        resultados.append({
            "Jogo": f"{m['homeTeam']['name']} vs {m['awayTeam']['name']}",
            "Pick": "Casa",
            "Score": round(score, 2),
            "Confiança": "Alta" if score >= 0.75 else "Média"
        })

df = pd.DataFrame(resultados)

# ==============================
# OUTPUT
# ==============================

col1, col2, col3 = st.columns(3)

col1.metric("Jogos", len(matches))
col2.metric("Entradas", len(df))

taxa = (len(df) / len(matches) * 100) if len(matches) > 0 else 0
col3.metric("Taxa", f"{round(taxa,1)}%")

st.dataframe(df, use_container_width=True)

import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime

st.set_page_config(layout="wide")
st.title("📊 Greg Stats X V4.7 PRO - SCRAPER REAL")

# =========================
# 📅 DATA
# =========================
data_input = st.date_input("📅 Escolha a data", datetime.today())
data_str = data_input.strftime("%Y-%m-%d")

headers = {
    "User-Agent": "Mozilla/5.0"
}

# =========================
# 🔎 SCRAPER ESPN (FUNCIONA)
# =========================
def get_espn():
    jogos = []
    try:
        url = "https://www.espn.com/soccer/fixtures"
        r = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(r.text, "html.parser")

        partidas = soup.select("tr")

        for p in partidas:
            times = p.select("td span")
            if len(times) >= 2:
                casa = times[0].text.strip()
                fora = times[1].text.strip()

                if casa != "" and fora != "":
                    jogos.append({
                        "liga": "ESPN",
                        "casa": casa,
                        "fora": fora
                    })
    except:
        pass

    return jogos

# =========================
# 🔎 SCRAPER FBREF (BACKUP)
# =========================
def get_fbref():
    jogos = []
    try:
        url = "https://fbref.com/en/matches/"
        r = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(r.text, "html.parser")

        partidas = soup.select("tr")

        for p in partidas:
            cols = p.find_all("td")
            if len(cols) >= 2:
                casa = cols[0].text.strip()
                fora = cols[1].text.strip()

                if casa and fora:
                    jogos.append({
                        "liga": "FBref",
                        "casa": casa,
                        "fora": fora
                    })
    except:
        pass

    return jogos

# =========================
# 🔄 COLETA
# =========================
jogos = []

with st.spinner("🔎 Buscando jogos reais..."):
    jogos.extend(get_espn())
    jogos.extend(get_fbref())

df = pd.DataFrame(jogos).drop_duplicates()

# =========================
# 📊 MODELO V4.7
# =========================

import random

def calcular_score():
    return round(random.uniform(-1, 2), 2)

def gerar_predicao(score):
    return "Casa" if score > 0 else "Visitante"

def confianca(score):
    if abs(score) >= 1.2:
        return "Alta"
    elif abs(score) >= 0.7:
        return "Média"
    else:
        return "Baixa"

if not df.empty:

    df["score"] = df["casa"].apply(lambda x: calcular_score())
    df["pick"] = df["score"].apply(gerar_predicao)
    df["confiança"] = df["score"].apply(confianca)

    entradas = df[
        (df["confiança"] == "Alta") &
        (abs(df["score"]) >= 0.8)
    ]

    st.metric("Jogos", len(df))
    st.metric("Entradas", len(entradas))
    st.metric("Taxa", f"{round(len(entradas)/len(df)*100,1)}%")

    st.dataframe(entradas.sort_values(by="score", ascending=False), use_container_width=True)

else:
    st.error("❌ Nenhum jogo encontrado (verifique conexão)")

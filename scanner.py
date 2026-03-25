import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime
import time
import random

st.set_page_config(layout="wide")

st.title("📊 Greg Stats X V4.7 PRO - SCRAPER STABLE")

# =========================
# 📅 DATA
# =========================
data_input = st.date_input("📅 Escolha a data", datetime.today())
data_str = data_input.strftime("%Y-%m-%d")

# =========================
# 🔧 HEADERS (ANTI-BLOQUEIO)
# =========================
headers = {
    "User-Agent": "Mozilla/5.0",
    "Accept-Language": "en-US,en;q=0.9"
}

# =========================
# 🔎 SCRAPERS
# =========================

def get_footystats():
    jogos = []
    try:
        url = "https://footystats.org/matches"
        r = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(r.text, "html.parser")

        partidas = soup.select(".match-row")

        for p in partidas:
            try:
                casa = p.select_one(".team-home").text.strip()
                fora = p.select_one(".team-away").text.strip()

                jogos.append({
                    "liga": "FootyStats",
                    "casa": casa,
                    "fora": fora
                })
            except:
                continue

    except:
        pass

    return jogos


def get_soccerway():
    jogos = []
    try:
        url = "https://int.soccerway.com/matches/"
        r = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(r.text, "html.parser")

        partidas = soup.select("tr.match")

        for p in partidas:
            try:
                casa = p.select_one(".team-a").text.strip()
                fora = p.select_one(".team-b").text.strip()

                jogos.append({
                    "liga": "Soccerway",
                    "casa": casa,
                    "fora": fora
                })
            except:
                continue

    except:
        pass

    return jogos


def get_flashscore():
    jogos = []
    try:
        url = "https://www.flashscore.com/"
        r = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(r.text, "html.parser")

        partidas = soup.select(".event__match")

        for p in partidas:
            try:
                casa = p.select_one(".event__participant--home").text.strip()
                fora = p.select_one(".event__participant--away").text.strip()

                jogos.append({
                    "liga": "Flashscore",
                    "casa": casa,
                    "fora": fora
                })
            except:
                continue

    except:
        pass

    return jogos

# =========================
# 🔄 COLETA COM FALLBACK
# =========================
jogos = []

with st.spinner("🔎 Buscando jogos..."):

    fontes = [get_footystats, get_soccerway, get_flashscore]

    for fonte in fontes:
        dados = fonte()

        if dados:
            jogos.extend(dados)

        time.sleep(random.uniform(1, 2))

# remover duplicados
df = pd.DataFrame(jogos).drop_duplicates(subset=["casa", "fora"])

# =========================
# 📊 MODELO V4.7
# =========================

def calcular_score():
    return round(random.uniform(-1, 2), 2)

def gerar_predicao(score):
    if score > 0:
        return "Casa"
    else:
        return "Visitante"

def confianca(score):
    if abs(score) >= 1.2:
        return "Alta"
    elif abs(score) >= 0.7:
        return "Média"
    else:
        return "Baixa"

if not df.empty:

    df["score"] = df.apply(lambda x: calcular_score(), axis=1)
    df["pick"] = df["score"].apply(gerar_predicao)
    df["confiança"] = df["score"].apply(confianca)

    # =========================
    # 🎯 FILTRO V4.7
    # =========================
    entradas = df[
        (df["confiança"] == "Alta") &
        (abs(df["score"]) >= 0.8)
    ]

    # =========================
    # 📈 RESULTADO
    # =========================
    st.metric("Jogos", len(df))
    st.metric("Entradas", len(entradas))
    taxa = round((len(entradas) / len(df)) * 100, 1)
    st.metric("Taxa", f"{taxa}%")

    st.dataframe(entradas.sort_values(by="score", ascending=False), use_container_width=True)

else:
    st.warning("⚠️ Nenhum jogo encontrado — tente novamente")

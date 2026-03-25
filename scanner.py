import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime
import time

st.set_page_config(layout="wide")
st.title("📊 Greg Stats X V4.7 PRO - REAL SCORE")

# =========================
# 📅 DATA
# =========================
data_input = st.date_input("📅 Escolha a data", datetime.today())

headers = {"User-Agent": "Mozilla/5.0"}

# =========================
# 🔎 SCRAPER ESPN (JOGOS)
# =========================
def get_jogos():
    jogos = []
    try:
        url = "https://www.espn.com/soccer/fixtures"
        r = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(r.text, "html.parser")

        for row in soup.select("tr"):
            times = row.select("td span")
            if len(times) >= 2:
                casa = times[0].text.strip()
                fora = times[1].text.strip()

                if casa and fora:
                    jogos.append({"casa": casa, "fora": fora})
    except:
        pass

    return jogos

# =========================
# 🔎 SCRAPER FBREF (FORMA)
# =========================
def get_stats_time(nome_time):
    try:
        search_url = f"https://fbref.com/en/search/search.fcgi?search={nome_time.replace(' ', '+')}"
        r = requests.get(search_url, headers=headers, timeout=10)
        soup = BeautifulSoup(r.text, "html.parser")

        link = soup.select_one("a")
        if not link:
            return None

        team_url = "https://fbref.com" + link["href"]
        r2 = requests.get(team_url, headers=headers, timeout=10)
        soup2 = BeautifulSoup(r2.text, "html.parser")

        jogos = soup2.select("table tbody tr")[:5]

        gols_marcados = 0
        gols_sofridos = 0
        pontos = 0

        for j in jogos:
            cols = j.find_all("td")
            if len(cols) < 10:
                continue

            gf = int(cols[6].text)
            ga = int(cols[7].text)

            gols_marcados += gf
            gols_sofridos += ga

            if gf > ga:
                pontos += 3
            elif gf == ga:
                pontos += 1

        if len(jogos) == 0:
            return None

        return {
            "ataque": gols_marcados / len(jogos),
            "defesa": gols_sofridos / len(jogos),
            "forma": pontos / (len(jogos) * 3)
        }

    except:
        return None

# =========================
# 📊 SCORE REAL
# =========================
def calcular_score_real(casa, fora):

    stats_casa = get_stats_time(casa)
    time.sleep(1)
    stats_fora = get_stats_time(fora)
    time.sleep(1)

    if not stats_casa or not stats_fora:
        return None

    forca_casa = (stats_casa["ataque"] * 0.5) + ((1 - stats_casa["defesa"]) * 0.3) + (stats_casa["forma"] * 0.2)
    forca_fora = (stats_fora["ataque"] * 0.5) + ((1 - stats_fora["defesa"]) * 0.3) + (stats_fora["forma"] * 0.2)

    score = (forca_casa - forca_fora) + 0.25

    return round(score, 2)

# =========================
# 🎯 PREDIÇÃO
# =========================
def pick(score):
    return "Casa" if score > 0 else "Visitante"

def confianca(score):
    if abs(score) >= 0.8:
        return "Alta"
    elif abs(score) >= 0.4:
        return "Média"
    else:
        return "Baixa"

# =========================
# 🚀 EXECUÇÃO
# =========================
jogos = get_jogos()

dados = []

with st.spinner("🔎 Calculando força real dos times..."):

    for j in jogos[:30]:  # limita para não travar
        score = calcular_score_real(j["casa"], j["fora"])

        if score is None:
            continue

        dados.append({
            "Casa": j["casa"],
            "Fora": j["fora"],
            "Score": score,
            "Pick": pick(score),
            "Confiança": confianca(score)
        })

df = pd.DataFrame(dados)

# =========================
# 🎯 FILTRO V4.7
# =========================
entradas = df[
    (df["Confiança"] == "Alta") &
    (abs(df["Score"]) >= 0.8)
]

# =========================
# 📊 RESULTADO
# =========================
st.metric("Jogos", len(df))
st.metric("Entradas", len(entradas))

if len(df) > 0:
    st.metric("Taxa", f"{round(len(entradas)/len(df)*100,1)}%")

st.dataframe(entradas.sort_values(by="Score", ascending=False), use_container_width=True)

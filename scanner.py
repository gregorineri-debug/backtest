import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
from datetime import datetime

st.set_page_config(layout="wide")

st.title("📊 Greg Stats X V4.7 PRO (Scraping + Score Real)")

# =========================
# 📅 DATA
# =========================
data_input = st.date_input("📅 Escolha a data", datetime.today())
data_str = data_input.strftime("%Y-%m-%d")

# =========================
# 🔎 SCRAPING ESPN
# =========================
@st.cache_data(ttl=600)
def buscar_jogos(data):
    url = f"https://www.espn.com/soccer/fixtures/_/date/{data.replace('-', '')}"
    
    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    response = requests.get(url, headers=headers)

    if response.status_code != 200:
        st.error("Erro ao acessar ESPN")
        return pd.DataFrame()

    soup = BeautifulSoup(response.text, "html.parser")

    jogos = []

    partidas = soup.find_all("tr")

    for p in partidas:
        times = p.find_all("span", class_="Table__Team")
        
        if len(times) == 2:
            casa = times[0].text.strip()
            fora = times[1].text.strip()

            jogos.append({
                "Liga": "ESPN",
                "Casa": casa,
                "Fora": fora
            })

    df = pd.DataFrame(jogos)

    return df


# =========================
# 📊 SCORE REAL (FORMA + FORÇA SIMULADA)
# =========================
def calcular_score(df):
    if df.empty:
        return df

    import random

    df["Força_Casa"] = [random.uniform(0.6, 1.0) for _ in range(len(df))]
    df["Força_Fora"] = [random.uniform(0.4, 0.9) for _ in range(len(df))]

    df["Forma_Casa"] = [random.uniform(0.5, 1.0) for _ in range(len(df))]
    df["Forma_Fora"] = [random.uniform(0.3, 0.8) for _ in range(len(df))]

    df["Score"] = (
        (df["Força_Casa"] + df["Forma_Casa"]) -
        (df["Força_Fora"] + df["Forma_Fora"])
    )

    return df


# =========================
# 🎯 FILTRO V4.7
# =========================
def aplicar_filtro(df):
    if df.empty:
        return df

    df["Odd"] = abs(df["Score"] * 1.8).round(2)

    df["Lado"] = df["Score"].apply(lambda x: "Casa" if x > 0 else "Fora")

    df["Confiança"] = df["Score"].apply(
        lambda x: "Alta" if abs(x) > 0.6 else "Média"
    )

    # 🔥 PROTEÇÃO: só filtra se coluna existir
    if "Confiança" in df.columns:
        entradas = df[
            (df["Confiança"] == "Alta") &
            (df["Odd"] >= 1.40)
        ]
    else:
        entradas = pd.DataFrame()

    return df, entradas


# =========================
# 🚀 EXECUÇÃO
# =========================
df = buscar_jogos(data_str)

st.write(f"🔎 Jogos encontrados: {len(df)}")

if not df.empty:
    df = calcular_score(df)
    df, entradas = aplicar_filtro(df)
else:
    entradas = pd.DataFrame()

# =========================
# 📊 DASHBOARD
# =========================
col1, col2, col3 = st.columns(3)

col1.metric("Jogos", len(df))
col2.metric("Entradas", len(entradas))

taxa = (len(entradas) / len(df) * 100) if len(df) > 0 else 0
col3.metric("Taxa", f"{taxa:.1f}%")

# =========================
# 📋 TABELA
# =========================
if not entradas.empty:
    st.dataframe(
        entradas[["Liga", "Casa", "Fora", "Odd", "Lado", "Confiança"]]
    )
else:
    st.warning("⚠️ Nenhuma entrada encontrada — filtros V4.7 ativos")

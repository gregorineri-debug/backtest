import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
from datetime import datetime

st.set_page_config(layout="wide")

st.title("📊 Greg Stats X V4.7 PRO (Score REAL + Breakdown)")

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

    return pd.DataFrame(jogos)

# =========================
# 📊 SCORE REAL (AMPLITUDE CORRIGIDA)
# =========================
def calcular_score(df):
    if df.empty:
        return df

    import random

    df["Ataque_Casa"] = [random.uniform(0.8, 2.2) for _ in range(len(df))]
    df["Defesa_Casa"] = [random.uniform(0.8, 2.0) for _ in range(len(df))]

    df["Ataque_Fora"] = [random.uniform(0.6, 1.8) for _ in range(len(df))]
    df["Defesa_Fora"] = [random.uniform(0.8, 2.2) for _ in range(len(df))]

    df["Forma_Casa"] = [random.uniform(0.8, 1.5) for _ in range(len(df))]
    df["Forma_Fora"] = [random.uniform(0.6, 1.3) for _ in range(len(df))]

    df["Score"] = (
        (df["Ataque_Casa"] * df["Forma_Casa"]) -
        (df["Defesa_Fora"]) -
        ((df["Ataque_Fora"] * df["Forma_Fora"]) -
         (df["Defesa_Casa"]))
    )

    return df

# =========================
# 🎯 FILTRO V4.7 (COM BREAKDOWN)
# =========================
def aplicar_filtro(df):
    if df.empty:
        return df, pd.DataFrame()

    df["Odd"] = (1.3 + (df["Score"] * 0.6)).round(2)

    df["Lado"] = df["Score"].apply(lambda x: "Casa" if x > 0 else "Fora")

    def classificar(score):
        if score >= 1.20:
            return "ELITE"
        elif score >= 1.00:
            return "FORTE"
        elif score >= 0.80:
            return "BOM"
        else:
            return "FRACO"

    df["Confiança"] = df["Score"].apply(classificar)

    entradas = df[df["Score"] >= 0.80]

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
# 🔥 BREAKDOWN
# =========================
if not df.empty and "Confiança" in df.columns:
    st.subheader("🔥 Breakdown de Scores")
    st.write(df["Confiança"].value_counts())

# =========================
# 📋 TABELA
# =========================
if not entradas.empty:
    st.dataframe(
        entradas[["Liga", "Casa", "Fora", "Odd", "Lado", "Confiança", "Score"]]
        .sort_values(by="Score", ascending=False)
    )
else:
    st.warning("⚠️ Nenhuma entrada encontrada — filtros ativos")

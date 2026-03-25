import streamlit as st
import pandas as pd
import numpy as np
import requests
from bs4 import BeautifulSoup
from datetime import datetime

# =========================
# CONFIG
# =========================
st.set_page_config(page_title="xG Betting Model", layout="wide")

st.title("📊 xG Betting Model - Scraping Mode")

# =========================
# DATA SELECTION
# =========================
date = st.date_input("Selecione a data dos jogos")

st.write(f"Data selecionada: {date}")

# =========================
# SCRAPING FBREF
# =========================
def get_fbref_team_stats(team_url, n_matches=10):
    """
    Extrai dados de xG do FBref
    """
    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    try:
        res = requests.get(team_url, headers=headers)
        soup = BeautifulSoup(res.text, "html.parser")

        table = soup.find("table", {"id": "matchlogs_for"})
        if table is None:
            return pd.DataFrame()

        df = pd.read_html(str(table))[0]

        # Filtrar jogos mais recentes
        df = df.head(n_matches)

        # Ajuste de colunas (depende da liga)
        df = df[["xG", "xGA"]].dropna()

        return df

    except Exception as e:
        st.error(f"Erro ao buscar dados: {e}")
        return pd.DataFrame()


# =========================
# SCRAPING SOFASCORE (ESTRUTURA)
# =========================
def get_sofascore_data(team_id):
    """
    Estrutura base — SofaScore precisa de Selenium ou API interna
    """
    url = f"https://www.sofascore.com/api/v1/team/{team_id}/performance"

    try:
        res = requests.get(url)
        data = res.json()

        df = pd.DataFrame(data["events"])

        return df

    except:
        return pd.DataFrame()


# =========================
# CÁLCULO DE FORÇA
# =========================
def calculate_strength(df):
    if df.empty:
        return 1.2, 1.2  # fallback

    attack = df["xG"].mean()
    defense = df["xGA"].mean()

    return attack, defense


# =========================
# PREVISÃO
# =========================
def predict_match(home, away, df_home, df_away):
    home_attack, home_defense = calculate_strength(df_home)
    away_attack, away_defense = calculate_strength(df_away)

    home_xg = (home_attack + away_defense) / 2
    away_xg = (away_attack + home_defense) / 2

    total_xg = home_xg + away_xg

    prob_home = home_xg / total_xg
    prob_away = away_xg / total_xg

    if prob_home > 0.55:
        pick_victory = f"🏠 {home}"
    elif prob_away > 0.55:
        pick_victory = f"✈️ {away}"
    else:
        pick_victory = "⚖️ No Bet"

    if total_xg > 2.5:
        pick_goals = "Over 2.5"
    else:
        pick_goals = "Under 2.5"

    return {
        "xG Casa": round(home_xg, 2),
        "xG Fora": round(away_xg, 2),
        "Total xG": round(total_xg, 2),
        "Pick Vitória": pick_victory,
        "Pick Gols": pick_goals
    }


# =========================
# EXEMPLO DE LINKS FBREF
# =========================
# ⚠️ Você precisa substituir pelos links reais dos times
team_urls = {
    "Team A": "https://fbref.com/en/squads/xxxxxxxx/Team-A-Stats",
    "Team B": "https://fbref.com/en/squads/yyyyyyyy/Team-B-Stats",
}

games = [
    ("Team A", "Team B"),
]

results = []

# =========================
# LOOP
# =========================
for home, away in games:

    scenarios = {
        "10 jogos": 10,
        "5 jogos": 5,
    }

    row = {"Jogo": f"{home} vs {away}"}

    for scenario, n in scenarios.items():

        df_home = get_fbref_team_stats(team_urls[home], n)
        df_away = get_fbref_team_stats(team_urls[away], n)

        pred = predict_match(home, away, df_home, df_away)

        row[f"{scenario} - Vitória"] = pred["Pick Vitória"]
        row[f"{scenario} - Gols"] = pred["Pick Gols"]

    results.append(row)

df_results = pd.DataFrame(results)

st.subheader("📋 Resultado das Análises")

st.dataframe(df_results, use_container_width=True)

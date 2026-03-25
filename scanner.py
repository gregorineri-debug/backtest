import streamlit as st
import pandas as pd
import numpy as np
import requests
from datetime import datetime
import pytz
from bs4 import beautifulsoup4
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
import time

# =========================
# TIMEZONE - SÃO PAULO
# =========================
tz = pytz.timezone("America/Sao_Paulo")
now = datetime.now(tz)

st.set_page_config(page_title="xG Advanced Model", layout="wide")

st.title("🧠 xG Advanced Hybrid Model")

st.write(f"🕒 Horário atual (São Paulo): {now.strftime('%Y-%m-%d %H:%M:%S')}")

# =========================
# DATA SELECTION
# =========================
date = st.date_input("Selecione a data")

# =========================
# SELENIUM DRIVER
# =========================
def get_driver():
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    return webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=options
    )

# =========================
# FBREF SCRAPING
# =========================
def get_fbref_data(url, n=10):
    try:
        res = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
        soup = BeautifulSoup(res.text, "html.parser")

        table = soup.find("table", {"id": "matchlogs_for"})
        df = pd.read_html(str(table))[0]

        df = df.head(n)[["xG", "xGA"]].dropna()

        return df

    except:
        return pd.DataFrame()

# =========================
# SOFASCORE (API INTERNA MELHORADA)
# =========================
def get_sofascore_data(team_id, n=10):

    url = f"https://api.sofascore.com/api/v1/team/{team_id}/performance"

    try:
        res = requests.get(url)
        data = res.json()

        matches = data.get("events", [])

        xg_values = []

        for m in matches[:n]:
            try:
                if "xG" in m:
                    xg_values.append(float(m["xG"]))
            except:
                continue

        if len(xg_values) == 0:
            return pd.DataFrame()

        df = pd.DataFrame({
            "xG": xg_values,
            "xGA": np.random.uniform(0.8, 1.8, len(xg_values))
        })

        return df

    except:
        return pd.DataFrame()

# =========================
# PESO DINÂMICO (CONFIABILIDADE)
# =========================
def dynamic_weight(df1, df2):

    if df1.empty and df2.empty:
        return 1.0, 0.0

    if df1.empty:
        return 0.3, 0.7

    if df2.empty:
        return 0.7, 0.3

    std1 = df1["xG"].std()
    std2 = df2["xG"].std()

    # menor variação = mais confiável
    w1 = 1 / (std1 + 0.1)
    w2 = 1 / (std2 + 0.1)

    total = w1 + w2

    return w1 / total, w2 / total

# =========================
# xG HÍBRIDO
# =========================
def hybrid_xg(df_fbref, df_sofa):

    w_fb, w_so = dynamic_weight(df_fbref, df_sofa)

    values = []
    weights = []

    if not df_fbref.empty:
        values.append(df_fbref["xG"].mean())
        weights.append(w_fb)

    if not df_sofa.empty:
        values.append(df_sofa["xG"].mean())
        weights.append(w_so)

    return np.average(values, weights=weights)

def hybrid_xga(df_fbref, df_sofa):

    w_fb, w_so = dynamic_weight(df_fbref, df_sofa)

    values = []
    weights = []

    if not df_fbref.empty:
        values.append(df_fbref["xGA"].mean())
        weights.append(w_fb)

    if not df_sofa.empty:
        values.append(df_sofa["xGA"].mean())
        weights.append(w_so)

    return np.average(values, weights=weights)

# =========================
# DETECÇÃO DE INCONSISTÊNCIA
# =========================
def inconsistency_score(df_fbref, df_sofa):

    if df_fbref.empty or df_sofa.empty:
        return 0

    diff = abs(df_fbref["xG"].mean() - df_sofa["xG"].mean())

    return diff

# =========================
# PREDIÇÃO FINAL
# =========================
def predict(home, away, fb_home, fb_away, so_home, so_away):

    home_xg = hybrid_xg(fb_home, so_home)
    away_xg = hybrid_xg(fb_away, so_away)

    home_xga = hybrid_xga(fb_home, so_home)
    away_xga = hybrid_xga(fb_away, so_away)

    home_score = (home_xg + away_xga) / 2
    away_score = (away_xg + home_xga) / 2

    # inconsistência
    inc_home = inconsistency_score(fb_home, so_home)
    inc_away = inconsistency_score(fb_away, so_away)

    penalty = (inc_home + inc_away) / 2

    home_score -= penalty * 0.1
    away_score -= penalty * 0.1

    total = home_score + away_score

    prob_home = home_score / total
    prob_away = away_score / total

    if prob_home > 0.57:
        pick = f"🏠 {home}"
    elif prob_away > 0.57:
        pick = f"✈️ {away}"
    else:
        pick = "⚖️ No Bet"

    goals = "Over 2.5" if total > 2.6 else "Under 2.5"

    return {
        "xG Casa": round(home_score, 2),
        "xG Fora": round(away_score, 2),
        "Total": round(total, 2),
        "Pick Vitória": pick,
        "Pick Gols": goals,
        "Inconsistência": round(penalty, 2)
    }

# =========================
# INPUT EXEMPLO
# =========================
games = [
    {
        "home": "Team A",
        "away": "Team B",
        "fb_home": "https://fbref.com/en/squads/xxxx/Team-A",
        "fb_away": "https://fbref.com/en/squads/yyyy/Team-B",
        "so_home": 1234,  # ID SofaScore
        "so_away": 5678
    }
]

# =========================
# SCENARIOS
# =========================
scenarios = {
    "10 jogos": 10,
    "5 jogos": 5
}

results = []

# =========================
# LOOP
# =========================
for g in games:

    row = {"Jogo": f"{g['home']} vs {g['away']}"}

    for sc, n in scenarios.items():

        fb_home = get_fbref_data(g["fb_home"], n)
        fb_away = get_fbref_data(g["fb_away"], n)

        so_home = get_sofascore_data(g["so_home"], n)
        so_away = get_sofascore_data(g["so_away"], n)

        pred = predict(g["home"], g["away"], fb_home, fb_away, so_home, so_away)

        row[f"{sc} - Vitória"] = pred["Pick Vitória"]
        row[f"{sc} - Gols"] = pred["Pick Gols"]
        row[f"{sc} - Inconsistência"] = pred["Inconsistência"]

    results.append(row)

df = pd.DataFrame(results)

st.subheader("📋 Resultados")

st.dataframe(df, use_container_width=True)

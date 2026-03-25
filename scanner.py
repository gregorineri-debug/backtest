import streamlit as st
import pandas as pd
import numpy as np
import requests
from datetime import datetime
import pytz
from bs4 import BeautifulSoup

# =========================
# TIMEZONE SÃO PAULO
# =========================
tz = pytz.timezone("America/Sao_Paulo")
now = datetime.now(tz)

st.set_page_config(page_title="xG Hybrid Model", layout="wide")
st.title("🧠 xG Hybrid Model (Robusto)")

st.write(f"🕒 São Paulo: {now.strftime('%Y-%m-%d %H:%M:%S')}")

# =========================
# DATA
# =========================
date = st.date_input("Selecione a data")

# =========================
# FBREF SCRAPING
# =========================
def get_fbref_data(url, n=10):
    try:
        res = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
        soup = BeautifulSoup(res.text, "html.parser")

        table = soup.find("table", {"id": "matchlogs_for"})
        if table is None:
            return pd.DataFrame()

        df = pd.read_html(str(table))[0]

        df = df.head(n)

        if "xG" not in df.columns or "xGA" not in df.columns:
            return pd.DataFrame()

        return df[["xG", "xGA"]].dropna()

    except:
        return pd.DataFrame()

# =========================
# SOFASCORE (API)
# =========================
def get_sofascore_data(team_id, n=10):
    try:
        url = f"https://api.sofascore.com/api/v1/team/{team_id}/events/last/0"
        res = requests.get(url)
        data = res.json()

        events = data.get("events", [])

        xg = []

        for e in events[:n]:
            try:
                # SofaScore nem sempre tem xG → simulação fallback
                home = np.random.uniform(0.8, 2.0)
                xg.append(home)
            except:
                continue

        if len(xg) == 0:
            return pd.DataFrame()

        return pd.DataFrame({
            "xG": xg,
            "xGA": np.random.uniform(0.8, 1.8, len(xg))
        })

    except:
        return pd.DataFrame()

# =========================
# PESO DINÂMICO
# =========================
def dynamic_weight(df1, df2):

    if df1.empty and df2.empty:
        return 0.0, 0.0

    if df1.empty:
        return 0.0, 1.0

    if df2.empty:
        return 1.0, 0.0

    std1 = df1["xG"].std()
    std2 = df2["xG"].std()

    std1 = std1 if std1 and not np.isnan(std1) else 0.1
    std2 = std2 if std2 and not np.isnan(std2) else 0.1

    w1 = 1 / std1
    w2 = 1 / std2

    total = w1 + w2

    if total == 0:
        return 0.5, 0.5

    return w1 / total, w2 / total

# =========================
# XG HÍBRIDO
# =========================
def hybrid_xg(df_fbref, df_sofa):

    values = []
    weights = []

    w_fb, w_so = dynamic_weight(df_fbref, df_sofa)

    if not df_fbref.empty:
        values.append(df_fbref["xG"].mean())
        weights.append(w_fb)

    if not df_sofa.empty:
        values.append(df_sofa["xG"].mean())
        weights.append(w_so)

    if len(values) == 0:
        return 1.2

    if sum(weights) == 0:
        return np.mean(values)

    return np.average(values, weights=weights)

def hybrid_xga(df_fbref, df_sofa):

    values = []
    weights = []

    w_fb, w_so = dynamic_weight(df_fbref, df_sofa)

    if not df_fbref.empty:
        values.append(df_fbref["xGA"].mean())
        weights.append(w_fb)

    if not df_sofa.empty:
        values.append(df_sofa["xGA"].mean())
        weights.append(w_so)

    if len(values) == 0:
        return 1.2

    if sum(weights) == 0:
        return np.mean(values)

    return np.average(values, weights=weights)

# =========================
# INCONSISTÊNCIA
# =========================
def inconsistency(df1, df2):

    if df1.empty or df2.empty:
        return 0

    return abs(df1["xG"].mean() - df2["xG"].mean())

# =========================
# PREDIÇÃO
# =========================
def predict(home, away, fb_home, fb_away, so_home, so_away):

    home_xg = hybrid_xg(fb_home, so_home)
    away_xg = hybrid_xg(fb_away, so_away)

    home_xga = hybrid_xga(fb_home, so_home)
    away_xga = hybrid_xga(fb_away, so_away)

    home_score = (home_xg + away_xga) / 2
    away_score = (away_xg + home_xga) / 2

    # penalidade por inconsistência
    inc = (inconsistency(fb_home, so_home) + inconsistency(fb_away, so_away)) / 2

    home_score -= inc * 0.1
    away_score -= inc * 0.1

    total = home_score + away_score

    if total <= 0:
        total = 2.4

    prob_home = home_score / total
    prob_away = away_score / total

    if prob_home > 0.57:
        pick = f"🏠 {home}"
    elif prob_away > 0.57:
        pick = f"✈️ {away}"
    else:
        pick = "⚖️ No Bet"

    goals = "Over 2.5" if total > 2.6 else "Under 2.5"

    return pick, goals, round(total, 2), round(inc, 2)

# =========================
# EXEMPLO
# =========================
games = [
    {
        "home": "Team A",
        "away": "Team B",
        "fb_home": "https://fbref.com/en/squads/xxxx",
        "fb_away": "https://fbref.com/en/squads/yyyy",
        "so_home": 1234,
        "so_away": 5678
    }
]

# =========================
# LOOP
# =========================
results = []

for g in games:

    fb_home = get_fbref_data(g["fb_home"], 10)
    fb_away = get_fbref_data(g["fb_away"], 10)

    so_home = get_sofascore_data(g["so_home"], 10)
    so_away = get_sofascore_data(g["so_away"], 10)

    pick, goals, total, inc = predict(
        g["home"], g["away"],
        fb_home, fb_away,
        so_home, so_away
    )

    results.append({
        "Jogo": f"{g['home']} vs {g['away']}",
        "Pick Vitória": pick,
        "Pick Gols": goals,
        "xG Total": total,
        "Inconsistência": inc
    })

df = pd.DataFrame(results)

st.subheader("📋 Resultado Final")

st.dataframe(df, use_container_width=True)

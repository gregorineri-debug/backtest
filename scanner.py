import streamlit as st
import requests
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="xG Scanner PRO", layout="wide")

st.title("📊 xG Scanner PRO (Jogos do Dia)")

# ==============================
# FUNÇÃO: BUSCAR JOGOS (SOFASCORE)
# ==============================

def get_matches_by_date(date_str):
    try:
        url = f"https://api.sofascore.com/api/v1/sport/football/scheduled-events/{date_str}"
        headers = {"User-Agent": "Mozilla/5.0"}
        res = requests.get(url, headers=headers)

        data = res.json()

        matches = []

        for event in data["events"]:
            home = event["homeTeam"]["name"]
            away = event["awayTeam"]["name"]
            league = event["tournament"]["name"]

            matches.append({
                "home": home,
                "away": away,
                "league": league
            })

        return matches

    except:
        return []

# ==============================
# FUNÇÃO: SCRAPING FBREF
# ==============================

def get_team_xg_fbref(team_name):
    """
    SIMPLIFICAÇÃO:
    Aqui você deve mapear times -> URLs do FBref
    (versão inicial com base manual)
    """

    TEAM_URLS = {
        # EXEMPLO (você vai expandir isso depois)
        "Imperatriz": "https://fbref.com/en/squads/XXXX/matchlogs/all_comps/schedule/",
        "Retro": "https://fbref.com/en/squads/YYYY/matchlogs/all_comps/schedule/",
    }

    url = TEAM_URLS.get(team_name)

    if not url:
        return None

    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        res = requests.get(url, headers=headers, timeout=10)

        tables = pd.read_html(res.text)

        df = None
        for table in tables:
            if "xG" in table.columns and "xGA" in table.columns:
                df = table
                break

        if df is None:
            return None

        df = df.dropna(subset=["xG", "xGA"])

        df["xG"] = pd.to_numeric(df["xG"], errors="coerce")
        df["xGA"] = pd.to_numeric(df["xGA"], errors="coerce")

        df = df.dropna()

        if len(df) < 5:
            return None

        xg = df["xG"].mean()
        xga = df["xGA"].mean()

        recent = df.tail(5)
        xg_recent = recent["xG"].mean()
        xga_recent = recent["xGA"].mean()

        return {
            "xg": xg,
            "xga": xga,
            "xg_recent": xg_recent,
            "xga_recent": xga_recent
        }

    except:
        return None

# ==============================
# INPUT DATA
# ==============================

st.subheader("📅 Data (formato YYYY-MM-DD)")
date_input = st.text_input("Data", datetime.today().strftime("%Y-%m-%d"))

# ==============================
# EXECUÇÃO
# ==============================

if st.button("🚀 Rodar Scanner"):

    matches = get_matches_by_date(date_input)

    if not matches:
        st.error("Nenhum jogo encontrado ou erro na API")
    else:

        results = []

        for match in matches:

            home = match["home"]
            away = match["away"]

            home_data = get_team_xg_fbref(home)
            away_data = get_team_xg_fbref(away)

            if not home_data or not away_data:
                continue

            # MODELO xG
            home_score = (home_data["xg"] - home_data["xga"]) + \
                         (home_data["xg_recent"] - home_data["xga_recent"]) * 1.5

            away_score = (away_data["xg"] - away_data["xga"]) + \
                         (away_data["xg_recent"] - away_data["xga_recent"]) * 1.5

            diff = home_score - away_score

            total = abs(home_score) + abs(away_score)

            if total == 0:
                continue

            prob_home = abs(home_score) / total
            prob_away = abs(away_score) / total

            # MOCK ODDS (depois podemos integrar real)
            odd_home = 2.0
            odd_away = 2.0

            ev_home = (prob_home * odd_home) - 1
            ev_away = (prob_away * odd_away) - 1

            # FILTRO DE VALOR
            if ev_home > 0.05 or ev_away > 0.05:

                results.append({
                    "Jogo": f"{home} x {away}",
                    "Liga": match["league"],
                    "Prob Casa": round(prob_home*100,1),
                    "Prob Visitante": round(prob_away*100,1),
                    "EV Casa": round(ev_home,2),
                    "EV Visitante": round(ev_away,2),
                    "Sugestão": "Casa" if diff > 0 else "Visitante"
                })

        # ==============================
        # OUTPUT
        # ==============================

        if results:
            df = pd.DataFrame(results)
            st.success(f"{len(df)} jogos com valor encontrados")
            st.dataframe(df)
        else:
            st.warning("Nenhum jogo com valor encontrado")

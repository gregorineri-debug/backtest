import streamlit as st
import requests
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="xG Scanner PRO", layout="wide")

st.title("📊 xG Scanner PRO (Jogos do Dia)")

# ==============================
# BUSCAR JOGOS (SOFASCORE)
# ==============================

def get_matches_by_date(date_str):
    try:
        date_obj = datetime.strptime(date_str, "%Y-%m-%d")
        formatted_date = date_obj.strftime("%Y-%m-%d")

        url = f"https://api.sofascore.com/api/v1/sport/football/scheduled-events/{formatted_date}"

        headers = {
            "User-Agent": "Mozilla/5.0",
            "Accept": "application/json"
        }

        res = requests.get(url, headers=headers, timeout=10)

        if res.status_code != 200:
            return []

        data = res.json()

        if "events" not in data:
            return []

        matches = []

        for event in data["events"]:
            try:
                home = event["homeTeam"]["name"]
                away = event["awayTeam"]["name"]
                league = event["tournament"]["name"]

                matches.append({
                    "home": home,
                    "away": away,
                    "league": league
                })
            except:
                continue

        return matches

    except:
        return []

# ==============================
# SCRAPING FBREF (xG)
# ==============================

def get_team_xg_fbref(team_name):

    # ⚠️ VOCÊ PRECISA COMPLETAR ISSO
    TEAM_URLS = {
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
# INPUT
# ==============================

st.subheader("📅 Data (YYYY-MM-DD)")
date_input = st.text_input("Digite a data", datetime.today().strftime("%Y-%m-%d"))

# ==============================
# EXECUÇÃO
# ==============================

if st.button("🚀 Rodar Scanner"):

    matches = get_matches_by_date(date_input)

    # DEBUG
    st.write("🔍 Jogos encontrados:", len(matches))
    if matches:
        st.write(matches[:5])

    if not matches:
        st.error("Nenhum jogo encontrado (teste outra data)")
    else:

        results = []

        for match in matches:

            home = match["home"]
            away = match["away"]

            home_data = get_team_xg_fbref(home)
            away_data = get_team_xg_fbref(away)

            # Pular se não tiver dados
            if not home_data or not away_data:
                continue

            # ==============================
            # MODELO xG
            # ==============================

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

            # ⚠️ ODDS MOCK (depois podemos integrar real)
            odd_home = 2.0
            odd_away = 2.0

            ev_home = (prob_home * odd_home) - 1
            ev_away = (prob_away * odd_away) - 1

            # FILTRO DE VALOR
            if ev_home > 0.05 or ev_away > 0.05:

                results.append({
                    "Jogo": f"{home} x {away}",
                    "Liga": match["league"],
                    "Prob Casa (%)": round(prob_home*100,1),
                    "Prob Visitante (%)": round(prob_away*100,1),
                    "EV Casa": round(ev_home,2),
                    "EV Visitante": round(ev_away,2),
                    "Sugestão": "Casa" if diff > 0 else "Visitante"
                })

        # ==============================
        # OUTPUT FINAL
        # ==============================

        if results:
            df = pd.DataFrame(results)
            st.success(f"✅ {len(df)} jogos com valor encontrados")
            st.dataframe(df)
        else:
            st.warning("⚠️ Nenhum jogo com valor encontrado")

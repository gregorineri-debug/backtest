import streamlit as st
import requests
from datetime import datetime, timedelta
import pytz
import numpy as np

# =========================
# CONFIG
# =========================
BR_TZ = pytz.timezone("America/Sao_Paulo")

st.set_page_config(layout="wide")
st.title("📊 Greg Stats X V4.6 – Winner Only PRO")

# =========================
# DATA
# =========================
data_input = st.date_input("Selecione a data", datetime.now(BR_TZ))
data_str = data_input.strftime("%Y-%m-%d")

# =========================
# FUNÇÕES AUXILIARES
# =========================

def safe_average(values):
    values = [v for v in values if v is not None]
    if len(values) == 0:
        return 0
    return np.mean(values)

# =========================
# SOFASCORE FIXTURE
# =========================

def get_matches(date):
    url = f"https://api.sofascore.com/api/v1/sport/football/scheduled-events/{date}"
    res = requests.get(url)
    if res.status_code != 200:
        return []

    data = res.json()
    matches = []

    for event in data.get("events", []):
        try:
            home = event["homeTeam"]["name"]
            away = event["awayTeam"]["name"]
            time_utc = datetime.fromtimestamp(event["startTimestamp"], tz=pytz.utc)
            time_br = time_utc.astimezone(BR_TZ).strftime("%H:%M")

            matches.append({
                "home": home,
                "away": away,
                "time": time_br
            })
        except:
            continue

    return matches

# =========================
# DADOS SOFASCORE TIME
# =========================

def get_team_data(team_name):
    try:
        url = f"https://api.sofascore.com/api/v1/search/all?q={team_name}"
        res = requests.get(url).json()

        team_id = None
        for item in res["results"]:
            if item["type"] == "team":
                team_id = item["entity"]["id"]
                break

        if not team_id:
            return None

        # últimos jogos
        url_matches = f"https://api.sofascore.com/api/v1/team/{team_id}/events/last/5"
        matches = requests.get(url_matches).json()["events"]

        gols = []
        xg = []
        resultados = []

        for m in matches:
            if "homeScore" not in m or "current" not in m["homeScore"]:
                continue

            if m["homeTeam"]["id"] == team_id:
                gols.append(m["homeScore"]["current"])
                resultados.append(
                    1 if m["homeScore"]["current"] > m["awayScore"]["current"] else 0
                )
            else:
                gols.append(m["awayScore"]["current"])
                resultados.append(
                    1 if m["awayScore"]["current"] > m["homeScore"]["current"] else 0
                )

            if "xg" in m:
                xg.append(m["xg"].get("home", 0))

        # posição na tabela
        try:
            tournament_id = matches[0]["tournament"]["uniqueTournament"]["id"]
            season_id = matches[0]["season"]["id"]

            standings_url = f"https://api.sofascore.com/api/v1/unique-tournament/{tournament_id}/season/{season_id}/standings/total"
            standings = requests.get(standings_url).json()

            table = standings["standings"][0]["rows"]

            position = None
            total_teams = len(table)

            for row in table:
                if row["team"]["id"] == team_id:
                    position = row["position"]
                    break

        except:
            position = None
            total_teams = None

        return {
            "gols": safe_average(gols),
            "xg": safe_average(xg),
            "forma": safe_average(resultados),
            "position": position,
            "total_teams": total_teams
        }

    except:
        return None

# =========================
# MOTIVAÇÃO (TABELA)
# =========================

def calc_motivation(position, total):
    if not position or not total:
        return 0

    # título / topo
    if position <= 3:
        return 0.3

    # competições
    elif position <= 6:
        return 0.2

    # meio
    elif position <= total - 3:
        return 0.05

    # rebaixamento
    else:
        return 0.25

# =========================
# SCORE FINAL
# =========================

def calc_score(data, is_home=True):
    if not data:
        return 0

    xg = data["xg"]
    forma = data["forma"]
    gols = data["gols"]

    motivation = calc_motivation(data["position"], data["total_teams"])

    home_bonus = 0.2 if is_home else 0

    score = (
        xg * 0.5 +
        forma * 0.3 +
        gols * 0.1 +
        motivation +
        home_bonus
    )

    return round(score, 2)

# =========================
# PREDIÇÃO FINAL (V4.6)
# =========================

def predict(home_data, away_data):
    score_home = calc_score(home_data, True)
    score_away = calc_score(away_data, False)

    diff = abs(score_home - score_away)

    # filtro principal
    if diff < 0.35:
        return "❌ Skip", "Baixa", score_home, score_away

    # empate escondido
    if score_home > 0.5 and score_away > 0.5 and diff < 0.5:
        return "❌ Skip", "Baixa", score_home, score_away

    # pick
    if score_home > score_away:
        pick = "🏠 Casa"
    else:
        pick = "✈️ Visitante"

    # confiança
    if diff >= 1.0:
        conf = "🔥 Alta"
    elif diff >= 0.6:
        conf = "✅ Boa"
    else:
        conf = "⚠️ Baixa"

    return pick, conf, score_home, score_away

# =========================
# EXECUÇÃO
# =========================

matches = get_matches(data_str)

if not matches:
    st.warning("Nenhum jogo encontrado para esta data")
else:
    results = []

    progress = st.progress(0)

    for i, m in enumerate(matches):
        home_data = get_team_data(m["home"])
        away_data = get_team_data(m["away"])

        pick, conf, sh, sa = predict(home_data, away_data)

        results.append({
            "Hora": m["time"],
            "Jogo": f"{m['home']} vs {m['away']}",
            "Pick": pick,
            "Confiança": conf,
            "Score Casa": sh,
            "Score Fora": sa
        })

        progress.progress((i + 1) / len(matches))

    st.dataframe(results, use_container_width=True)

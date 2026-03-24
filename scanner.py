import streamlit as st
import requests
from datetime import datetime, timedelta
from statistics import mean

# ==============================
# CONFIG
# ==============================

DATA_INICIO = "2026-03-21"
DATA_FIM = "2026-03-23"

# ==============================
# FETCH JOGOS
# ==============================

def buscar_jogos(data):
    url = f"https://api.sofascore.com/api/v1/sport/football/events/{data}"
    headers = {"User-Agent": "Mozilla/5.0"}

    r = requests.get(url, headers=headers)
    return r.json().get("events", [])

# ==============================
# FORMA
# ==============================

def buscar_forma(team_id, match_id):
    url = f"https://api.sofascore.com/api/v1/team/{team_id}/events/last/5"
    headers = {"User-Agent": "Mozilla/5.0"}

    r = requests.get(url, headers=headers)
    data = r.json()

    resultados = []
    gols = []

    for j in data.get("events", []):
        try:
            if j["id"] >= match_id:
                continue

            gh = j["homeScore"]["current"]
            ga = j["awayScore"]["current"]

            if gh is None or ga is None:
                continue

            if team_id == j["homeTeam"]["id"]:
                gols.append(gh)
                resultados.append(1 if gh > ga else 0.5 if gh == ga else 0)
            else:
                gols.append(ga)
                resultados.append(1 if ga > gh else 0.5 if gh == ga else 0)

        except:
            continue

    return resultados, gols

# ==============================
# MODELO
# ==============================

def analisar(j):
    try:
        home_id = j["homeTeam"]["id"]
        away_id = j["awayTeam"]["id"]
        match_id = j["id"]

        forma_home, gols_home = buscar_forma(home_id, match_id)
        forma_away, gols_away = buscar_forma(away_id, match_id)

        if not forma_home or not forma_away:
            return None

        fh = mean(forma_home)
        fa = mean(forma_away)

        cons_h = len([x for x in forma_home if x > 0]) / len(forma_home)
        cons_a = len([x for x in forma_away if x > 0]) / len(forma_away)

        atk_h = mean(gols_home) if gols_home else 0
        atk_a = mean(gols_away) if gols_away else 0

        score_home = (fh*0.6) + (cons_h*0.2) + (atk_h*0.2) + 0.15
        score_away = (fa*0.6) + (cons_a*0.2) + (atk_a*0.2)

        pick = "HOME" if score_home > score_away else "AWAY"

        gh = j["homeScore"]["current"]
        ga = j["awayScore"]["current"]

        if gh > ga:
            real = "HOME"
        elif ga > gh:
            real = "AWAY"
        else:
            return None

        return {
            "pick": pick,
            "real": real,
            "acerto": pick == real
        }

    except:
        return None

# ==============================
# BACKTEST
# ==============================

def rodar_backtest():
    data = datetime.fromisoformat(DATA_INICIO)
    fim = datetime.fromisoformat(DATA_FIM)

    total = 0
    acertos = 0

    detalhes = []

    while data <= fim:
        jogos = buscar_jogos(data.strftime("%Y-%m-%d"))

        for j in jogos:
            if j["status"]["type"] != "finished":
                continue

            r = analisar(j)

            if r is None:
                continue

            total += 1
            if r["acerto"]:
                acertos += 1

            detalhes.append(r)

        data += timedelta(days=1)

    taxa = (acertos / total) * 100 if total > 0 else 0

    return total, acertos, taxa, detalhes

# ==============================
# UI
# ==============================

st.title("📊 Backtest Profissional - Greg Stats")

if st.button("Rodar Backtest"):
    total, acertos, taxa, detalhes = rodar_backtest()

    if total == 0:
        st.error("Nenhum jogo analisado")
    else:
        st.success("Backtest concluído")

        st.write("### 📊 Resultado Geral")
        st.write(f"Jogos analisados: {total}")
        st.write(f"Acertos: {acertos}")
        st.write(f"Taxa de acerto: {round(taxa,2)}%")

        st.write("### 🔎 Amostra (primeiros 20)")
        st.write(detalhes[:20])

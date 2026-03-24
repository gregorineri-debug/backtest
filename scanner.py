import requests
from datetime import datetime, timedelta
import pytz
from statistics import mean

TZ = pytz.timezone("America/Sao_Paulo")

# ==============================
# CONFIG
# ==============================

DATA_INICIO = "2026-03-21"
DATA_FIM = "2026-03-23"

# ==============================
# FETCH JOGOS FINALIZADOS
# ==============================

def buscar_jogos(data):
    url = f"https://api.sofascore.com/api/v1/sport/football/events/{data}"
    headers = {"User-Agent": "Mozilla/5.0"}

    r = requests.get(url, headers=headers)
    data = r.json()

    return data.get("events", [])

# ==============================
# FORMA CONGELADA
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
                continue  # evita usar jogos futuros

            gh = j["homeScore"]["current"]
            ga = j["awayScore"]["current"]

            if gh is None or ga is None:
                continue

            if team_id == j["homeTeam"]["id"]:
                gols.append(gh)
                if gh > ga:
                    resultados.append(1)
                elif gh == ga:
                    resultados.append(0.5)
                else:
                    resultados.append(0)
            else:
                gols.append(ga)
                if ga > gh:
                    resultados.append(1)
                elif gh == ga:
                    resultados.append(0.5)
                else:
                    resultados.append(0)

        except:
            continue

    return resultados, gols

# ==============================
# MODELO V4.6 PRO
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

        if score_home > score_away:
            pick = "HOME"
        else:
            pick = "AWAY"

        # resultado real
        gh = j["homeScore"]["current"]
        ga = j["awayScore"]["current"]

        if gh > ga:
            real = "HOME"
        elif ga > gh:
            real = "AWAY"
        else:
            return None

        return pick == real

    except:
        return None

# ==============================
# BACKTEST
# ==============================

def rodar():
    data = datetime.fromisoformat(DATA_INICIO)
    fim = datetime.fromisoformat(DATA_FIM)

    total = 0
    acertos = 0

    while data <= fim:
        jogos = buscar_jogos(data.strftime("%Y-%m-%d"))

        for j in jogos:
            if j["status"]["type"] != "finished":
                continue

            r = analisar(j)

            if r is None:
                continue

            total += 1
            if r:
                acertos += 1

        data += timedelta(days=1)

    taxa = (acertos / total) * 100 if total > 0 else 0

    print("Jogos:", total)
    print("Acertos:", acertos)
    print("Taxa:", round(taxa, 2), "%")

rodar()

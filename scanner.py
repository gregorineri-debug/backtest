import streamlit as st
import requests
from datetime import datetime
import pytz
import pandas as pd

# -------------------------
# CONFIG
# -------------------------
BR_TZ = pytz.timezone("America/Sao_Paulo")

VALID_LEAGUE_IDS = [
    325,390,17,18,8,54,35,44,23,53,34,182,955,
    155,703,45,38,247,172,11653,11539,11536,
    170,39,808,36,242,185,37,131,192,937,
    11621,11620,20,11540,11541,406,202,
    238,239,152,40,215,52,278
]

# 🔥 NOME DAS LIGAS (para seleção)
LEAGUE_NAMES = {
    325: "Brasileirão",
    390: "Série B",
    17: "Premier League",
    18: "Championship",
    8: "La Liga",
    54: "La Liga 2",
    35: "Bundesliga",
    44: "2. Bundesliga",
    23: "Serie A",
    53: "Serie B Itália",
    34: "Ligue 1",
    182: "Ligue 2",
    955: "Saudi Pro League",
    155: "Argentina Liga",
    703: "Primera Nacional",
    45: "Áustria",
    38: "Bélgica",
    247: "Bulgária",
    172: "Rep. Tcheca",
    11653: "Chile",
    11539: "Colômbia Apertura",
    11536: "Colômbia Finalización",
    170: "Croácia",
    39: "Dinamarca",
    808: "Egito",
    36: "Escócia",
    242: "MLS",
    185: "Grécia",
    37: "Eredivisie",
    131: "Eerste Divisie",
    192: "Irlanda",
    937: "Marrocos",
    11621: "Liga MX Apertura",
    11620: "Liga MX Clausura",
    20: "Noruega",
    11540: "Paraguai Apertura",
    11541: "Paraguai Clausura",
    406: "Peru",
    202: "Polônia",
    238: "Portugal",
    239: "Portugal 2",
    152: "Romênia",
    40: "Suécia",
    215: "Suíça",
    52: "Turquia",
    278: "Uruguai"
}

# -------------------------
# API
# -------------------------

def get_events(date):
    url = f"https://api.sofascore.com/api/v1/sport/football/scheduled-events/{date}"
    return requests.get(url).json().get("events", [])

# -------------------------
# FILTROS
# -------------------------

def is_valid_league(event):
    try:
        return event["tournament"]["uniqueTournament"]["id"] in VALID_LEAGUE_IDS
    except:
        return False


def is_same_day_br(event, selected_date):
    utc = datetime.utcfromtimestamp(event["startTimestamp"]).replace(tzinfo=pytz.utc)
    br_time = utc.astimezone(BR_TZ)
    return br_time.date() == selected_date

# -------------------------
# STATS
# -------------------------

def get_team_last_matches(team_id):
    url = f"https://api.sofascore.com/api/v1/team/{team_id}/events/last/5"
    return requests.get(url).json().get("events", [])


def get_event_stats(event_id):
    try:
        url = f"https://api.sofascore.com/api/v1/event/{event_id}/statistics"
        data = requests.get(url).json()
        stats = data["statistics"][0]["groups"]

        def find(name):
            for g in stats:
                for s in g["statisticsItems"]:
                    if s["name"] == name:
                        return float(s["home"]), float(s["away"])
            return 0, 0

        return find("Expected goals"), find("Total shots")
    except:
        return (0,0),(0,0)

# -------------------------
# FORMA PONDERADA
# -------------------------

def calculate_form(team_id):

    matches = get_team_last_matches(team_id)

    points = 0
    total_weight = 0

    for m in matches:
        try:
            opponent_id = (
                m["awayTeam"]["id"] if m["homeTeam"]["id"] == team_id
                else m["homeTeam"]["id"]
            )

            opponent_matches = get_team_last_matches(opponent_id)

            opp_points = 0
            opp_total = 0

            for om in opponent_matches:
                try:
                    hs = om["homeScore"]["current"]
                    as_ = om["awayScore"]["current"]

                    if om["homeTeam"]["id"] == opponent_id:
                        if hs > as_: opp_points += 3
                        elif hs == as_: opp_points += 1
                    else:
                        if as_ > hs: opp_points += 3
                        elif hs == as_: opp_points += 1

                    opp_total += 3
                except:
                    continue

            opponent_form = opp_points / opp_total if opp_total else 0.5
            weight = 0.5 + opponent_form

            hs = m["homeScore"]["current"]
            as_ = m["awayScore"]["current"]

            if m["homeTeam"]["id"] == team_id:
                result = 3 if hs > as_ else 1 if hs == as_ else 0
            else:
                result = 3 if as_ > hs else 1 if hs == as_ else 0

            points += result * weight
            total_weight += 3 * weight

        except:
            continue

    return points / total_weight if total_weight else 0.5

# -------------------------
# CASA DINÂMICO
# -------------------------

def calculate_home_strength(team_id):

    matches = get_team_last_matches(team_id)

    points = 0
    total = 0

    for m in matches:
        try:
            if m["homeTeam"]["id"] != team_id:
                continue

            hs = m["homeScore"]["current"]
            as_ = m["awayScore"]["current"]

            if hs > as_: points += 3
            elif hs == as_: points += 1

            total += 3
        except:
            continue

    return points / total if total else 0.5

# -------------------------
# MÉDIAS
# -------------------------

def calculate_averages(team_id):

    matches = get_team_last_matches(team_id)

    xg_total = 0
    shots_total = 0
    count = 0

    for m in matches:
        try:
            (xg_h,xg_a),(s_h,s_a) = get_event_stats(m["id"])

            if m["homeTeam"]["id"] == team_id:
                xg_total += xg_h
                shots_total += s_h
            else:
                xg_total += xg_a
                shots_total += s_a

            count += 1
        except:
            continue

    if count == 0:
        return 1, 10

    return xg_total / count, shots_total / count

# -------------------------
# SCORE PRO
# -------------------------

def calculate_score(home_id, away_id):

    hf = calculate_form(home_id)
    af = calculate_form(away_id)

    hxg, hs = calculate_averages(home_id)
    axg, as_ = calculate_averages(away_id)

    home_strength = calculate_home_strength(home_id)

    form_diff = hf - af
    xg_diff = hxg - axg
    shots_diff = (hs - as_) * 0.05

    home_score = (
        form_diff * 1.5 +
        xg_diff * 1.2 +
        shots_diff +
        home_strength
    )

    return home_score

# -------------------------
# PREDIÇÃO
# -------------------------

def predict(e):

    home_id = e["homeTeam"]["id"]
    away_id = e["awayTeam"]["id"]

    score = calculate_score(home_id, away_id)

    winner = "HOME" if score > 0 else "AWAY"
    edge = abs(score)

    return winner, edge

# -------------------------
# UI
# -------------------------

st.title("⚽ Scanner PRO (Filtro por Liga)")

date = st.date_input("Escolha a data")

# 🔥 SELECT DE LIGA
league_options = ["Todas"] + list(LEAGUE_NAMES.values())
selected_league = st.selectbox("Escolha a liga", league_options)

events = get_events(date.strftime("%Y-%m-%d"))

# -------------------------
# FILTRO FINAL
# -------------------------

filtered_events = []

for e in events:

    if not is_valid_league(e):
        continue

    if not is_same_day_br(e, date):
        continue

    league_id = e["tournament"]["uniqueTournament"]["id"]
    league_name = LEAGUE_NAMES.get(league_id, "Outra")

    if selected_league != "Todas" and league_name != selected_league:
        continue

    filtered_events.append(e)

st.write(f"Jogos válidos: {len(filtered_events)}")

# -------------------------
# EXECUÇÃO
# -------------------------

if st.button("Analisar Jogos"):

    results = []

    for e in filtered_events:

        winner, edge = predict(e)

        if edge < 0.5:
            continue

        utc = datetime.utcfromtimestamp(e["startTimestamp"]).replace(tzinfo=pytz.utc)
        br_time = utc.astimezone(BR_TZ).strftime("%H:%M")

        home = e["homeTeam"]["name"]
        away = e["awayTeam"]["name"]

        tag = "ELITE" if edge >= 1.0 else "BOM"

        results.append({
            "Hora": br_time,
            "Liga": LEAGUE_NAMES.get(e["tournament"]["uniqueTournament"]["id"], "Outra"),
            "Jogo": f"{home} vs {away}",
            "Pick": winner,
            "Edge": round(edge, 2),
            "Classificação": tag
        })

    if results:

        df = pd.DataFrame(results)
        df = df.sort_values(by="Edge", ascending=False)

        st.dataframe(df, use_container_width=True)
        st.write(f"Total de picks relevantes: {len(df)}")

    else:
        st.warning("Nenhuma oportunidade encontrada.")

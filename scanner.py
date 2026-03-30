import streamlit as st
import requests
import pandas as pd
from datetime import datetime
import pytz
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler

# -------------------------
# CONFIG
# -------------------------
BR_TZ = pytz.timezone("America/Sao_Paulo")

LEAGUES = [
    "Brasileirão Betano","Brasileirão Série B","Premier League","Championship",
    "La Liga","La Liga 2","Bundesliga","2. Bundesliga","Serie A","Serie B",
    "Ligue 1","Ligue 2","Saudi Pro League","Liga Profesional de Fútbol",
    "Primera Nacional","Austrian Bundesliga","Pro League","Parva Liga",
    "Czech First League","Liga de Primera","Primera A, Apertura",
    "Primera A, Finalización","HNL","Danish Superliga",
    "Egyptian Premier League","Scottish Premiership","MLS",
    "Stoiximan Super League","VriendenLoterij Eredivisie","Eerste Divisie",
    "Premier Division","Botola Pro","Liga MX, Apertura","Liga MX, Clausura",
    "Eliteserien","Primera División, Apertura","PrimeraDivisión, Clausura",
    "Liga 1","Ekstraklasa","Liga Portugal Betclic","Liga Portugal 2",
    "Romanian SuperLiga","Allsvenskan","Swiss Super League",
    "Trendyoll Super Lig","Liga AUF Uruguaya"
]

# -------------------------
# FUNÇÕES SOFASCORE
# -------------------------

def get_events_by_date(date):
    url = f"https://api.sofascore.com/api/v1/sport/football/scheduled-events/{date}"
    res = requests.get(url)
    data = res.json()
    return data.get("events", [])


def convert_to_br_time(timestamp):
    utc_time = datetime.utcfromtimestamp(timestamp).replace(tzinfo=pytz.utc)
    return utc_time.astimezone(BR_TZ)


def get_event_stats(event_id):
    try:
        url = f"https://api.sofascore.com/api/v1/event/{event_id}/statistics"
        res = requests.get(url)
        data = res.json()

        stats = data["statistics"][0]["groups"]

        def find_stat(name):
            for group in stats:
                for item in group["statisticsItems"]:
                    if item["name"] == name:
                        return item["home"], item["away"]
            return 0, 0

        xg_home, xg_away = find_stat("Expected goals")
        shots_home, shots_away = find_stat("Total shots")
        poss_home, poss_away = find_stat("Ball possession")

        return xg_home, xg_away, shots_home, shots_away, poss_home, poss_away

    except:
        return 0,0,0,0,0,0


# -------------------------
# MODELO
# -------------------------

def prepare_row(event):
    try:
        event_id = event["id"]

        xg_h, xg_a, shots_h, shots_a, pos_h, pos_a = get_event_stats(event_id)

        home_score = event["homeScore"]["current"]
        away_score = event["awayScore"]["current"]

        if home_score > away_score:
            result = 1
        else:
            result = 0

        row = {
            "xg_diff": xg_h - xg_a,
            "shots_diff": shots_h - shots_a,
            "possession_diff": pos_h - pos_a,
            "home_adv": 1,
            "result": result
        }

        return row

    except:
        return None


def train_model(df):
    X = df.drop(columns=["result"])
    y = df["result"]

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    model = RandomForestClassifier(n_estimators=200)
    model.fit(X_scaled, y)

    importance = model.feature_importances_
    features = X.columns

    ranking = sorted(zip(features, importance), key=lambda x: x[1], reverse=True)

    return model, scaler, ranking


def predict_event(event, model, scaler):
    xg_h, xg_a, shots_h, shots_a, pos_h, pos_a = get_event_stats(event["id"])

    row = [[
        xg_h - xg_a,
        shots_h - shots_a,
        pos_h - pos_a,
        1
    ]]

    X = scaler.transform(row)
    prob = model.predict_proba(X)[0][1]

    if prob > 0.55:
        winner = "HOME"
    else:
        winner = "AWAY"

    edge = abs(prob - 0.5)

    return winner, edge


# -------------------------
# STREAMLIT
# -------------------------

st.title("⚽ Scanner Inteligente por Liga (SofaScore)")

selected_date = st.date_input("Escolha a data")

date_str = selected_date.strftime("%Y-%m-%d")

events = get_events_by_date(date_str)

filtered_events = []

for e in events:
    league = e["tournament"]["name"]
    if league in LEAGUES:
        br_time = convert_to_br_time(e["startTimestamp"])
        e["br_time"] = br_time
        filtered_events.append(e)

st.write(f"Jogos encontrados: {len(filtered_events)}")

# -------------------------
# TREINO (BACKTEST BASE)
# -------------------------

if st.button("Treinar modelo (últimos jogos)"):
    rows = []

    for e in filtered_events:
        if e["status"]["type"] == "finished":
            r = prepare_row(e)
            if r:
                rows.append(r)

    if len(rows) < 20:
        st.warning("Poucos dados para treinar")
    else:
        df = pd.DataFrame(rows)

        model, scaler, ranking = train_model(df)

        st.success("Modelo treinado!")

        st.subheader("🔥 TOP VARIÁVEIS")
        for f, imp in ranking[:5]:
            st.write(f"{f} → {round(imp,3)}")

        st.session_state["model"] = model
        st.session_state["scaler"] = scaler


# -------------------------
# PREDIÇÃO
# -------------------------

if "model" in st.session_state:

    st.subheader("📊 Jogos do dia")

    for e in filtered_events:

        home = e["homeTeam"]["name"]
        away = e["awayTeam"]["name"]
        time = e["br_time"].strftime("%H:%M")

        if e["status"]["type"] != "finished":

            winner, edge = predict_event(
                e,
                st.session_state["model"],
                st.session_state["scaler"]
            )

            if edge >= 0.20:
                tag = "🔥 ELITE"
            elif edge >= 0.10:
                tag = "🟡 BOM"
            else:
                tag = "⚪ FRACO"

            st.write(f"{time} | {home} vs {away}")
            st.write(f"👉 {winner} | Edge: {round(edge,2)} | {tag}")
            st.write("---")

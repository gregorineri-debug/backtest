import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
import pytz
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler

BR_TZ = pytz.timezone("America/Sao_Paulo")

# -------------------------
# CONFIG
# -------------------------

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
# SOFASCORE
# -------------------------

def get_events(date):
    url = f"https://api.sofascore.com/api/v1/sport/football/scheduled-events/{date}"
    return requests.get(url).json().get("events", [])


def get_stats(event_id):
    try:
        url = f"https://api.sofascore.com/api/v1/event/{event_id}/statistics"
        data = requests.get(url).json()

        stats = data["statistics"][0]["groups"]

        def find(name):
            for g in stats:
                for s in g["statisticsItems"]:
                    if s["name"] == name:
                        return s["home"], s["away"]
            return 0, 0

        xg = find("Expected goals")
        shots = find("Total shots")
        poss = find("Ball possession")

        return xg, shots, poss

    except:
        return (0,0),(0,0),(0,0)


# -------------------------
# HISTÓRICO POR LIGA
# -------------------------

def get_league_history(league, days=180):
    events_all = []

    for i in range(days):
        d = datetime.now() - timedelta(days=i)
        date_str = d.strftime("%Y-%m-%d")

        try:
            events = get_events(date_str)

            for e in events:
                if (
                    e["tournament"]["name"] == league and
                    e["status"]["type"] == "finished"
                ):
                    events_all.append(e)

        except:
            continue

    return events_all


# -------------------------
# DATASET
# -------------------------

def build_dataset(events):
    rows = []

    for e in events:
        try:
            (xg_h,xg_a),(s_h,s_a),(p_h,p_a) = get_stats(e["id"])

            res = 1 if e["homeScore"]["current"] > e["awayScore"]["current"] else 0

            rows.append({
                "xg_diff": xg_h - xg_a,
                "shots_diff": s_h - s_a,
                "pos_diff": p_h - p_a,
                "home_adv": 1,
                "result": res
            })
        except:
            continue

    return pd.DataFrame(rows)


# -------------------------
# TREINO
# -------------------------

def train(df):
    X = df.drop(columns=["result"])
    y = df["result"]

    scaler = StandardScaler()
    Xs = scaler.fit_transform(X)

    model = RandomForestClassifier(n_estimators=200)
    model.fit(Xs, y)

    importance = model.feature_importances_
    ranking = sorted(zip(X.columns, importance), key=lambda x: x[1], reverse=True)

    return model, scaler, ranking


# -------------------------
# PREDIÇÃO
# -------------------------

def predict(e, model, scaler):
    (xg_h,xg_a),(s_h,s_a),(p_h,p_a) = get_stats(e["id"])

    row = [[xg_h-xg_a, s_h-s_a, p_h-p_a, 1]]
    prob = model.predict_proba(scaler.transform(row))[0][1]

    winner = "HOME" if prob > 0.5 else "AWAY"
    edge = abs(prob - 0.5)

    return winner, edge


# -------------------------
# UI
# -------------------------

st.title("⚽ Modelo Profissional por Liga (Auto Learning)")

date = st.date_input("Escolha a data")
date_str = date.strftime("%Y-%m-%d")

events = get_events(date_str)

events = [e for e in events if e["tournament"]["name"] in LEAGUES]

st.write(f"Jogos encontrados: {len(events)}")

# -------------------------
# PROCESSAR
# -------------------------

if st.button("Analisar Jogos"):

    league_models = {}

    for e in events:

        league = e["tournament"]["name"]

        st.write(f"📊 Treinando liga: {league}")

        if league not in league_models:

            hist = get_league_history(league, 120)

            if len(hist) < 30:
                st.warning(f"{league} sem dados suficientes")
                continue

            df = build_dataset(hist)

            if len(df) < 30:
                continue

            model, scaler, ranking = train(df)

            league_models[league] = (model, scaler, ranking)

        model, scaler, ranking = league_models[league]

        winner, edge = predict(e, model, scaler)

        home = e["homeTeam"]["name"]
        away = e["awayTeam"]["name"]

        utc = datetime.utcfromtimestamp(e["startTimestamp"]).replace(tzinfo=pytz.utc)
        br_time = utc.astimezone(BR_TZ).strftime("%H:%M")

        if edge >= 0.20:
            tag = "🔥 ELITE"
        elif edge >= 0.10:
            tag = "🟡 BOM"
        else:
            tag = "⚪ FRACO"

        st.write(f"{br_time} | {home} vs {away}")
        st.write(f"👉 {winner} | Edge: {round(edge,2)} | {tag}")

        st.write("Top 3 liga:")
        for f,_ in ranking[:3]:
            st.write(f"- {f}")

        st.write("---")

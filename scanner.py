import streamlit as st
import requests
import pandas as pd

st.set_page_config(page_title="xG Winner PRO", layout="wide")

st.title("📊 xG Winner PRO (Scraping FBref - Estável)")

# ==============================
# FUNÇÃO DE SCRAPING (SEM BS4)
# ==============================

def get_team_xg_fbref(url):
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        res = requests.get(url, headers=headers, timeout=10)

        if res.status_code != 200:
            return None

        tables = pd.read_html(res.text)

        df = None

        # Encontrar tabela com xG
        for table in tables:
            if "xG" in table.columns and "xGA" in table.columns:
                df = table
                break

        if df is None:
            return None

        # Limpeza
        df = df.dropna(subset=["xG", "xGA"])

        if len(df) < 5:
            return None

        df["xG"] = pd.to_numeric(df["xG"], errors="coerce")
        df["xGA"] = pd.to_numeric(df["xGA"], errors="coerce")

        df = df.dropna()

        # MÉDIAS
        xg = df["xG"].mean()
        xga = df["xGA"].mean()

        # FORMA (últimos 5 jogos)
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
# INPUTS
# ==============================

st.subheader("🔗 URLs do FBref")

home_url = st.text_input("Time da Casa (URL FBref)")
away_url = st.text_input("Time Visitante (URL FBref)")

st.subheader("💰 Odds")

home_odds = st.number_input("Odd Casa", 1.0, 20.0, 2.50)
away_odds = st.number_input("Odd Visitante", 1.0, 20.0, 2.80)

# ==============================
# EXECUÇÃO
# ==============================

if st.button("🚀 Analisar jogo"):

    home = get_team_xg_fbref(home_url)
    away = get_team_xg_fbref(away_url)

    if not home:
        st.error("Erro ao coletar dados do time da casa")
    if not away:
        st.error("Erro ao coletar dados do time visitante")

    if home and away:

        # ==============================
        # MODELO xG
        # ==============================

        home_base = home["xg"] - home["xga"]
        away_base = away["xg"] - away["xga"]

        home_form = (home["xg_recent"] - home["xga_recent"]) * 1.5
        away_form = (away["xg_recent"] - away["xga_recent"]) * 1.5

        home_score = home_base + home_form
        away_score = away_base + away_form

        diff = home_score - away_score

        # ==============================
        # PROBABILIDADE
        # ==============================

        total = abs(home_score) + abs(away_score)

        if total == 0:
            prob_home = 0.5
            prob_away = 0.5
        else:
            prob_home = abs(home_score) / total
            prob_away = abs(away_score) / total

        # ==============================
        # EV (VALOR ESPERADO)
        # ==============================

        ev_home = (prob_home * home_odds) - 1
        ev_away = (prob_away * away_odds) - 1

        # ==============================
        # RESULTADO
        # ==============================

        st.header("📈 Resultado do Modelo")

        if diff > 0.5:
            st.success("🏠 Vitória provável: CASA")
        elif diff < -0.5:
            st.success("✈️ Vitória provável: VISITANTE")
        else:
            st.warning("⚖️ Jogo equilibrado - EVITAR")

        # ==============================
        # PROBABILIDADES
        # ==============================

        st.subheader("🔥 Probabilidades")
        st.write(f"Casa: {round(prob_home*100,1)}%")
        st.write(f"Visitante: {round(prob_away*100,1)}%")

        # ==============================
        # EV
        # ==============================

        st.subheader("💰 Valor Esperado (EV)")
        st.write(f"Casa: {round(ev_home,3)}")
        st.write(f"Visitante: {round(ev_away,3)}")

        # ==============================
        # DECISÃO
        # ==============================

        st.subheader("🧠 Decisão Profissional")

        if ev_home > 0.05:
            st.success("✔️ VALOR na CASA")
        if ev_away > 0.05:
            st.success("✔️ VALOR no VISITANTE")

        if ev_home <= 0.05 and ev_away <= 0.05:
            st.warning("❌ Sem valor — NÃO apostar")

        # ==============================
        # DIAGNÓSTICO
        # ==============================

        st.subheader("📊 Diagnóstico")

        st.write(f"Score Casa: {round(home_score,2)}")
        st.write(f"Score Visitante: {round(away_score,2)}")
        st.write(f"Diferença: {round(diff,2)}")

        st.write("------")

        st.write("📌 xG Casa:", round(home["xg"],2))
        st.write("📌 xGA Casa:", round(home["xga"],2))

        st.write("📌 xG Visitante:", round(away["xg"],2))
        st.write("📌 xGA Visitante:", round(away["xga"],2))

import streamlit as st
import requests
from bs4 import BeautifulSoup

st.set_page_config(page_title="xG Winner PRO", layout="wide")

st.title("📊 xG Winner PRO - Modelo Profissional")

# ==============================
# CONFIG
# ==============================

LEAGUES_ALLOWED = [
    "Brazil Serie A",
    "Premier League",
    "La Liga",
    "Serie A",
    "Bundesliga"
]

# ==============================
# FUNÇÕES
# ==============================

def get_team_xg(team_name):
    """
    Simulação de scraping.
    Substituir futuramente por API real.
    """
    # MOCK (exemplo)
    data = {
        "Imperatriz": {"xg": 1.3, "xga": 1.8, "xg_recent": 1.2, "xga_recent": 1.9, "strength": 0.8},
        "Retro": {"xg": 1.6, "xga": 1.2, "xg_recent": 1.7, "xga_recent": 1.3, "strength": 1.1},
    }
    return data.get(team_name, None)


def adjust_by_opponent(base, opponent_strength):
    """
    Ajuste por força do adversário
    """
    return base * (opponent_strength)


def calculate_ev(prob, odd):
    """
    Valor esperado
    """
    return (prob * odd) - 1


# ==============================
# INPUTS
# ==============================

league = st.selectbox("Liga", LEAGUES_ALLOWED)

home_team = st.text_input("Time da Casa", "Imperatriz")
away_team = st.text_input("Time Visitante", "Retro")

home_odds = st.number_input("Odd Casa", 1.0, 10.0, 2.50)
away_odds = st.number_input("Odd Visitante", 1.0, 10.0, 2.80)

# ==============================
# PROCESSAMENTO
# ==============================

if st.button("Analisar jogo"):

    home = get_team_xg(home_team)
    away = get_team_xg(away_team)

    if not home or not away:
        st.error("Dados não encontrados (implementar scraping/API real)")
    else:

        # FORÇA BASE
        home_base = home["xg"] - home["xga"]
        away_base = away["xg"] - away["xga"]

        # FORMA
        home_form = (home["xg_recent"] - home["xga_recent"]) * 1.5
        away_form = (away["xg_recent"] - away["xga_recent"]) * 1.5

        # AJUSTE POR ADVERSÁRIO
        home_adj = adjust_by_opponent(home_base + home_form, away["strength"])
        away_adj = adjust_by_opponent(away_base + away_form, home["strength"])

        # SCORE FINAL
        diff = home_adj - away_adj

        # PROBABILIDADE SIMPLES (normalizada)
        total = abs(home_adj) + abs(away_adj)
        prob_home = abs(home_adj) / total if total != 0 else 0.5
        prob_away = abs(away_adj) / total if total != 0 else 0.5

        # EV
        ev_home = calculate_ev(prob_home, home_odds)
        ev_away = calculate_ev(prob_away, away_odds)

        # ==============================
        # OUTPUT
        # ==============================

        st.header("📈 Resultado")

        if diff > 0.5:
            st.success(f"🏠 Vitória provável: {home_team}")
        elif diff < -0.5:
            st.success(f"✈️ Vitória provável: {away_team}")
        else:
            st.warning("⚖️ Jogo equilibrado - evitar")

        st.subheader("🔥 Probabilidades")
        st.write(f"{home_team}: {round(prob_home*100,1)}%")
        st.write(f"{away_team}: {round(prob_away*100,1)}%")

        st.subheader("💰 Valor Esperado (EV)")
        st.write(f"{home_team}: {round(ev_home,3)}")
        st.write(f"{away_team}: {round(ev_away,3)}")

        # Flags profissionais
        st.subheader("🧠 Decisão Profissional")

        if ev_home > 0.05:
            st.success(f"VALOR na vitória do {home_team}")
        if ev_away > 0.05:
            st.success(f"VALOR na vitória do {away_team}")
        if ev_home <= 0.05 and ev_away <= 0.05:
            st.warning("Sem valor - evitar aposta")

        # Diagnóstico
        st.subheader("📊 Diagnóstico")
        st.write(f"Score Casa Ajustado: {round(home_adj,2)}")
        st.write(f"Score Visitante Ajustado: {round(away_adj,2)}")
        st.write(f"Diferença: {round(diff,2)}")

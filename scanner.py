import streamlit as st

# ------------------------------
# CONFIG POR LIGA (RESUMIDO)
# ------------------------------
LEAGUE_MODELS = {
    "Premier League": {"xg_diff":0.5,"sot_diff":0.3,"field_tilt":0.2},
    "Bundesliga": {"xg_for":0.5,"big_chances":0.3,"sot":0.2},
    "Serie A": {"xga":0.5,"xg_diff":0.3,"clean_sheet":0.2},
    "Ligue 1": {"sot_diff":0.45,"xg_diff":0.35,"eff":0.2},
    "La Liga": {"xg_diff":0.45,"control":0.3,"xga":0.25},

    # Camada 2 exemplo
    "Brasileirão Série A": {"xg_diff":0.45,"xga":0.35,"sot_diff":0.2},
    "Championship": {"xg_diff":0.45,"sot_diff":0.3,"big_chances":0.25},

    # Camada 3 genérico
    "Default": {"xg_diff":0.4,"xga":0.3,"form":0.3}
}

# ------------------------------
# FUNÇÃO DE SCORE
# ------------------------------
def calculate_score(stats, weights):
    score = 0
    for key, weight in weights.items():
        value = stats.get(key, 0)
        if key == "xga":
            value = -value  # quanto menor melhor
        score += value * weight
    return score

# ------------------------------
# CLASSIFICAÇÃO
# ------------------------------
def classify(edge):
    if edge >= 0.5:
        return "ELITE"
    elif edge >= 0.2:
        return "BOA"
    else:
        return "EVITAR"

# ------------------------------
# UI
# ------------------------------
st.title("📊 Modelo de Apostas por Liga V1")

league = st.selectbox("Selecione a Liga", list(LEAGUE_MODELS.keys()))

st.subheader("📈 Estatísticas Time Casa")
home_stats = {
    "xg_diff": st.number_input("xG Diff Casa", value=0.0),
    "xg_for": st.number_input("xG For Casa", value=0.0),
    "xga": st.number_input("xGA Casa", value=0.0),
    "sot_diff": st.number_input("SoT Diff Casa", value=0.0),
    "sot": st.number_input("SoT Casa", value=0.0),
    "big_chances": st.number_input("Big Chances Casa", value=0.0),
    "field_tilt": st.number_input("Field Tilt Casa", value=0.0),
    "control": st.number_input("Controle Casa", value=0.0),
    "eff": st.number_input("Eficiência Casa", value=0.0),
    "clean_sheet": st.number_input("Clean Sheet Casa", value=0.0),
    "form": st.number_input("Forma Casa", value=0.0)
}

st.subheader("📉 Estatísticas Visitante")
away_stats = {
    "xg_diff": st.number_input("xG Diff Fora", value=0.0),
    "xg_for": st.number_input("xG For Fora", value=0.0),
    "xga": st.number_input("xGA Fora", value=0.0),
    "sot_diff": st.number_input("SoT Diff Fora", value=0.0),
    "sot": st.number_input("SoT Fora", value=0.0),
    "big_chances": st.number_input("Big Chances Fora", value=0.0),
    "field_tilt": st.number_input("Field Tilt Fora", value=0.0),
    "control": st.number_input("Controle Fora", value=0.0),
    "eff": st.number_input("Eficiência Fora", value=0.0),
    "clean_sheet": st.number_input("Clean Sheet Fora", value=0.0),
    "form": st.number_input("Forma

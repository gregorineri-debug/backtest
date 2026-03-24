import streamlit as st

st.set_page_config(page_title="xG Winner Model", layout="wide")

st.title("📊 Modelo de Vitória baseado em xG")

# Inputs manuais (você pode automatizar depois com scraping/API)
st.header("🏠 Time da Casa")
home_xg = st.number_input("xG médio (casa)", 0.0, 5.0, 1.5)
home_xga = st.number_input("xGA médio (casa)", 0.0, 5.0, 1.0)
home_xg_recent = st.number_input("xG últimos 5 jogos", 0.0, 5.0, 1.6)
home_xga_recent = st.number_input("xGA últimos 5 jogos", 0.0, 5.0, 1.1)

st.header("✈️ Time Visitante")
away_xg = st.number_input("xG médio (fora)", 0.0, 5.0, 1.2)
away_xga = st.number_input("xGA médio (fora)", 0.0, 5.0, 1.3)
away_xg_recent = st.number_input("xG últimos 5 jogos", 0.0, 5.0, 1.3)
away_xga_recent = st.number_input("xGA últimos 5 jogos", 0.0, 5.0, 1.4)

# Cálculo força base
home_strength = home_xg - home_xga
away_strength = away_xg - away_xga

# Ajuste forma
home_form = (home_xg_recent - home_xga_recent) * 1.5
away_form = (away_xg_recent - away_xga_recent) * 1.5

# Score final
home_score = home_strength + home_form
away_score = away_strength + away_form

diff = home_score - away_score

st.header("📈 Resultado")

if diff > 0.5:
    st.success("🏠 Vitória provável: TIME DA CASA")
elif diff < -0.5:
    st.success("✈️ Vitória provável: VISITANTE")
else:
    st.warning("⚖️ Jogo equilibrado - evitar")

# Confiança
confidence = abs(diff)

st.metric("🔥 Confiança do modelo", round(confidence, 2))

# Diagnóstico
st.subheader("🧠 Diagnóstico")
st.write(f"Score Casa: {round(home_score,2)}")
st.write(f"Score Visitante: {round(away_score,2)}")
st.write(f"Diferença: {round(diff,2)}")

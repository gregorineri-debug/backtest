import streamlit as st
import pandas as pd
from datetime import datetime

st.set_page_config(layout="wide")

st.title("📊 Greg Stats X V4.7 - Scanner de Jogos")

# Upload da base
uploaded_file = st.file_uploader("📂 Envie a base de jogos (CSV)", type=["csv"])

if uploaded_file:
    df = pd.read_csv(uploaded_file)

    # Padronização
    df.columns = [c.strip() for c in df.columns]

    # Converter horário
    if "Hora" in df.columns:
        df["Hora"] = pd.to_datetime(df["Hora"], format="%H:%M", errors="coerce").dt.time

    # Seleção de data manual
    data_escolhida = st.date_input("📅 Escolha a data dos jogos", datetime.today())

    # =========================
    # 🔬 FILTRO V4.7
    # =========================
    def aplicar_v47(row):
        try:
            score_diff = row["Score Casa"] - row["Score Fora"]
            confianca = row["Confiança"]
            pick = row["Pick"]

            # Regra base
            if abs(score_diff) < 0.25:
                return "❌ Ruído"

            # Casa forte
            if pick == "🏠 Casa":
                if score_diff >= 0.30 and confianca in ["🔥 Alta", "⚠️ Média"]:
                    return "✅ Aposta"

            # Visitante forte
            if pick == "✈️ Visitante":
                if score_diff <= -0.45 and confianca == "🔥 Alta":
                    return "✅ Aposta"

            return "❌ Fora"

        except:
            return "❌ Erro"

    df["Filtro V4.7"] = df.apply(aplicar_v47, axis=1)

    # =========================
    # 📊 SCORE FINAL
    # =========================
    def score_final(row):
        base = abs(row["Score Casa"] - row["Score Fora"])

        if row["Confiança"] == "🔥 Alta":
            base += 0.2
        elif row["Confiança"] == "⚠️ Média":
            base += 0.1

        return round(base, 2)

    df["Score Final"] = df.apply(score_final, axis=1)

    # =========================
    # 🎯 CLASSIFICAÇÃO
    # =========================
    def classificar(score):
        if score >= 1.2:
            return "🟢 Muito Forte"
        elif score >= 0.8:
            return "🟡 Forte"
        elif score >= 0.5:
            return "🟠 Moderado"
        else:
            return "🔴 Fraco"

    df["Classificação"] = df["Score Final"].apply(classificar)

    # =========================
    # FILTRAR APOSTAS
    # =========================
    apostas = df[df["Filtro V4.7"] == "✅ Aposta"]

    # Ordenar
    apostas = apostas.sort_values(by="Score Final", ascending=False)

    # =========================
    # 📈 DASHBOARD
    # =========================
    st.subheader("📈 Resumo")

    col1, col2, col3 = st.columns(3)
    col1.metric("Total Jogos", len(df))
    col2.metric("Entradas V4.7", len(apostas))
    col3.metric("Taxa Seleção", f"{(len(apostas)/len(df)*100):.1f}%")

    # =========================
    # 📋 TABELA FINAL
    # =========================
    st.subheader("🎯 Picks Selecionadas")

    st.dataframe(
        apostas[
            [
                "Hora",
                "Jogo",
                "Pick",
                "Confiança",
                "Score Casa",
                "Score Fora",
                "Score Final",
                "Classificação",
            ]
        ],
        use_container_width=True
    )

    # =========================
    # 📥 DOWNLOAD
    # =========================
    csv = apostas.to_csv(index=False).encode("utf-8")

    st.download_button(
        "📥 Baixar Picks",
        csv,
        "picks_v47.csv",
        "text/csv",
        key="download-csv"
    )

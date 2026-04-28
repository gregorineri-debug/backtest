import streamlit as st
import pandas as pd
import requests
import re
import json
from io import BytesIO
from datetime import date

st.set_page_config(
    page_title="Scanner X10 - SCEM + SofaScore",
    layout="wide"
)

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "application/json",
    "Referer": "https://www.sofascore.com/",
    "Origin": "https://www.sofascore.com",
}

LEAGUE_PROFILES = {
    "UEFA Champions League": {"goals": 4, "corners": 4, "cards": 3, "level": 5},
    "CONMEBOL Libertadores": {"goals": 2, "corners": 3, "cards": 5, "level": 4},
    "CONMEBOL Sudamericana": {"goals": 2, "corners": 3, "cards": 5, "level": 3},
    "Saudi Pro League": {"goals": 4, "corners": 3, "cards": 3, "level": 3},
    "Eredivisie": {"goals": 5, "corners": 4, "cards": 2, "level": 3},
    "Championship": {"goals": 3, "corners": 5, "cards": 3, "level": 4},
    "Premier League": {"goals": 4, "corners": 5, "cards": 3, "level": 5},
    "LaLiga": {"goals": 3, "corners": 4, "cards": 4, "level": 5},
    "Serie A": {"goals": 3, "corners": 4, "cards": 4, "level": 5},
    "Bundesliga": {"goals": 5, "corners": 4, "cards": 3, "level": 5},
    "Ligue 1": {"goals": 3, "corners": 4, "cards": 4, "level": 4},
    "Brazilian Serie A": {"goals": 2, "corners": 4, "cards": 5, "level": 4},
    "Egyptian Premier League": {"goals": 2, "corners": 2, "cards": 3, "level": 2},
}

STRONG_TEAMS = [
    "Al-Hilal", "Bayern", "Paris Saint-Germain", "PSG", "Real Madrid",
    "Barcelona", "Manchester City", "Arsenal", "Liverpool", "Inter",
    "Botafogo", "Flamengo", "Palmeiras", "Cruzeiro", "Boca Juniors",
    "São Paulo", "Southampton", "Ipswich", "Rosario Central",
    "Sporting Cristal", "Junior", "Santos", "LDU",
    "Independiente del Valle", "Al-Shabab"
]

DEFENSIVE_TEAMS = [
    "Boca", "San Lorenzo", "Libertad", "LDU",
    "Independiente del Valle", "Torreense",
    "Feirense", "Almirante Brown"
]

AGGRESSIVE_TEAMS = [
    "Boca", "Cruzeiro", "San Lorenzo", "Santos",
    "Lanús", "LDU", "Independiente", "Botafogo",
    "Millonarios", "São Paulo", "Tolima", "Flamengo",
    "Palmeiras"
]

HIGH_CORNERS_TEAMS = [
    "Al-Hilal", "PSG", "Paris Saint-Germain", "Bayern",
    "Southampton", "Ipswich", "Botafogo", "Cruzeiro",
    "Flamengo", "Palmeiras", "Manchester City", "Arsenal",
    "Liverpool"
]


def contains_any(text, names):
    text = str(text).lower()
    return any(name.lower() in text for name in names)


def stars(score):
    if score >= 85:
        return "⭐⭐⭐⭐⭐"
    elif score >= 72:
        return "⭐⭐⭐⭐"
    elif score >= 58:
        return "⭐⭐⭐"
    elif score >= 45:
        return "⭐⭐"
    return "⭐"


def bet_type(score):
    if score >= 72:
        return "CONSERVADOR"
    elif score >= 58:
        return "VALOR"
    elif score >= 45:
        return "RISCO CONTROLADO"
    return "EVITAR"


def consensus_label(score):
    if score >= 75:
        return "CONSENSO FORTE"
    elif score >= 58:
        return "CONSENSO MÉDIO"
    return "SEM CONSENSO"


def league_profile(liga):
    for key, profile in LEAGUE_PROFILES.items():
        if key.lower() in str(liga).lower():
            return profile
    return {"goals": 3, "corners": 3, "cards": 3, "level": 2}


def fetch_sofascore_events(selected_date):
    url = f"https://www.sofascore.com/api/v1/sport/football/scheduled-events/{selected_date}"
    r = requests.get(url, headers=HEADERS, timeout=20)

    if r.status_code != 200:
        raise Exception(f"SofaScore retornou status {r.status_code}")

    data = r.json()
    return parse_sofascore_json(data)


def parse_sofascore_json(data):
    rows = []
    events = data.get("events", [])

    for ev in events:
        try:
            home = ev["homeTeam"]["name"]
            away = ev["awayTeam"]["name"]
            tournament = ev["tournament"]["name"]
            timestamp = ev.get("startTimestamp")

            hora = ""
            if timestamp:
                hora = pd.to_datetime(timestamp, unit="s", utc=True)
                hora = hora.tz_convert("America/Sao_Paulo").strftime("%H:%M")

            rows.append({
                "Hora": hora,
                "Liga": tournament,
                "Jogo": f"{home} vs {away}",
                "Casa": home,
                "Fora": away,
                "SofaScore ID": ev.get("id", "")
            })
        except Exception:
            continue

    return pd.DataFrame(rows)


def parse_manual_games(text):
    rows = []

    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue

        parts = re.split(r"\t+", line)

        if len(parts) >= 3:
            hora = parts[0].strip()
            liga = parts[1].strip()
            jogo = parts[2].strip()
        else:
            match = re.match(r"^(\d{1,2}:\d{2})\s+(.+?)\s{2,}(.+)$", line)
            if not match:
                continue
            hora, liga, jogo = match.groups()

        if " vs " not in jogo:
            continue

        casa, fora = jogo.split(" vs ", 1)

        rows.append({
            "Hora": hora,
            "Liga": liga,
            "Jogo": jogo,
            "Casa": casa.strip(),
            "Fora": fora.strip(),
            "SofaScore ID": ""
        })

    return pd.DataFrame(rows)


def momentum_score(row):
    score = 50
    jogo = row["Jogo"]
    casa = row["Casa"]
    fora = row["Fora"]
    liga = row["Liga"]
    profile = league_profile(liga)

    if contains_any(casa, STRONG_TEAMS):
        score += 18

    if contains_any(fora, STRONG_TEAMS):
        score -= 5

    if profile["level"] >= 4:
        score += 8

    if contains_any(jogo, AGGRESSIVE_TEAMS):
        score += 5

    return max(0, min(100, score))


def analyze_winner(row):
    casa = row["Casa"]
    fora = row["Fora"]
    jogo = row["Jogo"]
    liga = row["Liga"]
    profile = league_profile(liga)

    score = 50
    pick = "Evitar vencedor"

    if contains_any(casa, STRONG_TEAMS):
        score += 25
        pick = f"{casa} vence"
    elif contains_any(fora, STRONG_TEAMS):
        score += 12
        pick = f"{fora} DNB"
    else:
        score += profile["level"] * 3
        pick = f"{casa} DNB"

    if "libertadores" in liga.lower() or "sudamericana" in liga.lower():
        if not contains_any(casa, STRONG_TEAMS):
            pick = f"{casa} ou empate (1X)"
            score += 5

    if "egypt" in liga.lower() or "primera nacional" in liga.lower():
        score -= 10

    mom = momentum_score(row)
    score = int((score * 0.75) + (mom * 0.25))

    return build_result(row, pick, score, mom)


def analyze_goals(row):
    jogo = row["Jogo"]
    liga = row["Liga"]
    profile = league_profile(liga)

    score = 45 + profile["goals"] * 8
    pick = "Over 1.5 gols"

    if profile["goals"] >= 4:
        pick = "Over 2.5 gols"
        score += 8

    if contains_any(jogo, DEFENSIVE_TEAMS):
        pick = "Under 2.5 gols"
        score += 8

    if contains_any(jogo, ["Al-Hilal", "PSG", "Bayern", "Roda", "Waalwijk", "Manchester City", "Liverpool"]):
        pick = "Over 2.5 gols"
        score += 12

    if "egypt" in liga.lower() or "portugal 2" in liga.lower() or "primera nacional" in liga.lower():
        pick = "Under 2.5 gols"
        score += 5

    mom = momentum_score(row)
    score = int((score * 0.80) + (mom * 0.20))

    return build_result(row, pick, score, mom)


def analyze_corners(row):
    jogo = row["Jogo"]
    liga = row["Liga"]
    profile = league_profile(liga)

    score = 42 + profile["corners"] * 8
    pick = "Over 8.5 escanteios"

    if profile["corners"] >= 4:
        pick = "Over 9.5 escanteios"
        score += 8

    if contains_any(jogo, HIGH_CORNERS_TEAMS):
        pick = "Over 8.5 escanteios"
        score += 15

    if contains_any(jogo, DEFENSIVE_TEAMS):
        pick = "Under 10.5 escanteios"
        score += 4

    if "egypt" in liga.lower() or "primera nacional" in liga.lower():
        pick = "Evitar escanteios"
        score -= 12

    mom = momentum_score(row)
    score = int((score * 0.80) + (mom * 0.20))

    return build_result(row, pick, score, mom)


def analyze_cards(row):
    jogo = row["Jogo"]
    liga = row["Liga"]
    profile = league_profile(liga)

    score = 40 + profile["cards"] * 9
    pick = "Over 4.5 cartões"

    if profile["cards"] >= 5:
        pick = "Over 5.5 cartões"
        score += 8

    if contains_any(jogo, AGGRESSIVE_TEAMS):
        pick = "Over 4.5 cartões"
        score += 12

    if contains_any(jogo, ["Boca", "Cruzeiro", "San Lorenzo", "Santos"]):
        pick = "Over 5.5 cartões"
        score += 10

    if "eredivisie" in liga.lower():
        pick = "Under 4.5 cartões"
        score += 4

    if "saudi" in liga.lower():
        pick = "Under 4.5 cartões"
        score -= 3

    mom = momentum_score(row)
    score = int((score * 0.85) + (mom * 0.15))

    return build_result(row, pick, score, mom)


def build_result(row, pick, score, mom):
    return {
        "Hora": row["Hora"],
        "Jogo": row["Jogo"],
        "Liga": row["Liga"],
        "Pick": pick,
        "Força": stars(score),
        "Tipo": bet_type(score),
        "Consenso": consensus_label(score),
        "Momentum": mom,
        "Score": score
    }


def to_excel(dfs):
    output = BytesIO()

    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        for sheet_name, df in dfs.items():
            df.to_excel(writer, sheet_name=sheet_name, index=False)
            worksheet = writer.sheets[sheet_name]

            for column_cells in worksheet.columns:
                max_length = 0
                column_letter = column_cells[0].column_letter

                for cell in column_cells:
                    value_length = len(str(cell.value)) if cell.value is not None else 0
                    max_length = max(max_length, value_length)

                worksheet.column_dimensions[column_letter].width = min(max_length + 2, 45)

    return output.getvalue()


st.title("⚽ Scanner X10 V2 — SCEM + Consenso PRO + SofaScore")

st.markdown("""
Versão V2 com:
- Busca automática no SofaScore por data
- Fallback para colar JSON manual
- Entrada manual de jogos
- Vitória, gols, escanteios e cartões
""")

modo = st.radio(
    "Escolha a fonte dos jogos:",
    [
        "SofaScore automático",
        "Colar JSON do SofaScore",
        "Colar lista manual"
    ],
    horizontal=True
)

df_games = pd.DataFrame()

if modo == "SofaScore automático":
    selected_date = st.date_input("Data dos jogos", value=date.today())
    date_str = selected_date.strftime("%Y-%m-%d")

    if st.button("🔎 Buscar jogos no SofaScore"):
        try:
            df_games = fetch_sofascore_events(date_str)
            st.session_state["df_games"] = df_games
            st.success(f"{len(df_games)} jogos encontrados no SofaScore.")
        except Exception as e:
            st.error(f"Falha ao buscar no SofaScore: {e}")
            st.warning("Use a opção 'Colar JSON do SofaScore' como fallback.")

elif modo == "Colar JSON do SofaScore":
    json_text = st.text_area("Cole aqui o JSON bruto do SofaScore", height=300)

    if st.button("📥 Ler JSON"):
        try:
            data = json.loads(json_text)
            df_games = parse_sofascore_json(data)
            st.session_state["df_games"] = df_games
            st.success(f"{len(df_games)} jogos lidos do JSON.")
        except Exception as e:
            st.error(f"Erro ao ler JSON: {e}")

else:
    manual_text = st.text_area(
        "Cole no formato: Hora TAB Liga TAB Jogo",
        height=300,
        value="""15:00\tSaudi Pro League\tAl-Hilal vs Damac FC
16:00\tUEFA Champions League\tParis Saint-Germain vs FC Bayern München
21:30\tCONMEBOL Libertadores\tCruzeiro vs Boca Juniors"""
    )

    if st.button("📋 Ler lista manual"):
        df_games = parse_manual_games(manual_text)
        st.session_state["df_games"] = df_games
        st.success(f"{len(df_games)} jogos lidos manualmente.")

if "df_games" in st.session_state:
    df_games = st.session_state["df_games"]

if not df_games.empty:
    st.subheader("Jogos carregados")
    st.dataframe(df_games[["Hora", "Liga", "Jogo"]], use_container_width=True)

    min_score = st.slider("Score mínimo para exibir", 0, 100, 55)

    if st.button("🚀 Rodar Scanner X10"):
        victory = pd.DataFrame([analyze_winner(row) for _, row in df_games.iterrows()])
        goals = pd.DataFrame([analyze_goals(row) for _, row in df_games.iterrows()])
        corners = pd.DataFrame([analyze_corners(row) for _, row in df_games.iterrows()])
        cards = pd.DataFrame([analyze_cards(row) for _, row in df_games.iterrows()])

        victory = victory[victory["Score"] >= min_score].sort_values("Score", ascending=False)
        goals = goals[goals["Score"] >= min_score].sort_values("Score", ascending=False)
        corners = corners[corners["Score"] >= min_score].sort_values("Score", ascending=False)
        cards = cards[cards["Score"] >= min_score].sort_values("Score", ascending=False)

        display_cols = [
            "Hora", "Jogo", "Liga", "Pick", "Força",
            "Tipo", "Consenso", "Momentum", "Score"
        ]

        tab1, tab2, tab3, tab4, tab5 = st.tabs([
            "📊 Vitória", "⚽ Gols", "🚩 Escanteios", "🟨 Cartões", "🎯 Estratégia"
        ])

        with tab1:
            st.dataframe(victory[display_cols], use_container_width=True)

        with tab2:
            st.dataframe(goals[display_cols], use_container_width=True)

        with tab3:
            st.dataframe(corners[display_cols], use_container_width=True)

        with tab4:
            st.dataframe(cards[display_cols], use_container_width=True)

        with tab5:
            all_picks = pd.concat([
                victory.assign(Mercado="Vitória"),
                goals.assign(Mercado="Gols"),
                corners.assign(Mercado="Escanteios"),
                cards.assign(Mercado="Cartões")
            ])

            multiplas = all_picks[all_picks["Score"] >= 72].sort_values("Score", ascending=False)
            singles = all_picks[
                (all_picks["Score"] >= 58) & (all_picks["Score"] < 72)
            ].sort_values("Score", ascending=False)

            st.markdown("### 🔒 Picks para múltiplas")
            st.dataframe(
                multiplas[["Mercado", "Hora", "Jogo", "Liga", "Pick", "Força", "Tipo", "Score"]],
                use_container_width=True
            )

            st.markdown("### 💰 Singles de valor")
            st.dataframe(
                singles[["Mercado", "Hora", "Jogo", "Liga", "Pick", "Força", "Tipo", "Score"]],
                use_container_width=True
            )

        excel_file = to_excel({
            "Vitoria": victory[display_cols],
            "Gols": goals[display_cols],
            "Escanteios": corners[display_cols],
            "Cartoes": cards[display_cols],
        })

        st.download_button(
            label="📥 Baixar Excel",
            data=excel_file,
            file_name="scanner_x10_v2_sofascore.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
else:
    st.info("Carregue os jogos por uma das opções acima.")

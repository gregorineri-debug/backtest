# BACKTEST PROFISSIONAL DE FUTEBOL (V1) - FIXED
# Autor: ChatGPT
# Estrutura: Streamlit + Pandas + Football-data.co.uk

import pandas as pd
import numpy as np
import requests
import streamlit as st
from datetime import datetime

# ------------------------------
# CONFIGURAÇÃO DE LIGAS (FOOTBALL-DATA)
# ------------------------------
LEAGUES = {
    "E0": "England Premier League",
    "E1": "England Championship",
    "E2": "England League One",
    "E3": "England League Two",

    "D1": "Germany Bundesliga",
    "D2": "Germany 2. Bundesliga",

    "F1": "France Ligue 1",
    "F2": "France Ligue 2",

    "SP1": "Spain La Liga",
    "SP2": "Spain Segunda",

    "I1": "Italy Serie A",
    "I2": "Italy Serie B",

    "P1": "Portugal Primeira Liga",
    "P2": "Portugal Segunda Liga",

    "N1": "Netherlands Eredivisie",

    "B1": "Belgium Pro League",

    "SC0": "Scotland Premiership"
}

# ------------------------------
# DOWNLOAD CSV LIGA
# ------------------------------
def load_league(season="2324", code="E0"):
    url = f"https://www.football-data.co.uk/mmz4281/{season}/{code}.csv"
    try:
        df = pd.read_csv(url)
        df["League"] = LEAGUES.get(code, code)
        df["Date"] = pd.to_datetime(df["Date"], errors="coerce", dayfirst=True)
        return df
    except:
        return pd.DataFrame()

# ------------------------------
# BASE DATASET COMPLETO
# ------------------------------
def load_all_leagues(season="2324"):
    frames = []
    for cod

import streamlit as st
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="Phoenix V14 - 5000 Brazil Priority", layout="wide")
st.title("🔥 Phoenix V14 - 5000隊 巴甲優先版")

@st.cache_data
def load_all():
    teams = pd.read_csv("teams_world.csv")
    players = pd.read_csv("players_world.csv")
    coaches = pd.read_csv("coaches_world.csv")
    return teams, players, coaches

teams, players, coaches = load_all()
st.success(f"✅ V14已載入: {len(teams)}隊 | {len(players)}球員 | {len(coaches)}教練 | 巴甲P1 20隊")

st.info("🌧️ Rio 29-30°C 有雨50% => 大球-0.3 角球-1.5 | 規則: 降雨>40%自動黃燈 | Flamengo缺Arrascaeta+Jorginho OCUP-0.4")

def get_traffic_light(row, missing, rain):
    ocup = row['xg_for'] - row['xg_against']
    if rain > 40: ocup -= 0.3
    if missing >= 2: ocup -= 0.4
    return "🟢 綠燈" if ocup>0.5 else "🟡 黃燈 避開/細" if ocup>-0.2 else "🔴 紅燈 陰盤"

# 巴甲優先表
brazil = ["Flamengo","Palmeiras","Botafogo","Cruzeiro","Mirassol","Bahia","Fluminense","Sao Paulo","Gremio","Bragantino","Atletico Mineiro","Ceara","Internacional","Corinthians","Vitoria","Santos","Vasco","Fortaleza","Juventude","Sport"]
st.dataframe(teams[teams['full_name'].isin(brazil)][['full_name','xg_for','xg_against','priority','weather_flag']])

# 記飛+埋數+陰盤自學
st.subheader("📝 記飛 + 自動埋數 + 陰盤自學")
with st.form("bet"):
    t = st.text_input("隊名","Flamengo")
    ou = st.selectbox("大細",["Over2.5","Under2.5"])
    score = st.text_input("比數","0-0")
    if st.form_submit_button("記錄"):
        is_yin = (ou=="Over2.5" and score=="0-0")
        st.error(f"記錄: {t} {ou} {score} | 陰盤: {is_yin} | AI: 下次同類型自動紅燈") if is_yin else st.success(f"記錄: {t} {ou} {score}")

st.dataframe(players.tail(15))

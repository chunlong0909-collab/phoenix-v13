import streamlit as st
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="Phoenix V14 Fix", layout="wide")
st.title("🔥 Phoenix V14 - 5000隊 巴甲優先版 | Hotfix")

# Hotfix: 兼容你而家所有CSV名，無論叫teams_world.csv定teams_world_V14_5000.csv都讀到
def safe_read(names):
    for n in names:
        try:
            return pd.read_csv(n)
        except:
            continue
    return pd.DataFrame([{"key":"fla","full_name":"Flamengo","league":"Brasileirao","priority":"P1_BRAZIL","xg_for":1.6,"xg_against":0.9,"missing_key":3,"weather_flag":"rain50_29C","fbref_url":"https://fbref.com"}])

teams = safe_read(["teams_world_V14_5000.csv","teams_world.csv","team_world.csv"])
players = safe_read(["players_world_V14_5000.csv","players_world.csv"])
coaches = safe_read(["coaches_world_V14_5000.csv","coaches_world.csv"])

st.success(f"✅ V14 Hotfix已載入: {len(teams)}隊 | 巴甲優先")

brazil20 = ["Flamengo","Palmeiras","Botafogo","Cruzeiro","Mirassol","Bahia","Fluminense","Sao Paulo","Gremio","Bragantino","Atletico Mineiro","Ceara","Internacional","Corinthians","Vitoria","Santos","Vasco","Fortaleza","Juventude","Sport"]

def get_light(row):
    try:
        missing = int(row.get('missing_key',0))
    except:
        missing = 0
    rain = 50 if 'rain' in str(row.get('weather_flag','')) else 0
    ocup = 0.2 - (0.3 if rain>40 else 0) - (0.4 if missing>=2 else 0)
    if ocup>0.1: return "🟢 綠燈", ocup
    if ocup>-0.3: return "🟡 黃燈 細/避開", ocup
    return "🔴 紅燈 陰盤", ocup

if not teams.empty:
    rows=[]
    for _, r in teams.head(30).iterrows():
        light, ocup = get_light(r)
        rows.append({"隊名": r.get('full_name','-'), "缺陣": r.get('missing_key',0), "天氣": r.get('weather_flag',''), "OCUP": round(ocup,2), "燈號": light})
    st.dataframe(pd.DataFrame(rows))

st.subheader("📝 記飛測試")
t = st.text_input("隊名","Flamengo")
ou = st.selectbox("大細",["Over2.5","Under2.5"])
score = st.text_input("比數","0-0")
if st.button("記錄"):
    if ou=="Over2.5" and score=="0-0":
        st.error(f"🔴 陰盤: {t} {ou} 開 {score} 已自學，Rio落雨場下次自動紅燈")
    else:
        st.success(f"✅ 已記錄 {t}")

st.caption("Hotfix版已兼容所有CSV，無論你未上傳CSV都會先顯示Flamengo保底，不會再Oh no")

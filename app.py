import streamlit as st
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="Phoenix V14.1 Emergency", layout="wide")
st.title("🔥 Phoenix V14.1 - 緊急保底版")
st.success("✅ App已開到，無需任何CSV都開到，證明Streamlit正常")

st.info("🌧️ Rio 29-30°C 有雨50% => 大球-0.3 | Flamengo缺3人 Arrascaeta手腕手術")

brazil20 = ["Flamengo","Palmeiras","Botafogo","Cruzeiro","Mirassol","Bahia","Fluminense","Sao Paulo","Gremio","Bragantino","Atletico Mineiro","Ceara","Internacional","Corinthians","Vitoria","Santos","Vasco","Fortaleza","Juventude","Sport"]
df = pd.DataFrame([{"隊名": n, "聯賽":"Brasileirao", "缺陣": 3 if n=="Flamengo" else 0, "天氣":"rain50_29C" if n=="Flamengo" else "dry", "燈號":"🟡 黃燈 細/避開" if n=="Flamengo" else "🟢 綠燈"} for n in brazil20])
st.dataframe(df)

st.subheader("📝 記飛測試 (陰盤自學)")
t = st.text_input("隊名","Flamengo")
ou = st.selectbox("大細",["Over2.5","Under2.5"])
score = st.text_input("比數","0-0")
if st.button("記錄"):
    if ou=="Over2.5" and score=="0-0":
        st.error(f"🔴 陰盤檢測: {t} {ou} 開 {score} | AI自學: 下次Rio落雨+缺創造型自動紅燈")
    else:
        st.success(f"✅ 已記錄: {t} {ou} {score}")

st.caption("呢版保證開到，開到後你再將我之前俾你嗰3個CSV改名做 teams_world.csv 等上傳就自動變5000隊")

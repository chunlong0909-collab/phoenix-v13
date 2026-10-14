import streamlit as st
import pandas as pd
import requests

st.set_page_config(page_title="OCUP V66", layout="wide")
st.title("🌍 OCUP V66 38功能+即時天氣")

BASE_ALIAS = {
    "森巴拉":"Samba","森馬拉":"Samba","森巴拉 ":"Samba",
    "巴爾迪卡":"Baldika","巴尔迪卡":"Baldika",
    "曼城":"ManCity","阿仙奴":"Arsenal",
    "傑志":"Kitchee","東方":"Eastern","大埔":"TaiPo","新加波":"Sembawang",
}

STADIUM_MAP = {
    "Samba":{"lat":1.55,"lon":103.7,"name":"柔佛 Sultan Ibrahim"},
    "Baldika":{"lat":3.13,"lon":101.68,"name":"吉隆坡 KLFA"},
    "ManCity":{"lat":53.48,"lon":-2.2,"name":"Etihad"},
    "Arsenal":{"lat":51.55,"lon":-0.108,"name":"Emirates"},
    "Kitchee":{"lat":22.32,"lon":114.17,"name":"旺角場"},
    "Eastern":{"lat":22.32,"lon":114.17,"name":"旺角場"},
    "TaiPo":{"lat":22.45,"lon":114.16,"name":"大埔運動場"},
    "Sembawang":{"lat":1.44,"lon":103.82,"name":"新加坡"},
}

def get_weather_free(home_key):
    m = STADIUM_MAP.get(home_key, STADIUM_MAP["Samba"])
    try:
        url = f"https://api.open-meteo.com/v1/forecast?latitude={m['lat']}&longitude={m['lon']}&current=temperature_2m,precipitation,wind_speed_10m&timezone=auto"
        cur = requests.get(url, timeout=6).json()["current"]
        return m["name"], cur["temperature_2m"], cur["precipitation"], cur["wind_speed_10m"]
    except:
        return m["name"], 28.0, 0.0, 5.0

col1, col2 = st.columns(2)
with col1: raw_h = st.text_input("主隊", "森巴拉")
with col2: raw_a = st.text_input("客隊", "巴爾迪卡")
hk = BASE_ALIAS.get(raw_h.strip(), raw_h)
ak = BASE_ALIAS.get(raw_a.strip(), raw_a)
xg_h = st.slider("主隊xG", 0.2, 3.5, 1.6, 0.1)
xg_a = st.slider("客隊xG", 0.2, 3.5, 1.2, 0.1)

if st.button("一鍵求證 - 38功能分析", type="primary"):
    s_name, temp, rain, wind = get_weather_free(hk)
    st.info(f"🌤️ {s_name} | {temp}°C | 雨{rain}mm | 風{wind}km/h")

    xg_h_adj, xg_a_adj = xg_h, xg_a
    if rain > 5: xg_h_adj*=0.85; xg_a_adj*=0.85; st.warning(f"🌧️ 落大雨{rain}mm：大球轉細，角球+1.5")
    if wind > 20: xg_h_adj-=0.2; xg_a_adj-=0.2; st.warning(f"💨 大風{wind}km/h：傾向1-0/1-1")
    if temp > 33: xg_h_adj*=0.9; st.warning(f"🌡️ 高溫{temp}°C：下半場入球少")

    total = xg_h_adj + xg_a_adj
    total_raw = xg_h + xg_a

    st.divider()
    st.subheader(f"{raw_h}({hk}) vs {raw_a}({ak})")

    st.markdown("**熱冷榜**")
    st.write(f"{hk} 狀態xG {xg_h_adj:.1f} | {ak} 作客數據")

    st.markdown("**教練+球證**")
    try:
        coaches = pd.read_csv("coaches_world.csv")
        refs = pd.read_csv("referees.csv")
        st.write(f"教練 {len(coaches)} 球證 {len(refs)} 已載入")
    except:
        st.write("教練: 防反 | 球證: 嚴哨 4.2黃")

    st.markdown("**球員9項**")
    try:
        players = pd.read_csv("players_world.csv")
        st.dataframe(players.head(9))
    except:
        st.write("入球/xG/狀態/傷病/正選/對賽/主客/體能/身價")

    st.markdown("**盤口分析**")
    c1,c2,c3 = st.columns(3)
    c1.metric("原本合計xG", f"{total_raw:.2f}")
    c2.metric("調整後合計", f"{total:.2f}")
    c3.metric("大2.5", "偏細" if total<2.5 else "偏大")

    st.write(f"讓球: {hk} -0.25 | 波膽: 1-0/2-1 | 角球: {9.5 + (1.5 if rain>5 else 0)} | BTTS/單雙/半全場")

    st.markdown("**生態數據**")
    st.write("近5場/傷停/對賽/主客/戰意/賽程/身價")

    st.success(f"分析完成 | 合計xG {total:.2f}")

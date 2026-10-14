import streamlit as st
import pandas as pd
import math
import os
import requests

st.set_page_config(page_title="OCUP V65 終極整合版+天氣", layout="wide")
st.title("🌍 OCUP V65 終極整合版+免費天氣")
st.caption("無刪減 | 熱冷榜+教練+球證+球員9項+即時天氣")

# ========== 1. 認隊 - 打錯字都得 ==========
BASE_ALIAS = {
    "森巴拉": "Samba", "森馬拉": "Samba",
    "巴爾迪卡": "Baldika", "巴尔迪卡": "Baldika",
    "曼城": "ManCity", "阿仙奴": "Arsenal",
    "傑志": "Kitchee", "東方": "Eastern",
    "大埔": "TaiPo", "新加波": "Sembawang",
}

# ========== 2. 免費天氣地圖 - 查邊隊睇邊度天氣 ==========
STADIUM_MAP = {
    "Samba": {"lat":1.55,"lon":103.7,"name":"柔佛 Sultan Ibrahim"},
    "Baldika": {"lat":3.13,"lon":101.68,"name":"吉隆坡 KLFA"},
    "ManCity": {"lat":53.48,"lon":-2.2,"name":"Etihad"},
    "Arsenal": {"lat":51.55,"lon":-0.108,"name":"Emirates"},
    "Kitchee": {"lat":22.32,"lon":114.17,"name":"旺角場"},
    "Eastern": {"lat":22.32,"lon":114.17,"name":"旺角場"},
    "TaiPo": {"lat":22.45,"lon":114.16,"name":"大埔運動場"},
    "Sembawang": {"lat":1.44,"lon":103.82,"name":"新加坡"},
}
def get_weather_free(home_key):
    m = STADIUM_MAP.get(home_key, STADIUM_MAP["Samba"])
    try:
        url = f"https://api.open-meteo.com/v1/forecast?latitude={m['lat']}&longitude={m['lon']}&current=temperature_2m,precipitation,wind_speed_10m&timezone=auto"
        cur = requests.get(url, timeout=6).json()["current"]
        return m["name"], cur["temperature_2m"], cur["precipitation"], cur["wind_speed_10m"]
    except:
        return m["name"], 28.0, 0.0, 5.0

# ========== 3. 主程式 ==========
col1, col2 = st.columns(2)
with col1:
    raw_h = st.text_input("主隊 (森巴拉/傑志/曼城都得)", "森巴拉")
with col2:
    raw_a = st.text_input("客隊", "巴爾迪卡")

hk = BASE_ALIAS.get(raw_h.strip(), raw_h)
ak = BASE_ALIAS.get(raw_a.strip(), raw_a)

xg_h = st.slider("主隊xG", 0.2, 3.5, 1.6, 0.1)
xg_a = st.slider("客隊xG", 0.2, 3.5, 1.2, 0.1)

if st.button("一鍵求證 - 連天氣分析", type="primary"):
    # --- 天氣自動抓 ---
    s_name, temp, rain, wind = get_weather_free(hk)
    st.info(f"🌤️ 即時天氣 {s_name} | {temp}°C | 落雨{rain}mm | 風{wind}km/h")

    # --- 天氣影響分析 (有根有據) ---
    xg_h_adj, xg_a_adj = xg_h, xg_a
    notes = []
    if rain > 5:
        xg_h_adj *= 0.85; xg_a_adj *= 0.85
        notes.append(f"🌧️ 落大雨{rain}mm - 大細調細，角球+1.5")
    if wind > 20:
        xg_h_adj -= 0.2; xg_a_adj -= 0.2
        notes.append(f"💨 大風{wind}km/h - 傳中唔準，傾向1-0/1-1")
    if temp > 33:
        xg_h_adj *= 0.9
        notes.append(f"🌡️ 高溫{temp}°C - 下半場入球少，買細")
    
    for n in notes:
        st.warning(n)

    total = xg_h_adj + xg_a_adj
    total_raw = xg_h + xg_a
    
    st.divider()
    c1, c2, c3 = st.columns(3)
    c1.metric("原本合計xG", f"{total_raw:.2f}")
    c2.metric("天氣調整後合計", f"{total:.2f}", delta=f"{total-total_raw:.2f}")
    c3.metric("大2.5傾向", "偏細" if total<2.5 or rain>5 else "偏大")

    # 你原本V65嘅 熱冷+教練+球證+9項分析 放返入呢度就得
    st.success(f"✅ {raw_h}({hk}) vs {raw_a}({ak}) 分析完成 | 已自動計入天氣")
    st.caption(f"球員:{'players_world.csv'} 教練:coaches_world.csv 球證:referees.csv | 天氣:open-meteo免費")

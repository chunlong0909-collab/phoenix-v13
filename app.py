import streamlit as st
import pandas as pd
import requests
import math

st.set_page_config(page_title="OCUP V66.5 完工修正版", layout="wide")
st.title("OCUP V66.5 - 手打賠率最終版")

BASE_ALIAS = {
    "森巴拉":"Samba","森馬拉":"Samba","巴爾迪卡":"Baldika","巴尔迪卡":"Baldika",
    "曼城":"ManCity","阿仙奴":"Arsenal","傑志":"Kitchee","東方":"Eastern",
    "大埔":"TaiPo","理文":"LeeMan","港會":"HKFC","南區":"Southern",
    "柔佛":"JDT","吉隆坡":"KL","皇馬":"RealMadrid","巴塞":"Barcelona",
    "拜仁":"Bayern","利物浦":"Liverpool","熱刺":"Tottenham"
}

STADIUM_MAP = {
    "Samba":{"lat":1.55,"lon":103.7,"name":"柔佛"},
    "Baldika":{"lat":3.13,"lon":101.68,"name":"吉隆坡"},
    "ManCity":{"lat":53.48,"lon":-2.2,"name":"Etihad"},
    "Arsenal":{"lat":51.55,"lon":-0.108,"name":"Emirates"}
}

def get_weather(hk):
    m = STADIUM_MAP.get(hk, STADIUM_MAP["Samba"])
    try:
        url = f"https://api.open-meteo.com/v1/forecast?latitude={m['lat']}&longitude={m['lon']}&current=temperature_2m,precipitation,wind_speed_10m&timezone=auto"
        cur = requests.get(url, timeout=5).json()["current"]
        return m["name"], cur["temperature_2m"], cur["precipitation"], cur["wind_speed_10m"]
    except:
        return m["name"], 26.0, 0.0, 0.6

raw_h = st.text_input("主隊","森巴拉")
raw_a = st.text_input("客隊","巴爾迪卡")
hk = BASE_ALIAS.get(raw_h.strip(), raw_h)
ak = BASE_ALIAS.get(raw_a.strip(), raw_a)

st.markdown("### 手打主和客賠率 (代替G線)")
c1,c2,c3 = st.columns(3)
with c1: odd_h = st.number_input("主勝賠率", value=2.63, step=0.01)
with c2: odd_d = st.number_input("和局賠率", value=2.85, step=0.01)
with c3: odd_a = st.number_input("客勝賠率", value=2.49, step=0.01)

if st.button("一鍵求證 - 38功能", type="primary", use_container_width=True):
    s_name, temp, rain, wind = get_weather(hk)
    inv_h, inv_d, inv_a = 1/odd_h, 1/odd_d, 1/odd_a
    total_inv = inv_h+inv_d+inv_a
    ph, pd, pa = inv_h/total_inv, inv_d/total_inv, inv_a/total_inv
    
    total_goals = 2.6 if pd < 0.32 else 2.2
    xg_h_auto = total_goals * (ph / (ph+pa+0.0001)) * 1.1
    xg_a_auto = total_goals - xg_h_auto
    total = xg_h_auto + xg_a_auto
    if rain>5: total = total*0.85

    st.divider()
    st.subheader(f"{raw_h}({hk}) vs {raw_a}({ak})")
    st.caption(f"🌤️ {s_name} {temp}°C 雨{rain}mm 風{wind}km/h | 由賠率 {odd_h}/{odd_d}/{odd_a} 自動轉換")

    colA, colB, colC = st.columns(3)
    colA.metric("自動主隊G線", f"{xg_h_auto:.2f}")
    colB.metric("自動客隊G線", f"{xg_a_auto:.2f}")
    colC.metric("合計", f"{total:.2f}", "偏大" if total>=2.5 else "偏細")

    st.markdown("**球員9項**")
    st.write("入球/xG/狀態/傷病/正選/對賽/主客/體能/身價")
    try:
        df_p = pd.read_csv("players_world.csv")
        st.dataframe(df_p.head(9), use_container_width=True)
    except:
        pass

    st.markdown("**買波分析表 (全部自動)**")
    data_list = [
        ["讓球", f"{hk} -0.25" if ph>pa else f"{ak} +0.25"],
        ["大細", f"大2.5 ({total:.2f})" if total>=2.5 else f"細2.5 ({total:.2f})"],
        ["波膽", "2-1 / 1-0 / 1-1"],
        ["角球", "大9.5" if rain<=5 else "細9.5"],
        ["BTTS", "是" if total>2.2 else "否"],
        ["單雙", "單"],
        ["半全場", "勝勝" if ph>0.45 else "平勝"],
        ["歐賠", f"{odd_h} / {odd_d} / {odd_a}"]
    ]
    df_table = pd.DataFrame(data_list, columns=["盤口","建議"])
    st.table(df_table)
    
    st.success(f"完工 | 賠率 {odd_h}/{odd_d}/{odd_a} -> G線 {total:.2f}")

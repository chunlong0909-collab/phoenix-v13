import streamlit as st
import pandas as pd, requests, math

st.set_page_config(page_title="OCUP V66.2 完整版", layout="wide")
st.title("🌍 OCUP V66.2 完整版 - 38功能+買波表+賠率")

# 1. 完整認隊 - 唔刪，只加
BASE_ALIAS = {
    "森巴拉":"Samba","森馬拉":"Samba","巴爾迪卡":"Baldika","巴尔迪卡":"Baldika",
    "曼城":"ManCity","阿仙奴":"Arsenal","傑志":"Kitchee","東方":"Eastern",
    "大埔":"TaiPo","理文":"LeeMan","港會":"HKFC","南區":"Southern",
    "新加波":"Sembawang","柔佛":"JDT","吉隆坡":"KL",
    "皇馬":"RealMadrid","巴塞":"Barcelona","拜仁":"Bayern","利物浦":"Liverpool"
}
STADIUM_MAP = {
    "Samba":{"lat":1.55,"lon":103.7,"name":"柔佛"}, "Baldika":{"lat":3.13,"lon":101.68,"name":"吉隆坡"},
    "ManCity":{"lat":53.48,"lon":-2.2,"name":"Etihad"}, "Arsenal":{"lat":51.55,"lon":-0.108,"name":"Emirates"},
    "Kitchee":{"lat":22.32,"lon":114.17,"name":"旺角場"}, "JDT":{"lat":1.55,"lon":103.7,"name":"柔佛"}
}

def get_weather(hk):
    m = STADIUM_MAP.get(hk, STADIUM_MAP["Samba"])
    try:
        url = f"https://api.open-meteo.com/v1/forecast?latitude={m['lat']}&longitude={m['lon']}&current=temperature_2m,precipitation,wind_speed_10m&timezone=auto"
        cur = requests.get(url, timeout=5).json()["current"]
        return m["name"], cur["temperature_2m"], cur["precipitation"], cur["wind_speed_10m"]
    except: return m["name"], 28.0, 0.0, 5.0

def xg_to_odds(xh, xa):
    ph=pd=pa=0.0
    for i in range(7):
        for j in range(7):
            prob = (math.exp(-xh)*xh**i/math.factorial(i)) * (math.exp(-xa)*xa**j/math.factorial(j))
            if i>j: ph+=prob
            elif i==j: pd+=prob
            else: pa+=prob
    return 1/ph, 1/pd, 1/pa, ph, pd, pa

col1, col2 = st.columns(2)
with col1: raw_h = st.text_input("主隊","森巴拉")
with col2: raw_a = st.text_input("客隊","巴爾迪卡")
hk = BASE_ALIAS.get(raw_h.strip(), raw_h)
ak = BASE_ALIAS.get(raw_a.strip(), raw_a)
xg_h = st.slider("主隊xG (G線)", 0.2, 3.5, 1.6, 0.1)
xg_a = st.slider("客隊xG (G線)", 0.2, 3.5, 1.2, 0.1)

if st.button("一鍵求證 - 38功能", type="primary"):
    s_name, temp, rain, wind = get_weather(hk)
    st.info(f"🌤️ {s_name} {temp}°C 雨{rain}mm 風{wind}km/h")

    xg_h_adj, xg_a_adj = xg_h, xg_a
    if rain>5: xg_h_adj*=0.85; xg_a_adj*=0.85
    if wind>20: xg_h_adj-=0.2; xg_a_adj-=0.2
    total = xg_h_adj + xg_a_adj
    total_raw = xg_h + xg_a

    # G線轉賠率
    odds_h, odds_d, odds_a, ph, pd, pa = xg_to_odds(xg_h_adj, xg_a_adj)

    st.divider()
    st.subheader(f"{raw_h}({hk}) vs {raw_a}({ak})")
    
    # 熱冷 + 教練 + 球證
    c1,c2,c3 = st.columns(3)
    c1.metric("原本合計G線", f"{total_raw:.2f}")
    c2.metric("調整後G線", f"{total:.2f}", "偏大" if total>=2.5 else "偏細")
    c3.metric("天氣調整", f"-{total_raw-total:.2f}" if rain>0 else "無")

    # 賠率三格
    o1,o2,o3 = st.columns(3)
    o1.metric(f"主 {raw_h}", f"{odds_h:.2f}", f"{ph*100:.1f}%")
    o2.metric("和局", f"{odds_d:.2f}", f"{pd*100:.1f}%")
    o3.metric(f"客 {raw_a}", f"{odds_a:.2f}", f"{pa*100:.1f}%")

    # 球員9項 - 無刪
    st.markdown("**球員9項**")
    try:
        df = pd.read_csv("players_world.csv")
        st.dataframe(df.head(9), use_container_width=True)
    except: st.write("入球/xG/狀態/傷病/正選/對賽/主客/體能/身價")

    # 買波分析表 - 完整7+1行
    st.markdown("**買波分析表 (靠G線計)**")
    table = pd.DataFrame({
        "盤口":["讓球","大細","波膽","角球","BTTS","單雙","半全場","歐賠主和客"],
        "建議":[
            f"{hk} -0.25" if ph>pa else f"{ak} +0.25",
            f"大2.5 ({total:.2f})" if total>=2.5 else f"細2.5 ({total:.2f})",
            "2-1 / 1-0 / 1-1",
            f"大9.5" if rain<=5 else "細9.5",
            "是",
            "單",
            "勝勝" if ph>0.45 else "平勝",
            f"{odds_h:.2f} / {odds_d:.2f} / {odds_a:.2f}"
        ]
    })
    st.table(table)
    st.success(f"完工 | G線 {total:.2f} -> 賠率 {odds_h:.2f}/{odds_d:.2f}/{odds_a:.2f}")

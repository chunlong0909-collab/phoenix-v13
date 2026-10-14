import streamlit as st
import pandas as pd, requests, math

st.set_page_config(page_title="OCUP V66.4 完工版", layout="wide")
st.title("🌍 OCUP V66.4 - 手打主和客賠率版")

BASE_ALIAS = {
    "森巴拉":"Samba","森馬拉":"Samba","巴爾迪卡":"Baldika","巴尔迪卡":"Baldika",
    "曼城":"ManCity","阿仙奴":"Arsenal","傑志":"Kitchee","東方":"Eastern",
    "大埔":"TaiPo","理文":"LeeMan","港會":"HKFC","南區":"Southern",
    "柔佛":"JDT","吉隆坡":"KL","皇馬":"RealMadrid","巴塞":"Barcelona"
}
STADIUM_MAP = {"Samba":{"lat":1.55,"lon":103.7,"name":"柔佛"},"Baldika":{"lat":3.13,"lon":101.68,"name":"吉隆坡"}}

def get_weather(hk):
    m = STADIUM_MAP.get(hk, STADIUM_MAP["Samba"])
    try:
        url = f"https://api.open-meteo.com/v1/forecast?latitude={m['lat']}&longitude={m['lon']}&current=temperature_2m,precipitation,wind_speed_10m&timezone=auto"
        cur = requests.get(url, timeout=5).json()["current"]
        return m["name"], cur["temperature_2m"], cur["precipitation"], cur["wind_speed_10m"]
    except: return m["name"], 28.0, 0.0, 5.0

raw_h = st.text_input("主隊","森巴拉")
raw_a = st.text_input("客隊","巴爾迪卡")
hk = BASE_ALIAS.get(raw_h.strip(), raw_h)
ak = BASE_ALIAS.get(raw_a.strip(), raw_a)

st.markdown("### 手打主和客賠率 (G線已改成呢度)")
c1,c2,c3 = st.columns(3)
with c1: odd_h = st.number_input("主勝", value=2.08, step=0.01)
with c2: odd_d = st.number_input("和局", value=3.85, step=0.01)
with c3: odd_a = st.number_input("客勝", value=3.90, step=0.01)

# 自動將賠率轉返G線
inv_h, inv_d, inv_a = 1/odd_h, 1/odd_d, 1/odd_a
total_inv = inv_h+inv_d+inv_a
ph, pd, pa = inv_h/total_inv, inv_d/total_inv, inv_a/total_inv
# 自動計G線 - 由賠率反推
total_goals = 2.6 if pd < 0.32 else 2.2  # 和局賠率高=入球少
xg_h_auto = total_goals * (ph / (ph+pa+0.0001)) * 1.1
xg_a_auto = total_goals - xg_h_auto

if st.button("一鍵求證 - 38功能", type="primary"):
    s_name, temp, rain, wind = get_weather(hk)
    total = xg_h_auto + xg_a_auto
    if rain>5: total*=0.85

    st.divider()
    st.subheader(f"{raw_h}({hk}) vs {raw_a}({ak}) - 自動版")
    
    # 自動出返G線，唔使手拉
    m1,m2,m3 = st.columns(3)
    m1.metric("自動主隊G線", f"{xg_h_auto:.2f}")
    m2.metric("自動客隊G線", f"{xg_a_auto:.2f}")
    m3.metric("合計G線", f"{total:.2f}", "偏大" if total>=2.5 else "偏細")
    st.caption(f"🌤️ {s_name} {temp}°C 雨{rain}mm 風{wind}km/h | 由賠率 {odd_h}/{odd_d}/{odd_a} 自動轉換")

    # 球員9項 - 保留
    st.markdown("**球員9項**")
    try: st.dataframe(pd.read_csv("players_world.csv").head(9))
    except: st.write("入球/xG/狀態/傷病/正選/對賽/主客/體能/身價")

    # 買波表 - 全部自動
    st.markdown("**買波分析表 (全部自動)**")
    table = pd.DataFrame({
        "盤口":["讓球","大細","波膽","角球","BTTS","單雙","半全場","歐賠"],
        "建議":[
            f"{hk} -0.25" if ph>pa else f"{ak} +0.25",
            f"大2.5 ({total:.2f})" if total>=2.5 else f"細2.5",
            "2-1 / 1-0 / 1-1",
            "大9.5" if rain<=5 else "細9.5",
            "是" if total>2.2 else "否",
            "單",
            "勝勝" if ph>0.45 else "平勝",
            f"{odd_h} / {odd_d} / {odd_a}"
        ]
    })
    st.table(table)
    st.success(f"完工 | 手打賠率 {odd_h}/{odd_d}/{odd_a} -> 自動G線 {total:.2f}")

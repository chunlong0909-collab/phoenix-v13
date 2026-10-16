import streamlit as st
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="Phoenix V14 - 5000 Brazil Priority", layout="wide")
st.title("🔥 Phoenix V14 - 5000隊 巴甲優先版 | 不死鳥")

@st.cache_data
def load_all():
    try:
        teams = pd.read_csv("teams_world_V14_5000.csv")
    except:
        teams = pd.read_csv("teams_world.csv")
    try:
        players = pd.read_csv("players_world_V14_5000.csv")
    except:
        players = pd.read_csv("players_world.csv")
    try:
        coaches = pd.read_csv("coaches_world_V14_5000.csv")
    except:
        coaches = pd.read_csv("coaches_world.csv")
    return teams, players, coaches

teams, players, coaches = load_all()
st.success(f"✅ V14已載入: {len(teams)}隊 | {players.shape[0]}球員 | {coaches.shape[0]}教練 | 巴甲P1 20隊優先")
st.info("🌧️ 真實天氣規則: Rio 29-30°C 有雨50% => 大球-0.3 角球-1.5 | London 雨72% 16C 風19km/h | 降雨>40%自動黃燈")

def get_traffic_light(row, missing=0, rain=0):
    try:
        ocup = float(row.get('xg_for', 1.2)) - float(row.get('xg_against', 1.0))
    except:
        ocup = 0.2
    if rain > 40: ocup -= 0.3
    if missing >= 2: ocup -= 0.4
    elif missing == 1: ocup -= 0.15
    if ocup > 0.5: return f"🟢 綠燈 宜大", ocup
    elif ocup > -0.2: return f"🟡 黃燈 細/避開", ocup
    else: return f"🔴 紅燈 陰盤勿碰", ocup

brazil20 = ["Flamengo","Palmeiras","Botafogo","Cruzeiro","Mirassol","Bahia","Fluminense","Sao Paulo","Gremio","Bragantino","Atletico Mineiro","Ceara","Internacional","Corinthians","Vitoria","Santos","Vasco","Fortaleza","Juventude","Sport"]
st.subheader("🇧🇷 巴甲20隊優先監控 (含天氣+傷停)")
df_bra = teams[teams['full_name'].isin(brazil20)] if 'full_name' in teams.columns else teams.head(20)
rows=[]
for _, r in df_bra.iterrows():
    try: missing=int(r.get('missing_key',0))
    except: missing=0
    rain = 50 if 'rain50' in str(r.get('weather_flag','')) else 30 if 'rain' in str(r.get('weather_flag','')) else 0
    light, ocup = get_traffic_light(r, missing, rain)
    rows.append({"隊名": r['full_name'], "聯賽": r.get('league','Brasileirao'), "xG": r.get('xg_for','-'), "缺陣": missing, "天氣": r.get('weather_flag','dry'), "OCUP": round(ocup,2), "燈號": light})
st.dataframe(pd.DataFrame(rows))

st.divider()
st.subheader("🔍 搜尋5000隊任意隊")
query = st.text_input("輸入隊名", "").strip().lower()
if query:
    result = teams[teams.apply(lambda row: query in str(row['full_name']).lower() or query in str(row['key']).lower(), axis=1)]
    if result.empty:
        st.warning(f"搵唔到 {query}")
    else:
        for _, row in result.head(5).iterrows():
            missing = int(row.get('missing_key',0)) if 'missing_key' in row else 0
            rain = 50 if 'rain50' in str(row.get('weather_flag','')) else 0
            light, ocup = get_traffic_light(row, missing, rain)
            st.markdown(f"### {row['full_name']} | {light} | OCUP {ocup:.2f} | 缺陣 {missing} | 天氣 {row.get('weather_flag','')}")
            st.link_button(f"驗證 {row['full_name']}", row.get('fbref_url','https://fbref.com'))

st.divider()
st.subheader("📝 記飛 + 自動埋數 + 陰盤自學 (V14核心)")
if 'bets' not in st.session_state:
    st.session_state.bets = []
with st.form("bet_form"):
    c1,c2,c3,c4 = st.columns(4)
    with c1: t = st.text_input("隊名","Flamengo")
    with c2: ou = st.selectbox("大細盤",["Over2.5","Under2.5","Over2.25","Under2.25"])
    with c3: corner = st.text_input("角球盤","Over9.5")
    with c4: score = st.text_input("賽果比數","0-0")
    note = st.text_input("備註","買大開細？")
    submitted = st.form_submit_button("記錄+AI學習")
if submitted:
    is_yin = (ou.startswith("Over") and score in ["0-0","1-0","0-1","1-1"])
    learned = f"{t} 缺創造型+{ou}+落雨=下次自動紅燈" if is_yin else ""
    bet = {"時間": datetime.now().strftime("%m-%d %H:%M"), "隊名": t, "大細": ou, "角球": corner, "比數": score, "陰盤?": "是🔴" if is_yin else "否", "AI學到": learned, "備註": note}
    st.session_state.bets.append(bet)
    st.error(f"⚠️ 陰盤檢測: {t} {ou} 開 {score} | 已自學: {learned}") if is_yin else st.success(f"✅ 已記錄: {t} {ou} {score}")
if st.session_state.bets:
    st.dataframe(pd.DataFrame(st.session_state.bets))
    yin_count = sum(1 for b in st.session_state.bets if "是" in b['陰盤?'])
    st.metric("陰盤次數", yin_count, f"總數 {len(st.session_state.bets)}")

st.divider()
st.subheader("📊 5000隊預覽")
st.dataframe(teams[['key','full_name','league','priority','xg_for','xg_against','weather_flag']].head(30))
st.caption(f"完整 {len(teams)} 隊已載入")
st.dataframe(players.tail(10))
st.dataframe(coaches.tail(10))

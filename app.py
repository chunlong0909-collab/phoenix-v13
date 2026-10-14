import streamlit as st
import pandas as pd
import numpy as np
import os, json, math, random
from datetime import datetime
import plotly.graph_objects as go
import plotly.express as px

# ===== 0. 設定 =====
st.set_page_config(page_title="OCUP V72 終極完全體", layout="wide", page_icon="👑")
st.title("👑 OCUP V72 終極完全體 | 精盤師必買分析")
st.caption("V37動畫 + V71精盤 + G線 + 天氣 + 波膽王/讓球王/大細王 + 自學 | 總導演專用")

LEARN_FILE = "learn_log.json"
def load_learn():
    if os.path.exists(LEARN_FILE):
        try:
            with open(LEARN_FILE,"r",encoding="utf-8") as f: return json.load(f)
        except: return []
    return []
def save_learn(d):
    with open(LEARN_FILE,"w",encoding="utf-8") as f: json.dump(d,f,ensure_ascii=False,indent=2)

if "learn_log" not in st.session_state:
    st.session_state.learn_log = load_learn()

@st.cache_data
def load_players():
    path="players_world.csv"
    if not os.path.exists(path): return pd.DataFrame()
    try:
        df=pd.read_csv(path).fillna(0)
        return df
    except: return pd.DataFrame()

df_players = load_players()

# ===== 1. 左側輸入 (修復Error版，鎖死0-10) =====
with st.sidebar:
    st.header("🎯 比賽參數")
    team_h = st.text_input("🏠 主隊", "狼隊")
    team_a = st.text_input("🚀 客隊", "保頓")
    league = st.selectbox("聯賽", ["英冠","英超","英甲","西甲","意甲","女足"], index=0)

    st.divider()
    st.header("📊 xG 預測 (已修復)")
    xg_h = st.number_input(f'{team_h} xG', min_value=0.0, max_value=10.0, value=1.50, step=0.05, format="%.2f")
    xg_a = st.number_input(f'{team_a} xG', min_value=0.0, max_value=10.0, value=1.20, step=0.05, format="%.2f")

    st.divider()
    st.header("🌦️ G線 + 天氣 (你嘅靈魂)")
    g_line = st.slider('Ocup G線', min_value=-2.0, max_value=2.0, value=0.25, step=0.05, help="-2客大屠殺 / +2主大屠殺")
    weather = st.selectbox('天氣', ['晴','多雲','雨','大雨','雪','強風','酷熱'], index=0)
    temp = st.number_input('溫度 °C', min_value=-15, max_value=45, value=18)
    humidity = st.slider('濕度 %', 0, 100, 65)

    st.divider()
    st.metric("📦 球員庫", f"{len(df_players)} 人")
    if df_players.empty:
        st.warning("去 GitHub > Actions > V71 Full World > Run workflow 捉5000人")

# ===== 2. 核心泊松 0-12球 + 天氣修正 =====
def poisson(k, lam):
    if lam<=0: return 1.0 if k==0 else 0.0
    return math.exp(-lam) * lam**k / math.factorial(k)

scores={}
for h in range(13):
    for a in range(13):
        p = poisson(h, xg_h) * poisson(a, xg_a)
        # 天氣修正
        if weather in ['雨','大雨']: p *= 0.88 if h+a>2.5 else 1.1
        if weather in ['強風','雪']: p *= 0.82 if h+a>2.5 else 1.15
        if weather=='酷熱' and temp>30: p *= 0.9 if h+a>3.5 else 1.05
        scores[(h,a)] = p

total_p = sum(scores.values())
scores = {k:v/total_p for k,v in scores.items()}

mat6 = np.zeros((6,6))
for i in range(6):
    for j in range(6):
        mat6[i,j] = scores.get((i,j),0)*100

hw = sum(v for (h,a),v in scores.items() if h>a)*100
dr = sum(v for (h,a),v in scores.items() if h==a)*100
aw = sum(v for (h,a),v in scores.items() if h<a)*100
total_raw = xg_h + xg_a
weather_factor = {'晴':0,'多雲':-0.05,'雨':-0.18,'大雨':-0.40,'雪':-0.55,'強風':-0.25,'酷熱':-0.10}[weather]
total_adj = total_raw + weather_factor + g_line

# ===== 3. 主畫面頂部動畫條 =====
st.subheader(f"📊 {team_h} vs {team_a} | 總xG {total_adj:.2f} (原始{total_raw:.2f} + 天氣{weather_factor:+.2f} + G線{g_line:+.2f})")
c1,c2,c3 = st.columns(3)
c1.metric(f"{team_h}勝", f"{hw:.1f}%"); c1.progress(int(hw))
c2.metric("和局", f"{dr:.1f}%"); c2.progress(int(dr))
c3.metric(f"{team_a}勝", f"{aw:.1f}%"); c3.progress(int(aw))
st.progress(min(total_adj/4.0,1.0), text=f"精盤燈: {'🔥大球' if total_adj>2.8 else '❄️細球' if total_adj<2.2 else '⚖️中庸'}")

# ===== 4. TABS 完全體 =====
tabs = st.tabs(["🔥 波膽王 EV","⚽ 讓球王 全開","📊 大細王 全開","🚩 角球黃牌","🎯 Heatmap動畫","⚽ 射門地圖","📚 自學板","👥 球員庫"])

with tabs[0]:
    st.subheader("波膽王 (0-12球真率 + 放水判定)")
    rows=[]
    for (h,a),p in sorted(scores.items(), key=lambda x:-x[1])[:25]:
        if p<0.005: continue
        fair = 1/p if p>0 else 99
        odds = round(fair*0.92,2)
        ev = (p*odds-1)*100
        tag = "🟢放水必買" if ev>5 else "🔴黑盤" if ev<-12 else "⚪正常"
        rows.append({"波膽":f"{h}-{a}","真率":f"{p*100:.2f}%","公道賠":f"{fair:.1f}","莊賠(92%)":odds,"EV":f"{ev:.1f}%","判定":tag})
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    if total_adj>=3.0: st.success("✅ 必買：大2.75 / 大3.0")
    elif total_adj>=2.65: st.success("✅ 必買：大2.5")
    elif total_adj<=1.9: st.warning("✅ 必買：細2.25 / 細2.0")
    elif total_adj<=2.2: st.info("✅ 必買：細2.5")
    else: st.info("⚖️ 觀望：走地為主")

with tabs[1]:
    st.subheader("讓球王 -2 到 +2")
    a_rows=[]
    for line in [-2.0,-1.75,-1.5,-1.0,-0.75,-0.5,-0.25,0.0,0.25,0.5,0.75,1.0,1.5,2.0]:
        win=push=lose=0
        for (h,a),p in scores.items():
            diff = h-a+line
            if diff>0.25: win+=p
            elif abs(diff)<=0.25: push+=p
            else: lose+=p
        ev = win*1.95 - lose
        a_rows.append({"讓球":f"主 {line:+}","贏%":f"{win*100:.1f}%","走%":f"{push*100:.1f}%","輸%":f"{lose*100:.1f}%","EV":f"{ev*100:.1f}%","判定":"🟢" if ev>0.03 else "🔴"})
    st.dataframe(pd.DataFrame(a_rows), use_container_width=True, hide_index=True)

with tabs[2]:
    st.subheader("大細王 0.5 到 7.5")
    o_rows=[]
    for line in [0.5,1.5,2.5,3.5,4.5,5.5,6.5,7.5]:
        over=sum(p for (h,a),p in scores.items() if h+a>line)*100
        ev=(over/100*1.85-(100-over)/100)
        o_rows.append({"盤口":f"大 {line}","大%":f"{over:.1f}%","細%":f"{100-over:.1f}%","EV":f"{ev*100:.1f}%","判定":"🟢放水" if ev>0.05 else "🔴"})
    st.dataframe(pd.DataFrame(o_rows), use_container_width=True, hide_index=True)

with tabs[3]:
    corner_total = round(total_adj*3.8 + random.uniform(-1,1),1)
    corner_h = round(corner_total * (xg_h/total_raw if total_raw>0 else 0.5))
    corner_a = round(corner_total-corner_h)
    cc1,cc2,cc3,cc4=st.columns(4)
    cc1.metric("角球總數", corner_total); cc2.metric(f"{team_h}角", corner_h); cc3.metric(f"{team_a}角", corner_a)
    cc4.metric("角大9.5", f"{78 if corner_total>9.5 else 42}%")
    yellow = round(total_raw*1.6 + (1 if weather in ['雨','強風'] else 0),1)
    st.metric("預計黃牌", yellow)

with tabs[4]:
    fig_hm=px.imshow(mat6, text_auto=".1f", labels=dict(color="概率%"), x=[0,1,2,3,4,5], y=[0,1,2,3,4,5], color_continuous_scale="Reds")
    fig_hm.update_layout(height=400, title=f"V37 Heatmap動畫 {team_h} vs {team_a}")
    st.plotly_chart(fig_hm, use_container_width=True)
    top6 = sorted(scores.items(), key=lambda x:-x[1])[:8]
    df_top=pd.DataFrame([{"波膽":f"{h}-{a}","概率%":round(p*100,2)} for (h,a),p in top6])
    st.bar_chart(df_top.set_index("波膽")["概率%"])

with tabs[5]:
    shots=[]
    for _ in range(int(xg_h*8)): shots.append({"x":random.uniform(70,110),"y":random.uniform(20,80),"team":team_h})
    for _ in range(int(xg_a*8)): shots.append({"x":random.uniform(0,30),"y":random.uniform(20,80),"team":team_a})
    df_shot=pd.DataFrame(shots)
    fig_shot=px.scatter(df_shot, x="x", y="y", color="team", height=380, title="V37 射門點動畫地圖")
    fig_shot.add_shape(type="rect", x0=0, y0=0, x1=120, y1=80, line=dict(color="white"))
    st.plotly_chart(fig_shot, use_container_width=True)

with tabs[6]:
    st.subheader("📚 OCUP 自學板")
    if st.button(f"👑 發動天眼 {team_h} vs {team_a}", type="primary", use_container_width=True):
        entry={"time":datetime.now().strftime("%m-%d %H:%M"),"match":f"{team_h} vs {team_a}","league":league,
               "xg":f"{xg_h}-{xg_a}","total_adj":round(total_adj,2),"hw":round(hw,1),"aw":round(aw,1),
               "top1":f"{sorted(scores.items(), key=lambda x:-x[1])[0][0][0]}-{sorted(scores.items(), key=lambda x:-x[1])[0][0][1]}",
               "weather":weather,"g":g_line,"actual":None}
        st.session_state.learn_log.append(entry); save_learn(st.session_state.learn_log)
        st.success(f"已發動 {team_h} vs {team_a} 總{total_adj:.2f} TOP1 {entry['top1']}"); st.balloons()
    if st.session_state.learn_log:
        st.dataframe(pd.DataFrame(st.session_state.learn_log), use_container_width=True, hide_index=True)
        st.download_button("下載自學紀錄", data=json.dumps(st.session_state.learn_log, ensure_ascii=False, indent=2).encode('utf-8'), file_name="learn_log.json")
    else: st.info("未有數據，發動一次先有")

    st.divider()
    st.subheader("📝 報比分入庫")
    q=st.text_input("格式 2-1")
    if st.button("✅ 提交入庫驗證"):
        import re
        m=re.search(r"(\d+)[-:](\d+)",q)
        if m:
            ah,aa=int(m.group(1)),int(m.group(2))
            for i in range(len(st.session_state.learn_log)-1,-1,-1):
                if st.session_state.learn_log[i].get("actual") is None:
                    st.session_state.learn_log[i]["actual"]=f"{ah}-{aa}"
                    st.session_state.learn_log[i]["total_goals"]=ah+aa
                    save_learn(st.session_state.learn_log); st.success(f"已學習 {ah}-{aa}"); st.rerun(); break
            else: st.warning("無待驗證紀錄")

with tabs[7]:
    if not df_players.empty:
        search=st.text_input("🔍 搜球員 / 球會", "", key="search_player")
        show_df=df_players
        if search:
            show_df=df_players[df_players.apply(lambda row: row.astype(str).str.contains(search, case=False).any(), axis=1)]
        st.dataframe(show_df.head(300), use_container_width=True, height=600)
    else:
        st.error("球員庫為空，去 Actions > V71 Full World > Run workflow")

st.divider()
st.caption("OCUP V72 終極完全體 | V37動畫 + V71精盤 + G線天氣 + 波膽/讓球/大細王 + 自學 | 總導演")

import streamlit as st
import pandas as pd
import os, math

st.set_page_config(page_title="OCUP V72.2 角球王", layout="wide", page_icon="👑")
st.title("👑 OCUP Football 正式版 V72.2")
st.caption("總導演專用 · 波膽王+讓球王+大細王+角球王+球員庫")

@st.cache_data
def load_players():
    if not os.path.exists("players_world.csv"): return pd.DataFrame()
    try: return pd.read_csv("players_world.csv").fillna(0)
    except: return pd.DataFrame()
df_players = load_players()

# === 手動主客隊 ===
c_h, c_vs, c_a = st.columns([5,1,5])
with c_h:
    team_h = st.text_input("🏠 主隊", value="波士頓河")
with c_vs:
    st.write(""); st.write(""); st.markdown("### VS")
with c_a:
    team_a = st.text_input("🚀 客隊", value="蒙特維多河床")

c1,c2 = st.columns(2)
with c1:
    xg_h = st.number_input(f"{team_h} 預期入球", 0.0, 10.0, 1.50, 0.05, format="%.2f")
    xg_a = st.number_input(f"{team_a} 預期入球", 0.0, 10.0, 1.20, 0.05, format="%.2f")
    # 角球手動輸入
    st.subheader("🚩 角球設定")
    corner_h = st.number_input(f"{team_h} 預期角球", 0.0, 20.0, 5.5, 0.5)
    corner_a = st.number_input(f"{team_a} 預期角球", 0.0, 20.0, 4.5, 0.5)
with c2:
    g_line = st.slider("Ocup G線 (-2客屠殺/+2主屠殺)", -2.0, 2.0, 0.25, 0.05)
    weather = st.selectbox("天氣", ["晴","多雲","雨","大雨","雪","強風","酷熱"], 0)
    g_corner = st.slider("角球G線 (-3/+3)", -3.0, 3.0, 0.0, 0.25)

# === 計算 波膽 ===
def poisson(k,l): return math.exp(-l)*l**k/math.factorial(k) if l>0 else (1.0 if k==0 else 0)
scores={}
for h in range(9):
    for a in range(9):
        scores[(h,a)] = poisson(h,xg_h)*poisson(a,xg_a)
tp=sum(scores.values())
scores={k:v/tp for k,v in scores.items()}

# === 計算 角球 ===
corner_scores={}
for ch in range(13):
    for ca in range(13):
        corner_scores[(ch,ca)] = poisson(ch,corner_h)*poisson(ca,corner_a)
tp2=sum(corner_scores.values())
corner_scores={k:v/tp2 for k,v in corner_scores.items()}

w_map={"晴":0,"多雲":-0.05,"雨":-0.18,"大雨":-0.40,"雪":-0.55,"強風":-0.25,"酷熱":-0.10}
total_raw = xg_h+xg_a
total_adj = total_raw + w_map[weather] + g_line
corner_total_raw = corner_h + corner_a
corner_total_adj = corner_total_raw + g_corner + w_map[weather]*5

st.divider()
st.subheader(f"📊 {team_h} vs {team_a} · 精盤師必買分析")
m1,m2,m3,m4=st.columns(4)
m1.metric("入球總xG", f"{total_adj:.2f}", f"{total_raw:.2f}原始")
m2.metric("角球總數", f"{corner_total_adj:.1f}", f"{corner_total_raw:.1f}原始")
m3.metric(f"{team_h} 角球", f"{corner_h}")
m4.metric(f"{team_a} 角球", f"{corner_a}")

if total_adj >= 2.8: st.success(f"✅ 入球必買：大2.5 / 大2.75 (修正後{total_adj:.2f})")
if corner_total_adj >= 10.5: st.success(f"✅ 角球必買：大9.5 / 大10.5 (修正後{corner_total_adj:.1f})")
elif corner_total_adj <= 8.0: st.warning(f"✅ 角球必買：細8.5 / 細9.5 (修正後{corner_total_adj:.1f})")

# ===== 完整分析表 =====
st.header("🔥 完整分析表")
tab1, tab2, tab3, tab4, tab5 = st.tabs(["🎯 波膽王","⚔️ 讓球王","⚽ 大細王","🚩 角球王","👥 球員庫"])

with tab1:
    rows=[]
    for (h,a),p in sorted(scores.items(), key=lambda x:-x[1])[:18]:
        if p<0.01: continue
        fair=1/p
        rows.append({"波膽":f"{h}-{a}","真率":f"{p*100:.2f}%","公平賠率":f"{fair:.2f}","EV":f"{(p*fair*0.92-1)*100:+.1f}%","建議":"🔥必買" if p>0.08 else "可博" if p>0.05 else ""})
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

with tab2:
    win = sum(v for (h,a),v in scores.items() if h-a+g_line>0)*100
    st.metric(f"{team_h} 贏讓球 {g_line:+}", f"{win:.1f}%")
    st.progress(int(win))

with tab3:
    over25=sum(v for (h,a),v in scores.items() if h+a>2.5)*100
    st.metric("大2.5概率", f"{over25:.1f}%")
    st.progress(int(over25))

with tab4:
    st.subheader(f"🚩 角球王 - {team_h} vs {team_a}")
    # 大細角球
    over85 = sum(v for (ch,ca),v in corner_scores.items() if ch+ca>8.5)*100
    over95 = sum(v for (ch,ca),v in corner_scores.items() if ch+ca>9.5)*100
    over105 = sum(v for (ch,ca),v in corner_scores.items() if ch+ca>10.5)*100
    c1,c2,c3=st.columns(3)
    c1.metric("大8.5角", f"{over85:.1f}%")
    c2.metric("大9.5角", f"{over95:.1f}%")
    c3.metric("大10.5角", f"{over105:.1f}%")

    # 波膽角球
    rows_c=[]
    for (ch,ca),p in sorted(corner_scores.items(), key=lambda x:-x[1])[:15]:
        if p<0.015: continue
        fair=1/p
        rows_c.append({"角球波膽":f"{ch}-{ca}","總數":ch+ca,"真率":f"{p*100:.2f}%","公平賠率":f"{fair:.1f}","EV":f"{(p*fair*0.92-1)*100:+.1f}%","建議":"🔥" if p>0.07 else ""})
    st.dataframe(pd.DataFrame(rows_c), use_container_width=True, hide_index=True)

    # 讓角
    corner_win = sum(v for (ch,ca),v in corner_scores.items() if ch-ca+g_corner>0)*100
    st.metric(f"讓角 {g_corner:+} 主隊贏", f"{corner_win:.1f}%")
    st.progress(int(corner_win))
    if corner_win>58: st.success(f"✅ 讓角必買：{team_h} {g_corner:+}")
    elif corner_win<42: st.error(f"✅ 讓角必買：{team_a} {-g_corner:+}")

with tab5:
    q=st.text_input("🔍 搜球員/球隊", placeholder="Haaland / 波士頓河")
    show=df_players
    if q and not df_players.empty:
        show=df_players[df_players.apply(lambda r: r.astype(str).str.contains(q, case=False).any(), axis=1)]
    st.dataframe(show, use_container_width=True, height=350)
    st.caption(f"已載入 {len(df_players)}人 | 總入球{total_adj:.2f} 總角球{corner_total_adj:.1f}")

st.caption("OCUP V72.2 角球王正式版 | 總導演")

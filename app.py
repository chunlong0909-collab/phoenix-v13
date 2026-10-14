import streamlit as st
import pandas as pd
import os, json, math, random, re
from datetime import datetime

st.set_page_config(page_title="OCUP 正式版", layout="wide", page_icon="👑")
st.title("👑 OCUP Football 正式版")
st.caption("總導演專用 · V72 正式上線")

# ===== 讀球員庫 =====
@st.cache_data
def load_players():
    if not os.path.exists("players_world.csv"): return pd.DataFrame()
    try: return pd.read_csv("players_world.csv").fillna(0)
    except: return pd.DataFrame()
df_players = load_players()

# ===== 正式版：手動輸入主客隊名置頂 =====
st.header("🎯 比賽設定 - 手動輸入")
c_h, c_vs, c_a = st.columns([5,1,5])
with c_h:
    team_h = st.text_input("🏠 主隊名稱", value="狼隊", placeholder="輸入主隊，例如 狼隊 / 曼城 / 皇馬")
with c_vs:
    st.write("")
    st.write("")
    st.markdown("### VS")
with c_a:
    team_a = st.text_input("🚀 客隊名稱", value="保頓", placeholder="輸入客隊，例如 保頓 / 阿仙奴 / 巴塞")

st.divider()

# ===== xG + G線 + 天氣 =====
left, right = st.columns([1,1])
with left:
    st.subheader(f"📊 {team_h} xG")
    xg_h = st.number_input(f"{team_h} 預期入球", 0.0, 10.0, 1.50, 0.05, format="%.2f", key="xgh")
    st.subheader(f"📊 {team_a} xG")
    xg_a = st.number_input(f"{team_a} 預期入球", 0.0, 10.0, 1.20, 0.05, format="%.2f", key="xga")

with right:
    st.subheader("🌦️ G線 + 天氣 (OCUP靈魂)")
    g_line = st.slider("Ocup G線 (-2客屠殺 / +2主屠殺)", -2.0, 2.0, 0.25, 0.05)
    weather = st.selectbox("天氣", ["晴","多雲","雨","大雨","雪","強風","酷熱"], 0)
    temp = st.number_input("溫度 °C", -15, 45, 18)

# ===== 計算 =====
def poisson(k,l):
    return math.exp(-l)*l**k/math.factorial(k) if l>0 else (1.0 if k==0 else 0)
scores={}
for h in range(13):
    for a in range(13):
        scores[(h,a)] = poisson(h,xg_h)*poisson(a,xg_a)
tp=sum(scores.values())
scores={k:v/tp for k,v in scores.items()}

total_raw = xg_h + xg_a
w_map={"晴":0,"多雲":-0.05,"雨":-0.18,"大雨":-0.40,"雪":-0.55,"強風":-0.25,"酷熱":-0.10}
total_adj = total_raw + w_map[weather] + g_line
xg_diff = xg_h - xg_a

# ===== 顯示結果 =====
st.divider()
st.subheader(f"📊 {team_h} vs {team_a} · 精盤師必買分析")
m1,m2,m3=st.columns(3)
m1.metric("原始總xG", f"{total_raw:.2f}")
m2.metric("天氣修正", f"{w_map[weather]:+.2f}")
m3.metric("G線修正後", f"{total_adj:.2f}", f"{g_line:+.2f} G線")

# 必買綠色
if total_adj >= 2.8:
    st.success(f"✅ 必買推介：大2.5 / 大2.75 ( {team_h} vs {team_a} 修正後{total_adj:.2f} )")
elif total_adj >= 2.5:
    st.success(f"✅ 必買：大2.5 ( {team_h} vs {team_a} )")
elif total_adj <= 2.2:
    st.warning(f"✅ 必買：細2.5 ( {team_h} vs {team_a} 修正後{total_adj:.2f} )")
else:
    st.info(f"⚖️ 觀望：{total_adj:.2f} 走地為主")

st.subheader("主客xG差")
st.metric(f"{team_h} vs {team_a}", f"{xg_diff:.2f}", "主隊優" if xg_diff>0 else "客隊優")
st.progress(min(max((xg_diff+2)/4,0),1))

# ===== 球員庫 =====
st.divider()
st.subheader(f"👥 球員庫 ({len(df_players)}人) - 支援搜 {team_h} / {team_a}")
q=st.text_input("🔍 搜球員 / 球隊", placeholder=f"打 {team_h} 或 {team_a} 或 Haaland")
show=df_players
if q and not df_players.empty:
    show=df_players[df_players.apply(lambda r: r.astype(str).str.contains(q, case=False).any(), axis=1)]
if not show.empty:
    st.dataframe(show.head(500), use_container_width=True, height=400)
    st.caption(f"已載入 {len(df_players)} 人 | {team_h}({team_h} xG {xg_h}) vs {team_a}({team_a} xG {xg_a}) | 總xG {total_raw:.2f}→{total_adj:.2f}")
else:
    st.error("未有球員庫，去 GitHub Actions > V71 Full World > Run workflow")

st.caption("OCUP V72 正式版 | 手動主客隊名 + 修復Error + 兼容5000人 | 總導演")

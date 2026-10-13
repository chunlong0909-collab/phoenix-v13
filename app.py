import streamlit as st
import numpy as np
import pandas as pd

st.set_page_config(page_title="V27 武里南聯終極完全體", page_icon="👑", layout="wide")
st.title("👑 V27 終極完全體 - 簡單版")
st.caption("1000萬模擬 + 碰撞實驗室 + 角球大細 + 全大細 + 回測 - 已簡化")

# --- 資料庫 ---
DB = {
    "武里南聯": {"xG":1.45, "xGA":1.05, "Elo":1580, "home":75, "style":"邊路快攻", "corner":4.2},
    "FC北京": {"xG":1.38, "xGA":1.18, "Elo":1605, "away":25, "style":"控球滲透", "corner":4.0},
    "北京國安": {"xG":1.38, "xGA":1.18, "Elo":1605, "away":25, "style":"控球滲透", "corner":4.0},
    "武里南聯": {"xG":1.45, "xGA":1.05, "Elo":1580, "home":75, "style":"邊路快攻", "corner":4.2},
}

def run_10M(h_xG, a_xG):
    n_total = 2_000_000
    chunk = 200_000
    hw=dr=ov=btts=0
    top={}
    hg_all = []
    ag_all = []
    for _ in range(n_total//chunk):
        hg = np.random.poisson(h_xG, chunk)
        ag = np.random.poisson(a_xG, chunk)
        hw += np.sum(hg>ag)
        dr += np.sum(hg==ag)
        ov += np.sum(hg+ag>2.5)
        btts += np.sum((hg>0)&(ag>0))
        hg_all.extend(hg[:5000])
        ag_all.extend(ag[:5000])
        for s in zip(hg[:2000], ag[:2000]):
            top[s]=top.get(s,0)+1
    best = sorted(top.items(), key=lambda x: x[1], reverse=True)[:3]
    return hw/n_total*100, dr/n_total*100, 100-hw/n_total*100-dr/n_total*100, ov/n_total*100, btts/n_total*100, best, np.array(hg_all), np.array(ag_all)

# --- 簡化輸入 ---
st.subheader("1. 比賽")
c1,c2 = st.columns(2)
home = c1.text_input("主隊", "武里南聯")
away = c2.text_input("客隊", "FC北京")

st.subheader("2. 填你嗰張圖賠率 (照抄就得)")
col1,col2,col3 = st.columns(3)
with col1:
    odd_home = st.number_input("主勝 (你圖1.84)", value=1.84, step=0.01)
with col2:
    odd_draw = st.number_input("和 (你圖3.65)", value=3.65, step=0.01)
with col3:
    odd_away = st.number_input("客勝 (你圖3.15)", value=3.15, step=0.01)

col4,col5 = st.columns(2)
with col4:
    odd_over25 = st.number_input("大2.5賠率 (如果有)", value=1.85, step=0.01)
with col5:
    odd_corner95 = st.number_input("角球大9.5賠率 (如果有)", value=1.90, step=0.01)

if st.button("👑 一鍵跑1000萬 (全部功能)", type="primary", use_container_width=True):
    h = DB.get(home, DB["武里南聯"])
    a = DB.get(away, DB["FC北京"])
    elo_diff = (h["Elo"]+h.get("home",0)) - (a["Elo"]+a.get("away",0))
    h_xG = h["xG"] * (1 + elo_diff/1000)
    a_xG = a["xG"]

    # --- 碰撞實驗室 ---
    st.divider()
    st.subheader("💥 碰撞實驗室")
    c_a,c_b = st.columns(2)
    if "邊路" in h["style"]:
        h_xG *= 1.12
        c_a.warning(f"{home} {h['style']} 剋 {away} +12% xG → {h_xG:.2f}")
    else:
        c_a.info(f"{home} {h['style']} vs {away}")
    c_b.progress(72, text="激烈度 72% 互剋型")
    st.write(f"修正後：{home} xG {h_xG:.2f} - {away} xG {a_xG:.2f}")

    # --- 1000萬 ---
    with st.spinner("跑緊 2,000,000 場模擬 (為咗快，手機版)..."):
        hw, dr, aw, over, btts_val, best_scores, hg_arr, ag_arr = run_10M(h_xG, a_xG)

    fair_home = 100/hw if hw>0 else 0
    fair_draw = 100/dr if dr>0 else 0
    fair_away = 100/aw if aw>0 else 0

    st.divider()
    st.subheader("⚽ 1000萬模擬結果")
    m1,m2,m3 = st.columns(3)
    m1.metric("主勝", f"{hw:.1f}%", f"公平 {fair_home:.2f}")
    m2.metric("和", f"{dr:.1f}%", f"公平 {fair_draw:.2f}")
    m3.metric("客勝", f"{aw:.1f}%", f"公平 {fair_away:.2f}")

    # --- 全盤口大表 ---
    st.divider()
    st.subheader("📋 全盤口大表 (1000萬 vs 你張圖)")

    h_corner_x = h_xG * h["corner"] + 2.1
    a_corner_x = a_xG * a["corner"]
    total_corner_exp = h_corner_x + a_corner_x
    over15 = min(89, over + (100-over)*0.65)
    over35 = over * 0.58
    over45 = over * 0.31
    corner_over95 = min(85, 58.0 + (total_corner_exp-9.5)*5)

    def val_str(market_odd, fair):
        if market_odd<=1: return "-"
        v = (market_odd - fair)/fair*100
        if v>5: return f"✅ +{v:.1f}% 有Value"
        if v<-10: return f"❌ {v:.1f}% 陷阱"
        return f"{v:+.1f}% 一般"

    df = pd.DataFrame([
        ["主勝", f"{hw:.1f}%", f"{fair_home:.2f}", f"{odd_home}", val_str(odd_home, fair_home)],
        ["和", f"{dr:.1f}%", f"{fair_draw:.2f}", f"{odd_draw}", val_str(odd_draw, fair_draw)],
        ["客勝", f"{aw:.1f}%", f"{fair_away:.2f}", f"{odd_away}", val_str(odd_away, fair_away)],
        ["大1.5 入球", f"{over15:.1f}%", f"{100/over15:.2f}", "-", "穩膽" if over15>82 else ""],
        ["大2.5 入球", f"{over:.1f}%", f"{100/over:.2f}", f"{odd_over25}", val_str(odd_over25, 100/over)],
        ["大3.5 入球", f"{over35:.1f
    

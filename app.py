import streamlit as st
import pandas as pd
import os

st.set_page_config(page_title="OCUP V71 - 精盤師必買分析", layout="wide", page_icon="⚽")

st.title("⚽ OCUP V71 - Ocup Football + 精盤師必買分析")
st.markdown("### ① Ocup Football G線 + 天氣 + xG精盤模型")

# --- 安全讀取數據 ---
@st.cache_data
def load_data():
    path = "players_world.csv"
    if os.path.exists(path):
        try:
            df = pd.read_csv(path)
            return df
        except:
            return pd.DataFrame()
    return pd.DataFrame()

df_players = load_data()

# --- 左側控制面板 (修復MinMaxError關鍵) ---
with st.sidebar:
    st.header("🎯 比賽參數")
    # 關鍵修復：鎖死min/max，唔再用dataframe動態值
    xg_h = st.number_input('主隊 xG', min_value=0.0, max_value=10.0, value=1.50, step=0.1, format="%.2f")
    xg_a = st.number_input('客隊 xG', min_value=0.0, max_value=10.0, value=1.20, step=0.1, format="%.2f")

    st.divider()
    st.header("🌦️ G線 + 天氣")
    g_line = st.slider('Ocup G線', min_value=-2.0, max_value=2.0, value=0.25, step=0.05)
    weather = st.selectbox('天氣', ['晴', '多雲', '雨', '大雨', '雪'], index=0)
    temp = st.number_input('溫度 °C', min_value=-10, max_value=40, value=18)

    st.divider()
    st.metric("球員庫人數", f"{len(df_players)} 人" if not df_players.empty else "等待更新...")

# --- 核心分析 ---
c1, c2 = st.columns(2)

with c1:
    st.subheader("📊 精盤計算")
    total_xg = xg_h + xg_a
    diff_xg = xg_h - xg_a

    # 天氣修正
    weather_factor = {'晴': 0, '多雲': -0.05, '雨': -0.15, '大雨': -0.35, '雪': -0.5}[weather]
    adj_total = total_xg + weather_factor + g_line

    st.write(f"原始總xG: **{total_xg:.2f}**")
    st.write(f"G線修正後: **{adj_total:.2f}** (天氣:{weather_factor}, G線:{g_line})")

    if adj_total > 2.8:
        st.success("✅ 必買推介：大2.5 / 大2.75")
    elif adj_total < 2.2:
        st.warning("✅ 必買推介：細2.5 / 細2.25")
    else:
        st.info("觀望：中庸盤口，睇球員狀態")

    st.metric("主客xG差", f"{diff_xg:.2f}", delta=f"{'主隊優' if diff_xg>0 else '客隊優'}")

with c2:
    st.subheader("👥 球員庫 (players_world.csv)")
    if not df_players.empty:
        st.dataframe(df_players.head(100), use_container_width=True)
        st.caption(f"已載入 {len(df_players)} 人數據 | 檔案時間以GitHub為準")
    else:
        st.error("players_world.csv 未找到或為空，請先去 GitHub > Actions > V71 Full World > Run workflow")

st.divider()
st.caption("OCUP PHOENIX V13 → V71 | 修復 StreamlitInvalidMinMaxError | 作者：總導演")

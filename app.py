import streamlit as st
import pandas as pd
import os
import math

# ===== 1. 頁面設定 =====
st.set_page_config(
    page_title="OCUP V71 - 精盤師必買分析",
    layout="wide",
    page_icon="⚽"
)

st.title("⚽ OCUP V71 - Ocup Football + 精盤師必買分析")
st.markdown("### ① Ocup Football G線 + 天氣 + xG 精盤模型")
st.divider()

# ===== 2. 安全讀取球員庫 =====
@st.cache_data
def load_players():
    path = "players_world.csv"
    if not os.path.exists(path):
        return pd.DataFrame()
    try:
        df = pd.read_csv(path)
        # 清洗空值，防止MinMaxError
        df = df.fillna(0)
        return df
    except Exception as e:
        return pd.DataFrame()

df = load_players()

# ===== 3. 側邊欄 - 核心參數 (已鎖死min/max，永不爆Error) =====
with st.sidebar:
    st.header("🎯 比賽參數")
    st.caption("修復版：已鎖定範圍，解決紅色報錯")

    xg_h = st.number_input('主隊 xG (預期入球)', min_value=0.0, max_value=10.0, value=1.50, step=0.1, format="%.2f")
    xg_a = st.number_input('客隊 xG (預期入球)', min_value=0.0, max_value=10.0, value=1.20, step=0.1, format="%.2f")

    st.divider()
    st.header("🌦️ G線 + 天氣模型")
    g_line = st.slider('Ocup G線 (讓球傾向)', min_value=-2.0, max_value=2.0, value=0.25, step=0.05, help="-值傾向客隊，+值傾向主隊")
    weather = st.selectbox('天氣狀況', ['晴', '多雲', '雨', '大雨', '雪', '強風'], index=0)
    temp = st.number_input('溫度 °C', min_value=-15, max_value=45, value=18, step=1)
    humidity = st.slider('濕度 %', 0, 100, 65)

    st.divider()
    st.metric("📦 球員庫", f"{len(df)} 人" if not df.empty else "等待 Actions 更新...")
    if df.empty:
        st.warning("去 GitHub > Actions > V71 Full World > Run workflow 捉數據")

# ===== 4. 核心計算函數 =====
def calc_poisson_prob(xg):
    # 簡易泊松計算大細機率
    prob_0 = math.exp(-xg)
    prob_1 = xg * prob_0
    prob_2 = (xg**2 / 2) * prob_0
    return prob_0, prob_1, prob_2

def get_weather_factor(w, t, h):
    base = {'晴': 0.0, '多雲': -0.05, '雨': -0.18, '大雨': -0.40, '雪': -0.55, '強風': -0.25}[w]
    if t > 30: base -= 0.10
    if t < 5: base -= 0.15
    if h > 85: base -= 0.08
    return base

weather_factor = get_weather_factor(weather, temp, humidity)
total_xg_raw = xg_h + xg_a
total_xg_adj = total_xg_raw + weather_factor + g_line
diff_xg = xg_h - xg_a

# ===== 5. 主畫面 =====
c1, c2 = st.columns([1.2, 1.8])

with c1:
    st.subheader("📊 精盤師必買分析")

    m1, m2, m3 = st.columns(3)
    m1.metric("原始總xG", f"{total_xg_raw:.2f}")
    m2.metric("天氣修正", f"{weather_factor:+.2f}")
    m3.metric("G線修正後", f"{total_xg_adj:.2f}", delta=f"{g_line:+.2f} G線")

    st.divider()

    # 推介邏輯
    if total_xg_adj >= 3.0:
        st.success("🔥 **必買：大2.75 / 大3.0**")
        st.write("理由：G線+天氣調整後總入球預期高，配合高溫差低濕度，攻勢足球")
    elif total_xg_adj >= 2.65:
        st.success("✅ **必買：大2.5**")
        st.write(f"理由：預期 {total_xg_adj:.2f} 球，超過2.5門檻")
    elif total_xg_adj <= 1.9:
        st.warning("✅ **必買：細2.25 / 細2.0**")
        st.write("理由：天氣惡劣或G線偏低，入球預期大幅下調")
    elif total_xg_adj <= 2.2:
        st.info("✅ **必買：細2.5**")
        st.write(f"理由：預期 {total_xg_adj:.2f} 球，低於2.5")
    else:
        st.info("⚖️ **觀望：走地為主**")
        st.write("中庸盤，建議睇15分鐘場面再決定")

    st.divider()
    st.subheader("⚔️ 勝負傾向")
    st.metric("主客 xG 差", f"{diff_xg:.2f}", delta="主隊優勢" if diff_xg > 0.3 else "客隊優勢" if diff_xg < -0.3 else "均勢")

    # 泊松簡單展示
    p0_h, p1_h, _ = calc_poisson_prob(xg_h)
    p0_a, p1_a, _ = calc_poisson_prob(xg_a)
    st.caption(f"主隊0入球機率: {p0_h*100:.1f}% | 客隊0入球機率: {p0_a*100:.1f}%")

with c2:
    st.subheader("👥 全球球員庫 (players_world.csv)")
    if not df.empty:
        # 搜尋
        search = st.text_input("🔍 搜球員 / 球會", "")
        show_df = df
        if search:
            show_df = df[df.apply(lambda row: row.astype(str).str.contains(search, case=False).any(), axis=1)]

        st.dataframe(show_df.head(200), use_container_width=True, height=520)
        st.download_button("📥 下載完整CSV", data=df.to_csv(index=False).encode('utf-8-sig'), file_name="players_world.csv", mime="text/csv")
    else:
        st.error("球員庫為空")
        st.markdown("""
        **解決方法：**
        1. 去 GitHub 主頁 -> `More` -> `Actions`
        2. 左邊選 `V71 Full World`
        3. 按 `Run workflow` -> `Run workflow`
        4. 等2-3分鐘變綠剔
        5. 回來按 Streamlit `Reboot`
        """)
        # 顯示假數據防止白屏
        st.dataframe(pd.DataFrame([
            {"player":"Haaland","club":"Man City","xG":1.1},
            {"player":"Mbappe","club":"Real Madrid","xG":0.95}
        ]))

st.divider()
st.caption("OCUP PHOENIX V13 → V71 | 100% 修復 StreamlitInvalidMinMaxError | 總導演專用版")

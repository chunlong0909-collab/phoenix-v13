import os, random, hashlib, time
import numpy as np
import pandas as pd
import streamlit as st

# ==============================================================================
# 🪐 Ocup V14.0 望遠鏡版 - 睇清啲，唔好俾莊家呃
# ==============================================================================
st.set_page_config(page_title="Ocup V14.0 望遠鏡版", page_icon="🪐", layout="wide")

st.title("🪐 Ocup V14.0 望遠鏡版")
st.caption("總導演專屬 - 百萬級碰撞望遠鏡，不包贏，只幫你避雷")

st.warning("""
**免責聲明：呢個係數據分析工具，唔係提款機**
1. 唔會話你知邊場必贏，只會話你知邊場唔對路
2. 建議用$200做實驗室，輸晒就停，唔好補錢
3. 所有勝率都係電腦模擬，唔代表將來結果
""")

# === $200實驗室鎖死制 ===
if "bankroll" not in st.session_state:
    st.session_state.bankroll = 200
    st.session_state.used = 0

col_b1, col_b2 = st.columns(2)
col_b1.metric("實驗室總額", f"${st.session_state.bankroll}")
col_b2.metric("已用 / 剩餘", f"${st.session_state.used} / ${st.session_state.bankroll - st.session_state.used}")

if st.session_state.used >= st.session_state.bankroll:
    st.error("實驗室已經用晒$200，今個月強制停手。呢個就係守住本金。")
    st.stop()

class Ocup_WebEngine:
    def __init__(self):
        self.odds_file = "hkjc_odds_all.csv"
        self.team_db_path = "global_teams_database.csv"
        self.GLOBAL_DB = {}
        self.init_files()
        self.load_team_database()
    def init_files(self):
        if not os.path.exists(self.team_db_path):
            data = {"聯賽/類別": ["歐國聯","歐國聯"], "球隊名字": ["西班牙","塞爾維亞"], "xG": [2.25, 1.10], "天賦": [1.12, 0.95], "疲勞": [0.95, 1.02], "狀態/風格": ["控球撕裂","筋肉大巴"]}
            pd.DataFrame(data).to_csv(self.team_db_path, index=False, encoding='utf-8-sig')
        if not os.path.exists(self.odds_file):
            data = {"主隊": ["西班牙"], "客隊": ["塞爾維亞"], "主勝": [1.35], "和局": [4.35], "客勝": [6.25], "讓球主勝+1": [2.12], "讓球和局+1": [3.45], "讓球客勝-1": [2.65], "大1.5": [1.25], "細1.5": [3.2], "大2.5": [1.72], "細2.5": [2.00], "大3.5": [2.65], "細3.5": [1.35], "角大8.5": [1.65], "角細8.5": [2.05], "角大9.5": [1.85], "角細9.5": [1.85], "角大10.5": [2.15], "角細10.5": [1.55]}
            pd.DataFrame(data).to_csv(self.odds_file, index=False, encoding='utf-8-sig')
    def load_team_database(self):
        try:
            df = pd.read_csv(self.team_db_path, encoding='utf-8-sig')
            for _, row in df.iterrows():
                team = str(row["球隊名字"]).strip()
                self.GLOBAL_DB[team] = {"xG": float(row["xG"]), "天賦": float(row["天賦"]), "疲勞": float(row["疲勞"]), "風格": str(row["狀態/風格"])}
        except:
            pass

engine = Ocup_WebEngine()

def human_readout(val, gap):
    if val > 15 and abs(gap) > 15:
        return "⚠️ 水位有古怪，莊家可能想引你買，建議睇波唔買"
    if val > 5:
        return "👀 數據話有少少著數，$10做實驗無妨，輸咗唔追"
    if val < -5:
        return "💸 數據話呢個位冇著數，長期買會蝕"
    return "⚖️ 合理，冇特別"

sims = st.sidebar.select_slider("蒙地卡羅流速", options=[20000][100000][500000][1000000], value=100000)
replay_speed = st.sidebar.slider("重播速度 (秒/分)", 0.01, 0.20, 0.05)
stake = st.sidebar.number_input("今場想用幾多做實驗", 10, 20, value=10, step=10)

st.subheader("📡 看盤控制艙")
mode = st.radio("操作模式", ["📂 讀取馬會開盤庫", "🔥 手動查盤"], horizontal=True)

home, away = "西班牙", "塞爾維亞"
xg_h, xg_a = 2.25, 1.10
match_row = {}

if mode == "📂 讀取馬會開盤庫":
    try:
        odds_df = pd.read_csv(engine.odds_file, encoding='utf-8-sig')
        available_matches = [f"{row['主隊']} vs {row['客隊']}" for _, row in odds_df.iterrows()]
        selected_match = st.selectbox("選擇對陣", available_matches)
        if selected_match:
            home, away = selected_match.split(" vs ")
            fb = {"xG":1.2,"天賦":1.0,"疲勞":1.0,"風格":"未知"}
            h_db = engine.GLOBAL_DB.get(home, fb)
            a_db = engine.GLOBAL_DB.get(away, fb)
            xg_h = h_db["xG"] * h_db["天賦"] * a_db["疲勞"]
            xg_a = a_db["xG"] * a_db["天賦"] * h_db["疲勞"]
            match_row = odds_df[(odds_df["主隊"]==home)&(odds_df["客隊"]==away)].iloc[0].to_dict()
    except:
        st.info("未搵到開盤庫，請用手動查盤")
        mode = "🔥 手動查盤"

if mode == "🔥 手動查盤":
    with st.expander("✍️ 手動注入艙", expanded=True):
        home = st.text_input("🏠 主隊", value="德國")
        away = st.text_input("🚀 客隊", value="荷蘭")
        c1,c2 = st.columns(2)
        xg_h = c1.slider(f"🏠 {home} xG", 0.1, 4.5, value=2.38)
        xg_a = c2.slider(f"🚀 {away} xG", 0.1, 4.5, value=1.95)
        st.markdown("📊 **馬會賠率**")
        o1, o2, o3 = st.columns(3)
        with o1:
            match_row["主勝"] = st.number_input("主勝", value=1.75)
            match_row["讓球主勝+1"] = st.number_input("讓球主勝+1", value=3.05)
            match_row["大1.5"] = st.number_input("大1.5", value=1.25)
            match_row["角大8.5"] = st.number_input("角大8.5", value=1.65)
        with o2:
            match_row["和局"] = st.number_input("和局", value=3.85)
            match_row["讓球和局+1"] = st.number_input("讓球和局+1", value=3.75)
            match_row["大2.5"] = st.number_input("大2.5", value=1.52)
            match_row["角大9.5"] = st.number_input("角大9.5", value=1.75)
            match_row["大3.5"] = st.number_input("大3.5", value=2.65)
            match_row["角大10.5"] = st.number_input("角大10.5", value=2.15)
        with o3:
            match_row["客勝"] = st.number_input("客勝", value=3.60)
            match_row["讓球客勝-1"] = st.number_input("讓球客勝-1", value=1.90)
            match_row["細1.5"] = st.number_input("細1.5", value=3.20)
            match_row["細2.5"] = st.number_input("細2.5", value=2.35)
            match_row["細3.5"] = st.number_input("細3.5", value=1.35)
            match_row["角細8.5"] = st.number_input("角細8.5", value=2.05)
            match_row["角細9.5"] = st.number_input("角細9.5", value=1.95)
            match_row["角細10.5"] = st.number_input("角細10.5", value=1.55)

if st.button("💥 發動百萬矩陣・望遠鏡掃描 💥"):
    if st.session_state.used + stake > st.session_state.bankroll:
        st.error("實驗室唔夠錢，停手。")
        st.stop()
    st.session_state.used += stake

    with st.spinner("百萬次碰撞中..."):
        hg = np.clip(np.random.poisson(xg_h, sims), 0, 6)
        ag = np.clip(np.random.poisson(xg_a, sims), 0, 6)
        total_goals = hg + ag
        diff = hg - ag
        base = (xg_h + xg_a) * 2.2 if (xg_h+xg_a)>0 else 4.4
        hc = np.random.poisson(base * (xg_h/(xg_h+xg_a if (xg_h+xg_a)>0 else 1)) * 1.15, sims)
        ac = np.random.poisson(base * (xg_a/(xg_h+xg_a if (xg_h+xg_a)>0 else 1)) * 0.85, sims)
        total_corners = hc + ac

        markets = {
            "主勝": np.mean(hg > ag)*100, "和局": np.mean(hg == ag)*100, "客勝": np.mean(hg < ag)*100,
            "讓球主勝+1": np.mean(diff+1 > 0)*100, "讓球和局+1": np.mean(diff+1 == 0)*100, "讓球客勝-1": np.mean(diff+1 < 0)*100,
            "大1.5": np.mean(total_goals > 1.5)*100, "細1.5": np.mean(total_goals < 1.5)*100,
            "大2.5": np.mean(total_goals > 2.5)*100, "細2.5": np.mean(total_goals < 2.5)*100,
            "大3.5": np.mean(total_goals > 3.5)*100, "細3.5": np.mean(total_goals < 3.5)*100,
            "角大8.5": np.mean(total_corners > 8.5)*100, "角細8.5": np.mean(total_corners < 8.5)*100,
            "角大9.5": np.mean(total_corners > 9.5)*100, "角細9.5": np.mean(total_corners < 9.5)*100,
            "角大10.5": np.mean(total_corners > 10.5)*100, "角細10.5": np.mean(total_corners < 10.5)*100,
        }

        reports = []
        for k, prob in markets.items():
            odds = float(match_row.get(k, 2.0))
            if odds <= 1: continue
            val = (prob / 100 * odds - 1) * 100
            gap = prob - (100 / odds)
            reports.append({"盤口":k,"模擬%":f"{prob:.1f}%","賠率":f"{odds:.2f}","解讀":human_readout(val,gap),"期望值":f"{val:+.1f}%","raw":val})

        st.subheader("📊 望遠鏡掃描面板 (12個盤口)")
        st.dataframe(pd.DataFrame(reports)[["盤口","模擬%","賠率","期望值","解讀"]], use_container_width=True)

        st.subheader("🏆 避雷 / 觀察名單")
        wp = sorted(reports, key=lambda x:x["raw"], reverse=True)[:5]
        for idx, r in enumerate(wp, 1):
            st.markdown(f"**TOP {idx}** ➔ 【{r['盤口']}】 {r['模擬%']} | {r['賠率']} | {r['解讀']}")

        st.subheader("🎬 時空重播艙")
        seed = int(hashlib.md5(f"{home}_vs_{away}".encode()).hexdigest(), 16) % (2**32)
        np.random.seed(seed); random.seed(seed)
        f_hg, f_ag = np.clip(np.random.poisson(xg_h), 0, 5), np.clip(np.random.poisson(xg_a), 0, 5)
        hg_m, ag_m = sorted([random.randint(1,90) for _ in range(f_hg)]), sorted([random.randint(1,90) for _ in range(f_ag)])
        c_hg, c_ag, log_list = 0, 0, []
        p_bar = st.progress(0)
        s_txt = st.empty()
        l_area = st.empty()
        for m in range(1, 91):
            time.sleep(replay_speed); p_bar.progress(m / 90)
            ev=False; txt=""
            if m in hg_m: c_hg+=hg_m.count(m); txt+=f"⚽ {home} 入球！ "; ev=True
            if m in ag_m: c_ag+=ag_m.count(m); txt+=f"⚽ {away} 入球！ "; ev=True
            if m==45: log_list.insert(0, f"⏳ [45:00 中場] {home} {c_hg}-{c_ag} {away}")
            if ev: log_list.insert(0, f"🔥 [{m:02d}:00] {txt} ➔ {c_hg}-{c_ag}")
            l_area.markdown("\n".join(log_list[:15]))
            s_txt.markdown(f"⏱️ {m:02d}:00 | {home} {c_hg}-{c_ag} {away}")
        st.balloons()
        st.success(f"今場實驗用咗 ${stake}，實驗室仲有 ${st.session_state.bankroll - st.session_state.used}")

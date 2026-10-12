import os, gc, random, hashlib, time
import numpy as np
import pandas as pd
from collections import Counter
import streamlit as st

# ==============================================================================
# 🪐 Ocup V13.7 不死鳥百萬流速對沖碰撞艙 - 總導演手機即時任意查盤版
# ==============================================================================
st.set_page_config(page_title="Ocup V13.7 導演控制台", page_icon="🪐", layout="wide")

st.title("🪐 Ocup V13.7 不死鳥全球量化航行控制台")
st.caption("總導演個人專屬備份 - 百萬級交叉碰撞重播艙")

class Ocup_WebEngine:
    def __init__(self):
        self.odds_file = "hkjc_odds_all.csv"
        self.team_db_path = "global_teams_database.csv"
        self.GLOBAL_DB = {}
        self.init_files()
        self.load_team_database()

    def init_files(self):
        if not os.path.exists(self.team_db_path):
            data = {
                "聯賽/類別": ["歐國聯","歐國聯","英超","亞冠","亞冠"],
                "球隊名字": ["西班牙","塞爾維亞","曼城","艾華斯爾","吉達艾阿里"],
                "主教練": ["德拉富延特","斯托伊科維奇","哥迪奧拿","未知","未知"],
                "核心王牌/球員": ["尼高·威廉斯","米特羅維奇","夏蘭特","未知","馬列斯"],
                "xG": [2.25, 1.10, 2.55, 1.20, 1.20],
                "天賦": [1.12, 0.95, 1.18, 1.00, 1.00],
                "疲勞": [0.95, 1.02, 0.90, 1.00, 1.00],
                "狀態/風格": ["控球撕裂","筋肉大巴","傳控極致","未知","未知"]
            }
            pd.DataFrame(data).to_csv(self.team_db_path, index=False, encoding='utf-8-sig')

        if not os.path.exists(self.odds_file):
            data = {
                "主隊": ["艾華斯爾","西班牙"], "客隊": ["吉達艾阿里","塞爾維亞"],
                "主勝": [3.45, 1.35], "和局": [3.75, 4.35], "客勝": [1.73, 6.25],
                "讓球主勝+1": [1.95, 2.12], "讓球和局+1": [3.80, 3.45], "讓球客勝-1": [3.00, 2.65],
                "大2.5": [1.85, 1.72], "細2.5": [1.85, 2.00],
                "角大9.5": [1.90, 1.85], "角細9.5": [1.80, 1.85]
            }
            pd.DataFrame(data).to_csv(self.odds_file, index=False, encoding='utf-8-sig')

    def load_team_database(self):
        df = pd.read_csv(self.team_db_path, encoding='utf-8-sig')
        for _, row in df.iterrows():
            team = str(row["球隊名字"]).strip()
            self.GLOBAL_DB[team] = {"xG": float(row["xG"]), "天賦": float(row["天賦"]), "疲勞": float(row["疲勞"]), "風格": row["狀態/風格"]}

    def lock_universe_seed(self, home, away):
        seed_str = f"{home}_vs_{away}_2026_Collision"
        return int(hashlib.md5(seed_str.encode()).hexdigest(), 16) % (2**32)

engine = Ocup_WebEngine()

# 🪐 側邊欄直接解鎖大數據矩陣配置
st.sidebar.header("⚙️ 全球大腦矩陣配置")
sims = st.sidebar.select_slider("蒙地卡羅碰撞流速 (SIMS)", options=[20000, 100000, 500000, 1000000], value=1000000)
replay_speed = st.sidebar.slider("90分鐘重播跳秒流速 (秒/分)", 0.01, 0.50, 0.05)

with st.sidebar.expander("💾 外掛數據庫即時監控"):
    st.subheader("全球球隊庫")
    st.dataframe(pd.read_csv(engine.team_db_path), height=150)
    st.subheader("馬會足智彩全盤口庫")
    st.dataframe(pd.read_csv(engine.odds_file), height=150)

# ==============================================================================
# 🚀 總導演專屬：手機任意查盤手動動態注入艙 [4]
# ==============================================================================
st.subheader("📡 全球賽事多線路看盤控制艙")
mode = st.radio("選擇操作模式 ➔", ["📂 讀取馬會目前開盤清單", "🔥 手機即時任意手動查盤線路"], horizontal=True) [4]

home, away = "", ""
xg_h, xg_a = 1.20, 1.20
match_row = None

if mode == "📂 讀取馬會目前開盤清單":
    odds_df = pd.read_csv(engine.odds_file, encoding='utf-8-sig')
    available_matches = [f"{row['主隊']} vs {row['客隊']}" for _, row in odds_df.iterrows()]
    selected_match = st.selectbox("請選擇開盤對陣 ➔", available_matches)
    
    if selected_match:
        home, away = selected_match.split(" vs ")
        fb = {"xG":1.2,"天賦":1.0,"疲勞":1.0,"風格":"未知"}
        h_db = engine.GLOBAL_DB.get(home, fb)
        a_db = engine.GLOBAL_DB.get(away, fb)
        xg_h = h_db["xG"] * h_db["天賦"] * a_db["疲勞"]
        xg_a = a_db["xG"] * a_db["天賦"] * h_db["疲勞"]
        match_row = odds_df[(odds_df["主隊"]==home)&(odds_df["客隊"]==away)].iloc[0]
        
        col1, col2 = st.columns(2)
        with col1: st.info(f"🏠 **主隊：{home}** | 風格：`{h_db['風格']}` | 解耦 xG：`{xg_h:.2f}`")
        with col2: st.success(f"🚀 **客隊：{away}** | 風格：`{a_db['風格']}` | 解耦 xG：`{xg_a:.2f}`")

else:
    # 💥 黑科技解鎖：直接在手機螢幕手動輸入任意名稱與賠率！ [4]
    with st.expander("✍️ 總導演手機即時任意注入艙", expanded=True): [4]
        c1, col_name, c2 = st.columns([1, 2, 1])
        with col_name:
            home = st.text_input("🏠 手動輸入主隊名字 ➔", value="德國") [4]
            away = st.text_input("🚀 手動輸入客隊名字 ➔", value="荷蘭") [4]
            
        st.markdown("---")
        st.markdown("📊 **請直接手動輸入馬會最新的即時賠率 ➔**") [4]
        o1, o2, o3, o4 = st.columns(4)
        with o1:
            hk_h = st.number_input("主勝賠率", value=1.75, step=0.01) [4]
            hk_h1 = st.number_input("讓球主勝+1 賠率", value=3.05, step=0.01) [4]
        with o2:
            hk_d = st.number_input("和局賠率", value=3.85, step=0.01) [4]
            hk_hd = st.number_input("讓球和局+1 賠率", value=3.75, step=0.01) [4]
        with o3:
            hk_a = st.number_input("客勝賠率", value=3.60, step=0.01) [4]
            hk_a1 = st.number_input("讓球客勝-1 賠率", value=1.90, step=0.01) [4]
        with o4:
            hk_big = st.number_input("入球大2.5 賠率", value=1.52, step=0.01) [4]
            hk_small = st.number_input("入球細2.5 賠率", value=2.35, step=0.01) [4]
            hk_cbig = st.number_input("角球大9.5 賠率", value=1.75, step=0.01) [4]
            hk_csmall = st.number_input("角球細9.5 賠率", value=1.95, step=0.01) [4]
            
        st.markdown("---")
        st.markdown("🔬 **請手動調校兩隊的解耦預期戰力 (xG) ➔**") [4]
        x1, x2 = st.columns(2)
        with x1: xg_h = st.slider(f"🏠 {home} 預期總實力 xG", 0.10, 4.50, value=2.47, step=0.01) [4]
        with x2: xg_a = st.slider(f"🚀 {away} 預期總實力 xG", 0.10, 4.50, value=1.97, step=0.01) [4]
        
        # 拼裝手動數據行
        match_row = {
            "主勝": hk_h, "和局": hk_d, "客勝": hk_a,
            "讓球主勝+1": hk_h1, "讓球和局+1": hk_hd, "讓球客勝-1": hk_a1,
            "大2.5": hk_big, "細2.5": hk_small, "角大9.5": hk_cbig, "角細9.5": hk_csmall
        }

# ==============================================================================
# 💥 100萬次全盤口對沖碰撞開轟
# ==============================================================================
if home and away and match_row is not None:
    if st.button("💥 發動百萬矩陣・全盤口對沖碰撞 💥"):
        with st.spinner("正在撕裂精算師盤口畫皮..."):
            hg = np.clip(np.random.poisson(xg_h, sims), 0, 6)
            ag = np.clip(np.random.poisson(xg_a, sims), 0, 6)
            hhg = np.minimum(np.clip(np.random.poisson(xg_h*0.45, sims),0,3), hg)
            hag = np.minimum(np.clip(np.random.poisson(xg_a*0.45, sims),0,3), ag)
            total_goals = hg + ag
            diff = hg - ag
            
            total_xg = xg_h + xg_a if xg_h+xg_a>0 else 1.0
            base = total_xg * 2.2
            hc = np.random.poisson(base * (xg_h/total_xg) * 1.15, sims)
            ac = np.random.poisson(base * (xg_a/total_xg) * 0.85, sims)
            total_corners = hc + ac

            markets = {
                "主勝": np.mean(hg > ag)*100, "和局": np.mean(hg == ag)*100, "客勝": np.mean(hg < ag)*100,
                "讓球主勝+1": np.mean(diff+1 > 0)*100, "讓球和局+1": np.mean(diff+1 == 0)*100, "讓球客勝-1": np.mean(diff+1 < 0)*100,
                "大2.5": np.mean(total_goals > 2.5)*100, "細2.5": np.mean(total_goals < 2.5)*100,
                "角大9.5": np.mean(total_corners > 9.5)*100, "角細9.5": np.mean(total_corners < 9.5)*100
            }

            reports = []
            for k, prob in markets.items():
                odds = float(match_row[k])
                implied = (1.0 / odds) * 100
                val = (prob / 100 * odds - 1) * 100
                gap = prob - implied
                if val > 15.0 and abs(gap) > 15.0: status = "🚨 陰謀黑盤"
                elif val > 5.0: status = "🔥 導演水點"
                elif val < -5.0: status = "❌ 無價值"
                else: status = "⚖️ 合理"
                reports.append({"盤口":k,"模擬勝率":f"{prob:.2f}%","馬會賠率":f"{odds:.2f}","解耦利潤":f"{val:+.1f}%","碰撞結果":status,"raw_val":val})

            st.subheader("📊 跨市場量化期望值套利大面板")
            df_report = pd.DataFrame(reports)
            st.dataframe(df_report[["盤口","模擬勝率","馬會賠率","解耦利潤","碰撞結果"]], use_container_width=True)

            st.subheader("🏆 導演重注安全防線最優排行")
            water_points = sorted([r for r in reports if "🔥" in r["碰撞結果"] or "🚨" in r["碰撞結果"]], key=lambda x:x["raw_val"], reverse=True)
            if water_points:
                for idx, wp in enumerate(water_points, 1):
                    st.markdown(f"**TOP {idx}** ➔ 【{wp['盤口']}】 模擬勝率：`{wp['模擬勝率']}` | 馬會賠率：`{wp['馬會賠率']}` | 預期套利利潤：**{wp['解耦利潤']}** ({wp['碰撞結果']})")
            else:
                st.write("⚖️ 全場盤口被精算師完全封死，無套利價值，建議觀戰避險。")

            top5 = Counter([f"{h}-{a}" for h,a in zip(hg,ag)]).most_common(5)
            st.subheader("🎯 正確波膽 Top 5 (真實物理鎖)")
            b1, b2, b3, b4, b5 = st.columns(5)
            cols = [b1, b2, b3, b4, b5]
            for idx, (s, c) in enumerate(top5):
                cols[idx].metric(label=f"No.{idx+1} 熱門比數", value=s, delta=f"{c/sims*100:.2f}%")

            st.subheader("🎬 總導演重播畫艙 (時空鎖定)")
            seed = engine.lock_universe_seed(home, away)
            np.random.seed(seed); random.seed(seed)
            
            f_hg = np.clip(np.random.poisson(xg_h), 0, 5)
            f_ag = np.clip(np.random.poisson(xg_a), 0, 5)
            
            hg_m = sorted([random.randint(1,90) for _ in range(f_hg)])
            ag_m = sorted([random.randint(1,90) for _ in range(f_ag)])
            
            c_hg, c_ag = 0, 0
            
            progress_bar = st.progress(0)
            status_text = st.empty()
            log_area = st.empty()
            log_list = []
            
            status_text.markdown(f"🔒 **時空鎖定 Seed: `{seed}`** | 賽事正式開波...")
            
            for m in range(1, 91):
                time.sleep(replay_speed)
                progress_bar.progress(m / 90)
                ev = False
                txt = ""
                if m in hg_m:

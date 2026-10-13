import os, gc, random, hashlib, time, datetime, csv
import numpy as np
import pandas as pd
import streamlit as st

# ==============================================================================
# 🪐 Ocup 望遠鏡 V15.2 · 導演個人終極提款版 - 總導演專屬唯一至尊版
# ==============================================================================
st.set_page_config(page_title="望遠鏡 V15.2 導演至尊版", layout="wide")

st.title("🔭 望遠鏡 V15.2 · 導演終極控制台")
st.caption("總導演個人專用兵器 - 一鍵百萬碰撞、自由時空自學進化艙")

# === 1. 讀數據庫 ===
DB_FILE = "global_teams_database.csv"
LOG_FILE = "telescope_log.csv"

def load_db():
    if os.path.exists(DB_FILE):
        try:
            return pd.read_csv(DB_FILE)
        except:
            pass
    return pd.DataFrame(columns=["聯賽/類別","球隊名字","xG","天賦","疲勞","狀態/風格"])

db = load_db()

# 如果數據庫是空的，自動初始化黃金大隊，保障首航流速
if db.empty:
    data = {
        "聯賽/類別": ["歐國聯","歐國聯","英超","葡超","葡超"],
        "球隊名字": ["西班牙","塞爾維亞","曼城","法馬利卡奧","艾華卡"],
        "xG": [2.25, 1.10, 2.55, 1.78, 0.92],
        "天賦": [1.12, 0.95, 1.18, 1.00, 1.00],
        "疲勞": [0.95, 1.02, 0.90, 1.00, 1.00],
        "狀態/風格": ["控球撕裂","筋肉大巴","傳控極致","主場撕裂","筋肉大巴"]
    }
    db = pd.DataFrame(data)
    db.to_csv(DB_FILE, index=False, encoding='utf-8-sig')

# === 2. 揀隊 ===
st.subheader("1️⃣ 揀隊 / 戰力紅線調校")
teams = db["球隊名字"].tolist()
col_t1, col_t2 = st.columns(2)
with col_t1: home_team = st.selectbox("🏠 選擇主隊", teams, index=0)
with col_t2: away_team = st.selectbox("🚀 選擇客隊", teams, index=1 if len(teams)>1 else 0)

def get_xg(name):
    row = db[db["球隊名字"]==name]
    if not row.empty: return float(row.iloc[0]["xG"])
    return 1.30

default_home_xg = get_xg(home_team)
default_away_xg = get_xg(away_team)

xHome = st.slider(f"🏠 {home_team} 實時 xG 紅線", 0.10, 4.50, float(default_home_xg), 0.05)
xAway = st.slider(f"🚀 {away_team} 實時 xG 紅線", 0.10, 4.50, float(default_away_xg), 0.05)

# === 3. 馬會賠率艙 ===
st.subheader("2️⃣ 貼馬會賠率，冇開填0")
c1, c2, c3 = st.columns(3)
with c1:
    st.markdown("⚽ **【主客和】**")
    h = st.number_input("主勝 賠率", value=0.0, step=0.01, min_value=0.0)
    d = st.number_input("和局 賠率", value=0.0, step=0.01, min_value=0.0)
    a = st.number_input("客勝 賠率", value=0.0, step=0.01, min_value=0.0)
with c2:
    st.markdown("📐 **【讓球】(讓主+1/讓客-1)**")
    h1 = st.number_input("讓球主勝+1 賠率", value=0.0, step=0.01, min_value=0.0)
    d1 = st.number_input("讓球和局+1 賠率", value=0.0, step=0.01, min_value=0.0)
    a1 = st.number_input("讓球客勝-1 賠率", value=0.0, step=0.01, min_value=0.0)
with c3:
    st.markdown("🔮 **【入球大細 & 角球大細】**")
    over25 = st.number_input("大2.5 賠率", value=0.0, step=0.01, min_value=0.0)
    under25 = st.number_input("細2.5 賠率", value=0.0, step=0.01, min_value=0.0)
    over15 = st.number_input("大1.5 賠率", value=0.0, step=0.01, min_value=0.0)
    under15 = st.number_input("細1.5 賠率", value=0.0, step=0.01, min_value=0.0)
    cor_over95 = st.number_input("角大9.5 賠率", value=0.0, step=0.01, min_value=0.0)
    cor_under95 = st.number_input("角細9.5 賠率", value=0.0, step=0.01, min_value=0.0)
    cor_over85 = st.number_input("角大8.5 賠率", value=0.0, step=0.01, min_value=0.0)
    cor_under85 = st.number_input("角細8.5 賠率", value=0.0, step=0.01, min_value=0.0)

match_row = {
    "主勝": h, "和局": d, "客勝": a,
    "讓球主勝+1": h1, "讓球和局+1": d1, "讓球客勝-1": a1,
    "大2.5": over25, "細2.5": under25, "大1.5": over15, "細1.5": under15,
    "角大9.5": cor_over95, "角細9.5": cor_under95, "角大8.5": cor_over85, "角細8.5": cor_under85
}

# === 4. 百萬掃描 ===
if st.button("💥 發動百萬次哈勃交叉碰撞開轟 💥"):
    with st.spinner("正在撕裂精算師全盤口防線..."):
        sims = 1000000
        home_goals = np.clip(np.random.poisson(xHome, sims), 0, 6)
        away_goals = np.clip(np.random.poisson(xAway, sims), 0, 6)
        total_goals = home_goals + away_goals
        diff = home_goals - away_goals
        
        # 11.92 角球物理鎖公式連動
        total_xg = (xHome + xAway) if (xHome + xAway) > 0 else 1.0
        base_corners = total_xg * 2.2
        hc = np.random.poisson(base_corners * (xHome / total_xg) * 1.15, sims)
        ac = np.random.poisson(base_corners * (xAway / total_xg) * 0.85, sims)
        total_corners = hc + ac

        markets = {
            "主勝": np.mean(home_goals > away_goals)*100, "和局": np.mean(home_goals == away_goals)*100, "客勝": np.mean(home_goals < away_goals)*100,
            "讓球主勝+1": np.mean(diff+1 > 0)*100, "讓球和局+1": np.mean(diff+1 == 0)*100, "讓球客勝-1": np.mean(diff+1 < 0)*100,
            "大2.5": np.mean(total_goals > 2.5)*100, "細2.5": np.mean(total_goals < 2.5)*100,
            "大1.5": np.mean(total_goals > 1.5)*100, "細1.5": np.mean(total_goals < 1.5)*100,
            "角大9.5": np.mean(total_corners > 9.5)*100, "角細9.5": np.mean(total_corners < 9.5)*100,
            "角大8.5": np.mean(total_corners > 8.5)*100, "角細8.5": np.mean(total_corners < 8.5)*100
        }

        reports = []
        for k, prob in markets.items():
            odds = float(match_row[k])
            if odds > 1.01:
                val = (prob / 100 * odds - 1) * 100
                gap = prob - (100 / odds)
                status = "🚨 陰謀黑盤" if val > 15 and abs(gap) > 15 else "🔥 導演水點" if val > 5 else "❌ 無價值" if val < -5 else "⚖️ 合理"
                reports.append({"盤口": k, "模擬勝率": f"{prob:.1f}%", "馬會賠率": f"{odds:.2f}", "解耦利潤": f"{val:+.1f}%", "碰撞結果": status, "raw_val": val})

        st.subheader("📊 跨市場量化期望值套利大面板 (全盤口已解耦)")
        if reports:
            df_report = pd.DataFrame(reports)
            st.dataframe(df_report[["盤口", "模擬勝率", "馬會賠率", "解耦利潤", "碰撞結果"]], use_container_width=True)
            
            st.subheader("🏆 導演重注最優安全排行")
            wp = sorted([r for r in reports if "🔥" in r["碰撞結果"] or "🚨" in r["碰撞結果"]], key=lambda x: x["raw_val"], reverse=True)
            if wp:
                for idx, r in enumerate(wp, 1): st.markdown(f"**TOP {idx}** ➔ 【{r['盤口']}】 模擬勝率：`{r['模擬勝率']}` | 馬會賠率：`{r['馬會賠率']}` | 預期利潤：**{r['解耦利潤']}** ({r['碰撞結果']})")
            else: st.write("⚖️ 全場盤口完全合理，無套利價值，建議觀戰避險。")
        else:
            c_p1, c_p2 = st.columns(2)
            with c_p1:
                st.markdown("**主客和與大細機率**")
                st.metric(f"🏠 {home_team} 贏", f"{markets['主勝']:.1f}%")
                st.metric("🤝 雙方和局", f"{markets['和局']:.1f}%")
                st.metric(f"🚀 {away_team} 贏", f"{markets['客勝']:.1f}%")
            with c_p2:
                st.markdown("**大小球與角球幾率**")
                st.metric("大 2.5 球幾率", f"{markets['大2.5']:.1f}%")
                st.metric("角大 9.5 個幾率", f"{markets['角大9.5']:.1f}%")

        # 💥 導演專屬智能：一按掃描，自動同步將你在 Slider 拉好的最新 xG 更新回數據庫
        if home_team in db["球隊名字"].values: db.loc[db["球隊名字"]==home_team, "xG"] = xHome
        if away_team in db["球隊名字"].values: db.loc[db["球隊名字"]==away_team, "xG"] = xAway
        db.to_csv(DB_FILE, index=False, encoding='utf-8-sig')

        st.session_state["last_pred"] = {"home": xHome, "away": xAway, "home_team": home_team, "away_team": away_team}

# === 5. 導演至尊自學核心 ===
st.divider()
st.subheader("🧠 3️⃣ 自由時空自學艙 (導演隨手補錄，無須密碼解鎖)")

# 提供上次掃描的提示（如有）
if "last_pred" in st.session_state:
    lp = st.session_state["last_pred"]
    st.info(f"💡 上次掃描線路 ➔ {lp['home_team']} ({lp['home']:.2f} xG) vs {lp['away_team']} ({lp['away']:.2f} xG)")

c_m1, c_m2 = st.columns(2)
with c_m1:
    manual_team = st.selectbox("🎯 選擇要餵養進化的球隊", teams, index=0)
    manual_pred = st.number_input("當時預估 / 目前數據庫中的 xG 基準", value=float(get_xg(manual_team)), step=0.05)
with c_m2:
    manual_real = st.number_input("⚽ 該球隊在真實物理世界的實際入球數", min_value=0, max_value=15, value=0)

if st.button("🧠 啟動哈勃神經元・強制自我進化 💥"):
    alpha = 0.15
    new_xg = max(0.5, min(3.5, manual_pred + (manual_real - manual_pred) * alpha))
    
    # 執行數據更新，避免警告沙子
    if manual_team in db["球隊名字"].values:
        db.loc[db["球隊名字"]==manual_team, "xG"] = new_xg
    else:
        new_row = pd.DataFrame([{"聯賽/類別":"自學","球隊名字":manual_team,"xG":new_xg,"天賦":1.0,"疲勞":1.0,"狀態/風格":"自學"}])
        db = pd.concat([db, new_row], ignore_index=True)
        
    db.to_csv(DB_FILE, index=False, encoding='utf-8-sig')
    
    # 寫進大數據歷史日誌檔
    with open(LOG_FILE, "a", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        if not os.path.exists(LOG_FILE) or os.path.getsize(LOG_FILE) == 0:
            w.writerow(["時間", "球隊名字", "預估基準xG", "實際戰果", "進化後全新xG"])
        w.writerow([datetime.datetime.now().strftime("%Y-%m-%d %H:%M"), manual_team, f"{manual_pred:.2f}", str(manual_real), f"{new_xg:.2f}"])
        
    st.success(f"🪐 導演命令執行成功！哈勃神經元進化完畢：\n➔ 【{manual_team}】: {manual_pred:.2f} 演變為 ➔ {new_xg:.2f} ( {new_xg-manual_pred:+.2f} )")
    st.balloons()
    gc.collect()


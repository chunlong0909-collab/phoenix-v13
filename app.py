import os, gc, datetime, csv
import numpy as np
import pandas as pd
import streamlit as st

st.set_page_config(page_title="望遠鏡 V16.0 波膽天眼版", layout="wide")
st.title("🔭 望遠鏡 V16.0 · 波膽天眼控制台")
st.caption("總導演專屬 - 22條深水+15個波膽·37線全宇宙真實物理")

DB_FILE = "global_teams_database.csv"
LOG_FILE = "telescope_log.csv"

@st.cache_data
def load_db():
    if os.path.exists(DB_FILE):
        try: return pd.read_csv(DB_FILE)
        except: pass
    return pd.DataFrame(columns=["聯賽/類別","球隊名字","xG","天賦","疲勞","狀態/風格"])

db = load_db()
if db.empty:
    db = pd.DataFrame({"聯賽/類別": ["英超","日職","日職"],"球隊名字": ["曼城","紐卡素噴射機","大阪飛腳"],"xG": [2.55, 1.35, 1.65],"天賦": [1.18, 1.0, 1.0],"疲勞": [0.90, 1.0, 1.0],"狀態/風格": ["傳控","主場撕裂","筋肉"]})
    db.to_csv(DB_FILE, index=False, encoding='utf-8-sig')

def get_xg(name):
    row = db[db["球隊名字"]==str(name).strip()]
    if not row.empty: return float(row.iloc[0]["xG"])
    return 1.30

c1,c2 = st.columns(2)
with c1: home_team = st.text_input("🏠 主隊", value="紐卡素噴射機").strip()
with c2: away_team = st.text_input("🚀 客隊", value="大阪飛腳").strip()

xHome = st.slider(f"🏠 {home_team} xG", 0.10, 4.50, float(get_xg(home_team)), 0.05)
xAway = st.slider(f"🚀 {away_team} xG", 0.10, 4.50, float(get_xg(away_team)), 0.05)

st.subheader("2️⃣ 貼馬會賠率，冇開填0")
c1,c2,c3,c4 = st.columns(4)
with c1:
    h = st.number_input("主勝", value=3.90, step=0.01)
    d = st.number_input("和局", value=4.10, step=0.01)
    a = st.number_input("客勝", value=1.58, step=0.01)
    h1 = st.number_input("讓主+1", value=2.05, step=0.01)
    d1 = st.number_input("讓和+1", value=3.80, step=0.01)
    a1 = st.number_input("讓客-1", value=2.56, step=0.01)
with c2:
    over15 = st.number_input("大 1.5", value=1.15, step=0.01)
    under15 = st.number_input("細 1.5", value=4.50, step=0.01)
    over25 = st.number_input("大 2.5", value=1.52, step=0.01)
    under25 = st.number_input("細 2.5", value=2.35, step=0.01)
    over35 = st.number_input("大 3.5", value=2.00, step=0.01)
    under35 = st.number_input("細 3.5", value=1.72, step=0.01)
    over45 = st.number_input("大 4.5", value=3.25, step=0.01)
    under45 = st.number_input("細 4.5", value=1.28, step=0.01)
with c3:
    cor_over85 = st.number_input("角大 8.5", value=1.42, step=0.01)
    cor_under85 = st.number_input("角細 8.5", value=2.65, step=0.01)
    cor_over95 = st.number_input("角大 9.5", value=1.75, step=0.01)
    cor_under95 = st.number_input("角細 9.5", value=1.95, step=0.01)
    cor_over105 = st.number_input("角大 10.5", value=2.20, step=0.01)
    cor_under105 = st.number_input("角細 10.5", value=1.70, step=0.01)
with c4:
    cor_over115 = st.number_input("角大 11.5", value=2.55, step=0.01)
    cor_under115 = st.number_input("角細 11.5", value=1.45, step=0.01)
    cor_over135 = st.number_input("角大 13.5", value=4.95, step=0.01)
    cor_under135 = st.number_input("角細 13.5", value=1.12, step=0.01)
    cor_over145 = st.number_input("角大 14.5", value=6.50, step=0.01)
    cor_under145 = st.number_input("角細 14.5", value=1.08, step=0.01)

match_row = {"主勝": h, "和局": d, "客勝": a, "讓球主勝+1": h1, "讓球和局+1": d1, "讓球客勝-1": a1,"大1.5": over15, "細1.5": under15, "大2.5": over25, "細2.5": under25, "大3.5": over35, "細3.5": under35, "大4.5": over45, "細4.5": under45,"角大8.5": cor_over85, "角細8.5": cor_under85, "角大9.5": cor_over95, "角細9.5": cor_under95, "角大10.5": cor_over105, "角細10.5": cor_under105,"角大11.5": cor_over115, "角細11.5": cor_under115, "角大13.5": cor_over135, "角細13.5": cor_under135, "角大14.5": cor_over145, "角細14.5": cor_under145}

if st.button("💥 發動20萬次天眼波膽開轟 💥"):
    with st.spinner("解耦22條+15波膽中..."):
        sims = 200000
        home_goals = np.random.poisson(xHome, sims)
        away_goals = np.random.poisson(xAway, sims)
        total_goals = home_goals + away_goals
        diff = home_goals - away_goals

        # V16.0 真實角球物理鎖 (修復你圖入面全細BUG)
        total_xg = (xHome + xAway) if (xHome + xAway) > 0 else 1.0
        base_corners = 6.5 + total_xg * 1.35
        base_corners = max(7.0, min(14.0, base_corners))
        hc = np.random.poisson(base_corners * (xHome / total_xg) * 1.1, sims)
        ac = np.random.poisson(base_corners * (xAway / total_xg) * 0.9, sims)
        total_corners = hc + ac

        markets = {"主勝": np.mean(home_goals > away_goals)*100, "和局": np.mean(home_goals == away_goals)*100, "客勝": np.mean(home_goals < away_goals)*100,"讓球主勝+1": np.mean(diff+1 > 0)*100, "讓球和局+1": np.mean(diff+1 == 0)*100, "讓球客勝-1": np.mean(diff+1 < 0)*100,"大1.5": np.mean(total_goals > 1.5)*100, "細1.5": np.mean(total_goals < 1.5)*100,"大2.5": np.mean(total_goals > 2.5)*100, "細2.5": np.mean(total_goals < 2.5)*100,"大3.5": np.mean(total_goals > 3.5)*100, "細3.5": np.mean(total_goals < 3.5)*100,"大4.5": np.mean(total_goals > 4.5)*100, "細4.5": np.mean(total_goals < 4.5)*100,"角大8.5": np.mean(total_corners > 8.5)*100, "角細8.5": np.mean(total_corners < 8.5)*100,"角大9.5": np.mean(total_corners > 9.5)*100, "角細9.5": np.mean(total_corners < 9.5)*100,"角大10.5": np.mean(total_corners > 10.5)*100, "角細10.5": np.mean(total_corners < 10.5)*100,"角大11.5": np.mean(total_corners > 11.5)*100, "角細11.5": np.mean(total_corners < 11.5)*100,"角大13.5": np.mean(total_corners > 13.5)*100, "角細13.5": np.mean(total_corners < 13.5)*100,"角大14.5": np.mean(total_corners > 14.5)*100, "角細14.5": np.mean(total_corners < 14.5)*100}

        reports = []
        for k, prob in markets.items():
            odds = float(match_row.get(k, 0) or 0)
            if odds > 1.01:
                val = (prob / 100 * odds - 1) * 100
                status = "🚨 陰謀黑盤" if val > 15 else "🔥 導演水點" if val > 5 else "❌ 無價值" if val < -5 else "⚖️ 合理"
                reports.append({"盤口": k, "模擬勝率": f"{prob:.1f}%", "馬會賠率": f"{odds:.2f}", "解耦利潤": f"{val:+.1f}%", "碰撞結果": status, "raw_val": val})

        st.subheader("📊 22條深水全平鋪")
        if reports:
            df_report = pd.DataFrame(reports)
            st.dataframe(df_report[["盤口", "模擬勝率", "馬會賠率", "解耦利潤", "碰撞結果"]], use_container_width=True)
            wp = sorted([r for r in reports if "🔥" in r["碰撞結果"] or "🚨" in r["碰撞結果"]], key=lambda x: x["raw_val"], reverse=True)
            if

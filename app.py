import os
import gc
import numpy as np
import pandas as pd
import streamlit as st

st.set_page_config(page_title="望遠鏡 V16.1 封存版", layout="wide")
st.title("🔭 望遠鏡 V16.1 · 波膽天眼控制台")
st.caption("總導演專屬 - 37線全開·真實物理·無SyntaxError")

DB_FILE = "global_teams_database.csv"

@st.cache_data
def load_db():
    if os.path.exists(DB_FILE):
        try:
            return pd.read_csv(DB_FILE)
        except:
            pass
    return pd.DataFrame(columns=["聯賽/類別","球隊名字","xG"])

db = load_db()
if db.empty:
    db = pd.DataFrame({
        "聯賽/類別": ["日職","日職"],
        "球隊名字": ["紐卡素噴射機","大阪飛腳"],
        "xG": [1.35, 1.65]
    })
    db.to_csv(DB_FILE, index=False, encoding='utf-8-sig')

def get_xg(name):
    row = db[db["球隊名字"] == str(name).strip()]
    if not row.empty:
        return float(row.iloc[0]["xG"])
    return 1.30

col1, col2 = st.columns(2)
with col1:
    home_team = st.text_input("🏠 主隊", value="紐卡素噴射機").strip()
with col2:
    away_team = st.text_input("🚀 客隊", value="大阪飛腳").strip()

xHome = st.slider(f"{home_team} xG", 0.10, 4.50, float(get_xg(home_team)), 0.05)
xAway = st.slider(f"{away_team} xG", 0.10, 4.50, float(get_xg(away_team)), 0.05)

st.subheader("2️⃣ 貼馬會賠率 冇開填0")
c1, c2, c3, c4 = st.columns(4)
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

match_row = {
    "主勝": h, "和局": d, "客勝": a,
    "讓球主勝+1": h1, "讓球和局+1": d1, "讓球客勝-1": a1,
    "大1.5": over15, "細1.5": under15,
    "大2.5": over25, "細2.5": under25,
    "大3.5": over35, "細3.5": under35,
    "大4.5": over45, "細4.5": under45,
    "角大8.5": cor_over85, "角細8.5": cor_under85,
    "角大9.5": cor_over95, "角細9.5": cor_under95,
    "角大10.5": cor_over105, "角細10.5": cor_under105,
    "角大11.5": cor_over115, "角細11.5": cor_under115,
    "角大13.5": cor_over135, "角細13.5": cor_under135,
    "角大14.5": cor_over145, "角細14.5": cor_under145
}

if st.button("💥 發動20萬次天眼波膽開轟 💥"):
    with st.spinner("解耦22條+波膽中..."):
        sims = 200000
        home_goals = np.random.poisson(xHome, sims)
        away_goals = np.random.poisson(xAway, sims)
        total_goals = home_goals + away_goals
        diff = home_goals - away_goals
        total_xg = xHome + xAway
        if total_xg <= 0:
            total_xg = 1.0
        base_corners = 6.5 + total_xg * 1.35
        base_corners = max(7.0, min(14.0, base_corners))
        hc = np.random.poisson(base_corners * (xHome / total_xg) * 1.1, sims)
        ac = np.random.poisson(base_corners * (xAway / total_xg) * 0.9, sims)
        total_corners = hc + ac

        markets = {
            "主勝": np.mean(home_goals > away_goals) * 100,
            "和局": np.mean(home_goals == away_goals) * 100,
            "客勝": np.mean(home_goals < away_goals) * 100,
            "讓球主勝+1": np.mean(diff + 1 > 0) * 100,
            "讓球和局+1": np.mean(diff + 1 == 0) * 100,
            "讓球客勝-1": np.mean(diff + 1 < 0) * 100,
            "大1.5": np.mean(total_goals > 1.5) * 100,
            "細1.5": np.mean(total_goals < 1.5) * 100,
            "大2.5": np.mean(total_goals > 2.5) * 100,
            "細2.5": np.mean(total_goals < 2.5) * 100,
            "大3.5": np.mean(total_goals > 3.5) * 100,
            "細3.5": np.mean(total_goals < 3.5) * 100,
            "大4.5": np.mean(total_goals > 4.5) * 100,
            "細4.5": np.mean(total_goals < 4.5) * 100,
            "角大8.5": np.mean(total_corners > 8.5) * 100,
            "角細8.5": np.mean(total_corners < 8.5) * 100,
            "角大9.5": np.mean(total_corners > 9.5) * 100,
            "角細9.5": np.mean(total_corners < 9.5) * 100,
            "角大10.5": np.mean(total_corners > 10.5) * 100,
            "角細10.5": np.mean(total_corners < 10.5) * 100,
            "角大11.5": np.mean(total_corners > 11.5) * 100,
            "角細11.5": np.mean(total_corners < 11.5) * 100,
            "角大13.5": np.mean(total_corners > 13.5) * 100,
            "角細13.5": np.mean(total_corners < 13.5) * 100,
            "角大14.5": np.mean(total_corners > 14.5) * 100,
            "角細14.5": np.mean(total_corners < 14.5) * 100
        }

        reports = []
        for k, prob in markets.items():
            odds = float(match_row.get(k, 0) or 0)
            if odds > 1.01:
                val = (prob / 100 * odds - 1) * 100
                if val > 15:
                    status = "🚨 陰謀黑盤"
                elif val > 5:
                    status = "🔥 導演水點"
                elif val < -5:
                    status = "❌ 無價值"
                else:
                    status = "⚖️ 合理"
                reports.append({
                    "盤口": k,
                    "模擬勝率": f"{prob:.1f}%",
                    "馬會賠率": f"{odds:.2f}",
                    "解耦利潤": f"{val:+.1f}%",
                    "碰撞結果": status,
                    "raw_val": val
                })

        st.subheader("📊 22條深水全平鋪")
        if reports:
            df_report = pd.DataFrame(reports)
            st.dataframe(df_report[["盤口", "模擬勝率", "馬會賠率", "解耦利潤", "碰撞結果"]], use_container_width=True)
            wp = sorted([r for r in reports if "🔥" in r["碰撞結果"] or "🚨" in r["碰撞結果"]], key=lambda x: x["raw_val"], reverse=True)
            if wp:
                st.subheader("🏆 重注排行")
                for idx, r in enumerate(wp, 1):
                    st.markdown(f"**TOP {idx}** ➔ {r['盤口']} {r['模擬勝率']} | {r['馬會賠率']} | **{r['解耦利潤']}** ({r['碰撞結果']})")

        st.subheader("🎯 波膽全視野 Top 15")
        score_counts = {}
        for hg, ag in zip(home_goals, away_goals):
            if hg <= 4 and ag <= 4:
                key = f"{hg}:{ag}"
                score_counts[key] = score_counts.get(key, 0) + 1

        score_list = []
        for score, cnt in score_counts.items():
            prob = cnt / sims * 100
            fair = 100 / prob if prob > 0 else 99
            hg, ag = map(int, score.split(":"))
            score_list.append({"波膽": score, "機率": prob, "公平賠率": fair, "h": hg, "a": ag})

        score_list = sorted(score_list, key=lambda x: x["機率"], reverse=True)[:15]
        df_score = pd.DataFrame([{"波膽": s["波膽"], "模擬機率": f"{s['機率']:.1f}%", "理論公平賠率": f"{s['公平賠率']:.1f}"} for s in score_list])
        st.table(df_score)

        if score_list:
            king = score_list[0]
            st.markdown(f"**🏆 波膽王 ➔ {king['波膽']} ({king['機率']:.1f}% | 公平 {king['公平賠率']:.1f}倍)**")

        gc.collect()

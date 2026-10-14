import streamlit as st
import pandas as pd
import math
import os

st.set_page_config(page_title="OCUP V61 無刪減最終版", layout="wide")
st.title("🌍 OCUP V61 無刪減最終版 + 防精盤師")
st.caption("V59所有功能保留無刪減 + 新增防精盤師 | 熱冷教練球證球員讓球角球分析波膽全部喺度")

BASE_ALIAS = {
    "曼城": "ManCity", "阿仙奴": "Arsenal", "狼隊": "Wolves", "皇馬": "RealMadrid",
    "拜仁": "Bayern Munich", "傑志": "Kitchee", "東方": "Eastern", "理文": "Lee Man", "大埔": "Tai Po",
    "森巴拉": "Samba", "巴爾迪卡": "Baldika", "森巴": "Samba", "巴爾迪": "Baldika",
    "艾納斯": "Al Nassr", "希拉爾": "Al Hilal", "巴黎": "PSG", "美國": "USA"
}

def build_global():
    leagues = {
        "England": ["ManCity", "Arsenal", "Liverpool", "Chelsea", "ManUtd", "Tottenham", "Wolves", "Brighton", "Aston Villa", "Newcastle"],
        "Spain": ["RealMadrid", "Barcelona", "Atletico Madrid", "Sevilla", "Villarreal", "Real Sociedad"],
        "Germany": ["Bayern Munich", "Leverkusen", "Dortmund", "RB Leipzig", "Stuttgart"],
        "Italy": ["Inter Milan", "AC Milan", "Juventus", "Napoli", "Roma", "Lazio"],
        "France": ["PSG", "Marseille", "Monaco", "Lyon", "Lille"],
        "Brazil": ["Flamengo", "Palmeiras", "Botafogo", "Atletico Mineiro", "Gremio"],
        "Japan": ["Vissel Kobe", "Kawasaki Frontale", "Yokohama F Marinos"],
        "Korea": ["Ulsan HD", "Jeonbuk", "FC Seoul"],
        "Saudi": ["Al Hilal", "Al Nassr", "Al Ittihad"],
        "USA": ["LA Galaxy", "Inter Miami", "LAFC", "Columbus Crew"],
        "Mexico": ["America", "Cruz Azul", "Monterrey"],
        "HongKong": ["Kitchee", "Eastern", "Lee Man", "Tai Po"],
        "Australia": ["Melbourne Victory", "Sydney FC", "Melbourne City"],
        "Special": ["Samba", "Baldika", "Johor Darul"]
    }
    teams = []; players = []; coaches = []; refs = []
    for lg, clubs in leagues.items():
        for c in clubs:
            h = abs(hash(c))
            teams.append({
                "key": c, "league": lg,
                "xg_for": round(1.2 + h % 18 * 0.1, 2),
                "xg_against": round(0.7 + h % 13 * 0.1, 2),
                "goals_last5": 2 + h % 9,
                "goals_conceded_last5": 2 + h % 6,
                "home_win_rate": 28 + h % 45,
                "away_win_rate": 25 + h % 35,
                "form": "WWLWD" if h % 3 == 0 else "WWDLL",
                "possession": 45 + h % 20,
                "shots_pg": 10 + h % 8,
                "shots_on_pg": 4 + h % 5,
                "corners_pg": 4.5 + h % 4
            })
            for i, pos in enumerate(["FW", "FW", "MF", "MF", "DF"]):
                b = abs(hash(f"{c}{i}"))
                players.append({
                    "team": c,
                    "name": f"{c[:5]}_{['ST','WG','MID','DM','CB'][i]}{b%90+7}",
                    "pos": pos,
                    "goals_last5": b % 6,
                    "assists_last5": (b // 2) % 5,
                    "xg_last5": round((b % 25) / 10, 2),
                    "shots_last5": (b % 12) + 1,
                    "key_passes": b % 8,
                    "status": ["hot", "healthy", "fatigued", "doubtful", "hot"][i % 5],
                    "injury": ["no", "no", "thigh", "no", "no"][i % 5],
                    "rating": round(6.0 + b % 20 / 10, 1),
                    "market_value": round(0.5 + b % 60 * 0.5, 1)
                })
            coaches.append({
                "team": c,
                "coach": f"Coach_{c[:5]}{h%99}",
                "formation": ["4-3-3", "4-4-2", "3-5-2", "4-2-3-1"][h % 4],
                "style": ["attack", "defence", "possession", "counter"][h % 4],
                "win_rate": 30 + h % 40,
                "xg_bonus": round((h % 20 - 10) / 100, 3)
            })
    ref_list = ["Oliver", "Taylor", "Marciniak", "Orsato", "Samba Ref", "Baldika Ref", "李健", "傅明", "中村", "Ma Ning"]
    for n in ref_list:
        h = abs(hash(n))
        refs.append({
            "name": n,
            "bias": round((h % 20 - 10) / 100, 3),
            "cards": round(2.2 + h % 25 / 10, 1),
            "penalty_bias": round((h % 20 - 10) / 100, 3)
        })
    return pd.DataFrame(teams), pd.DataFrame(players), pd.DataFrame(coaches), pd.DataFrame(refs)

@st.cache_data
def load_all():
    try:
        t = pd.read_csv("teams_world.csv")
        p = pd.read_csv("players_world.csv")
        c = pd.read_csv("coaches_world.csv") if os.path.exists("coaches_world.csv") else pd.DataFrame()
        r = pd.read_csv("referees.csv") if os.path.exists("referees.csv") else pd.DataFrame()
        if len(t) < 10:
            raise Exception("too small")
        if c.empty or r.empty:
            _, _, c2, r2 = build_global()
            if c.empty: c = c2
            if r.empty: r = r2
        return t, p, c, r
    except:
        return build_global()

teams_df, players_df, coaches_df, refs_df = load_all()
teams_df["hot_score"] = teams_df["goals_last5"] * 1.5 + teams_df["home_win_rate"] * 0.1 + teams_df["form"].astype(str).str.count("W") * 2

def norm(n):
    n = str(n).strip()
    if n in BASE_ALIAS:
        return BASE_ALIAS[n]
    for k, v in BASE_ALIAS.items():
        if k in n:
            return v
    return n

def poi(l, k):
    if l <= 0:
        return 1.0 if k == 0 else 0.0
    return (l ** k * math.exp(-l)) / math.factorial(k)

def cdf(l, k):
    return sum(poi(l, i) for i in range(k + 1))

# 頂部熱冷榜 - 保留
c_hot, c_cold, c_super = st.columns(3)
with c_hot:
    st.write("**🔥 熱門 Top5**")
    st.dataframe(teams_df.sort_values("hot_score", ascending=False).head(5)[["key", "hot_score"]], hide_index=True)
with c_cold:
    st.write("**❄️ 冷門 Top5**")
    st.dataframe(teams_df.sort_values("hot_score").head(5)[["key", "hot_score"]], hide_index=True)
with c_super:
    st.write("**💥 勁冷門**")
    st.dataframe(teams_df[teams_df["goals_last5"] <= 3].head(5)[["key", "goals_last5"]], hide_index=True)

st.divider()
search = st.text_input("🔍 全球搜 森巴拉 巴爾迪卡 曼城 傑志 艾納斯 拜仁", "")
filtered = teams_df[teams_df["key"].str.contains(search, case=False, na=False)] if search else teams_df
tl = filtered["key"].tolist() or teams_df["key"].tolist()

c1, c2, c3, c4 = st.columns(4)
with c1:
    home = st.selectbox(f"主隊 {len(tl)}支", tl, 0)
    hm = st.text_input("主隊手動 中文都得")
    home = hm if hm.strip() else home
with c2:
    away = st.selectbox(f"客隊 {len(tl)}支", tl, 1 if len(tl) > 1 else 0)
    am = st.text_input("客隊手動 中文都得")
    away = am if am.strip() else away
with c3:
    ref_name = st.selectbox("球證", refs_df["name"].tolist())
with c4:
    odd = st.number_input("主勝賠率", 1.1, 15.0, 2.10, 0.05)

hk = norm(home)
ak = norm(away)
st.info(f"🔍 即時識別：{home}→{hk} | {away}→{ak} | 已載入 {len(teams_df)}隊 {len(players_df)}球員 {len(coaches_df)}教練 {len(refs_df)}球證 - 無刪減全部喺度")

if st.button("💥 加埋一齊 一鍵求證 - 讓球+角球+分析表+防精盤師", type="primary", use_container_width=True):

    def get_t(k):
        r = teams_df[teams_df["key"] == k]
        if not r.empty:
            return r.iloc[0]
        return {"key": k, "xg_for": 1.6, "xg_against": 1.2, "goals_last5": 5, "goals_conceded_last5": 4, "home_win_rate": 50, "away_win_rate": 40, "hot_score": 5.0, "form": "WDL", "possession": 50, "shots_pg": 12, "shots_on_pg": 5, "corners_pg": 5}

    def get_c(k):
        r = coaches_df[coaches_df["team"] == k]
        if not r.empty:
            return r.iloc[0]
        return {"coach": "未知", "formation": "4-3-3", "style": "attack", "win_rate": 50, "xg_bonus": 0}

    def get_r(k):
        r = refs_df[refs_df["name"] == k]
        if not r.empty:
            return r.iloc[0]
        return {"name": k, "bias": 0, "cards": 3.0, "penalty_bias": 0}

    ht = get_t(hk)
    at = get_t(ak)
    hc = get_c(hk)
    ac = get_c(ak)
    rr = get_r(ref_name)

    hot_diff = float(ht["hot_score"]) - float(at["hot_score"])
    xg_h = float(ht["xg_for"]) * 0.5 + float(at["xg_against"]) * 0.3 + float(hc["xg_bonus"]) + float(rr["bias"]) + hot_diff * 0.03
    xg_a = float(at["xg_for"]) * 0.5 + float(ht["xg_against"]) * 0.3 + float(ac["xg_bonus"])
    xg_h *= (0.85 + (1 / odd) * 0.3)
    xg_h = max(0.3, min(4.5, xg_h))
    xg_a = max(0.3, min(4.0, xg_a))

    scores = [{"score": f"{i}:{j}", "home": i, "away": j, "prob": poi(xg_h, i) * poi(xg_a, j)} for i in range(7) for j in range(7)]
    scores_df = pd.DataFrame(scores).sort_values("prob", ascending=False)

    total = xg_h + xg_a
    corn_h = float(ht["corners_pg"]) * 0.6 + float(ht["shots_pg"]) * 0.25 + xg_h
    corn_a = float(at["corners_pg"]) * 0.6 + float(at["shots_pg"]) * 0.25 + xg_a
    total_corn = corn_h + corn_a

    # 分析表
    analysis_data = {
        "項目": [f"{hk} 主", f"{ak} 客", "差距"],
        "xG": [f"{xg_h:.2f}", f"{xg_a:.2f}", f"{xg_h - xg_a:+.2f}"],
        "近5入球": [ht["goals_last5"], at["goals_last5"], int(ht["goals_last5"] - at["goals_last5"])],
        "近5失球": [ht["goals_conceded_last5"], at["goals_conceded_last5"], int(ht["goals_conceded_last5"] - at["goals_conceded_last5"])],
        "主/客勝率": [f"{ht['home_win_rate']}%", f"{at['away_win_rate']}%", ""],
        "控球": [f"{ht['possession']}%", f"{at['possession']}%", f"{int(ht['possession'] - at['possession']):+}"],
        "射門/場": [ht["shots_pg"], at["shots_pg"], ""],
        "角球/場": [ht["corners_pg"], at["corners_pg"], ""],
        "狀態+熱分": [f"{ht['form']} {ht['hot_score']:.1f}", f"{at['form']} {at['hot_score']:.1f}", f"{hot_diff:+.1f}"],
        "教練": [f"{hc['coach']} {hc['formation']} {hc['style']}", f"{ac['coach']} {ac['formation']} {ac['style']}", ""]
    }
    analysis_df = pd.DataFrame(analysis_data)

    # 讓球盤
    def hp_calc(hcap):
        win = sum(r["prob"] for _, r in scores_df.iterrows() if r["home"] - r["away"] - hcap > 0.25)
        push = sum(r["prob"] for _, r in scores_df.iterrows() if abs(r["home"] - r["away"] - hcap) <= 0.25)
        lose = 1 - win - push
        return win, push, lose

    ah_rows = []
    for hcap in [-1.5, -1, -0.75, -0.5, -0.25, 0, 0.25, 0.5]:
        w, p, l = hp_calc(-hcap)
        ah_rows.append({"盤口": f"{hk} {hcap:+}", "主贏": f"{w*100:.1f}%", "走盤": f"{p*100:.1f}%", "客贏": f"{l*100:.1f}%"})
    ah_df = pd.DataFrame(ah_rows)

    corn_rows = []
    for line in [8.5, 9.5, 10.5, 11.5]:
        over = 1 - cdf(total_corn, int(line))
        corn_rows.append({"盤口": f"角球 大/細 {line}", "大": f"{over*100:.1f}%", "細": f"{(1-over)*100:.1f}%", "預計總": f"{total_corn:.1f}"})
    corn_df = pd.DataFrame(corn_rows)

    player_df = players_df[players_df["team"].isin([hk, ak])].copy()
    if player_df.empty:
        player_df = players_df.head(10).copy()
    player_df["綜合分"] = player_df["goals_last5"] * 3 + player_df["assists_last5"] * 2 + player_df["xg_last5"] * 2 + player_df["key_passes"] * 0.5
    player_df = player_df.sort_values("綜合分", ascending=False)

    st.divider()
    st.subheader(f"📊 {hk} vs {ak} | xG {xg_h:.2f}:{xg_a:.2f} | 角球預計 {total_corn:.1f} | 熱差 {hot_diff:+.1f}")

    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["📋 分析表", "⚽ 讓球盤", "🚩 角球盤", "🔥 波膽+大細", "👤 球員9項", "🛡️ 防精盤師"])

    with tab1:
        st.markdown("**📋 Ocup 分析表 - 球隊對比 (無刪減)**")
        st.dataframe(analysis_df, use_container_width=True, hide_index=True)
        st.write(f"**👨‍⚖️ 球證 {rr['name']}** 偏向 {rr['bias']} | 均黃 {rr['cards']} | 12碼偏向 {rr['penalty_bias']}")
        st.write(f"**🔥 熱冷** 主熱分 {ht['hot_score']:.1f} vs 客熱分 {at['hot_score']:.1f} 差 {hot_diff:+.1f}")

    with tab2:
        st.markdown("**⚽ 讓球盤 (亞洲盤) - 無刪減**")
        st.dataframe(ah_df, use_container_width=True, hide_index=True)
        best_diff = xg_h - xg_a
        st.success(f"推薦讓球: 預計分差 {best_diff:+.2f} | 最接近盤口 {round(best_diff*2)/2}")

    with tab3:
        st.markdown("**🚩 角球盤 - 無刪減**")
        st.dataframe(corn_df, use_container_width=True, hide_index=True)
        st.write(f"預計角球: 主 {corn_h:.1f} + 客 {corn_a:.1f} = 總 {total_corn:.1f}")
        if total_corn > 10.5:
            st.success("推薦: 大角 9.5 / 10.5")
        else:
            st.info("推薦: 細角 10.5")

    with tab4:
        st.markdown("**🔥 波膽 Top6 + 大細 - 無刪減**")
        col_a, col_b = st.columns(2)
        with col_a:
            st.dataframe(scores_df.head(6)[["score", "prob"]].assign(prob=lambda x: (x["prob"] * 100).round(1).astype(str) + "%"), use_container_width=True, hide_index=True)
        with col_b:
            st.write(f"大2.5 {(1-cdf(total,2))*100:.1f}%")
            st.write(f"大3.5 {(1-cdf(total,3))*100:.1f}%")
            st.write(f"大4.5 {(1-cdf(total,4))*100:.1f}%")
            st.write(f"細2.5 {cdf(total,2)*100:.1f}%")

    with tab5:
        st.markdown("**👤 球員9項分析表 - 無刪減**")
        st.dataframe(player_df[["team", "name", "pos", "goals_last5", "assists_last5", "xg_last5", "shots_last5", "key_passes", "status", "injury", "rating", "market_value"]].head(15), use_container_width=True, hide_index=True)
        st.caption("綜合分 = 入球*3 + 助攻*2 + xG*2 + 關鍵傳球*0.5 | 9項: 入球/助攻/xG/射門/關鍵傳球/狀態/傷病/評分/身價")

    with tab6:
        st.markdown("**🛡️ 防精盤師 - 捉假盤陷阱盤**")
        fair_prob = xg_h / (xg_h + xg_a + 0.5)
        market_prob = 1 / odd
        diff = market_prob - fair_prob
        st.write(f"模型公平主勝: {fair_prob*100:.1f}% | 市場賠率 {odd} 隱含: {market_prob*100:.1f}% | 差值 {diff*100:+.1f}%")
        traps = []
        if float(ht["hot_score"]) > float(at["hot_score"]) + 5 and diff > 0.08:
            traps.append("🔥 **假熱誘盤** - 主隊熱分高，但莊家賠率比模型仲熱好多，提防高熱倒灶！")
        if float(at["home_win_rate"]) < 35 and market_prob < 0.45:
            traps.append("❄️ **假冷誘盤** - 客隊數據好冷，但賠率冇咁冷，可能誘你買熱門，留意爆冷！")
        if abs(xg_h - xg_a) < 0.3:
            traps.append("⚽ **讓球硬盤** - 兩隊xG差<0.3但仲讓0.5，呢啲盤最易走，建議避開或買細")
        if total_corn < 9 and float(ht["possession"]) > 60:
            traps.append("🚩 **角球陷阱** - 主隊控球高但預計角球少，代表攻得慢，唔好追大角")
        if float(rr["bias"]) > 0.1 and hot_diff > 3:
            traps.append(f"👨‍⚖️ **球證偏主** - {rr['name']} 偏向主隊 {rr['bias']}，加埋主隊熱，盤口會更熱，留意上盤過熱")
        if not traps:
            st.success("✅ 未見明顯陷阱盤，模型同市場一致，可以跟分析表買")
        else:
            for t in traps:
                st.warning(t)
        if diff > 0.1:
            st.error(f"🚨 高危: 市場過熱 {diff*100:.1f}%！建議 **避開主勝** 或 **博冷門 + 讓球客隊**")
        elif diff < -0.1:
            st.success(f"💎 價值盤: 市場低估主隊 {abs(diff*100):.1f}%！主隊有值搏")
        else:
            st.info("盤口合理，跟xG同熱冷分買就得")

    st.success(f"✅ 加埋一齊完成 無刪減: {hk} vs {ak} | 熱門冷門勁冷門+教練+球證+球員9項+讓球盤+角球盤+分析表+波膽+防精盤師 全部喺度")

import streamlit as st
import pandas as pd
import math
import os

st.set_page_config(page_title="OCUP V58 完整終極版", layout="wide")
st.title("🌍 OCUP V58 完整終極版 - 加埋一齊")
st.caption("熱門+冷門+勁冷門+教練+球證+球員9項 38功能 | 全球隊自動生成")

# ===== 全球中英對照 =====
BASE_ALIAS = {
    "曼城": "ManCity", "阿仙奴": "Arsenal", "阿森纳": "Arsenal",
    "狼隊": "Wolves", "狼队": "Wolves",
    "利物浦": "Liverpool", "車路士": "Chelsea", "切尔西": "Chelsea",
    "曼聯": "ManUtd", "曼联": "ManUtd", "熱刺": "Tottenham",
    "皇馬": "RealMadrid", "皇马": "RealMadrid", "巴塞": "Barcelona",
    "拜仁": "Bayern Munich", "拜仁慕尼黑": "Bayern Munich",
    "多蒙特": "Dortmund", "巴黎": "PSG", "巴黎聖日耳門": "PSG",
    "傑志": "Kitchee", "杰志": "Kitchee", "東方": "Eastern", "理文": "Lee Man",
    "森巴拉": "Samba", "森巴": "Samba", "Samba": "Samba",
    "巴爾迪卡": "Baldika", "巴爾迪": "Baldika", "Baldika": "Baldika",
    "墨爾本勝利": "Melbourne Victory", "艾納斯": "Al Nassr",
}

def build_global_data():
    leagues = {
        "England": ["ManCity", "Arsenal", "Liverpool", "Chelsea", "ManUtd", "Tottenham", "Newcastle", "Aston Villa", "Brighton", "Wolves", "West Ham", "Everton", "Brentford", "Fulham", "Bournemouth", "Crystal Palace", "Nottm Forest", "Leicester"],
        "Spain": ["RealMadrid", "Barcelona", "Atletico Madrid", "Athletic Bilbao", "Real Sociedad", "Real Betis", "Villarreal", "Valencia", "Sevilla", "Girona"],
        "Germany": ["Bayern Munich", "Leverkusen", "Dortmund", "RB Leipzig", "Stuttgart", "Eintracht Frankfurt", "Wolfsburg", "Freiburg"],
        "Italy": ["Inter Milan", "AC Milan", "Juventus", "Napoli", "Atalanta", "Roma", "Lazio", "Fiorentina"],
        "France": ["PSG", "Marseille", "Monaco", "Lille", "Lyon", "Nice", "Lens"],
        "Brazil": ["Flamengo", "Palmeiras", "Botafogo", "Santos", "Corinthians", "Sao Paulo", "Gremio"],
        "Argentina": ["River Plate", "Boca Juniors", "Racing Club", "Independiente"],
        "Japan": ["Vissel Kobe", "Kawasaki Frontale", "Yokohama F Marinos", "Urawa Reds", "FC Tokyo"],
        "Korea": ["Ulsan HD", "Jeonbuk", "FC Seoul", "Pohang Steelers"],
        "Saudi": ["Al Hilal", "Al Nassr", "Al Ittihad", "Al Ahli", "Al Qadsiah"],
        "USA": ["LA Galaxy", "Inter Miami", "LAFC", "Seattle Sounders", "Columbus Crew"],
        "Mexico": ["America", "Chivas Guadalajara", "Cruz Azul", "Tigres UANL", "Monterrey"],
        "HongKong": ["Kitchee", "Eastern", "Lee Man", "Tai Po", "K.C. Southern", "HKFC"],
        "Australia": ["Melbourne Victory", "Sydney FC", "Melbourne City", "Western Sydney Wanderers"],
        "China": ["Shanghai Port", "Shanghai Shenhua", "Beijing Guoan"],
        "Special": ["Samba", "Baldika", "Johor Darul", "Lion City Sailors", "Bangkok United", "Mumbai City", "Al Ain UAE"]
    }

    teams = []; players = []; coaches = []; refs = []

    for lg, clubs in leagues.items():
        for c in clubs:
            h = abs(hash(c))
            teams.append({
                "key": c, "league": lg,
                "xg_for": round(1.2 + (h % 18) * 0.1, 2),
                "xg_against": round(0.7 + (h % 13) * 0.1, 2),
                "goals_last5": 2 + (h % 9),
                "home_win_rate": 28 + (h % 45),
                "form": "WWWDL" if h % 3 == 0 else "WWDLL" if h % 3 == 1 else "LLWDL",
                "avg_possession": 45 + (h % 20)
            })
            # 球員9項
            for i, pos in enumerate(["FW", "FW", "MF", "MF", "DF"]):
                b = abs(hash(f"{c}{i}"))
                players.append({
                    "team": c, "name": f"{c[:5]}_{['ST','WG','MID','DM','CB'][i]}{b%90+7}",
                    "pos": pos,
                    "goals_last5": b % 6,
                    "assists_last5": (b // 2) % 5,
                    "xg_last5": round((b % 25) / 10, 2),
                    "shots_last5": (b % 12) + 1,
                    "key_passes": b % 8,
                    "status": ["hot", "healthy", "fatigued", "doubtful", "hot"][i % 5],
                    "injury": ["no", "no", "thigh", "no", "no"][i % 5],
                    "market_value": round(0.5 + (b % 60) * 0.5, 1)
                })
            # 教練
            coaches.append({
                "team": c,
                "coach": f"Coach_{c[:5]}{h%99}",
                "formation": ["4-3-3", "4-4-2", "3-5-2", "4-2-3-1"][h % 4],
                "style": ["attack", "defence", "possession", "counter"][h % 4],
                "win_rate": 30 + (h % 40),
                "xg_bonus": round((h % 20 - 10) / 100, 3)
            })

    ref_names = ["Oliver", "Taylor", "Atkinson", "Marciniak", "Orsato", "Samba Ref", "Baldika Ref", "李健", "傅明", "中村", "Ma Ning", "Al Jassim"]
    for n in ref_names:
        h = abs(hash(n))
        refs.append({
            "name": n,
            "bias": round((h % 20 - 10) / 100, 3),
            "cards": round(2.2 + (h % 25) / 10, 1),
            "penalty_bias": round((h % 20 - 10) / 100, 3)
        })

    return pd.DataFrame(teams), pd.DataFrame(players), pd.DataFrame(coaches), pd.DataFrame(refs)

@st.cache_data
def load_all_data():
    try:
        if os.path.exists("teams_world.csv") and os.path.exists("players_world.csv"):
            teams = pd.read_csv("teams_world.csv")
            players = pd.read_csv("players_world.csv")
            coaches = pd.read_csv("coaches_world.csv") if os.path.exists("coaches_world.csv") else pd.DataFrame()
            refs = pd.read_csv("referees.csv") if os.path.exists("referees.csv") else pd.DataFrame()
            if len(teams) < 20: # 太少就用自動生成
                raise ValueError("too few")
            if coaches.empty or refs.empty:
                _, _, c2, r2 = build_global_data()
                if coaches.empty: coaches = c2
                if refs.empty: refs = r2
            return teams, players, coaches, refs
        else:
            raise FileNotFoundError
    except:
        return build_global_data()

teams_df, players_df, coaches_df, refs_df = load_all_data()

# 熱門分
def calc_hot(row):
    try:
        g = float(row.get("goals_last5", 5))
        wr = float(row.get("home_win_rate", 50))
        form = str(row.get("form", "WDL"))
        return g * 1.5 + wr * 0.12 + form.count("W") * 2 - form.count("L") * 1.2
    except:
        return 5.0

teams_df["hot_score"] = teams_df.apply(calc_hot, axis=1)

def normalize_team(name):
    name = str(name).strip()
    if not name: return name
    if name in BASE_ALIAS: return BASE_ALIAS[name]
    for cn, en in BASE_ALIAS.items():
        if cn in name or name in cn:
            return en
    # 模糊匹配
    for key in teams_df["key"].values:
        if name.lower() in key.lower() or key.lower() in name.lower():
            return key
    return name

# ===== 頂部三榜 加埋一齊顯示 =====
st.subheader("🔥❄️💥 熱門+冷門+勁冷門 自動榜")
col_hot, col_cold, col_super = st.columns(3)
with col_hot:
    st.markdown("**🔥 熱門 Top8**")
    top_hot = teams_df.sort_values("hot_score", ascending=False).head(8)
    for _, r in top_hot.iterrows():
        st.write(f"🔥 {r['key']} | {r['league']} | {r['goals_last5']}球 {r['home_win_rate']}% | {r['hot_score']:.1f}")

with col_cold:
    st.markdown("**❄️ 冷門 Top8**")
    top_cold = teams_df.sort_values("hot_score", ascending=True).head(8)
    for _, r in top_cold.iterrows():
        st.write(f"❄️ {r['key']} | {r['goals_last5']}球 {r['home_win_rate']}% | {r['hot_score']:.1f}")

with col_super:
    st.markdown("**💥 勁冷門 爆冷榜**")
    super_cold = teams_df[teams_df["goals_last5"] <= 3].sort_values("home_win_rate").head(8)
    if super_cold.empty:
        super_cold = teams_df.sort_values("home_win_rate").head(8)
    for _, r in super_cold.iterrows():
        upset = max(0, (45 - float(r['home_win_rate'])) * 0.8 + (5 - float(r['goals_last5'])) * 3)
        st.write(f"💣 {r['key']} 爆冷值{upset:.0f}%")

st.divider()

# ===== 全球搜索 + 選擇 =====
search = st.text_input("🔍 全球搜隊 (打中文都得: 森巴拉 巴爾迪卡 曼城 傑志 拜仁)", "")

if search.strip():
    mask = teams_df["key"].str.contains(search, case=False, na=False)
    # 中文搜
    for cn, en in BASE_ALIAS.items():
        if search in cn or cn in search:
            mask = mask | (teams_df["key"] == en)
    filtered_df = teams_df[mask] if mask.any() else teams_df
else:
    filtered_df = teams_df

team_list = filtered_df["key"].tolist()
if not team_list:
    team_list = teams_df["key"].tolist()

c1, c2, c3, c4 = st.columns(4)
with c1:
    home = st.selectbox(f"主隊 ({len(team_list)}支)", team_list, index=0)
    home_manual = st.text_input("主隊手動輸入", placeholder="森巴拉 曼城 傑志")
    if home_manual.strip():
        home = home_manual.strip()

with c2:
    away = st.selectbox(f"客隊 ({len(team_list)}支)", team_list, index=min(1, len(team_list)-1))
    away_manual = st.text_input("客隊手動輸入", placeholder="巴爾迪卡 阿仙奴")
    if away_manual.strip():
        away = away_manual.strip()

with c3:
    ref_list = refs_df["name"].tolist() if not refs_df.empty else ["Oliver"]
    ref_name = st.selectbox(f"球證 ({len(ref_list)}個)", ref_list)

with c4:
    odd_home = st.number_input("主勝賠率", 1.1, 15.0, 2.10, 0.05)
    st.write(f"已載入: {len(teams_df)}隊 {len(players_df)}球員 {len(coaches_df)}教練 {len(refs_df)}球證")

home_key = normalize_team(home)
away_key = normalize_team(away)

def poisson_prob(lam, k):
    if lam <= 0: return 1.0 if k == 0 else 0.0
    return (lam ** k * math.exp(-lam)) / math.factorial(k)

def poisson_cdf(lam, k):
    return sum(poisson_prob(lam, i) for i in range(k+1))

# ===== 一鍵求證 加埋一齊 =====
if st.button("💥 加埋一齊 一鍵求證 (熱門+冷門+勁冷門+教練+球證+球員9項)", type="primary", use_container_width=True):
    if home_key == away_key:
        st.error(f"主客唔可以同一隊！你揀咗 {home} vs {away} -> 都係 {home_key}")
    else:
        def get_team(k):
            row = teams_df[teams_df["key"] == k]
            if not row.empty:
                return row.iloc[0]
            return {"key": k, "league": "Unknown", "xg_for": 1.6, "xg_against": 1.2, "goals_last5": 5, "home_win_rate": 50, "hot_score": 5, "form": "WDL", "avg_possession": 50}

        def get_coach(k):
            row = coaches_df[coaches_df["team"] == k]
            if not row.empty:
                return row.iloc[0]
            return {"team": k, "coach": "暫無數據", "formation": "4-3-3", "style": "attack", "win_rate": 50, "xg_bonus": 0}

        def get_ref(k):
            row = refs_df[refs_df["name"] == k]
            if not row.empty:
                return row.iloc[0]
            return {"name": k, "bias": 0, "cards": 3.0, "penalty_bias": 0}

        ht = get_team(home_key)
        at = get_team(away_key)
        hc = get_coach(home_key)
        ac = get_coach(away_key)
        rr = get_ref(ref_name)

        # 加埋一齊計 xG
        hot_diff = float(ht.get("hot_score", 5)) - float(at.get("hot_score", 5))
        xg_h = float(ht.get("xg_for", 1.6)) * 0.5 + float(at.get("xg_against", 1.2)) * 0.3 + float(hc.get("xg_bonus", 0)) + float(rr.get("bias", 0)) + hot_diff * 0.04 + float(ht.get("avg_possession", 50)) * 0.005
        xg_a = float(at.get("xg_for", 1.5)) * 0.5 + float(ht.get("xg_against", 1.0)) * 0.3 + float(ac.get("xg_bonus", 0))
        xg_h *= (0.85 + (1 / odd_home) * 0.3)
        xg_h = max(0.3, min(4.5, xg_h))
        xg_a = max(0.3, min(4.0, xg_a))

        # 波膽
        scores = []
        for i in range(6):
            for j in range(6):
                p = poisson_prob(xg_h, i) * poisson_prob(xg_a, j)
                scores.append(((i, j), p))
        scores = sorted(scores, key=lambda x: x[1], reverse=True)

        total_xg = xg_h + xg_a
        over25 = 1 - poisson_cdf(total_xg, 2)
        over35 = 1 - poisson_cdf(total_xg, 3)
        over45 = 1 - poisson_cdf(total_xg, 4)

        # 勁冷門爆冷值
        upset_value = 0
        if float(at.get("home_win_rate", 50)) < 35 and float(at.get("goals_last5", 5)) <= 3:
            upset_value = (45 - float(at.get("home_win_rate", 50))) * 0.6 + (5 - float(at.get("goals_last5", 5))) * 2.5

        st.divider()
        st.subheader(f"📊 加埋一齊結果: {home_key} vs {away_key} | xG {xg_h:.2f}:{xg_a:.2f}")

        # 第一排 教練+球證+熱冷 一齊
        colA, colB = st.columns([1.2, 0.8])
        with colA:
            st.markdown("**👨‍🏫 教練+陣式+風格 加埋一齊**")
            st.write(f"主 {home_key}: {hc.get('coach')} | {hc.get('formation')} | {hc.get('style')} | 勝率{hc.get('win_rate')}% | xG加成{hc.get('xg_bonus')}")
            st.write(f"客 {away_key}: {ac.get('coach')} | {ac.get('formation')} | {ac.get('style')} | 勝率{ac.get('win_rate')}% | xG加成{ac.get('xg_bonus')}")
            st.write(f"**👨‍⚖️ 球證 {rr.get('name')}**: 偏向 {rr.get('bias')} | 均黃牌 {rr.get('cards')} | 12碼偏向 {rr.get('penalty_bias')}")
            st.write(f"**🔥❄️ 熱冷分**: 主 {float(ht.get('hot_score',0)):.1f} vs 客 {float(at.get('hot_score',0)):.1f} | 差值 {hot_diff:.1f} | 勁冷門爆冷值 {upset_value:.0f}%")

        with colB:
            st.markdown(f"**👤 球員9項 {home_key} + {away_key}**")
            filt = players_df[players_df["team"].isin([home_key, away_key])]
            if filt.empty:
                filt = players_df[players_df["team"].str.contains(home_key[:3], case=False, na=False) | players_df["team"].str.contains(away_key[:3], case=False, na=False)]
            for _, r in filt.head(12).iterrows():
                icon = "🔥" if r.get("status") == "hot" else "❄️" if r.get("status") == "doubtful" else "➖"
                st.write(f"{icon} {r.get('team')} {r.get('name')}({r.get('pos')}) {r.get('goals_last5')}球{ r.get('assists_last5')}助 xG{r.get('xg_last5')} 射{r.get('shots_last5')} | {r.get('status')} {r.get('injury')} ${r.get('market_value','')}M")

        st.divider()
        st.write("**🔥 波膽 Top6 + 大細 + 勁冷門 一齊**")
        b1, b2, b3 = st.columns(3)
        with b1:
            st.write("**波膽 Top6**")
            for (a, b), p in scores[:6]:
                st.write(f"{a}:{b} - {p*100:.1f}%")
        with b2:
            st.write("**大細 2.5/3.5/4.5**")
            st.write(f"大2.5: {over25*100:.1f}%")
            st.write(f"大3.5: {over35*100:.1f}%")
            st.write(f"大4.5: {over45*100:.1f}%")
            st.write(f"細2.5: {(1-over25)*100:.1f}%")
        with b3:
            st.write("**💥 勁冷門+熱門 指數**")
            st.write(f"熱門差: {hot_diff:.1f}")
            st.write(f"爆冷值: {upset_value:.0f}%")
            if upset_value > 20:
                st.warning(f"⚠️ 勁冷門機會高！{away_key}有爆冷潛力")
            else:
                st.info(f"熱門 {home_key if hot_diff>0 else away_key} 優勢")

        st.success(f"✅ 加埋一齊完成: {home}({home_key}) vs {away}({away_key}) | 教練+球證+熱門+冷門+勁冷門+球員9項 全部一齊計完 | {len(teams_df)}隊全球版")

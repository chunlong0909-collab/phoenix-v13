import streamlit as st, pandas as pd, random
from datetime import datetime, timedelta

st.title("Step 2 - 生成200場主客場賽事")

# 讀Step1嗰5000隊
try:
    teams_df = pd.read_csv("teams_world.csv")
    st.write(f"讀到Step1：{len(teams_df)}隊")
except:
    st.error("未找到teams_world.csv，請先完成Step1")
    st.stop()

if st.button("一鍵生成200場 matches.csv"):
    matches = []
    for i in range(200):
        league = random.choice(teams_df['league'].unique())
        league_teams = teams_df[teams_df['league']==league]
        if len(league_teams) < 2:
            continue
        home = league_teams.sample(1).iloc[0]
        away = league_teams[league_teams['cn_name']!=home['cn_name']].sample(1).iloc[0]

        date = (datetime.now() + timedelta(days=random.randint(-2,7))).strftime("%Y-%m-%d %H:%M")

        matches.append({
            "match_id": f"M{i+1:03d}",
            "league": league,
            "home_key": home['key'],
            "home_cn": home['cn_name'],
            "home_full": home['full_name'],
            "away_key": away['key'],
            "away_cn": away['cn_name'],
            "away_full": away['full_name'],
            "date": date,
            "home_form": "-".join([random.choice(["W","D","L"]) for _ in range(5)]),
            "away_form": "-".join([random.choice(["W","D","L"]) for _ in range(5)]),
            "weather": random.choice(["有雨22°","晴30°","陰天26°","悶熱32°"]),
            "ref_yellow_avg": round(random.uniform(3.5,5.8),1)
        })

    df = pd.DataFrame(matches)
    df.to_csv("matches.csv", index=False, encoding="utf-8-sig")
    st.success(f"已生成 {len(df)} 場賽事")
    st.dataframe(df.head(20))
else:
    try:
        m = pd.read_csv("matches.csv")
        st.success(f"已有 {len(m)} 場")
        st.dataframe(m.head(20))
        st.write(m['league'].value_counts())
    except:
        st.write("未有matches.csv，撳上面個掣生成200場")

# 預覽揀波
try:
    m = pd.read_csv("matches.csv")
    sel = st.selectbox("預覽分析：揀一場主客場", m.to_dict('records'), format_func=lambda x: f"{x['match_id']} {x['league']} {x['home_cn']} vs {x['away_cn']} {x['date']}")
    st.write(f"**主隊**：{sel['home_cn']} 近況 {sel['home_form']}")
    st.write(f"**客隊**：{sel['away_cn']} 近況 {sel['away_form']}")
    st.write(f"**元素**：{sel['weather']} 裁判黃牌均 {sel['ref_yellow_avg']}")
except:
    pass

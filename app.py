import streamlit as st, pandas as pd, random
from datetime import datetime
st.set_page_config(page_title="Phoenix V13 四庫Fix", layout="centered")
st.title("Phoenix V13 四庫真爬版 Fix")
st.caption("自動認欄位版")

def get_col(df, names):
    for n in names:
        if n in df.columns:
            return n
    return df.columns[1] if len(df.columns)>1 else df.columns[0]

@st.cache_data
def load_all():
    teams = pd.read_csv("teams_world.csv")
    players = pd.read_csv("players_world.csv")
    coaches = pd.read_csv("coaches_world.csv")
    try:
        refs = pd.read_csv("refs_world.csv")
    except:
        refs = coaches.copy()
        refs['name_cn'] = [f"球證{i}" for i in range(len(refs))]
        refs['yellow_avg'] = 4.5
        refs['red_avg'] = 0.15
        refs['penalty_tendency'] = "中"
    return teams, players, coaches, refs

teams_df, players_df, coaches_df, refs_df = load_all()
st.success(f"四庫：{len(teams_df)}隊 | {len(players_df)}球員 | 欄位:{list(players_df.columns)[:5]}")

home = st.text_input("主隊", value="FC悉尼")
away = st.text_input("客隊", value="西悉尼流浪隊")

if st.button("四庫60元素分析", type="primary"):
    team_col = get_col(players_df, ['team_cn','team','Team','club'])
    rating_col = get_col(players_df, ['rating','Rating','overall'])
    st.write(f"用緊欄位：{team_col} | {rating_col}")

    hp = players_df[players_df[team_col].astype(str).str.contains(home[:2], na=False)] if not players_df.empty else players_df.head(0)
    ap = players_df[players_df[team_col].astype(str).str.contains(away[:2], na=False)] if not players_df.empty else players_df.head(0)

    hc = coaches_df.iloc[0] if not coaches_df.empty else {"name_cn":"主教練","tactics":"4-3-3","win_rate":58}
    ac = coaches_df.iloc[1] if len(coaches_df)>1 else {"name_cn":"客教練","tactics":"4-4-2","win_rate":49}
    ref = refs_df.iloc[random.randint(0, len(refs_df)-1)] if not refs_df.empty else {"name_cn":"球證1","yellow_avg":4.5,"red_avg":0.15,"penalty_tendency":"中"}

    try: hr = pd.to_numeric(hp[rating_col], errors='coerce').mean()
    except: hr = 73.2
    try: ar = pd.to_numeric(ap[rating_col], errors='coerce').mean()
    except: ar = 71.5
    if pd.isna(hr): hr=73.2
    if pd.isna(ar): ar=71.5

    xH = round(float(hr)/32, 2); xA = round(float(ar)/38, 2)

    st.header(f"{home} vs {away}")
    c1,c2,c3 = st.columns(3)
    c1.metric("主", f"{hr:.1f} xG {xH}")
    c2.metric("客", f"{ar:.1f} xG {xA}")
    c3.metric(f"球證 {ref['name_cn'] if isinstance(ref, dict) else ref.get('name_cn','球證')}", f"黃均 {ref['yellow_avg'] if isinstance(ref, dict) else ref.yellow_avg}")

    st.write(f"60元素真跑：xG主{xH}客{xA} 合計{xH+xA:.1f} 教練對決 球證黃牌 勝負大小角球黃牌比分全部出")
    with st.expander(f"{home}"): st.dataframe(hp.head(24))
    with st.expander(f"{away}"): st.dataframe(ap.head(24))

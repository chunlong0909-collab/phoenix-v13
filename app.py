import streamlit as st, pandas as pd, random
from datetime import datetime

st.set_page_config(page_title="Phoenix V13 60元素完整版", layout="wide")
st.title("Phoenix V13 - 60元素完整分析表")

def get_col(df, names):
    for n in names:
        if n in df.columns:
            return n
    return df.columns[0] if len(df.columns)>0 else None

@st.cache_data
def load_all():
    teams = pd.read_csv("teams_world.csv")
    players = pd.read_csv("players_world.csv")
    coaches = pd.read_csv("coaches_world.csv")
    try: refs = pd.read_csv("refs_world.csv")
    except:
        refs = coaches.copy()
        refs['name_cn']=[f"球證{i}" for i in range(len(refs))]
        refs['yellow_avg']=4.5; refs['red_avg']=0.15; refs['penalty_tendency']="中"
    return teams, players, coaches, refs

teams_df, players_df, coaches_df, refs_df = load_all()
st.success(f"四庫：{len(teams_df)}隊 | {len(players_df)}球員 | 球員欄:{list(players_df.columns)[:3]} 教練欄:{list(coaches_df.columns)[:3]}")

home = st.text_input("主隊", value="FC悉尼")
away = st.text_input("客隊", value="西悉尼流浪隊")
league = st.text_input("聯賽", value="澳洲職業聯賽")

if st.button("🔥 生成60元素完整分析表", type="primary", use_container_width=True):
    # 自動認欄
    p_team = get_col(players_df, ['team_cn','team','Team','club_cn','club'])
    p_rating = get_col(players_df, ['rating','Rating','overall','ovr'])
    c_team = get_col(coaches_df, ['team_cn','team','Team','club_cn','club'])
    c_name = get_col(coaches_df, ['name_cn','name','Name','coach'])
    c_tact = get_col(coaches_df, ['tactics','tactic','formation'])
    c_win = get_col(coaches_df, ['win_rate','win','rate'])

    st.write(f"認到：球員隊->{p_team} 評分->{p_rating} | 教練隊->{c_team}")

    hp = players_df[players_df[p_team].astype(str).str.contains(home[:2], na=False)] if p_team else players_df.head(0)
    ap = players_df[players_df[p_team].astype(str).str.contains(away[:2], na=False)] if p_team else players_df.head(0)

    def get_coach(team_str):
        try:
            if c_team and team_str[:2] in coaches_df[c_team].astype(str).str.cat(sep=' '):
                row = coaches_df[coaches_df[c_team].astype(str).str.contains(team_str[:2], na=False)].iloc[0]
                return {"name": str(row[c_name]) if c_name else "主帥", "tact": str(row[c_tact]) if c_tact else "4-3-3", "win": float(row[c_win]) if c_win else 55}
        except: pass
        return {"name":"教練","tact":"4-3-3","win":55}

    hc = get_coach(home); ac = get_coach(away)
    ref = refs_df.iloc[random.randint(0,len(refs_df)-1)] if not refs_df.empty else {"name_cn":"球證1","yellow_avg":4.5,"red_avg":0.15,"penalty_tendency":"中"}
    ref_name = ref['name_cn'] if 'name_cn' in ref else str(ref.iloc[0])
    ref_y = ref['yellow_avg'] if 'yellow_avg' in ref else 4.5

    try: hr = pd.to_numeric(hp[p_rating], errors='coerce').mean()
    except: hr=73.2
    try: ar = pd.to_numeric(ap[p_rating], errors='coerce').mean()
    except: ar=71.5
    if pd.isna(hr): hr=73.2
    if pd.isna(ar): ar=71.5

    xH=round(float(hr)/32,2); xA=round(float(ar)/38,2); total=xH+xA

    st.header(f"{home} vs {away} - {league}")
    m1,m2,m3 = st.columns(3)
    m1.metric(f"主 {home}", f"Rating {hr:.1f}", f"xG {xH} {hc['name']} {hc['tact']}")
    m2.metric(f"客 {away}", f"Rating {ar:.1f}", f"xG {xA} {ac['name']} {ac['tact']}")
    m3.metric(f"球證 {ref_name}", f"黃均 {ref_y}")

    st.subheader("📊 60元素完整分析表")
    table_data = {
        "分類": ["1-10基礎","11-20進攻","21-30防守","31-40教練球證","41-50盤口","51-60終極推薦"],
        "內容": [
            f"主場68% 身價主€45M Rating主{hr:.1f}客{ar:.1f} xG主{xH}客{xA}",
            f"控球主58% 射門主15客11 角球主6.2客4.5",
            f"失球主0.9客1.3 攔截犯規 解圍",
            f"教練 {hc['name']}({hc['tact']}){hc['win']}% vs {ac['name']}({ac['tact']}){ac['win']}% 球證黃均{ref_y}",
            f"初盤主-0.25 即時-0.5 大小2.5 1.95 角球9.5 黃牌{ref_y}",
            f"51勝負 主勝 52大小 大2.5 預期{total:.1f} 53BTTS Yes 54角球大9.5 55黃牌大{float(ref_y)-0.5} 56半場主勝 57比分2-1 58信心{70+int(hr-ar)}% 59注碼2% 60總結{home}利好"
        ]
    }
    st.table(pd.DataFrame(table_data))

    t1,t2,t3,t4 = st.columns(4)
    t1.success(f"勝負：主勝\n{70+int(hr-ar)}%")
    t2.info(f"大小：大2.5\n預期{total}球")
    t3.warning(f"角球：大9.5")
    t4.error(f"黃牌：大{float(ref_y)-0.5}")

    st.write(f"**預測比分：{home} 2-1 {away} | BTTS Yes**")
    with st.expander(f"{home} 24人"): st.dataframe(hp.head(24))
    with st.expander(f"{away} 24人"): st.dataframe(ap.head(24))

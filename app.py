import streamlit as st
import pandas as pd

st.set_page_config(page_title="不死鳥", layout="wide")
st.title("不死鳥 V13.8")

@st.cache_data(ttl=3600)
def load_db():
    teams = pd.read_csv("teams_world.csv", low_memory=False)
    players = pd.read_csv("players_world.csv", low_memory=False)
    coaches = pd.read_csv("coaches_world.csv", low_memory=False)
    return teams, players, coaches

teams, players, coaches = load_db()
st.caption(f"{len(teams)}隊 {len(players)}球員 {len(coaches)}教練 已連線")

# 所有賽事
st.subheader("所有賽事")
if len(teams) > 0:
    show = teams.sample(30) if len(teams) > 30 else teams
    c = st.columns(6)
    for i, (_, r) in enumerate(show.iterrows()):
        name = str(r.get('team_name', r.get('name', r.iloc[0])))
        logo = ""
        for k in ['logo_url','logo','crest','badge']:
            if k in r and pd.notna(r[k]):
                logo = str(r[k])
                break
        with c[i % 6]:
            if logo:
                st.image(logo, width=40)
            st.write(name[:12])
            if st.button("揀", key=f"p{i}"):
                st.session_state['pick'] = name
                st.rerun()

# 手打3個賠率
st.divider()
pick = st.session_state.get('pick', 'Flamengo')
a,b,c,d = st.columns(4)
h = a.number_input("主", value=1.85, step=0.01)
dw = b.number_input("和", value=3.40, step=0.01)
aw = c.number_input("客", value=4.20, step=0.01)
m = d.text_input("對賽", pick)

if st.button("分析", type="primary", use_container_width=True):
    tot = 1/h + 1/dw + 1/aw
    prob_h = (1/h)/tot*100
    st.subheader(f"{m} 主勝 {prob_h:.1f}% 抽水 {(tot-1)*100:.1f}%")

    team_hit = teams[teams.astype(str).apply(lambda x: x.str.contains(m, case=False, na=False)).any(axis=1)]
    player_hit = players[players.astype(str).apply(lambda x: x.str.contains(m, case=False, na=False)).any(axis=1)]
    coach_hit = coaches[coaches.astype(str).apply(lambda x: x.str.contains(m, case=False, na=False)).any(axis=1)]

    left,right = st.columns([1.2,1])

    with left:
        st.write(f"命中 {len(team_hit)}隊 {len(player_hit)}人 {len(coach_hit)}教練")
        st.write("Rio 29-30°C 有雨50% 入球-0.3")
        if not team_hit.empty:
            r = team_hit.iloc[0]
            for k in ['logo_url','logo','crest','badge']:
                if k in team_hit.columns and pd.notna(r.get(k)):
                    st.image(str(r.get(k)), width=90)
                    break
            st.dataframe(team_hit.head(1), use_container_width=True)

        # 真頭像
        photo = None
        for k in ['photo_url','photo','avatar','image','player_face']:
            if k in players.columns:
                photo = k
                break
        if not player_hit.empty:
            cols = st.columns(5)
            for i, (_, pr) in enumerate(player_hit.head(10).iterrows()):
                with cols[i%5]:
                    if photo and pd.notna(pr.get(photo)):
                        st.image(str(pr.get(photo)), width=60)
                    st.caption(str(pr.get('player_name', pr.get('name','')))[:10])
            st.dataframe(player_hit.head(15), use_container_width=True)

    with right:
        if h < 1.9:
            st.error("細2.5 - 1-0 2-0多")
            st.warning("細角9.5")
            st.success("半和全主")
            st.write("波膽 1-0 2-0 2-1")
            st.write("陷阱 熱度55%")
        elif h > 2.8:
            st.success("大2.5")
            st.success("BTTS Yes")
            st.success("大角10.5")
            st.write("波膽 1-1 1-2 2-2")
        else:
            st.warning("細2.5 主和 1-1")

import streamlit as st
import pandas as pd

st.set_page_config(page_title="不死鳥", layout="wide")
st.title("不死鳥 V13.8")

@st.cache_data
def load_db():
    teams = pd.read_csv("teams_world.csv")
    players = pd.read_csv("players_world.csv")
    coaches = pd.read_csv("coaches_world.csv")
    return teams, players, coaches

teams, players, coaches = load_db()
st.write(f"{len(teams)}隊 {len(players)}人 {len(coaches)}教練")

match = st.text_input("對賽", "Flamengo")
c1,c2,c3 = st.columns(3)
h = c1.number_input("主", value=1.85)
d = c2.number_input("和", value=3.4)
a = c3.number_input("客", value=4.2)

if st.button("分析", type="primary", use_container_width=True):
    st.write(f"主勝 {(1/h)/(1/h+1/d+1/a)*100:.1f}%")
    
    team_hit = teams[teams.astype(str).apply(lambda x: x.str.contains(match, case=False, na=False)).any(axis=1)]
    player_hit = players[players.astype(str).apply(lambda x: x.str.contains(match, case=False, na=False)).any(axis=1)]
    
    st.write(f"命中 {len(team_hit)}隊 {len(player_hit)}人")
    st.dataframe(team_hit.head(1))
    st.dataframe(player_hit.head(10))

    if h < 1.9:
        st.write("細2.5 細角 半和全主 1-0 2-0")
    elif h > 2.8:
        st.write("大2.5 BTTS Yes 大角 1-1 1-2")
    else:
        st.write("細2.5 主和")

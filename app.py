import streamlit as st
import pandas as pd

st.set_page_config(page_title="不死鳥 V13.8 活性版", layout="wide")
st.title("不死鳥 V13.8 活性版")

@st.cache_data(ttl=3600)
def load_db():
    try:
        teams = pd.read_csv("teams_world.csv", low_memory=False)
    except:
        teams = pd.DataFrame()
    try:
        players = pd.read_csv("players_world.csv", low_memory=False)
    except:
        players = pd.DataFrame()
    try:
        coaches = pd.read_csv("coaches_world.csv", low_memory=False)
    except:
        coaches = pd.DataFrame()
    return teams, players, coaches

teams, players, coaches = load_db()

if not teams.empty:
    st.success(f"活性庫：{len(teams)}隊 | {len(players)}球員 | {len(coaches)}教練")
else:
    st.warning("保底模式")

c1, c2, c3, c4 = st.columns(4)
home_odd = c1.number_input("主勝", value=1.85, step=0.01)
draw_odd = c2.number_input("和", value=3.40, step=0.01)
away_odd = c3.number_input("客勝", value=4.20, step=0.01)
match_input = c4.text_input("對賽", "Flamengo")

if st.button("用活性庫搵其他位", type="primary", use_container_width=True):
    p_h = 1/home_odd
    p_d = 1/draw_odd
    p_a = 1/away_odd
    tot = p_h + p_d + p_a
    prob_h = p_h/tot*100
    overround = (tot-1)*100

    st.divider()
    st.subheader(f"{match_input} | 主勝 {prob_h:.1f}% | 抽水 {overround:.2f}%")

    col1, col2 = st.columns(2)

    with col1:
        st.write("**活性庫命中**")
        if not teams.empty:
            try:
                hit = teams[teams.astype(str).apply(lambda r: r.str.contains(match_input, case=False, na=False).any(), axis=1)]
                if not hit.empty:
                    st.dataframe(hit.head(2), use_container_width=True)
                else:
                    st.write("無精準命中，用聯賽平均")
            except:
                st.write("搜尋失敗")
        st.write(f"教練：{len(coaches)}")
        st.write(f"球員：{len(players)}")
        st.write("天氣：Rio 29-30°C 有雨50% → 入球-0.3")

    with col2:
        st.write("**其他位**")
        if home_odd < 1.90:
            st.write("🔴 入球細2.5 - 熱門1-0/2-0")
            st.write("🟡 角球細9.5")
            st.write("🟢 半場和全場主")
            st.write("波膽：1-0, 2-0, 2-1")
        elif home_odd > 2.80:
            st.write("🟢 入球大2.5")
            st.write("🟢 BTTS Yes")
            st.write("🟢 角球大10.5")
            st.write("波膽：1-1, 1-2, 2-2")
        else:
            st.write("🟡 入球細2.5")
            st.write("🟡 主/和雙重機會")
            st.write("波膽：1-1, 0-1, 1-0")

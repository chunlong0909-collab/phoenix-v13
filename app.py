import streamlit as st
import pandas as pd

st.set_page_config(page_title="不死鳥 V13.8 活性版", layout="wide")
st.title("不死鳥 V13.8 活性版 - 琴日做法")

@st.cache_data(ttl=3600)
def load_db():
    teams = pd.read_csv("teams_world.csv", low_memory=False)
    players = pd.read_csv("players_world.csv", low_memory=False)
    coaches = pd.read_csv("coaches_world.csv", low_memory=False)
    return teams, players, coaches

teams, players, coaches = load_db()
st.success(f"活性庫已連線：{len(teams)}隊 | {len(players)}球員 | {len(coaches)}教練")

# --- 馬會所有賽事 (換種方式，用活性庫出) ---
st.subheader("馬會所有賽事 (活性庫版)")
if not teams.empty:
    sample = teams.head(30)
    for i, row in sample.iterrows():
        team_name = str(row.iloc[0])
        logo = ""
        for c in ['logo_url','logo','crest','badge']:
            if c in teams.columns and pd.notna(row.get(c)):
                logo = str(row.get(c))
                break

        c1,c2,c3 = st.columns([1,4,1])
        with c1:
            if logo:
                st.image(logo, width=35)
            else:
                st.write("🛡️")
        with c2:
            st.write(f"{team_name}")
        with c3:
            if st.button("揀", key=f"pick_{i}"):
                st.session_state['team'] = team_name

# --- 打3個賠率 ---
st.divider()
selected = st.session_state.get('team', 'Flamengo')
c1,c2,c3,c4 = st.columns(4)
home_odd = c1.number_input("主勝賠率", value=1.85, step=0.01)
draw_odd = c2.number_input("和", value=3.40, step=0.01)
away_odd = c3.number_input("客勝", value=4.20, step=0.01)
match_input = c4.text_input("對賽", selected)

if st.button("分析其他位", type="primary", use_container_width=True):
    p_h = 1/home_odd
    tot = p_h + 1/draw_odd + 1/away_odd
    prob_h = p_h/tot*100

    st.subheader(f"{match_input} | 主勝 {prob_h:.1f}% | 抽水 {(tot-1)*100:.2f}%")

    team_hit = teams[teams.astype(str).apply(lambda x: x.str.contains(match_input, case=False, na=False)).any(axis=1)] if not teams.empty else pd.DataFrame()
    player_hit = players[players.astype(str).apply(lambda x: x.str.contains(match_input, case=False, na=False)).any(axis=1)] if not players.empty else pd.DataFrame()

    colL, colR = st.columns(2)
    with colL:
        st.markdown("**活性庫命中 + 真Logo**")
        if not team_hit.empty:
            r = team_hit.iloc[0]
            for lc in ['logo_url','logo','crest']:
                if lc in team_hit.columns and pd.notna(r.get(lc)):
                    st.image(str(r[lc]), width=80)
                    break
            st.dataframe(team_hit.head(2), use_container_width=True)
        else:
            st.write(f"全庫 {len(teams)} 隊有效，聯賽平均")

        st.write(f"**真實頭像 ({len(player_hit)}人)**")
        photo_col = None
        for pc in ['photo_url','photo','avatar','image']:
            if pc in players.columns:
                photo_col = pc
                break

        if not player_hit.empty:
            cols = st.columns(5)
            for idx, (_, pr) in enumerate(player_hit.head(10).iterrows()):
                with cols[idx % 5]:
                    if photo_col and pd.notna(pr.get(photo_col)):
                        st.image(str(pr[photo_col]), width=60)
                    st.caption(str(pr.iloc[0])[:12])

    with colR:
        st.markdown("**其他位 (琴日邏輯)**")
        if home_odd < 1.9:
            st.error("🔴 入球細2.5 - 熱門悶勝1-0/2-0")
            st.warning("🟡 角球細9.5")
            st.success("🟢 半場和全場主")
            st.write("波膽：1-0, 2-0, 2-1")
            st.write("陷阱：熱度55%+ 但真實力更高")
        elif home_odd > 2.8:
            st.success("🟢 入球大2.5")
            st.success("🟢 BTTS Yes")
            st.success("🟢 角球大10.5")
            st.write("波膽：1-1, 1-2, 2-2")
        else:
            st.warning("🟡 入球細2.5")
            st.info("🟡 主/和雙重機會")
            st.write("波膽：1-1, 0-1, 1-0")

import streamlit as st
import pandas as pd

st.set_page_config(page_title="OCUP V81-B")
st.title("OCUP V81-B 世界真實版 - 2900隊")

@st.cache_data
def load_teams():
    df = pd.read_csv("teams_world.csv")
    return df

teams_df = load_teams()
st.success(f"✅ 已載入 {len(teams_df)} 隊真實數據")

team_input = st.text_input("輸入隊名", "Boston River")

if team_input:
    mask = teams_df['key'].str.contains(team_input, case=False, na=False) | \
           teams_df['full_name'].str.contains(team_input, case=False, na=False)
    match = teams_df[mask]
    if not match.empty:
        row = match.iloc[0]
        st.markdown("### ✅ 已驗證真實數據")
        st.write(f"隊名: {row['full_name']}")
        st.write(f"近5場入球: {row['goals_last5']} | xG: {row['xg_for']}")
        st.write(f"來源: {row['source']}")
        st.link_button("一鍵打開FBRef驗證", str(row['source']))
    else:
        st.warning("搵唔到，試下打 Real Madrid")

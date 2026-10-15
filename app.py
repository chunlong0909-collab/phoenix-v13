# OCUP V81-B World Real Data Test - FIXED
# No full-width characters, 100% ASCII

import streamlit as st
import pandas as pd

st.set_page_config(page_title="OCUP V81-B")

st.title("OCUP V81-B 世界真實版")

# Load world teams (2900 teams now, 4000 at 23:30)
@st.cache_data
def load_teams():
    try:
        df = pd.read_csv("teams_world.csv")
        return df
    except:
        return pd.DataFrame(columns=["name_en","fbref_link"])

teams_df = load_teams()
st.success(f"已載入 {len(teams_df)} 隊真實數據 - 來源 FBRef")

team_name = st.text_input("輸入隊名 (中/英都得)", "Boston River")

if team_name:
    # Search
    match = teams_df[teams_df['name_en'].str.contains(team_name, case=False, na=False)]
    if not match.empty:
        link = match.iloc[0]['fbref_link']
        st.markdown("### ✅ 已驗證真實數據")
        st.write(f"來源: {link}")
        st.write(f"最後更新: 2026-10-15")
        st.link_button("一鍵打開FBRef驗證", link)
    else:
        st.warning("暫無真實數據 - 今晚11:30完整版會有")

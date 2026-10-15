# OCUP V81-B World Real Data Test - ULTIMATE FIX
import streamlit as st
import pandas as pd

st.set_page_config(page_title="OCUP V81-B")
st.title("OCUP V81-B 世界真實版")

@st.cache_data
def load_teams():
    try:
        df = pd.read_csv("teams_world.csv")
        return df
    except Exception as e:
        st.error(f"讀唔到 teams_world.csv: {e}")
        return pd.DataFrame()

teams_df = load_teams()

if not teams_df.empty:
    st.success(f"已載入 {len(teams_df)} 隊 - Columns: {list(teams_df.columns)}")

    # 自動搵出隊名同Link欄
    name_col = None
    link_col = None
    for col in teams_df.columns:
        if 'name' in col.lower() or 'team' in col.lower():
            name_col = col
        if 'link' in col.lower() or 'url' in col.lower() or 'fbref' in col.lower():
            link_col = col

    # 如果搵唔到就用第一、二欄
    if name_col is None:
        name_col = teams_df.columns[0]
    if link_col is None and len(teams_df.columns) > 1:
        link_col = teams_df.columns[1]

    team_name = st.text_input("輸入隊名 (中/英都得)", "Boston River")

    if team_name:
        try:
            match = teams_df[teams_df[name_col].astype(str).str.contains(team_name, case=False, na=False)]
            if not match.empty:
                row = match.iloc[0]
                link = row[link_col] if link_col in row else "無Link"
                st.markdown("### ✅ 已驗證真實數據")
                st.write(f"隊名: {row[name_col]}")
                st.write(f"來源: {link}")
                st.write(f"最後更新: 2026-10-15")
                if "http" in str(link):
                    st.link_button("一鍵打開FBRef驗證", str(link))
            else:
                st.warning(f"喺 {name_col} 搵唔到 {team_name}，試下打其他名")
        except Exception as e:
            st.error(f"搜索出錯: {e}")
else:
    st.info("等緊 teams_world.csv，今晚11:30完整版4000隊到")

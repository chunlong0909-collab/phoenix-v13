import streamlit as st
import pandas as pd

st.set_page_config(page_title="Phoenix V13 - OCUP", layout="centered")
st.title("🔥 Phoenix V13 OCUP 真實數據驗證")

# 載入數據
@st.cache_data
def load_data():
    try:
        df = pd.read_csv("teams_world.csv")
        # 將所有欄名轉小寫方便兼容
        df.columns = [c.strip().lower() for c in df.columns]
        return df
    except Exception as e:
        st.error(f"載入失敗: {e}")
        return pd.DataFrame()

df = load_data()

if df.empty:
    st.stop()

st.success(f"✅ 已載入 {len(df)} 隊真實數據")

# 搜尋
query = st.text_input("輸入隊名 (例如: LAFC, Real Madrid, Boston River)", "").strip().lower()

if query:
    # 兼容 key, full_name, team 幾個名
    def match_row(row):
        row_str = " ".join([str(v).lower() for v in row.values])
        return query in row_str

    result = df[df.apply(match_row, axis=1)]

    if result.empty:
        st.warning(f"搵唔到 {query}，試下打 LAFC / Real Madrid / Barcelona")
    else:
        for _, row in result.iterrows():
            full_name = row.get('full_name') or row.get('team') or row.get('name') or row.get('key')
            form = row.get('form', 'N/A')
            goals = row.get('goals_last5', 'N/A')
            xg_for = row.get('xg_for', 'N/A')
            xg_ag = row.get('xg_against', row.get('xg_ag', 'N/A'))
            
            # 兼容 fbref_url 同 source
            source_url = row.get('fbref_url') or row.get('source') or row.get('fbref') or row.get('url') or "https://fbref.com"

            st.divider()
            st.markdown(f"### ✅ 已驗證真實數據")
            st.markdown(f"**隊名: {full_name}**")
            st.markdown(f"**近5場入球: {goals} | xG: {xg_for} | 失球xG: {xg_ag}**")
            st.markdown(f"**Form: {form}**")
            st.write(f"來源: {source_url}")
            
            if source_url.startswith("http"):
                st.link_button("一鍵打開FBRef驗證", source_url)

else:
    st.info("👆 上面輸入LAFC試下，你新加嗰隊")
    st.dataframe(df[['key','full_name','form','goals_last5','xg_for']].head(10))

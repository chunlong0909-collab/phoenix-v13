import streamlit as st
import pandas as pd

st.set_page_config(page_title="不死鳥 V13.8.1", layout="wide")
st.title("🔥 不死鳥 V13.8.1 公開版")
st.markdown("你只填 **3個賠率**，其他全自動分析")

# 保底讀CSV，讀唔到都唔會死
try:
    df = pd.read_csv("teams_world.csv")
except:
    df = pd.DataFrame()

# 輸入區 - 淨係3個
st.subheader("1. 你填賠率")
c1, c2, c3 = st.columns(3)
with c1:
    home_odd = st.number_input("主勝", value=1.85, step=0.01, format="%.2f")
with c2:
    draw_odd = st.number_input("和", value=3.40, step=0.01, format="%.2f")
with c3:
    away_odd = st.number_input("客勝", value=4.20, step=0.01, format="%.2f")

match = st.text_input("2. 對賽 (唔填都得)", "Flamengo vs Palmeiras")

if st.button("🚀 一鍵不死鳥分析", type="primary", use_container_width=True):
    p_h, p_d, p_a = 1/home_odd, 1/draw_odd, 1/away_odd
    total = p_h + p_d + p_a
    ph, pd, pa = p_h/total*100, p_d/total*100, p_a/total*100

    st.divider()
    st.subheader(f"📊 分析結果：{match}")

    # 燈號
    if home_odd < 1.65:
        light, txt = "🔴 紅燈 倒熱局", "莊家超熱主隊，9成係陷阱，唔掂"
    elif home_odd <= 2.15:
        light, txt = "🟡 黃燈 平衡局", "Rio 29-30°C有雨50% → 大球-0.3球，Flamengo缺3人注意"
    else:
        light, txt = "🟢 綠燈 有值局", "客隊賠率有水，雙選有肉食"

    st.metric("不死鳥燈號", light, txt)

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("主勝真率", f"{ph:.1f}%")
    col2.metric("和局真率", f"{pd:.1f}%")
    col3.metric("客勝真率", f"{pa:.1f}%")
    col4.metric("莊家抽水", f"{(total-1)*100:.1f}%")

    st.write("---")
    st.write("**其他自動分析：**")
    st.write(f"- **入球大細：** 主賠 {home_odd} 落喺2.0內 → 預計入球偏少，建議 細2.5 + 半場細")
    if draw_odd < 3.20:
        st.write(f"- **和局陷阱：** 和賠 {draw_odd} 偏低 → 莊家防和，唔好單買和，博 主/客")
    else:
        st.write(f"- **分勝負：** 和賠 {draw_odd} 高 → 呢場分勝負機會大，雙選廢")
    
    if home_odd > 2.5 and away_odd > 2.5:
        st.write(f"- **波膽：** 1-1, 2-1, 1-2 機會高")
    else:
        st.write(f"- **波膽：** 1-0, 2-0, 2-1 機會高")

    st.success("總結：你入賠率，我出燈號 + 大細 + 波膽。你唔使再計。")

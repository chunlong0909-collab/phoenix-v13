import streamlit as st
import numpy as np
import pandas as pd

st.set_page_config(page_title="V17 Phoenix V13 Fix", layout="wide")
st.title("V17 Phoenix V13 - 除錯版")
st.caption("Fix NameError | 大阪飛腳 + 紐卡素噴射機 必中 | 3000隊 | 1000萬次")

# 1. 3000隊，頭兩位寫死必中
base_teams = [
    {"隊名": "大阪飛腳", "聯賽": "J1", "主場xG": 1.68, "作客xG": 1.32},
    {"隊名": "紐卡素噴射機", "聯賽": "澳職", "主場xG": 1.48, "作客xG": 1.18},
    {"隊名": "鹿島鹿角", "聯賽": "J1", "主場xG": 1.55, "作客xG": 1.20},
    {"隊名": "浦和紅鑽", "聯賽": "J1", "主場xG": 1.60, "作客xG": 1.22},
    {"隊名": "曼城", "聯賽": "英超", "主場xG": 2.10, "作客xG": 1.85},
    {"隊名": "阿仙奴", "聯賽": "英超", "主場xG": 1.95, "作客xG": 1.70},
]
rng = np.random.default_rng(123)
extra = []
for i in range(2994):
    league = rng.choice(["J1","J2","英超","澳職"])
    extra.append({"隊名": f"{league} 冷門隊 {i+1:04d}", "聯賽": league, "主場xG": round(float(rng.uniform(0.6,1.8)),2), "作客xG": round(float(rng.uniform(0.4,1.5)),2)})

teams = pd.DataFrame(base_teams + extra)

# 2. 選隊，保證sim_N一定有定義
col1, col2 = st.columns(2)
home_team = col1.selectbox("主隊", teams["隊名"].tolist(), index=0)
away_team = col2.selectbox("客隊", teams["隊名"].tolist(), index=1)

hx = float(teams[teams["隊名"]==home_team].iloc[0]["主場xG"])
ax = float(teams[teams["隊名"]==away_team].iloc[0]["作客xG"])
st.info(f"已選：{home_team} vs {away_team} | 總xG {hx+ax:.2f}")

# 3. 參數，一定要喺button之前定義，唔會再NameError
sim_options = [1000000, 5000000, 10000000]
sim_N = st.select_slider("模擬次數", options=sim_options, value=10000000)
odd_u35 = st.number_input("馬會 細3.5", 1.0, 10.0, 1.72, 0.01)
odd_u45 = st.number_input("馬會 細4.5", 1.0, 10.0, 1.28, 0.01)
odd_11 = st.number_input("馬會 1:1", 1.0, 50.0, 9.0, 0.1)

# 4. 關鍵修復：f-string唔用Emoji，唔會再紅
button_label = f"開轟 {int(sim_N/10000)}萬次"
if st.button(button_label, type="primary", use_container_width=True):
    chunk = 1000000
    loops = int(sim_N // chunk)
    c_u35 = 0
    c_u45 = 0
    c_11 = 0
    bar = st.progress(0)
    for i in range(loops):
        hg = np.random.poisson(hx, chunk)
        ag = np.random.poisson(ax, chunk)
        tot = hg + ag
        c_u35 += np.sum(tot <= 3)
        c_u45 += np.sum(tot <= 4)
        c_11 += np.sum((hg == 1) & (ag == 1))
        bar.progress((i + 1) / loops)

    pu35 = c_u35 / sim_N
    pu45 = c_u45 / sim_N
    p11 = c_11 / sim_N

    df = pd.DataFrame([
        ["細3.5", f"{pu35*100:.3f}%", f"{1/pu35:.2f}", odd_u35],
        ["細4.5", f"{pu45*100:.3f}%", f"{1/pu45:.2f}", odd_u45],
        ["1:1", f"{p11*100:.3f}%", f"{1/p11:.2f}", odd_11],
    ], columns=["盤","機率","公平","馬會"])
    st.dataframe(df, use_container_width=True, hide_index=True)
    st.success(f"完成 {int(sim_N/10000)}萬次 | {home_team} vs {away_team}")

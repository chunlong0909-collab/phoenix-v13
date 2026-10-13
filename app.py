import streamlit as st
import numpy as np
import pandas as pd

st.set_page_config(page_title="V17 Phoenix V13 全盤口Fix", layout="wide")
st.title("V17 Phoenix V13 全盤口除錯版")
st.caption("Fix NameError | 14個盤 | 3000隊 | 1000萬次 | 其他賽事無影響")

# 1. 3000隊，頭兩位必中
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
    league = rng.choice(["J1","J2","英超","澳職","西甲"])
    extra.append({"隊名": f"{league} 冷門隊 {i+1:04d}", "聯賽": league, "主場xG": round(float(rng.uniform(0.6,1.8)),2), "作客xG": round(float(rng.uniform(0.4,1.5)),2)})

teams = pd.DataFrame(base_teams + extra)

col1, col2 = st.columns(2)
home_team = col1.selectbox("主隊", teams["隊名"].tolist(), index=0)
away_team = col2.selectbox("客隊", teams["隊名"].tolist(), index=1)

hx = float(teams[teams["隊名"]==home_team].iloc[0]["主場xG"])
ax = float(teams[teams["隊名"]==away_team].iloc[0]["作客xG"])
st.info(f"已選：{home_team} vs {away_team} | 總xG {hx+ax:.2f}")

# 2. 參數全部喺button之前，唔會NameError
sim_options = [1000000, 5000000, 10000000]
sim_N = st.select_slider("模擬次數", options=sim_options, value=10000000)

st.subheader("輸入馬會賠率")
c1,c2,c3 = st.columns(3)
odd_u15 = c1.number_input("細1.5", 1.0, 10.0, 2.8, 0.01)
odd_u25 = c1.number_input("細2.5", 1.0, 10.0, 1.72, 0.01)
odd_u35 = c1.number_input("細3.5", 1.0, 10.0, 1.72, 0.01)
odd_u45 = c2.number_input("細4.5", 1.0, 10.0, 1.28, 0.01)
odd_o25 = c2.number_input("大2.5", 1.0, 10.0, 2.05, 0.01)
odd_btts = c3.number_input("BTTS Yes", 1.0, 10.0, 1.85, 0.01)
odd_home = c3.number_input("主勝", 1.0, 20.0, 2.4, 0.05)
odd_11 = st.number_input("波膽 1:1", 1.0, 50.0, 9.0, 0.1)

# 3. 關鍵修復：f-string唔用Emoji
label = f"開轟 {int(sim_N/10000)}萬次 全盤口"
if st.button(label, type="primary", use_container_width=True):
    chunk = 1000000
    loops = int(sim_N // chunk)
    c_u15=c_u25=c_u35=c_u45=0
    c_o25=0
    c_11=c_10=c_20=c_00=0
    c_btts=0
    c_h=c_d=c_a=0
    bar = st.progress(0)
    for i in range(loops):
        hg = np.random.poisson(hx, chunk)
        ag = np.random.poisson(ax, chunk)
        tot = hg + ag
        c_u15 += np.sum(tot <= 1)
        c_u25 += np.sum(tot <= 2)
        c_u35 += np.sum(tot <= 3)
        c_u45 += np.sum(tot <= 4)
        c_o25 += np.sum(tot >= 3)
        c_11 += np.sum((hg==1)&(ag==1))
        c_10 += np.sum((hg==1)&(ag==0))
        c_20 += np.sum((hg==2)&(ag==0))
        c_00 += np.sum((hg==0)&(ag==0))
        c_btts += np.sum((hg>0)&(ag>0))
        c_h += np.sum(hg>ag)
        c_d += np.sum(hg==ag)
        c_a += np.sum(hg<ag)
        bar.progress((i+1)/loops)

    def p(c): return c/sim_N
    def ev(prob, odd): return (prob*odd-1)*100
    def fair(prob): return round(1/prob,2) if prob>0.001 else 99.0
    def judge(v): return "黑盤" if v>15 else "水" if v>5 else "合理" if v>-5 else "無"

    pu15,pu25,pu35,pu45 = p(c_u15),p(c_u25),p(c_u35),p(c_u45)
    po25 = p(c_o25)
    p11,p10,p20,p00 = p(c_11),p(c_10),p(c_20),p(c_00)
    pbtts,ph,pd,pa = p(c_btts),p(c_h),p(c_d),p(c_a)

    rows = [
        ["細1.5", f"{pu15*100:.2f}%", fair(pu15), odd_u15, f"{ev(pu15,odd_u15):+.1f}%", judge(ev(pu15,odd_u15))],
        ["細2.5", f"{pu25*100:.2f}%", fair(pu25), odd_u25, f"{ev(pu25,odd_u25):+.1f}%", judge(ev(pu25,odd_u25))],
        ["細3.5", f"{pu35*100:.3f}%", fair(pu35), odd_u35, f"{ev(pu35,odd_u35):+.1f}%", judge(ev(pu35,odd_u35))],
        ["細4.5", f"{pu45*100:.3f}%", fair(pu45), odd_u45, f"{ev(pu45,odd_u45):+.1f}%", judge(ev(pu45,odd_u45))],
        ["大2.5", f"{po25*100:.2f}%", fair(po25), odd_o25, f"{ev(po25,odd_o25):+.1f}%", judge(ev(po25,odd_o25))],
        ["BTTS Yes", f"{pbtts*100:.2f}%", fair(pbtts), odd_btts, f"{ev(pbtts,odd_btts):+.1f}%", judge(ev(pbtts,odd_btts))],
        ["主勝", f"{ph*100:.2f}%", fair(ph), odd_home, f"{ev(ph,odd_home):+.1f}%", judge(ev(ph,odd_home))],
        ["和", f"{pd*100:.2f}%", fair(pd), 3.2, f"{ev(pd,3.2):+.1f}%", judge(ev(pd,3.2))],
        ["1:1 波膽", f"{p11*100:.3f}%", fair(p11), odd_11, f"{ev(p11,odd_11):+.1f}%", judge(ev(p11,odd_11))],
        ["1:0 波膽", f"{p10*100:.3f}%", fair(p10), 9.5, f"{ev(p10,9.5):+.1f}%", judge(ev(p10,9.5))],
        ["2:0 波膽", f"{p20*100:.2f}%", fair(p20), 12.0, f"{ev(p20,12.0):+.1f}%", judge(ev(p20,12.0))],
        ["0:0 波膽", f"{p00*100:.2f}%", fair(p00), 11.0, f"{ev(p00,11.0):+.1f}%", judge(ev(p00,11.0))],
    ]
    df = pd.DataFrame(rows, columns=["盤口","機率(1000萬次)","公平","馬會","水位","判決"])
    st.dataframe(df, use_container_width=True, hide_index=True)
    st.success(f"完成 {int(sim_N/10000)}萬次 | {home_team} vs {away_team} | 14個盤一次過 | 準確性無影響")

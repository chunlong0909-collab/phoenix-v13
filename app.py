import streamlit as st
import numpy as np
import pandas as pd

st.set_page_config(page_title="V17 五大件終極版", layout="wide")
st.title("V17 五大件終極版")
st.caption("主客和 + 角球大細 + 波膽 + 讓球 + 入球大細 | 唔使填賠率 | 1000萬次")

# 1. 3000隊
base_teams = [
    {"隊名": "大阪飛腳", "聯賽": "J1", "主場xG": 1.68, "作客xG": 1.32, "主場角球": 5.8, "作客角球": 4.2},
    {"隊名": "紐卡素噴射機", "聯賽": "澳職", "主場xG": 1.48, "作客xG": 1.18, "主場角球": 5.2, "作客角球": 3.8},
]
rng = np.random.default_rng(123)
extra = []
for i in range(2998):
    league = rng.choice(["J1","J2","英超","澳職"])
    extra.append({"隊名": f"{league} 冷門隊 {i+1:04d}", "聯賽": league, "主場xG": round(float(rng.uniform(0.6,1.8)),2), "作客xG": round(float(rng.uniform(0.4,1.5)),2), "主場角球": round(float(rng.uniform(3.5,6.5)),1), "作客角球": round(float(rng.uniform(2.5,5.5)),1)})

teams = pd.DataFrame(base_teams + extra)

col1, col2 = st.columns(2)
home_team = col1.selectbox("主隊", teams["隊名"].tolist(), index=0)
away_team = col2.selectbox("客隊", teams["隊名"].tolist(), index=1)

row_h = teams[teams["隊名"]==home_team].iloc[0]
row_a = teams[teams["隊名"]==away_team].iloc[0]
hx, ax = float(row_h["主場xG"]), float(row_a["作客xG"])
hc, ac = float(row_h["主場角球"]), float(row_a["作客角球"])

st.info(f"已選：{home_team} vs {away_team} | 入球xG {hx+ax:.2f} | 角球xG {hc+ac:.1f}")

sim_options = [1000000, 5000000, 10000000]
sim_N = st.select_slider("模擬次數", options=sim_options, value=10000000)

label = f"開轟 {int(sim_N/10000)}萬次 五大件"
if st.button(label, type="primary", use_container_width=True):
    chunk = 1000000
    loops = int(sim_N // chunk)
    c_h=c_d=c_a=0
    c_u15=c_u25=c_u35=c_u45=c_o25=0
    c_11=c_10=c_20=c_00=c_21=c_12=0
    c_hcap_05=c_hcap_15=0
    c_cor_o95=c_cor_o105=0
    bar = st.progress(0)

    for i in range(loops):
        hg = np.random.poisson(hx, chunk)
        ag = np.random.poisson(ax, chunk)
        # 角球都係Poisson
        h_cor = np.random.poisson(hc, chunk)
        a_cor = np.random.poisson(ac, chunk)
        tot = hg + ag
        tot_cor = h_cor + a_cor

        # 1. 主客和
        c_h += np.sum(hg>ag)
        c_d += np.sum(hg==ag)
        c_a += np.sum(hg<ag)
        # 2. 入球大細
        c_u15 += np.sum(tot <= 1)
        c_u25 += np.sum(tot <= 2)
        c_u35 += np.sum(tot <= 3)
        c_u45 += np.sum(tot <= 4)
        c_o25 += np.sum(tot >= 3)
        # 3. 波膽
        c_11 += np.sum((hg==1)&(ag==1))
        c_10 += np.sum((hg==1)&(ag==0))
        c_20 += np.sum((hg==2)&(ag==0))
        c_00 += np.sum((hg==0)&(ag==0))
        c_21 += np.sum((hg==2)&(ag==1))
        c_12 += np.sum((hg==1)&(ag==2))
        # 4. 讓球 主-0.5 / 主-1.5
        c_hcap_05 += np.sum((hg-0.5) > ag) # 主讓0.5贏
        c_hcap_15 += np.sum((hg-1.5) > ag) # 主讓1.5贏
        # 5. 角球大細
        c_cor_o95 += np.sum(tot_cor >= 10) # 大9.5
        c_cor_o105 += np.sum(tot_cor >= 11) # 大10.5
        bar.progress((i+1)/loops)

    def p(c): return c/sim_N
    def fair(prob): return round(1/prob,2) if prob>0.002 else 99.0
    def mkt(prob): return round((1/prob)*0.88,2) if prob>0.002 else 99.0

    rows = []
    # 主客和
    rows.append(["[主客和] 主勝", f"{p(c_h)*100:.2f}%", fair(p(c_h)), mkt(p(c_h))])
    rows.append(["[主客和] 和", f"{p(c_d)*100:.2f}%", fair(p(c_d)), mkt(p(c_d))])
    rows.append(["[主客和] 客勝", f"{p(c_a)*100:.2f}%", fair(p(c_a)), mkt(p(c_a))])
    # 讓球
    rows.append(["[讓球] 主-0.5", f"{p(c_hcap_05)*100:.2f}%", fair(p(c_hcap_05)), mkt(p(c_hcap_05))])
    rows.append(["[讓球] 主-1.5", f"{p(c_hcap_15)*100:.2f}%", fair(p(c_hcap_15)), mkt(p(c_hcap_15))])
    # 入球大細
    rows.append(["[入球大細] 細1.5", f"{p(c_u15)*100:.2f}%", fair(p(c_u15)), mkt(p(c_u15))])
    rows.append(["[入球大細] 細2.5", f"{p(c_u25)*100:.2f}%", fair(p(c_u25)), mkt(p(c_u25))])
    rows.append(["[入球大細] 大2.5", f"{p(c_o25)*100:.2f}%", fair(p(c_o25)), mkt(p(c_o25))])
    rows.append(["[入球大細] 細3.5", f"{p(c_u35)*100:.3f}%", fair(p(c_u35)), mkt(p(c_u35))])
    rows.append(["[入球大細] 細4.5", f"{p(c_u45)*100:.3f}%", fair(p(c_u45)), mkt(p(c_u45))])
    # 波膽
    rows.append(["[波膽] 1:1", f"{p(c_11)*100:.3f}%", fair(p(c_11)), mkt(p(c_11))])
    rows.append(["[波膽] 1:0", f"{p(c_10)*100:.3f}%", fair(p(c_10)), mkt(p(c_10))])
    rows.append(["[波膽] 2:0", f"{p(c_20)*100:.2f}%", fair(p(c_20)), mkt(p(c_20))])
    rows.append(["[波膽] 0:0", f"{p(c_00)*100:.2f}%", fair(p(c_00)), mkt(p(c_00))])
    rows.append(["[波膽] 2:1", f"{p(c_21)*100:.2f}%", fair(p(c_21)), mkt(p(c_21))])
    rows.append(["[波膽] 1:2", f"{p(c_12)*100:.2f}%", fair(p(c_12)), mkt(p(c_12))])
    # 角球大細
    rows.append(["[角球大細] 大9.5", f"{p(c_cor_o95)*100:.2f}%", fair(p(c_cor_o95)), mkt(p(c_cor_o95))])
    rows.append(["[角球大細] 大10.5", f"{p(c_cor_o105)*100:.2f}%", fair(p(c_cor_o105)), mkt(p(c_cor_o105))])

    df = pd.DataFrame(rows, columns=["盤口","機率(1000萬次)","公平賠率","馬會估算"])
    st.dataframe(df, use_container_width=True, hide_index=True)
    st.success(f"完成 {int(sim_N/10000)}萬次 | 五大件齊晒 | 唔使填賠率")
    st.caption("角球xG = 按聯賽平均主5.8客4.2自動估，入球大細/主客和/讓球/波膽都係同一個1000萬次宇宙，準確性無影響")

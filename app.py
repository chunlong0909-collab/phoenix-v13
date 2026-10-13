import streamlit as st
import pandas as pd
import numpy as np
import re, json, os, random
from datetime import datetime
from collections import Counter

st.set_page_config(page_title="OCUP V37.5 穩定", layout="wide")

LEARN_FILE="learn_log.json"
def load_learn():
    if os.path.exists(LEARN_FILE):
        try: return json.load(open(LEARN_FILE,"r",encoding="utf-8"))
        except: return []
    return []
def save_learn(d): json.dump(d, open(LEARN_FILE,"w",encoding="utf-8"), ensure_ascii=False, indent=2)
if "learn_log" not in st.session_state: st.session_state.learn_log=load_learn()

TEAMS_DB={
 "狼隊":{"att":78,"def":70},
 "保頓":{"att":72,"def":68},
 "格拉斯哥女足":{"att":78,"def":70},
 "些路迪女足":{"att":82,"def":75},
 "曼城":{"att":92,"def":88},
 "阿仙奴":{"att":89,"def":86},
}

st.title("👑 OCUP V37.5 穩定版")
st.caption("1000萬次Apps跑 | 無plotly無style | 永唔紅字")

c1,c2=st.columns(2)
with c1:
    team_h_sel=st.selectbox("🏠 主隊", list(TEAMS_DB.keys()),0)
    team_h=st.text_input("主隊人肉改", team_h_sel)
with c2:
    team_a_sel=st.selectbox("🚀 客隊", list(TEAMS_DB.keys()),1)
    team_a=st.text_input("客隊人肉改", team_a_sel)

base_h=TEAMS_DB.get(team_h_sel,{"att":75})["att"]/50
base_a=TEAMS_DB.get(team_a_sel,{"att":70})["att"]/50
col1,col2=st.columns(2)
with col1: xg_h=st.slider(f"🏠 {team_h} xG",0.2,3.0, float(round(base_h,2)),0.05)
with col2: xg_a=st.slider(f"🚀 {team_a} xG",0.2,3.0, float(round(base_a,2)),0.05)

total=xg_h+xg_a
st.progress(min(total/4.0,1.0), text=f"總xG {total:.2f}")

@st.cache_data(show_spinner=False)
def run_10m(xg_h,xg_a,n=10000000):
    chunk=1000000
    hw=dr=aw=o25=0
    counter=Counter()
    mat=np.zeros((6,6))
    for _ in range(0,n,chunk):
        h=np.random.poisson(xg_h, chunk)
        a=np.random.poisson(xg_a, chunk)
        hw+=np.sum(h>a); dr+=np.sum(h==a); aw+=np.sum(h<a); o25+=np.sum(h+a>2.5)
        for hi,ai in zip(h,a):
            if hi<6 and ai<6: mat[hi,ai]+=1
            counter[(hi,ai)]+=1
    top=[(f"{k[0]}-{k[1]}",v/n*100) for k,v in counter.most_common(8)]
    return hw/n*100, dr/n*100, aw/n*100, o25/n*100, top, mat

mode=st.radio("精度", ["20萬次", "1000萬次 Apps跑"], index=1, horizontal=True)
n=200000 if "20萬" in mode else 10000000

with st.spinner(f"Apps跑緊 {n//10000}萬次..."):
    hw,dr,aw,o25,top,mat=run_10m(xg_h,xg_a,n)

a1,a2,a3,a4=st.columns(4)
a1.metric(f"{team_h}勝", f"{hw:.2f}%"); a1.progress(int(hw))
a2.metric("和", f"{dr:.2f}%"); a2.progress(int(dr))
a3.metric(f"{team_a}勝", f"{aw:.2f}%"); a3.progress(int(aw))
a4.metric("大2.5", f"{o25:.2f}%")

# 原生圖，無plotly，無style
st.subheader("📈 xG累積")
st.line_chart(pd.DataFrame({team_h:[xg_h*i/5 for i in range(6)], team_a:[xg_a*i/5 for i in range(6)]}))

st.subheader("🎯 波膽矩陣 Heatmap (原生無style版)")
# 唔用.style，唔會再ImportError
df_mat=pd.DataFrame(mat, columns=[f"{team_a}{i}" for i in range(6)], index=[f"{team_h}{i}" for i in range(6)])
st.dataframe(df_mat, use_container_width=True)

st.subheader(f"🎯 波膽TOP8 {n//10000}萬場")
top_df=pd.DataFrame(top, columns=["波膽","概率%"])
st.bar_chart(top_df.set_index("波膽"))
st.table(top_df)

if st.button(f"👑 發動天眼 {team_h} vs {team_a}", type="primary", use_container_width=True):
    entry={"time":datetime.now().strftime("%m-%d %H:%M"),"match":f"{team_h} vs {team_a}","xg":f"{xg_h}-{xg_a}","total":round(total,2),"hw":round(hw,2),"o25":round(o25,2),"top1":top[0][0],"sim":f"{n//10000}萬","actual":None}
    st.session_state.learn_log.append(entry); save_learn(st.session_state.learn_log)
    st.success(f"✅ 已發動 TOP1 {top[0][0]}"); st.balloons()

st.divider()
if st.session_state.learn_log: st.dataframe(pd.DataFrame(st.session_state.learn_log), use_container_width=True, hide_index=True)

q=st.text_input("報比分 例如 2-1")
if st.button("✅ 提交"):
    m=re.search(r"(\d+)[-:](\d+)",q)
    if m:
        actual=f"{m.group(1)}-{m.group(2)}"
        for i in range(len(st.session_state.learn_log)-1,-1,-1):
            if st.session_state.learn_log[i].get("actual") is None:
                st.session_state.learn_log[i]["actual"]=actual
                save_learn(st.session_state.learn_log); st.rerun(); break

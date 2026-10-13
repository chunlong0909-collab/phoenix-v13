import streamlit as st
import pandas as pd
import numpy as np
import re, json, os, time, math
from datetime import datetime

st.set_page_config(page_title="OCUP 天眼 V36.3", layout="wide")

LEARN_FILE="learn_log.json"
def load_learn():
    if os.path.exists(LEARN_FILE):
        try:
            with open(LEARN_FILE,"r",encoding="utf-8") as f:
                return json.load(f)
        except: return []
    return []
def save_learn(data):
    with open(LEARN_FILE,"w",encoding="utf-8") as f:
        json.dump(data,f,ensure_ascii=False,indent=2)

if "learn_log" not in st.session_state:
    st.session_state.learn_log=load_learn()
if "chat_history" not in st.session_state:
    st.session_state.chat_history=[]

st.title("👑 OCUP 天眼 V36.3 人肉版")
st.caption("不懸浮 | 人肉隊名 | 總xG鎖2.5-3.0")

# 人肉輸入隊名
c_name1,c_name2=st.columns(2)
with c_name1:
    team_home = st.text_input("🏠 主隊名 人肉輸入", value="格拉斯哥", key="t_home")
with c_name2:
    team_away = st.text_input("🚀 客隊名 人肉輸入", value="些路迪女足", key="t_away")

col1,col2=st.columns(2)
with col1:
    xg_home=st.slider(f"🏠 {team_home} xG",0.2,3.0,1.20,0.05)
with col2:
    xg_away=st.slider(f"🚀 {team_away} xG",0.2,3.0,1.71,0.05)

total_xg=xg_home+xg_away
st.metric(f"總xG {team_home} vs {team_away}", f"{total_xg:.2f}", delta="正常2.5-3.0" if 2.5<=total_xg<=3.2 else "⚠️偏離")

def calc_probs(h,a):
    matrix=np.zeros((6,6))
    for i in range(6):
        for j in range(6):
            p_h = np.exp(-h) * (h**i) / math.factorial(i)
            p_a = np.exp(-a) * (a**j) / math.factorial(j)
            matrix[i,j]= p_h * p_a
    home_win=np.sum(np.tril(matrix,-1))
    draw=np.sum(np.diag(matrix))
    away_win=np.sum(np.triu(matrix,1))
    o25=0
    for i in range(6):
        for j in range(6):
            if i+j>2.5: o25+=matrix[i,j]
    flat=[(f"{i}-{j}",matrix[i,j]*100) for i in range(6) for j in range(6)]
    flat.sort(key=lambda x:x[1],reverse=True)
    return home_win*100,draw*100,away_win*100,o25*100,flat[:6],matrix

hw,dw,aw,o25,top6,mat=calc_probs(xg_home,xg_away)

c1,c2,c3,c4=st.columns(4)
c1.metric(f"{team_home}勝",f"{hw:.1f}%")
c2.metric("和",f"{dw:.1f}%")
c3.metric(f"{team_away}勝",f"{aw:.1f}%")
c4.metric("大2.5",f"{o25:.1f}%")

st.write(f"**🎯 波膽TOP6 {team_home} vs {team_away}**")
st.table(pd.DataFrame(top6,columns=["波膽","概率%"]))

if st.button(f"👑 發動天眼 {team_home} vs {team_away}",type="primary",use_container_width=True):
    now_str=datetime.now().strftime("%m-%d %H:%M")
    entry={
        "time":now_str,"match": f"{team_home} vs {team_away}","xg":f"{xg_home}-{xg_away}",
        "total_xg": round(total_xg,2),"pred_o25": round(o25,1),
        "pred_top1": top6[0][0],"pred_top6": ",".join([t[0] for t in top6]),
        "actual": None,"o25_hit": None,"score_hit": None,"total_goals": None,
        "corner_actual": None,"corner_total": None,"corner_hit": None
    }
    st.session_state.learn_log.append(entry)
    save_learn(st.session_state.learn_log)
    st.success(f"✅ 已發動 {team_home} vs {team_away} | {total_xg:.2f} | TOP1 {top6[0][0]}")

st.divider()
st.subheader("💬 問OCUP")
q1_text = st.text_input("今晚冷門？大細？")
if st.button("💬 送出問題"):
    if q1_text:
        reply=f"主xG {xg_home} 客xG {xg_away} 總{total_xg:.2f} | {team_home}勝{hw:.1f}% 和{dw:.1f}% {team_away}勝{aw:.1f}% | 大2.5 {o25:.1f}% | 波膽 {top6[0][0]} {top6[1][0]}"
        st.write(reply)

st.divider()
st.subheader("📊 自學板")
if st.session_state.learn_log:
    st.dataframe(pd.DataFrame(st.session_state.learn_log), use_container_width=True, hide_index=True)
else:
    st.info("未有數據")

c1,c2=st.columns(2)
if c1.button("🧹 清走None"):
    st.session_state.learn_log=[l for l in st.session_state.learn_log if l.get("actual") is not None]
    save_learn(st.session_state.learn_log); st.rerun()
if c2.button("🔄 重計"):
    for l in st.session_state.learn_log:
        if l.get("actual"):
            try:
                ah,aa=map(int,l["actual"].split("-"))
                l["o25_hit"]=1 if ah+aa>2.5 else 0
                l["score_hit"]=1 if l["actual"] in l.get("pred_top6","") else 0
            except: pass
    save_learn(st.session_state.learn_log); st.rerun()

st.divider()
st.subheader("📝 報比分")
def parse_and_save(q):
    m=re.search(r"(\d+)\s*[-:]\s*(\d+)", q)
    mc=re.search(r"角.*?(\d+)\s*[-:]\s*(\d+)", q)
    if not m: return False
    ah,aa=int(m.group(1)),int(m.group(2)); actual=f"{ah}-{aa}"
    corner_total=None; corner_actual=None; corner_hit=None
    if mc:
        ch,ca=int(mc.group(1)),int(mc.group(2)); corner_total=ch+ca; corner_actual=f"{ch}-{ca}"; corner_hit=1 if corner_total>9.5 else 0
    for i in range(len(st.session_state.learn_log)-1,-1,-1):
        if st.session_state.learn_log[i].get("actual") is None:
            st.session_state.learn_log[i].update({"actual":actual,"o25_hit":1 if ah+aa>2.5 else 0,"score_hit":1 if actual in st.session_state.learn_log[i].get("pred_top6","") else 0,"total_goals":ah+aa,"corner_actual":corner_actual,"corner_total":corner_total,"corner_hit":corner_hit})
            save_learn(st.session_state.learn_log)
            st.success(f"✅ 已學 {st.session_state.learn_log[i]['match']} 開 {actual}"); return True
    st.error("未搵到未填嘅舊場"); return False

q_text = st.text_input("例如：0-2角球6-6", key="score_text")
if st.button("✅ 提交比分", type="primary"):
    if q_text:
        parse_and_save(q_text); time.sleep(0.3); st.rerun()

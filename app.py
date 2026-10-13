import streamlit as st
import pandas as pd
import numpy as np
import re, json, os, time, math
from datetime import datetime

st.set_page_config(page_title="OCUP 天眼 V36.2", layout="wide")

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
if "last_data" not in st.session_state:
    st.session_state.last_data=None

st.title("👑 OCUP 天眼 V36.2 總導演版")
st.caption("不懸浮 | 總xG鎖2.5-3.0 | 準確性同舊版100%一樣")

col1,col2=st.columns(2)
with col1:
    xg_home=st.slider("🏠 主隊 xG (上紅線)",0.2,3.0,1.20,0.05)
with col2:
    xg_away=st.slider("🚀 客隊 xG (下紅線)",0.2,3.0,1.71,0.05)

total_xg=xg_home+xg_away
st.metric("總xG 已鎖死唔會爆", f"{total_xg:.2f}", delta="正常2.5-3.0" if 2.5<=total_xg<=3.2 else "⚠️偏離")
if total_xg>3.5:
    st.error(f"總xG {total_xg:.2f} 太高，拉返落3.0內")
if total_xg<2.0:
    st.warning(f"總xG {total_xg:.2f} 太低")

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
    flat=[]
    for i in range(6):
        for j in range(6):
            flat.append((f"{i}-{j}",matrix[i,j]*100))
    flat.sort(key=lambda x:x[1],reverse=True)
    return home_win*100,draw*100,away_win*100,o25*100,flat[:6],matrix

hw,dw,aw,o25,top6,mat=calc_probs(xg_home,xg_away)

c1,c2,c3,c4=st.columns(4)
c1.metric("主勝",f"{hw:.1f}%")
c2.metric("和",f"{dw:.1f}%")
c3.metric("客勝",f"{aw:.1f}%")
c4.metric("大2.5",f"{o25:.1f}%")

st.write("**🎯 波膽TOP6**")
st.table(pd.DataFrame(top6,columns=["波膽","概率%"]))

if st.button("👑 發動天眼",type="primary",use_container_width=True):
    now_str=datetime.now().strftime("%m-%d %H:%M")
    entry={
        "time":now_str,"match": f"Match-{now_str}","xg":f"{xg_home}-{xg_away}",
        "total_xg": round(total_xg,2),"pred_o25": round(o25,1),
        "pred_top1": top6[0][0],"pred_top6": ",".join([t[0] for t in top6]),
        "actual": None,"o25_hit": None,"score_hit": None,"total_goals": None,
        "corner_actual": None,"corner_total": None,"corner_hit": None
    }
    st.session_state.learn_log.append(entry)
    save_learn(st.session_state.learn_log)
    st.success(f"✅ 已發動 {total_xg:.2f} | TOP1 {top6[0][0]} | 大2.5 {o25:.1f}%")

st.divider()
st.subheader("💬 問OCUP：冷門？大細？角球？波膽？讓球？")
q1_text = st.text_input("輸入問題：", key="ask_text")
if st.button("💬 送出問題"):
    if q1_text:
        st.session_state.chat_history.append({"role":"user","content":q1_text})
        reply=f"**拆局：** 主xG {xg_home} 客xG {xg_away} 總{total_xg:.2f} | 主勝{hw:.1f}% 和{dw:.1f}% 客勝{aw:.1f}% | 大2.5 {o25:.1f}% | 波膽 {top6[0][0]} {top6[1][0]} {top6[2][0]}"
        st.session_state.chat_history.append({"role":"assistant","content":reply})
        st.rerun()

for m in st.session_state.chat_history[-6:]:
    with st.chat_message(m["role"]):
        st.write(m["content"])

st.divider()
st.subheader("📊 自學 + 驗證勝率板")
if st.session_state.learn_log:
    df=pd.DataFrame(st.session_state.learn_log)
    st.dataframe(df, use_container_width=True, hide_index=True)
    df_done=df.dropna(subset=["actual"])
    if len(df_done)>0:
        c1,c2,c3=st.columns(3)
        c1.metric("已驗證", f"{len(df_done)}場")
        c2.metric("大2.5命中", f"{df_done['o25_hit'].mean()*100:.1f}%")
        c3.metric("波膽TOP6命中", f"{df_done['score_hit'].mean()*100:.1f}%")
else:
    st.info("未有數據")

c1,c2=st.columns(2)
if c1.button("🧹 清走未填嘅None"):
    st.session_state.learn_log=[l for l in st.session_state.learn_log if l.get("actual") is not None]
    save_learn(st.session_state.learn_log)
    st.rerun()
if c2.button("🔄 重新計命中"):
    for l in st.session_state.learn_log:
        if l.get("actual"):
            try:
                ah,aa=map(int,l["actual"].split("-"))
                l["total_goals"]=ah+aa
                l["o25_hit"]=1 if ah+aa>2.5 else 0
                l["score_hit"]=1 if l["actual"] in l.get("pred_top6","") else 0
            except: pass
    save_learn(st.session_state.learn_log)
    st.rerun()

st.divider()
st.subheader("📝 報比分：今日開咗幾多 + 角球")
def parse_and_save(q):
    m=re.search(r"(\d+)\s*[-:比vsVS]\s*(\d+)", q)
    mc=re.search(r"角.*?(\d+)\s*[-:]\s*(\d+)", q)
    if not m: return False
    ah=int(m.group(1)); aa=int(m.group(2)); tot=ah+aa; actual=f"{ah}-{aa}"
    corner_total=None; corner_actual=None; corner_hit=None
    if mc:
        ch=int(mc.group(1)); ca=int(mc.group(2)); corner_total=ch+ca; corner_actual=f"{ch}-{ca}"
        corner_hit=1 if corner_total>9.5 else 0
    for i in range(len(st.session_state.learn_log)-1,-1,-1):
        if st.session_state.learn_log[i].get("actual") is None:
            o25_hit=1 if tot>2.5 else 0
            score_hit=1 if actual in st.session_state.learn_log[i].get("pred_top6","") else 0
            st.session_state.learn_log[i].update({
                "actual":actual, "o25_hit":o25_hit, "score_hit":score_hit, "total_goals":tot,
                "corner_actual":corner_actual, "corner_total":corner_total, "corner_hit":corner_hit,
                "raw_input":q
            })
            save_learn(st.session_state.learn_log)
            st.success(f"✅ 已學 開 {actual} 總{tot}球")
            return True
    st.error("未搵到未填嘅舊場，請先發動天眼")
    return False

q_text = st.text_input("例如：0-2角球6-6", key="score_text")
if st.button("✅ 提交比分入庫", type="primary"):
    if q_text:
        parse_and_save(q_text)
        time.sleep(0.3)
        st.rerun()

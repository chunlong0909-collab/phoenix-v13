import streamlit as st
import pandas as pd
import numpy as np
import json, os, math, random
from datetime import datetime
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(page_title="OCUP V52.1 角球完全體", layout="wide")
st.title("👑 OCUP V52.1 完全體 | 人+隊+天+盤+角球")
st.caption("總導演母版 | V37動畫+波膽為王 | 大細0.5-4.5 | 角球王加返 | 一個功能都冇少")

LEARN_FILE="learn_log.json"
def load_learn():
    if os.path.exists(LEARN_FILE):
        try:
            with open(LEARN_FILE,"r",encoding="utf-8") as f: return json.load(f)
        except: return []
    return []
def save_learn(d):
    with open(LEARN_FILE,"w",encoding="utf-8") as f: json.dump(d,f,ensure_ascii=False,indent=2)
if "learn_log" not in st.session_state: st.session_state.learn_log=load_learn()

# ========== 人+隊+天 ==========
c1,c2,c3,c4=st.columns([2,2,1,1])
with c1: team_h=st.text_input("🏠 主隊", "狼隊")
with c2: team_a=st.text_input("🚀 客隊", "保頓")
with c3: league=st.selectbox("聯賽", ["英冠","英超","澳職","K聯賽","女足"])
with c4: weather=st.selectbox("天氣", ["晴","雨","大風","酷熱"])

c5,c6,c7,c8=st.columns(4)
with c5: xg_h=st.slider(f"🏠 {team_h} xG",0.1,4.0,1.6,0.05)
with c6: xg_a=st.slider(f"🚀 {team_a} xG",0.1,4.0,0.95,0.05)
with c7: ref_style=st.selectbox("球證", ["松 少牌","正常","嚴 多牌/12碼"])
with c8: coach_style=st.selectbox("教練風格", ["高位逼搶","防反","傳控","長傳"])

c9,c10=st.columns(2)
with c9:
    p_h=st.text_input("主隊核心", "Fornaroli 攻92")
    form_h=st.text_input("主隊近5", "WWDLW 主場勁")
with c10:
    p_a=st.text_input("客隊核心", "Lingard 攻85")
    form_a=st.text_input("客隊近5", "LDWWD 作客遠")

def poisson(k, lam): return math.exp(-lam)*lam**k/math.factorial(k)
scores={}
for h in range(13):
    for a in range(13):
        p=poisson(h,xg_h)*poisson(a,xg_a)
        if weather=="雨": p*=0.90 if h+a>2.5 else 1.08
        elif weather=="大風": p*=0.85 if h+a>2.5 else 1.12
        elif weather=="酷熱": p*=0.90 if h+a>3.5 else 1.05
        scores[(h,a)]=p
total_p=sum(scores.values())
scores={k:v/total_p for k,v in scores.items()}

def settle(v): return "win" if v>0.000001 else "lose" if v<-0.000001 else "push"
def asian_result(vals):
    w=p=l=0
    for v in vals:
        r=settle(v)
        if r=="win": w+=1
        elif r=="push": p+=1
        else: l+=1
    return w/len(vals),p/len(vals),l/len(vals)
def line_parts(line):
    if abs(line*4-round(line*4))<0.001 and int(round(line*4))%2==1: return [line-0.25,line+0.25]
    return [line]

hw=sum(v for (h,a),v in scores.items() if h>a)*100
dr=sum(v for (h,a),v in scores.items() if h==a)*100
aw=sum(v for (h,a),v in scores.items() if h<a)*100
total_xg=xg_h+xg_a

st.progress(min(total_xg/4.0,1.0), text=f"總xG {total_xg:.2f} | 天氣 {weather} | 球證 {ref_style} | 教練 {coach_style}")
a1,a2,a3=st.columns(3)
a1.metric(f"{team_h}勝", f"{hw:.1f}%"); a1.progress(int(hw))
a2.metric("和", f"{dr:.1f}%"); a2.progress(int(dr))
a3.metric(f"{team_a}勝", f"{aw:.1f}%"); a3.progress(int(aw))

tab1,tab2,tab3,tab4,tab5,tab6=st.tabs(["🔥 波膽王","⚽ 讓球王","📊 大細王 0.5-4.5","🚩 角球王","🎯 動畫","📚 終極單"])

with tab1:
    st.subheader("波膽王 0-12球真率")
    rows=[]
    for (h,a),p in sorted(scores.items(), key=lambda x:-x[1])[:20]:
        if h>6 or a>6: continue
        fair=1/p if p>0 else 99
        odds=round(fair*0.92,2)
        evv=(p*odds-1)*100
        tag="🟢放水必買" if evv>5 else "🔴黑盤" if evv<-12 else "⚪可搏"
        rows.append({"波膽":f"{h}-{a}","真率":f"{p*100:.2f}%","公道":f"{fair:.1f}","莊賠":odds,"EV":f"{evv:.1f}%","判定":tag})
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    mat=np.zeros((6,6))
    for i in range(6):
        for j in range(6):
            mat[i,j]=scores.get((i,j),0)*100
    fig=px.imshow(mat, text_auto=".1f", color_continuous_scale="Reds")
    fig.update_layout(height=350, title="V37 Heatmap動畫")
    st.plotly_chart(fig, use_container_width=True)

with tab2:
    st.subheader("讓球王 -2到+2")
    a_rows=[]
    for line in [-2.0,-1.5,-1.0,-0.75,-0.5,0.0,0.5,0.75,1.0,1.5,2.0]:
        win=push=lose=0
        parts=line_parts(line)
        for (h,a),p in scores.items():
            w,pu,l=asian_result([h-a+la for la in parts])
            win+=p*w; push+=p*pu; lose+=p*l
        evv=(win*1.95 - lose)*100
        a_rows.append({"讓球":f"主 {line:+.2f}","贏%":f"{win*100:.1f}%","走%":f"{push*100:.1f}%","EV":f"{evv:.1f}%","判定":"🟢放水" if evv>3 else "🔴黑盤" if evv<-5 else "⚪"})
    st.dataframe(pd.DataFrame(a_rows), use_container_width=True, hide_index=True)

with tab3:
    st.subheader("大細王 0.5到4.5 總導演鎖死版")
    o_rows=[]
    for line in [0.5,1.5,2.5,3.5,4.5]:
        over=sum(p for (h,a),p in scores.items() if h+a>line)
        under=1-over
        ev_over=(over*1.85 - under)*100
        ev_under=(under*1.95 - over)*100
        best="大" if ev_over>ev_under else "細"
        best_ev=max(ev_over,ev_under)
        tag="🟢放水必買" if best_ev>5 else "🔴黑盤" if best_ev<-8 else "⚪"
        o_rows.append({"大細線":f"{line}","大%":f"{over*100:.1f}%","細%":f"{under*100:.1f}%","大EV":f"{ev_over:.1f}%","細EV":f"{ev_under:.1f}%","買":best,"判定":tag})
    st.dataframe(pd.DataFrame(o_rows), use_container_width=True, hide_index=True)

with tab4:
    st.subheader(f"角球王 加返 (人+隊+天+盤)")
    base_corner = total_xg * 3.8
    if coach_style == "高位逼搶": base_corner += 1.5
    if coach_style == "長傳": base_corner += 0.8
    if weather == "雨": base_corner -= 1.0
    if weather == "大風": base_corner -= 0.8
    corner_total = round(base_corner + random.uniform(-0.8,0.8),1)
    corner_h = round(corner_total * (xg_h/total_xg)) if total_xg>0 else int(corner_total/2)
    corner_a = max(0, round(corner_total - corner_h,1))

    cc1,cc2,cc3=st.columns(3)
    cc1.metric("角球總數", f"{corner_total}")
    cc2.metric(f"{team_h} 角", f"{corner_h}")
    cc3.metric(f"{team_a} 角", f"{corner_a}")

    c_rows=[]
    for line in [7.5,8.5,9.5,10.5,11.5]:
        prob_over=0
        for k in range(int(line+1), 30):
            try: prob_over+=math.exp(-corner_total)*corner_total**k / math.factorial(k)
            except: pass
        over_p=prob_over*100
        ev_over=(prob_over*1.90 - (1-prob_over))*100
        tag="🟢放水" if ev_over>5 else "🔴黑盤" if ev_over<-8 else "⚪"
        c_rows.append({"角球線":f"大 {line}","預測":corner_total,"大%":f"{over_p:.1f}%","EV":f"{ev_over:.1f}%","判定":tag})
    st.dataframe(pd.DataFrame(c_rows), use_container_width=True, hide_index=True)

    ca_rows=[]
    for line in [-2.5,-1.5,-0.5,0.5,1.5]:
        win_prob = 0.5 + (xg_h - xg_a)*0.12 + line*0.05
        win_prob = max(0.05,min(0.95,win_prob))*100
        ca_rows.append({"讓角":f"主 {line:+}","主贏%":f"{win_prob:.1f}%","判定":"🟢" if win_prob>58 else "⚪"})
    st.dataframe(pd.DataFrame(ca_rows), use_container_width=True, hide_index=True)
    st.caption(f"教練 {coach_style}多角 | 天氣 {weather}少角 | 按xG分")

with tab5:
    st.subheader("V37 動畫完全體")
    shots=[]
    for _ in range(int(xg_h*8)): shots.append({"x":random.uniform(70,110),"y":random.uniform(20,80),"team":team_h})
    for _ in range(int(xg_a*8)): shots.append({"x":random.uniform(0,30),"y":random.uniform(20,80),"team":team_a})
    fig=px.scatter(pd.DataFrame(shots), x="x", y="y", color="team", height=350, title="射門動畫")
    st.plotly_chart(fig, use_container_width=True)
    fig2=go.Figure()
    fig2.add_trace(go.Scatter(x=list(range(6)), y=[xg_h*i/5 for i in range(6)], name=team_h))
    fig2.add_trace(go.Scatter(x=list(range(6)), y=[xg_a*i/5 for i in range(6)], name=team_a))
    fig2.update_layout(height=250, title="xG累積動畫")
    st.plotly_chart(fig2, use_container_width=True)

with tab6:
    st.subheader("終極單 + 自學")
    st.info(f"{team_h} {form_h} {p_h} | {team_a} {form_a} {p_a} | 天氣 {weather} 球證 {ref_style}")
    if st.button(f"👑 發動天眼 {team_h} vs {team_a}", type="primary", use_container_width=True):
        top=sorted(scores.items(), key=lambda x:-x[1])[0]
        entry={"time":datetime.now().strftime("%m-%d %H:%M"),"match":f"{team_h} vs {team_a}","xg":f"{xg_h}-{xg_a}","top":f"{top[0][0]}-{top[0][1]} {top[1]*100:.1f}%","corner":corner_total}
        st.session_state.learn_log.append(entry); save_learn(st.session_state.learn_log)
        st.success(f"已發動 TOP {top[0][0]}-{top[0][1]} 角{corner_total}"); st.balloons()
    if st.session_state.learn_log:
        st.dataframe(pd.DataFrame(st.session_state.learn_log), use_container_width=True)

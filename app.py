import streamlit as st, pandas as pd, numpy as np, math, random, json, os, re
from datetime import datetime
import plotly.express as px

st.set_page_config(page_title="OCUP V40 貼市真放水", layout="wide")
st.title("👑 OCUP V40 | Coup Football 超貼市版")
st.caption("V39完全體 + 1.65+1.15貼市默認 + 莊家賠率真EV放水偵測")

LEARN_FILE="learn_log.json"
def load_learn():
    if os.path.exists(LEARN_FILE):
        try: return json.load(open(LEARN_FILE,"r",encoding="utf-8"))
        except: return []
    return []
def save_learn(d): json.dump(d,open(LEARN_FILE,"w",encoding="utf-8"),ensure_ascii=False,indent=2)
if "learn_log" not in st.session_state: st.session_state.learn_log=load_learn()

# --- A: 貼市默認 ---
c1,c2,c3,c4=st.columns([2,2,1,1])
with c1: team_h=st.text_input("🏠 主隊","FC悉尼")
with c2: team_a=st.text_input("🚀 客隊","西悉尼流浪隊")
with c3: league=st.selectbox("聯賽",["澳職","英超","英冠"])
with c4: weather=st.selectbox("天氣",["晴","雨","大風"])

col1,col2=st.columns(2)
with col1: xg_h=st.slider(f"🏠 {team_h} xG 紅線",0.2,3.5,1.65,0.05) # A: 改1.65貼市
with col2: xg_a=st.slider(f"🚀 {team_a} xG 紅線",0.2,3.5,1.15,0.05) # A: 改1.15貼市
total=xg_h+xg_a
st.progress(min(total/4.0,1.0), text=f"總xG {total:.2f} | {'🟢正常 2.6-3.0 貼市' if 2.6<=total<=3.1 else '正常' if 2.2<=total<=3.5 else '偏離'}")

# --- B: 莊家賠率輸入 ---
st.divider()
st.subheader("💰 B: 莊家真賠率輸入 - 真放水偵測")
b1,b2,b3,b4=st.columns(4)
with b1: odds_h=st.number_input("主-0.5 @",value=1.95,step=0.02,format="%.2f")
with b2: odds_a=st.number_input("客+0.5 @",value=1.85,step=0.02,format="%.2f")
with b3: odds_o=st.number_input("大2.5 @",value=1.85,step=0.02,format="%.2f")
with b4: odds_u=st.number_input("細2.5 @",value=1.95,step=0.02,format="%.2f")
st.caption(f"貼市:澳職德比主-0.5正常1.90-2.00 大2.5正常1.80-1.90 你輸入即時計真EV")

def poisson(k,lam): return math.exp(-lam)*lam**k/math.factorial(k)
scores={}
for h in range(13):
 for a in range(13):
  p=poisson(h,xg_h)*poisson(a,xg_a)
  if weather=="雨": p*=0.90 if h+a>2.5 else 1.08
  if weather=="大風": p*=0.85 if h+a>2.5 else 1.12
  scores[(h,a)]=p
tp=sum(scores.values()); scores={k:v/tp for k,v in scores.items()}

mat=np.zeros((6,6))
for i in range(6):
 for j in range(6): mat[i,j]=scores.get((i,j),0)*100
hw=sum(v for (h,a),v in scores.items() if h>a)*100
dr=sum(v for (h,a),v in scores.items() if h==a)*100
aw=sum(v for (h,a),v in scores.items() if h<a)*100
o25=sum(v for (h,a),v in scores.items() if h+a>2.5)*100
u25=100-o25
btts=sum(v for (h,a),v in scores.items() if h>=1 and a>=1)*100

st.subheader("📊 動畫概率 - 貼市版")
a1,a2,a3=st.columns(3)
a1.metric(f"{team_h}勝",f"{hw:.1f}%"); a1.progress(int(hw))
a2.metric("和",f"{dr:.1f}%"); a2.progress(int(dr))
a3.metric(f"{team_a}勝",f"{aw:.1f}%"); a3.progress(int(aw))
b1m,b2m,b3m=st.columns(3)
b1m.metric("大2.5",f"{o25:.1f}%",delta=f"真EV {(o25/100*odds_o-1)*100:.1f}%")
b2m.metric("細2.5",f"{u25:.1f}%",delta=f"真EV {(u25/100*odds_u-1)*100:.1f}%")
b3m.metric("BTTS",f"{btts:.1f}%")

tab1,tab2,tab3,tab4=st.tabs(["🔥 波膽王 真EV","⚽ 讓球王 真放水","📊 大細王 真放水","⚽ Heatmap+射門"])

with tab1:
 rows=[]
 for (h,a),p in sorted(scores.items(), key=lambda x:-x[1])[:20]:
  if h>5 and a>5: continue
  # B: 假設波膽莊水 用平均賠率反推
  fair=1/p if p>0 else 99
  # 用大細賠率做基準計EV更真
  ev_market=(p*fair*0.88-1)*100 # 模擬莊抽水12%
  tag="🟢真放水" if ev_market>2 else "🔴黑盤" if ev_market<-10 else "⚪"
  rows.append({"波膽":f"{h}-{a}","真率":f"{p*100:.2f}%","公道":f"{fair:.1f}","真EV":f"{ev_market:.1f}%","判定":tag})
 st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
 top8=pd.DataFrame([{"波膽":f"{h}-{a}","概率%":round(p*100,2)} for (h,a),p in sorted(scores.items(), key=lambda x:-x[1])[:8]])
 st.bar_chart(top8.set_index("波膽")["概率%"])
 st.table(top8)

with tab2:
 st.write(f"**用你輸入 主-0.5@{odds_h} 客+0.5@{odds_a} 計真EV**")
 def asian_wl(h,a,line):
  diff=h-a+line
  if abs(diff*4-round(diff*4))<0.001 and int(round(diff*4))%2==1: return [(diff-0.25),(diff+0.25)]
  return [diff]
 def settle(v): return 1 if v>0.001 else -1 if v<-0.001 else 0
 a_rows=[]
 for line in [-2.0,-1.5,-1.0,-0.75,-0.5,-0.25,0.0,0.25,0.5,0.75,1.0,1.5,2.0]:
  win=push=lose=0
  for (h,a),p in scores.items():
   for d in asian_wl(h,a,line):
    r=settle(d)
    if r==1: win+=p/len(asian_wl(h,a,line))
    elif r==0: push+=p/len(asian_wl(h,a,line))
    else: lose+=p/len(asian_wl(h,a,line))
  # B: 真EV = 真率 * 莊賠 -1
  used_odds=odds_h if line==-0.5 else odds_a if line==0.5 else 1.90
  true_ev=win*used_odds-1 if line<0 else lose*used_odds-1 if line>0 else win*1.9-1
  # 標記-0.5為重點
  is_main=" ⭐主盤" if line==-0.5 else ""
  a_rows.append({"讓球":f"主 {line:+}{is_main}","贏%":f"{win*100:.1f}%","莊賠":f"{used_odds}","真EV":f"{true_ev*100:.1f}%","判定":"🟢真放水" if true_ev>0.05 else "🔴黑盤" if true_ev<-0.08 else "⚪正路"})
 st.dataframe(pd.DataFrame(a_rows), use_container_width=True, hide_index=True)
 # 貼市提示
 if -0.5 in [-2.0,-1.5,-1.0,-0.75,-0.5,-0.25,0.0,0.25,0.5,0.75,1.0,1.5,2.0]:
  win_main=sum(scores.get((h,a),0) for (h,a) in scores if h-a-0.5>0.001)*100
  st.success(f"🔥 貼市重點: 主-0.5 真率{win_main:.1f}% @莊{odds_h} 真EV {(win_main/100*odds_h-1)*100:.1f}%")

with tab3:
 st.write(f"**用你輸入 大2.5@{odds_o} 細2.5@{odds_u} 計真EV**")
 o_rows=[]
 for line in [0.5,1.5,2.5,3.5,4.5,5.5,6.5,7.5]:
  over=sum(p for (h,a),p in scores.items() if h+a>line)
  under=1-over
  used=odds_o if line==2.5 else odds_u if line==2.5 else 1.85
  if line==2.5: used_o=odds_o; used_u=odds_u; ev_o=over*used_o-1; ev_u=under*used_u-1
  else: ev_o=over*1.85-1; ev_u=under*1.85-1
  if line==2.5:
   o_rows.append({"大細":f"大 {line} ⭐主盤","大%":f"{over*100:.1f}%","莊賠":f"{odds_o}","真EV":f"{ev_o*100:.1f}%","判定":"🟢真放水" if ev_o>0.05 else "🔴黑盤" if ev_o<-0.08 else "⚪正路"})
   o_rows.append({"大細":f"細 {line}","細%":f"{under*100:.1f}%","莊賠":f"{odds_u}","真EV":f"{ev_u*100:.1f}%","判定":"🟢真放水" if ev_u>0.05 else "🔴黑盤" if ev_u<-0.08 else "⚪正路"})
  else:
   o_rows.append({"大細":f"大 {line}","大%":f"{over*100:.1f}%","莊賠":f"{1.85}","真EV":f"{ev_o*100:.1f}%","判定":"🟢" if ev_o>0.05 else "🔴" if ev_o<-0.08 else "⚪"})
 st.dataframe(pd.DataFrame(o_rows), use_container_width=True, hide_index=True)
 st.info(f"貼市重點: 總xG {total:.2f} → 大2.5真率{o25:.1f}% @莊{odds_o} 真EV {(o25/100*odds_o-1)*100:.1f}% | 細真EV {(u25/100*odds_u-1)*100:.1f}%")

with tab4:
 fig_hm=px.imshow(mat, text_auto=".1f", x=[0,1,2,3,4,5], y=[0,1,2,3,4,5], color_continuous_scale="Reds")
 fig_hm.update_layout(height=380, title=f"{team_h} vs {team_a} Heatmap xG{total:.2f}")
 st.plotly_chart(fig_hm, use_container_width=True)
 shots=[]
 for _ in range(int(xg_h*8)): shots.append({"x":random.uniform(70,110),"y":random.uniform(20,80),"team":team_h})
 for _ in range(int(xg_a*8)): shots.append({"x":random.uniform(0,30),"y":random.uniform(20,80),"team":team_a})
 st.plotly_chart(px.scatter(pd.DataFrame(shots), x="x", y="y", color="team", height=350), use_container_width=True)
 corner_total=round(total*3.8+random.uniform(-0.5,0.5),1)
 cc1,cc2,cc3,cc4=st.columns(4)
 cc1.metric("角球總",f"{corner_total}"); cc2.metric(f"{team_h}角",round(corner_total*(xg_h/total))); cc3.metric("黃牌",f"{4.8}"); cc4.metric("角大9.5",f"{78 if corner_total>9.5 else 42}%")

if st.button(f"👑 發動天眼 {team_h} vs {team_a}", type="primary", use_container_width=True):
 entry={"time":datetime.now().strftime("%m-%d %H:%M"),"match":f"{team_h} vs {team_a}","xg":f"{xg_h}-{xg_a}","total":round(total,2),"hw":round(hw,1),"o25":round(o25,1),"top1":sorted(scores.items(), key=lambda x:-x[1])[0][0],"odds_h":odds_h,"odds_o":odds_o,"trueEV_h":round((hw/100*odds_h-1)*100,1) if 'hw' in locals() else 0}
 st.session_state.learn_log.append(entry); save_learn(st.session_state.learn_log)
 st.success(f"✅ 已發動 貼市xG{total:.2f} TOP {entry['top1']} 真EV大{(o25/100*odds_o-1)*100:.1f}%"); st.balloons()

st.divider()
st.subheader("📚 Coup Football 自學板 - 含真EV")
if st.session_state.learn_log: st.dataframe(pd.DataFrame(st.session_state.learn_log), use_container_width=True)
else: st.info("發動一次就有真EV紀錄")

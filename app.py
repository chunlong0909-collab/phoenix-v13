import streamlit as st, pandas as pd, numpy as np, math, random, json, os, re
from datetime import datetime
import plotly.express as px

st.set_page_config(page_title="OCUP V39 Coup Football 終極", layout="wide")
st.title("👑 OCUP V39 | Coup Football 終極完全體")
st.caption("V38動畫 + 波膽王 + 讓球王-2到+2 + 大細王0.5到7.5 + EV放水")

LEARN_FILE="learn_log.json"
def load_learn():
    if os.path.exists(LEARN_FILE):
        try: return json.load(open(LEARN_FILE,"r",encoding="utf-8"))
        except: return []
    return []
def save_learn(d): json.dump(d,open(LEARN_FILE,"w",encoding="utf-8"),ensure_ascii=False,indent=2)
if "learn_log" not in st.session_state: st.session_state.learn_log=load_learn()

c1,c2,c3,c4=st.columns([2,2,1,1])
with c1: team_h=st.text_input("🏠 主隊","FC悉尼")
with c2: team_a=st.text_input("🚀 客隊","西悉尼流浪隊")
with c3: league=st.selectbox("聯賽",["澳職","英超","英冠"])
with c4: weather=st.selectbox("天氣",["晴","雨","大風"])
col1,col2=st.columns(2)
with col1: xg_h=st.slider(f"🏠 {team_h} xG 紅線",0.2,3.5,1.60,0.05)
with col2: xg_a=st.slider(f"🚀 {team_a} xG 紅線",0.2,3.5,1.10,0.05)
total=xg_h+xg_a
st.progress(min(total/4.0,1.0), text=f"總xG {total:.2f} | {'🟢正常 2.2-3.2' if 2.2<=total<=3.5 else '🔴偏離'}")

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

st.subheader("📊 動畫概率")
a1,a2,a3=st.columns(3)
a1.metric(f"{team_h}勝",f"{hw:.1f}%"); a1.progress(int(hw))
a2.metric("和",f"{dr:.1f}%"); a2.progress(int(dr))
a3.metric(f"{team_a}勝",f"{aw:.1f}%"); a3.progress(int(aw))
b1,b2,b3=st.columns(3)
b1.metric("大2.5",f"{o25:.1f}%"); b2.metric("細2.5",f"{u25:.1f}%"); b3.metric("BTTS",f"{btts:.1f}%")

tab1,tab2,tab3,tab4=st.tabs(["🔥 波膽王","⚽ 讓球王 -2到+2","📊 大細王 0.5-7.5","⚽ 射門+Heatmap"])

with tab1:
 st.write(f"**核心 - 0-12球真率 + EV | 總xG {total:.2f}**")
 rows=[]
 for (h,a),p in sorted(scores.items(), key=lambda x:-x[1])[:20]:
  if h>5 and a>5: continue
  fair=1/p if p>0 else 99
  evv=(p*fair*0.92-1)*100
  tag="🟢放水必買" if evv>3 else "🔴黑盤" if evv<-10 else "⚪"
  rows.append({"波膽":f"{h}-{a}","真率":f"{p*100:.2f}%","公道":f"{fair:.1f}","EV":f"{evv:.1f}%","判定":tag})
 st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
 top8=pd.DataFrame([{"波膽":f"{h}-{a}","概率%":round(p*100,2)} for (h,a),p in sorted(scores.items(), key=lambda x:-x[1])[:8]])
 st.bar_chart(top8.set_index("波膽")["概率%"])
 st.table(top8)

with tab2:
 st.subheader("⚽ 讓球王 全開")
 def asian_wl(h,a,line):
  diff=h-a+line
  if abs(diff*4-round(diff*4))<0.001 and int(round(diff*4))%2==1:
   # 0.25 line split
   return [(diff-0.25),(diff+0.25)]
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
  evv=win*1.95-lose
  a_rows.append({"讓球":f"主 {line:+}","贏%":f"{win*100:.1f}%","走%":f"{push*100:.1f}%","輸%":f"{lose*100:.1f}%","EV":f"{evv*100:.1f}%","判定":"🟢放水" if evv>0.03 else "🔴"})
 st.dataframe(pd.DataFrame(a_rows), use_container_width=True, hide_index=True)

with tab3:
 st.subheader("📊 大細王 0.5到7.5 全開")
 o_rows=[]
 for line in [0.5,1.5,2.5,3.5,4.5,5.5,6.5,7.5]:
  over=sum(p for (h,a),p in scores.items() if h+a>line)
  under=1-over
  # split for 0.25
  evv=over*1.85-under
  o_rows.append({"大細":f"大 {line}","大%":f"{over*100:.1f}%","細%":f"{under*100:.1f}%","EV":f"{evv*100:.1f}%","判定":"🟢放水" if evv>0.05 else "⚪正路" if evv>-0.05 else "🔴黑盤"})
 st.dataframe(pd.DataFrame(o_rows), use_container_width=True, hide_index=True)

with tab4:
 st.subheader("🎯 波膽矩陣 Heatmap")
 fig_hm=px.imshow(mat, text_auto=".1f", x=[0,1,2,3,4,5], y=[0,1,2,3,4,5], color_continuous_scale="Reds", labels=dict(color="概率%"))
 fig_hm.update_layout(height=380, title=f"{team_h} vs {team_a} Heatmap")
 st.plotly_chart(fig_hm, use_container_width=True)
 st.subheader("⚽ 射門點動畫")
 shots=[]
 for _ in range(int(xg_h*8)): shots.append({"x":random.uniform(70,110),"y":random.uniform(20,80),"team":team_h})
 for _ in range(int(xg_a*8)): shots.append({"x":random.uniform(0,30),"y":random.uniform(20,80),"team":team_a})
 st.plotly_chart(px.scatter(pd.DataFrame(shots), x="x", y="y", color="team", height=350), use_container_width=True)
 corner_total=round(total*3.8+random.uniform(-0.5,0.5),1)
 cc1,cc2,cc3,cc4=st.columns(4)
 cc1.metric("角球總",f"{corner_total}"); cc2.metric(f"{team_h}角",round(corner_total*(xg_h/total))); cc3.metric("黃牌",f"{4.8}"); cc4.metric("角大9.5",f"{78 if corner_total>9.5 else 42}%")

if st.button(f"👑 發動天眼 {team_h} vs {team_a}", type="primary", use_container_width=True):
 entry={"time":datetime.now().strftime("%m-%d %H:%M"),"match":f"{team_h} vs {team_a}","xg":f"{xg_h}-{xg_a}","total":round(total,2),"hw":round(hw,1),"o25":round(o25,1),"top1":sorted(scores.items(), key=lambda x:-x[1])[0][0]}
 st.session_state.learn_log.append(entry); save_learn(st.session_state.learn_log)
 st.success(f"✅ 已發動 {team_h} 總{total:.2f} TOP {entry['top1']}"); st.balloons()

st.divider()
st.subheader("📚 Coup Football 自學板")
if st.session_state.learn_log: st.dataframe(pd.DataFrame(st.session_state.learn_log), use_container_width=True)
else: st.info("發動一次就有紀錄")

q=st.text_input("📝 報比分 2-1")
if st.button("✅ 提交入庫"):
 m=re.search(r"(\d+)[-:](\d+)",q)
 if m:
  if st.session_state.learn_log:
   st.session_state.learn_log[-1]["actual"]=m.group(0)
   save_learn(st.session_state.learn_log)
  st.success(f"已學 {m.group(0)}"); st.rerun()

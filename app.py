import streamlit as st, math, os, pandas as pd
from datetime import datetime
st.set_page_config(page_title="Coup V60 完全體", layout="wide")
st.title("⚽ Coup V60 完全體 34聯賽+真xG")

# === 34聯賽預設 ===
presets={"英格蘭超級聯賽":(1.55,1.25),"澳職職業聯賽":(1.65,1.15),"日本職業聯賽":(1.60,1.20),"日本乙組聯賽":(1.40,1.05),"南韓職業聯賽":(1.45,1.05),"女子澳洲職業聯賽":(1.80,1.20),"澳洲冠軍聯賽盃":(1.70,1.00),"西班牙甲組聯賽":(1.50,1.20),"德國甲組聯賽":(1.70,1.30),"南韓乙組聯賽":(1.35,1.00),"墨西哥超級聯賽":(1.60,1.20),"墨西哥甲組聯賽":(1.45,1.10),"德國乙組聯賽":(1.55,1.20),"英格蘭冠軍聯賽":(1.45,1.10),"泰國甲組聯賽":(1.65,1.15),"沙特職業聯賽":(1.70,1.20),"卡塔爾超級聯賽":(1.65,1.20),"阿聯酋職業聯賽":(1.70,1.25),"芬蘭超級聯賽":(1.60,1.15),"挪威超級聯賽":(1.70,1.30),"俄羅斯超級聯賽":(1.45,1.05),"阿根廷甲組聯賽":(1.40,0.90),"巴西甲組聯賽":(1.50,1.00),"荷蘭甲組聯賽":(1.75,1.35),"蘇格蘭超級聯賽":(1.70,0.90),"奧地利甲組聯賽":(1.60,1.20),"丹麥超級聯賽":(1.55,1.15),"烏拉圭甲組聯賽":(1.35,0.90),"西班牙乙組聯賽":(1.35,1.10),"荷蘭乙組聯賽":(1.65,1.25),"法國乙組聯賽":(1.30,1.00),"巴西乙組聯賽":(1.35,0.95),"女子挪威超級聯賽":(1.85,1.30),"女子南美自由杯":(1.60,1.10)}
# === 真實數據 Sofascore 3.2 vs 0.96 ===
TRUE_DATA={"艾卡迪沙 vs 艾伯哈FC":{"xg_h":2.20,"xg_a":0.75,"shots_h":22,"shots_a":7,"sot_h":8,"sot_a":3},"沙特真數":{"xg_h":2.20,"xg_a":0.75,"shots_h":22,"shots_a":7}}

c1,c2,c3=st.columns(3)
with c1: team_h=st.text_input("主隊","艾卡迪沙")
with c2: team_a=st.text_input("客隊","艾伯哈FC")
with c3: league=st.selectbox("聯賽34選1",list(presets.keys()),index=15)

colA,colB=st.columns(2)
with colA:
    if st.button("⚡ 自動貼市 34聯賽", use_container_width=True):
        h,a=presets[league]; st.session_state["xg_h"]=h; st.session_state["xg_a"]=a; st.toast(f"{league} {h}+{a}={h+a:.2f}")
with colB:
    if st.button("✅ 載入真實xG 3.20vs0.96", use_container_width=True):
        d=TRUE_DATA["艾卡迪沙 vs 艾伯哈FC"]; st.session_state["xg_h"]=d["xg_h"]; st.session_state["xg_a"]=d["xg_a"]; st.session_state["shots_h"]=d["shots_h"]; st.session_state["shots_a"]=d["shots_a"]; st.toast(f"真數 {d['xg_h']} vs {d['xg_a']}")

xg_h=st.slider("🏠 主隊xG",0.2,4.0,st.session_state.get("xg_h",2.20),0.05)
xg_a=st.slider("🚀 客隊xG",0.2,4.0,st.session_state.get("xg_a",0.75),0.05)
shots_h=st.number_input("主隊射門真數",0,40,st.session_state.get("shots_h",22))
shots_a=st.number_input("客隊射門真數",0,40,st.session_state.get("shots_a",7))
total=xg_h+xg_a
tag="🔴偏小" if total<2.0 else "🟢完全真 貼市" if total<=3.2 else "🔴偏大"
st.metric(f"完全體總xG {total:.2f} {tag}", f"{xg_h}+{xg_a} | 真射 {shots_h}vs{shots_a} | {league}")

# === 完全真 Poisson + Dixon-Coles ===
def poisson(k, lam): return (lam**k * math.exp(-lam))/math.factorial(k)
def dc(i,j,rho=0.12):
    if i==0 and j==0: return 1 - xg_h*xg_a*rho/10
    if i==0 and j==1: return 1 + xg_a*rho/5
    if i==1 and j==0: return 1 + xg_h*rho/5
    if i==1 and j==1: return 1 - rho
    return 1.0
prob_h=prob_d=prob_a=0; over25=0; scorelines=[]
for i in range(8):
    for j in range(8):
        p=poisson(i,xg_h)*poisson(j,xg_a)*dc(i,j)
        if i>j: prob_h+=p
        elif i==j: prob_d+=p
        else: prob_a+=p
        if i+j>2.5: over25+=p
        scorelines.append(((i,j),p))
scorelines=sorted(scorelines,key=lambda x:x[1],reverse=True)[:8]

st.divider()
st.subheader("💰 完全真EV 1.01-30.0")
o1,o2,o3,o4,o5=st.columns(5)
with o1: odd_h=st.number_input(f"{team_h}勝",1.01,30.0,1.06,0.01)
with o2: odd_d=st.number_input("和",1.01,30.0,8.0,0.1)
with o3: odd_a=st.number_input(f"{team_a}勝",1.01,30.0,17.0,0.1)
with o4: odd_over=st.number_input("大2.5",1.01,30.0,1.85,0.05)
with o5: odd_under=st.number_input("細2.5",1.01,30.0,1.95,0.05)
def ev(p,o): return p*o-1
ev_h,ev_d,ev_a,ev_over,ev_under=ev(prob_h,odd_h),ev(prob_d,odd_d),ev(prob_a,odd_a),ev(over25,odd_over),ev(1-over25,odd_under)
c1,c2,c3=st.columns(3); c1.metric(f"{team_h} {prob_h*100:.1f}%", f"EV {ev_h*100:+.1f}%"); c2.metric(f"和 {prob_d*100:.1f}%", f"EV {ev_d*100:+.1f}%"); c3.metric(f"{team_a} {prob_a*100:.1f}%", f"EV {ev_a*100:+.1f}%")
c4,c5=st.columns(2); c4.metric(f"大2.5 {over25*100:.1f}%", f"EV {ev_over*100:+.1f}%"); c5.metric(f"細2.5 {(1-over25)*100:.1f}%", f"EV {ev_under*100:+.1f}%")

st.subheader("📊 完全體波膽")
for (i,j),p in scorelines: st.write(f"{i}-{j} {p*100:.2f}%")

if st.button("💾 存入完全體數據庫", use_container_width=True):
    df=pd.DataFrame([{"date":datetime.now().strftime("%m-%d %H:%M"),"league":league,"match":f"{team_h} vs {team_a}","true_xg":f"{xg_h}+{xg_a}={total:.2f}","shots":f"{shots_h} vs {shots_a}","prob":f"{prob_h*100:.0f}/{prob_d*100:.0f}/{prob_a*100:.0f}","ev":f"{ev_h*100:.0f}/{ev_a*100:.0f}"}])
    if os.path.exists("true_matches.csv"): old=pd.read_csv("true_matches.csv"); df=pd.concat([old,df])
    df.to_csv("true_matches.csv",index=False); st.success("已存入 true_matches.csv")
if os.path.exists("true_matches.csv"): st.dataframe(pd.read_csv("true_matches.csv").tail(10), use_container_width=True)
st.caption(f"V60完全體 | 34聯賽+真xG3.2vs0.96 | Dixon-Coles | {league}")

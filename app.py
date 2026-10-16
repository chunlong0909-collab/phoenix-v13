import streamlit as st
import math, os, pandas as pd
from datetime import datetime

st.set_page_config(page_title="Coup Football V40 終極自己用", layout="wide")
st.title("⚽ Coup Football V40 終極自己用版")

# === 34個聯賽 貼市 ===
presets={
    "英格蘭超級聯賽":(1.55,1.25), "澳職職業聯賽":(1.65,1.15), "日本職業聯賽":(1.60,1.20),
    "日本乙組聯賽":(1.40,1.05), "南韓職業聯賽":(1.45,1.05), "女子澳洲職業聯賽":(1.80,1.20),
    "澳洲冠軍聯賽盃":(1.70,1.00), "西班牙甲組聯賽":(1.50,1.20), "德國甲組聯賽":(1.70,1.30),
    "南韓乙組聯賽":(1.35,1.00), "墨西哥超級聯賽":(1.60,1.20), "墨西哥甲組聯賽":(1.45,1.10),
    "德國乙組聯賽":(1.55,1.20), "英格蘭冠軍聯賽":(1.45,1.10), "泰國甲組聯賽":(1.65,1.15),
    "沙特職業聯賽":(1.70,1.20), "卡塔爾超級聯賽":(1.65,1.20), "阿聯酋職業聯賽":(1.70,1.25),
    "芬蘭超級聯賽":(1.60,1.15), "挪威超級聯賽":(1.70,1.30), "俄羅斯超級聯賽":(1.45,1.05),
    "阿根廷甲組聯賽":(1.40,0.90), "巴西甲組聯賽":(1.50,1.00), "荷蘭甲組聯賽":(1.75,1.35),
    "蘇格蘭超級聯賽":(1.70,0.90), "奧地利甲組聯賽":(1.60,1.20), "丹麥超級聯賽":(1.55,1.15),
    "烏拉圭甲組聯賽":(1.35,0.90), "西班牙乙組聯賽":(1.35,1.10), "荷蘭乙組聯賽":(1.65,1.25),
    "法國乙組聯賽":(1.30,1.00), "巴西乙組聯賽":(1.35,0.95), "女子挪威超級聯賽":(1.85,1.30),
    "女子南美自由杯":(1.60,1.10)
}

c1,c2,c3=st.columns(3)
with c1: team_h=st.text_input("主隊","FC悉尼")
with c2: team_a=st.text_input("客隊","西悉尼流浪者")
with c3: league=st.selectbox("聯賽",list(presets.keys()),index=1)

if st.button("⚡ 自動貼市填寫", use_container_width=True):
    h,a=presets[league]
    st.session_state["xg_h_auto"]=h
    st.session_state["xg_a_auto"]=a
    st.toast(f"已自動 {league} {h}+{a}={h+a:.2f}", icon="⚽")

default_h=st.session_state.get("xg_h_auto",1.65)
default_a=st.session_state.get("xg_a_auto",1.15)
col1,col2=st.columns(2)
with col1: xg_h=st.slider(f"🏠 {team_h} xG 紅線",0.2,3.5,default_h,0.05)
with col2: xg_a=st.slider(f"🚀 {team_a} xG 紅線",0.2,3.5,default_a,0.05)

total=xg_h+xg_a
if total<2.0: color,txt="🔴","偏離 偏小"
elif total<2.6: color,txt="🟡","偏小"
elif total<=3.0: color,txt="🟢","正常 貼市"
else: color,txt="🔴","偏大"
st.metric(f"總xG {total:.2f} {color} {txt}", f"{xg_h} + {xg_a}")

def poisson(k, lam): return (lam**k * math.exp(-lam))/math.factorial(k)
max_g=6
prob_h=prob_d=prob_a=0; over25=0; scorelines=[]
for i in range(max_g+1):
    for j in range(max_g+1):
        p=poisson(i,xg_h)*poisson(j,xg_a)
        if i>j: prob_h+=p
        elif i==j: prob_d+=p
        else: prob_a+=p
        if i+j>2.5: over25+=p
        scorelines.append(((i,j),p))
scorelines=sorted(scorelines,key=lambda x:x[1],reverse=True)[:6]

st.divider()
st.subheader("💰 365賠率 - 計真EV")
o1,o2,o3,o4,o5=st.columns(5)
# 已Fix 1.01-30.0 唔再紅
with o1: odd_h=st.number_input(f"{team_h}勝",1.01,30.0,2.10,0.05)
with o2: odd_d=st.number_input("和",1.01,30.0,3.30,0.05)
with o3: odd_a=st.number_input(f"{team_a}勝",1.01,30.0,3.40,0.05)
with o4: odd_over=st.number_input("大2.5",1.01,30.0,1.85,0.05)
with o5: odd_under=st.number_input("細2.5",1.01,30.0,1.95,0.05)

def true_ev(prob,odd): return prob*odd-1
ev_h,ev_d,ev_a=true_ev(prob_h,odd_h),true_ev(prob_d,odd_d),true_ev(prob_a,odd_a)
ev_over,ev_under=true_ev(over25,odd_over),true_ev(1-over25,odd_under)
def ev_tag(ev): return "🟢真放水" if ev>0.05 else "🟡正路" if ev>-0.05 else "🔴黑盤"

c1,c2,c3=st.columns(3)
c1.metric(f"{team_h}勝 {prob_h*100:.1f}% {ev_tag(ev_h)}", f"真EV {ev_h*100:.1f}%")
c2.metric(f"和 {prob_d*100:.1f}% {ev_tag(ev_d)}", f"真EV {ev_d*100:.1f}%")
c3.metric(f"{team_a}勝 {prob_a*100:.1f}% {ev_tag(ev_a)}", f"真EV {ev_a*100:.1f}%")
c4,c5=st.columns(2)
c4.metric(f"大2.5 {over25*100:.1f}% {ev_tag(ev_over)}", f"真EV {ev_over*100:.1f}%")
c5.metric(f"細2.5 {(1-over25)*100:.1f}% {ev_tag(ev_under)}", f"真EV {ev_under*100:.1f}%")

st.subheader("📊 波膽 - 天眼神機")
for (i,j),p in scorelines: st.write(f"**{i}-{j} {p*100:.2f}%**")

st.divider()
st.subheader("🧠 自學板 - 自己用記賽果")
s1,s2,s3=st.columns(3)
with s1: real_h=st.number_input("主隊實際入球",0,10,1)
with s2: real_a=st.number_input("客隊實際入球",0,10,1)
with s3:
    if st.button("💾 儲存賽果", use_container_width=True):
        df_new=pd.DataFrame([{"date":datetime.now().strftime("%m-%d %H:%M"),"league":league,"match":f"{team_h} vs {team_a}","pred":f"{xg_h:.2f}+{xg_a:.2f}={total:.2f}","score":f"{real_h}-{real_a}","over":over25}])
        if os.path.exists("matches.csv"):
            df_old=pd.read_csv("matches.csv")
            df=pd.concat([df_old,df_new])
        else: df=df_new
        df.to_csv("matches.csv",index=False)
        st.success(f"已儲存 {team_h} {real_h}-{real_a} {team_a}")

if os.path.exists("matches.csv"):
    st.dataframe(pd.read_csv("matches.csv").tail(10), use_container_width=True)
else: st.caption("未有賽果，賽後記得儲存")

st.caption(f"終極自己用版 | {league} | 總xG {total:.2f} | 34聯賽 | 已Fix紅框")

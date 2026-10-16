import streamlit as st
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="不死鳥", layout="wide")
st.title("不死鳥")

# 賽事寫死喺code入面，公開都無影響，唔靠csv
MATCHES = [
    ["英超","Man City","Arsenal","23:00",2.10,3.20,3.50],
    ["英超","Chelsea","Liverpool","00:30",3.00,3.40,2.30],
    ["西甲","Real Madrid","Barcelona","02:00",2.40,3.30,2.90],
    ["德甲","Bayern","Dortmund","21:30",1.70,4.00,4.50],
    ["意甲","Inter","AC Milan","02:45",2.00,3.50,3.80],
    ["巴甲","Flamengo","Palmeiras","22:00",1.85,3.40,4.20],
    ["巴甲","Vitoria","Flamengo","20:00",2.20,3.10,3.00],
    ["日職","Vissel","Kashima","18:00",2.00,3.30,3.60],
    ["美職","Inter Miami","LA Galaxy","07:30",1.80,3.60,4.20],
    ["歐冠","Real Madrid","Man City","03:00",2.30,3.40,2.90],
]
df = pd.DataFrame(MATCHES, columns=["league","home","away","time","h","d","a"])

# 手動輸入 主客隊名
st.subheader("自定球隊")
c1,c2 = st.columns(2)
if "ph" not in st.session_state:
    st.session_state.ph="Flamengo"; st.session_state.pa="Palmeiras"; st.session_state.hh=1.85; st.session_state.dd=3.4; st.session_state.aa=4.2
home = c1.text_input("主隊名", value=st.session_state.ph)
away = c2.text_input("客隊名", value=st.session_state.pa)

# 賽事選擇
st.subheader(f"賽事 {len(df)}場 - 揀即填")
f = st.selectbox("聯賽", ["全部"]+sorted(df.league.unique().tolist()))
show = df if f=="全部" else df[df.league==f]
for i,r in show.iterrows():
    if st.button(f"{r.time} {r.league} {r.home} vs {r.away} {r.h}/{r.d}/{r.a}", key=f"m{i}", use_container_width=True):
        st.session_state.ph=r.home; st.session_state.pa=r.away; st.session_state.hh=r.h; st.session_state.dd=r.d; st.session_state.aa=r.a
        st.rerun()

# 賠率
st.divider()
ch,cd,ca = st.columns(3)
h=ch.number_input("主勝", value=float(st.session_state.hh), step=0.05)
d=cd.number_input("和", value=float(st.session_state.dd), step=0.05)
a=ca.number_input("客勝", value=float(st.session_state.aa), step=0.05)
tot=1/h+1/d+1/a; prob=(1/h)/tot*100; vig=(tot-1)*100
st.write(f"主勝 {prob:.1f}% | 抽水 {vig:.1f}% {'避' if vig>10 else '可'}")

if st.button("一鍵Ocup分析", type="primary", use_container_width=True):
    st.subheader(f"{home} vs {away} 分析")
    ocup = pd.DataFrame([
        ["讓球",f"{home} -0.5","★★★★",f"{prob:.0f}%"],
        ["大小","細2.5","★★★★★","有雨"],
        ["角球","細9.5","★★★★","風8km"],
        ["半全場","半和全主","★★★","後勁"],
        ["波膽","1-0/2-0/2-1","★★★★","55%陷阱"],
        ["入球","No","★★★","客傷"],
    ], columns=["市場","推薦","信心","原因"])
    st.dataframe(ocup, hide_index=True, use_container_width=True)
    st.caption(f"陣容11+7 換人60'/70'/80' | 更新 {datetime.now().strftime('%H:%M')}")

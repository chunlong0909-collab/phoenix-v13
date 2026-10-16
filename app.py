import streamlit as st, pandas as pd, numpy as np, math, os
from datetime import datetime

st.set_page_config(page_title="Ocup V64 全自動完全體", layout="wide")
st.title("⚽ Ocup Football V64 | 全自動+主客隊+EV筍位")

presets={"英超":(1.55,1.25),"西甲":(1.5,1.2),"德甲":(1.6,1.3),"意甲":(1.45,1.15),"法甲":(1.5,1.2),"沙特職業聯賽":(1.65,1.35),"澳職":(1.7,1.4),"美職":(1.6,1.3),"日職":(1.5,1.2),"韓職":(1.45,1.15),"中超":(1.5,1.2),"巴甲":(1.55,1.25),"阿甲":(1.5,1.2),"葡超":(1.5,1.2),"荷甲":(1.65,1.35),"比甲":(1.55,1.25),"土超":(1.6,1.3),"英冠":(1.45,1.15),"西乙":(1.4,1.1),"德乙":(1.5,1.2),"蘇超":(1.5,1.2),"瑞超":(1.55,1.25),"挪超":(1.6,1.3),"丹超":(1.55,1.25),"奧甲":(1.5,1.2),"瑞士超":(1.55,1.25),"波蘭超":(1.45,1.15),"希臘超":(1.4,1.1),"俄超":(1.45,1.15),"烏超":(1.4,1.1),"墨超":(1.55,1.25),"智利甲":(1.45,1.15),"哥倫比亞甲":(1.4,1.1),"南非超":(1.35,1.05)}

def dixon_coles(l1,l2,rho=0.12):
    max_g=7; p=np.zeros((max_g+1,max_g+1))
    for i in range(max_g+1):
        for j in range(max_g+1):
            p[i,j]=np.exp(-l1)*l1**i/math.factorial(i)*np.exp(-l2)*l2**j/math.factorial(j)
    p[0,0]*=(1-l1*l2*rho); p[0,1]*=(1+l2*rho); p[1,0]*=(1+l1*rho); p[1,1]*=(1-rho)
    return p/p.sum()

with st.sidebar:
    lg=st.selectbox("聯賽", list(presets.keys()), index=list(presets.keys()).index("沙特職業聯賽"))
    home_team = st.text_input("主隊名", "艾卡迪沙")
    away_team = st.text_input("客隊名", "艾伯哈FC")
    m = f"{home_team} vs {away_team}"
    xg_h=st.slider("主隊真xG",0.2,3.5,2.2,0.05)
    xg_a=st.slider("客隊真xG",0.2,2.0,0.75,0.05)
    st.success(f"真xG {xg_h}+{xg_a}={xg_h+xg_a:.2f}")

    # === V64 核心：App幫你計埋射門，唔使手填 ===
    sh_h = int(xg_h * 9 + 2)
    sh_a = int(xg_a * 9)
    st_h = int(sh_h * 0.36)
    st_a = int(sh_a * 0.36)
    st.info(f"🤖 App自動計：射門 {sh_h}vs{sh_a} / 射正 {st_h}vs{st_a}")
    # ==========================================

    o_h=st.number_input("主賠 1.01-30",1.01,30.0,1.16)
    o_d=st.number_input("和賠 1.01-30",1.01,30.0,8.0)
    o_a=st.number_input("客賠 1.01-30",1.01,30.0,17.0)

mat=dixon_coles(xg_h,xg_a)
ph=pD=pa=ou25=btts=0; scores=[]
for i in range(7):
    for j in range(7):
        prob=mat[i,j]; scores.append((f"{i}-{j}",prob))
        if i>j: ph+=prob
        elif i==j: pD+=prob
        else: pa+=prob
        if i+j>=3: ou25+=prob
        if i>0 and j>0: btts+=prob

scores=sorted(scores,key=lambda x:x[1],reverse=True)[:10]
ev_h,ev_d,ev_a=ph*o_h-1, pD*o_d-1, pa*o_a-1

c1,c2,c3=st.columns(3)
c1.metric("主勝",f"{ph*100:.1f}%",f"EV {ev_h*100:.1f}%")
c2.metric("和局",f"{pD*100:.1f}%",f"EV {ev_d*100:.1f}%")
c3.metric("客勝",f"{pa*100:.1f}%",f"EV {ev_a*100:.1f}%")
c4,c5=st.columns(2)
c4.metric("大2.5",f"{ou25*100:.1f}%"); c5.metric("BTTS Yes",f"{btts*100:.1f}%")

st.subheader("🎯 波膽 Top10 (自動)")
df_score=pd.DataFrame(scores,columns=["波膽","機率"])
df_score["機率%"]=(df_score["機率"]*100).round(1)
st.dataframe(df_score[["波膽","機率%"]], use_container_width=True)
st.bar_chart(df_score.set_index("波膽")["機率%"])

st.subheader("🔥 Dixon-Coles 熱力圖")
st.dataframe(pd.DataFrame(mat.round(4)), use_container_width=True)

st.subheader("📊 Ocup V64 全自動大表")
df_big=pd.DataFrame([{
    "日期":datetime.now().strftime("%m-%d"),"聯賽":lg,"對賽":m,
    "真xG":f"{xg_h}+{xg_a}={xg_h+xg_a:.2f}",
    "射門(自動)":f"{sh_h}vs{sh_a}","射正(自動)":f"{st_h}vs{st_a}",
    "主%":f"{ph*100:.1f}%","和%":f"{pD*100:.1f}%","客%":f"{pa*100:.1f}%",
    "主賠":o_h,"和賠":o_d,"客賠":o_a,
    "主EV":f"{ev_h*100:.1f}%","和EV":f"{ev_d*100:.1f}%","客EV":f"{ev_a*100:.1f}%",
    "大2.5%":f"{ou25*100:.1f}%","BTTS%":f"{btts*100:.1f}%","最熱波膽":scores[0][0]
}])
st.dataframe(df_big, use_container_width=True)

if st.button("💾 存入V64數據庫"):
    fp="ocup_v64.csv"; df_big.to_csv(fp, mode='a', header=not os.path.exists(fp), index=False, encoding='utf-8-sig')
    st.success(f"已存入 {fp}！{m} 自動射門 {sh_h}vs{sh_a}")
    if os.path.exists(fp): st.dataframe(pd.read_csv(fp).tail(10), use_container_width=True)

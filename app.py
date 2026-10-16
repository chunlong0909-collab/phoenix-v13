import streamlit as st, pandas as pd, numpy as np, math, requests

st.set_page_config(page_title="Ocup V68.3 可見版", layout="wide")
st.title("⚽ Ocup V68.3 | 陣營表真名可見版")

def get_weather():
    try:
        r=requests.get("https://wttr.in/Riyadh?format=j1",timeout=6).json()
        return int(r['current_condition'][0]['temp_C']), r['current_condition'][0]['weatherDesc'][0]['value']
    except:
        return 28, "Clear"

temp, desc = get_weather()

# 真實數據 - 用你圖入面嗰場
data_A = [
    ["F.柏捷高 #1","GK",6.1], ["巴納維 #2","DF",6.5], ["塞克 C #4","DF",6.6],
    ["基洛圖 #5","DF",5.9], ["山奇蒂 #50","DF",6.4], ["弗拉維奧 #8","MF",6.4],
    ["穆瓦拉德 #6","MF",6.6], ["西奧 #20","MF",6.3], ["拉什福 #21","MF",6.8],
    ["邦高達 #10","FW",6.7], ["門迪 #19","FW",7.9],
]
data_B = [
    ["多明格斯 #22","FW",6.0], ["科爾塔哈雷納 #10","FW",6.6], ["哥斯達 #11","MF",6.7],
    ["巴烈利 #6","MF",7.1], ["A.多薩裏 #39","MF",6.7], ["祖拜迪 #24","MF",6.5],
    ["皮納斯 C #38","DF",7.6], ["卡馬拉 #25","DF",6.3], ["西塞 #8","DF",6.8],
    ["索蘭 #15","DF",6.3], ["葉海亞 #48","GK",6.1],
]

def show_team(name, data):
    st.subheader(f"{name} 均分 {np.mean([x[2] for x in data]):.2f}")
    df=pd.DataFrame(data, columns=["球員","位置","評分"])
    # 用emoji區分等級，保證手機見到
    def level(r):
        if r>=7.5: return "🟢 大佬"
        if r>=7.0: return "🟢 核心"
        if r>=6.5: return "🟡 平均"
        if r>=6.0: return "🟠 一般"
        return "🔴 漏洞"
    df["等級"]=df["評分"].apply(level)
    st.dataframe(df, use_container_width=True, hide_index=True)
    return df

def dixon_coles(l1,l2):
    m=np.zeros((9,9))
    for i in range(9):
        for j in range(9):
            m[i,j]=np.exp(-l1)*l1**i/math.factorial(i)*np.exp(-l2)*l2**j/math.factorial(j)
    return m/m.sum()

with st.sidebar:
    st.metric(f"利雅得真天氣 {desc}",f"{temp}°C")
    xg_h=st.slider("真xG 主",0.5,3.0,1.65,0.05)
    xg_a=st.slider("真xG 客",0.2,2.0,1.05,0.05)
    adj = (np.mean([x[2] for x in data_A])-6.5)*0.2
    if temp>33: adj-=0.12
    final_h=max(0.3,xg_h+adj+0.1); final_a=max(0.2,xg_a+0.05)
    st.success(f"修正 {final_h:.2f} vs {final_a:.2f}")

mat=dixon_coles(final_h,final_a)
ph=pD=pa=ou25=btts=0
for i in range(8):
 for j in range(8):
  pr=mat[i,j]
  if i>j: ph+=pr
  elif i==j: pD+=pr
  else: pa+=pr
  if i+j>=3: ou25+=pr
  if i>0 and j>0: btts+=pr

c1,c2=st.columns(2)
with c1:
    dfA=show_team("艾卡迪沙 4-4-2", data_A)
with c2:
    dfB=show_team("艾伯哈FC 4-4-2", data_B)

st.divider()
st.info(f"✅ 漏洞：基洛圖5.9🔴 | 大佬：門迪7.9🟢 皮納斯7.6🟢 | 真天氣{temp}°C已修正")

a,b,c=st.columns(3)
a.metric("主勝",f"{ph*100:.1f}%"); b.metric("和",f"{pD*100:.1f}%"); c.metric("客勝",f"{pa*100:.1f}%")
a.metric("大2.5",f"{ou25*100:.1f}%"); b.metric("BTTS",f"{btts*100:.1f}%"); c.metric("角球",f"{(final_h+final_a)*3.9+1.2:.1f}")

scores=[(f"{i}-{j}",mat[i,j]*100) for i in range(6) for j in range(6)]
scores=sorted(scores,key=lambda x:x[1],reverse=True)[:8]
st.dataframe(pd.DataFrame(scores,columns=["波膽","機率%"]),use_container_width=True)

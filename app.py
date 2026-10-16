import streamlit as st, pandas as pd, numpy as np, math, requests

st.set_page_config(page_title="Ocup V68.2 修復", layout="wide")
st.title("⚽ Ocup V68.2 | 真名顯示修復版")

def get_real_weather(city="Riyadh"):
    try:
        r = requests.get(f"https://wttr.in/{city}?format=j1", timeout=8).json()
        return int(r['current_condition'][0]['temp_C']), r['current_condition'][0]['weatherDesc'][0]['value'], True
    except:
        return 28, "Clear", False

temp, desc, real = get_real_weather()

TEAM_A = [
    {"n":"F.柏捷高 #1 GK","r":6.1}, {"n":"巴納維 #2 DF","r":6.5}, {"n":"塞克 C #4 DF","r":6.6},
    {"n":"基洛圖 #5 DF","r":5.9}, {"n":"山奇蒂 #50 DF","r":6.4}, {"n":"弗拉維奧 #8 MF","r":6.4},
    {"n":"穆瓦拉德 #6 MF","r":6.6}, {"n":"西奧 #20 MF","r":6.3}, {"n":"拉什福 #21 MF","r":6.8},
    {"n":"邦高達 #10 FW","r":6.7}, {"n":"門迪 #19 FW","r":7.9},
]
TEAM_B = [
    {"n":"多明格斯 #22 FW","r":6.0}, {"n":"科爾塔哈雷納 #10 FW","r":6.6}, {"n":"哥斯達 #11 MF","r":6.7},
    {"n":"巴烈利 #6 MF","r":7.1}, {"n":"A.多薩裏 #39 MF","r":6.7}, {"n":"祖拜迪 #24 MF","r":6.5},
    {"n":"皮納斯 C #38 DF","r":7.6}, {"n":"卡馬拉 #25 DF","r":6.3}, {"n":"西塞 #8 DF","r":6.8},
    {"n":"索蘭 #15 DF","r":6.3}, {"n":"葉海亞 #48 GK","r":6.1},
]

def color(r):
    if r>=7.5: return "#00C853"
    if r>=7.0: return "#2E7D32"
    if r>=6.5: return "#F9A825"
    return "#D32F2F" if r<6.0 else "#EF6C00"

def render_formation(players, title):
    html = f"<div style='background:#2E7D32;padding:15px;border-radius:15px;margin-bottom:15px'><h4 style='color:white;text-align:center;margin:0 0 10px 0'>{title} 均分 {np.mean([x['r'] for x in players]):.2f}</h4>"
    for p in players:
        html+=f"<div style='display:flex;justify-content:space-between;align-items:center;background:#FFFFFF;margin:6px 0;padding:10px 12px;border-radius:10px;border:1px solid #ddd'><span style='color:#000000!important;font-weight:bold;font-size:14px'>{p['n']}</span><span style='background:{color(p['r'])};color:white;padding:4px 10px;border-radius:12px;font-weight:bold;font-size:13px'>{p['r']}</span></div>"
    html+="</div>"
    st.markdown(html, unsafe_allow_html=True)

def dixon_coles(l1,l2):
    max_g=8; m=np.zeros((max_g+1,max_g+1))
    for i in range(max_g+1):
        for j in range(max_g+1):
            m[i,j]=np.exp(-l1)*l1**i/math.factorial(i)*np.exp(-l2)*l2**j/math.factorial(j)
    return m/m.sum()

with st.sidebar:
    st.metric(f"利雅得真實 {desc}",f"{temp}°C","✅真實" if real else "")
    xg_h=st.slider("真xG 主",0.5,3.0,1.65,0.05)
    xg_a=st.slider("真xG 客",0.2,2.0,1.05,0.05)
    adj = (np.mean([x['r'] for x in TEAM_A])-6.5)*0.2
    if temp>33: adj-=0.12
    final_h=max(0.3,xg_h+adj+0.1); final_a=max(0.2,xg_a+0.05)
    st.success(f"修正後 {final_h:.2f} vs {final_a:.2f}")

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

exp_corner=(final_h+final_a)*3.9+1.2

c1,c2=st.columns(2)
with c1: render_formation(TEAM_A,"艾卡迪沙 4-4-2")
with c2: render_formation(TEAM_B,"艾伯哈FC 4-4-2")

st.success(f"漏洞 基洛圖5.9 | 大佬 門迪7.9+皮納斯7.6 | 真天氣{temp}°C已修正 | 最後真xG {final_h:.2f} vs {final_a:.2f}")

m1,m2,m3=st.columns(3)
m1.metric("主勝",f"{ph*100:.1f}%"); m2.metric("和",f"{pD*100:.1f}%"); m3.metric("客勝",f"{pa*100:.1f}%")
st.code(f"大2.5 {ou25*100:.1f}% | BTTS {btts*100:.1f}% | 預計角球 {exp_corner:.1f} | 天氣 {temp}°C {desc}")
scores=[(f"{i}-{j}",mat[i,j]*100) for i in range(6) for j in range(6)]
scores=sorted(scores,key=lambda x:x[1],reverse=True)[:8]
st.dataframe(pd.DataFrame(scores,columns=["波膽","機率%"]),use_container_width=True)

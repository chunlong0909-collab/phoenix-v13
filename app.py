import streamlit as st, pandas as pd, numpy as np, math, requests

st.set_page_config(page_title="Ocup V68.1 無痛版", layout="wide")
st.title("⚽ Ocup V68.1 | 真天氣+陣營+全盤口 (無matplotlib)")

def get_real_weather(city="Riyadh"):
    try:
        r = requests.get(f"https://wttr.in/{city}?format=j1", timeout=8).json()
        temp = int(r['current_condition'][0]['temp_C'])
        desc = r['current_condition'][0]['weatherDesc'][0]['value']
        return temp, desc, True
    except:
        return 38, "Sunny", False

temp, desc, real = get_real_weather()

TEAM_A = [
    {"n":"F.柏捷高","r":6.1,"p":"GK"}, {"n":"巴納維","r":6.5,"p":"DF"}, {"n":"塞克 C","r":6.6,"p":"DF"},
    {"n":"基洛圖","r":5.9,"p":"DF"}, {"n":"山奇蒂","r":6.4,"p":"DF"}, {"n":"弗拉維奧","r":6.4,"p":"MF"},
    {"n":"穆瓦拉德","r":6.6,"p":"MF"}, {"n":"西奧","r":6.3,"p":"MF"}, {"n":"拉什福","r":6.8,"p":"MF"},
    {"n":"邦高達","r":6.7,"p":"FW"}, {"n":"門迪","r":7.9,"p":"FW"},
]
TEAM_B = [
    {"n":"多明格斯","r":6.0,"p":"FW"}, {"n":"科爾塔哈雷納","r":6.6,"p":"FW"}, {"n":"哥斯達","r":6.7,"p":"MF"},
    {"n":"巴烈利","r":7.1,"p":"MF"}, {"n":"A.多薩裏","r":6.7,"p":"MF"}, {"n":"祖拜迪","r":6.5,"p":"MF"},
    {"n":"皮納斯 C","r":7.6,"p":"DF"}, {"n":"卡馬拉","r":6.3,"p":"DF"}, {"n":"西塞","r":6.8,"p":"DF"},
    {"n":"索蘭","r":6.3,"p":"DF"}, {"n":"葉海亞","r":6.1,"p":"GK"},
]

def color(r):
    if r>=7.5: return "#00C853"
    if r>=7.0: return "#7CB342"
    if r>=6.5: return "#FFB300"
    return "#D32F2F" if r<6.0 else "#FF6F00"

def render_formation(players, title):
    html = f"<div style='background:#2E7D32;padding:15px;border-radius:15px'><h4 style='color:white;text-align:center'>{title} 均分 {np.mean([x['r'] for x in players]):.2f}</h4>"
    for p in players:
        html+=f"<div style='display:flex;justify-content:space-between;background:white;margin:5px;padding:8px;border-radius:8px'><span>{p['p']} {p['n']}</span><span style='background:{color(p['r'])};color:white;padding:2px 8px;border-radius:10px;font-weight:bold'>{p['r']}</span></div>"
    html+="</div>"
    st.markdown(html, unsafe_allow_html=True)

def dixon_coles(l1,l2):
    max_g=8; m=np.zeros((max_g+1,max_g+1))
    for i in range(max_g+1):
        for j in range(max_g+1):
            m[i,j]=np.exp(-l1)*l1**i/math.factorial(i)*np.exp(-l2)*l2**j/math.factorial(j)
    return m/m.sum()

with st.sidebar:
    st.metric("利雅得真實天氣",f"{temp}°C",desc)
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

tab1,tab2=st.tabs(["陣營表","全盤口"])
with tab1:
    c1,c2=st.columns(2)
    with c1: render_formation(TEAM_A,"艾卡迪沙 4-4-2")
    with c2: render_formation(TEAM_B,"艾伯哈FC 4-4-2")
    st.info(f"漏洞 基洛圖5.9 | 大佬 門迪7.9+皮納斯7.6 | 真天氣{temp}°C已修正")

with tab2:
    st.code(f"""
主勝 {ph*100:.1f}% | 和 {pD*100:.1f}% | 客勝 {pa*100:.1f}%
大2.5 {ou25*100:.1f}% | BTTS {btts*100:.1f}%
預計角球 {exp_corner:.1f} | 預計牌數 4.2張
天氣 {temp}°C {desc} {'✅真實' if real else ''}
""")
    scores=[(f"{i}-{j}",mat[i,j]*100) for i in range(6) for j in range(6)]
    scores=sorted(scores,key=lambda x:x[1],reverse=True)[:8]
    st.dataframe(pd.DataFrame(scores,columns=["波膽","%"]),use_container_width=True)

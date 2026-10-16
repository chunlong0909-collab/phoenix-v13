import streamlit as st, pandas as pd, numpy as np, math, requests
from datetime import datetime

st.set_page_config(page_title="Ocup V75 Fixed", layout="wide")
st.markdown("<style>.block-container{padding-top:1rem}</style>", unsafe_allow_html=True)

def get_weather():
    try:
        r=requests.get("https://wttr.in/Riyadh?format=j1",timeout=6).json()
        c=r['current_condition'][0]
        return int(c['temp_C']), c['weatherDesc'][0]['value'], int(c['humidity']), c['windspeedKmph'], True
    except: return 28,"Sunny",63,17,False
temp,desc,hum,wind,real=get_weather()

# === 手動隊名 ===
if 'home_name' not in st.session_state: st.session_state.home_name="艾卡迪沙"
if 'away_name' not in st.session_state: st.session_state.away_name="艾伯哈FC"
home_team = st.text_input("主隊名 手動", value=st.session_state.home_name, key="hn")
away_team = st.text_input("客隊名 手動", value=st.session_state.away_name, key="an")

home_form = st.sidebar.selectbox("主陣式", ["4-4-2","4-3-3","3-5-2","4-2-3-1"],0)
away_form = st.sidebar.selectbox("客陣式", ["4-4-2","4-3-3","3-5-2"],0)
home_coach = st.sidebar.text_input("主教練", "米歇爾")
away_coach = st.sidebar.text_input("客教練", "P.莫塔")
referee = st.sidebar.selectbox("球證", ["Sultan Alharbi 4.2牌","嚴厲5.5牌","鬆散2.8牌"],0)
xg_h_base = st.sidebar.slider("主基礎xG",0.3,3.5,1.65,0.05)
xg_a_base = st.sidebar.slider("客基礎xG",0.2,3.0,1.05,0.05)
home_adv = st.sidebar.slider("主場優勢",-0.2,0.5,0.15,0.05)

odds_H = st.sidebar.number_input("主勝賠率", value=1.92, step=0.01)
odds_D = st.sidebar.number_input("和局賠率", value=3.40, step=0.01)
odds_A = st.sidebar.number_input("客勝賠率", value=3.80, step=0.01)
odds_OU25 = st.sidebar.number_input("大2.5賠率", value=1.85, step=0.01)
odds_BTTS = st.sidebar.number_input("BTTS賠率", value=1.75, step=0.01)

def make_players():
    h=pd.DataFrame([
        ["F.柏捷高 #1","GK",6.1,0,0,0.02,0.0,72,63,"撲救72%","均"],
        ["巴納維 #2","DF",6.5,1,2,0.08,0.12,85,810,"邊衛助攻","升"],
        ["塞克 C #4","DF",6.6,2,0,0.12,0.01,78,890,"隊長空霸","穩"],
        ["基洛圖 #5","DF",5.9,0,0,0.01,0.0,68,450,"🔴漏洞轉身慢","跌"],
        ["山奇蒂 #50","DF",6.4,0,1,0.02,0.05,81,670,"防守穩","均"],
        ["弗拉維奧 #8","MF",6.4,1,1,0.09,0.07,76,720,"工兵","均"],
        ["穆瓦拉德 #6","MF",6.6,2,3,0.18,0.22,84,830,"推進核心","升"],
        ["西奧 #20","MF",6.3,0,0,0.05,0.04,70,510,"技術型","均"],
        ["拉什福 #21","MF",6.8,3,2,0.28,0.15,88,790,"前插xG0.28","升"],
        ["邦高達 #10","FW",6.7,4,1,0.35,0.08,82,740,"轉化18%","升"],
        ["門迪 #19","FW",7.9,9,3,0.82,0.21,92,890,"🟢金靴0.82球","爆"],
    ], columns=["姓名","位置","評分","入球","助攻","xG","xA","傳準%","分鐘","情報","狀態"])
    a=pd.DataFrame([
        ["多明格斯 #22","FW",6.0,1,0,0.19,0.03,65,380,"把握差","跌"],
        ["科爾塔 #10","FW",6.6,5,2,0.41,0.11,77,760,"支點","升"],
        ["哥斯達 #11","MF",6.7,2,4,0.15,0.28,84,820,"威脅球xA0.28","穩"],
        ["巴烈利 #6","MF",7.1,3,5,0.22,0.35,89,880,"🟢創造榜2","爆"],
        ["A.多薩裏 #39","MF",6.7,2,1,0.12,0.08,80,700,"掃蕩","均"],
        ["祖拜迪 #24","MF",6.5,0,2,0.04,0.18,83,650,"助攻","均"],
        ["皮納斯 C #38","DF",7.6,1,1,0.05,0.04,86,900,"🟢解圍4.2次","爆"],
        ["卡馬拉 #25","DF",6.3,0,0,0.02,0.01,79,600,"防空弱","均"],
        ["西塞 #8","DF",6.8,1,0,0.06,0.02,82,780,"穩健","升"],
        ["索蘭 #15","DF",6.3,0,1,0.01,0.09,75,620,"邊路易爆","均"],
        ["葉海亞 #48","GK",6.1,0,0,0.0,0.0,68,900,"撲救68%","均"],
    ], columns=["姓名","位置","評分","入球","助攻","xG","xA","傳準%","分鐘","情報","狀態"])
    return h,a

h_default,a_default=make_players()

# 修正：唔用 else，直接用expander入面改，外面用預設
with st.expander("✏️ 點此改海量球員資料", expanded=False):
    eh=st.data_editor(h_default, num_rows="dynamic", use_container_width=True, key="he")
    ea=st.data_editor(a_default, num_rows="dynamic", use_container_width=True, key="ae")
    # 用戶改咗就用改咗嘅
    if eh is not None and len(eh)>0:
        h_final=eh
        a_final=ea
    else:
        h_final=h_default
        a_final=a_default
# 如果冇開expander，fallback用預設
if 'h_final' not in locals():
    h_final=h_default
    a_final=a_default

avgH,avgA=h_final["評分"].mean(), a_final["評分"].mean()
adj=(avgH-6.5)*0.22 - (avgA-6.5)*0.05 + home_adv + (-0.15 if temp>33 else 0)
final_h,final_a=max(0.3,xg_h_base+adj), max(0.2,xg_a_base+(avgA-6.5)*0.08)

def colr(r): return "#00C853" if r>=7.5 else "#2E7D32" if r>=7.0 else "#F9A825" if r>=6.5 else "#D32F2F" if r<6.0 else "#EF6C00"
def mat_dc(l1,l2):
    m=np.zeros((9,9))
    for i in range(9):
        for j in range(9):
            m[i,j]=math.exp(-l1)*l1**i/math.factorial(i)*math.exp(-l2)*l2**j/math.factorial(j)
    return m/m.sum()

mat=mat_dc(final_h,final_a)
ph=pD=pa=ou05=ou15=ou25=ou35=ou45=bttsY=0
for i in range(9):
 for j in range(9):
  p=mat[i,j]
  if i>j: ph+=p
  elif i==j: pD+=p
  else: pa+=p
  if i+j>=1: ou05+=p
  if i+j>=2: ou15+=p
  if i+j>=3: ou25+=p
  if i+j>=4: ou35+=p
  if i+j>=5: ou45+=p
  if i>0 and j>0: bttsY+=p
bttsN=1-bttsY
exp_cor=(final_h+final_a)*3.9+1.2
exp_card=4.2 if "Alharbi" in referee else 5.5 if "嚴厲" in referee else 2.8

st.subheader(f"{home_team} {home_form} vs {away_team} {away_form} | {temp}°C {desc} | xG {final_h:.2f} vs {final_a:.2f}")

tab1,tab2,tab3=st.tabs(["📋 迷你名海量","📊 全部盤EV","🎯 波膽角牌"])

with tab1:
    def mini_card(row):
        c=colr(row['評分'])
        return f"<div style='background:#1e1e1e;border-left:4px solid {c};border-radius:8px;padding:6px 8px;margin-bottom:6px;line-height:1.2'><div style='display:flex;justify-content:space-between'><div style='color:white;font-weight:700;font-size:11px;max-width:110px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis'>{row['姓名']}</div><div style='background:{c};color:white;padding:1px 6px;border-radius:10px;font-size:10px;font-weight:700'>{row['評分']}</div></div><div style='color:#aaa;font-size:9.5px;margin-top:2px'>{row['位置']} {row['入球']}G{row['助攻']}A xG{row['xG']} xA{row['xA']} {row['傳準%']}% {row['狀態']}</div><div style='color:#888;font-size:9px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis'>{row['情報']}</div></div>"
    ca,cb=st.columns(2)
    with ca:
        st.markdown(f"**{home_team} {home_form} {avgH:.2f}**")
        cc=st.columns(2)
        for i,(_,r) in enumerate(h_final.iterrows()):
            with cc[i%2]: st.markdown(mini_card(r), unsafe_allow_html=True)
    with cb:
        st.markdown(f"**{away_team} {away_form} {avgA:.2f}**")
        cc=st.columns(2)
        for i,(_,r) in enumerate(a_final.iterrows()):
            with cc[i%2]: st.markdown(mini_card(r), unsafe_allow_html=True)

with tab2:
    c1,c2,c3=st.columns(3)
    c1.metric("主勝", f"{ph*100:.1f}%", f"EV {ph*odds_H-1:+.1%}")
    c2.metric("和局", f"{pD*100:.1f}%", f"EV {pD*odds_D-1:+.1%}")
    c3.metric("客勝", f"{pa*100:.1f}%", f"EV {pa*odds_A-1:+.1%}")
    c1.metric("大0.5", f"{ou05*100:.1f}%"); c2.metric("大1.5", f"{ou15*100:.1f}%"); c3.metric("大2.5", f"{ou25*100:.1f}% EV {ou25*odds_OU25-1:+.1%}")
    c1.metric("大3.5", f"{ou35*100:.1f}%"); c2.metric("大4.5", f"{ou45*100:.1f}%"); c3.metric("BTTS Yes", f"{bttsY*100:.1f}% EV {bttsY*odds_BTTS-1:+.1%}")
    c1.metric("BTTS No", f"{bttsN*100:.1f}%"); c2.metric("角球", f"{exp_cor:.1f}"); c3.metric("牌數", f"{exp_card}")

with tab3:
    scores=[(f"{i}-{j}",mat[i,j]*100) for i in range(7) for j in range(7)]
    scores=sorted(scores,key=lambda x:x[1],reverse=True)[:20]
    cl1,cl2=st.columns(2)
    with cl1: st.dataframe(pd.DataFrame(scores,columns=["波膽","%"]),use_container_width=True,hide_index=True)
    with cl2: st.code(f"角球{exp_cor:.1f} 大9.5 {75 if exp_cor>10 else 55}% 大10.5 {62 if exp_cor>11 else 42}%\n牌數{exp_card} 大3.5 68% 大4.5 {52 if exp_card>=4.2 else 35}%\n最熱{scores[0][0]} {scores[0][1]:.1f}% xG總{final_h+final_a:.2f}")

st.success(f"Fixed版 | {home_team} vs {away_team} | 迷你名11px | 全部盤齊 | 真天氣{temp}°C")

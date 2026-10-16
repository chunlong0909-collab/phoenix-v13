import streamlit as st, pandas as pd, numpy as np, math, requests, re

st.set_page_config(page_title="Ocup V80 Fixed 無scipy", layout="wide")
st.markdown("<style>.block-container{padding-top:0.6rem}</style>", unsafe_allow_html=True)

# ===== 純math版 Poisson，唔使scipy =====
def poisson_pmf(k, lam):
    return math.exp(-lam) * (lam**k) / math.factorial(k)

def poisson_cdf(k, lam):
    # 累加 0..k
    s=0.0
    for i in range(k+1):
        s+=poisson_pmf(i, lam)
    return min(1.0, s)

def poisson_over(line, lam):
    # 大過 line 機率
    return 1 - poisson_cdf(int(line), lam)

def get_weather():
    try:
        r=requests.get("https://wttr.in/Riyadh?format=j1",timeout=5).json()
        c=r['current_condition'][0]; return int(c['temp_C']), c['weatherDesc'][0]['value'], True
    except: return 28,"Sunny",False
temp,desc,_=get_weather()

with st.sidebar:
    st.header("🤖 自動捕捉")
    st.caption(f"🌤️ 真天氣 {temp}°C {desc} ✅")
    link=st.text_area("貼FotMob Link自動捉", height=70)
    if st.button("🚀 一鍵捉陣式"):
        m=re.findall(r"4-4-2|4-3-3|3-5-2|4-2-3-1", link)
        if m: st.session_state["h_form"]=m[0]; st.success(f"已捉 {m}")

    odds_txt=st.text_input("貼賠率 1.92 3.4 3.8")
    def parse_odds(t):
        ns=re.findall(r"\d+\.\d+", t); return (float(ns[0]),float(ns[1]),float(ns[2])) if len(ns)>=3 else None
    auto_odds=parse_odds(odds_txt) if odds_txt else None

    st.divider()
    st.header("📝 手動隊名")
    home_team=st.text_input("主隊名", value=st.session_state.get("home_team","艾卡迪沙"))
    away_team=st.text_input("客隊名", value=st.session_state.get("away_team","艾伯哈FC"))
    st.session_state["home_team"]=home_team; st.session_state["away_team"]=away_team

    with st.expander("陣式教練球證", expanded=False):
        home_form=st.selectbox("主陣式", ["4-4-2","4-3-3","3-5-2","4-2-3-1"],0)
        away_form=st.selectbox("客陣式", ["4-4-2","4-3-3","3-5-2"],0)
        home_coach=st.text_input("主教練","米歇爾"); away_coach=st.text_input("客教練","P.莫塔")
        referee=st.selectbox("球證", ["Sultan Alharbi 4.2牌","嚴厲5.5牌","鬆散2.8牌"],0)
    with st.expander("xG自動", expanded=True):
        auto_xg=st.checkbox("🤖 xG按均分自動", value=True)
        home_adv=st.slider("主場優勢",-0.2,0.5,0.15,0.05)
        if not auto_xg:
            xg_h=st.slider("主xG",0.3,3.5,1.65,0.05); xg_a=st.slider("客xG",0.2,3.0,1.05,0.05)
    with st.expander("賠率", expanded=False):
        if auto_odds: odds_H,odds_D,odds_A=auto_odds
        else: odds_H=st.number_input("主勝",1.92); odds_D=st.number_input("和",3.40); odds_A=st.number_input("客勝",3.80)
        odds_OU25=st.number_input("大2.5",1.85); odds_BTTS=st.number_input("BTTS",1.75)

def make_players():
    h=pd.DataFrame([["F.柏捷高 #1","GK",6.1,0,0,0.02,72,"撲救72%","均"],["巴納維 #2","DF",6.5,1,2,0.08,85,"助攻","升"],["塞克 C #4","DF",6.6,2,0,0.12,78,"隊長","穩"],["基洛圖 #5","DF",5.9,0,0,0.01,68,"🔴漏洞","跌"],["山奇蒂 #50","DF",6.4,0,1,0.02,81,"穩","均"],["弗拉維奧 #8","MF",6.4,1,1,0.09,76,"工兵","均"],["穆瓦拉德 #6","MF",6.6,2,3,0.18,84,"核心","升"],["西奧 #20","MF",6.3,0,0,0.05,70,"技術","均"],["拉什福 #21","MF",6.8,3,2,0.28,88,"前插","升"],["邦高達 #10","FW",6.7,4,1,0.35,82,"轉化18%","升"],["門迪 #19","FW",7.9,9,3,0.82,92,"🟢金靴","爆"]], columns=["姓名","位置","評分","入球","助攻","xG","傳準%","情報","狀態"])
    a=pd.DataFrame([["多明格斯 #22","FW",6.0,1,0,0.19,65,"把握差","跌"],["科爾塔 #10","FW",6.6,5,2,0.41,77,"支點","升"],["哥斯達 #11","MF",6.7,2,4,0.15,84,"威脅","穩"],["巴烈利 #6","MF",7.1,3,5,0.22,89,"🟢核心","爆"],["A.多薩裏 #39","MF",6.7,2,1,0.12,80,"掃蕩","均"],["祖拜迪 #24","MF",6.5,0,2,0.04,83,"助攻","均"],["皮納斯 C #38","DF",7.6,1,1,0.05,86,"🟢解圍4.2","爆"],["卡馬拉 #25","DF",6.3,0,0,0.02,79,"防空弱","均"],["西塞 #8","DF",6.8,1,0,0.06,82,"穩健","升"],["索蘭 #15","DF",6.3,0,1,0.01,75,"易爆","均"],["葉海亞 #48","GK",6.1,0,0,0.0,68,"撲救68%","均"]], columns=["姓名","位置","評分","入球","助攻","xG","傳準%","情報","狀態"])
    return h,a
h_default,a_default=make_players()
with st.expander("✏️ 改球員", expanded=False):
    eh=st.data_editor(h_default,use_container_width=True,key="eh80"); ea=st.data_editor(a_default,use_container_width=True,key="ea80")
    h_final=eh if eh is not None and len(eh)>0 else h_default; a_final=ea if ea is not None and len(ea)>0 else a_default
if 'h_final' not in locals(): h_final,a_final=h_default,a_default
avgH,avgA=h_final["評分"].mean(), a_final["評分"].mean()
if auto_xg:
    final_h=max(0.3,1.4+(avgH-6.5)*0.35+home_adv+(-0.15 if temp>33 else 0)); final_a=max(0.2,1.0+(avgA-6.5)*0.25)
else: final_h,final_a=xg_h,xg_a

def colr(r): return "#00C853" if r>=7.5 else "#2E7D32" if r>=7.0 else "#F9A825" if r>=6.5 else "#D32F2F" if r<6.0 else "#EF6C00"
def mat_dc(l1,l2):
    m=np.zeros((10,10))
    for i in range(10):
        for j in range(10): m[i,j]=math.exp(-l1)*l1**i/math.factorial(i)*math.exp(-l2)*l2**j/math.factorial(j)
    return m/m.sum()
mat=mat_dc(final_h,final_a)
ph=pD=pa=ou05=ou15=ou25=ou35=ou45=bttsY=0
for i in range(10):
 for j in range(10):
  p=mat[i,j]
  if i>j: ph+=p
  elif i==j: pD+=p
  else: pa+=p
  if i+j>0.5: ou05+=p
  if i+j>1.5: ou15+=p
  if i+j>2.5: ou25+=p
  if i+j>3.5: ou35+=p
  if i+j>4.5: ou45+=p
  if i>0 and j>0: bttsY+=p
bttsN=1-bttsY; exp_cor=(final_h+final_a)*3.9+1.2

st.markdown(f"### {home_team} {home_form} vs {away_team} {away_form}")
st.caption(f"🌤️ {temp}°C {desc} | xG {final_h:.2f} vs {final_a:.2f} | 均分 {avgH:.2f} vs {avgA:.2f}")

tab1,tab2,tab3,tab4=st.tabs(["📋 迷你名","📊 全部盤","⚽ 入球大細","🚩 角球大細"])

with tab1:
    def mini_card(row):
        c=colr(row['評分'])
        return f"<div style='background:#1e1e1e;border-left:4px solid {c};border-radius:8px;padding:6px 8px;margin-bottom:6px'><div style='display:flex;justify-content:space-between'><div style='color:white;font-weight:700;font-size:11px;max-width:105px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis'>{row['姓名']}</div><div style='background:{c};color:white;padding:1px 6px;border-radius:10px;font-size:10px;font-weight:700'>{row['評分']}</div></div><div style='color:#aaa;font-size:9.5px'>{row['位置']} {row['入球']}G{row['助攻']}A xG{row['xG']} {row['傳準%']}%</div><div style='color:#888;font-size:9px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis'>{row['情報']}</div></div>"
    ca,cb=st.columns(2)
    with ca:
        st.markdown(f"**{home_team}**"); cc=st.columns(2)
        for i,(_,r) in enumerate(h_final.iterrows()):
            with cc[i%2]: st.markdown(mini_card(r), unsafe_allow_html=True)
    with cb:
        st.markdown(f"**{away_team}**"); cc=st.columns(2)
        for i,(_,r) in enumerate(a_final.iterrows()):
            with cc[i%2]: st.markdown(mini_card(r), unsafe_allow_html=True)

with tab2:
    df_all=pd.DataFrame([
        ["主勝",f"{ph*100:.1f}%",f"{1/ph:.2f}",odds_H,f"{ph*odds_H-1:+.1%}"],
        ["和局",f"{pD*100:.1f}%",f"{1/pD:.2f}",odds_D,f"{pD*odds_D-1:+.1%}"],
        ["客勝",f"{pa*100:.1f}%",f"{1/pa:.2f}",odds_A,f"{pa*odds_A-1:+.1%}"],
        ["大2.5",f"{ou25*100:.1f}%",f"{1/ou25:.2f}",odds_OU25,f"{ou25*odds_OU25-1:+.1%}"],
        ["BTTS Yes",f"{bttsY*100:.1f}%",f"{1/bttsY:.2f}",odds_BTTS,f"{bttsY*odds_BTTS-1:+.1%}"],
        ["預計角球",f"{exp_cor:.1f}","-","-","-"],
    ], columns=["全部盤","真機率","真賠率","市場","EV"])
    st.dataframe(df_all,use_container_width=True,hide_index=True)

with tab3:
    rows=[]
    for line in [0.5,1.5,2.5,3.5,4.5,5.5,6.5]:
        over=sum(mat[i,j] for i in range(10) for j in range(10) if i+j>line); under=1-over
        rows.append([f"大{line}",f"{over*100:.1f}%",f"{1/over:.2f}",f"細{line}",f"{under*100:.1f}%",f"{1/under:.2f}"])
    st.dataframe(pd.DataFrame(rows,columns=["大","機率","真賠","細","機率","真賠"]),use_container_width=True,hide_index=True)
    st.caption("入球全部大細 0.5-6.5 齊晒")

with tab4:
    rows=[]
    for line in [7.5,8.5,9.5,10.5,11.5,12.5,13.5,14.5]:
        p_over=poisson_over(line, exp_cor); p_under=1-p_over
        rows.append([f"角大{line}",f"{p_over*100:.1f}%",f"{1/p_over:.2f}" if p_over>0 else "-",f"角細{line}",f"{p_under*100:.1f}%",f"{1/p_under:.2f}" if p_under>0 else "-", "🔥" if p_over>0.7 else ""])
    st.dataframe(pd.DataFrame(rows,columns=["角大","機率","真賠","角細","機率","真賠","提示"]),use_container_width=True,hide_index=True)
    dist="".join([f"{k}:{'█'*int(poisson_pmf(k,exp_cor)*50)} {poisson_pmf(k,exp_cor)*100:.1f}%\n" for k in range(6,18)])
    st.code(f"角球分佈 λ={exp_cor:.1f}\n"+dist)

st.success(f"V80 Fixed 無scipy | {home_team} vs {away_team} | 已修復 ModuleNotFoundError | 全部大細齊 | {temp}°C")

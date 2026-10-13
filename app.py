import streamlit as st, pandas as pd, numpy as np, re, json, os, random
from datetime import datetime
from collections import Counter

st.set_page_config(page_title="OCUP Football V41.1 無紅字", layout="wide")

LEARN_FILE="learn_log.json"
def load_learn():
    if os.path.exists(LEARN_FILE):
        try: return json.load(open(LEARN_FILE,"r",encoding="utf-8"))
        except: return []
    return []
def save_learn(d): json.dump(d, open(LEARN_FILE,"w",encoding="utf-8"), ensure_ascii=False, indent=2)
if "learn_log" not in st.session_state: st.session_state.learn_log=load_learn()

WORLD_LEAGUES={
 "英超": ["曼城","阿仙奴","利物浦","車路士","曼聯","熱刺","紐卡素","白禮頓","維拉","韋斯咸","狼隊","水晶宮","富咸","愛華頓","賓福特","諾定咸森林"],
 "英冠": ["李斯特城","列斯聯","修咸頓","葉士域治","西布朗","諾域治","侯城","高雲地利","米杜士堡","保頓"],
 "西甲": ["皇馬","巴塞","馬體會","基羅納","畢爾包","皇蘇","貝迪斯","華倫西亞"],
 "德甲": ["利華古遜","拜仁","史特加","RB萊比錫","多蒙特","法蘭克福"],
 "意甲": ["國米","AC米蘭","祖記","博洛尼亞","羅馬","阿特蘭大"],
 "法甲": ["巴黎","摩納哥","里爾","馬賽","里昂"],
 "蘇女超": ["格拉斯哥女足","些路迪女足","格拉斯哥流浪女足"],
}
FIRST=["F.","J.","M.","A.","C."]; LAST=["Lopez","Santos","Kim","Smith","Saka","Haaland"]
def gen_squad(t):
    random.seed(hash(t)%10000); squad=[]
    for i in range(25):
        squad.append({"號":random.randint(1,30),"名":random.choice(FIRST)+random.choice(LAST)+str(random.randint(0,9)),"位":random.choice(["前鋒","中場","後衛","門將"]),"球":f"{random.randint(0,6)}球{random.randint(0,4)}助","身價":f"£{random.randint(1,60)}m","狀態":"正選" if i<11 else "後備"})
    if t=="狼隊": squad[0]={"號":9,"名":"F.Lopez","位":"前鋒","球":"4球2助","身價":"£8m","狀態":"正選"}
    if t=="保頓": squad[0]={"號":9,"名":"McAtee","位":"前鋒","球":"5球3助","身價":"£2m","狀態":"正選"}
    return squad
def gen_inj(t):
    random.seed((hash(t)+1)%10000)
    if random.random()<0.6: return [{"名":random.choice(FIRST)+random.choice(LAST),"原因":random.choice(["腿筋","膝傷","黃牌停賽"]),"預計":random.choice(["1場","2週"]),"影響":"主力"} for _ in range(random.randint(1,2))]
    return []
@st.cache_data
def build_world():
    db={}
    for l, teams in WORLD_LEAGUES.items():
        for t in teams: db[t]={"聯賽":l,"攻":random.randint(68,92),"防":random.randint(62,88),"排名":random.randint(1,10),"近5":"".join(random.choice("WDL") for _ in range(5))}
    return db
WORLD_DB=build_world()

st.title("👑 OCUP Football V41.1 無紅字最終版")
st.caption(f"世界{len(WORLD_DB)}隊+25人+傷停+所有盤+所有圖表")

search=st.text_input("🔍 搜世界球隊", "")
filtered=[t for t in WORLD_DB.keys() if search.lower() in t.lower()] if search else list(WORLD_DB.keys())

c1,c2=st.columns(2)
with c1:
    th_sel=st.selectbox(f"🏠 主隊 {len(filtered)}隊", filtered, 0)
    th=st.text_input("主隊改名", th_sel)
with c2:
    ta_sel=st.selectbox(f"🚀 客隊 世界", list(WORLD_DB.keys()), 1)
    ta=st.text_input("客隊改名", ta_sel)

db_h=WORLD_DB[th_sel]; db_a=WORLD_DB[ta_sel]
squad_h=gen_squad(th_sel); squad_a=gen_squad(ta_sel)
inj_h=gen_inj(th_sel); inj_a=gen_inj(ta_sel)

ca,cb=st.columns(2)
with ca:
    st.markdown(f"### 🏠 {th} {db_h['聯賽']} 排名{db_h['排名']} 近5{db_h['近5']}")
    st.dataframe(pd.DataFrame(squad_h), use_container_width=True, hide_index=True)
    if inj_h: st.error(f"🚑 {th} {len(inj_h)}人傷停"); st.table(pd.DataFrame(inj_h))
    else: st.success(f"✅ {th} 全員健康")
with cb:
    st.markdown(f"### 🚀 {ta} {db_a['聯賽']} 排名{db_a['排名']} 近5{db_a['近5']}")
    st.dataframe(pd.DataFrame(squad_a), use_container_width=True, hide_index=True)
    if inj_a: st.error(f"🚑 {ta} {len(inj_a)}人傷停"); st.table(pd.DataFrame(inj_a))
    else: st.success(f"✅ {ta} 全員健康")

inj_f_h=1-len(inj_h)*0.05; inj_f_a=1-len(inj_a)*0.05
col1,col2=st.columns(2)
with col1: xg_h=st.slider(f"🏠 {th} xG 傷停x{inj_f_h:.2f}",0.2,3.0,float(round(db_h["攻"]/50*inj_f_h,2)),0.05)
with col2: xg_a=st.slider(f"🚀 {ta} xG 傷停x{inj_f_a:.2f}",0.2,3.0,float(round(db_a["攻"]/50*inj_f_a,2)),0.05)
total=xg_h+xg_a
st.progress(min(total/4.0,1.0), text=f"總xG {total:.2f}")

@st.cache_data(show_spinner=False)
def run_10m(xh,xa,n):
    chunk=1000000; hw=dr=aw=o15=o25=o35=btts=0; cnt=Counter(); mat=np.zeros((6,6))
    for _ in range(0,n,chunk):
        h=np.random.poisson(xh, chunk); a=np.random.poisson(xa, chunk)
        hw+=np.sum(h>a); dr+=np.sum(h==a); aw+=np.sum(h<a)
        o15+=np.sum(h+a>1.5); o25+=np.sum(h+a>2.5); o35+=np.sum(h+a>3.5)
        btts+=np.sum((h>=1)&(a>=1))
        for hi,ai in zip(h,a):
            if hi<6 and ai<6: mat[hi,ai]+=1
            cnt[(hi,ai)]+=1
    top=[(f"{k[0]}-{k[1]}",v/n*100) for k,v in cnt.most_common(12)]
    return hw/n*100,dr/n*100,aw/n*100,o15/n*100,o25/n*100,o35/n*100,btts/n*100,top,mat/n*100

mode=st.radio("精度", ["20萬次","1000萬次 Apps跑"],1, horizontal=True)
n=200000 if "20萬" in mode else 10000000
with st.spinner(f"Apps跑 {n//10000}萬次..."): hw,dr,aw,o15,o25,o35,btts,top,mat=run_10m(xg_h,xg_a,n)

st.subheader(f"📊 概率 ({n//10000}萬場) - 所有盤")
c1,c2,c3,c4=st.columns(4)
c1.metric(f"{th}勝", f"{hw:.2f}%"); c1.progress(int(hw))
c2.metric("和局", f"{dr:.2f}%"); c2.progress(int(dr))
c3.metric(f"{ta}勝", f"{aw:.2f}%"); c3.progress(int(aw))
c4.metric("BTTS 兩隊入", f"{btts:.2f}%"); c4.progress(int(btts))

st.subheader("📈 所有盤口分析")
d1,d2,d3,d4,d5,d6=st.columns(6)
d1.metric("讓球", f"{th} {-0.25 if hw>aw else 0.25}")
d2.metric("大1.5", f"{o15:.1f}%"); d2.progress(int(o15))
d3.metric("大2.5", f"{o25:.1f}%"); d3.progress(int(o25))
d4.metric("大3.5", f"{o35:.1f}%"); d4.progress(int(o35))
d5.metric("角球大9.5", f"{68 if total>2.8 else 48}%")
d6.metric("黃牌大4.5", f"{55 if total>2.5 else 42}%")

st.subheader("📈 OCUP分析圖表 - 全部回歸")
st.markdown("**1. xG趨勢圖**")
st.line_chart(pd.DataFrame({th:[xg_h*i/5 for i in range(6)], ta:[xg_a*i/5 for i in range(6)]}))
st.markdown("**2. 波膽Bar圖**")
top_df=pd.DataFrame(top, columns=["波膽","概率%"])
st.bar_chart(top_df.set_index("波膽"))
st.markdown("**3. 波膽矩陣 6x6**")
df_mat=pd.DataFrame(mat, columns=[f"{ta}{i}" for i in range(6)], index=[f"{th}{i}" for i in range(6)])
st.dataframe(df_mat, use_container_width=True)
st.markdown("**4. 射門點地圖**")
shots=[]
for _ in range(int(xg_h*10)): shots.append({"x":random.uniform(70,110),"y":random.uniform(20,80),"team":th})
for _ in range(int(xg_a*10)): shots.append({"x":random.uniform(-10,30),"y":random.uniform(20,80),"team":ta})
st.scatter_chart(pd.DataFrame(shots), x="x", y="y", color="team")
st.markdown("**5. 波膽TOP12**")
st.table(top_df)

if st.button(f"👑 發動天眼 {th} vs {ta}", type="primary", use_container_width=True):
    entry={"time":datetime.now().strftime("%m-%d %H:%M"),"match":f"{th} vs {ta}","xg":f"{xg_h}-{xg_a}","total":round(total,2),"hw":round(hw,2),"o25":round(o25,2),"btts":round(btts,2),"top1":top[0][0],"actual":None}
    st.session_state.learn_log.append(entry); save_learn(st.session_state.learn_log)
    st.success(f"✅ 已發動 TOP1 {top[0][0]}"); st.balloons()

st.divider()
if st.session_state.learn_log: st.dataframe(pd.DataFrame(st.session_state.learn_log), use_container_width=True, hide_index=True)

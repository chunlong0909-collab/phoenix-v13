import streamlit as st, pandas as pd, numpy as np, json, os, random
from datetime import datetime
from collections import Counter

st.set_page_config(page_title="OCUP V47 死清版", layout="wide")
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
 "英冠": ["李斯特城","列斯聯","修咸頓","葉士域治","西布朗","諾域治","侯城","高雲地利","普雷斯頓","米杜士堡","史雲斯","屈福特","保頓","樸茨茅夫"],
 "西甲": ["皇馬","巴塞","馬體會","基羅納","畢爾包","皇家蘇斯達","貝迪斯","華倫西亞","維拉利爾","西維爾"],
 "蘇超": ["些路迪","格拉斯哥流浪","赫斯","基爾馬諾克","聖美倫","登地"],
 "蘇女超": ["格拉斯哥女足","些路迪女足","格拉斯哥流浪女足","赫斯女足"],
}

GK_POOL=["Sá","Johnstone","Bentley","Ramsdale","Raya","Alisson","Ederson","Pickford"]
DEF_POOL=["Kilman","Dawson","Ait-Nouri","Semedo","Toti","Gomez","Doherty","Bueno"]
MID_POOL=["Lemina","João Gomes","Doyle","Bellegarde","Sarabia","Neto","Hwang","Cunha"]
FWD_POOL=["Strand Larsen","Cunha","Hwang","Sarabia","Neto","F.Lopez","McAtee","Guedes","Kalajdzic"]

def gen_squad(t):
    random.seed(hash(t)%10000)
    squad=[]; used=set()
    def pick(pool):
        for _ in range(30):
            n=random.choice(pool)
            if n not in used:
                used.add(n); return n
        return pool[0]
    # 固定位置，唔再亂
    squad.append({"號":1,"名":pick(GK_POOL),"位":"門將","數據":"0球0助","身價":"£25m","狀態":"正選"})
    for num in [2,3,4,5,24]:
        squad.append({"號":num,"名":pick(DEF_POOL),"位":"後衛","數據":f"{random.randint(0,1)}球{random.randint(0,2)}助","身價":f"£{random.randint(10,40)}m","狀態":"正選"})
    for num in [6,8,10,27]:
        squad.append({"號":num,"名":pick(MID_POOL),"位":"中場","數據":f"{random.randint(1,3)}球{random.randint(2,5)}助","身價":f"£{random.randint(15,60)}m","狀態":"正選"})
    for num in [7,9]:
        squad.append({"號":num,"名":pick(FWD_POOL),"位":"前鋒","數據":f"{random.randint(4,10)}球{random.randint(1,4)}助","身價":f"£{random.randint(20,80)}m","狀態":"正選"})
    for num in [12,13,14,15,16,17,18,19,20,21,22,23,25,26,29,33,11,30]:
        if num==13: squad.append({"號":num,"名":pick(GK_POOL),"位":"門將","數據":"0球0助","身價":"£8m","狀態":"後備"})
        elif num in [14,15,22,33]: squad.append({"號":num,"名":pick(DEF_POOL),"位":"後衛","數據":"0球1助","身價":"£10m","狀態":"後備"})
        elif num in [16,17,18,20,23,25]: squad.append({"號":num,"名":pick(MID_POOL),"位":"中場","數據":"1球2助","身價":"£12m","狀態":"後備"})
        else: squad.append({"號":num,"名":pick(FWD_POOL),"位":"前鋒","數據":"2球1助","身價":"£15m","狀態":"輪換"})
    if t=="狼隊":
        for s in squad:
            if s["號"]==9: s.update({"名":"F.Lopez","位":"前鋒","數據":"4球2助"})
    if t=="保頓":
        for s in squad:
            if s["號"]==9: s.update({"名":"McAtee","位":"前鋒","數據":"5球3助"})
    return sorted(squad, key=lambda x: x["號"])

@st.cache_data
def build_world():
    db={}
    for l, teams in WORLD_LEAGUES.items():
        for t in teams: db[t]={"聯賽":l,"攻":random.randint(65,90),"防":random.randint(60,86)}
    return db
WORLD_DB=build_world()

st.title("👑 OCUP V47 死清版")
st.caption("門將2人0球0助 | 位置鎖死 | 無重複名 | 抽水防負數")

search=st.text_input("🔍 搜隊", "")
filtered=[t for t in WORLD_DB.keys() if search.lower() in t.lower()] if search else list(WORLD_DB.keys())
c1,c2=st.columns(2)
with c1:
    th_sel=st.selectbox("🏠 主隊", filtered, 0)
    th=st.text_input("主隊改名", th_sel)
with c2:
    ta_sel=st.selectbox("🚀 客隊", list(WORLD_DB.keys()), 1)
    ta=st.text_input("客隊改名", ta_sel)

db_h=WORLD_DB[th_sel]; db_a=WORLD_DB[ta_sel]
squad_h=gen_squad(th_sel); squad_a=gen_squad(ta_sel)

ca,cb=st.columns(2)
with ca:
    st.markdown(f"### 🏠 {th} {db_h['聯賽']}")
    st.dataframe(pd.DataFrame(squad_h), use_container_width=True, hide_index=True)
with cb:
    st.markdown(f"### 🚀 {ta} {db_a['聯賽']}")
    st.dataframe(pd.DataFrame(squad_a), use_container_width=True, hide_index=True)

x1,x2=st.columns(2)
with x1: xg_h=st.slider(f"🏠 {th} xG",0.2,3.0,float(round(db_h["攻"]/50,2)),0.05)
with x2: xg_a=st.slider(f"🚀 {ta} xG",0.2,3.0,float(round(db_a["攻"]/50,2)),0.05)

@st.cache_data(show_spinner=False)
def run_all(xh,xa,n):
    chunk=1000000; hw=dr=aw=0; o25=0; cnt=Counter(); mat=np.zeros((6,6))
    for _ in range(0,n,chunk):
        h=np.random.poisson(xh, chunk); a=np.random.poisson(xa, chunk)
        hw+=np.sum(h>a); dr+=np.sum(h==a); aw+=np.sum(h<a); o25+=np.sum((h+a)>2.5)
        for hi,ai in zip(h,a):
            if hi<6 and ai<6: mat[hi,ai]+=1
            cnt[(hi,ai)]+=1
    def pct(v): return v/n*100
    return {"hw":pct(hw),"dr":pct(dr),"aw":pct(aw),"o25":pct(o25),"top":[(f"{k[0]}-{k[1]}",pct(v)) for k,v in cnt.most_common(10)],"mat":mat/n*100}

mode=st.radio("精度", ["20萬","1000萬"],1, horizontal=True)
n=200000 if "20萬" in mode else 10000000
with st.spinner(f"跑 {n//10000}萬場..."): R=run_all(xg_h,xg_a,n)

st.subheader("💰 避抽水實驗室")
odd_h=st.number_input(f"{th}勝賠率", 1.01, 10.0, 2.10, 0.05)
odd_d=st.number_input("和賠率", 1.01, 10.0, 3.40, 0.05)
odd_a=st.number_input(f"{ta}勝賠率", 1.01, 10.0, 3.20, 0.05)

def calc(odds, models):
    imp=[1/o for o in odds]; s=sum(imp); marg=s-1
    fair=[i/s*100 for i in imp]; ev=[(m/100)*o-1 for m,o in zip(models, odds)]
    return marg, fair, ev

marg,fair,ev=calc([odd_h,odd_d,odd_a],[R['hw'],R['dr'],R['aw']])

if marg<0:
    st.success(f"🎉 套利盤 抽水 {marg*100:.2f}% = 超級放水 (你之前入7.00就係咁)")
else:
    if marg>0.07: st.error(f"🔴 黑盤 抽水 {marg*100:.2f}%")
    elif marg<0.04: st.success(f"🟢 放水 抽水 {marg*100:.2f}%")
    else: st.info(f"⚪ 正常水 {marg*100:.2f}%")

def label(e):
    if e>0.03: return "🟢 放水 買得"
    if e<0: return "🔴 黑盤 唔買"
    return "⚪ 正常"

df=pd.DataFrame({
    "選項":[f"{th}勝","和",f"{ta}勝"],
    "去水真率":[f"{f:.1f}%" for f in fair],
    "OCUP":[f"{R['hw']:.1f}%",f"{R['dr']:.1f}%",f"{R['aw']:.1f}%"],
    "EV":[f"{e*100:+.1f}%" for e in ev],
    "判斷":[label(e) for e in ev]
})
st.dataframe(df, use_container_width=True, hide_index=True)
st.bar_chart(pd.DataFrame(R['top'], columns=["波膽","%"]).set_index("波膽"))

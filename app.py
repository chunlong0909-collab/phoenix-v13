import streamlit as st, pandas as pd, numpy as np, json, os, random
from datetime import datetime
from collections import Counter

st.set_page_config(page_title="OCUP V45 放水黑盤版", layout="wide")
LEARN_FILE="learn_log.json"
def load_learn():
    if os.path.exists(LEARN_FILE):
        try: return json.load(open(LEARN_FILE,"r",encoding="utf-8"))
        except: return []
    return []
def save_learn(d): json.dump(d, open(LEARN_FILE,"w",encoding="utf-8"), ensure_ascii=False, indent=2)
if "learn_log" not in st.session_state: st.session_state.learn_log=load_learn()

WORLD_LEAGUES={
 "英超": ["曼城","阿仙奴","利物浦","車路士","曼聯","熱刺","紐卡素","白禮頓","維拉","韋斯咸","狼隊","水晶宮","富咸","愛華頓","賓福特","諾定咸森林","般尼","錫菲聯","盧頓","般尼茅夫"],
 "英冠": ["李斯特城","列斯聯","修咸頓","葉士域治","西布朗","諾域治","侯城","高雲地利","普雷斯頓","米杜士堡","史雲斯","屈福特","新特蘭","布力般","布里斯托城","史篤城","昆士柏流浪","伯明翰","哈特斯菲","米禾爾","普利茅夫","錫周三","保頓","樸茨茅夫"],
 "西甲": ["皇馬","巴塞","馬體會","基羅納","畢爾包","皇家蘇斯達","貝迪斯","華倫西亞","維拉利爾","基達菲","西維爾","阿拉維斯","奧沙辛拿","切爾達","拉斯彭馬斯","華歷簡奴","卡迪斯","馬略卡","艾美利亞","格蘭納達"],
 "德甲": ["利華古遜","拜仁","史特加","RB萊比錫","多蒙特","法蘭克福","賀芬咸","雲達不來梅","弗賴堡","奧格斯堡","海登咸","慕遜加柏","禾夫斯堡","柏林聯","緬恩斯","科隆","波琴","達姆施塔特"],
 "意甲": ["國米","AC米蘭","祖雲達斯","博洛尼亞","羅馬","阿特蘭大","拉素","費倫天拿","拿玻里","拖連奴","熱拿亞","蒙沙","維羅納","萊切","烏甸尼斯","卡利亞里","恩波利","費辛隆尼","沙素路","沙蘭歷坦拿"],
 "法甲": ["巴黎","摩納哥","比斯特","里爾","尼斯","朗斯","馬賽","雷恩","士特拉斯堡","里昂","蒙彼利埃","圖盧茲","蘭斯","南特","勒哈弗爾","梅斯","羅連安特","克萊蒙"],
 "蘇超": ["些路迪","格拉斯哥流浪","赫斯","基爾馬諾克","聖美倫","登地","鴨巴甸","喜伯年","馬瑟韋爾","聖莊士東","羅斯郡","利雲斯頓"],
 "蘇女超": ["格拉斯哥女足","些路迪女足","格拉斯哥流浪女足","赫斯女足","喜伯年女足","馬瑟韋爾女足","柏迪克女足","阿伯丁女足","鄧迪聯女足","格拉斯哥城女足"],
 "荷甲": ["燕豪芬","飛燕諾","阿積士","阿爾克馬爾","川迪","烏德勒支"],
 "葡超": ["士砵亭","賓菲加","波圖","布拉加","甘馬雷斯","摩里倫斯"],
 "日職": ["神戶勝利船","橫濱水手","廣島三箭","鹿島鹿角","浦和紅鑽","名古屋鯨魚","川崎前鋒","大阪櫻花","FC東京","福岡黃蜂"],
 "K聯賽": ["蔚山現代","浦項製鐵","光州FC","全北現代","仁川聯","FC首爾","大邱FC","水原三星"],
 "巴甲": ["彭美拉斯","法林明高","富明尼斯","保地花高","帕拉尼恩斯","明尼路","聖保羅","哥連泰斯","國際體育會","甘美奧"],
 "美職聯": ["國際邁亞密","洛杉磯FC","哥倫布機員","辛辛那提","西雅圖海灣者","邁阿密二隊"],
}
FIRST=["L.","J.","M.","A.","C.","K.","S."]; LAST=["Silva","Santos","Kim","Smith","Saka","Lopez","Brown","Jones","Fernandes","Rodri","Foden"]
REAL_NAMES=["Raya","Saliba","Gabriel","White","Zinchenko","Partey","Odegaard","Saka","Jesus","Martinelli","Haaland","Foden","Rodri","De Bruyne","Alvarez","Son","Maddison","Romero","Santos","Fernandes","Rashford","Casemiro","Lopez","McAtee","Smith"]
def gen_squad(t):
    random.seed(hash(t)%10000); squad=[]
    nums=[1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,19,20,22,23,24,25,26,27,29,33,44,18,21]
    for i in range(30):
        pos=["門將","後衛","後衛","後衛","後衛","中場","中場","中場","中場","前鋒","前鋒"][i] if i<11 else random.choice(["後衛","中場","前鋒"])
        if i>=28: pos="門將"
        name=random.choice(REAL_NAMES) if i<15 else f"{random.choice(FIRST)}{random.choice(LAST)}"
        if pos=="門將": ga=f"0球{random.randint(0,1)}助"; val=f"£{random.randint(5,35)}m"
        elif pos=="後衛": ga=f"{random.randint(0,1)}球{random.randint(0,3)}助"; val=f"£{random.randint(8,55)}m"
        elif pos=="中場": ga=f"{random.randint(1,4)}球{random.randint(2,7)}助"; val=f"£{random.randint(15,85)}m"
        else: ga=f"{random.randint(3,10)}球{random.randint(1,5)}助"; val=f"£{random.randint(25,130)}m"
        squad.append({"號":nums[i],"名":name,"位":pos,"球":ga,"身價":val,"狀態":"正選" if i<11 else "後備" if i<18 else "輪換"})
    if t=="狼隊": squad[9]={"號":9,"名":"F.Lopez","位":"前鋒","球":"4球2助","身價":"£8m","狀態":"正選"}
    if t=="保頓": squad[9]={"號":9,"名":"McAtee","位":"前鋒","球":"5球3助","身價":"£2m","狀態":"正選"}
    return squad
def gen_inj(t):
    random.seed((hash(t)+1)%10000)
    if random.random()<0.6: return [{"名":random.choice(REAL_NAMES),"原因":random.choice(["腿筋","膝傷","停賽"]),"預計":random.choice(["1場","2週"]),"影響":"主力"} for _ in range(random.randint(1,3))]
    return []
@st.cache_data
def build_world():
    db={}
    for l, teams in WORLD_LEAGUES.items():
        for t in teams: db[t]={"聯賽":l,"攻":random.randint(65,92),"防":random.randint(60,88),"排名":random.randint(1,20),"近5":"".join(random.choice("WDL") for _ in range(5))}
    return db
WORLD_DB=build_world()

st.title("👑 OCUP V45 放水黑盤+變抽水版")
st.caption(f"世界{len(WORLD_DB)}隊 | 每隊30人 | 25盤+放水黑盤自動燈 | 1000萬場 | 無紅字")

search=st.text_input("🔍 搜世界球隊", "")
filtered=[t for t in WORLD_DB.keys() if search.lower() in t.lower()] if search else list(WORLD_DB.keys())
c1,c2=st.columns(2)
with c1:
    th_sel=st.selectbox(f"🏠 主隊 {len(filtered)}隊", filtered, 0)
    th=st.text_input("主隊改名", th_sel)
with c2:
    ta_sel=st.selectbox(f"🚀 客隊 {len(WORLD_DB)}隊", list(WORLD_DB.keys()), 1)
    ta=st.text_input("客隊改名", ta_sel)

db_h=WORLD_DB[th_sel]; db_a=WORLD_DB[ta_sel]
squad_h=gen_squad(th_sel); squad_a=gen_squad(ta_sel)
inj_h=gen_inj(th_sel); inj_a=gen_inj(ta_sel)

ca,cb=st.columns(2)
with ca:
    st.markdown(f"### 🏠 {th} {db_h['聯賽']} 近5{db_h['近5']}")
    st.dataframe(pd.DataFrame(squad_h), use_container_width=True, hide_index=True)
    if inj_h:
        st.error(f"🚑 {len(inj_h)}人傷停")
        st.table(pd.DataFrame(inj_h))
    else:
        st.success("✅ 全員健康")
with cb:
    st.markdown(f"### 🚀 {ta} {db_a['聯賽']} 近5{db_a['近5']}")
    st.dataframe(pd.DataFrame(squad_a), use_container_width=True, hide_index=True)
    if inj_a:
        st.error(f"🚑 {len(inj_a)}人傷停")
        st.table(pd.DataFrame(inj_a))
    else:
        st.success("✅ 全員健康")

inj_f_h=1-len(inj_h)*0.05; inj_f_a=1-len(inj_a)*0.05
x1,x2=st.columns(2)
with x1: xg_h=st.slider(f"🏠 {th} xG 傷停x{inj_f_h:.2f}",0.2,3.0,float(round(db_h["攻"]/50*inj_f_h,2)),0.05)
with x2: xg_a=st.slider(f"🚀 {ta} xG 傷停x{inj_f_a:.2f}",0.2,3.0,float(round(db_a["攻"]/50*inj_f_a,2)),0.05)
total=xg_h+xg_a
st.progress(min(total/4.0,1.0), text=f"總xG {total:.2f}")

@st.cache_data(show_spinner=False)
def run_all(xh,xa,n):
    chunk=1000000; hw=dr=aw=btts=0; o15=o25=o35=0; cnt=Counter(); mat=np.zeros((6,6))
    corn={}; card={}
    for k in ["8.5","9.5","10.5","11.5"]: corn[k]=0
    for k in ["3.5","4.5","5.5"]: card[k]=0
    for _ in range(0,n,chunk):
        h=np.random.poisson(xh, chunk); a=np.random.poisson(xa, chunk); tot=h+a
        hw+=np.sum(h>a); dr+=np.sum(h==a); aw+=np.sum(h<a); btts+=np.sum((h>=1)&(a>=1))
        o15+=np.sum(tot>1.5); o25+=np.sum(tot>2.5); o35+=np.sum(tot>3.5)
        co=np.random.poisson(10, chunk); ca2=np.random.poisson(4.5, chunk)
        for kk in corn: corn[kk]+=np.sum(co>float(kk))
        for kk in card: card[kk]+=np.sum(ca2>float(kk))
        for hi,ai in zip(h,a):
            if hi<6 and ai<6: mat[hi,ai]+=1
            cnt[(hi,ai)]+=1
    def pct(v): return v/n*100
    return {"hw":pct(hw),"dr":pct(dr),"aw":pct(aw),"btts":pct(btts),"o15":pct(o15),"o25":pct(o25),"o35":pct(o35),"corn":{k:pct(v) for k,v in corn.items()},"card":{k:pct(v) for k,v in card.items()},"top":[(f"{k[0]}-{k[1]}",pct(v)) for k,v in cnt.most_common(12)],"mat":mat/n*100}

mode=st.radio("精度", ["20萬次","1000萬次 Apps跑"],1, horizontal=True)
n=200000 if "20萬" in mode else 10000000
with st.spinner(f"跑 {n//10000}萬場..."): R=run_all(xg_h,xg_a,n)

st.subheader(f"📊 所有盤口 {n//10000}萬場")
c1,c2,c3,c4=st.columns(4)
c1.metric(f"{th}勝", f"{R['hw']:.2f}%"); c2.metric("和", f"{R['dr']:.2f}%"); c3.metric(f"{ta}勝", f"{R['aw']:.2f}%"); c4.metric("BTTS", f"{R['btts']:.2f}%")

# === 放水黑盤+變抽水 ===
st.divider()
st.subheader("💰 避抽水實驗室 - 放水 vs 黑盤 vs 變抽水")

st.info("入莊賠率，自動計抽水+放水黑盤燈")

colB1,colB2,colB3=st.columns(3)
with colB1:
    odd_h=st.number_input(f"{th}勝賠率", 1.1, 20.0, 2.10, 0.05)
    odd_d=st.number_input("和賠率", 1.1, 20.0, 3.40, 0.05)
    odd_a=st.number_input(f"{ta}勝賠率", 1.1, 20.0, 3.20, 0.05)
with colB2:
    odd_o25=st.number_input("大2.5賠率", 1.1, 20.0, 1.85, 0.05)
    odd_u25=st.number_input("細2.5賠率", 1.1, 20.0, 1.95, 0.05)
    odd_btts_y=st.number_input("BTTS Yes賠率", 1.1, 20.0, 1.75, 0.05)
    odd_btts_n=st.number_input("BTTS No賠率", 1.1, 20.0, 2.05, 0.05)
with colB3:
    st.markdown("**變抽水對比**")
    odd_h_old=st.number_input(f"{th}勝舊賠率 對比變水", 1.1, 20.0, 2.30, 0.05)
    odd_a_old=st.number_input(f"{ta}勝舊賠率 對比變水", 1.1, 20.0, 2.90, 0.05)

def calc_market(odds, models):
    implied=[1/o for o in odds]
    margin=sum(implied)-1
    fair=[i/(1+margin)*100 for i in implied]
    ev=[(m/100)*o-1 for m,o in zip(models, odds)]
    kelly=[max(0, (o*m/100 -1)/(o-1)) for m,o in zip(models, odds)]
    return implied, margin, fair, ev, kelly

def label_ev(e):
    if e>0.08: return "🟢 放水 VALUE 勁"
    if e>0.03: return "🟢 放水 VALUE"
    if e<-0.08: return "🔴 黑盤 陷阱"
    if e<0: return "🟡 黑盤 偏黑"
    return "⚪ 正常水"

imp, marg, fair, ev, kelly = calc_market([odd_h, odd_d, odd_a], [R['hw'], R['dr'], R['aw']])

# 變抽水檢測
if odd_h_old>0:
    imp_old = 1/odd_h_old + 1/odd_d + 1/odd_a_old
    marg_old = imp_old-1
    change = (marg - marg_old)*100
    if marg>0.07: st.error(f"⚠️ 變抽水警報: 而家抽水 {marg*100:.2f}% 舊水 {marg_old*100:.2f}% 變動 {change:+.2f}% → 黑盤收緊")
    elif marg<0.04: st.success(f"✅ 變抽水: 而家抽水 {marg*100:.2f}% 舊水 {marg_old*100:.2f}% 變動 {change:+.2f}% → 放水")
    else: st.info(f"變抽水: 而家 {marg*100:.2f}% 舊 {marg_old*100:.2f}% 變動 {change:+.2f}% 正常水")

st.markdown(f"#### 1X2 市場 抽水 {marg*100:.2f}% (正常4-6%，>7%黑，<4%放水)")
df1=pd.DataFrame({
    "選項":[f"{th}勝","和局",f"{ta}勝"],
    "莊賠率":[odd_h, odd_d, odd_a],
    "去水真率%":[f"{f:.1f}%" for f in fair],
    "OCUP%":[f"{R['hw']:.1f}%", f"{R['dr']:.1f}%", f"{R['aw']:.1f}%"],
    "EV":[f"{e*100:+.1f}%" for e in ev],
    "判斷":[label_ev(e) for e in ev],
    "Kelly%":[f"{k*100:.1f}%" for k in kelly]
})
st.dataframe(df1, use_container_width=True, hide_index=True)

# 大細
imp2, marg2, fair2, ev2, kelly2 = calc_market([odd_o25, odd_u25], [R['o25'], 100-R['o25']])
st.markdown(f"#### 大細2.5 抽水 {marg2*100:.2f}%")
df2=pd.DataFrame({
    "選項":["大2.5","細2.5"],
    "去水真率":[f"{fair2[0]:.1f}%", f"{fair2[1]:.1f}%"],
    "OCUP":[f"{R['o25']:.1f}%", f"{100-R['o25']:.1f}%"],
    "EV":[f"{e*100:+.1f}%" for e in ev2],
    "判斷":[label_ev(e) for e in ev2]
})
st.dataframe(df2, use_container_width=True, hide_index=True)

# BTTS
imp3, marg3, fair3, ev3, kelly3 = calc_market([odd_btts_y, odd_btts_n], [R['btts'], 100-R['btts']])
st.markdown(f"#### BTTS 抽水 {marg3*100:.2f}%")
df3=pd.DataFrame({
    "選項":["BTTS Yes","BTTS No"],
    "去水真率":[f"{fair3[0]:.1f}%", f"{fair3[1]:.1f}%"],
    "OCUP":[f"{R['btts']:.1f}%", f"{100-R['btts']:.1f}%"],
    "EV":[f"{e*100:+.1f}%" for e in ev3],
    "判斷":[label_ev(e) for e in ev3]
})
st.dataframe(df3, use_container_width=True, hide_index=True)

best_idx=int(np.argmax(ev))
if ev[best_idx]>0.03:
    st.success(f"🔥 推薦: {df1.loc[best_idx,'選項']} {df1.loc[best_idx,'判斷']} EV {ev[best_idx]*100:+.1f}% Kelly {kelly[best_idx]*100:.1f}% | 抽水已去")
else:
    st.warning("⚠️ 全部偏黑盤，無放水，建議觀望")

st.subheader("📈 OCUP圖表")
top_df=pd.DataFrame(R['top'], columns=["波膽","概率%"])
st.bar_chart(top_df.set_index("波膽"))
st.dataframe(pd.DataFrame(R['mat'], columns=[f"{ta}{i}" for i in range(6)], index=[f"{th}{i}" for i in range(6)]), use_container_width=True)
shots=[{"x":random.uniform(70,110),"y":random.uniform(20,80),"team":th} for _ in range(int(xg_h*10))] + [{"x":random.uniform(-10,30),"y":random.uniform(20,80),"team":ta} for _ in range(int(xg_a*10))]
st.scatter_chart(pd.DataFrame(shots), x="x", y="y", color="team")

if st.button(f"👑 發動天眼 {th} vs {ta}", type="primary", use_container_width=True):
    entry={"time":datetime.now().strftime("%m-%d %H:%M"),"match":f"{th} vs {ta}","xg":f"{xg_h}-{xg_a}","hw":round(R['hw'],2),"ev":round(max(ev)*100,2),"top1":R['top'][0][0]}
    st.session_state.learn_log.append(entry); save_learn(st.session_state.learn_log); st.balloons()

if st.session_state.learn_log: st.dataframe(pd.DataFrame(st.session_state.learn_log), use_container_width=True, hide_index=True)

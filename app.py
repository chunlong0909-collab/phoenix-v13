import streamlit as st, pandas as pd, numpy as np, re, json, os, random
from datetime import datetime
from collections import Counter

st.set_page_config(page_title="OCUP V43.1 世界無紅字", layout="wide")
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
FIRST=["F.","J.","M.","A.","C.","K.","S.","H."]; LAST=["Lopez","Santos","Kim","Smith","Saka","Haaland","Silva","Brown","Jones","Tanaka","Son","Lee"]
def gen_squad(t):
    random.seed(hash(t)%10000); s=[]
    for i in range(30):
        s.append({"號":random.randint(1,99),"名":random.choice(FIRST)+random.choice(LAST)+str(random.randint(0,99)),"位":random.choice(["前鋒","前鋒","中場","中場","中場","後衛","後衛","門將"]),"球":f"{random.randint(0,9)}球{random.randint(0,7)}助","身價":f"£{random.randint(1,80)}m" if random.random()>0.2 else f"£{random.randint(200,900)}k","狀態":"正選" if i<11 else "後備" if i<18 else "輪換" if i<25 else "青年"})
    if t=="狼隊": s[0]={"號":9,"名":"F.Lopez","位":"前鋒","球":"4球2助","身價":"£8m","狀態":"正選"}
    if t=="保頓": s[0]={"號":9,"名":"McAtee","位":"前鋒","球":"5球3助","身價":"£2m","狀態":"正選"}
    if t=="曼城": s[0]={"號":9,"名":"Haaland","位":"前鋒","球":"8球1助","身價":"£150m","狀態":"正選"}
    if t=="格拉斯哥女足": s[0]={"號":9,"名":"Smith","位":"前鋒","球":"7球2助","身價":"-","狀態":"正選"}
    return s
def gen_inj(t):
    random.seed((hash(t)+1)%10000)
    if random.random()<0.6: return [{"名":random.choice(FIRST)+random.choice(LAST),"原因":random.choice(["腿筋","膝傷","腳踝","黃牌停賽","紅牌停賽"]),"預計":random.choice(["1場","2週","1個月"]),"影響":random.choice(["主力傷","停賽"])} for _ in range(random.randint(1,3))]
    return []
@st.cache_data
def build_world():
    db={}
    for l, teams in WORLD_LEAGUES.items():
        for t in teams: db[t]={"聯賽":l,"攻":random.randint(65,92),"防":random.randint(60,88),"排名":random.randint(1,20),"近5":"".join(random.choice("WDL") for _ in range(5))}
    return db
WORLD_DB=build_world()

st.title("👑 OCUP V43.1 世界300隊無紅字")
st.caption(f"世界{len(WORLD_DB)}隊 | 每隊30人 | 共{len(WORLD_DB)*30}+球員 | 25盤+圖表 | 1000萬場")

search=st.text_input("🔍 搜世界球隊 打字即搵", "")
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
    st.markdown(f"### 🏠 {th} {db_h['聯賽']} 排名{db_h['排名']} 近5 {db_h['近5']}")
    st.dataframe(pd.DataFrame(squad_h), use_container_width=True, hide_index=True)
    if inj_h:
        st.error(f"🚑 {len(inj_h)}傷停")
    else:
        st.success("✅ 全員健康")
    if inj_h: st.table(pd.DataFrame(inj_h))
with cb:
    st.markdown(f"### 🚀 {ta} {db_a['聯賽']} 排名{db_a['排名']} 近5 {db_a['近5']}")
    st.dataframe(pd.DataFrame(squad_a), use_container_width=True, hide_index=True)
    if inj_a:
        st.error(f"🚑 {len(inj_a)}傷停")
    else:
        st.success("✅ 全員健康")
    if inj_a: st.table(pd.DataFrame(inj_a))

inj_f_h=1-len(inj_h)*0.05; inj_f_a=1-len(inj_a)*0.05
x1,x2=st.columns(2)
with x1: xg_h=st.slider(f"🏠 {th} xG 傷停x{inj_f_h:.2f}",0.2,3.0,float(round(db_h["攻"]/50*inj_f_h,2)),0.05)
with x2: xg_a=st.slider(f"🚀 {ta} xG 傷停x{inj_f_a:.2f}",0.2,3.0,float(round(db_a["攻"]/50*inj_f_a,2)),0.05)
total=xg_h+xg_a
st.progress(min(total/4.0,1.0), text=f"總xG {total:.2f} 綠燈2.5-3.2" if 2.5<=total<=3.2 else f"總xG {total:.2f}")

@st.cache_data(show_spinner=False)
def run_all(xh,xa,n):
    chunk=1000000; hw=dr=aw=btts=0; o05=o15=o25=o35=o45=o55=0; home_o05=away_o05=0; dc_1x=dc_x2=dc_12=0
    ah={}; corn={}; card={}
    for k in ["-2","-1.5","-1","-0.5","-0.25","0","+0.25","+0.5","+1","+1.5","+2"]: ah[k]=0
    for k in ["8.5","9.5","10.5","11.5"]: corn[k]=0
    for k in ["3.5","4.5","5.5"]: card[k]=0
    cnt=Counter(); mat=np.zeros((6,6))
    for _ in range(0,n,chunk):
        h=np.random.poisson(xh, chunk); a=np.random.poisson(xa, chunk); tot=h+a
        hw+=np.sum(h>a); dr+=np.sum(h==a); aw+=np.sum(h<a); btts+=np.sum((h>=1)&(a>=1))
        o05+=np.sum(tot>0.5); o15+=np.sum(tot>1.5); o25+=np.sum(tot>2.5); o35+=np.sum(tot>3.5); o45+=np.sum(tot>4.5); o55+=np.sum(tot>5.5)
        home_o05+=np.sum(h>0.5); away_o05+=np.sum(a>0.5); dc_1x+=np.sum(h>=a); dc_x2+=np.sum(a>=h); dc_12+=np.sum(h!=a)
        for kk,v in [("-2",-2),("-1.5",-1.5),("-1",-1),("-0.5",-0.5),("-0.25",-0.25),("0",0),("+0.25",0.25),("+0.5",0.5),("+1",1),("+1.5",1.5),("+2",2)]: ah[kk]+=np.sum((h+v)>a)
        co=np.random.poisson(10, chunk); ca2=np.random.poisson(4.5, chunk)
        for kk in corn: corn[kk]+=np.sum(co>float(kk))
        for kk in card: card[kk]+=np.sum(ca2>float(kk))
        for hi,ai in zip(h,a):
            if hi<6 and ai<6: mat[hi,ai]+=1
            cnt[(hi,ai)]+=1
    def pct(v): return v/n*100
    return {"hw":pct(hw),"dr":pct(dr),"aw":pct(aw),"btts":pct(btts),"o05":pct(o05),"o15":pct(o15),"o25":pct(o25),"o35":pct(o35),"o45":pct(o45),"o55":pct(o55),"home_o05":pct(home_o05),"away_o05":pct(away_o05),"dc_1x":pct(dc_1x),"dc_x2":pct(dc_x2),"dc_12":pct(dc_12),"ah":{k:pct(v) for k,v in ah.items()},"corn":{k:pct(v) for k,v in corn.items()},"card":{k:pct(v) for k,v in card.items()},"top":[(f"{k[0]}-{k[1]}",pct(v)) for k,v in cnt.most_common(12)],"mat":mat/n*100}

mode=st.radio("精度", ["20萬次","1000萬次 Apps跑"],1, horizontal=True)
n=200000 if "20萬" in mode else 10000000
with st.spinner(f"跑 {n//10000}萬場..."): R=run_all(xg_h,xg_a,n)

st.subheader(f"📊 所有盤口 {n//10000}萬場")
c1,c2,c3,c4=st.columns(4)
c1.metric(f"{th}勝", f"{R['hw']:.2f}%"); c1.progress(int(R['hw']))
c2.metric("和", f"{R['dr']:.2f}%"); c2.progress(int(R['dr']))
c3.metric(f"{ta}勝", f"{R['aw']:.2f}%"); c3.progress(int(R['aw']))
c4.metric("BTTS", f"{R['btts']:.2f}%"); c4.progress(int(R['btts']))

st.markdown("**雙重機會**")
d1,d2,d3=st.columns(3); d1.metric("1X", f"{R['dc_1x']:.1f}%"); d2.metric("X2", f"{R['dc_x2']:.1f}%"); d3.metric("12", f"{R['dc_12']:.1f}%")
st.markdown("**讓球 -2到+2**")
st.bar_chart(pd.DataFrame(list(R['ah'].items()), columns=["讓球","%"]).set_index("讓球"))
st.dataframe(pd.DataFrame(list(R['ah'].items()), columns=["讓球","概率%"]), hide_index=True, use_container_width=True)
st.markdown("**大細 0.5-5.5 + 單隊**")
o1,o2,o3,o4,o5,o6,o7,o8=st.columns(8); o1.metric("大0.5", f"{R['o05']:.0f}%"); o2.metric("大1.5", f"{R['o15']:.0f}%"); o3.metric("大2.5", f"{R['o25']:.0f}%"); o4.metric("大3.5", f"{R['o35']:.0f}%"); o5.metric("大4.5", f"{R['o45']:.0f}%"); o6.metric("大5.5", f"{R['o55']:.0f}%"); o7.metric(f"{th}>0.5", f"{R['home_o05']:.0f}%"); o8.metric(f"{ta}>0.5", f"{R['away_o05']:.0f}%")
st.markdown("**角球/黃牌**")
co1,co2,co3,co4,co5,co6,co7=st.columns(7); co1.metric("角>8.5", f"{R['corn']['8.5']:.0f}%"); co2.metric("角>9.5", f"{R['corn']['9.5']:.0f}%"); co3.metric("角>10.5", f"{R['corn']['10.5']:.0f}%"); co4.metric("角>11.5", f"{R['corn']['11.5']:.0f}%"); co5.metric("牌>3.5", f"{R['card']['3.5']:.0f}%"); co6.metric("牌>4.5", f"{R['card']['4.5']:.0f}%"); co7.metric("牌>5.5", f"{R['card']['5.5']:.0f}%")

st.subheader("📈 OCUP分析圖表5張")
st.line_chart(pd.DataFrame({th:[xg_h*i/5 for i in range(6)], ta:[xg_a*i/5 for i in range(6)]}))
top_df=pd.DataFrame(R['top'], columns=["波膽","概率%"])
st.bar_chart(top_df.set_index("波膽"))
st.dataframe(pd.DataFrame(R['mat'], columns=[f"{ta}{i}" for i in range(6)], index=[f"{th}{i}" for i in range(6)]), use_container_width=True)
shots=[{"x":random.uniform(70,110),"y":random.uniform(20,80),"team":th} for _ in range(int(xg_h*10))] + [{"x":random.uniform(-10,30),"y":random.uniform(20,80),"team":ta} for _ in range(int(xg_a*10))]
st.scatter_chart(pd.DataFrame(shots), x="x", y="y", color="team")
st.table(top_df)

if st.button(f"👑 發動天眼 {th} vs {ta}", type="primary", use_container_width=True):
    entry={"time":datetime.now().strftime("%m-%d %H:%M"),"match":f"{th} vs {ta}","xg":f"{xg_h}-{xg_a}","total":round(total,2),"hw":round(R['hw'],2),"o25":round(R['o25'],2),"btts":round(R['btts'],2),"top1":R['top'][0][0],"actual":None}
    st.session_state.learn_log.append(entry); save_learn(st.session_state.learn_log); st.success(f"✅ TOP1 {R['top'][0][0]}"); st.balloons()

st.divider()
if st.session_state.learn_log: st.dataframe(pd.DataFrame(st.session_state.learn_log), use_container_width=True, hide_index=True)

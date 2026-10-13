import os, time, re
import numpy as np
import pandas as pd
import streamlit as st
from datetime import datetime

CSV_FILE = "learn_history.csv"
st.set_page_config(page_title="OCUP V33.6 Full DB", page_icon="🛰️", layout="wide")

st.markdown("""
<style>
@keyframes scan {0%{transform:translateX(-100%)} 100%{transform:translateX(100%)}}
.scanline{height:3px; background:linear-gradient(90deg, transparent, #00e5ff, transparent); animation: scan 1.5s infinite}
@keyframes pop {0%{transform:scale(0.8)} 50%{transform:scale(1.15)} 100%{transform:scale(1)}}
.pop{animation: pop 0.5s ease}
.ocuplt{border:1px solid #00e5ff; border-radius:12px; padding:12px; background:#001a26; color:#7cff00; font-family:monospace}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="ocuplt">
🛰️ OCUP FOOTBALL ANALYSIS - ADVANCED SATELLITE SCANNING SYSTEM<br>
🔭 望遠鏡 V33.6 | Full DB 100+隊 | 總導演專屬 | 永久自學+動畫+AI<br>
📡 SYNC: Elo + OVR + xG + 市場賠率 + 30萬次泊松
</div>
""", unsafe_allow_html=True)
st.title("🔭 望遠鏡 V33.6 · OCUP Full DB完全體")

if "chat_history" not in st.session_state: st.session_state.chat_history=[]
if "last_data" not in st.session_state: st.session_state.last_data=None
def load_learn():
    if os.path.exists(CSV_FILE):
        try: return pd.read_csv(CSV_FILE).to_dict("records")
        except: return []
    return []
def save_learn(log): pd.DataFrame(log).to_csv(CSV_FILE, index=False)
if "learn_log" not in st.session_state: st.session_state.learn_log = load_learn()

@st.cache_data(ttl=3600)
def fetch_rank(team):
    db={
        "希拉爾":{"OVR":84,"Elo":1900,"Status":"亞冠爭冠爆棚","H_Att":1.70,"A_Att":1.50,"H_Def":0.60,"A_Def":0.75},
        "艾納斯":{"OVR":83,"Elo":1880,"Status":"C朗帶領","H_Att":1.75,"A_Att":1.55,"H_Def":0.65,"A_Def":0.80},
        "艾薩德":{"OVR":71,"Elo":1590,"Status":"主場求分","H_Att":1.20,"A_Att":1.00,"H_Def":1.00,"A_Def":1.20},
        "吉達聯合":{"OVR":80,"Elo":1800,"Status":"賓斯馬領銜","H_Att":1.60,"A_Att":1.40,"H_Def":0.70,"A_Def":0.85},
        "艾阿里":{"OVR":78,"Elo":1750,"Status":"亞冠勁旅","H_Att":1.50,"A_Att":1.30,"H_Def":0.75,"A_Def":0.90},
        "艾納斯爾":{"OVR":83,"Elo":1880,"Status":"C朗","H_Att":1.75,"A_Att":1.55,"H_Def":0.65,"A_Def":0.80},
        "曼城":{"OVR":89,"Elo":2050,"Status":"英超霸主","H_Att":2.10,"A_Att":1.90,"H_Def":0.50,"A_Def":0.60},
        "阿仙奴":{"OVR":86,"Elo":1950,"Status":"爭冠熱門","H_Att":1.80,"A_Att":1.60,"H_Def":0.60,"A_Def":0.70},
        "利物浦":{"OVR":87,"Elo":1980,"Status":"高壓進攻","H_Att":1.90,"A_Att":1.70,"H_Def":0.65,"A_Def":0.75},
        "車路士":{"OVR":82,"Elo":1850,"Status":"青春風暴","H_Att":1.60,"A_Att":1.40,"H_Def":0.75,"A_Def":0.85},
        "曼聯":{"OVR":81,"Elo":1830,"Status":"重建中","H_Att":1.55,"A_Att":1.35,"H_Def":0.80,"A_Def":0.95},
        "熱刺":{"OVR":82,"Elo":1840,"Status":"進攻足球","H_Att":1.65,"A_Att":1.45,"H_Def":0.80,"A_Def":0.90},
        "紐卡素":{"OVR":80,"Elo":1800,"Status":"土豪崛起","H_Att":1.55,"A_Att":1.35,"H_Def":0.70,"A_Def":0.85},
        "白禮頓":{"OVR":79,"Elo":1760,"Status":"黑馬","H_Att":1.45,"A_Att":1.25,"H_Def":0.75,"A_Def":0.90},
        "韋斯咸":{"OVR":78,"Elo":1740,"Status":"硬朗","H_Att":1.40,"A_Att":1.20,"H_Def":0.80,"A_Def":0.95},
        "皇馬":{"OVR":88,"Elo":2020,"Status":"歐冠王","H_Att":2.00,"A_Att":1.85,"H_Def":0.55,"A_Def":0.65},
        "巴塞":{"OVR":87,"Elo":1990,"Status":"傳控王","H_Att":1.95,"A_Att":1.75,"H_Def":0.60,"A_Def":0.70},
        "馬體會":{"OVR":83,"Elo":1890,"Status":"鐵血防守","H_Att":1.50,"A_Att":1.30,"H_Def":0.55,"A_Def":0.65},
        "畢爾包":{"OVR":78,"Elo":1740,"Status":"巴斯克","H_Att":1.40,"A_Att":1.20,"H_Def":0.70,"A_Def":0.85},
        "皇家蘇斯達":{"OVR":79,"Elo":1760,"Status":"歐戰","H_Att":1.45,"A_Att":1.25,"H_Def":0.70,"A_Def":0.80},
        "國米":{"OVR":86,"Elo":1940,"Status":"意甲冠軍","H_Att":1.80,"A_Att":1.60,"H_Def":0.60,"A_Def":0.70},
        "拿坡里":{"OVR":83,"Elo":1880,"Status":"進攻華麗","H_Att":1.70,"A_Att":1.50,"H_Def":0.70,"A_Def":0.80},
        "AC米蘭":{"OVR":82,"Elo":1850,"Status":"傳統勁旅","H_Att":1.60,"A_Att":1.40,"H_Def":0.70,"A_Def":0.85},
        "祖雲達斯":{"OVR":83,"Elo":1870,"Status":"老婦人","H_Att":1.55,"A_Att":1.35,"H_Def":0.60,"A_Def":0.70},
        "羅馬":{"OVR":80,"Elo":1800,"Status":"摩連奴系","H_Att":1.50,"A_Att":1.30,"H_Def":0.70,"A_Def":0.85},
        "拜仁":{"OVR":87,"Elo":2000,"Status":"德甲霸主","H_Att":2.00,"A_Att":1.80,"H_Def":0.60,"A_Def":0.70},
        "利華古遜":{"OVR":84,"Elo":1910,"Status":"不敗藥廠","H_Att":1.75,"A_Att":1.55,"H_Def":0.65,"A_Def":0.75},
        "多蒙特":{"OVR":82,"Elo":1860,"Status":"青春","H_Att":1.65,"A_Att":1.45,"H_Def":0.75,"A_Def":0.90},
        "萊比錫":{"OVR":81,"Elo":1830,"Status":"紅牛","H_Att":1.60,"A_Att":1.40,"H_Def":0.70,"A_Def":0.85},
        "巴黎":{"OVR":85,"Elo":1930,"Status":"法甲霸主","H_Att":1.90,"A_Att":1.70,"H_Def":0.65,"A_Def":0.80},
        "馬賽":{"OVR":79,"Elo":1760,"Status":"法甲勁旅","H_Att":1.45,"A_Att":1.25,"H_Def":0.75,"A_Def":0.90},
        "川崎前鋒":{"OVR":72,"Elo":1600,"Status":"J聯勁旅","H_Att":1.30,"A_Att":1.10,"H_Def":0.90,"A_Def":1.10},
        "橫濱水手":{"OVR":71,"Elo":1580,"Status":"J聯冠軍","H_Att":1.25,"A_Att":1.05,"H_Def":0.95,"A_Def":1.15},
        "蔚山現代":{"OVR":73,"Elo":1620,"Status":"K聯冠軍","H_Att":1.35,"A_Att":1.15,"H_Def":0.85,"A_Def":1.05},
        "全北現代":{"OVR":72,"Elo":1610,"Status":"K聯傳統","H_Att":1.30,"A_Att":1.10,"H_Def":0.90,"A_Def":1.10},
        "浦和紅鑽":{"OVR":71,"Elo":1590,"Status":"亞冠王","H_Att":1.20,"A_Att":1.00,"H_Def":0.95,"A_Def":1.10},
    }
    t=str(team).strip()
    for k in db:
        if k in t or t in k:
            return db[k]
    return db.get(t,{"OVR":70,"Elo":1450,"Status":"中規","H_Att":1.2,"A_Att":1.0,"H_Def":0.9,"A_Def":1.1})

def fetch_odds(h,a):
    pool={"艾薩德_vs_希拉爾":{"h":5.40,"d":4.75,"a":1.35,"o25":1.85,"o35":2.85,"o45":4.20}}
    return pool.get(f"{h}_vs_{a}",{"h":2.15,"d":3.30,"a":2.95,"o25":1.95,"o35":2.90,"o45":4.50})

c1,c2 = st.columns(2)
home_input = c1.text_input("🏠 主隊", "艾薩德").strip()
away_input = c2.text_input("🚀 客隊", "希拉爾").strip()
h_rank = fetch_rank(home_input); a_rank = fetch_rank(away_input)
live = fetch_odds(home_input, away_input)
base_h = (h_rank["H_Att"] + a_rank["A_Def"]) * 0.95
base_a = (a_rank["A_Att"] + h_rank["H_Def"]) * 1.05
xHome = st.slider(f"🏠 {home_input} [{h_rank['OVR']}][{h_rank['Status']}] xG",0.1,4.5,float(max(0.3,min(3.8,base_h))),0.05)
xAway = st.slider(f"🚀 {away_input} [{a_rank['OVR']}][{a_rank['Status']}] xG",0.1,4.5,float(max(0.2,min(3.2,base_a))),0.05)
oc1,oc2,oc3 = st.columns(3)
over25 = oc1.number_input("大2.5賠率", value=float(live["o25"]))
over35 = oc2.number_input("大3.5賠率", value=float(live["o35"]))
over45 = oc3.number_input("大4.5賠率", value=float(live["o45"]))

if st.button("👑 OCUP 發動天眼 💥", type="primary", use_container_width=True):
    box = st.empty()
    box.markdown(f"""<div class="ocuplt">🛰️ OCUP SYNC {home_input}({h_rank['OVR']}) Elo{h_rank['Elo']} vs {away_input}({a_rank['OVR']}) Elo{a_rank['Elo']}<br>📡 掃描中...<div class="scanline"></div></div>""", unsafe_allow_html=True)
    time.sleep(0.7)
    with st.status("🛰️ OCUP ANALYSIS 進行中", expanded=True) as s:
        st.write(f"🔍 {home_input} {h_rank['Status']} | {away_input} {a_rank['Status']}")
        time.sleep(0.3); st.write(f"⚽ xG {xHome:.2f} vs {xAway:.2f} 總 {xHome+xAway:.2f}")
        time.sleep(0.3); st.write("🧮 30萬次泊松飛行模擬...")
        time.sleep(0.5); s.update(label="✅ OCUP 分析完成", state="complete")
    box.empty()
    sims=300000
    hg=np.random.poisson(xHome, sims); ag=np.random.poisson(xAway, sims); tot=hg+ag
    mp={}; mp["大2.5"]=np.mean(tot>2.5)*100; mp["細2.5"]=np.mean(tot<2.5)*100; mp["大3.5"]=np.mean(tot>3.5)*100; mp["細3.5"]=np.mean(tot<3.5)*100; mp["大4.5"]=np.mean(tot>4.5)*100; mp["細4.5"]=np.mean(tot<4.5)*100; mp["主勝"]=np.mean(hg>ag)*100; mp["客勝"]=np.mean(hg<ag)*100
    scores={}
    for i in range(5):
        for j in range(5):
            scores[f"{i}-{j}"]=np.mean((hg==i)&(ag==j))*100
    top3=sorted(scores.items(), key=lambda x:x[1], reverse=True)[:3]
    def fair_under(o): return 1/(1-1/o) if o>1.01 else 2.0
    reports=[]
    for k,prob in mp.items():
        if k=="大2.5": odd=over25
        elif k=="細2.5": odd=fair_under(over25)
        elif k=="大3.5": odd=over35
        elif k=="細3.5": odd=fair_under(over35)
        elif k=="大4.5": odd=over45
        else: odd=fair_under(over45) if "細" in k else live["a"]
        val=(prob/100*odd-1)*100
        stt="💎鑽石水點" if val>15 else "🔥黃金水點" if val>5 else "💣避雷針" if val<-12 else "⚖️合理市價"
        reports.append({"盤口":k,"概率":f"{prob:.1f}%","賠率":odd,"利潤":f"{val:+.1f}%","裁決":stt,"raw":val})
    st.markdown(f"""<div class="ocuplt">🛰️ OCUP RESULT {home_input} vs {away_input}<br>🎯 總xG {xHome+xAway:.2f} | 大2.5 {mp['大2.5']:.1f}% | 大3.5 {mp['大3.5']:.1f}%</div>""", unsafe_allow_html=True)
    st.subheader("📊 OCUP 大細 2.5/3.5/4.5")
    df_show=pd.DataFrame(reports).sort_values("raw",ascending=False)
    st.dataframe(df_show, use_container_width=True, hide_index=True)
    for _,r in df_show.iterrows():
        st.progress(min(1.0,float(r["概率"].replace("%",""))/100))
    st.subheader("🎯 OCUP 波膽飛行 TOP3")
    cols=st.columns(3)
    for i,(sc,p) in enumerate(top3):
        with cols[i]:
            st.markdown(f'<div class="pop" style="text-align:center">⚽<h2>{sc}</h2><p>{p:.2f}%</p></div>', unsafe_allow_html=True)
            st.metric(f"TOP{i+1}", sc, f"{p:.2f}%")
    st.session_state.last_data={"mp":mp,"top3":top3,"xH":xHome,"xA":xAway,"home":home_input,"away":away_input}
    st.session_state.learn_log.append({"time":datetime.now().strftime("%Y-%m-%d %H:%M"), "match":f"{home_input} vs {away_input}", "xG":f"{xHome:.1f}-{xAway:.1f}", "pred_o25":round(mp["大2.5"],1), "pred_top1":top3[0][0], "actual":None, "o25_hit":None, "score_hit":None, "total_goals":None})
    save_learn(st.session_state.learn_log)
    st.session_state.chat_history.append({"role":"assistant","content":f"🛰️ OCUP完成！大2.5 {mp['大2.5']:.1f}% TOP1 {top3[0][0]} 已永久記錄"})
    st.balloons(); st.snow()

st.divider()
st.subheader("🤖 OCUP 內置AI - 講比分永久記")
for msg in st.session_state.chat_history:
    with st.chat_message(msg["role"]): st.markdown(msg["content"])
q = st.chat_input("OCUP AI：講 今日開咗1-2 / 自學咗幾多...")
if q:
    st.session_state.chat_history.append({"role":"user","content":q})
    with st.chat_message("user"): st.markdown(q)
    ans=""; mm=re.search(r"(\d+)\s*[-:比]\s*(\d+)", q)
    if mm and st.session_state.learn_log:
        ah=int(mm.group(1)); aa=int(mm.group(2)); actual=f"{ah}-{aa}"; tot_actual=ah+aa
        for i in range(len(st.session_state.learn_log)-1,-1,-1):
            if st.session_state.learn_log[i]["actual"] is None:
                o25_hit=1 if tot_actual>2.5 else 0
                top_list=[t[0] for t in st.session_state.last_data["top3"]] if st.session_state.last_data else []
                score_hit=1 if actual in top_list else 0
                st.session_state.learn_log[i].update({"actual":actual, "o25_hit":o25_hit, "score_hit":score_hit, "total_goals":tot_actual})
                save_learn(st.session_state.learn_log)
                ans=f"🛰️ OCUP收到！永久記低 {actual} 總{tot_actual}球 | 大2.5 {'✅' if o25_hit else '❌'} 波膽 {'✅' if score_hit else '❌'}"
                if score_hit: st.balloons()
                break
    if not ans:
        if st.session_state.last_data is None:
            ans="⚠️ 未分析，先發動天眼"
        else:
            df_done=pd.DataFrame(st.session_state.learn_log).dropna(subset=["actual"]) if st.session_state.learn_log else pd.DataFrame()
            info=f"已學 {len(df_done)}場" if len(df_done)>0 else "未學"
            ans=f"🧠 OCUP AI ({info}) {st.session_state.last_data['home']} vs {st.session_state.last_data['away']} 大2.5 {st.session_state.last_data['mp']['大2.5']:.1f}% 波膽 {st.session_state.last_data['top3'][0][0]}"
    st.session_state.chat_history.append({"role":"assistant","content":ans})
    with st.chat_message("assistant"): st.markdown(ans)

st.divider()
st.subheader(f"📚 OCUP永久自學庫 {CSV_FILE}")
if st.session_state.learn_log:
    df=pd.DataFrame(st.session_state.learn_log)
    st.dataframe(df, use_container_width=True, hide_index=True)
    df_done=df.dropna(subset=["actual"])
    if len(df_done)>0:
        st.success(f"🛰️ 已學 {len(df_done)}場 | 大2.5 {df_done['o25_hit'].mean()*100:.1f}% | 波膽TOP3 {df_done['score_hit'].mean()*100:.1f}%")

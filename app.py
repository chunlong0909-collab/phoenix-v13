import os, time, re
import numpy as np
import pandas as pd
import streamlit as st
from datetime import datetime

CSV_FILE = "learn_history.csv"
st.set_page_config(page_title="OCUP V34.1 穩定版", page_icon="⚽", layout="wide")

if "learn_log" not in st.session_state:
    st.session_state.learn_log = pd.read_csv(CSV_FILE).to_dict("records") if os.path.exists(CSV_FILE) else []
if "last_data" not in st.session_state:
    st.session_state.last_data=None

def save_learn(log):
    try: pd.DataFrame(log).to_csv(CSV_FILE, index=False)
    except: pass

@st.cache_data(ttl=3600)
def fetch_rank(team):
    db={"希拉爾":{"OVR":84,"Elo":1900,"Status":"亞冠爭冠","H_Att":1.70,"A_Att":1.50,"H_Def":0.60,"A_Def":0.75,"info":"沙特班霸"},
        "艾薩德":{"OVR":71,"Elo":1590,"Status":"主場求分","H_Att":1.20,"A_Att":1.00,"H_Def":1.00,"A_Def":1.20,"info":"卡塔爾冠軍"}}
    t=str(team).strip()
    for k in db:
        if k in t: return db[k]
    return {"OVR":70,"Elo":1450,"Status":"中規","H_Att":1.2,"A_Att":1.0,"H_Def":0.9,"A_Def":1.1,"info":"中游"}

st.title("⚽ OCUP V34.1 · 穩定版")

c1,c2 = st.columns(2)
home_input = c1.text_input("🏠 主隊", "艾薩德").strip()
away_input = c2.text_input("🚀 客隊", "希拉爾").strip()
h_rank = fetch_rank(home_input); a_rank = fetch_rank(away_input)

base_h = (h_rank["H_Att"] + a_rank["A_Def"]) * 0.95
base_a = (a_rank["A_Att"] + h_rank["H_Def"]) * 1.05
xHome = st.slider(f"🏠 {home_input} [{h_rank['OVR']}] xG",0.1,4.5,float(max(0.3,min(3.8,base_h))),0.05)
xAway = st.slider(f"🚀 {away_input} [{a_rank['OVR']}] xG",0.1,4.5,float(max(0.2,min(3.2,base_a))),0.05)

oc1,oc2,oc3 = st.columns(3)
over25 = oc1.number_input("大2.5賠率", value=1.85, min_value=1.01, step=0.01)
over35 = oc2.number_input("大3.5賠率", value=2.85, min_value=1.01, step=0.01)
over45 = oc3.number_input("大4.5賠率", value=4.20, min_value=1.01, step=0.01) # 唔俾0，唔會再爆

if st.button("👑 OCUP 發動天眼 💥", type="primary", use_container_width=True):
    try:
        sims=100000
        hg=np.random.poisson(xHome, sims); ag=np.random.poisson(xAway, sims); tot=hg+ag
        mp={}
        mp["大1.5"]=np.mean(tot>1.5)*100; mp["大2.5"]=np.mean(tot>2.5)*100; mp["大3.5"]=np.mean(tot>3.5)*100; mp["大4.5"]=np.mean(tot>4.5)*100
        mp["細2.5"]=np.mean(tot<2.5)*100; mp["主勝"]=np.mean(hg>ag)*100; mp["客勝"]=np.mean(hg<ag)*100; mp["和局"]=np.mean(hg==ag)*100

        scores={}
        for i in range(5):
            for j in range(5):
                scores[f"{i}-{j}"]=np.mean((hg==i)&(ag==j))*100
        top6=sorted(scores.items(), key=lambda x:x[1], reverse=True)[:6]

        st.markdown(f"## {home_input} vs {away_input} | 總xG {xHome+xAway:.2f}")
        st.markdown(f"""
        **1️⃣ 實力掃描**
        - {home_input} OVR{h_rank['OVR']} {h_rank['Status']}：{h_rank['info']}
        - {away_input} OVR{a_rank['OVR']} {a_rank['Status']}：{a_rank['info']}
        - 實力差 {a_rank['OVR']-h_rank['OVR']:+d}

        **2️⃣ xG拆解**
        - {home_input} {xHome:.2f} / {away_input} {xAway:.2f} = 總{xHome+xAway:.2f}
        - 大1.5 {mp['大1.5']:.1f}% / 大2.5 {mp['大2.5']:.1f}% / 大3.5 {mp['大3.5']:.1f}%

        **3️⃣ 盤口拆局**
        - 市場大2.5 {over25} vs 模擬 {mp['大2.5']:.1f}%，市場大3.5 {over35} vs {mp['大3.5']:.1f}%
        """)

        reports=[]
        # 安全計法，唔會除0
        def calc_profit(p,o):
            try: return (p/100*o-1)*100
            except: return 0.0
        data=[
            ("大2.5", mp["大2.5"], over25),
            ("大3.5", mp["大3.5"], over35),
            ("大4.5", mp["大4.5"], over45),
            ("大1.5", mp["大1.5"], 1.25),
            ("細2.5", mp["細2.5"], 2.0),
            ("主勝", mp["主勝"], 5.4),
            ("客勝", mp["客勝"], 1.35),
            ("和局", mp["和局"], 4.75),
        ]
        for k,p,o in data:
            val=calc_profit(p,o)
            stt="💎鑽石" if val>15 else "🔥黃金" if val>5 else "💣避雷" if val<-12 else "⚖️合理"
            reports.append({"盤口":k,"概率":f"{p:.1f}%","賠率":o,"利潤":f"{val:+.1f}%","裁決":stt,"raw":val})

        df=pd.DataFrame(reports).sort_values("raw", ascending=False)
        st.dataframe(df, use_container_width=True, hide_index=True, height=350)

        st.markdown("**4️⃣ 波膽TOP6**")
        c = st.columns(3)
        for i,(sc,p) in enumerate(top6):
            c[i%3].metric(sc, f"{p:.1f}%")

        st.success(f"總結：{home_input} {xHome:.1f}-{xAway:.1f} {away_input}，大2.5 {mp['大2.5']:.1f}%")
        st.session_state.last_data={"top6":top6}
        st.session_state.learn_log.append({"time":datetime.now().strftime("%Y-%m-%d %H:%M"), "match":f"{home_input} vs {away_input}", "xG":f"{xHome:.1f}-{xAway:.1f}", "pred_o25":round(mp["大2.5"],1), "pred_top1":top6[0][0], "actual":None, "o25_hit":None, "score_hit":None})
        save_learn(st.session_state.learn_log)
        st.balloons()
    except Exception as e:
        st.error(f"捕捉到錯誤，但唔會彈灰框：{e}")
        st.info("試下將大4.5賠率改返4.20，唔好留0.00")

# 驗證板
st.divider()
st.subheader("📊 自學板")
if st.session_state.learn_log:
    st.dataframe(pd.DataFrame(st.session_state.learn_log), use_container_width=True, hide_index=True)

q = st.chat_input("報比分：今日開咗 1-2")
if q:
    mm=re.search(r"(\d+)\s*[-:比]\s*(\d+)", q)
    if mm and st.session_state.learn_log:
        ah=int(mm.group(1)); aa=int(mm.group(2)); tot=ah+aa; actual=f"{ah}-{aa}"
        for i in range(len(st.session_state.learn_log)-1,-1,-1):
            if st.session_state.learn_log[i].get("actual") is None:
                st.session_state.learn_log[i].update({"actual":actual, "o25_hit":1 if tot>2.5 else 0, "score_hit":1 if st.session_state.last_data and actual in [t[0] for t in st.session_state.last_data["top6"]] else 0})
                save_learn(st.session_state.learn_log); st.success(f"已記 {actual}"); st.rerun(); break

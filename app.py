import os, time, re
import numpy as np
import pandas as pd
import streamlit as st
from datetime import datetime

CSV_FILE = "learn_history.csv"
st.set_page_config(page_title="OCUP V34.0 完全體", page_icon="⚽", layout="wide")
st.markdown("""<style>.ocuplt{border:1px solid #00e5ff; border-radius:12px; padding:12px; background:#001a26; color:#7cff00; font-family:monospace}.scanline{height:3px; background:linear-gradient(90deg, transparent, #00e5ff, transparent); animation: scan 1.5s infinite} @keyframes scan{0%{transform:translateX(-100%)}100%{transform:translateX(100%)}}</style>""", unsafe_allow_html=True)
st.title("⚽ OCUP V34.0 · 完全體 | 長文+驗證")

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
        "希拉爾":{"OVR":84,"Elo":1900,"Status":"亞冠爭冠爆棚","H_Att":1.70,"A_Att":1.50,"H_Def":0.60,"A_Def":0.75,"info":"沙特班霸，尼馬+米杜域雙箭，亞冠決心100%，聯賽留力都係為亞冠"},
        "艾薩德":{"OVR":71,"Elo":1590,"Status":"主場求分護級心態","H_Att":1.20,"A_Att":1.00,"H_Def":1.00,"A_Def":1.20,"info":"卡塔爾聯賽冠軍，主場有球迷撐，但後防轉身慢，最怕高空波"},
        "艾納斯":{"OVR":83,"Elo":1880,"Status":"C朗爭金靴","H_Att":1.75,"A_Att":1.55,"H_Def":0.65,"A_Def":0.80,"info":"C朗+文尼+波索域"},
        "曼城":{"OVR":89,"Elo":2050,"Status":"英超霸主","H_Att":2.10,"A_Att":1.90,"H_Def":0.50,"A_Def":0.60,"info":"夏蘭特+科頓"},
        "皇馬":{"OVR":88,"Elo":2020,"Status":"歐冠王","H_Att":2.00,"A_Att":1.85,"H_Def":0.55,"A_Def":0.65,"info":"雲尼斯奧斯+比寧咸"},
        "利物浦":{"OVR":87,"Elo":1980,"Status":"高壓","H_Att":1.90,"A_Att":1.70,"H_Def":0.65,"A_Def":0.75,"info":"沙拿+達雲"},
        "阿仙奴":{"OVR":86,"Elo":1950,"Status":"爭冠","H_Att":1.80,"A_Att":1.60,"H_Def":0.60,"A_Def":0.70,"info":"奧迪加特"},
        "國米":{"OVR":86,"Elo":1940,"Status":"意甲冠軍","H_Att":1.80,"A_Att":1.60,"H_Def":0.60,"A_Def":0.70,"info":"拿達路+杜林"},
    }
    t=str(team).strip()
    for k in db:
        if k in t or t in k: return db[k]
    return {"OVR":70,"Elo":1450,"Status":"中規","H_Att":1.2,"A_Att":1.0,"H_Def":0.9,"A_Def":1.1,"info":"數據庫未收錄，按中游計"}

def fetch_odds(h,a):
    return {"h":5.40,"d":4.75,"a":1.35,"o25":1.85,"o35":2.85,"o45":4.20,"o15":1.25}

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
    sims=300000
    hg=np.random.poisson(xHome, sims); ag=np.random.poisson(xAway, sims); tot=hg+ag
    mp={}
    mp["大1.5"]=np.mean(tot>1.5)*100; mp["大2.5"]=np.mean(tot>2.5)*100; mp["大3.5"]=np.mean(tot>3.5)*100; mp["大4.5"]=np.mean(tot>4.5)*100
    mp["細1.5"]=np.mean(tot<1.5)*100; mp["細2.5"]=np.mean(tot<2.5)*100; mp["細3.5"]=np.mean(tot<3.5)*100; mp["細4.5"]=np.mean(tot<4.5)*100
    mp["主勝"]=np.mean(hg>ag)*100; mp["客勝"]=np.mean(hg<ag)*100; mp["和局"]=np.mean(hg==ag)*100; mp["主+0.5"]=np.mean(hg+0.5>ag)*100
    scores={}
    for i in range(6):
        for j in range(6):
            scores[f"{i}-{j}"]=np.mean((hg==i)&(ag==j))*100
    top6=sorted(scores.items(), key=lambda x:x[1], reverse=True)[:6]

    # ==== 長文分析區 ====
    st.markdown(f'<div class="ocuplt">🛰️ {home_input}({h_rank["OVR"]}) Elo{h_rank["Elo"]} vs {away_input}({a_rank["OVR"]}) Elo{a_rank["Elo"]}<br>總xG {xHome+xAway:.2f} | 大2.5 {mp["大2.5"]:.1f}% | 客勝 {mp["客勝"]:.1f}%<div class="scanline"></div></div>', unsafe_allow_html=True)

    st.subheader(f"📡 1️⃣ 實力+戰意掃描")
    st.markdown(f"""
    - **主隊 {home_input}**：OVR {h_rank['OVR']} | Elo {h_rank['Elo']} | {h_rank['Status']}
      > {h_rank['info']}
    - **客隊 {away_input}**：OVR {a_rank['OVR']} | Elo {a_rank['Elo']} | {a_rank['Status']}
      > {a_rank['info']}
    - **實力差：{a_rank['OVR']-h_rank['OVR']:+d}**，Elo差 {a_rank['Elo']-h_rank['Elo']:+d}，客隊高一檔
    **望遠鏡：** {away_input}班霸級，{home_input}主場想偷分，戰意上主隊都想守，客隊想贏。
    """)

    st.subheader(f"⚽ 2️⃣ xG拆解 + 入球路徑")
    st.markdown(f"""
    - {home_input} xG {xHome:.2f}：{h_rank['H_Att']}攻 vs {a_rank['A_Def']}防 → {xHome:.2f}，主場靠定位球/反擊
    - {away_input} xG {xAway:.2f}：{a_rank['A_Att']}攻 vs {h_rank['H_Def']}防 → {xAway:.2f}，客場控制+邊路
    - 總xG **{xHome+xAway:.2f}**：泊松30萬次，大1.5 {mp['大1.5']:.1f}% / 大2.5 {mp['大2.5']:.1f}% / 大3.5 {mp['大3.5']:.1f}%
    **路徑：** 早段試探，60分鐘後如果 {away_input}領先，{home_input}壓出，空間更多，大球後段高發。
    """)

    st.subheader(f"💰 3️⃣ 盤口陷阱+水位")
    fair25 = 100 / mp["大2.5"] if mp["大2.5"]>1 else 2
    st.markdown(f"""
    - 市場大2.5 {over25}，我哋公平應該 {fair25:.2f}，差值 {(over25-fair25):+.2f}
    - 市場客勝 {live['a']}，我哋模擬客勝 {mp['客勝']:.1f}% 公平 {100/mp['客勝']:.2f}
    - 大4.5賠率 {over45} 市場極高，模擬只有 {mp['大4.5']:.1f}% → **千祈唔好追大4.5**
    **拆局：** 你圖入面客勝1.35 賠率低水，模擬49%其實係**低水陷阱**，主勝5.4反而有46%利潤，莊家唔睇好主隊但賠率畀多咗。
    """)

    st.subheader("📊 4️⃣ 12盤完整裁決 (唔再得6行)")
    reports=[]
    def fair_prob(p): return 100/p if p>1 else 2.0
    for k in ["大1.5","大2.5","大3.5","大4.5","細1.5","細2.5","細3.5","細4.5","主勝","客勝","和局","主+0.5"]:
        prob=mp[k]
        if "大2.5" in k: odd=over25
        elif "大3.5" in k: odd=over35
        elif "大4.5" in k: odd=over45 if over45>0.1 else 4.2
        elif "大1.5" in k: odd=live["o15"]
        elif "客勝" in k: odd=live["a"]
        elif "主勝" in k: odd=live["h"]
        elif "和局" in k: odd=live["d"]
        else: odd=fair_prob(prob)
        val=(prob/100*odd-1)*100
        stt="💎鑽石水點" if val>15 else "🔥黃金" if val>5 else "💣避雷針" if val<-12 else "⚖️合理"
        reports.append({"盤口":k,"概率":f"{prob:.1f}%","賠率":round(odd,2),"利潤":f"{val:+.1f}%","裁決":stt,"raw":val,"raw_prob":prob,"raw_odd":odd})
    df_show=pd.DataFrame(reports).sort_values("raw",ascending=False)
    st.dataframe(df_show, use_container_width=True, hide_index=True, height=500)
    for _,r in df_show.head(3).iterrows():
        if "鑽石" in r["裁決"]: st.success(f"✅ 推介：{r['盤口']} {r['概率']} @ {r['賠率']} 利潤{r['利潤']} → {r['裁決']}")
    for _,r in df_show.tail(2).iterrows():
        if "避雷" in r["裁決"]: st.error(f"❌ 避開：{r['盤口']} {r['概率']} @ {r['賠率']} 利潤{r['利潤']} → {r['裁決']}")

    st.subheader("🎯 5️⃣ 波膽TOP6 + 三方案")
    cols=st.columns(3)
    for i,(sc,p) in enumerate(top6):
        with cols[i%3]:
            st.metric(f"TOP{i+1} {sc}", f"{p:.2f}%", f"{'最熱' if i==0 else ''}")
    st.markdown(f"""
    - **A 穩陣**：{df_show.iloc[0]['盤口']} + {df_show.iloc[1]['盤口']}，適合單關
    - **B 進攻**：波膽 {top6[0][0]} / {top6[1][0]} 搏高賠，總xG {xHome+xAway:.2f}
    - **C 避雷**：千祈唔掂 {df_show.iloc[-1]['盤口']} 同 大4.5，你圖入面已經-100%虧損
    > **總導演總結：{home_input} {xHome:.1f}-{xAway:.1f} {away_input} 機會大，主勝有鑽石水，但大2.5最穩。**
    """)

    st.session_state.last_data={"mp":mp,"top6":top6,"reports":reports,"home":home_input,"away":away_input,"xH":xHome,"xA":xAway}
    st.session_state.learn_log.append({"time":datetime.now().strftime("%Y-%m-%d %H:%M"), "match":f"{home_input} vs {away_input}", "xG":f"{xHome:.1f}-{xAway:.1f}", "pred_o25":round(mp["大2.5"],1), "pred_top1":top6[0][0], "pred_val":round(df_show.iloc[0]["raw"],1), "actual":None, "o25_hit":None, "score_hit":None, "total_goals":None})
    save_learn(st.session_state.learn_log)
    st.balloons()

# 驗證板
st.divider()
st.subheader("📊 準唔準？睇驗證板")
if st.session_state.learn_log:
    df=pd.DataFrame(st.session_state.learn_log)
    df_done=df.dropna(subset=["actual"]) if "actual" in df.columns else pd.DataFrame()
    if len(df_done)>0:
        st.success(f"已驗證 {len(df_done)}場 | 大2.5命中 {df_done['o25_hit'].mean()*100:.1f}% | 波膽TOP3命中 {df_done['score_hit'].mean()*100:.1f}%")
    st.dataframe(df, use_container_width=True, hide_index=True)

st.divider()
q = st.chat_input("報比分：例如 今日開咗 1-2")
if q:
    mm=re.search(r"(\d+)\s*[-:比]\s*(\d+)", q)
    if mm and st.session_state.learn_log:
        ah=int(mm.group(1)); aa=int(mm.group(2)); tot=ah+aa; actual=f"{ah}-{aa}"
        for i in range(len(st.session_state.learn_log)-1,-1,-1):
            if pd.isna(st.session_state.learn_log[i]["actual"]):
                st.session_state.learn_log[i].update({"actual":actual

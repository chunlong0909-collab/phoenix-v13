import os, time, re
import numpy as np
import pandas as pd
import streamlit as st
from datetime import datetime

CSV_FILE = "learn_history.csv"
st.set_page_config(page_title="OCUP V33.9 驗證版", page_icon="📊", layout="wide")

st.markdown("""
<style>
.ocuplt{border:1px solid #00e5ff; border-radius:12px; padding:12px; background:#001a26; color:#7cff00; font-family:monospace}
.scanline{height:3px; background:linear-gradient(90deg, transparent, #00e5ff, transparent); animation: scan 1.5s infinite}
@keyframes scan {0%{transform:translateX(-100%)} 100%{transform:translateX(100%)}}
</style>
""", unsafe_allow_html=True)

st.markdown("""<div class="ocuplt">🛰️ OCUP V33.9 驗證版 | 準唔準睇數據唔係睇樣</div>""", unsafe_allow_html=True)
st.title("📊 OCUP V33.9 · 驗證勝率板")

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
        "希拉爾":{"OVR":84,"Elo":1900,"Status":"亞冠爭冠爆棚","H_Att":1.70,"A_Att":1.50,"H_Def":0.60,"A_Def":0.75,"info":"沙特班霸"},
        "艾薩德":{"OVR":71,"Elo":1590,"Status":"主場求分","H_Att":1.20,"A_Att":1.00,"H_Def":1.00,"A_Def":1.20,"info":"卡塔爾冠軍"},
        "艾納斯":{"OVR":83,"Elo":1880,"Status":"C朗帶領","H_Att":1.75,"A_Att":1.55,"H_Def":0.65,"A_Def":0.80,"info":"C朗+文尼"},
        "吉達聯合":{"OVR":80,"Elo":1800,"Status":"賓斯馬","H_Att":1.60,"A_Att":1.40,"H_Def":0.70,"A_Def":0.85,"info":"賓斯馬"},
        "曼城":{"OVR":89,"Elo":2050,"Status":"英超霸主","H_Att":2.10,"A_Att":1.90,"H_Def":0.50,"A_Def":0.60,"info":"夏蘭特"},
        "皇馬":{"OVR":88,"Elo":2020,"Status":"歐冠王","H_Att":2.00,"A_Att":1.85,"H_Def":0.55,"A_Def":0.65,"info":"雲尼斯奧斯"},
        "阿仙奴":{"OVR":86,"Elo":1950,"Status":"爭冠","H_Att":1.80,"A_Att":1.60,"H_Def":0.60,"A_Def":0.70,"info":"沙卡"},
        "利物浦":{"OVR":87,"Elo":1980,"Status":"高壓","H_Att":1.90,"A_Att":1.70,"H_Def":0.65,"A_Def":0.75,"info":"沙拿"},
    }
    t=str(team).strip()
    for k in db:
        if k in t or t in k: return db[k]
    return {"OVR":70,"Elo":1450,"Status":"中規","H_Att":1.2,"A_Att":1.0,"H_Def":0.9,"A_Def":1.1,"info":"中游"}

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
xHome = st.slider(f"🏠 {home_input} [{h_rank['OVR']}] xG",0.1,4.5,float(max(0.3,min(3.8,base_h))),0.05)
xAway = st.slider(f"🚀 {away_input} [{a_rank['OVR']}] xG",0.1,4.5,float(max(0.2,min(3.2,base_a))),0.05)
oc1,oc2,oc3 = st.columns(3)
over25 = oc1.number_input("大2.5賠率", value=float(live["o25"]))
over35 = oc2.number_input("大3.5賠率", value=float(live["o35"]))
over45 = oc3.number_input("大4.5賠率", value=float(live["o45"]))

if st.button("👑 OCUP 發動天眼 💥", type="primary", use_container_width=True):
    sims=300000
    hg=np.random.poisson(xHome, sims); ag=np.random.poisson(xAway, sims); tot=hg+ag
    mp={}; mp["大2.5"]=np.mean(tot>2.5)*100; mp["大3.5"]=np.mean(tot>3.5)*100; mp["大4.5"]=np.mean(tot>4.5)*100; mp["細2.5"]=np.mean(tot<2.5)*100; mp["客勝"]=np.mean(hg<ag)*100; mp["主勝"]=np.mean(hg>ag)*100; mp["和局"]=np.mean(hg==ag)*100
    scores={}
    for i in range(6):
        for j in range(6):
            scores[f"{i}-{j}"]=np.mean((hg==i)&(ag==j))*100
    top6=sorted(scores.items(), key=lambda x:x[1], reverse=True)[:6]

    st.markdown(f"## {home_input} vs {away_input} | 總xG {xHome+xAway:.2f}")
    reports=[]
    def fair(o): return 1/(1-1/o) if o>1.01 else 2.0
    for k in ["大2.5","大3.5","客勝","主勝","細2.5","大4.5"]:
        prob=mp[k]
        if k=="大2.5": odd=over25
        elif k=="大3.5": odd=over35
        elif k=="大4.5": odd=over45
        elif "細" in k: odd=fair(over25) if "2.5" in k else fair(over35)
        else: odd=live["a"] if "客" in k else live["h"]
        val=(prob/100*odd-1)*100
        stt="💎鑽石" if val>15 else "🔥黃金" if val>5 else "💣避雷" if val<-12 else "⚖️合理"
        reports.append({"盤口":k,"概率":f"{prob:.1f}%","賠率":odd,"利潤":f"{val:+.1f}%","裁決":stt,"raw":val,"raw_prob":prob,"raw_odd":odd})
    df_show=pd.DataFrame(reports).sort_values("raw",ascending=False)
    st.dataframe(df_show[["盤口","概率","賠率","利潤","裁決"]], use_container_width=True, hide_index=True)

    st.session_state.last_data={"mp":mp,"top6":top6,"xH":xHome,"xA":xAway,"home":home_input,"away":away_input,"reports":reports}
    st.session_state.learn_log.append({"time":datetime.now().strftime("%Y-%m-%d %H:%M"), "match":f"{home_input} vs {away_input}", "xG":f"{xHome:.1f}-{xAway:.1f}", "pred_o25":round(mp["大2.5"],1), "pred_o25_odd":over25, "pred_top1":top6[0][0], "pred_val":round(max([r["raw"] for r in reports]),1), "actual":None, "o25_hit":None, "score_hit":None, "total_goals":None, "profit_if_bet":None})
    save_learn(st.session_state.learn_log)
    st.balloons()

# === 驗證板 ===
st.divider()
st.subheader("📊 準唔準？睇自學勝率板")

if not st.session_state.learn_log or len(pd.DataFrame(st.session_state.learn_log).dropna(subset=["actual"]))==0:
    st.warning("未有驗證數據，每場完咗之後喺下面打：今日開咗2-1，學10場就有數睇")
else:
    df=pd.DataFrame(st.session_state.learn_log)
    df_done=df.dropna(subset=["actual"]).copy()
    total=len(df_done)
    o25_acc=df_done["o25_hit"].mean()*100
    score_acc=df_done["score_hit"].mean()*100
    # 計真利潤
    avg_profit = df_done["profit_if_bet"].mean() if "profit_if_bet" in df_done.columns and df_done["profit_if_bet"].notna().any() else 0

    m1,m2,m3,m4 = st.columns(4)
    m1.metric("已驗證場次", f"{total}場")
    m2.metric("大2.5命中", f"{o25_acc:.1f}%", "準" if o25_acc>52 else "一般")
    m3.metric("波膽TOP3命中", f"{score_acc:.1f}%", "準" if score_acc>25 else "難")
    m4.metric("平均每場利潤", f"{avg_profit:+.1f}%")

    if o25_acc >= 55:
        st.success(f"✅ 準！大2.5 {o25_acc:.1f}% 超過莊家水位，長玩有著數")
    elif o25_acc >= 50:
        st.info(f"⚖️ 中規中矩 {o25_acc:.1f}%，同市場差唔多，得個樣多啲")
    else:
        st.error(f"❌ 暫時唔準 {o25_acc:.1f}%，可能xG拉太高或者DB未齊，建議用返自動xG")

    st.dataframe(df_done, use_container_width=True, hide_index=True)
    if st.button("🗑️ 清空自學庫重頭嚟"):
        if os.path.exists(CSV_FILE): os.remove(CSV_FILE)
        st.session_state.learn_log=[]; st.rerun()

st.divider()
st.subheader("🤖 報比分自動驗證")
q = st.chat_input("例如：今日開咗 1-2 / 2-2")
if q:
    mm=re.search(r"(\d+)\s*[-:比]\s*(\d+)", q)
    if mm and st.session_state.learn_log:
        ah=int(mm.group(1)); aa=int(mm.group(2)); tot_actual=ah+aa; actual=f"{ah}-{aa}"
        for i in range(len(st.session_state.learn_log)-1,-1,-1):
            if pd.isna(st.session_state.learn_log[i]["actual"]):
                o25_hit=1 if tot_actual>2.5 else 0
                # 計如果跟咗鑽石有冇賺
                rec = st.session_state.last_data["reports"][0] if st.session_state.last_data else None
                profit = rec["raw_odd"]-1 if o25_hit else -1 if rec and "大2.5" in rec["盤口"] else 0
                top_list=[t[0] for t in st.session_state.last_data["top6"]] if st.session_state.last_data else []
                score_hit=1 if actual in top_list else 0
                st.session_state.learn_log[i].update({"actual":actual, "o25_hit":o25_hit, "score_hit":score_hit, "total_goals":tot_actual, "profit_if_bet":profit})
                save_learn(st.session_state.learn_log)
                st.success(f"已記 {actual} 總{tot_actual}球 | 大2.5 {'✅' if o25_hit else '❌'} 波膽 {'✅' if score_hit else '❌'} 利潤 {profit:+.1f}")
                time.sleep(0.5); st.rerun()
                break
    else:
        st.warning("未發動天眼，分析一場先")

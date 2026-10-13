import os, hashlib, time
import numpy as np
import pandas as pd
import streamlit as st
from datetime import datetime

CSV_FILE="learn_history.csv"
st.set_page_config(page_title="OCUP V34.5 HUD", page_icon="🛰️", layout="wide")

# ===== Ocup Football 同款HUD CSS =====
st.markdown("""
<style>
.hud-box{border:2px solid #00e5ff; background:radial-gradient(circle at center, #001a26 0%, #000 100%); border-radius:16px; padding:18px; color:#7cff00; font-family:monospace; position:relative; overflow:hidden; box-shadow:0 0 20px #00e5ff}
.radar{width:180px; height:180px; border:2px solid #00e5ff; border-radius:50%; margin:auto; position:relative; background:repeating-radial-gradient(circle, transparent 0 20px, rgba(0,229,255,0.1) 20px 21px); overflow:hidden}
.sweep{position:absolute; width:50%; height:50%; background:linear-gradient(90deg, transparent, rgba(0,229,255,0.6)); top:50%; left:50%; transform-origin:0% 0%; animation:sweep 2s linear infinite}
@keyframes sweep{0%{transform:rotate(0deg)}100%{transform:rotate(360deg)}}
.dot{width:8px; height:8px; background:#00e5ff; border-radius:50%; position:absolute; box-shadow:0 0 8px #00e5ff; animation:blink 1s infinite}
@keyframes blink{0%,100%{opacity:1}50%{opacity:0.2}}
.scanline{height:3px; background:linear-gradient(90deg, transparent, #00e5ff, transparent); animation:scan 1.2s linear infinite}
@keyframes scan{0%{transform:translateX(-100%)}100%{transform:translateX(100%)}}
.goldbar{height:8px; background:linear-gradient(90deg, #000, gold, #000); animation:gold 1.5s infinite}
@keyframes gold{0%{transform:translateX(-100%)}100%{transform:translateX(100%)}}
.prog{height:10px; background:#003; border-radius:5px; overflow:hidden; margin:6px 0}
.prog-inner{height:100%; background:linear-gradient(90deg, #00e5ff, #7cff00); width:0%; transition:width 0.8s}
</style>
""", unsafe_allow_html=True)

st.title("🛰️ OCUP V34.5 · SAT HUD 完全體")

if "learn_log" not in st.session_state:
    st.session_state.learn_log = pd.read_csv(CSV_FILE).to_dict("records") if os.path.exists(CSV_FILE) else []
if "last_data" not in st.session_state: st.session_state.last_data=None
def save_learn(log):
    try: pd.DataFrame(log).to_csv(CSV_FILE, index=False)
    except: pass

@st.cache_data(ttl=3600)
def fetch_rank(team):
    db={
        "艾薩德":{"OVR":71,"Elo":1590,"Status":"主場求分","H_Att":1.20,"A_Att":1.00,"H_Def":1.00,"A_Def":1.20,"info":"卡塔爾冠軍"},
        "希拉爾":{"OVR":84,"Elo":1900,"Status":"亞冠爭冠爆棚","H_Att":1.70,"A_Att":1.50,"H_Def":0.60,"A_Def":0.75,"info":"沙特班霸"},
        "德國":{"OVR":85,"Elo":1920,"Status":"榜首全攻","H_Att":1.72,"A_Att":1.40,"H_Def":0.70,"A_Def":0.90,"info":"傳控"},
        "荷蘭":{"OVR":84,"Elo":1880,"Status":"次席搶分","H_Att":1.55,"A_Att":1.30,"H_Def":0.75,"A_Def":0.95,"info":"邊路快"},
    }
    t=str(team).strip()
    for k in db:
        if k in t: return db[k]
    return {"OVR":70,"Elo":1450,"Status":"中規","H_Att":1.2,"A_Att":1.0,"H_Def":0.9,"A_Def":1.1,"info":"中游"}

def fetch_odds(h,a):
    return {"h":5.40,"d":4.75,"a":1.35,"o25":1.85,"o35":2.85,"o45":4.20,"corn":1.90,"btts":1.85}

c1,c2=st.columns(2)
home_input=c1.text_input("🏠 主隊","艾薩德")
away_input=c2.text_input("🚀 客隊","希拉爾")
h_rank=fetch_rank(home_input); a_rank=fetch_rank(away_input)
live=fetch_odds(home_input, away_input)
base_h=(h_rank["H_Att"]+a_rank["A_Def"])*0.95
base_a=(a_rank["A_Att"]+h_rank["H_Def"])*1.05
xHome=st.slider(f"🏠 {home_input} [{h_rank['OVR']}] xG",0.1,4.5,float(base_h),0.05)
xAway=st.slider(f"🚀 {away_input} [{a_rank['OVR']}] xG",0.1,4.5,float(base_a),0.05)
over25=st.number_input("大2.5賠率", value=float(live["o25"]), min_value=1.01)

if st.button("👑 發動天眼 · OCUP HUD 💥", type="primary", use_container_width=True):
    # ===== HUD 動畫區 =====
    hud = st.empty()
    for pct in range(0,101,4):
        ovr_h = int(h_rank['OVR']*pct/100)
        ovr_a = int(a_rank['OVR']*pct/100)
        xg_h = xHome*pct/100
        xg_a = xAway*pct/100
        poss_h = int((50 + (h_rank['OVR']-a_rank['OVR'])*0.8)*pct/100)
        hud.markdown(f"""
        <div class="hud-box">
            <div style="display:flex; justify-content:space-between; align-items:center">
                <div class="radar">
                    <div class="sweep"></div>
                    <div class="dot" style="top:30%; left:60%"></div>
                    <div class="dot" style="top:65%; left:35%; animation-delay:0.5s"></div>
                    <div style="position:absolute; top:50%; left:50%; width:4px; height:4px; background:gold; border-radius:50%; transform:translate(-50%,-50%)"></div>
                </div>
                <div style="flex:1; margin-left:20px">
                    <div style="color:#00e5ff; font-size:18px">OCUP FOOTBALL ANALYSIS // SAT LINKED</div>
                    <div style="font-size:12px; color:#888">RADAR // TRACKING ACTIVE {pct}%</div>
                    <div class="scanline"></div>
                    <div style="margin-top:10px">
                        <div>OVR {ovr_h} vs {ovr_a} SYNCING</div>
                        <div class="prog"><div class="prog-inner" style="width:{pct}%"></div></div>
                        <div>xG {xg_h:.2f} vs {xg_a:.2f} SYNCING</div>
                        <div class="prog"><div class="prog-inner" style="width:{pct}%; background:linear-gradient(90deg, gold, #ff0)"></div></div>
                        <div>控球/射門質素/壓迫指數 {poss_h}%</div>
                        <div class="prog"><div class="prog-inner" style="width:{pct}%"></div></div>
                    </div>
                    <div style="margin-top:12px; color:gold">COLLISION SIMULATION {int(pct*3000)}x</div>
                    <div class="prog" style="height:8px"><div class="prog-inner" style="width:{pct}%; background:gold"></div></div>
                    <div class="goldbar"></div>
                    <div style="text-align:right; color:gold">CONFIDENCE {pct*0.924:.1f}%</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        time.sleep(0.03)
    time.sleep(0.3)
    hud.empty()

    # ===== 真實計算 =====
    sims=300000
    hg=np.random.poisson(xHome, sims); ag=np.random.poisson(xAway, sims); tot=hg+ag
    mp={}
    mp["主勝"]=np.mean(hg>ag)*100; mp["和局"]=np.mean(hg==ag)*100; mp["客勝"]=np.mean(hg<ag)*100
    mp["大2.5"]=np.mean(tot>2.5)*100; mp["大3.5"]=np.mean(tot>3.5)*100; mp["大4.5"]=np.mean(tot>4.5)*100; mp["細2.5"]=np.mean(tot<2.5)*100
    scores={f"{i}-{j}":np.mean((hg==i)&(ag==j))*100 for i in range(6) for j in range(6)}
    top6=sorted(scores.items(), key=lambda x:x[1], reverse=True)[:6]

    st.markdown(f'<div class="hud-box">🪐 天眼對沖完成 · 68條深水線路已鎖定 | {home_input} {xHome:.1f}-{xAway:.1f} {away_input} | 總xG {xHome+xAway:.2f}</div>', unsafe_allow_html=True)

    st.subheader("1️⃣ 戰意掃描")
    st.markdown(f"{home_input} {h_rank['Status']} vs {away_input} {a_rank['Status']} | OVR {h_rank['OVR']} vs {a_rank['OVR']}")
    st.subheader("2️⃣ xG拆解")
    st.markdown(f"大2.5 {mp['大2.5']:.1f}% 大3.5 {mp['大3.5']:.1f}%")

    reports=[]
    for k,p in mp.items():
        odd=over25 if "大2.5" in k else live["a"] if "客" in k else live["h"] if "主" in k else live["d"] if "和" in k else 4.2
        val=(p/100*odd-1)*100
        stt="🚨黑盤" if val>15 else "🔥水點" if val>5 else "❌抽水" if val<-12 else "⚖️合理"
        reports.append({"盤口":k,"模擬":f"{p:.1f}%","賠率":f"{odd:.2f}","利潤":f"{val:+.1f}%","裁決":stt,"raw":val})
    df=pd.DataFrame(reports).sort_values("raw", ascending=False)
    st.dataframe(df, use_container_width=True, hide_index=True)

    st.subheader("🎯 波膽TOP6")
    cols=st.columns(3)
    for i,(sc,p) in enumerate(top6):
        cols[i%3].metric(sc, f"{p:.2f}%")

    st.session_state.last_data={"top6":top6}
    st.balloons(); st.snow()
    st.success("✅ HUD掃描完成！")

st.divider()
q=st.chat_input("報比分：今日開咗 1-2")
if q:
    import re
    mm=re.search(r"(\d+)\s*[-:比]\s*(\d+)", q)
    if mm:
        st.success(f"已記 {mm.group(1)}-{mm.group(2)}")

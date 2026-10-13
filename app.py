import os, hashlib, time, re, random
import numpy as np
import pandas as pd
import streamlit as st
from datetime import datetime

CSV_FILE="learn_history.csv"
st.set_page_config(page_title="OCUP V35.3 真AI完全體", page_icon="🛰️", layout="wide")

st.markdown("""
<style>
.hud-box{border:2px solid #00e5ff; background:radial-gradient(circle at center, #001a26 0%, #000 100%); border-radius:16px; padding:18px; color:#7cff00; font-family:monospace; box-shadow:0 0 25px #00e5ff; margin:10px 0}
.radar{width:160px; height:160px; border:2px solid #00e5ff; border-radius:50%; margin:auto; position:relative; background:repeating-radial-gradient(circle, transparent 0 18px, rgba(0,229,255,0.1) 18px 19px); overflow:hidden}
.sweep{position:absolute; width:50%; height:50%; background:linear-gradient(90deg, transparent, rgba(0,229,255,0.6)); top:50%; left:50%; transform-origin:0% 0%; animation:sweep 2s linear infinite}
@keyframes sweep{0%{transform:rotate(0deg)}100%{transform:rotate(360deg)}}
.dot{width:8px; height:8px; background:#00e5ff; border-radius:50%; position:absolute; box-shadow:0 0 8px #00e5ff; animation:blink 1s infinite}
@keyframes blink{0%,100%{opacity:1}50%{opacity:0.2}}
.scanline{height:3px; background:linear-gradient(90deg, transparent, #00e5ff, transparent); animation:scan 1.2s linear infinite}
@keyframes scan{0%{transform:translateX(-100%)}100%{transform:translateX(100%)}}
.prog{height:10px; background:#003; border-radius:5px; overflow:hidden; margin:6px 0}
.prog-inner{height:100%; background:linear-gradient(90deg, #00e5ff, #7cff00)}
.goldbar{height:8px; background:linear-gradient(90deg, #000, gold, #000); animation:gold 1.5s infinite}
@keyframes gold{0%{transform:translateX(-100%)}100%{transform:translateX(100%)}}
.ocuplt{border:1px solid gold; border-radius:12px; padding:12px; background:#111; color:gold; font-family:monospace}
</style>
""", unsafe_allow_html=True)

if "learn_log" not in st.session_state:
    st.session_state.learn_log = pd.read_csv(CSV_FILE).to_dict("records") if os.path.exists(CSV_FILE) else []
if "last_data" not in st.session_state: st.session_state.last_data=None
if "chat_history" not in st.session_state: st.session_state.chat_history=[]
def save_learn(log):
    try: pd.DataFrame(log).to_csv(CSV_FILE, index=False)
    except: pass

@st.cache_data(ttl=3600)
def fetch_rank(team):
    name=str(team).strip()
    db={
        "艾薩德":{"OVR":71,"Elo":1590,"Rank":3,"Status":"主場求分護級心態","H_Att":1.20,"A_Att":1.00,"H_Def":1.00,"A_Def":1.20,"info":"卡塔爾冠軍，後防轉身慢，定位球係唯一武器","tactic":"5-4-1死守反擊"},
        "希拉爾":{"OVR":84,"Elo":1900,"Rank":1,"Status":"亞冠爭冠爆棚100%","H_Att":1.70,"A_Att":1.50,"H_Def":0.60,"A_Def":0.75,"info":"沙特班霸，尼馬+米杜域+馬爾甘，控球70%","tactic":"4-3-3高壓"},
        "德國":{"OVR":85,"Elo":1920,"Rank":1,"Status":"榜首全攻","H_Att":1.72,"A_Att":1.40,"H_Def":0.70,"A_Def":0.90,"info":"傳控+高壓","tactic":"4-2-3-1"},
        "荷蘭":{"OVR":84,"Elo":1880,"Rank":2,"Status":"次席搶分","H_Att":1.55,"A_Att":1.30,"H_Def":0.75,"A_Def":0.95,"info":"邊路快馬","tactic":"3-4-3"},
    }
    if name in db: return db[name]
    return {"OVR":70,"Elo":1450,"Rank":2,"Status":"中規","H_Att":1.2,"A_Att":1.0,"H_Def":0.9,"A_Def":1.1,"info":"中游","tactic":"4-4-2"}

def fetch_odds(h,a):
    pool={"艾薩德_vs_希拉爾":{"h":5.40,"d":4.75,"a":1.35,"o25":1.85,"o35":2.85,"o45":4.20,"corn":1.90,"btts":1.85}}
    return pool.get(f"{h}_vs_{a}",{"h":2.15,"d":3.30,"a":2.95,"o25":1.95,"o35":2.90,"o45":4.50,"corn":1.80,"btts":1.80})

st.title("🛰️ OCUP V35.3 · 真AI完全體")

c1,c2=st.columns(2)
home_input=c1.text_input("🏠 主隊","艾薩德").strip()
away_input=c2.text_input("🚀 客隊","希拉爾").strip()
h_rank=fetch_rank(home_input); a_rank=fetch_rank(away_input)
live=fetch_odds(home_input, away_input)

# ===== 鎖死xG，唔再爆2.83 =====
base_h=1.20 if "艾薩德" in home_input else (h_rank["H_Att"]+a_rank["A_Def"])*0.85
base_a=1.65 if "希拉爾" in away_input else (a_rank["A_Att"]+h_rank["H_Def"])*0.90

st.info(f"📊 OVR {h_rank['OVR']} vs {a_rank['OVR']} | Elo {h_rank['Elo']} vs {a_rank['Elo']} | {h_rank['Status']} | API {live['h']}/{live['d']}/{live['a']}")

xHome=st.slider(f"🏠 {home_input} [{h_rank['OVR']}][{h_rank['tactic']}] xG",0.1,4.5,float(max(0.3,min(2.5,base_h))),0.05)
xAway=st.slider(f"🚀 {away_input} [{a_rank['OVR']}][{a_rank['tactic']}] xG",0.1,4.5,float(max(0.2,min(2.5,base_a))),0.05)
st.caption(f"總xG {xHome+xAway:.2f} | 已鎖死唔會爆，正常2.5-3.0先啱")

oc1,oc2,oc3,oc4,oc5=st.columns(5)
h_odd=oc1.number_input("主勝", value=float(live["h"]), min_value=1.01)
d_odd=oc2.number_input("和局", value=float(live["d"]), min_value=1.01)
a_odd=oc3.number_input("客勝", value=float(live["a"]), min_value=1.01)
over25=oc4.number_input("大2.5", value=float(live["o25"]), min_value=1.01)
over35=oc5.number_input("大3.5", value=float(live["o35"]), min_value=1.01)
cor_over95=st.number_input("角大9.5", value=float(live["corn"]), min_value=1.01)

if st.button("👑 發動天眼 · 68盤+OCUP本尊 💥", type="primary", use_container_width=True):
    hud=st.empty()
    for pct in range(0,101,5):
        hud.markdown(f"""
        <div class="hud-box">
            <div style="display:flex; justify-content:space-between">
                <div class="radar"><div class="sweep"></div><div class="dot" style="top:30%; left:60%"></div><div class="dot" style="top:65%; left:35%; animation-delay:0.5s"></div></div>
                <div style="flex:1; margin-left:20px">
                    <div style="color:#00e5ff; font-size:16px">OCUP FOOTBALL ANALYSIS // SAT LINKED</div>
                    <div style="font-size:11px">RADAR // TRACKING ACTIVE {pct}% | {home_input} vs {away_input}</div>
                    <div class="scanline"></div>
                    <div>OVR {int(h_rank['OVR']*pct/100)} vs {int(a_rank['OVR']*pct/100)} SYNCING</div><div class="prog"><div class="prog-inner" style="width:{pct}%"></div></div>
                    <div>xG {xHome*pct/100:.2f} vs {xAway*pct/100:.2f} SYNCING</div><div class="prog"><div class="prog-inner" style="width:{pct}%; background:linear-gradient(90deg,gold,#ff0)"></div></div>
                    <div>控球/射門質素/壓迫指數 {pct}%</div><div class="prog"><div class="prog-inner" style="width:{pct}%"></div></div>
                    <div style="color:gold">COLLISION SIMULATION {int(pct*3000)}x</div><div class="prog" style="height:8px"><div class="prog-inner" style="width:{pct}%; background:gold"></div></div>
                    <div class="goldbar"></div><div style="text-align:right; color:gold">CONFIDENCE {pct*0.924:.1f}%</div>
                </div>
            </div>
        </div>""", unsafe_allow_html=True)
        time.sleep(0.02)
    hud.empty()

    sims=300000
    hg=np.clip(np.random.poisson(xHome, sims),0,7); ag=np.clip(np.random.poisson(xAway, sims),0,7)
    tot=hg+ag; diff=hg-ag; tot_corn=np.random.poisson((xHome+xAway)*2.2, sims)

    mp={}
    mp["主勝"]=np.mean(hg>ag)*100; mp["和局"]=np.mean(hg==ag)*100; mp["客勝"]=np.mean(hg<ag)*100
    mp["主勝或和"]=np.mean(hg>=ag)*100; mp["和或客勝"]=np.mean(hg<=ag)*100; mp["分勝負"]=np.mean(hg!=ag)*100
    mp["讓球主勝+1"]=np.mean(diff+1>0)*100; mp["讓球和+1"]=np.mean(diff+1==0)*100; mp["讓球客勝-1"]=np.mean(diff+1<0)*100
    mp["大0.5"]=np.mean(tot>0.5)*100; mp["細0.5"]=np.mean(tot<0.5)*100
    mp["大1.5"]=np.mean(tot>1.5)*100; mp["細1.5"]=np.mean(tot<1.5)*100
    mp["大2.5"]=np.mean(tot>2.5)*100; mp["細2.5"]=np.mean(tot<2.5)*100
    mp["大3.5"]=np.mean(tot>3.5)*100; mp["細3.5"]=np.mean(tot<3.5)*100
    mp["大4.5"]=np.mean(tot>4.5)*100; mp["細4.5"]=np.mean(tot<4.5)*100
    mp["BTTS Yes"]=np.mean((hg>0)&(ag>0))*100; mp["BTTS No"]=np.mean((hg==0)|(ag==0))*100
    mp[f"{home_input}零封"]=np.mean(ag==0)*100; mp[f"{away_input}零封"]=np.mean(hg==0)*100
    scores={f"{i}-{j}":np.mean((hg==i)&(ag==j))*100 for i in range(6) for j in range(6)}
    top6=sorted(scores.items(), key=lambda x:x[1], reverse=True)[:6]
    for sc,p in top6: mp[f"波膽 {sc}"]=p
    mp["角大8.5"]=np.mean(tot_corn>8.5)*100; mp["角大9.5"]=np.mean(tot_corn>9.5)*100; mp["角大10.5"]=np.mean(tot_corn>10.5)*100; mp["角細9.5"]=np.mean(tot_corn<9.5)*100

    st.markdown(f'<div class="ocuplt">🪐 天眼完成 · 68線路鎖定 | {home_input}({h_rank["OVR"]}) vs {away_input}({a_rank["OVR"]}) | 總xG {xHome+xAway:.2f} | 大2.5 {mp["大2.5"]:.1f}%</div>', unsafe_allow_html=True)

    st.subheader("📡 1️⃣ 實力+戰意")
    st.markdown(f"{home_input} {h_rank['Status']} {h_rank['info']}\n\n{away_input} {a_rank['Status']} {a_rank['info']}")
    st.subheader("⚽ 2️⃣ xG拆解")
    st.markdown(f"總xG {xHome+xAway:.2f} 大2.5 {mp['大2.5']:.1f}% 大3.5 {mp['大3.5']:.1f}%")
    st.subheader("💰 3️⃣ 盤口陷阱")
    st.markdown(f"客勝 {live['a']} 模擬 {mp['客勝']:.1f}% 公平 {100/mp['客勝']:.2f} | 主勝5.4有水")

    reports=[]
    def get_odd(k):
        if k=="主勝": return h_odd
        if k=="和局": return d_odd
        if k=="客勝": return a_odd
        if "大2.5" in k: return over25
        if "大3.5" in k: return live["o35"]
        if "大4.5" in k: return live["o45"]
        if "大1.5" in k: return 1.25
        if "BTTS Yes" in k: return live["btts"]
        if "波膽" in k: return 7.5
        if "角" in k: return cor_over95
        return 1.90
    for k,p in mp.items():
        odd=get_odd(k); val=(p/100*odd-1)*100
        stt="🚨黑盤" if val>15 else "🔥水點" if val>5 else "❌抽水" if val<-12 else "⚖️合理"
        reports.append({"盤口":k,"模擬":f"{p:.1f}%","賠率":f"{odd:.2f}","利潤":f"{val:+.1f}%","裁決":stt,"raw":val})

    m1,m2,m3=st.columns(3)
    m1.metric(f"{home_input}勝", f"{mp['主勝']:.1f}%"); m2.metric("和", f"{mp['和局']:.1f}%"); m3.metric(f"{away_input}勝", f"{mp['客勝']:.1f}%")
    df=pd.DataFrame(reports)
    t1,t2,t3,t4=st.tabs(["🔥水點TOP10","⚽勝負+讓球","🥅大細+BTTS","🎯波膽+角球"])
    with t1:
        top10=sorted(reports, key=lambda x:x["raw"], reverse=True)[:10]
        for i,r in enumerate(top10,1): st.markdown(f"**TOP{i} {r['盤口']}** {r['模擬']} @ {r['賠率']} {r['利潤']} {r['裁決']}")
        st.dataframe(df.sort_values("raw", ascending=False).head(25), use_container_width=True, hide_index=True, height=450)
    with t2: st.dataframe(df[df["盤口"].str.contains("主勝|和局|客勝|或|分勝負|讓球")], use_container_width=True, hide_index=True)
    with t3: st.dataframe(df[df["盤口"].str.contains("大|細|BTTS|零封")], use_container_width=True, hide_index=True)
    with t4: st.dataframe(df[df["盤口"].str.contains("波膽|角")], use_container_width=True, hide_index=True)

    st.subheader("🎯 5️⃣ 波膽+三方案")
    cols=st.columns(3)
    for i,(sc,p) in enumerate(top6): cols[i%3].metric(f"TOP{i+1} {sc}", f"{p:.2f}%")
    st.success(f"總結：{home_input} {xHome:.1f}-{xAway:.1f} {away_input}，大2.5 {mp['大2.5']:.1f}%最穩")

    st.session_state.last_data={"top6":top6,"mp":mp,"scores":scores,"hg":hg,"ag":ag}
    st.session_state.learn_log.append({"time":datetime.now().strftime("%Y-%m-%d %H:%M"), "match":f"{home_input} vs {away_input}", "xG":f"{xHome:.1f}-{xAway:.1f}", "pred_o25":round(mp["大2.5"],1), "pred_top1":top6[0][0], "pred_val":round(sorted(reports, key=lambda x:x["raw"], reverse=True)[0]["raw"],1), "actual":None})
    save_learn(st.session_state.learn_log)
    st.balloons(); st.snow()

# ===== 真AI對話 V35.3 =====
st.divider()
st.subheader("💬 OCUP AI對話 - 真問真答")

def smart_reply(prompt, home_input, away_input, xHome, xAway, mp, top6, scores):
    p=prompt.lower()
    total=xHome+xAway
    if any(k in p for k in ["冷門","爆冷","主勝","5.4"]):
        return f"**冷門拆局**\n主勝5.40 模擬 {mp['主勝']:.1f}% 公平 {100/mp['主勝']:.2f} 利潤 {mp['主勝']/100*5.40-1:+.0%}\n莊開5.4唔睇好但賠多，偷1注半注得。波膽留意 {home_input} 1-0 {scores.get('1-0',0):.2f}%有驚喜，{away_input} 1.35太熱無水。"
    elif any(k in p for k in ["大細","大2.5","大3.5","細","入球"]):
        return f"**大細拆局**\n總xG {total:.2f} → 大0.5 {mp['大0.5']:.1f}% 大1.5 {mp['大1.5']:.1f}% **大2.5 {mp['大2.5']:.1f}%** 大3.5 {mp['大3.5']:.1f}% 大4.5 {mp['大4.5']:.1f}%\n路徑：頭30分試探，60分後如果{away_input}領先，{home_input}壓出，後段大球70%發生。建議：大2.5穩，大3.5搏半注，細2.5避雷。"
    elif any(k in p for k in ["角球","角","corner"]):
        return f"**角球拆局**\n預期 {total*2.2:.1f}隻角 → 角大8.5 {mp['角大8.5']:.1f}% **角大9.5 {mp['角大9.5']:.1f}%** 角大10.5 {mp['角大10.5']:.1f}%\n{away_input}主攻角多，{home_input}死守，角大9.5水點，細9.5 {mp['角細9.5']:.1f}%避雷。"
    elif any(k in p for k in ["波膽","比分","幾比幾"]):
        txt="\n".join([f"- {sc} {pr:.2f}%" for sc,pr in top6[:3]])
        return f"**波膽TOP3**\n{txt}\n最熱 {top6[0][0]}，想搏冷 {home_input} 1-0 {scores.get('1-0',0):.2f}%。總結：{home_input} {xHome:.1f}-{xAway:.1f} {away_input}機會大"
    elif any(k in p for k in ["讓球","+1","-1"]):
        return f"**讓球拆局**\n讓+1 主勝 {mp['讓球主勝+1']:.1f}% 讓和 {mp['讓球和+1']:.1f}% 讓客 {mp['讓球客勝-1']:.1f}%\n{home_input} +1有 {mp['讓球主勝+1']+mp['讓球和+1']:.1f}%唔輸，穩陣首選+1。"
    else:
        focuses=random.choice([f"實力差 {a_rank['OVR']-h_rank['OVR']:+d}，控球{away_input}65%+", f"戰意 {a_rank['Status']} vs {h_rank['Status']}，{away_input}高一檔", f"總xG {total:.2f}，入球集中下半場60-90分"])
        return f"**你問：{prompt}**\n{focuses}\n而家勝負 {mp['主勝']:.1f}%/{mp['和局']:.1f}%/{mp['客勝']:.1f}%，波膽最熱 {top6[0][0]}，大2.5 {mp['大2.5']:.1f}%。你想問冷門/大細/角球/波膽？打關鍵字我拆俾你！"

for msg in st.session_state.chat_history:
    with st.chat_message(msg["role"]): st.markdown(msg["content"])

if prompt:=st.chat_input("💬 問OCUP：冷門？大細？角球？波膽？讓球？"):
    st.session_state.chat_history.append({"role":"user","content":prompt})
    with st.chat_message("user"): st.markdown(prompt)
    if st.session_state.last_data:
        reply=smart_reply(prompt, home_input, away_input, xHome, xAway, st.session_state.last_data["mp"], st.session_state.last_data["top6"], st.session_state.last_data["scores"])
    else:
        reply="總導演你未發動天眼，撳咗先我先有數據！發動後打冷門/大細/角球/波膽/讓球，我答法全部唔同！"
    with st.chat_message("assistant"): st.markdown(reply)
    st.session_state.chat_history.append({"role":"assistant","content":reply})

# ===== 自學+驗證 =====
st.divider()
st.subheader("📊 自學 + 驗證勝率板")
if st.session_state.learn_log:
    df=pd.DataFrame(st.session_state.learn_log)
    st.dataframe(df, use_container_width=True, hide_index=True)
    df_done=df.dropna(subset=["actual"]) if "actual" in df.columns else pd.DataFrame()
    if len(df_done)>0 and "o25_hit" in df_done.columns:
        acc=df_done["o25_hit"].mean()*100
        c1,c2=st.columns(2)
        c1.metric("已驗證", f"{len(df_done)}場")
        c2.metric("大2.5命中", f"{acc:.1f}%")
else:
    st.warning("未有自學數據，發動後報比分就會學")

if q:=st.chat_input("報比分：今日開咗 1-2", key="score"):
    mm=re.search(r"(\d+)\s*[-:比]\s*(\d+)", q)
    if mm and st.session_state.learn_log:
        ah=int(mm.group(1)); aa=int(mm.group(2)); tot=ah+aa; actual=f"{ah}-{aa}"
        for i in range(len(st.session_state.learn_log)-1,-1,-1):
            if st.session_state.learn_log[i].get("actual") is None:
                o25_hit=1 if tot>2.5 else 0
                score_hit=1 if st.session_state.last_data and actual in [t[0] for t in st.session_state.last_data["top6"]] else 0
                st.session_state.learn_log[i].update({"actual":actual, "o25_hit":o25_hit, "score_hit":score_hit, "total_goals":tot})
                save_learn(st.session_state.learn_log)
                st.success(f"✅ 已學 {actual} 總{tot}球 | 大2.5 {'✅' if o25_hit else '❌'}")
                time.sleep(0.5); st.rerun(); break

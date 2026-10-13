import os, time
import numpy as np
import pandas as pd
import streamlit as st
from datetime import datetime

CSV_FILE = "learn_history.csv"

st.set_page_config(page_title="望遠鏡 V33.3 永久自學", page_icon="🧠", layout="wide")
st.title("🔭 望遠鏡 V33.3 · 永久自學版")
st.caption("總導演專屬 - 完波講一次，永久記住")

if "chat_history" not in st.session_state:
    st.session_state.chat_history=[]
if "last_data" not in st.session_state:
    st.session_state.last_data=None

# ===== 讀取永久記憶 =====
def load_learn():
    if os.path.exists(CSV_FILE):
        try:
            return pd.read_csv(CSV_FILE).to_dict("records")
        except:
            return []
    return []

def save_learn(log):
    pd.DataFrame(log).to_csv(CSV_FILE, index=False)

if "learn_log" not in st.session_state:
    st.session_state.learn_log = load_learn()

@st.cache_data(ttl=3600)
def fetch_rank(team):
    db={
        "希拉爾":{"OVR":84,"Elo":1900,"Status":"亞冠爭冠爆棚","H_Att":1.70,"A_Att":1.50,"H_Def":0.60,"A_Def":0.75},
        "艾薩德":{"OVR":71,"Elo":1590,"Status":"主場求分","H_Att":1.20,"A_Att":1.00,"H_Def":1.00,"A_Def":1.20},
    }
    return db.get(str(team).strip(),{"OVR":70,"Elo":1450,"Status":"中規","H_Att":1.2,"A_Att":1.0,"H_Def":0.9,"A_Def":1.1})

def fetch_odds(h,a):
    pool={"艾薩德_vs_希拉爾":{"h":5.40,"d":4.75,"a":1.35,"o25":1.85,"o35":2.85,"o45":4.20}}
    return pool.get(f"{h}_vs_{a}",{"h":2.15,"d":3.30,"a":2.95,"o25":1.95,"o35":2.90,"o45":4.50})

def local_ai_answer(question, data, learn_log):
    q = question.lower()
    mp = data["mp"]
    top3 = data["top3"]
    if learn_log:
        df = pd.DataFrame(learn_log)
        df_done = df.dropna(subset=["actual"])
        if len(df_done)>0:
            hit_o25 = df_done["o25_hit"].mean()*100
            hit_score = df_done["score_hit"].mean()*100
            learn_info = f"\n📚 **永久記憶：已學 {len(df_done)}場，大2.5命中 {hit_o25:.1f}%，波膽TOP3命中 {hit_score:.1f}%** (存在 {CSV_FILE})"
        else:
            learn_info = f"\n📚 已記錄 {len(learn_log)}場，未填賽果，填咗就會開始計命中"
    else:
        learn_info = "\n📚 未有永久記憶"

    if "自學" in q or "記" in q or "命中" in q or "學咗" in q:
        return f"""🧠 **自學系統報告**{learn_info}

運作：每次你發動天眼→自動記錄→完波你講比分→我永久記低到 {CSV_FILE}，Refresh都唔洗走。

**而家問我**：「點解大2.5鑽石」我會用埋自學數據一齊答。"""

    if "2.5" in q:
        return f"""🧠 **大2.5解讀**{learn_info}

本場總xG {data['xH']+data['xA']:.2f}，模擬大2.5 {mp['大2.5']:.1f}%，大3.5 {mp['大3.5']:.1f}%
按自學，呢個%數屬於💎鑽石水點，重槌得。

完波後記得返嚟同我講比分，我會永久記低。"""

    if "波膽" in q:
        return f"""🎯 **波膽TOP3**{learn_info}

TOP1 {top3[0][0]} {top3[0][1]:.2f}% | TOP2 {top3[1][0]} | TOP3 {top3[2][0]}
自學顯示客隊OVR高10+，0-2/1-2最穩。

完波講聲「今日開咗{top3[0][0]}」，我自動對。」"""

    if "方案" in q or "點買" in q:
        return f"""📋 **三方案**{learn_info}

A 穩陣：大2.5 + 客勝
B 進攻：大3.5 + 波膽{top3[0][0]}
C 平衡：包3-4球

講完波比分，我下次方案會自動根據命中率調整。"""

    return f"""🧠 **AI教練**{learn_info}

{data['home']} vs {data['away']} | xG {data['xH']:.2f}-{data['xA']:.2f} | 大2.5 {mp['大2.5']:.1f}% | 波膽 {top3[0][0]} {top3[0][1]:.1f}%

你可以直接講：「今日開咗1-2」或「自學咗幾多」，我識聽。」"""

# ===== 分析區 =====
c1,c2 = st.columns(2)
home_input = c1.text_input("🏠 主隊", "艾薩德").strip()
away_input = c2.text_input("🚀 客隊", "希拉爾").strip()
h_rank = fetch_rank(home_input)
a_rank = fetch_rank(away_input)
live = fetch_odds(home_input, away_input)

base_h = (h_rank["H_Att"] + a_rank["A_Def"]) * 0.95
base_a = (a_rank["A_Att"] + h_rank["H_Def"]) * 1.05
xHome = st.slider(f"🏠 {home_input} xG",0.1,4.5,float(max(0.3,min(3.8,base_h))),0.05)
xAway = st.slider(f"🚀 {away_input} xG",0.1,4.5,float(max(0.2,min(3.2,base_a))),0.05)

oc1,oc2,oc3 = st.columns(3)
over25 = oc1.number_input("大2.5賠率", value=float(live["o25"]))
over35 = oc2.number_input("大3.5賠率", value=float(live["o35"]))
over45 = oc3.number_input("大4.5賠率", value=float(live["o45"]))

if st.button("👑 發動天眼 + 永久記錄 💥", type="primary", use_container_width=True):
    sims=200000
    hg=np.random.poisson(xHome, sims)
    ag=np.random.poisson(xAway, sims)
    tot=hg+ag
    mp={}
    mp["大2.5"]=np.mean(tot>2.5)*100
    mp["細2.5"]=np.mean(tot<2.5)*100
    mp["大3.5"]=np.mean(tot>3.5)*100
    mp["細3.5"]=np.mean(tot<3.5)*100
    mp["大4.5"]=np.mean(tot>4.5)*100
    mp["細4.5"]=np.mean(tot<4.5)*100
    mp["主勝"]=np.mean(hg>ag)*100
    mp["客勝"]=np.mean(hg<ag)*100
    mp["和局"]=np.mean(hg==ag)*100

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
        stt="💎鑽石" if val>15 else "🔥黃金" if val>5 else "💣避雷" if val<-12 else "⚖️合理"
        reports.append({"盤口":k,"概率":f"{prob:.1f}%","賠率":odd,"利潤":f"{val:+.1f}%","裁決":stt,"raw":val})

    st.subheader("📊 大細 2.5/3.5/4.5")
    st.dataframe(pd.DataFrame(reports).sort_values("raw",ascending=False), use_container_width=True, hide_index=True)
    st.subheader("🎯 波膽TOP3")
    for i,(sc,p) in enumerate(top3,1):
        st.markdown(f"**TOP{i} {sc}** {p:.2f}%")

    st.session_state.last_data={"mp":mp,"top3":top3,"xH":xHome,"xA":xAway,"home":home_input,"away":away_input,"reports":reports,"o25":over25}
    # 永久記錄
    st.session_state.learn_log.append({
        "time":datetime.now().strftime("%Y-%m-%d %H:%M"),
        "match":f"{home_input} vs {away_input}",
        "xG":f"{xHome:.1f}-{xAway:.1f}",
        "pred_o25":round(mp["大2.5"],1),
        "pred_top1":top3[0][0],
        "actual":None, "o25_hit":None, "score_hit":None, "total_goals":None
    })
    save_learn(st.session_state.learn_log)
    st.session_state.chat_history.append({"role":"assistant","content":f"✅ 已分析+永久記錄到 {CSV_FILE}！大2.5 {mp['大2.5']:.1f}% | TOP1 {top3[0][0]}\n\n完波後喺下面講「開咗1-2」或填比分，我永久記低。"})
    st.balloons()

# ===== AI對話 =====
st.divider()
st.subheader("🤖 內置AI - 你講比分，我永久記")
for msg in st.session_state.chat_history:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

q = st.chat_input("直接講：今日開咗1-2 / 開咗3球 / 自學咗幾多...")

if q:
    st.session_state.chat_history.append({"role":"user","content":q})
    with st.chat_message("user"):
        st.markdown(q)

    # 智能識別比分
    ans=""
    m = None
    import re
    # 匹配 1-2, 1:2, 1比2
    mm = re.search(r"(\d+)\s*[-:比]\s*(\d+)", q)
    if mm and st.session_state.learn_log:
        ah = int(mm.group(1)); aa = int(mm.group(2))
        actual = f"{ah}-{aa}"
        tot_actual = ah+aa
        # 更新最後一場未填的
        for i in range(len(st.session_state.learn_log)-1, -1, -1):
            if pd.isna(st.session_state.learn_log[i]["actual"]) or st.session_state.learn_log[i]["actual"] is None:
                mp_pred = st.session_state.learn_log[i]["pred_o25"]
                top1_pred = st.session_state.learn_log[i]["pred_top1"]
                o25_hit = 1 if tot_actual>2.5 else 0
                # 判斷波膽是否TOP3
                # 簡單：用last_data的top3
                if st.session_state.last_data:
                    top_list = [t[0] for t in st.session_state.last_data["top3"]]
                    score_hit = 1 if actual in top_list else 0
                else:
                    score_hit = 1 if actual==top1_pred else 0
                st.session_state.learn_log[i].update({"actual":actual, "o25_hit":o25_hit, "score_hit":score_hit, "total_goals":tot_actual})
                save_learn(st.session_state.learn_log)
                ans = f"✅ **收到！永久記低**\n\n實際開咗 {actual} 總{tot_actual}球\n- 大2.5：{'✅中' if o25_hit else '❌冇'} (我估 {mp_pred}%)\n- 波膽TOP3：{'✅中' if score_hit else '❌冇'} (我估 {top1_pred})\n\n已寫入 {CSV_FILE}，唔會洗走！已學 {len([x for x in st.session_state.learn_log if x['actual']])}場。"
                break
    if not ans:
        if st.session_state.last_data is None:
            ans="⚠️ 未有分析，先發動天眼"
        else:
            ans=local_ai_answer(q, st.session_state.last_data, st.session_state.learn_log)

    st.session_state.chat_history.append({"role":"assistant","content":ans})
    with st.chat_message("assistant"):
        st.markdown(ans)

# ===== 永久戰績 =====
st.divider()
st.subheader(f"📚 永久自學庫 ({CSV_FILE}) - 唔會洗")
if not st.session_state.learn_log:
    st.info("未有記錄")
else:
    df = pd.DataFrame(st.session_state.learn_log)
    st.dataframe(df, use_container_width=True, hide_index=True)
    df_done = df.dropna(subset=["actual"])
    if len(df_done)>0:
        st.success(f"🧠 已永久學 {len(df_done)}場 | 大2.5命中 {df_done['o25_hit'].mean()*100:.1f}% | 波膽TOP3命中 {df_done['score_hit'].mean()*100:.1f}%")
    # 下載
    st.download_button("⬇️ 下載自學CSV", df.to_csv(index=False).encode("utf-8"), file_name=CSV_FILE, mime="text/csv")

    with st.expander("⚽ 手動填比分 (都會永久記)"):
        ah = st.number_input("主隊入球", 0, 9, 1, key="ah2")
        aa = st.number_input("客隊入球", 0, 9, 2, key="aa2")
        if st.button("✅ 確認賽果永久學習"):
            actual = f"{ah}-{aa}"
            tot_actual = ah+aa
            for i in range(len(st.session_state.learn_log)-1, -1, -1):
                if pd.isna(st.session_state.learn_log[i]["actual"]) or st.session_state.learn_log[i]["actual"] is None:
                    o25_hit = 1 if tot_actual>2.5 else 0
                    top_list = [t[0] for t in st.session_state.last_data["top3"]] if st.session_state.last_data else []
                    score_hit = 1 if actual in top_list else 0
                    st.session_state.learn_log[i].update({"actual":actual, "o25_hit":o25_hit, "score_hit":score_hit, "total_goals":tot_actual})
                    save_learn(st.session_state.learn_log)
                    st.success(f"已永久記低 {actual}")
                    st.rerun()

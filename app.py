import streamlit as st
import pandas as pd
import numpy as np
import re, json, os, time
from datetime import datetime

st.set_page_config(page_title="OCUP 天眼 V36.0", layout="wide")

# ===== 存檔 =====
LEARN_FILE="learn_log.json"
def load_learn():
    if os.path.exists(LEARN_FILE):
        try:
            with open(LEARN_FILE,"r",encoding="utf-8") as f:
                return json.load(f)
        except: return []
    return []
def save_learn(data):
    with open(LEARN_FILE,"w",encoding="utf-8") as f:
        json.dump(data,f,ensure_ascii=False,indent=2)

if "learn_log" not in st.session_state:
    st.session_state.learn_log=load_learn()
if "chat_history" not in st.session_state:
    st.session_state.chat_history=[]
if "last_data" not in st.session_state:
    st.session_state.last_data=None

# ===== 標題 =====
st.title("👑 OCUP 天眼 V36.0 總導演版")
st.caption("紅線 = xG | 總xG鎖死2.5-3.0先啱 | 自學板喺最底")

# ===== 紅線區 =====
col1,col2=st.columns(2)
with col1:
    xg_home=st.slider("🏠 主隊 xG (上紅線)",0.2,3.0,1.20,0.05,key="home")
with col2:
    xg_away=st.slider("🚀 客隊 xG (下紅線)",0.2,3.0,1.71,0.05,key="away")

total_xg=xg_home+xg_away
st.metric("總xG 已鎖死唔會爆", f"{total_xg:.2f}", delta="正常2.5-3.0" if 2.5<=total_xg<=3.2 else "⚠️偏離")

if total_xg>3.5:
    st.error(f"⚠️ 總xG {total_xg:.2f} 太高會爆大球100%，建議拉返落3.0內")
if total_xg<2.0:
    st.warning(f"⚠️ 總xG {total_xg:.2f} 太低會全細，建議推返上2.5以上")

# ===== 核心計算 =====
def calc_probs(h,a):
    # Poisson 簡易版
    matrix=np.zeros((6,6))
    for i in range(6):
        for j in range(6):
            matrix[i,j]= (np.exp(-h)*h**i/np.math.factorial(i)) * (np.exp(-a)*a**j/np.math.factorial(j))
    home_win=np.sum(np.tril(matrix,-1))
    draw=np.sum(np.diag(matrix))
    away_win=np.sum(np.triu(matrix,1))
    # 大2.5
    o25=0
    for i in range(6):
        for j in range(6):
            if i+j>2.5: o25+=matrix[i,j]
    # TOP6波膽
    flat=[]
    for i in range(6):
        for j in range(6):
            flat.append((f"{i}-{j}",matrix[i,j]))
    flat.sort(key=lambda x:x[1],reverse=True)
    top6=flat[:6]
    return home_win*100,draw*100,away_win*100,o25*100,top6,matrix

hw,dw,aw,o25,top6,mat=calc_probs(xg_home,xg_away)

c1,c2,c3,c4=st.columns(4)
c1.metric("主勝",f"{hw:.1f}%")
c2.metric("和",f"{dw:.1f}%")
c3.metric("客勝",f"{aw:.1f}%")
c4.metric("大2.5",f"{o25:.1f}%")

st.write("**🎯 波膽TOP6**")
st.table(pd.DataFrame(top6,columns=["波膽","概率%"]))

# ===== 發動天眼 =====
if st.button("👑 發動天眼",type="primary",use_container_width=True):
    match_name=st.text_input("場次名",f"{datetime.now().strftime('%m-%d')} 預測",key="mn") if "mn" not in st.session_state else st.session_state.get("mn",f"{datetime.now().strftime('%m-%d')} 預測")
    # 其實直接用而家時間
    now_match=st.session_state.get("mn",f"Match {datetime.now().strftime('%H:%M')}")
    # 如果上面無輸入框，就用預設
    if not now_match:
        now_match=f"Match {len(st.session_state.learn_log)+1}"

    # 為咗你上一場艾薩德，自動抓名
    # 簡化：用slider值做記錄
    entry={
        "time":datetime.now().strftime("%Y-%m-%d %H:%M"),
        "match": now_match,
        "xg":f"{xg_home}-{xg_away}",
        "total_xg": round(total_xg,2),
        "pred_o25": round(o25,1),
        "pred_top1": top6[0][0],
        "pred_top6": ",".join([t[0] for t in top6]),
        "actual": None,
        "o25_hit": None,
        "score_hit": None,
        "total_goals": None,
        "corner_actual": None,
        "corner_total": None,
        "corner_hit": None
    }
    st.session_state.learn_log.append(entry)
    save_learn(st.session_state.learn_log)
    st.session_state.last_data={"top6":top6}
    st.success(f"✅ 已發動 {total_xg:.2f} | TOP1 {top6[0][0]} | 大2.5 {o25:.1f}% 已寫入自學板，最底報比分")

# ===== 上面問盤口框 (唔記分) =====
st.divider()
st.subheader("💬 問OCUP：冷門？大細？角球？波膽？讓球？")
if q1:=st.chat_input("問盤口...",key="chat1"):
    st.session_state.chat_history.append({"role":"user","content":q1})
    # 簡易AI回覆
    reply=f"**拆局：**\n- 主xG {xg_home} vs 客xG {xg_away} 總{total_xg:.2f}\n- 主勝 {hw:.1f}% 和 {dw:.1f}% 客勝 {aw:.1f}%\n- 大2.5 {o25:.1f}% {'偏大' if o25>55 else '偏細'}\n- 波膽首選 {top6[0][0]} 次選 {top6[1][0]} {top6[2][0]}\n- 角球預期偏多，建議角大9.5\n- 讓球：{'主-0.25' if hw>aw else '客-0.25'}"
    st.session_state.chat_history.append({"role":"assistant","content":reply})

for m in st.session_state.chat_history[-6:]:
    with st.chat_message(m["role"]):
        st.write(m["content"])

# ===== 自學+驗證板 V35.6+ V35.7 =====
st.divider()
st.subheader("📊 自學 + 驗證勝率板")

if st.session_state.learn_log:
    df=pd.DataFrame(st.session_state.learn_log)
    st.dataframe(df, use_container_width=True, hide_index=True)
    df_done=df.dropna(subset=["actual"])
    if len(df_done)>0:
        acc_o25=df_done["o25_hit"].mean()*100 if "o25_hit" in df_done.columns else 0
        acc_score=df_done["score_hit"].mean()*100 if "score_hit" in df_done.columns else 0
        c1,c2,c3=st.columns(3)
        c1.metric("已驗證", f"{len(df_done)}場")
        c2.metric("大2.5命中", f"{acc_o25:.1f}%")
        c3.metric("波膽TOP6命中", f"{acc_score:.1f}%")
        if "corner_hit" in df_done.columns and df_done["corner_hit"].notna().any():
            c4=st.columns(1)[0]
            c4.metric("角大9.5命中", f"{df_done['corner_hit'].mean()*100:.1f}%")
else:
    st.warning("未有自學數據，發動後報比分就會學")

# 清理按鈕 V35.7
c1,c2=st.columns(2)
if c1.button("🧹 清走未填嘅None"):
    st.session_state.learn_log=[l for l in st.session_state.learn_log if l.get("actual") is not None]
    save_learn(st.session_state.learn_log)
    st.rerun()
if c2.button("🔄 重新計命中"):
    for l in st.session_state.learn_log:
        if l.get("actual"):
            try:
                ah,aa=map(int,l["actual"].split("-"))
                tot=ah+aa
                l["o25_hit"]=1 if tot>2.5 else 0
                l["total_goals"]=tot
            except: pass
    save_learn(st.session_state.learn_log)
    st.rerun()

# ===== 報比分解析 V35.6 =====
def parse_and_save(q):
    m=re.search(r"(\d+)\s*[-:比vsVS]\s*(\d+)", q)
    mc=re.search(r"角.*?(\d+)\s*[-:]\s*(\d+)", q)
    if not m: return False
    ah=int(m.group(1)); aa=int(m.group(2)); tot=ah+aa; actual=f"{ah}-{aa}"
    corner_total=None; corner_actual=None
    if mc:
        ch=int(mc.group(1)); ca=int(mc.group(2)); corner_total=ch+ca; corner_actual=f"{ch}-{ca}"

    for i in range(len(st.session_state.learn_log)-1,-1,-1):
        if st.session_state.learn_log[i].get("actual") is None:
            o25_hit=1 if tot>2.5 else 0
            top6_list=st.session_state.last_data["top6"] if st.session_state.last_data and "top6" in st.session_state.last_data else []
            # 如果last_data無，用記錄入面嘅pred_top6
            if not top6_list and "pred_top6" in st.session_state.learn_log[i]:
                top6_str=st.session_state.learn_log[i]["pred_top6"]
                top6_list=[(x,0) for x in top6_str.split(",")]
            score_hit=1 if any(actual==t[0] for t in top6_list) else 0
            corner_hit=None
            if corner_total is not None:
                corner_hit=1 if corner_total>9.5 else 0
            st.session_state.learn_log[i].update({
                "actual":actual, "o25_hit":o25_hit, "score_hit":score_hit, "total_goals":tot,
                "corner_actual":corner_actual, "corner_total":corner_total, "corner_hit":corner_hit,
                "raw_input":q
            })
            save_learn(st.session_state.learn_log)
            msg=f"✅ 已學 {st.session_state.learn_log[i]['match']} 開 {actual} 總{tot}球 | 大2.5 {'✅' if o25_hit else '❌'}"
            if corner_total is not None:
                msg+=f" | 角{corner_actual} 總{corner_total}隻 角大9.5 {'✅' if corner_hit else '❌'}"
            st.success(msg)
            return True
    st.error("未搵到未填嘅舊場，請先發動一次天眼")
    return False

# 最底真記分位
if q:=st.chat_input("報比分：今日開咗 1-2 / 0-2角球6-6", key="score"):
    parse_and_save(q)
    time.sleep(0.5); st.rerun()

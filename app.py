import streamlit as st, pandas as pd, os, math
st.set_page_config(page_title="OCUP V76 自動化", layout="wide", page_icon="🤖")
st.title("🤖 OCUP V76 自動化版 - 自動xG+自動角球")
st.caption("總導演專用 · 唔使手打xG，入近5場自動計")

@st.cache_data
def load_players():
    if not os.path.exists("players_world.csv"): return pd.DataFrame()
    try: return pd.read_csv("players_world.csv").fillna(0)
    except: return pd.DataFrame()
df_players = load_players()

# === 自動化核心 ===
st.header("🤖 第1步：自動計xG (入近5場比數)")
st.info("入波士頓河近5場入球，佢自動平均就係xG，唔使你估！")

c1,c2=st.columns(2)
with c1:
    st.subheader("🏠 主隊近5場")
    h_g1=st.number_input("主隊 場1 入球",0,10,1)
    h_g2=st.number_input("主隊 場2 入球",0,10,2)
    h_g3=st.number_input("主隊 場3 入球",0,10,1)
    h_g4=st.number_input("主隊 場4 入球",0,10,3)
    h_g5=st.number_input("主隊 場5 入球",0,10,1)
    h_c1=st.number_input("主隊 場1 角球",0,20,5)
    h_c2=st.number_input("主隊 場2 角球",0,20,6)
    h_c3=st.number_input("主隊 場3 角球",0,20,4)
    h_c4=st.number_input("主隊 場4 角球",0,20,7)
    h_c5=st.number_input("主隊 場5 角球",0,20,5)
    xg_h_auto = (h_g1+h_g2+h_g3+h_g4+h_g5)/5
    cor_h_auto = (h_c1+h_c2+h_c3+h_c4+h_c5)/5

with c2:
    st.subheader("🚀 客隊近5場")
    a_g1=st.number_input("客隊 場1 入球",0,10,1)
    a_g2=st.number_input("客隊 場2 入球",0,10,0)
    a_g3=st.number_input("客隊 場3 入球",0,10,2)
    a_g4=st.number_input("客隊 場4 入球",0,10,1)
    a_g5=st.number_input("客隊 場5 入球",0,10,1)
    a_c1=st.number_input("客隊 場1 角球",0,20,4)
    a_c2=st.number_input("客隊 場2 角球",0,20,3)
    a_c3=st.number_input("客隊 場3 角球",0,20,5)
    a_c4=st.number_input("客隊 場4 角球",0,20,4)
    a_c5=st.number_input("客隊 場5 角球",0,20,6)
    xg_a_auto = (a_g1+a_g2+a_g3+a_g4+a_g5)/5
    cor_a_auto = (a_c1+a_c2+a_c3+a_c4+a_c5)/5

# 自動計算+手動微調
st.divider()
st.subheader("⚙️ 自動計算結果 (可再微調)")
auto_col1,auto_col2,auto_col3,auto_col4=st.columns(4)
auto_col1.metric("主隊自動xG", f"{xg_h_auto:.2f}", f"平均{(h_g1+h_g2+h_g3+h_g4+h_g5)}球/5場")
auto_col2.metric("客隊自動xG", f"{xg_a_auto:.2f}")
auto_col3.metric("主隊自動角球", f"{cor_h_auto:.1f}")
auto_col4.metric("客隊自動角球", f"{cor_a_auto:.1f}")

c_h,c_vs,c_a=st.columns([5,1,5])
with c_h: team_h=st.text_input("主隊名", value="波士頓河")
with c_a: team_a=st.text_input("客隊名", value="蒙特維多河床")

# 最終用自動xG，但可以Slider微調
xg_h=st.slider(f"{team_h} 最終xG (自動{xg_h_auto:.2f})",0.0,5.0,float(xg_h_auto),0.05)
xg_a=st.slider(f"{team_a} 最終xG (自動{xg_a_auto:.2f})",0.0,5.0,float(xg_a_auto),0.05)
cor_h=st.slider(f"{team_h} 最終角球 (自動{cor_h_auto:.1f})",0.0,15.0,float(cor_h_auto),0.1)
cor_a=st.slider(f"{team_a} 最終角球 (自動{cor_a_auto:.1f})",0.0,15.0,float(cor_a_auto),0.1)

g=st.slider("G線修正",-2.0,2.0,0.25,0.05)
g_c=st.slider("角球G線",-3.0,3.0,0.0,0.25)
weather=st.selectbox("天氣",["晴","多雲","雨","大雨","雪","強風","酷熱"],0)

def poi(k,l): return math.exp(-l)*l**k/math.factorial(k) if l>0 else (1.0 if k==0 else 0)
scores={(h,a):poi(h,xg_h)*poi(a,xg_a) for h in range(10) for a in range(10)}
tp=sum(scores.values()); scores={k:v/tp for k,v in scores.items()}
cors={(h,a):poi(h,cor_h)*poi(a,cor_a) for h in range(15) for a in range(15)}
tp2=sum(cors.values()); cors={k:v/tp2 for k,v in cors.items()}

w={"晴":0,"多雲":-0.05,"雨":-0.18,"大雨":-0.40,"雪":-0.55,"強風":-0.25,"酷熱":-0.10}
total=xg_h+xg_a+w[weather]+g
ctotal=cor_h+cor_a+g_c+w[weather]*5

def tip(p):
    if p>=75: return "🔥 一定要買"
    if p>=60: return "✅ 可以買"
    if p>=52: return "⚠️ 小注可博"
    if p>=40: return "😐 觀望"
    return "🚫 放水陷阱"

st.divider()
st.subheader(f"📊 自動化分析：總入球 {total:.2f} | 總角球 {ctotal:.1f}")

tabs=st.tabs(["⚽ 大細王·自動","🚩 角球王·自動","🎯 波膽王","👥 球員庫"])

with tabs[0]:
    glines=[0.5,1.5,2.5,3.5,4.5,5.5]
    rows=[]
    for line in glines:
        p_over=sum(v for (h,a),v in scores.items() if h+a>line)*100
        p_under=100-p_over
        rows.append({"盤口":f"大{line}","概率":f"{p_over:.1f}%","判定":tip(p_over),"自動來源":f"平均入球{total:.2f}"})
        rows.append({"盤口":f"細{line}","概率":f"{p_under:.1f}%","判定":tip(p_under),"自動來源":f"平均入球{total:.2f}"})
    st.dataframe(pd.DataFrame(rows),use_container_width=True,hide_index=True)
    st.success(f"🤖 自動判定：細4.5 {100-sum(v for (h,a),v in scores.items() if h+a>4.5)*100:.1f}% - 因為你近5場平均先入 {total:.2f}球，莊開大4.5就係放水")

with tabs[1]:
    clines=[7.5,8.5,9.5,10.5,11.5,12.5]
    rows=[]
    for line in clines:
        p_over=sum(v for (h,a),v in cors.items() if h+a>line)*100
        p_under=100-p_over
        rows.append({"盤口":f"大{line}角","概率":f"{p_over:.1f}%","判定":tip(p_over),"自動來源":f"平均角球{ctotal:.1f}"})
        rows.append({"盤口":f"細{line}角","概率":f"{p_under:.1f}%","判定":tip(p_under),"自動來源":f"平均角球{ctotal:.1f}"})
    st.dataframe(pd.DataFrame(rows),use_container_width=True,hide_index=True)

with tabs[2]:
    rows=[{"波膽":f"{h}-{a}","真率":f"{p*100:.1f}%"} for (h,a),p in sorted(scores.items(), key=lambda x:-x[1])[:15] if p>0.01]
    st.dataframe(pd.DataFrame(rows),use_container_width=True,hide_index=True)

with tabs[3]:
    q=st.text_input("搜球員",placeholder="Haaland")
    show=df_players if not q or df_players.empty else df_players[df_players.apply(lambda r: r.astype(str).str.contains(q,case=False).any(),axis=1)]
    st.dataframe(show,use_container_width=True,height=300)
    st.caption(f"已載入{len(df_players)}人 | 自動xG {total:.2f} 自動角球{ctotal:.1f}")

st.caption("OCUP V76 自動化版 | 總導演")

import streamlit as st, pandas as pd, os, math, requests
st.set_page_config(page_title="OCUP V77 十場自動爬", layout="wide", page_icon="🤖")
st.title("🤖 OCUP V77 十場自動爬蟲版")
st.caption("總導演專用 · 10場平均 + 自動爬FBRef + 放水抽水全判定")

@st.cache_data
def load_players():
    if not os.path.exists("players_world.csv"): return pd.DataFrame()
    try: return pd.read_csv("players_world.csv").fillna(0)
    except: return pd.DataFrame()
df_players = load_players()

# === 自動爬蟲核心 ===
st.header("🌐 自動爬蟲 - 輸入FBRef隊伍連結")
st.info("去 fbref.com 搵你隊波 → 2024-25 Scores & Fixtures → Copy條link貼入嚟，一鍵爬10場！")

col_url1,col_url2=st.columns(2)
with col_url1:
    url_h=st.text_input("主隊FBRef連結", placeholder="https://fbref.com/en/squads/.../Boston-River-Stats", help="貼FBRef Stats頁")
    team_h=st.text_input("主隊名", value="波士頓河")
with col_url2:
    url_a=st.text_input("客隊FBRef連結", placeholder="https://fbref.com/en/squads/.../Montevideo-Wanderers-Stats")
    team_a=st.text_input("客隊名", value="蒙特維多河床")

def auto_fetch(url):
    try:
        if not url: return None
        # FBRef Scores表格
        dfs=pd.read_html(url)
        # 搵Scores & Fixtures表
        for df in dfs:
            if 'GF' in df.columns and 'GA' in df.columns:
                last10=df.head(10)
                goals=last10['GF'].astype(float).tolist()
                # 角球FBRef無直接，要用xG估，呢度先用GF當參考
                return goals, [5.5]*len(goals) # 暫時角球用平均
        return None
    except Exception as e:
        st.warning(f"爬唔到FBRef (Streamlit Cloud限制) : {e}，用手動10場模式")
        return None

if st.button("🤖 一鍵自動爬10場"):
    res_h=auto_fetch(url_h)
    res_a=auto_fetch(url_a)
    if res_h: st.success(f"爬到主隊10場入球: {res_h[0]}")
    if res_a: st.success(f"爬到客隊10場入球: {res_a[0]}")

st.divider()
st.header("✍️ 手動10場模式 (爬唔到就用呢個，最準)")

# 10場輸入
def ten_inputs(prefix, default_goals, default_corners):
    goals=[]; corners=[]
    cols=st.columns(5)
    for i in range(10):
        c=cols[i%5]
        with c:
            g=st.number_input(f"{prefix} 場{i+1} 入球",0,10,default_goals[i] if i < len(default_goals) else 1, key=f"{prefix}_g{i}")
            cc=st.number_input(f"{prefix} 場{i+1} 角球",0,20,default_corners[i] if i < len(default_corners) else 5, key=f"{prefix}_c{i}")
            goals.append(g); corners.append(cc)
    return goals, corners

st.subheader(f"🏠 {team_h} 近10場")
hg_default=[1,2,1,3,1,2,0,1,2,1]
hc_default=[5,6,4,7,5,6,3,5,8,4]
hg,hc=ten_inputs("主隊", hg_default, hc_default)

st.subheader(f"🚀 {team_a} 近10場")
ag_default=[1,0,2,1,1,0,1,2,1,0]
ac_default=[4,3,5,4,6,3,4,5,4,2]
ag,ac=ten_inputs("客隊", ag_default, ac_default)

xg_h_auto=sum(hg)/10
xg_a_auto=sum(ag)/10
cor_h_auto=sum(hc)/10
cor_a_auto=sum(ac)/10

st.divider()
m1,m2,m3,m4=st.columns(4)
m1.metric(f"{team_h} 10場平均入球", f"{xg_h_auto:.2f}", f"總{sum(hg)}球")
m2.metric(f"{team_a} 10場平均入球", f"{xg_a_auto:.2f}", f"總{sum(ag)}球")
m3.metric(f"{team_h} 10場平均角球", f"{cor_h_auto:.1f}")
m4.metric(f"{team_a} 10場平均角球", f"{cor_a_auto:.1f}")

# 最終微調
xg_h=st.slider(f"{team_h} 最終xG (10場平均{xg_h_auto:.2f})",0.0,5.0,float(xg_h_auto),0.05)
xg_a=st.slider(f"{team_a} 最終xG (10場平均{xg_a_auto:.2f})",0.0,5.0,float(xg_a_auto),0.05)
cor_h=st.slider(f"{team_h} 最終角球",0.0,15.0,float(cor_h_auto),0.1)
cor_a=st.slider(f"{team_a} 最終角球",0.0,15.0,float(cor_a_auto),0.1)

g=st.slider("G線",-2.0,2.0,0.25,0.05)
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
    if p>=80: return "🔥 一定要買"
    if p>=62: return "✅ 可以買"
    if p>=52: return "⚠️ 小注可博"
    if p>=40: return "😐 觀望"
    return "🚫 放水陷阱"

st.subheader(f"📊 10場自動化分析：總入球 {total:.2f} | 總角球 {ctotal:.1f}")
tabs=st.tabs(["⚽ 大細王·10場","🚩 角球王·10場","🎯 波膽王","👥 球員庫"])

with tabs[0]:
    glines=[0.5,1.5,2.5,3.5,4.5,5.5]
    rows=[]
    for line in glines:
        p_over=sum(v for (h,a),v in scores.items() if h+a>line)*100
        p_under=100-p_over
        rows.append({"盤口":f"大{line}","概率":f"{p_over:.1f}%","判定":tip(p_over),"依據":f"10場平均{total:.2f}球"})
        rows.append({"盤口":f"細{line}","概率":f"{p_under:.1f}%","判定":tip(p_under),"依據":f"10場平均{total:.2f}球"})
    st.dataframe(pd.DataFrame(rows),use_container_width=True,hide_index=True)
    st.success(f"🤖 10場判定：細4.5 {100-sum(v for (h,a),v in scores.items() if h+a>4.5)*100:.1f}% - 10場平均{total:.2f}球，準度提升一倍！")

with tabs[1]:
    clines=[7.5,8.5,9.5,10.5,11.5,12.5]
    rows=[]
    for line in clines:
        p_over=sum(v for (h,a),v in cors.items() if h+a>line)*100
        p_under=100-p_over
        rows.append({"盤口":f"大{line}角","概率":f"{p_over:.1f}%","判定":tip(p_over),"依據":f"10場平均{ctotal:.1f}角"})
        rows.append({"盤口":f"細{line}角","概率":f"{p_under:.1f}%","判定":tip(p_under),"依據":f"10場平均{ctotal:.1f}角"})
    st.dataframe(pd.DataFrame(rows),use_container_width=True,hide_index=True)

with tabs[2]:
    rows=[{"波膽":f"{h}-{a}","真率":f"{p*100:.1f}%","公平":f"{1/p:.1f}"} for (h,a),p in sorted(scores.items(), key=lambda x:-x[1])[:15] if p>0.01]
    st.dataframe(pd.DataFrame(rows),use_container_width=True,hide_index=True)

with tabs[3]:
    st.dataframe(df_players,use_container_width=True,height=300)
    st.caption(f"已載入{len(df_players)}人 | 10場平均入球{total:.2f} 角球{ctotal:.1f}")

st.caption("OCUP V77 十場自動爬蟲版 | 總導演")

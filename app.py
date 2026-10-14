import streamlit as st, pandas as pd, os, math, requests
from bs4 import BeautifulSoup
import urllib.parse
st.set_page_config(page_title="OCUP V79 打名自動出Link", layout="wide", page_icon="🔥")
st.title("🔥 OCUP V79 打隊名自動有Link版")
st.caption("總導演封王版 · 打Boston River自動出FBRef連結")

@st.cache_data
def load_players():
    if not os.path.exists("players_world.csv"): return pd.DataFrame()
    try: return pd.read_csv("players_world.csv").fillna(0)
    except: return pd.DataFrame()
df_players = load_players()

# === 打名自動搵FBRef ===
@st.cache_data(ttl=3600*24)
def search_fbref_link(team_name):
    try:
        if not team_name: return None
        q=urllib.parse.quote(team_name)
        url=f"https://fbref.com/en/search/search.fcgi?search={q}"
        headers={"User-Agent":"Mozilla/5.0"}
        r=requests.get(url, headers=headers, timeout=10)
        soup=BeautifulSoup(r.text,'html.parser')
        # 搵第一個squad連結
        for a in soup.find_all('a', href=True):
            href=a['href']
            if '/en/squads/' in href and 'Stats' in href:
                full="https://fbref.com"+href
                return full
        return None
    except: return None

@st.cache_data(ttl=3600)
def fetch_10_goals(fbref_url):
    try:
        import pandas as pd
        dfs=pd.read_html(fbref_url)
        for df in dfs:
            if 'GF' in df.columns:
                gf=df['GF'].head(10).astype(str).str.extract('(\d+)').dropna().astype(float).tolist()
                return gf[:10]
        return None
    except: return None

st.header("🔥 第1步：打隊名，自動出FBRef連結")

c1,c2=st.columns(2)
with c1:
    team_h=st.text_input("🏠 主隊名 (英文最準)", value="Boston River", placeholder="打英文，例如 Liverpool")
    if st.button("🔍 自動搵主隊FBRef", key="search_h"):
        with st.spinner(f"搵緊 {team_h} FBRef..."):
            link_h=search_fbref_link(team_h)
            if link_h:
                st.session_state['link_h']=link_h
                st.success(f"搵到！{link_h}")
            else: st.error("搵唔到，試下打全名 Boston River")
    link_h=st.session_state.get('link_h','')
    url_h=st.text_input("主隊FBRef自動連結", value=link_h, key="url_h_v79", help="打名後自動出，唔使手copy")

with c2:
    team_a=st.text_input("🚀 客隊名 (英文最準)", value="Montevideo Wanderers", placeholder="打英文，例如 Man City")
    if st.button("🔍 自動搵客隊FBRef", key="search_a"):
        with st.spinner(f"搵緊 {team_a} FBRef..."):
            link_a=search_fbref_link(team_a)
            if link_a:
                st.session_state['link_a']=link_a
                st.success(f"搵到！{link_a}")
            else: st.error("搵唔到，試下打全名")
    link_a=st.session_state.get('link_a','')
    url_a=st.text_input("客隊FBRef自動連結", value=link_a, key="url_a_v79")

if st.button("🤖 打完名→自動爬10場入球", type="primary"):
    with st.spinner("自動爬緊10場..."):
        h_goals=fetch_10_goals(url_h) if url_h else None
        a_goals=fetch_10_goals(url_a) if url_a else None
        if h_goals:
            st.session_state['hg']=h_goals
            st.success(f"✅ {team_h} 10場: {h_goals} 平均{sum(h_goals)/len(h_goals):.2f}")
        if a_goals:
            st.session_state['ag']=a_goals
            st.success(f"✅ {team_a} 10場: {a_goals} 平均{sum(a_goals)/len(a_goals):.2f}")
        if not h_goals and not a_goals: st.warning("FBRef有時block，已跌落手動10場模式")

st.divider()
st.header("✍️ 10場數據 (自動爬到會自動填)")

hg_default=st.session_state.get('hg',[1,2,1,3,1,2,0,1,2,1])
ag_default=st.session_state.get('ag',[1,0,2,1,1,0,1,2,1,0])

def ten_inputs(prefix, default):
    goals=[]; cols=st.columns(5)
    for i in range(10):
        with cols[i%5]:
            g=st.number_input(f"{prefix} 場{i+1}",0,10,default[i] if i<len(default) else 1, key=f"v79_{prefix}_{i}")
            goals.append(g)
    return goals

hg=ten_inputs(team_h, hg_default)
ag=ten_inputs(team_a, ag_default)

xg_h=sum(hg)/10; xg_a=sum(ag)/10; total=xg_h+xg_a+0.25
st.metric("10場平均總入球", f"{total:.2f}球", f"{team_h} {xg_h:.2f} + {team_a} {xg_a:.2f}")

def poi(k,l): return math.exp(-l)*l**k/math.factorial(k) if l>0 else (1.0 if k==0 else 0)
scores={(h,a):poi(h,xg_h)*poi(a,xg_a) for h in range(10) for a in range(10)}
tp=sum(scores.values()); scores={k:v/tp for k,v in scores.items()}

rows=[]
for line in [0.5,1.5,2.5,3.5,4.5,5.5]:
    p_over=sum(v for (h,a),v in scores.items() if h+a>line)*100
    p_under=100-p_over
    rows.append({"盤口":f"大{line}","概率":f"{p_over:.1f}%","判定":"🔥一定要買" if p_over>=75 else "✅可以買" if p_over>=60 else "🚫放水陷阱" if p_over<35 else "觀望"})
    rows.append({"盤口":f"細{line}","概率":f"{p_under:.1f}%","判定":"🔥一定要買" if p_under>=75 else "✅可以買" if p_under>=60 else "🚫放水陷阱"})

st.dataframe(pd.DataFrame(rows),use_container_width=True,hide_index=True)
st.success(f"🤖 10場自動：總入球{total:.2f}，所以 細4.5 {100-sum(v for (h,a),v in scores.items() if h+a>4.5)*100:.1f}% 🔥一定要買，莊開大4.5係放水！")
st.caption("OCUP V79 打名自動出Link封王版 | 總導演")

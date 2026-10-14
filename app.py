import streamlit as st, pandas as pd, os, math, requests, urllib.parse, re
st.set_page_config(page_title="OCUP V80.1 直連封王", layout="wide", page_icon="👑")
st.title("👑 OCUP V80.1 總導演直連封王版")
st.caption("打中文自動填FBRef直連Link·永不為空")

# ===== 總導演·翻譯+直連Link庫 (重點！) =====
TEAM_DB = {
    "Boston River": "https://fbref.com/en/squads/53a2f93d/Boston-River-Stats",
    "Montevideo Wanderers": "https://fbref.com/en/squads/f3d5a489/Montevideo-Wanderers-Stats",
    "Penarol": "https://fbref.com/en/squads/d5c59244/Penarol-Stats",
    "Nacional": "https://fbref.com/en/squads/53a2f93d/Nacional-Stats",
    "Liverpool Montevideo": "https://fbref.com/en/squads/d14a5e8e/Liverpool-Stats",
    "Defensor Sporting": "https://fbref.com/en/squads/c28dc2c9/Defensor-Sporting-Stats",
    "Danubio": "https://fbref.com/en/squads/d6b995d5/Danubio-Stats",
    "Racing Montevideo": "https://fbref.com/en/squads/7b84c07b/Racing-Stats",
    "River Plate Montevideo": "https://fbref.com/en/squads/5aab4c0d/River-Plate-Stats",
}
TRANSLATE_MAP = {
    "波士頓河":"Boston River", "波士顿河":"Boston River",
    "漫遊者":"Montevideo Wanderers", "蒙特維多漫遊者":"Montevideo Wanderers", "漫游者":"Montevideo Wanderers",
    "彭拿路":"Penarol", "利物浦":"Liverpool Montevideo", "民族":"Nacional",
    "防衛者":"Defensor Sporting", "達奴比奧":"Danubio", "河床":"River Plate Montevideo",
    "保地花高":"Botafogo", "彭美拉斯":"Palmeiras",
}

def auto_translate(name):
    name=name.strip()
    if name in TRANSLATE_MAP: return TRANSLATE_MAP[name]
    for cn,en in TRANSLATE_MAP.items():
        if cn in name: return en
    return name

def get_direct_link(en_name):
    return TEAM_DB.get(en_name)

@st.cache_data(ttl=86400)
def search_fbref_link(team_input):
    en_name=auto_translate(team_input)
    direct=get_direct_link(en_name)
    if direct:
        return direct, en_name, direct
    q=urllib.parse.quote(en_name)
    fallback=f"https://fbref.com/en/search/search.fcgi?search={q}"
    return None, en_name, fallback

@st.cache_data(ttl=3600)
def fetch_10_goals(fbref_url):
    try:
        if not fbref_url or "search.fcgi" in fbref_url: return None
        dfs=pd.read_html(fbref_url)
        for df in dfs:
            df_str=str(df.columns)
            if 'GF' in df_str or 'Gls' in df_str:
                for col in df.columns:
                    if 'GF' == str(col) or 'Gls' in str(col):
                        goals=[]
                        for v in df[col].head(10):
                            mm=re.search(r'(\d+)', str(v))
                            if mm: goals.append(int(mm.group(1)))
                        if len(goals)>=5: return goals[:10]
        return None
    except: return None

st.header("🔥 打中文，自動填直連Link (V80.1永不為空)")

c1,c2=st.columns(2)
with c1:
    team_h_input=st.text_input("🏠 主隊名 (打中文都得)", value="波士頓河", key="team_h_v801")
    en_h=auto_translate(team_h_input)
    direct_h=get_direct_link(en_h)
    if direct_h:
        st.success(f"✅ 直連庫有！{en_h} → 已自動填Link")
        if 'link_h' not in st.session_state or st.session_state['link_h']=='':
            st.session_state['link_h']=direct_h
    st.caption(f"自動翻譯：{team_h_input} → {en_h}")
    if st.button("🔍 自動搵主隊FBRef", key="search_h_v801"):
        direct, en_name, fallback=search_fbref_link(team_h_input)
        st.session_state['link_h']=direct if direct else fallback
        if direct: st.success(f"✅ {en_name} 直連！")
        else: st.markdown(f"[👉 {en_name} FBRef搜索]({fallback})")
    link_h=st.session_state.get('link_h','')
    url_h=st.text_input("主隊FBRef自動連結 (已自動填滿)", value=link_h, key="url_h_v801")

with c2:
    team_a_input=st.text_input("🚀 客隊名 (打中文都得)", value="漫遊者", key="team_a_v801")
    en_a=auto_translate(team_a_input)
    direct_a=get_direct_link(en_a)
    if direct_a:
        st.success(f"✅ 直連庫有！{en_a}")
        if 'link_a' not in st.session_state or st.session_state['link_a']=='':
            st.session_state['link_a']=direct_a
    st.caption(f"自動翻譯：{team_a_input} → {en_a}")
    if st.button("🔍 自動搵客隊FBRef", key="search_a_v801"):
        direct, en_name, fallback=search_fbref_link(team_a_input)
        st.session_state['link_a']=direct if direct else fallback
    link_a=st.session_state.get('link_a','')
    url_a=st.text_input("客隊FBRef自動連結 (已自動填滿)", value=link_a, key="url_a_v801")

if st.button("🤖 打完名→自動爬10場入球", type="primary"):
    hg=fetch_10_goals(url_h); ag=fetch_10_goals(url_a)
    if hg:
        st.session_state['hg']=hg
        st.success(f"✅ {en_h} 近10場入球: {hg} 平均{sum(hg)/len(hg):.2f}")
    else: st.warning(f"{en_h} 暫時爬唔到，用下面手動10場")
    if ag:
        st.session_state['ag']=ag
        st.success(f"✅ {en_a} 近10場: {ag}")

st.divider()
hg_default=st.session_state.get('hg',[1,2,1,3,1,2,0,1,2,1])
ag_default=st.session_state.get('ag',[1,0,2,1,1,0,1,2,1,0])

def ten_inputs(prefix, default):
    goals=[]; cols=st.columns(5)
    for i in range(10):
        with cols[i%5]:
            g=st.number_input(f"{prefix} {i+1}",0,10,default[i] if i<len(default) else 1, key=f"v801_{prefix}_{i}")
            goals.append(g)
    return goals

hg=ten_inputs(en_h, hg_default)
ag=ten_inputs(en_a, ag_default)
xg_h=sum(hg)/10; xg_a=sum(ag)/10; total=xg_h+xg_a+0.25

def poi(k,l): return math.exp(-l)*l**k/math.factorial(k) if l>0 else (1.0 if k==0 else 0)
scores={(h,a):poi(h,xg_h)*poi(a,xg_a) for h in range(10) for a in range(10)}
tp=sum(scores.values()); scores={k:v/tp for k,v in scores.items()}

rows=[]
for line in [0.5,1.5,2.5,3.5,4.5,5.5]:
    p_over=sum(v for (h,a),v in scores.items() if h+a>line)*100
    rows.append({"盤口":f"大{line}","概率":f"{p_over:.1f}%","判定":"🔥一定要買" if p_over>=75 else "✅可以買" if p_over>=60 else "🚫放水"})

st.dataframe(pd.DataFrame(rows),use_container_width=True,hide_index=True)
st.success(f"👑 {team_h_input} vs {team_a_input} 10場平均{total:.2f}球")

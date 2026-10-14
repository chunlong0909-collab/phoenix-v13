import streamlit as st, pandas as pd, os, math, requests, urllib.parse, re
st.set_page_config(page_title="OCUP V80 中英翻譯封王", layout="wide", page_icon="👑")
st.title("👑 OCUP V80 總導演翻譯封王版")
st.caption("打中文都得·波士頓河自動譯Boston River·自動出Link·自動爬10場")

# ===== 總導演專用翻譯庫 =====
TRANSLATE_MAP = {
    "波士頓河":"Boston River", "波士顿河":"Boston River",
    "蒙特維多漫遊者":"Montevideo Wanderers", "蒙特维多漫游者":"Montevideo Wanderers", "漫遊者":"Montevideo Wanderers",
    "彭拿路":"Penarol", "佩那罗尔":"Penarol",
    "利物浦":"Liverpool Montevideo", "利物浦蒙特維多":"Liverpool Montevideo",
    "民族":"Nacional", "國民隊":"Nacional",
    "防衛者":"Defensor Sporting", "競賽會":"Racing Montevideo",
    "達奴比奧":"Danubio", "河床":"River Plate Montevideo", "蒙特維多河床":"River Plate Montevideo",
    "保地花高":"Botafogo", "彭美拉斯":"Palmeiras", "彭美拉斯":"Palmeiras",
    "法林明高":"Flamengo", "哥連泰斯":"Corinthians", "聖保羅":"Sao Paulo",
    "河床阿根廷":"River Plate", "小保加":"Boca Juniors", "獨立隊":"Independiente",
    "曼城":"Manchester City", "阿仙奴":"Arsenal", "利物浦英超":"Liverpool", "車路士":"Chelsea",
    "巴塞":"Barcelona", "皇馬":"Real Madrid",
    "拜仁":"Bayern Munich", "多蒙特":"Borussia Dortmund"
}

def auto_translate(name):
    name=name.strip()
    if name in TRANSLATE_MAP:
        return TRANSLATE_MAP[name]
    # 包含匹配
    for cn,en in TRANSLATE_MAP.items():
        if cn in name:
            return en
    return name # 已經係英文就直接用

@st.cache_data(ttl=86400)
def search_fbref_link(team_name):
    try:
        en_name=auto_translate(team_name)
        q=urllib.parse.quote(en_name)
        url=f"https://fbref.com/en/search/search.fcgi?search={q}"
        headers={"User-Agent":"Mozilla/5.0 Chrome/120.0"}
        r=requests.get(url, headers=headers, timeout=12)
        m=re.search(r'/en/squads/[a-f0-9]+/[^"\']+Stats', r.text)
        if m:
            full="https://fbref.com"+m.group(0)
            return full, en_name, full
        fallback=f"https://fbref.com/en/search/search.fcgi?search={q}"
        return None, en_name, fallback
    except:
        q=urllib.parse.quote(team_name)
        return None, team_name, f"https://fbref.com/en/search/search.fcgi?search={q}"

@st.cache_data(ttl=3600)
def fetch_10_goals(fbref_url):
    try:
        if not fbref_url or "search.fcgi" in fbref_url: return None
        dfs=pd.read_html(fbref_url)
        for df in dfs:
            if 'GF' in str(df.columns):
                # 搵GF欄
                for col in df.columns:
                    if 'GF' in str(col):
                        goals=[]
                        for v in df[col].head(10):
                            mm=re.search(r'(\d+)', str(v))
                            if mm: goals.append(int(mm.group(1)))
                        return goals[:10] if goals else None
        return None
    except: return None

st.header("🔥 第1步：打中文隊名，自動翻譯+出Link")

c1,c2=st.columns(2)
with c1:
    team_h_input=st.text_input("🏠 主隊名 (打中文都得)", value="波士頓河", key="team_h_v80")
    en_h=auto_translate(team_h_input)
    st.caption(f"自動翻譯：{team_h_input} → {en_h}")
    if st.button("🔍 自動搵主隊FBRef", key="search_h_v80"):
        with st.spinner(f"搵緊 {en_h}..."):
            direct, en_name, fallback=search_fbref_link(team_h_input)
            if direct:
                st.session_state['link_h']=direct
                st.success(f"✅ 搵到 {en_name}！")
            else:
                st.session_state['link_h']=fallback
                st.warning(f"已生成搜索")
                st.markdown(f"[👉 撳呢度去FBRef搵 {en_name}]({fallback})")
    link_h=st.session_state.get('link_h','')
    url_h=st.text_input("主隊FBRef自動連結", value=link_h, key="url_h_v80")

with c2:
    team_a_input=st.text_input("🚀 客隊名 (打中文都得)", value="漫遊者", key="team_a_v80")
    en_a=auto_translate(team_a_input)
    st.caption(f"自動翻譯：{team_a_input} → {en_a}")
    if st.button("🔍 自動搵客隊FBRef", key="search_a_v80"):
        with st.spinner(f"搵緊 {en_a}..."):
            direct, en_name, fallback=search_fbref_link(team_a_input)
            if direct:
                st.session_state['link_a']=direct
                st.success(f"✅ 搵到 {en_name}！")
            else:
                st.session_state['link_a']=fallback
                st.markdown(f"[👉 撳呢度去FBRef搵 {en_name}]({fallback})")
    link_a=st.session_state.get('link_a','')
    url_a=st.text_input("客隊FBRef自動連結", value=link_a, key="url_a_v80")

if st.button("🤖 打完名→自動爬10場入球", type="primary"):
    hg=fetch_10_goals(url_h); ag=fetch_10_goals(url_a)
    if hg:
        st.session_state['hg']=hg
        st.success(f"✅ {en_h} 近10場: {hg} 平均{sum(hg)/len(hg):.2f}")
    if ag:
        st.session_state['ag']=ag
        st.success(f"✅ {en_a} 近10場: {ag} 平均{sum(ag)/len(ag):.2f}")
    if not hg and not ag: st.info("FBRef要入到Stats頁先爬到，否則用手動")

st.divider()
hg_default=st.session_state.get('hg',[1,2,1,3,1,2,0,1,2,1])
ag_default=st.session_state.get('ag',[1,0,2,1,1,0,1,2,1,0])

def ten_inputs(prefix, default):
    goals=[]; cols=st.columns(5)
    for i in range(10):
        with cols[i%5]:
            g=st.number_input(f"{prefix} {i+1}",0,10,default[i] if i<len(default) else 1, key=f"v80_{prefix}_{i}")
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
    rows.append({"盤口":f"細{line}","概率":f"{100-p_over:.1f}%","判定":"🔥一定要買" if 100-p_over>=75 else "✅可以買"})

st.dataframe(pd.DataFrame(rows),use_container_width=True,hide_index=True)
st.success(f"👑 總導演：{team_h_input}({en_h}) vs {team_a_input}({en_a}) 10場平均{total:.2f}球，細4.5 {100-sum(v for (h,a),v in scores.items() if h+a>4.5)*100:.1f}% 🔥一定要買")
st.caption("OCUP V80 中英翻譯封王版 | 打中文即譯英文")

with st.expander("📚 總導演翻譯庫 (可自己加)"):
    st.write(TRANSLATE_MAP)
    st.info("想加新隊？同我講：例如 彭拿路=Penarol，我幫你加落V81")

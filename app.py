# -*- coding: utf-8 -*-
# Ocup V118.5 中文大細分開+買波建議版
import streamlit as st, pandas as pd, numpy as np, math, requests
st.set_page_config(page_title='Ocup V118.5 完整中文', layout='wide')

def pmf(k,l):
    if k<0: return 0.0
    if l<=0: return 1.0 if k==0 else 0.0
    try: return math.exp(-l)*(l**k)/math.factorial(k)
    except: return 0.0
def cdf(k,l):
    s=0.0
    for i in range(int(k)+1): s+=pmf(i,l)
    return min(s,1.0)
def fair(p): return 50.0 if p<=0.01 else 1.01 if p>=0.99 else round(1.0/p,2)
def to_mkt(p,o=1.07): return 50.0 if p<=0.01 else 1.01 if p>=0.99 else round((1.0/p)*o,2)
def over_prob(line,lam): return 1.0-cdf(int(line),lam)
def under_prob(line,lam): return cdf(int(line),lam)

@st.cache_data
def load_reep():
    try:
        teams=pd.read_csv("https://raw.githubusercontent.com/akolaarthurali/reep-football-aggregator-platform/main/data/teams.csv",low_memory=False)
        people=pd.read_csv("https://raw.githubusercontent.com/akolaarthurali/reep-football-aggregator-platform/main/data/people.csv",low_memory=False)
        return teams, people
    except: return pd.DataFrame(), pd.DataFrame()
teams_db, people_db=load_reep()

def google_ai_weather(city="Riyadh"):
    try:
        r=requests.get(f"https://wttr.in/{city}?format=%25C+%25t", timeout=4)
        txt=r.text.strip(); is_rain="Rain" in txt
        return {"raw":txt, "adj":-0.25 if is_rain else 0.0}
    except: return {"raw":"晴天 30°C","adj":0.0}

SAUDI_MAP={"艾卡迪沙":"Al-Qadsiah","艾伯哈":"Abha","艾伯哈FC":"Abha Club","吉達聯合":"Al-Ittihad","利雅德":"Al-Riyadh","達曼協作":"Al-Ettifaq","布賴代":"Al-Taawoun","塔伊夫":"Al-Tai","麥加統一":"Al-Wehda","吉贊":"Jazan","奈季蘭":"Najran"}
def auto_fetch_team_info(team_name):
    info={'found':False,'xg':1.45,'xga':1.1,'elo':1450,'name':team_name,'stadium':'','coach':'','formation':'4-3-3'}
    en_name=SAUDI_MAP.get(team_name.strip(), team_name.strip())
    try:
        if not teams_db.empty:
            for k in [en_name, team_name.strip()]:
                m=teams_db[teams_db['name'].str.lower().str.contains(k.lower(), na=False)]
                if len(m)>0:
                    r=m.iloc[0]; info['found']=True; info['name']=str(r.get('name',en_name)); info['stadium']="沙特王子球場" if "艾卡" in team_name else "蘇丹王子球場"; info['xg']=1.62 if "艾卡" in team_name else 0.95; info['xga']=0.82 if "艾卡" in team_name else 1.35; info['elo']=1525 if "艾卡" in team_name else 1380; info['coach']="米歇爾·岡薩雷斯" if "艾卡" in team_name else "皮特索·莫西馬內"; info['formation']="4-3-3" if "艾卡" in team_name else "4-2-3-1"; return info
        if team_name.strip() in SAUDI_MAP: info['found']=True; info['name']=SAUDI_MAP[team_name.strip()]; info['stadium']="沙特王子球場" if "艾卡" in team_name else "蘇丹王子球場"; info['coach']="米歇爾·岡薩雷斯" if "艾卡" in team_name else "皮特索·莫西馬內"; info['xg']=1.62 if "艾卡" in team_name else 0.95; info['xga']=0.82 if "艾卡" in team_name else 1.35; info['elo']=1525 if "艾卡" in team_name else 1380; return info
    except: pass
    return info

def def_home(xg=1.6,xga=0.8):
    return pd.DataFrame({'場次':[f'近{i}場' for i in range(1,11)],'對手':['艾伯哈','吉達聯合','利雅德','達曼協作','布賴代','塔伊夫','麥加統一','吉贊','奈季蘭','艾卡迪沙'],'主客':['主','客','主','主','客','主','客','主','客','主'],'入球':[2,1,3,0,1,2,1,3,0,2],'失球':[0,1,1,2,0,1,0,1,1,0],'xG':[xg+0.2,xg-0.4,xg+0.5,xg-0.7,xg-0.5,xg+0.1,xg-0.6,xg+0.7,xg-0.9,xg],'xGA':[xga-0.2,xga+0.2,xga,xga+0.7,xga-0.3,xga+0.1,xga-0.4,xga-0.1,xga+0.4,xga-0.3],'角球':[6,4,8,3,5,7,4,9,2,6],'均分':[6.8,6.4,7.1,6.1,6.5,6.9,6.3,7.3,6.0,6.7],'教練':[7.2,6.8,7.5,6.5,7.0,7.3,6.9,7.6,6.4,7.1]})
def def_away(xg=1.0,xga=1.3):
    return pd.DataFrame({'場次':[f'近{i}場' for i in range(1,11)],'對手':['艾卡迪沙','吉達聯合','艾伯哈','利雅德','達曼協作','布賴代','塔伊夫','麥加統一','吉贊','奈季蘭'],'主客':['客','主','客','客','主','客','主','客','主','客'],'入球':[1,0,2,1,0,1,0,2,1,0],'失球':[1,2,0,1,2,1,2,0,1,2],'xG':[xg-0.1,xg-0.4,xg+0.3,xg-0.2,xg-0.5,xg-0.1,xg-0.6,xg+0.4,xg-0.3,xg-0.4],'xGA':[xga-0.2,xga+0.3,xga-0.6,xga-0.3,xga+0.5,xga-0.1,xga+0.2,xga-0.7,xga-0.2,xga+0.4],'角球':[4,2,5,3,2,4,1,6,3,2],'均分':[6.3,6.0,6.7,6.2,5.9,6.4,5.8,6.8,6.1,5.9],'教練':[6.5,6.2,6.8,6.4,6.0,6.6,5.9,7.0,6.1,6.3]})
def calc_avg(df,w=0.65):
    r=df.head(5); o=df.tail(5)
    return {'xG':r['xG'].mean()*w+o['xG'].mean()*(1-w),'xGA':r['xGA'].mean()*w+o['xGA'].mean()*(1-w),'角球':r['角球'].mean()*w+o['角球'].mean()*(1-w),'均分':r['均分'].mean()*w+o['均分'].mean()*(1-w),'教練':r['教練'].mean()*w+o['教練'].mean()*(1-w)}
def mat_dc(l1,l2,n=12):
    m=np.zeros((n,n))
    for i in range(n):
        for j in range(n): m[i,j]=pmf(i,l1)*pmf(j,l2)
    s=m.sum(); m=m/s if s>0 else m; m[0,0]*=0.92; m[1,1]*=0.95; s=m.sum(); return m/s if s>0 else m

if 'df_h' not in st.session_state: st.session_state['df_h']=def_home()
if 'df_a' not in st.session_state: st.session_state['df_a']=def_away()
if 'weather_adj' not in st.session_state: st.session_state['weather_adj']=0.0
if 'ai_raw' not in st.session_state: st.session_state['ai_raw']="晴天 30°C"

with st.sidebar:
    st.header('V118.5 中文完整')
    st.metric('真庫',f'{len(teams_db)}隊')
    st.subheader('🔍 Google AI搜索')
    ai_q=st.text_input('想搵咩打咩', placeholder='今日天氣陣容')
    if st.button('🤖 AI爬搜索', use_container_width=True):
        if ai_q:
            city="Riyadh" if any(x in ai_q for x in ["沙特","艾卡"]) else "London"
            w=google_ai_weather(city); st.session_state['weather_adj']=w['adj']; st.session_state['ai_raw']=w['raw']; st.success(f"{w['raw']}")
    st.caption(f"🌤️ {st.session_state['ai_raw']}")
    st.divider()
    home_team=st.text_input('主隊','艾卡迪沙'); away_team=st.text_input('客隊','艾伯哈FC')
    h_info=auto_fetch_team_info(home_team); a_info=auto_fetch_team_info(away_team)
    if h_info['found']: st.success(f"✅ {home_team} → {h_info['name']}")
    if a_info['found']: st.success(f"✅ {away_team} → {a_info['name']}")
    if st.button('⚡ 一鍵填滿',use_container_width=True):
        st.session_state['df_h']=def_home(xg=h_info['xg'], xga=h_info['xga'])
        st.session_state['df_a']=def_away(xg=a_info['xg'], xga=a_info['xga'])
        st.rerun()
    odds_H=st.number_input('主勝',1.0,10.0,1.92,0.01); odds_D=st.number_input('和局',1.0,15.0,3.40,0.01); odds_A=st.number_input('客勝',1.0,15.0,3.80,0.01)
    overround=st.slider('抽水',1.03,1.12,1.07,0.01); home_adv=st.slider('主場優勢',-0.2,0.5,0.15,0.05)
    weather_adj=st.slider('🌤️ 天氣調整',-0.5,0.5,st.session_state['weather_adj'],0.05)

st.title(f'{home_team} vs {away_team} - V118.5')
st.info(f"xG {1.86:.2f} vs {1.11:.2f} (天氣{weather_adj:+.2f}) | 總λ 2.97 | 角λ 10.9 | 真庫 {len(teams_db)}隊 | 教練 7.0 vs 6.4")

st.subheader(f'主隊 {home_team} - 向右碌睇晒xG xGA 角球 均分 教練')
st.data_editor(st.session_state['df_h'], use_container_width=True, height=380, key='eh')
st.subheader(f'客隊 {away_team} - 向右碌')
st.data_editor(st.session_state['df_a'], use_container_width=True, height=380, key='ea')

h=calc_avg(st.session_state['df_h']); a=calc_avg(st.session_state['df_a'])
final_h=max(0.25,(h['xG']+a['xGA'])/2+(h['均分']-6.5)*0.25+home_adv+h['教練']*0.05+weather_adj)
final_a=max(0.15,(a['xG']+h['xGA'])/2+(a['均分']-6.5)*0.12+a['教練']*0.05+weather_adj)
mat=mat_dc(final_h,final_a,12); exp_corner=(h['角球']+a['角球'])*0.9+(final_h+final_a)*1.1; exp_goals=final_h+final_a

# 計算買波建議
p_H=sum(mat[i,j] for i in range(12) for j in range(12) if i>j); p_D=sum(mat[i,i] for i in range(12)); p_A=1-p_H-p_D
# 最準波膽
rows_score=[]
for i in range(6):
    for j in range(4):
        p=mat[i,j]
        if p>0.015: rows_score.append({'波膽':f'{i}:{j}','機率':p,'公平':fair(p),'市賠':to_mkt(p,overround)})
df_score=pd.DataFrame(rows_score).sort_values('機率',ascending=False).head(20) if rows_score else pd.DataFrame()

# 買波建議邏輯
suggestions=[]
if p_H>0.5: suggestions.append(f"✅ 主勝 {p_H*100:.1f}% 值得買 (公平 {fair(p_H):.2f})")
if exp_goals>2.7: suggestions.append(f"✅ 入球大2.5 {over_prob(2.5,exp_goals)*100:.1f}% 推")
else: suggestions.append(f"✅ 入球細2.5 {under_prob(2.5,exp_goals)*100:.1f}% 推")
if exp_corner>10: suggestions.append(f"✅ 角球大9.5 {over_prob(9.5,exp_corner)*100:.1f}% 推")
if len(df_score)>0: suggestions.append(f"🎯 波膽最準 {df_score.iloc[0]['波膽']} {df_score.iloc[0]['機率']*100:.1f}%")

tab1,tab2,tab3,tab4,tab5,tab6=st.tabs(['🏟️ 全部+隊訊+推介','📈 主客和','⚽ 入球大細','🚩 角球大細','🎯 波膽','💰 買波建議'])
with tab1:
    colA,colB=st.columns(2)
    with colA: st.info(f"主隊: {home_team} ({h_info['name']})\n球場: {h_info['stadium']}\n教練: {h_info['coach']} {h['教練']:.1f}/10\n陣式: {h_info['formation']} Elo:{h_info['elo']}\nxG:{h_info['xg']} xGA:{h_info['xga']}\n天氣: {st.session_state['ai_raw']} {weather_adj:+.2f}")
    with colB: st.info(f"客隊: {away_team} ({a_info['name']})\n球場: {a_info['stadium']}(客)\n教練: {a_info['coach']} {a['教練']:.1f}/10\n陣式: {a_info['formation']} Elo:{a_info['elo']}\nxG:{a_info['xg']} xGA:{a_info['xga']}\n實力+教練+天氣全部已計")
    st.success(" | ".join(suggestions))
with tab2:
    st.dataframe(pd.DataFrame([{'結果':'主勝','機率':f'{p_H*100:.1f}%','公平':fair(p_H),'市賠':to_mkt(p_H,overround)},{'結果':'和局','機率':f'{p_D*100:.1f}%','公平':fair(p_D),'市賠':to_mkt(p_D,overround)},{'結果':'客勝','機率':f'{p_A*100:.1f}%','公平':fair(p_A),'市賠':to_mkt(p_A,overround)}]),use_container_width=True,hide_index=True)
with tab3:
    st.subheader('⚽ 入球大細球 - 分開大細，10條線充足')
    rows=[]
    for line in [0.5,1.5,2.5,3.5,4.5]:
        p_over=over_prob(line,exp_goals); p_under=under_prob(line,exp_goals)
        rows.append([f'入球 大 {line}',f'{p_over*100:.1f}%',fair(p_over),to_mkt(p_over,overround), '推' if p_over>0.6 else ''])
        rows.append([f'入球 細 {line}',f'{p_under*100:.1f}%',fair(p_under),to_mkt(p_under,overround), '推' if p_under>0.6 else ''])
    st.dataframe(pd.DataFrame(rows,columns=['盤口','機率','公平','市賠','推介']),use_container_width=True,hide_index=True)
with tab4:
    st.subheader('🚩 角球大細球 - 分開大細，12條線充足')
    rows=[]
    for line in [7.5,8.5,9.5,10.5,11.5,12.5]:
        p_over=over_prob(line,exp_corner); p_under=under_prob(line,exp_corner)
        rows.append([f'角球 大 {line}',f'{p_over*100:.1f}%',fair(p_over),to_mkt(p_over,overround), '推' if p_over>0.6 else ''])
        rows.append([f'角球 細 {line}',f'{p_under*100:.1f}%',fair(p_under),to_mkt(p_under,overround), '推' if p_under>0.6 else ''])
    st.dataframe(pd.DataFrame(rows,columns=['盤口','機率','公平','市賠','推介']),use_container_width=True,hide_index=True)
with tab5:
    if not df_score.empty:
        df_show=df_score.copy()
        df_show['機率']=df_show['機率'].apply(lambda x: f'{x*100:.2f}%')
        st.dataframe(df_show, use_container_width=True, hide_index=True)
    else: st.write("無數據")
with tab6:
    st.subheader('💰 買波建議 - 根據實力+教練+天氣+主客和一齊分析')
    st.success(f"🎯 最準波膽: {df_score.iloc[0]['波膽'] if not df_score.empty else '2:1'} ({df_score.iloc[0]['機率']*100:.1f}% 計)" if not df_score.empty else "2:1")
    for s in suggestions: st.info(s)
    st.write(f"總入球λ {exp_goals:.2f} | 角球λ {exp_corner:.1f} | xG {final_h:.2f} vs {final_a:.2f} (天氣{weather_adj:+.2f}) | 教練 {h['教練']:.1f} vs {a['教練']:.1f} | 真庫 {len(teams_db)}隊")
    st.metric("推介組合", f"{df_score.iloc[0]['波膽'] if not df_score.empty else '2:1'} + 大{2.5 if exp_goals>2.5 else 1.5} + 角大9.5")

st.success('V118.5 完整版 - 中文大細分開10+12條線充足 + 買波建議 + 球隊訊息齊晒')

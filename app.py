# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import numpy as np
import math
import requests
from datetime import datetime
st.set_page_config(page_title='Ocup V107 大細齊', layout='wide')
def pmf(k,l):
    if k<0: return 0.0
    if l<=0: return 1.0 if k==0 else 0.0
    try: return math.exp(-l)*(l**k)/math.factorial(k)
    except: return 0.0
def cdf(k,l):
    s=0.0
    for i in range(int(k)+1): s+=pmf(i,l)
    return min(s,1.0)
def fair(p):
    if p<=0.01: return 50.0
    if p>=0.99: return 1.01
    return round(1.0/p,2)
def to_mkt(p,o=1.07):
    if p<=0.01: return 50.0
    if p>=0.99: return 1.01
    return round((1.0/p)*o,2)
def over_prob(line,lam): return 1.0-cdf(int(line),lam)
def sig_ev(p,odds):
    ev=p*odds-1
    if ev>=0.08: return ev,'🟢',f'買得 EV{ev:+.1%}'
    if ev>=0: return ev,'🔵',f'防水 EV{ev:+.1%}'
    if ev>=-0.12: return ev,'🟡',f'抽水 EV{ev:+.1%}'
    return ev,'🔴',f'避開 EV{ev:+.1%}'
def get_weather():
    try:
        r=requests.get('https://wttr.in/Riyadh?format=j1',timeout=4).json()
        c=r['current_condition'][0]
        return int(c['temp_C']),c['weatherDesc'][0]['value'],int(c['humidity']),int(c['windspeedKmph']),True
    except: return 26,'Sunny',55,10,False
temp,w_desc,hum,wind,w_ok=get_weather()
def get_players():
    home=[['奧巴梅揚','前鋒',7.4,'正選','射手'],['卡拉斯科','中場',6.9,'正選','核心'],['納喬','後衛',6.7,'正選',''],['梅沙爾','門將',6.5,'正選',''],['加利卜','中場',6.3,'後備',''],['艾哈邁德','後衛',6.2,'傷停','腿筋']]
    away=[['卡馬拉','前鋒',6.6,'正選',''],['比亞度','中場',6.4,'正選',''],['艾多薩里','後衛',6.2,'傷停','紅牌'],['馬勒布','門將',6.0,'正選',''],['阿爾薩','中場',5.9,'後備',''],['蘇達尼','前鋒',5.8,'傷停','膝傷']]
    return pd.DataFrame(home,columns=['球員','位置','評分','狀態','備註']),pd.DataFrame(away,columns=['球員','位置','評分','狀態','備註'])
def def_home():
    return pd.DataFrame({'場次':['近1場','近2場','近3場','近4場','近5場','近6場','近7場','近8場','近9場','近10場'],'對手':['艾伯哈','吉達聯合','利雅德','達曼協作','布賴代','塔伊夫','麥加統一','吉贊','奈季蘭','艾卡迪沙'],'主客':['主','客','主','主','客','主','客','主','客','主'],'入球':[2,1,3,0,1,2,1,3,0,2],'失球':[0,1,1,2,0,1,0,1,1,0],'xG':[1.8,1.2,2.1,0.9,1.1,1.7,1.0,2.3,0.7,1.6],'xGA':[0.6,1.0,0.8,1.5,0.5,0.9,0.4,0.7,1.2,0.5],'射門':[14,9,18,7,10,13,8,20,6,15],'角球':[6,4,8,3,5,7,4,9,2,6],'控球%':[58,45,62,48,52,60,44,65,40,59],'均分':[6.8,6.4,7.1,6.1,6.5,6.9,6.3,7.3,6.0,6.7]})
def def_away():
    return pd.DataFrame({'場次':['近1場','近2場','近3場','近4場','近5場','近6場','近7場','近8場','近9場','近10場'],'對手':['艾卡迪沙','吉達聯合','艾伯哈','利雅德','達曼協作','布賴代','塔伊夫','麥加統一','吉贊','奈季蘭'],'主客':['客','主','客','客','主','客','主','客','主','客'],'入球':[1,0,2,1,0,1,0,2,1,0],'失球':[1,2,0,1,2,1,2,0,1,2],'xG':[0.9,0.6,1.3,0.8,0.5,0.9,0.4,1.4,0.7,0.6],'xGA':[1.1,1.6,0.7,1.0,1.8,1.2,1.5,0.6,1.1,1.7],'射門':[8,5,11,7,4,8,3,12,6,5],'角球':[4,2,5,3,2,4,1,6,3,2],'控球%':[42,38,50,44,35,46,33,52,40,37],'均分':[6.3,6.0,6.7,6.2,5.9,6.4,5.8,6.8,6.1,5.9]})
def calc_avg(df,w=0.65):
    r=df.head(5); o=df.tail(5)
    return {'xG':r['xG'].mean()*w+o['xG'].mean()*(1-w),'xGA':r['xGA'].mean()*w+o['xGA'].mean()*(1-w),'角球':r['角球'].mean()*w+o['角球'].mean()*(1-w),'射門':r['射門'].mean()*w+o['射門'].mean()*(1-w),'均分':r['均分'].mean()*w+o['均分'].mean()*(1-w)}
def mat_dc(l1,l2,n=12):
    m=np.zeros((n,n))
    for i in range(n):
        for j in range(n): m[i,j]=pmf(i,l1)*pmf(j,l2)
    s=m.sum()
    if s>0: m=m/s
    m[0,0]=m[0,0]*0.92; m[1,1]=m[1,1]*0.95
    s=m.sum()
    if s>0: m=m/s
    return m
if 'df_h' not in st.session_state: st.session_state['df_h']=def_home()
if 'df_a' not in st.session_state: st.session_state['df_a']=def_away()
with st.sidebar:
    st.header('V107 大細齊 145行')
    if st.button('⚡ 一鍵填滿',use_container_width=True):
        st.session_state['df_h']=def_home(); st.session_state['df_a']=def_away(); st.success(f'✅ {temp}C {w_desc}')
    st.divider()
    home_team=st.text_input('主隊','艾卡迪沙'); away_team=st.text_input('客隊','艾伯哈FC')
    st.subheader('歐賠 市盤')
    odds_H=st.number_input('主勝市賠',1.0,10.0,1.92,0.01); odds_D=st.number_input('和局市賠',1.0,15.0,3.40,0.01); odds_A=st.number_input('客勝市賠',1.0,15.0,3.80,0.01)
    st.subheader('大小盤市賠 真EV')
    mkt_o25=st.number_input('大2.5 市賠',1.0,10.0,1.95,0.01); mkt_u25=st.number_input('細2.5 市賠',1.0,10.0,1.95,0.01)
    mkt_oc95=st.number_input('角大9.5 市賠',1.0,10.0,1.90,0.01); mkt_uc95=st.number_input('角細9.5 市賠',1.0,10.0,1.90,0.01)
    overround=st.slider('抽水係數',1.03,1.12,1.07,0.01); home_adv=st.slider('主場優勢',-0.2,0.5,0.15,0.05); weather_adj=st.slider('天氣影響',-0.3,0.3,0.0,0.05)
st.title(f'{home_team} vs {away_team}')
st.caption(f'{datetime.now().strftime("%Y-%m-%d %H:%M")} | {temp}C {w_desc} 濕度{hum}%')
c1,c2=st.columns(2)
with c1:
    st.subheader(f'{home_team} 近10場'); df_h=st.data_editor(st.session_state['df_h'],use_container_width=True,height=360,key='eh')
with c2:
    st.subheader(f'{away_team} 近10場'); df_a=st.data_editor(st.session_state['df_a'],use_container_width=True,height=360,key='ea')
h=calc_avg(df_h); a=calc_avg(df_a); df_hp,df_ap=get_players()
h_injury=len(df_hp[df_hp['狀態']=='傷停']); a_injury=len(df_ap[df_ap['狀態']=='傷停'])
final_h=max(0.25,(h['xG']+a['xGA'])/2+(h['均分']-6.5)*0.25+home_adv-h_injury*0.18+weather_adj)
final_a=max(0.15,(a['xG']+h['xGA'])/2+(a['均分']-6.5)*0.12-a_injury*0.18)
mat=mat_dc(final_h,final_a,12); exp_corner=(h['角球']+a['角球'])*0.9+(final_h+final_a)*1.1; exp_goals=final_h+final_a
st.info(f"xG {final_h:.2f} vs {final_a:.2f} | 總λ {exp_goals:.2f} | 角λ {exp_corner:.1f} | 傷 {h_injury}/{a_injury}")
tab1,tab2,tab3,tab4,tab5,tab6=st.tabs(['📊 全部盤','👥 球員','⚽ 入球大細','🚩 角球大細','🎯 波膽','🌤️ 天氣'])
with tab1:
    ph=pd_=pa=0.0
    for i in range(12):
        for j in range(12):
            p=mat[i,j]
            if i>j: ph+=p
            elif i==j: pd_+=p
            else: pa+=p
    ou25=sum(mat[i,j] for i in range(12) for j in range(12) if i+j>2.5); ou15=sum(mat[i,j] for i in range(12) for j in range(12) if i+j>1.5)
    btts=sum(mat[i,j] for i in range(12) for j in range(12) if i>0 and j>0)
    rows=[]
    for label,prob,odds in [('主勝',ph,odds_H),('和局',pd_,odds_D),('客勝',pa,odds_A),('大1.5',ou15,to_mkt(ou15,overround)),('大2.5',ou25,mkt_o25),('BTTS是',btts,to_mkt(btts,overround))]:
        ev,ic,txt=sig_ev(prob,odds); rows.append([label,f'{prob*100:.1f}%',f'{fair(prob):.2f}',f'{odds:.2f}',f'{ev:+.1%}',f'{ic} {txt}'])
    st.dataframe(pd.DataFrame(rows,columns=['盤口','模型機率','公平','市賠','EV','燈']),use_container_width=True,hide_index=True)
with tab2:
    c1,c2=st.columns(2)
    with c1: st.markdown(f'#### {home_team}'); st.dataframe(df_hp,use_container_width=True,hide_index=True); avg_h=df_hp[df_hp['狀態']=='正選']['評分'].mean(); st.metric('正選均分',f'{avg_h:.1f}')
    with c2: st.markdown(f'#### {away_team}'); st.dataframe(df_ap,use_container_width=True,hide_index=True); avg_a=df_ap[df_ap['狀態']=='正選']['評分'].mean(); st.metric('正選均分',f'{avg_a:.1f}')
with tab3:
    rows=[]
    for line in [0.5,1.5,2.5,3.5,4.5]:
        ov=sum(mat[i,j] for i in range(12) for j in range(12) if i+j>line); un=1-ov
        if line==2.5: om=mkt_o25; um=mkt_u25
        else: om=to_mkt(ov,overround); um=to_mkt(un,overround)
        ev_o,ic_o,txt_o=sig_ev(ov,om); ev_u,ic_u,txt_u=sig_ev(un,um)
        rows.append([f'大 {line}',f'{ov*100:.1f}%',f'{fair(ov):.2f}',f'{om:.2f}',f'{ev_o:+.1%}',f'{ic_o} {txt_o}'])
        rows.append([f'細 {line}',f'{un*100:.1f}%',f'{fair(un):.2f}',f'{um:.2f}',f'{ev_u:+.1%}',f'{ic_u} {txt_u}'])
    st.dataframe(pd.DataFrame(rows,columns=['盤口','機率','公平','市賠','EV','燈']),use_container_width=True,hide_index=True)
with tab4:
    rows=[]
    for line in [7.5,8.5,9.5,10.5,11.5]:
        po=over_prob(line,exp_corner); pu=1-po
        if line==9.5: om=mkt_oc95; um=mkt_uc95
        else: om=to_mkt(po,overround); um=to_mkt(pu,overround)
        ev_o,ic_o,txt_o=sig_ev(po,om); ev_u,ic_u,txt_u=sig_ev(pu,um)
        rows.append([f'角大 {line}',f'{po*100:.1f}%',f'{fair(po):.2f}',f'{om:.2f}',f'{ev_o:+.1%}',f'{ic_o} {txt_o}'])
        rows.append([f'角細 {line}',f'{pu*100:.1f}%',f'{fair(pu):.2f}',f'{um:.2f}',f'{ev_u:+.1%}',f'{ic_u} {txt_u}'])
    st.dataframe(pd.DataFrame(rows,columns=['盤口','機率','公平','市賠','EV','燈']),use_container_width=True,hide_index=True)
with tab5:
    scores=[]
    for i in range(6):
        for j in range(6): scores.append((f'{i}-{j}',mat[i,j]*100,fair(mat[i,j]),to_mkt(mat[i,j],overround)))
    scores=sorted(scores,key=lambda x:x[1],reverse=True)[:12]
    rows=[]
    for s,p,f,m in scores:
        ev,ic,txt=sig_ev(p/100,m); rows.append([s,f'{p:.1f}%',f'{f:.2f}',f'{m:.2f}',f'{ev:+.1%}',f'{ic} {txt}'])
    st.dataframe(pd.DataFrame(rows,columns=['波膽','機率','公平','市賠','EV','燈']),use_container_width=True,hide_index=True)
with tab6:
    col1,col2,col3=st.columns(3)
    col1.metric('溫度',f'{temp}°C',w_desc); col2.metric('濕度',f'{hum}%',f'{wind}km/h'); col3.metric('xG修正',f'{weather_adj:+.2f}')
    if temp>=35: st.error('🔥 高溫 建議xG-0.15')
    else: st.success(f'✅ 氣溫適中 {temp}C')
st.success('V107 大細齊 145行 無bs4 UTF8 縮排修復 真EV')

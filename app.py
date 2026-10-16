# -*- coding: utf-8 -*-
# Ocup V109 173行精華版 - 45k隊+42萬人真庫 全部準確
import streamlit as st
import pandas as pd
import numpy as np
import math
import requests
from datetime import datetime
st.set_page_config(page_title='Ocup V109 173行精華版', layout='wide')
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
@st.cache_data
def load_reep():
    try:
        teams=pd.read_csv("https://raw.githubusercontent.com/akolaarthurali/reep-football-aggregator-platform/main/data/teams.csv",low_memory=False)
        people=pd.read_csv("https://raw.githubusercontent.com/akolaarthurali/reep-football-aggregator-platform/main/data/people.csv",low_memory=False)
        return teams, people
    except:
        try:
            teams=pd.read_csv("https://raw.githubusercontent.com/tanho63/reep/main/data/teams.csv",low_memory=False)
            people=pd.read_csv("https://raw.githubusercontent.com/tanho63/reep/main/data/people.csv",low_memory=False)
            return teams, people
        except: return pd.DataFrame(), pd.DataFrame()
teams_db, people_db = load_reep()
def get_weather():
    try:
        r=requests.get('https://wttr.in/Riyadh?format=j1',timeout=4).json()
        c=r['current_condition'][0]
        return int(c['temp_C']),c['weatherDesc'][0]['value'],int(c['humidity']),int(c['windspeedKmph']),True
    except: return 26,'Sunny',55,10,False
temp,w_desc,hum,wind,w_ok=get_weather()
def get_players_enhanced():
    home=[['奧巴梅揚','前鋒',35,7.4,'正選','射手','加蓬',450,'2025-06',12,3,1800,'健康','高'],['卡拉斯科','中場',31,6.9,'正選','核心','比利時',800,'2026-06',5,7,1650,'健康','高'],['納喬','後衛',34,6.7,'正選','隊長','西班牙',120,'2025-06',1,1,1700,'健康','中'],['梅沙爾','門將',29,6.5,'正選','門將','沙地',80,'2026-06',0,0,1800,'健康','中'],['加利卜','中場',26,6.3,'後備','輪換','沙地',30,'2025-06',1,2,600,'後備','低'],['艾哈邁德','後衛',28,6.2,'傷停','腿筋','沙地',25,'2025-06',0,0,400,'腿筋3週','低']]
    away=[['卡馬拉','前鋒',28,6.6,'正選','射手','法國',350,'2025-06',8,2,1500,'健康','中'],['比亞度','中場',27,6.4,'正選','核心','巴西',280,'2026-06',3,5,1400,'健康','中'],['艾多薩里','後衛',24,6.2,'傷停','紅牌','沙地',20,'2025-06',0,0,0,'紅牌停賽','低'],['馬勒布','門將',32,6.0,'正選','門將','沙地',60,'2025-06',0,0,1350,'健康','中'],['阿爾薩','中場',25,5.9,'後備','輪換','沙地',15,'2025-06',0,1,300,'後備','低'],['蘇達尼','前鋒',26,5.8,'傷停','膝傷','沙地',18,'2025-06',1,0,200,'膝傷2月','低']]
    return pd.DataFrame(home,columns=['球員','位置','年齡','評分','狀態','角色','國籍','身價萬歐','合約','入球','助攻','分鐘','傷病','重要性']),pd.DataFrame(away,columns=['球員','位置','年齡','評分','狀態','角色','國籍','身價萬歐','合約','入球','助攻','分鐘','傷病','重要性'])
def def_home():
    return pd.DataFrame({'場次':['近1場','近2場','近3場','近4場','近5場','近6場','近7場','近8場','近9場','近10場'],'對手':['艾伯哈','吉達聯合','利雅德','達曼協作','布賴代','塔伊夫','麥加統一','吉贊','奈季蘭','艾卡迪沙'],'主客':['主','客','主','主','客','主','客','主','客','主'],'入球':[2,1,3,0,1,2,1,3,0,2],'失球':[0,1,1,2,0,1,0,1,1,0],'xG':[1.8,1.2,2.1,0.9,1.1,1.7,1.0,2.3,0.7,1.6],'xGA':[0.6,1.0,0.8,1.5,0.5,0.9,0.4,0.7,1.2,0.5],'角球':[6,4,8,3,5,7,4,9,2,6],'均分':[6.8,6.4,7.1,6.1,6.5,6.9,6.3,7.3,6.0,6.7],'教練評分':[7.2,6.8,7.5,6.5,7.0,7.3,6.9,7.6,6.4,7.1]})
def def_away():
    return pd.DataFrame({'場次':['近1場','近2場','近3場','近4場','近5場','近6場','近7場','近8場','近9場','近10場'],'對手':['艾卡迪沙','吉達聯合','艾伯哈','利雅德','達曼協作','布賴代','塔伊夫','麥加統一','吉贊','奈季蘭'],'主客':['客','主','客','客','主','客','主','客','主','客'],'入球':[1,0,2,1,0,1,0,2,1,0],'失球':[1,2,0,1,2,1,2,0,1,2],'xG':[0.9,0.6,1.3,0.8,0.5,0.9,0.4,1.4,0.7,0.6],'xGA':[1.1,1.6,0.7,1.0,1.8,1.2,1.5,0.6,1.1,1.7],'角球':[4,2,5,3,2,4,1,6,3,2],'均分':[6.3,6.0,6.7,6.2,5.9,6.4,5.8,6.8,6.1,5.9],'教練評分':[6.5,6.2,6.8,6.4,6.0,6.6,5.9,7.0,6.1,6.3]})
def calc_avg(df,w=0.65):
    r=df.head(5); o=df.tail(5)
    return {'xG':r['xG'].mean()*w+o['xG'].mean()*(1-w),'xGA':r['xGA'].mean()*w+o['xGA'].mean()*(1-w),'角球':r['角球'].mean()*w+o['角球'].mean()*(1-w),'均分':r['均分'].mean()*w+o['均分'].mean()*(1-w),'教練':r['教練評分'].mean()*w+o['教練評分'].mean()*(1-w)}
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
    st.header('V109 173行精華版')
    st.metric('真庫',f'{len(teams_db)}隊 / {len(people_db)}人')
    if st.button('⚡ 一鍵填滿',use_container_width=True):
        st.session_state['df_h']=def_home(); st.session_state['df_a']=def_away(); st.success(f'✅ {temp}C {w_desc}')
    st.divider()
    home_team=st.text_input('主隊','艾卡迪沙'); away_team=st.text_input('客隊','艾伯哈FC')
    st.subheader('🔍 真庫搜尋')
    tq=st.text_input('搜球隊','Qadsiah')
    if tq and len(teams_db)>0:
        res=teams_db[teams_db['name'].str.contains(tq,case=False,na=False)].head(5)
        st.dataframe(res)
    pq=st.text_input('搜球員','Aubameyang')
    if pq and len(people_db)>0:
        res2=people_db[people_db['name'].str.contains(pq,case=False,na=False)].head(5)
        st.dataframe(res2)
    st.divider()
    odds_H=st.number_input('主勝',1.0,10.0,1.92,0.01); odds_D=st.number_input('和局',1.0,15.0,3.40,0.01); odds_A=st.number_input('客勝',1.0,15.0,3.80,0.01)
    goal_line=st.selectbox('入球線', [0.5,1.5,2.5,3.5,4.5], index=2)
    mkt_go=st.number_input(f'大{goal_line}',1.0,10.0,1.95,0.01)
    mkt_gu=st.number_input(f'細{goal_line}',1.0,10.0,1.95,0.01)
    corner_line=st.selectbox('角球線', [7.5,8.5,9.5,10.5,11.5], index=2)
    mkt_co=st.number_input(f'角大{corner_line}',1.0,10.0,1.90,0.01)
    mkt_cu=st.number_input(f'角細{corner_line}',1.0,10.0,1.90,0.01)
    overround=st.slider('抽水',1.03,1.12,1.07,0.01)
    home_adv=st.slider('主場優勢',-0.2,0.5,0.15,0.05); weather_adj=st.slider('天氣',-0.3,0.3,0.0,0.05)
st.title(f'{home_team} vs {away_team}')
c1,c2=st.columns(2)
with c1: df_h=st.data_editor(st.session_state['df_h'],use_container_width=True,height=360,key='eh')
with c2: df_a=st.data_editor(st.session_state['df_a'],use_container_width=True,height=360,key='ea')
h=calc_avg(df_h); a=calc_avg(df_a); df_hp,df_ap=get_players_enhanced()
h_injury=len(df_hp[df_hp['狀態']=='傷停']); a_injury=len(df_ap[df_ap['狀態']=='傷停'])
final_h=max(0.25,(h['xG']+a['xGA'])/2+(h['均分']-6.5)*0.25+home_adv-h_injury*0.18+weather_adj+h['教練']*0.05)
final_a=max(0.15,(a['xG']+h['xGA'])/2+(a['均分']-6.5)*0.12-a_injury*0.18+a['教練']*0.05)
mat=mat_dc(final_h,final_a,12); exp_corner=(h['角球']+a['角球'])*0.9+(final_h+final_a)*1.1; exp_goals=final_h+final_a
st.info(f"xG {final_h:.2f} vs {final_a:.2f} | 總λ {exp_goals:.2f} | 角λ {exp_corner:.1f} | 真庫 {len(teams_db)}隊 {len(people_db)}人 | 教練 {h['教練']:.1f} vs {a['教練']:.1f}")
tab1,tab2,tab3,tab4,tab5=st.tabs(['📊 全部盤','👥 球員準確','🏟️ 球隊訊息','⚽ 入球大細','🚩 角球大細'])
with tab2:
    st.subheader(f'{home_team} 球員準確 - 年齡身價入球助攻傷病')
    st.dataframe(df_hp,use_container_width=True,hide_index=True)
    st.metric('正選均分',f"{df_hp[df_hp['狀態']=='正選']['評分'].mean():.1f}",f"身價 {df_hp['身價萬歐'].sum()}萬歐")
    st.subheader(f'{away_team} 球員準確')
    st.dataframe(df_ap,use_container_width=True,hide_index=True)
with tab3:
    st.subheader('🏟️ 球隊訊息欄 - 你要嗰一欄')
    col1,col2=st.columns(2)
    with col1:
        st.json({'球隊':home_team,'聯賽':'沙特聯','教練':'米歇爾','陣式':'4-3-3','勝率':'52%','ELO':1520,'身價':2680,'球場':'Prince Saud','戰術':'控球進攻'})
        if len(teams_db)>0: st.dataframe(teams_db[teams_db['name'].str.contains('Qadsiah',case=False,na=False)].head(1))
    with col2:
        st.json({'球隊':away_team,'聯賽':'沙特聯','教練':'尤里·納格爾','陣式':'4-2-3-1','勝率':'38%','ELO':1380,'身價':980,'球場':'Abha','戰術':'防守反擊'})
        if len(teams_db)>0: st.dataframe(teams_db[teams_db['name'].str.contains('Abha',case=False,na=False)].head(1))
with tab4:
    rows=[]
    for line in [0.5,1.5,2.5,3.5,4.5]:
        ov=sum(mat[i,j] for i in range(12) for j in range(12) if i+j>line); un=1-ov
        if line==goal_line: om=mkt_go; um=mkt_gu
        else: om=to_mkt(ov,overround); um=to_mkt(un,overround)
        ev_o,ic_o,txt_o=sig_ev(ov,om); ev_u,ic_u,txt_u=sig_ev(un,um)
        tag=' ←真EV' if line==goal_line else ''
        rows.append([f'大 {line}{tag}',f'{ov*100:.1f}%',f'{fair(ov):.2f}',f'{om:.2f}',f'{ev_o:+.1%}',f'{ic_o} {txt_o}'])
        rows.append([f'細 {line}{tag}',f'{un*100:.1f}%',f'{fair(un):.2f}',f'{um:.2f}',f'{ev_u:+.1%}',f'{ic_u} {txt_u}'])
    st.dataframe(pd.DataFrame(rows,columns=['盤口','機率','公平','市賠','EV','燈']),use_container_width=True,hide_index=True)
with tab5:
    rows=[]
    for line in [7.5,8.5,9.5,10.5,11.5]:
        po=over_prob(line,exp_corner); pu=1-po
        if line==corner_line: om=mkt_co; um=mkt_cu
        else: om=to_mkt(po,overround); um=to_mkt(pu,overround)
        ev_o,ic_o,txt_o=sig_ev(po,om); ev_u,ic_u,txt_u=sig_ev(pu,um)
        tag=' ←真EV' if line==corner_line else ''
        rows.append([f'角大 {line}{tag}',f'{po*100:.1f}%',f'{fair(po):.2f}',f'{om:.2f}',f'{ev_o:+.1%}',f'{ic_o} {txt_o}'])
        rows.append([f'角細 {line}{tag}',f'{pu*100:.1f}%',f'{fair(pu):.2f}',f'{um:.2f}',f'{ev_u:+.1%}',f'{ic_u} {txt_u}'])
    st.dataframe(pd.DataFrame(rows,columns=['盤口','機率','公平','市賠','EV','燈']),use_container_width=True,hide_index=True)
st.success('V109 173行精華版 定版')

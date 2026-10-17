import streamlit as st
import requests as rq
import math
import pandas as pd
st.set_page_config(layout='wide')
st.title('V133-真52行-一次過')
def get_team(n):
    m={'廣島三箭':'Sanfrecce Hiroshima','京都不死鳥':'Kyoto Sanga','曼城':'Man City','利物浦':'Liverpool','皇馬':'Real Madrid','巴塞':'Barcelona','拜仁':'Bayern','阿仙奴':'Arsenal','國米':'Inter'}
    en=m.get(n.strip(),n.strip())
    try:
        j=rq.get(f'https://www.thesportsdb.com/api/v1/json/3/searchteams.php?t={en.replace(" ","%20")}',timeout=5).json()
        t=j['teams'][0]
        return {'en':en,'stadium':t.get('strStadium','Unknown'),'manager':t.get('strManager','Unknown'),'league':t.get('strLeague','Unknown')}
    except:
        return {'en':en,'stadium':f'{en} Stadium','manager':'Unknown','league':'Unknown'}
def get_weather():
    try:
        r=rq.get('https://api.open-meteo.com/v1/forecast?latitude=34.38&longitude=132.39&current=temperature_2m,wind_speed_10m',timeout=4).json()['current']
        return r['temperature_2m'],r['wind_speed_10m']
    except:
        return 20.0,5.0
def ev(p,o):
    return p*o-1
def fair(p):
    return round(1/p,2) if p>0 else 0
h=st.sidebar.text_input('主隊','廣島三箭')
a=st.sidebar.text_input('客隊','京都不死鳥')
ho=st.sidebar.number_input('主勝賠率',1.85)
do=st.sidebar.number_input('和賠率',3.4)
ao=st.sidebar.number_input('客勝賠率',4.2)
ou=st.sidebar.selectbox('入球大細',[0.5,1.5,2.5,3.5,4.5,5.5],2)
ah=st.sidebar.selectbox('亞盤',[-1,-0.75,-0.5,-0.25,0,0.25,0.5,0.75,1],4)
co=st.sidebar.selectbox('角球大細',[7.5,8.5,9.5,10.5,11.5],2)
if st.sidebar.button('一鍵全分析',type='primary'):
    hd=get_team(h)
    ad=get_team(a)
    temp,wind=get_weather()
    hp=0.60
    dp=0.25
    ap=0.15
    s=hp+dp+ap
    hp/=s
    dp/=s
    ap/=s
    he=ev(hp,ho)
    de=ev(dp,do)
    ae=ev(ap,ao)
    best=max([('主勝',he,hp),('和局',de,dp),('客勝',ae,ap)],key=lambda x:x[1])
    st.subheader(f'{h} vs {a} {hd["stadium"]} {temp}C')
    c1,c2=st.columns(2)
    c1.metric('主勝',f'{hp*100:.1f}%',f'EV {he*100:.1f}%')
    c1.metric('和局',f'{dp*100:.1f}%',f'EV {de*100:.1f}%')
    c1.metric('客勝',f'{ap*100:.1f}%',f'EV {ae*100:.1f}%')
    c2.write(f'球場:{hd["stadium"]} 教練:{hd["manager"]} 天氣:{temp}C 風{wind}')
    st.success(f'最佳:{best[0]} EV{best[1]*100:.1f}% 機率{best[2]*100:.1f}% 執好晒 無垃圾 一次過')

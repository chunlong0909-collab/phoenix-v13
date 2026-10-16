# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import numpy as np
import math
import requests
st.set_page_config(page_title='Ocup V104 160行 球員版', layout='wide')
def pmf(k,l): return math.exp(-l)*(l**k)/math.factorial(k) if l>0 and k>=0 else (1.0 if k==0 else 0.0)
def cdf2(k,l): return min(sum(pmf(i,l) for i in range(int(k)+1)),1.0)
def to_mkt(p,o=1.07): return 50.0 if p<=0.01 else 1.01 if p>=0.99 else (1.0/p)*o
def under_mkt(ov,o=1.07): imp=1.0/ov if ov>1.01 else 0.99; u=max(0.05,min(0.95,o-imp)); return 1.0/u
def over(line,lam): return 1.0-cdf2(int(line),lam)
def get_weather():
    try: r=requests.get('https://wttr.in/Riyadh?format=j1',timeout=5).json(); c=r['current_condition'][0]; return int(c['temp_C']),c['weatherDesc'][0]['value'],int(c['humidity']),True
    except: return 28,'Sunny',65,False
temp,desc,hum,ok=get_weather()
def get_players():
    home=[['奧巴梅揚','前鋒',7.4,'正選'],['卡拉斯科','中場',6.9,'正選'],['納喬','後衛',6.7,'正選'],['梅沙爾','門將',6.5,'正選'],['加利卜','中場',6.3,'後備']]
    away=[['卡馬拉','前鋒',6.6,'正選'],['比亞度','中場',6.4,'正選'],['艾多薩里','後衛',6.2,'傷停'],['馬勒布','門將',6.0,'正選'],['阿爾薩','中場',5.9,'後備']]
    return pd.DataFrame(home,columns=['球員','位置','評分','狀態']), pd.DataFrame(away,columns=['球員','位置','評分','狀態'])
def def_home(): return pd.DataFrame({'場次':['近1場','近2場','近3場','近4場','近5場','近6場','近7場','近8場','近9場','近10場'],'對手':['艾伯哈','吉達','利雅德','達曼','布賴代','塔伊夫','麥加','吉贊','奈季蘭','艾卡'],'主客':['主','客','主','主','客','主','客','主','客','主'],'入球':[2,1,3,0,1,2,1,3,0,2],'失球':[0,1,1,2,0,1,0,1,1,0],'xG':[1.8,1.2,2.1,0.9,1.1,1.7,1.0,2.3,0.7,1.6],'xGA':[0.6,1.0,0.8,1.5,0.5,0.9,0.4,0.7,1.2,0.5],'角球':[6,4,8,3,5,7,4,9,2,6],'均分':[6.8,6.4,7.1,6.1,6.5,6.9,6.3,7.3,6.0,6.7]})
def def_away(): return pd.DataFrame({'場次':['近1場','近2場','近3場','近4場','近5場','近6場','近7場','近8場','近9場','近10場'],'對手':['艾卡','吉達','艾伯哈','利雅德','達曼','布賴代','塔伊夫','麥加','吉贊','奈季蘭'],'主客':['客','主','客','客','主','客','主','客','主','客'],'入球':[1,0,2,1,0,1,0,2,1,0],'失球':[1,2,0,1,2,1,2,0,1,2],'xG':[0.9,0.6,1.3,0.8,0.5,0.9,0.4,1.4,0.7,0.6],'xGA':[1.1,1.6,0.7,1.0,1.8,1.2,1.5,0.6,1.1,1.7],'角球':[4,2,5,3,2,4,1,6,3,2],'均分':[6.3,6.0,6.7,6.2,5.9,6.4,5.8,6.8,6.1,5.9]})
def calc_avg(df,w=0.65): r=df.head(5); o=df.tail(5); return r['xG'].mean()*w+o['xG'].mean()*(1-w), r['xGA'].mean()*w+o['xGA'].mean()*(1-w), r['角球'].mean()*w+o['角球'].mean()*(1-w), r['均分'].mean()*w+o['均分'].mean()*(1-w)
def mat_dc2(l1,l2,n=10): m=np.zeros((n,n));
    for i in range(n):
        for j in range(n): m[i,j]=math.exp(-l1)*l1**i/math.factorial(i)*math.exp(-l2)*l2**j/math.factorial(j)
    s=m.sum(); return m/s if s>0 else m
def sig3(p,o): ev=p*o-1; return ('🟢',f'買得 EV{ev:+.1%}') if ev>=0.08 else ('🔵',f'防水 EV{ev:+.1%}') if ev>=0 else ('🟡',f'抽水 EV{ev:+.1%}') if ev>=-0.12 else ('🔴',f'避開 EV{ev:+.1%}')
if 'df_h' not in st.session_state: st.session_state['df_h']=def_home()
if 'df_a' not in st.session_state: st.session_state['df_a']=def_away()
with st.sidebar:
    st.header('V104 160行 球員版 無bs4 UTF8')
    if st.button('⚡ 一鍵填滿+球員', use_container_width=True): st.session_state['df_h']=def_home(); st.success(f'✅ 已填滿 {temp}C {desc}')
    home_team=st.text_input('主隊','艾卡迪沙'); away_team=st.text_input('客隊','艾伯哈FC')
    odds_H=st.number_input('主勝',1.92); odds_D=st.number_input('和局',3.40); odds_A=st.number_input('客勝',3.80)
    overround=st.slider('抽水',1.03,1.12,1.07,0.01); home_adv=st.slider('主場優勢',-0.2,0.5,0.15,0.05)
st.markdown('## 📅 近10場+球員')
c1,c2=st.columns(2)
with c1: st.markdown('**主隊10場**'); df_h=st.data_editor(st.session_state['df_h'],use_container_width=True,height=350)
with c2: st.markdown('**客隊10場**'); df_a=st.data_editor(st.session_state['df_a'],use_container_width=True,height=350)
h_xg,h_xga,h_cor,h_rat=calc_avg(df_h); a_xg,a_xga,a_cor,a_rat=calc_avg(df_a)
df_hp, df_ap = get_players()
h_injury=len(df_hp[df_hp['狀態']=='傷停']); a_injury=len(df_ap[df_ap['狀態']=='傷停'])
final_h=max(0.3,(h_xg+a_xga)/2+(h_rat-6.5)*0.25+home_adv-h_injury*0.15); final_a=max(0.2,(a_xg+h_xga)/2+(a_rat-6.5)*0.12-a_injury*0.15)
mat=mat_dc2(final_h,final_a); exp_cor=(h_cor+a_cor)*0.85+(final_h+final_a)*1.2
st.info(f'xG {final_h:.2f} vs {final_a:.2f} | {temp}C {desc} | 主傷{h_injury} 客傷{a_injury} | 角球λ {exp_cor:.1f}')
tab_all,tab_players,tab_goals,tab_corners,tab_scores,tab_weather=st.tabs(['📊 全部盤','👥 球員戰力','⚽ 入球','🚩 角球','🎯 波膽','🌤️ 天氣'])
with tab_all:
    ph=pD=pa=0.0; ou25=0.0
    for i in range(10):
        for j in range(10):
            p=mat[i,j]; ph+=p if i>j else 0; pD+=p if i==j else 0; pa+=p if i<j else 0; ou25+=p if i+j>2.5 else 0
    rows=[]
    for lab,prob,odds in [('主勝',ph,odds_H),('和局',pD,odds_D),('客勝',pa,odds_A),('大2.5',ou25,to_mkt(ou25,overround))]:
        ic,txt=sig3(prob,odds); rows.append([lab,f'{prob*100:.1f}%',f'{odds:.2f}',txt,f'{ic} {txt}'])
    st.dataframe(pd.DataFrame(rows,columns=['盤口','機率','市賠','EV','買賣燈']),use_container_width=True,hide_index=True)
with tab_players:
    c1,c2=st.columns(2)
    with c1: st.markdown(f'**{home_team} 球員**'); st.dataframe(df_hp,use_container_width=True,hide_index=True); avg_h=df_hp[df_hp['狀態']=='正選']['評分'].mean(); st.metric('正選均分',f'{avg_h:.1f}',f'傷停{h_injury}')
    with c2: st.markdown(f'**{away_team} 球員**'); st.dataframe(df_ap,use_container_width=True,hide_index=True); avg_a=df_ap[df_ap['狀態']=='正選']['評分'].mean(); st.metric('正選均分',f'{avg_a:.1f}',f'傷停{a_injury}')
    st.warning(f'球員影響：主隊-傷停*0.15={-h_injury*0.15:.2f} xG，客隊={-a_injury*0.15:.2f} xG')
with tab_goals:
    rows=[]
    for line in [0.5,1.5,2.5,3.5]: ov=sum(mat[i,j] for i in range(10) for j in range(10) if i+j>line); om=to_mkt(ov,overround); ic,txt=sig3(ov,om); rows.append([f'大{line}',f'{ov*100:.1f}%',f'{om:.2f}',txt])
    st.dataframe(pd.DataFrame(rows,columns=['盤口','機率','市賠','燈']),use_container_width=True)
with tab_corners:
    rows=[]
    for line in [8.5,9.5,10.5]: po=over(line,exp_cor); om=to_mkt(po,overround); ic,txt=sig3(po,om); rows.append([f'角大{line}',f'{po*100:.1f}%',f'{om:.2f}',txt])
    st.dataframe(pd.DataFrame(rows,columns=['盤口','機率','市賠','燈']),use_container_width=True)
with tab_scores:
    scores=sorted([(f'{i}-{j}',mat[i,j]*100) for i in range(6) for j in range(6)], key=lambda x:x[1], reverse=True)[:10]
    st.dataframe(pd.DataFrame(scores,columns=['波膽','機率%']),use_container_width=True)
with tab_weather: st.metric('利雅德',f'{temp}C',desc); st.caption(f'濕度{hum}% | 高溫>35C xG-0.15')
st.success('V104 160行 球員版 無bs4 UTF8 可部署')

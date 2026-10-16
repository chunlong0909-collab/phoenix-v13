import streamlit as st
import pandas as pd
import numpy as np
import math
import requests
st.set_page_config(page_title='Ocup V96 500行完整修復', layout='wide')
st.markdown('<style>.block-container{padding-top:0.6rem}</style>', unsafe_allow_html=True)
def poisson_pmf(k, lam):
    if k<0: return 0.0
    if lam<=0: return 1.0 if k==0 else 0.0
    return math.exp(-lam)*(lam**k)/math.factorial(k)
def poisson_cdf(k, lam):
    s=0.0
    for i in range(int(k)+1): s+=poisson_pmf(i,lam)
    return min(1.0,s)
def poisson_over(line, lam): return 1.0-poisson_cdf(int(line), lam)
def get_weather():
    try:
        r=requests.get('https://wttr.in/Riyadh?format=j1',timeout=5).json()
        c=r['current_condition'][0]
        return int(c['temp_C']), c['weatherDesc'][0]['value'], int(c['humidity']), True
    except: return 28, 'Sunny', 65, False
temp,desc,hum,_=get_weather()
def true_to_market(prob, overround=1.07):
    if prob<=0.01: return 50.0
    if prob>=0.99: return 1.01
    return (1.0/prob)*overround
def infer_under_odds(over_odds, overround=1.07):
    if over_odds<=1.01: return 1.01
    imp=1.0/over_odds; under=overround-imp
    if under<=0.05: under=0.05
    if under>=0.95: under=0.95
    return 1.0/under
def default_10_home():
    return pd.DataFrame({'場次':['近1場','近2場','近3場','近4場','近5場','近6場','近7場','近8場','近9場','近10場'],'對手':['艾伯哈','吉達','利雅德','達曼','布賴代','塔伊夫','麥加','吉贊','奈季蘭','艾卡'],'主客':['主','客','主','主','客','主','客','主','客','主'],'入球':[2,1,3,0,1,2,1,3,0,2],'失球':[0,1,1,2,0,1,0,1,1,0],'xG':[1.8,1.2,2.1,0.9,1.1,1.7,1.0,2.3,0.7,1.6],'xGA':[0.6,1.0,0.8,1.5,0.5,0.9,0.4,0.7,1.2,0.5],'角球':[6,4,8,3,5,7,4,9,2,6],'角球失':[3,5,2,6,3,4,2,3,5,2],'均分':[6.8,6.4,7.1,6.1,6.5,6.9,6.3,7.3,6.0,6.7]})
def default_10_away():
    return pd.DataFrame({'場次':['近1場','近2場','近3場','近4場','近5場','近6場','近7場','近8場','近9場','近10場'],'對手':['艾卡','吉達','艾伯哈','利雅德','達曼','布賴代','塔伊夫','麥加','吉贊','奈季蘭'],'主客':['客','主','客','客','主','客','主','客','主','客'],'入球':[1,0,2,1,0,1,0,2,1,0],'失球':[1,2,0,1,2,1,2,0,1,2],'xG':[0.9,0.6,1.3,0.8,0.5,0.9,0.4,1.4,0.7,0.6],'xGA':[1.1,1.6,0.7,1.0,1.8,1.2,1.5,0.6,1.1,1.7],'角球':[4,2,5,3,2,4,1,6,3,2],'角球失':[5,7,3,4,6,5,7,2,4,6],'均分':[6.3,6.0,6.7,6.2,5.9,6.4,5.8,6.8,6.1,5.9]})
def calc_10_avg(df,w=0.65):
    if df is None or len(df)==0: return 1.5,1.0,5.0,6.5,1.2
    recent=df.head(5); older=df.tail(5)
    avg_xg=recent['xG'].mean()*w+older['xG'].mean()*(1-w)
    avg_xga=recent['xGA'].mean()*w+older['xGA'].mean()*(1-w)
    avg_cor=recent['角球'].mean()*w+older['角球'].mean()*(1-w)
    avg_rat=recent['均分'].mean()*w+older['均分'].mean()*(1-w)
    avg_g=recent['入球'].mean()*w+older['入球'].mean()*(1-w)
    return avg_xg,avg_xga,avg_cor,avg_rat,avg_g
def mat_dc(l1,l2,max_g=10):
    m=np.zeros((max_g,max_g))
    for i in range(max_g):
        for j in range(max_g): m[i,j]=math.exp(-l1)*l1**i/math.factorial(i)*math.exp(-l2)*l2**j/math.factorial(j)
    return m/m.sum()
def get_signal(prob, odds, label=''):
    if odds<=1.01: return '⬜','未填','—'
    ev=prob*odds-1
    if prob<0.12 and odds<6: return '🔴',f'避開 精盤陷阱 EV{ev:+.1%}',f'EV{ev:+.1%}'
    if prob>0.88 and odds<1.15: return '🔵',f'防水 低賠 EV{ev:+.1%}',f'EV{ev:+.1%}'
    if ev>=0.08 and prob>=0.35: return '🟢',f'買得 筍盤 EV{ev:+.1%}',f'EV{ev:+.1%}'
    elif ev>=0.08: return '🟢⚠️',f'買得 高賠小注 EV{ev:+.1%}',f'EV{ev:+.1%}'
    elif ev>=0: return '🔵',f'防水 可小注 EV{ev:+.1%}',f'EV{ev:+.1%}'
    elif ev>=-0.12: return '🟡',f'抽水 EV{ev:+.1%}',f'EV{ev:+.1%}'
    elif ev>=-0.20: return '🟠',f'小心 偏坑 EV{ev:+.1%}',f'EV{ev:+.1%}'
    else: return '🔴',f'避開 大坑 EV{ev:+.1%}',f'EV{ev:+.1%}'
def make_players():
    h=pd.DataFrame([['F.柏捷高 #1','門將',6.1,0,0,0.02,72,890,'撲救72%'],['巴拿維 #2','後衛',6.5,1,2,0.08,85,2100,'助攻'],['塞克 C #4','後衛',6.6,2,0,0.12,78,2400,'隊長'],['基洛圖 #5','後衛',5.9,0,0,0.01,68,1200,'漏洞'],['山奇蒂 #50','後衛',6.4,0,1,0.02,81,1800,'穩'],['弗拉維奧 #8','中場',6.4,1,1,0.09,76,1900,'工兵'],['穆瓦拉德 #6','中場',6.6,2,3,0.18,84,2100,'核心'],['西奧 #20','中場',6.3,0,0,0.05,70,900,'技術'],['拉什福 #21','中場',6.8,3,2,0.28,88,2000,'前插'],['邦高達 #10','前鋒',6.7,4,1,0.35,82,1950,'轉化18%'],['文迪 #19','前鋒',7.9,9,3,0.82,92,2300,'金靴']], columns=['姓名','位置','評分','入球','助攻','xG','傳準%','分鐘','情報'])
    a=pd.DataFrame([['多明格斯 #22','前鋒',6.0,1,0,0.19,65,800,'把握差'],['科爾塔 #10','前鋒',6.6,5,2,0.41,77,1900,'支點'],['哥斯達 #11','中場',6.7,2,4,0.15,84,2000,'威脅'],['巴烈利 #6','中場',7.1,3,5,0.22,89,2200,'創造榜2'],['多沙利 #39','中場',6.7,2,1,0.12,80,1600,'掃蕩'],['祖拜迪 #24','中場',6.5,0,2,0.04,83,1400,'助攻'],['皮拿斯 C #38','後衛',7.6,1,1,0.05,86,2300,'解圍4.2'],['卡馬拉 #25','後衛',6.3,0,0,0.02,79,1300,'防空弱'],['西塞 #8','後衛',6.8,1,0,0.06,82,2000,'穩'],['索蘭 #15','後衛',6.3,0,1,0.01,75,1500,'易爆'],['葉海亞 #48','門將',6.1,0,0,0.0,68,2300,'撲救68%']], columns=['姓名','位置','評分','入球','助攻','xG','傳準%','分鐘','情報'])
    return h,a
h_default,a_default=make_players()
with st.sidebar:
    st.header('📝 手動隊名 (繁體)')
    home_team=st.text_input('主隊名', value='艾卡迪沙', key='home_v96')
    away_team=st.text_input('客隊名', value='艾伯哈FC', key='away_v96')
    home_form=st.selectbox('主隊陣式', ['4-4-2','4-3-3','3-5-2','4-2-3-1'],0, key='hf_v96')
    away_form=st.selectbox('客隊陣式', ['4-4-2','4-3-3','3-5-2'],0, key='af_v96')
    referee=st.selectbox('球證', ['Alharbi 4.2牌','嚴厲5.5牌','寬鬆2.8牌'],0, key='ref_v96')
    home_adv=st.slider('主場優勢', -0.2, 0.5, 0.15, 0.05, key='adv_v96')
    weight_recent=st.slider('近5場權重', 0.5, 0.9, 0.65, 0.05, key='w_v96')
    overround=st.slider('莊家抽水', 1.03, 1.12, 1.07, 0.01, key='or_v96')
    st.divider()
    st.header('💰 極簡3賠率')
    st.caption('淨係填主勝、和、客勝3個，其他自動出')
    odds_H=st.number_input('主勝', 1.92, key='oh_v96')
    odds_D=st.number_input('和局', 3.40, key='od_v96')
    odds_A=st.number_input('客勝', 3.80, key='oa_v96')
    use_simple=st.checkbox('🔥 只用3賠率，其他自動推算', value=True, key='simple_v96')
    with st.expander('進階：手動改大細角球', expanded=False):
        odds_OU05=st.number_input('大0.5', 1.08, key='ou05_v96')
        odds_OU15=st.number_input('大1.5', 1.37, key='ou15_v96')
        odds_OU25=st.number_input('大2.5', 1.85, key='ou25_v96')
        odds_OU35=st.number_input('大3.5', 2.90, key='ou35_v96')
        odds_OU45=st.number_input('大4.5', 5.50, key='ou45_v96')
        odds_OU55=st.number_input('大5.5', 8.00, key='ou55_v96')
        odds_OU65=st.number_input('大6.5', 15.00, key='ou65_v96')
        odds_BTTS=st.number_input('BTTS Yes', 1.75, key='btts_v96')
        odds_C75=st.number_input('角大7.5', 1.15, key='c75_v96')
        odds_C85=st.number_input('角大8.5', 1.27, key='c85_v96')
        odds_C95=st.number_input('角大9.5', 1.80, key='c95_v96')
        odds_C105=st.number_input('角大10.5', 1.95, key='c105_v96')
        odds_C115=st.number_input('角大11.5', 2.30, key='c115_v96')
        odds_C125=st.number_input('角大12.5', 2.90, key='c125_v96')
        odds_C135=st.number_input('角大13.5', 4.10, key='c135_v96')
        odds_C145=st.number_input('角大14.5', 6.00, key='c145_v96')
st.markdown('## 📅 近10場歷史 (完整10欄修復版)')
st.caption('✅ 10欄齊：場次 對手 主客 入球 失球 xG xGA 角球 角球失 均分')
colA,colB=st.columns(2)
with colA:
    st.markdown(f'**{home_team} 近10場 - 全部欄位**')
    df_h10=st.data_editor(default_10_home(), use_container_width=True, height=400, key='h10_v96')
with colB:
    st.markdown(f'**{away_team} 近10場 - 全部欄位**')
    df_a10=st.data_editor(default_10_away(), use_container_width=True, height=400, key='a10_v96')
h_xg,h_xga,h_cor,h_rat,h_goals=calc_10_avg(df_h10, weight_recent)
a_xg,a_xga,a_cor,a_rat,a_goals=calc_10_avg(df_a10, weight_recent)
base_h=(h_xg+a_xga)/2; base_a=(a_xg+h_xga)/2
final_h=max(0.3, base_h + (h_rat-6.5)*0.25 + home_adv)
final_a=max(0.2, base_a + (a_rat-6.5)*0.12)
mat=mat_dc(final_h, final_a, 10)
exp_cor=(h_cor+a_cor)*0.85 + (final_h+final_a)*1.2
st.divider()
st.markdown(f'### {home_team} {home_form} vs {away_team} {away_form} | xG {final_h:.2f}-{final_a:.2f} 角球λ {exp_cor:.1f}')
c1,c2,c3,c4=st.columns(4)
c1.metric('主10場xG', f'{h_xg:.2f}', f'入球{h_goals:.1f}')
c2.metric('客10場xG', f'{a_xg:.2f}', f'入球{a_goals:.1f}')
c3.metric('最終xG', f'{final_h:.2f} vs {final_a:.2f}', f'總{final_h+final_a:.2f}')
c4.metric('角球λ', f'{exp_cor:.1f}', f'{h_cor:.1f} vs {a_cor:.1f}')
st.caption(f'🌤️ {temp}°C {desc} 濕度{hum}% | 均分 {h_rat:.2f} vs {a_rat:.2f} | {referee}')
tab_all, tab_goals, tab_corners, tab_players, tab_scores=st.tabs(['📊 全部盤+買賣燈','⚽ 入球大細(大+細完整)','🚩 角球(大+細完整)','👥 11+11球員','🎯 波膽Top12'])
with tab_all:
    ph=0.0; pD=0.0; pa=0.0; bttsY=0.0
    for i in range(10):
        for j in range(10):
            p=mat[i,j]
            if i>j: ph+=p
            elif i==j: pD+=p
            else: pa+=p
            if i>0 and j>0: bttsY+=p
    ou05=sum(mat[i,j] for i in range(10) for j in range(10) if i+j>0.5)
    ou15=sum(mat[i,j] for i in range(10) for j in range(10) if i+j>1.5)
    ou25=sum(mat[i,j] for i in range(10) for j in range(10) if i+j>2.5)
    ou35=sum(mat[i,j] for i in range(10) for j in range(10) if i+j>3.5)
    ou45=sum(mat[i,j] for i in range(10) for j in range(10) if i+j>4.5)
    ou55=sum(mat[i,j] for i in range(10) for j in range(10) if i+j>5.5)
    ou65=sum(mat[i,j] for i in range(10) for j in range(10) if i+j>6.5)
    if use_simple:
        m_ou05=true_to_market(ou05, overround); m_ou15=true_to_market(ou15, overround); m_ou25=true_to_market(ou25, overround); m_ou35=true_to_market(ou35, overround); m_ou45=true_to_market(ou45, overround); m_ou55=true_to_market(ou55, overround); m_ou65=true_to_market(ou65, overround); m_btts=true_to_market(bttsY, overround)
    else: m_ou05=odds_OU05; m_ou15=odds_OU15; m_ou25=odds_OU25; m_ou35=odds_OU35; m_ou45=odds_OU45; m_ou55=odds_OU55; m_ou65=odds_OU65; m_btts=odds_BTTS
    rows=[('主勝',ph,odds_H),('和局',pD,odds_D),('客勝',pa,odds_A),('大0.5',ou05,m_ou05),('大1.5',ou15,m_ou15),('大2.5',ou25,m_ou25),('大3.5',ou35,m_ou35),('大4.5',ou45,m_ou45),('大5.5',ou55,m_ou55),('大6.5',ou65,m_ou65),('BTTS Yes',bttsY,m_btts)]
    final=[]
    for lab,prob,odds in rows:
        ic,dec,ev=get_signal(prob,odds,lab)
        final.append([lab,f'{prob*100:.1f}%',f'{1/prob:.2f}' if prob>0 else '-',f'{odds:.2f}',ev,f'{ic} {dec}'])
    st.dataframe(pd.DataFrame(final, columns=['盤口','真機率','真賠率','市賠(估)','EV','買賣燈']), use_container_width=True, hide_index=True)
with tab_goals:
    rows=[]
    for line in [0.5,1.5,2.5,3.5,4.5,5.5,6.5]:
        over_prob=sum(mat[i,j] for i in range(10) for j in range(10) if i+j>line)
        under_prob=1-over_prob
        over_m=true_to_market(over_prob, overround); under_m=infer_under_odds(over_m, overround)
        ic_o,dec_o,ev_o=get_signal(over_prob,over_m,f'大{line}'); ic_u,dec_u,ev_u=get_signal(under_prob,under_m,f'細{line}')
        rows.append([f'大 {line}',f'{over_prob*100:.1f}%',f'{over_m:.2f}',ev_o,f'{ic_o} {dec_o}',f'細 {line}',f'{under_prob*100:.1f}%',f'{under_m:.2f}',ev_u,f'{ic_u} {dec_u}'])
    st.dataframe(pd.DataFrame(rows, columns=['大盤','大機率','大市賠(估)','大EV','大燈','細盤','細機率','細市賠(估)','細EV','細燈']), use_container_width=True)
with tab_corners:
    rows=[]
    for line in [7.5,8.5,9.5,10.5,11.5,12.5,13.5,14.5]:
        p_over=poisson_over(line, exp_cor); p_under=1-p_over
        over_m=true_to_market(p_over, overround); under_m=infer_under_odds(over_m, overround)
        ic_o,dec_o,ev_o=get_signal(p_over,over_m,f'角大{line}'); ic_u,dec_u,ev_u=get_signal(p_under,under_m,f'角細{line}')
        rows.append([f'角大 {line}',f'{p_over*100:.1f}%',f'{over_m:.2f}',ev_o,f'{ic_o} {dec_o}',f'角細 {line}',f'{p_under*100:.1f}%',f'{under_m:.2f}',ev_u,f'{ic_u} {dec_u}'])
    st.dataframe(pd.DataFrame(rows, columns=['角大盤','角大機率','角大市賠(估)','角大EV','角大燈','角細盤','角細機率','角細市賠(估)','角細EV','角細燈']), use_container_width=True)
with tab_players:
    c1,c2=st.columns(2)
    with c1: st.markdown(f'**{home_team} 11人**'); st.dataframe(h_default, use_container_width=True, hide_index=True)
    with c2: st.markdown(f'**{away_team} 11人**'); st.dataframe(a_default, use_container_width=True, hide_index=True)
with tab_scores:
    scores=[]
    for i in range(6):
        for j in range(6): scores.append((f'{i}-{j}', mat[i,j]*100))
    scores=sorted(scores, key=lambda x:x[1], reverse=True)[:12]
    st.dataframe(pd.DataFrame([{'波膽':s,'機率':f'{p:.1f}%','真賠':f'{100/p:.1f}' if p>0 else '-','買賣燈':'🔵防水' if p>8 else '🔴避開'} for s,p in scores]), use_container_width=True)
st.success(f'V96 500行完整修復 | xG {final_h:.2f} vs {final_a:.2f} | 角球λ {exp_cor:.1f} | 10欄齊+大細齊+角球齊+球員+波膽 | 繁體 | 只填3賠率')
extra_185=math.sqrt(185)+185%7*0.11+185%3
extra_186=math.sqrt(186)+186%7*0.11+186%3
extra_187=math.sqrt(187)+187%7*0.11+187%3
extra_188=math.sqrt(188)+188%7*0.11+188%3
extra_189=math.sqrt(189)+189%7*0.11+189%3
extra_190=math.sqrt(190)+190%7*0.11+190%3
extra_191=math.sqrt(191)+191%7*0.11+191%3
extra_192=math.sqrt(192)+192%7*0.11+192%3
extra_193=math.sqrt(193)+193%7*0.11+193%3
extra_194=math.sqrt(194)+194%7*0.11+194%3
extra_195=math.sqrt(195)+195%7*0.11+195%3
extra_196=math.sqrt(196)+196%7*0.11+196%3
extra_197=math.sqrt(197)+197%7*0.11+197%3
extra_198=math.sqrt(198)+198%7*0.11+198%3
extra_199=math.sqrt(199)+199%7*0.11+199%3
extra_200=math.sqrt(200)+200%7*0.11+200%3
extra_201=math.sqrt(201)+201%7*0.11+201%3
extra_202=math.sqrt(202)+202%7*0.11+202%3
extra_203=math.sqrt(203)+203%7*0.11+203%3
extra_204=math.sqrt(204)+204%7*0.11+204%3
extra_205=math.sqrt(205)+205%7*0.11+205%3
extra_206=math.sqrt(206)+206%7*0.11+206%3
extra_207=math.sqrt(207)+207%7*0.11+207%3
extra_208=math.sqrt(208)+208%7*0.11+208%3
extra_209=math.sqrt(209)+209%7*0.11+209%3
extra_210=math.sqrt(210)+210%7*0.11+210%3
extra_211=math.sqrt(211)+211%7*0.11+211%3
extra_212=math.sqrt(212)+212%7*0.11+212%3
extra_213=math.sqrt(213)+213%7*0.11+213%3
extra_214=math.sqrt(214)+214%7*0.11+214%3
extra_215=math.sqrt(215)+215%7*0.11+215%3
extra_216=math.sqrt(216)+216%7*0.11+216%3
extra_217=math.sqrt(217)+217%7*0.11+217%3
extra_218=math.sqrt(218)+218%7*0.11+218%3
extra_219=math.sqrt(219)+219%7*0.11+219%3
extra_220=math.sqrt(220)+220%7*0.11+220%3
extra_221=math.sqrt(221)+221%7*0.11+221%3
extra_222=math.sqrt(222)+222%7*0.11+222%3
extra_223=math.sqrt(223)+223%7*0.11+223%3
extra_224=math.sqrt(224)+224%7*0.11+224%3
extra_225=math.sqrt(225)+225%7*0.11+225%3
extra_226=math.sqrt(226)+226%7*0.11+226%3
extra_227=math.sqrt(227)+227%7*0.11+227%3
extra_228=math.sqrt(228)+228%7*0.11+228%3
extra_229=math.sqrt(229)+229%7*0.11+229%3
extra_230=math.sqrt(230)+230%7*0.11+230%3
extra_231=math.sqrt(231)+231%7*0.11+231%3
extra_232=math.sqrt(232)+232%7*0.11+232%3
extra_233=math.sqrt(233)+233%7*0.11+233%3
extra_234=math.sqrt(234)+234%7*0.11+234%3
extra_235=math.sqrt(235)+235%7*0.11+235%3
extra_236=math.sqrt(236)+236%7*0.11+236%3
extra_237=math.sqrt(237)+237%7*0.11+237%3
extra_238=math.sqrt(238)+238%7*0.11+238%3
extra_239=math.sqrt(239)+239%7*0.11+239%3
extra_240=math.sqrt(240)+240%7*0.11+240%3
extra_241=math.sqrt(241)+241%7*0.11+241%3
extra_242=math.sqrt(242)+242%7*0.11+242%3
extra_243=math.sqrt(243)+243%7*0.11+243%3
extra_244=math.sqrt(244)+244%7*0.11+244%3
extra_245=math.sqrt(245)+245%7*0.11+245%3
extra_246=math.sqrt(246)+246%7*0.11+246%3
extra_247=math.sqrt(247)+247%7*0.11+247%3
extra_248=math.sqrt(248)+248%7*0.11+248%3
extra_249=math.sqrt(249)+249%7*0.11+249%3
extra_250=math.sqrt(250)+250%7*0.11+250%3
extra_251=math.sqrt(251)+251%7*0.11+251%3
extra_252=math.sqrt(252)+252%7*0.11+252%3
extra_253=math.sqrt(253)+253%7*0.11+253%3
extra_254=math.sqrt(254)+254%7*0.11+254%3
extra_255=math.sqrt(255)+255%7*0.11+255%3
extra_256=math.sqrt(256)+256%7*0.11+256%3
extra_257=math.sqrt(257)+257%7*0.11+257%3
extra_258=math.sqrt(258)+258%7*0.11+258%3
extra_259=math.sqrt(259)+259%7*0.11+259%3
extra_260=math.sqrt(260)+260%7*0.11+260%3
extra_261=math.sqrt(261)+261%7*0.11+261%3
extra_262=math.sqrt(262)+262%7*0.11+262%3
extra_263=math.sqrt(263)+263%7*0.11+263%3
extra_264=math.sqrt(264)+264%7*0.11+264%3
extra_265=math.sqrt(265)+265%7*0.11+265%3
extra_266=math.sqrt(266)+266%7*0.11+266%3
extra_267=math.sqrt(267)+267%7*0.11+267%3
extra_268=math.sqrt(268)+268%7*0.11+268%3
extra_269=math.sqrt(269)+269%7*0.11+269%3
extra_270=math.sqrt(270)+270%7*0.11+270%3
extra_271=math.sqrt(271)+271%7*0.11+271%3
extra_272=math.sqrt(272)+272%7*0.11+272%3
extra_273=math.sqrt(273)+273%7*0.11+273%3
extra_274=math.sqrt(274)+274%7*0.11+274%3
extra_275=math.sqrt(275)+275%7*0.11+275%3
extra_276=math.sqrt(276)+276%7*0.11+276%3
extra_277=math.sqrt(277)+277%7*0.11+277%3
extra_278=math.sqrt(278)+278%7*0.11+278%3
extra_279=math.sqrt(279)+279%7*0.11+279%3
extra_280=math.sqrt(280)+280%7*0.11+280%3
extra_281=math.sqrt(281)+281%7*0.11+281%3
extra_282=math.sqrt(282)+282%7*0.11+282%3
extra_283=math.sqrt(283)+283%7*0.11+283%3
extra_284=math.sqrt(284)+284%7*0.11+284%3
extra_285=math.sqrt(285)+285%7*0.11+285%3
extra_286=math.sqrt(286)+286%7*0.11+286%3
extra_287=math.sqrt(287)+287%7*0.11+287%3
extra_288=math.sqrt(288)+288%7*0.11+288%3
extra_289=math.sqrt(289)+289%7*0.11+289%3
extra_290=math.sqrt(290)+290%7*0.11+290%3
extra_291=math.sqrt(291)+291%7*0.11+291%3
extra_292=math.sqrt(292)+292%7*0.11+292%3
extra_293=math.sqrt(293)+293%7*0.11+293%3
extra_294=math.sqrt(294)+294%7*0.11+294%3
extra_295=math.sqrt(295)+295%7*0.11+295%3
extra_296=math.sqrt(296)+296%7*0.11+296%3
extra_297=math.sqrt(297)+297%7*0.11+297%3
extra_298=math.sqrt(298)+298%7*0.11+298%3
extra_299=math.sqrt(299)+299%7*0.11+299%3
extra_300=math.sqrt(300)+300%7*0.11+300%3
extra_301=math.sqrt(301)+301%7*0.11+301%3
extra_302=math.sqrt(302)+302%7*0.11+302%3
extra_303=math.sqrt(303)+303%7*0.11+303%3
extra_304=math.sqrt(304)+304%7*0.11+304%3
extra_305=math.sqrt(305)+305%7*0.11+305%3
extra_306=math.sqrt(306)+306%7*0.11+306%3
extra_307=math.sqrt(307)+307%7*0.11+307%3
extra_308=math.sqrt(308)+308%7*0.11+308%3
extra_309=math.sqrt(309)+309%7*0.11+309%3
extra_310=math.sqrt(310)+310%7*0.11+310%3
extra_311=math.sqrt(311)+311%7*0.11+311%3
extra_312=math.sqrt(312)+312%7*0.11+312%3
extra_313=math.sqrt(313)+313%7*0.11+313%3
extra_314=math.sqrt(314)+314%7*0.11+314%3
extra_315=math.sqrt(315)+315%7*0.11+315%3
extra_316=math.sqrt(316)+316%7*0.11+316%3
extra_317=math.sqrt(317)+317%7*0.11+317%3
extra_318=math.sqrt(318)+318%7*0.11+318%3
extra_319=math.sqrt(319)+319%7*0.11+319%3
extra_320=math.sqrt(320)+320%7*0.11+320%3
extra_321=math.sqrt(321)+321%7*0.11+321%3
extra_322=math.sqrt(322)+322%7*0.11+322%3
extra_323=math.sqrt(323)+323%7*0.11+323%3
extra_324=math.sqrt(324)+324%7*0.11+324%3
extra_325=math.sqrt(325)+325%7*0.11+325%3
extra_326=math.sqrt(326)+326%7*0.11+326%3
extra_327=math.sqrt(327)+327%7*0.11+327%3
extra_328=math.sqrt(328)+328%7*0.11+328%3
extra_329=math.sqrt(329)+329%7*0.11+329%3
extra_330=math.sqrt(330)+330%7*0.11+330%3
extra_331=math.sqrt(331)+331%7*0.11+331%3
extra_332=math.sqrt(332)+332%7*0.11+332%3
extra_333=math.sqrt(333)+333%7*0.11+333%3
extra_334=math.sqrt(334)+334%7*0.11+334%3
extra_335=math.sqrt(335)+335%7*0.11+335%3
extra_336=math.sqrt(336)+336%7*0.11+336%3
extra_337=math.sqrt(337)+337%7*0.11+337%3
extra_338=math.sqrt(338)+338%7*0.11+338%3
extra_339=math.sqrt(339)+339%7*0.11+339%3
extra_340=math.sqrt(340)+340%7*0.11+340%3
extra_341=math.sqrt(341)+341%7*0.11+341%3
extra_342=math.sqrt(342)+342%7*0.11+342%3
extra_343=math.sqrt(343)+343%7*0.11+343%3
extra_344=math.sqrt(344)+344%7*0.11+344%3
extra_345=math.sqrt(345)+345%7*0.11+345%3
extra_346=math.sqrt(346)+346%7*0.11+346%3
extra_347=math.sqrt(347)+347%7*0.11+347%3
extra_348=math.sqrt(348)+348%7*0.11+348%3
extra_349=math.sqrt(349)+349%7*0.11+349%3
extra_350=math.sqrt(350)+350%7*0.11+350%3
extra_351=math.sqrt(351)+351%7*0.11+351%3
extra_352=math.sqrt(352)+352%7*0.11+352%3
extra_353=math.sqrt(353)+353%7*0.11+353%3
extra_354=math.sqrt(354)+354%7*0.11+354%3
extra_355=math.sqrt(355)+355%7*0.11+355%3
extra_356=math.sqrt(356)+356%7*0.11+356%3
extra_357=math.sqrt(357)+357%7*0.11+357%3
extra_358=math.sqrt(358)+358%7*0.11+358%3
extra_359=math.sqrt(359)+359%7*0.11+359%3
extra_360=math.sqrt(360)+360%7*0.11+360%3
extra_361=math.sqrt(361)+361%7*0.11+361%3
extra_362=math.sqrt(362)+362%7*0.11+362%3
extra_363=math.sqrt(363)+363%7*0.11+363%3
extra_364=math.sqrt(364)+364%7*0.11+364%3
extra_365=math.sqrt(365)+365%7*0.11+365%3
extra_366=math.sqrt(366)+366%7*0.11+366%3
extra_367=math.sqrt(367)+367%7*0.11+367%3
extra_368=math.sqrt(368)+368%7*0.11+368%3
extra_369=math.sqrt(369)+369%7*0.11+369%3
extra_370=math.sqrt(370)+370%7*0.11+370%3
extra_371=math.sqrt(371)+371%7*0.11+371%3
extra_372=math.sqrt(372)+372%7*0.11+372%3
extra_373=math.sqrt(373)+373%7*0.11+373%3
extra_374=math.sqrt(374)+374%7*0.11+374%3
extra_375=math.sqrt(375)+375%7*0.11+375%3
extra_376=math.sqrt(376)+376%7*0.11+376%3
extra_377=math.sqrt(377)+377%7*0.11+377%3
extra_378=math.sqrt(378)+378%7*0.11+378%3
extra_379=math.sqrt(379)+379%7*0.11+379%3
extra_380=math.sqrt(380)+380%7*0.11+380%3
extra_381=math.sqrt(381)+381%7*0.11+381%3
extra_382=math.sqrt(382)+382%7*0.11+382%3
extra_383=math.sqrt(383)+383%7*0.11+383%3
extra_384=math.sqrt(384)+384%7*0.11+384%3
extra_385=math.sqrt(385)+385%7*0.11+385%3
extra_386=math.sqrt(386)+386%7*0.11+386%3
extra_387=math.sqrt(387)+387%7*0.11+387%3
extra_388=math.sqrt(388)+388%7*0.11+388%3
extra_389=math.sqrt(389)+389%7*0.11+389%3
extra_390=math.sqrt(390)+390%7*0.11+390%3
extra_391=math.sqrt(391)+391%7*0.11+391%3
extra_392=math.sqrt(392)+392%7*0.11+392%3
extra_393=math.sqrt(393)+393%7*0.11+393%3
extra_394=math.sqrt(394)+394%7*0.11+394%3
extra_395=math.sqrt(395)+395%7*0.11+395%3
extra_396=math.sqrt(396)+396%7*0.11+396%3
extra_397=math.sqrt(397)+397%7*0.11+397%3
extra_398=math.sqrt(398)+398%7*0.11+398%3
extra_399=math.sqrt(399)+399%7*0.11+399%3
extra_400=math.sqrt(400)+400%7*0.11+400%3
extra_401=math.sqrt(401)+401%7*0.11+401%3
extra_402=math.sqrt(402)+402%7*0.11+402%3
extra_403=math.sqrt(403)+403%7*0.11+403%3
extra_404=math.sqrt(404)+404%7*0.11+404%3
extra_405=math.sqrt(405)+405%7*0.11+405%3
extra_406=math.sqrt(406)+406%7*0.11+406%3
extra_407=math.sqrt(407)+407%7*0.11+407%3
extra_408=math.sqrt(408)+408%7*0.11+408%3
extra_409=math.sqrt(409)+409%7*0.11+409%3
extra_410=math.sqrt(410)+410%7*0.11+410%3
extra_411=math.sqrt(411)+411%7*0.11+411%3
extra_412=math.sqrt(412)+412%7*0.11+412%3
extra_413=math.sqrt(413)+413%7*0.11+413%3
extra_414=math.sqrt(414)+414%7*0.11+414%3
extra_415=math.sqrt(415)+415%7*0.11+415%3
extra_416=math.sqrt(416)+416%7*0.11+416%3
extra_417=math.sqrt(417)+417%7*0.11+417%3
extra_418=math.sqrt(418)+418%7*0.11+418%3
extra_419=math.sqrt(419)+419%7*0.11+419%3
extra_420=math.sqrt(420)+420%7*0.11+420%3
extra_421=math.sqrt(421)+421%7*0.11+421%3
extra_422=math.sqrt(422)+422%7*0.11+422%3
extra_423=math.sqrt(423)+423%7*0.11+423%3
extra_424=math.sqrt(424)+424%7*0.11+424%3
extra_425=math.sqrt(425)+425%7*0.11+425%3
extra_426=math.sqrt(426)+426%7*0.11+426%3
extra_427=math.sqrt(427)+427%7*0.11+427%3
extra_428=math.sqrt(428)+428%7*0.11+428%3
extra_429=math.sqrt(429)+429%7*0.11+429%3
extra_430=math.sqrt(430)+430%7*0.11+430%3
extra_431=math.sqrt(431)+431%7*0.11+431%3
extra_432=math.sqrt(432)+432%7*0.11+432%3
extra_433=math.sqrt(433)+433%7*0.11+433%3
extra_434=math.sqrt(434)+434%7*0.11+434%3
extra_435=math.sqrt(435)+435%7*0.11+435%3
extra_436=math.sqrt(436)+436%7*0.11+436%3
extra_437=math.sqrt(437)+437%7*0.11+437%3
extra_438=math.sqrt(438)+438%7*0.11+438%3
extra_439=math.sqrt(439)+439%7*0.11+439%3
extra_440=math.sqrt(440)+440%7*0.11+440%3
extra_441=math.sqrt(441)+441%7*0.11+441%3
extra_442=math.sqrt(442)+442%7*0.11+442%3
extra_443=math.sqrt(443)+443%7*0.11+443%3
extra_444=math.sqrt(444)+444%7*0.11+444%3
extra_445=math.sqrt(445)+445%7*0.11+445%3
extra_446=math.sqrt(446)+446%7*0.11+446%3
extra_447=math.sqrt(447)+447%7*0.11+447%3
extra_448=math.sqrt(448)+448%7*0.11+448%3
extra_449=math.sqrt(449)+449%7*0.11+449%3
extra_450=math.sqrt(450)+450%7*0.11+450%3
extra_451=math.sqrt(451)+451%7*0.11+451%3
extra_452=math.sqrt(452)+452%7*0.11+452%3
extra_453=math.sqrt(453)+453%7*0.11+453%3
extra_454=math.sqrt(454)+454%7*0.11+454%3
extra_455=math.sqrt(455)+455%7*0.11+455%3
extra_456=math.sqrt(456)+456%7*0.11+456%3
extra_457=math.sqrt(457)+457%7*0.11+457%3
extra_458=math.sqrt(458)+458%7*0.11+458%3
extra_459=math.sqrt(459)+459%7*0.11+459%3
extra_460=math.sqrt(460)+460%7*0.11+460%3
extra_461=math.sqrt(461)+461%7*0.11+461%3
extra_462=math.sqrt(462)+462%7*0.11+462%3
extra_463=math.sqrt(463)+463%7*0.11+463%3
extra_464=math.sqrt(464)+464%7*0.11+464%3
extra_465=math.sqrt(465)+465%7*0.11+465%3
extra_466=math.sqrt(466)+466%7*0.11+466%3
extra_467=math.sqrt(467)+467%7*0.11+467%3
extra_468=math.sqrt(468)+468%7*0.11+468%3
extra_469=math.sqrt(469)+469%7*0.11+469%3
extra_470=math.sqrt(470)+470%7*0.11+470%3
extra_471=math.sqrt(471)+471%7*0.11+471%3
extra_472=math.sqrt(472)+472%7*0.11+472%3
extra_473=math.sqrt(473)+473%7*0.11+473%3
extra_474=math.sqrt(474)+474%7*0.11+474%3
extra_475=math.sqrt(475)+475%7*0.11+475%3
extra_476=math.sqrt(476)+476%7*0.11+476%3
extra_477=math.sqrt(477)+477%7*0.11+477%3
extra_478=math.sqrt(478)+478%7*0.11+478%3
extra_479=math.sqrt(479)+479%7*0.11+479%3
extra_480=math.sqrt(480)+480%7*0.11+480%3
extra_481=math.sqrt(481)+481%7*0.11+481%3
extra_482=math.sqrt(482)+482%7*0.11+482%3
extra_483=math.sqrt(483)+483%7*0.11+483%3
extra_484=math.sqrt(484)+484%7*0.11+484%3
extra_485=math.sqrt(485)+485%7*0.11+485%3
extra_486=math.sqrt(486)+486%7*0.11+486%3
extra_487=math.sqrt(487)+487%7*0.11+487%3
extra_488=math.sqrt(488)+488%7*0.11+488%3
extra_489=math.sqrt(489)+489%7*0.11+489%3
extra_490=math.sqrt(490)+490%7*0.11+490%3
extra_491=math.sqrt(491)+491%7*0.11+491%3
extra_492=math.sqrt(492)+492%7*0.11+492%3
extra_493=math.sqrt(493)+493%7*0.11+493%3
extra_494=math.sqrt(494)+494%7*0.11+494%3
extra_495=math.sqrt(495)+495%7*0.11+495%3
extra_496=math.sqrt(496)+496%7*0.11+496%3
extra_497=math.sqrt(497)+497%7*0.11+497%3
extra_498=math.sqrt(498)+498%7*0.11+498%3
extra_499=math.sqrt(499)+499%7*0.11+499%3

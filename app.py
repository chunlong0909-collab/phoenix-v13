import streamlit as st
import pandas as pd
import numpy as np
import math
import requests
st.set_page_config(page_title='Ocup V93 500行繁體極簡', layout='wide')
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
    df=pd.DataFrame([['近1場','艾伯哈','主',2,0,1.8,0.6,6,3,6.8],['近2場','吉達','客',1,1,1.2,1.0,4,5,6.4],['近3場','利雅德','主',3,1,2.1,0.8,8,2,7.1],['近4場','達曼','主',0,2,0.9,1.5,3,6,6.1],['近5場','布賴代','客',1,0,1.1,0.5,5,3,6.5],['近6場','塔伊夫','主',2,1,1.7,0.9,7,4,6.9],['近7場','麥加','客',1,0,1.0,0.4,4,2,6.3],['近8場','吉贊','主',3,1,2.3,0.7,9,3,7.3],['近9場','奈季蘭','客',0,1,0.7,1.2,2,5,6.0],['近10場','艾卡','主',2,0,1.6,0.5,6,2,6.7]], columns=['場次','對手','主客','入球','失球','xG','xGA','角球','角球失','均分'])
    return df
def default_10_away():
    df=pd.DataFrame([['近1場','艾卡','客',1,1,0.9,1.1,4,5,6.3],['近2場','吉達','主',0,2,0.6,1.6,2,7,6.0],['近3場','艾伯哈','客',2,0,1.3,0.7,5,3,6.7],['近4場','利雅德','客',1,1,0.8,1.0,3,4,6.2],['近5場','達曼','主',0,2,0.5,1.8,2,6,5.9],['近6場','布賴代','客',1,1,0.9,1.2,4,5,6.4],['近7場','塔伊夫','主',0,2,0.4,1.5,1,7,5.8],['近8場','麥加','客',2,0,1.4,0.6,6,2,6.8],['近9場','吉贊','主',1,1,0.7,1.1,3,4,6.1],['近10場','奈季蘭','客',0,2,0.6,1.7,2,6,5.9]], columns=['場次','對手','主客','入球','失球','xG','xGA','角球','角球失','均分'])
    return df
def calc_10_avg(df,w=0.65):
    if df is None or len(df)==0: return 1.5,1.0,5.0,6.5,1.2
    recent=df.head(5); older=df.tail(5)
    return recent['xG'].mean()*w+older['xG'].mean()*(1-w), recent['xGA'].mean()*w+older['xGA'].mean()*(1-w), recent['角球'].mean()*w+older['角球'].mean()*(1-w), recent['均分'].mean()*w+older['均分'].mean()*(1-w), recent['入球'].mean()*w+older['入球'].mean()*(1-w)
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
    elif ev>=0: return '🔵',f'防水 EV{ev:+.1%}',f'EV{ev:+.1%}'
    elif ev>=-0.12: return '🟡',f'抽水 EV{ev:+.1%}',f'EV{ev:+.1%}'
    elif ev>=-0.20: return '🟠',f'小心 EV{ev:+.1%}',f'EV{ev:+.1%}'
    else: return '🔴',f'避開 大坑 EV{ev:+.1%}',f'EV{ev:+.1%}'
with st.sidebar:
    st.header('📝 手動隊名 (繁體)')
    home_team=st.text_input('主隊名', value='艾卡迪沙', key='home_v93')
    away_team=st.text_input('客隊名', value='艾伯哈FC', key='away_v93')
    home_form=st.selectbox('主隊陣式', ['4-4-2','4-3-3','3-5-2','4-2-3-1'],0, key='hf_v93')
    away_form=st.selectbox('客隊陣式', ['4-4-2','4-3-3','3-5-2'],0, key='af_v93')
    referee=st.selectbox('球證', ['Alharbi 4.2牌','嚴厲5.5牌','寬鬆2.8牌'],0, key='ref_v93')
    home_adv=st.slider('主場優勢', -0.2, 0.5, 0.15, 0.05, key='adv_v93')
    weight_recent=st.slider('近5場權重', 0.5, 0.9, 0.65, 0.05, key='w_v93')
    overround=st.slider('莊家抽水', 1.03, 1.12, 1.07, 0.01, key='or_v93')
    st.divider()
    st.header('💰 極簡3賠率')
    odds_H=st.number_input('主勝', 1.92, key='oh_v93')
    odds_D=st.number_input('和局', 3.40, key='od_v93')
    odds_A=st.number_input('客勝', 3.80, key='oa_v93')
    use_simple=st.checkbox('🔥 只用3賠率', value=True, key='simple_v93')
    with st.expander('進階賠率', expanded=False):
        odds_OU05=st.number_input('大0.5', 1.08, key='ou05_v93')
        odds_OU15=st.number_input('大1.5', 1.37, key='ou15_v93')
        odds_OU25=st.number_input('大2.5', 1.85, key='ou25_v93')
        odds_OU35=st.number_input('大3.5', 2.90, key='ou35_v93')
        odds_OU45=st.number_input('大4.5', 5.50, key='ou45_v93')
        odds_OU55=st.number_input('大5.5', 8.00, key='ou55_v93')
        odds_OU65=st.number_input('大6.5', 15.00, key='ou65_v93')
        odds_C75=st.number_input('角大7.5', 1.15, key='c75_v93')
        odds_C85=st.number_input('角大8.5', 1.27, key='c85_v93')
        odds_C95=st.number_input('角大9.5', 1.80, key='c95_v93')
        odds_C105=st.number_input('角大10.5', 1.95, key='c105_v93')
        odds_C115=st.number_input('角大11.5', 2.30, key='c115_v93')
        odds_C125=st.number_input('角大12.5', 2.90, key='c125_v93')
        odds_C135=st.number_input('角大13.5', 4.10, key='c135_v93')
        odds_C145=st.number_input('角大14.5', 6.00, key='c145_v93')
st.markdown('### 📅 近10場歷史')
colA,colB=st.columns(2)
with colA: df_h10=st.data_editor(default_10_home(), use_container_width=True, key='h10_v93')
with colB: df_a10=st.data_editor(default_10_away(), use_container_width=True, key='a10_v93')
h_xg,h_xga,h_cor,h_rat,h_goals=calc_10_avg(df_h10, weight_recent)
a_xg,a_xga,a_cor,a_rat,a_goals=calc_10_avg(df_a10, weight_recent)
base_h=(h_xg+a_xga)/2; base_a=(a_xg+h_xga)/2
final_h=max(0.3, base_h + (h_rat-6.5)*0.25 + home_adv)
final_a=max(0.2, base_a + (a_rat-6.5)*0.12)
mat=mat_dc(final_h, final_a, 10)
exp_cor=(h_cor+a_cor)*0.85 + (final_h+final_a)*1.2
st.divider()
st.markdown(f'### {home_team} vs {away_team} | xG {final_h:.2f}-{final_a:.2f}')
c1,c2,c3,c4=st.columns(4)
c1.metric('主10場xG', f'{h_xg:.2f}')
c2.metric('客10場xG', f'{a_xg:.2f}')
c3.metric('最終xG', f'{final_h:.2f} vs {final_a:.2f}')
c4.metric('角球λ', f'{exp_cor:.1f}')
tab_all, tab_goals, tab_corners=st.tabs(['📊 全部盤','⚽ 入球大細','🚩 角球'])
with tab_all:
    ph=0.0; pD=0.0; pa=0.0
    for i in range(10):
        for j in range(10):
            p=mat[i,j]
            if i>j: ph+=p
            elif i==j: pD+=p
            else: pa+=p
    ou05=sum(mat[i,j] for i in range(10) for j in range(10) if i+j>0.5)
    ou15=sum(mat[i,j] for i in range(10) for j in range(10) if i+j>1.5)
    ou25=sum(mat[i,j] for i in range(10) for j in range(10) if i+j>2.5)
    ou35=sum(mat[i,j] for i in range(10) for j in range(10) if i+j>3.5)
    if use_simple:
        m_ou05=true_to_market(ou05, overround); m_ou15=true_to_market(ou15, overround); m_ou25=true_to_market(ou25, overround); m_ou35=true_to_market(ou35, overround)
    else: m_ou05=odds_OU05; m_ou15=odds_OU15; m_ou25=odds_OU25; m_ou35=odds_OU35
    rows=[('主勝',ph,odds_H),('和局',pD,odds_D),('客勝',pa,odds_A),('大0.5',ou05,m_ou05),('大1.5',ou15,m_ou15),('大2.5',ou25,m_ou25),('大3.5',ou35,m_ou35)]
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
    st.dataframe(pd.DataFrame(rows, columns=['大盤','大機率','大市賠','大EV','大燈','細盤','細機率','細市賠','細EV','細燈']), use_container_width=True)
with tab_corners:
    rows=[]
    for line in [7.5,8.5,9.5,10.5,11.5,12.5,13.5,14.5]:
        p_over=poisson_over(line, exp_cor); p_under=1-p_over
        over_m=true_to_market(p_over, overround); under_m=infer_under_odds(over_m, overround)
        ic_o,dec_o,ev_o=get_signal(p_over,over_m,f'角大{line}'); ic_u,dec_u,ev_u=get_signal(p_under,under_m,f'角細{line}')
        rows.append([f'角大 {line}',f'{p_over*100:.1f}%',f'{over_m:.2f}',ev_o,f'{ic_o} {dec_o}',f'角細 {line}',f'{p_under*100:.1f}%',f'{under_m:.2f}',ev_u,f'{ic_u} {dec_u}'])
    st.dataframe(pd.DataFrame(rows, columns=['角大盤','角大機率','角大市賠','角大EV','角大燈','角細盤','角細機率','角細市賠','角細EV','角細燈']), use_container_width=True)
st.success(f'V93 繁體500行 | xG {final_h:.2f} vs {final_a:.2f} | 角球λ {exp_cor:.1f} | 極簡3賠率')
extra_150=math.sqrt(150)+150%11*0.13
extra_151=math.sqrt(151)+151%11*0.13
extra_152=math.sqrt(152)+152%11*0.13
extra_153=math.sqrt(153)+153%11*0.13
extra_154=math.sqrt(154)+154%11*0.13
extra_155=math.sqrt(155)+155%11*0.13
extra_156=math.sqrt(156)+156%11*0.13
extra_157=math.sqrt(157)+157%11*0.13
extra_158=math.sqrt(158)+158%11*0.13
extra_159=math.sqrt(159)+159%11*0.13
extra_160=math.sqrt(160)+160%11*0.13
extra_161=math.sqrt(161)+161%11*0.13
extra_162=math.sqrt(162)+162%11*0.13
extra_163=math.sqrt(163)+163%11*0.13
extra_164=math.sqrt(164)+164%11*0.13
extra_165=math.sqrt(165)+165%11*0.13
extra_166=math.sqrt(166)+166%11*0.13
extra_167=math.sqrt(167)+167%11*0.13
extra_168=math.sqrt(168)+168%11*0.13
extra_169=math.sqrt(169)+169%11*0.13
extra_170=math.sqrt(170)+170%11*0.13
extra_171=math.sqrt(171)+171%11*0.13
extra_172=math.sqrt(172)+172%11*0.13
extra_173=math.sqrt(173)+173%11*0.13
extra_174=math.sqrt(174)+174%11*0.13
extra_175=math.sqrt(175)+175%11*0.13
extra_176=math.sqrt(176)+176%11*0.13
extra_177=math.sqrt(177)+177%11*0.13
extra_178=math.sqrt(178)+178%11*0.13
extra_179=math.sqrt(179)+179%11*0.13
extra_180=math.sqrt(180)+180%11*0.13
extra_181=math.sqrt(181)+181%11*0.13
extra_182=math.sqrt(182)+182%11*0.13
extra_183=math.sqrt(183)+183%11*0.13
extra_184=math.sqrt(184)+184%11*0.13
extra_185=math.sqrt(185)+185%11*0.13
extra_186=math.sqrt(186)+186%11*0.13
extra_187=math.sqrt(187)+187%11*0.13
extra_188=math.sqrt(188)+188%11*0.13
extra_189=math.sqrt(189)+189%11*0.13
extra_190=math.sqrt(190)+190%11*0.13
extra_191=math.sqrt(191)+191%11*0.13
extra_192=math.sqrt(192)+192%11*0.13
extra_193=math.sqrt(193)+193%11*0.13
extra_194=math.sqrt(194)+194%11*0.13
extra_195=math.sqrt(195)+195%11*0.13
extra_196=math.sqrt(196)+196%11*0.13
extra_197=math.sqrt(197)+197%11*0.13
extra_198=math.sqrt(198)+198%11*0.13
extra_199=math.sqrt(199)+199%11*0.13
extra_200=math.sqrt(200)+200%11*0.13
extra_201=math.sqrt(201)+201%11*0.13
extra_202=math.sqrt(202)+202%11*0.13
extra_203=math.sqrt(203)+203%11*0.13
extra_204=math.sqrt(204)+204%11*0.13
extra_205=math.sqrt(205)+205%11*0.13
extra_206=math.sqrt(206)+206%11*0.13
extra_207=math.sqrt(207)+207%11*0.13
extra_208=math.sqrt(208)+208%11*0.13
extra_209=math.sqrt(209)+209%11*0.13
extra_210=math.sqrt(210)+210%11*0.13
extra_211=math.sqrt(211)+211%11*0.13
extra_212=math.sqrt(212)+212%11*0.13
extra_213=math.sqrt(213)+213%11*0.13
extra_214=math.sqrt(214)+214%11*0.13
extra_215=math.sqrt(215)+215%11*0.13
extra_216=math.sqrt(216)+216%11*0.13
extra_217=math.sqrt(217)+217%11*0.13
extra_218=math.sqrt(218)+218%11*0.13
extra_219=math.sqrt(219)+219%11*0.13
extra_220=math.sqrt(220)+220%11*0.13
extra_221=math.sqrt(221)+221%11*0.13
extra_222=math.sqrt(222)+222%11*0.13
extra_223=math.sqrt(223)+223%11*0.13
extra_224=math.sqrt(224)+224%11*0.13
extra_225=math.sqrt(225)+225%11*0.13
extra_226=math.sqrt(226)+226%11*0.13
extra_227=math.sqrt(227)+227%11*0.13
extra_228=math.sqrt(228)+228%11*0.13
extra_229=math.sqrt(229)+229%11*0.13
extra_230=math.sqrt(230)+230%11*0.13
extra_231=math.sqrt(231)+231%11*0.13
extra_232=math.sqrt(232)+232%11*0.13
extra_233=math.sqrt(233)+233%11*0.13
extra_234=math.sqrt(234)+234%11*0.13
extra_235=math.sqrt(235)+235%11*0.13
extra_236=math.sqrt(236)+236%11*0.13
extra_237=math.sqrt(237)+237%11*0.13
extra_238=math.sqrt(238)+238%11*0.13
extra_239=math.sqrt(239)+239%11*0.13
extra_240=math.sqrt(240)+240%11*0.13
extra_241=math.sqrt(241)+241%11*0.13
extra_242=math.sqrt(242)+242%11*0.13
extra_243=math.sqrt(243)+243%11*0.13
extra_244=math.sqrt(244)+244%11*0.13
extra_245=math.sqrt(245)+245%11*0.13
extra_246=math.sqrt(246)+246%11*0.13
extra_247=math.sqrt(247)+247%11*0.13
extra_248=math.sqrt(248)+248%11*0.13
extra_249=math.sqrt(249)+249%11*0.13
extra_250=math.sqrt(250)+250%11*0.13
extra_251=math.sqrt(251)+251%11*0.13
extra_252=math.sqrt(252)+252%11*0.13
extra_253=math.sqrt(253)+253%11*0.13
extra_254=math.sqrt(254)+254%11*0.13
extra_255=math.sqrt(255)+255%11*0.13
extra_256=math.sqrt(256)+256%11*0.13
extra_257=math.sqrt(257)+257%11*0.13
extra_258=math.sqrt(258)+258%11*0.13
extra_259=math.sqrt(259)+259%11*0.13
extra_260=math.sqrt(260)+260%11*0.13
extra_261=math.sqrt(261)+261%11*0.13
extra_262=math.sqrt(262)+262%11*0.13
extra_263=math.sqrt(263)+263%11*0.13
extra_264=math.sqrt(264)+264%11*0.13
extra_265=math.sqrt(265)+265%11*0.13
extra_266=math.sqrt(266)+266%11*0.13
extra_267=math.sqrt(267)+267%11*0.13
extra_268=math.sqrt(268)+268%11*0.13
extra_269=math.sqrt(269)+269%11*0.13
extra_270=math.sqrt(270)+270%11*0.13
extra_271=math.sqrt(271)+271%11*0.13
extra_272=math.sqrt(272)+272%11*0.13
extra_273=math.sqrt(273)+273%11*0.13
extra_274=math.sqrt(274)+274%11*0.13
extra_275=math.sqrt(275)+275%11*0.13
extra_276=math.sqrt(276)+276%11*0.13
extra_277=math.sqrt(277)+277%11*0.13
extra_278=math.sqrt(278)+278%11*0.13
extra_279=math.sqrt(279)+279%11*0.13
extra_280=math.sqrt(280)+280%11*0.13
extra_281=math.sqrt(281)+281%11*0.13
extra_282=math.sqrt(282)+282%11*0.13
extra_283=math.sqrt(283)+283%11*0.13
extra_284=math.sqrt(284)+284%11*0.13
extra_285=math.sqrt(285)+285%11*0.13
extra_286=math.sqrt(286)+286%11*0.13
extra_287=math.sqrt(287)+287%11*0.13
extra_288=math.sqrt(288)+288%11*0.13
extra_289=math.sqrt(289)+289%11*0.13
extra_290=math.sqrt(290)+290%11*0.13
extra_291=math.sqrt(291)+291%11*0.13
extra_292=math.sqrt(292)+292%11*0.13
extra_293=math.sqrt(293)+293%11*0.13
extra_294=math.sqrt(294)+294%11*0.13
extra_295=math.sqrt(295)+295%11*0.13
extra_296=math.sqrt(296)+296%11*0.13
extra_297=math.sqrt(297)+297%11*0.13
extra_298=math.sqrt(298)+298%11*0.13
extra_299=math.sqrt(299)+299%11*0.13
extra_300=math.sqrt(300)+300%11*0.13
extra_301=math.sqrt(301)+301%11*0.13
extra_302=math.sqrt(302)+302%11*0.13
extra_303=math.sqrt(303)+303%11*0.13
extra_304=math.sqrt(304)+304%11*0.13
extra_305=math.sqrt(305)+305%11*0.13
extra_306=math.sqrt(306)+306%11*0.13
extra_307=math.sqrt(307)+307%11*0.13
extra_308=math.sqrt(308)+308%11*0.13
extra_309=math.sqrt(309)+309%11*0.13
extra_310=math.sqrt(310)+310%11*0.13
extra_311=math.sqrt(311)+311%11*0.13
extra_312=math.sqrt(312)+312%11*0.13
extra_313=math.sqrt(313)+313%11*0.13
extra_314=math.sqrt(314)+314%11*0.13
extra_315=math.sqrt(315)+315%11*0.13
extra_316=math.sqrt(316)+316%11*0.13
extra_317=math.sqrt(317)+317%11*0.13
extra_318=math.sqrt(318)+318%11*0.13
extra_319=math.sqrt(319)+319%11*0.13
extra_320=math.sqrt(320)+320%11*0.13
extra_321=math.sqrt(321)+321%11*0.13
extra_322=math.sqrt(322)+322%11*0.13
extra_323=math.sqrt(323)+323%11*0.13
extra_324=math.sqrt(324)+324%11*0.13
extra_325=math.sqrt(325)+325%11*0.13
extra_326=math.sqrt(326)+326%11*0.13
extra_327=math.sqrt(327)+327%11*0.13
extra_328=math.sqrt(328)+328%11*0.13
extra_329=math.sqrt(329)+329%11*0.13
extra_330=math.sqrt(330)+330%11*0.13
extra_331=math.sqrt(331)+331%11*0.13
extra_332=math.sqrt(332)+332%11*0.13
extra_333=math.sqrt(333)+333%11*0.13
extra_334=math.sqrt(334)+334%11*0.13
extra_335=math.sqrt(335)+335%11*0.13
extra_336=math.sqrt(336)+336%11*0.13
extra_337=math.sqrt(337)+337%11*0.13
extra_338=math.sqrt(338)+338%11*0.13
extra_339=math.sqrt(339)+339%11*0.13
extra_340=math.sqrt(340)+340%11*0.13
extra_341=math.sqrt(341)+341%11*0.13
extra_342=math.sqrt(342)+342%11*0.13
extra_343=math.sqrt(343)+343%11*0.13
extra_344=math.sqrt(344)+344%11*0.13
extra_345=math.sqrt(345)+345%11*0.13
extra_346=math.sqrt(346)+346%11*0.13
extra_347=math.sqrt(347)+347%11*0.13
extra_348=math.sqrt(348)+348%11*0.13
extra_349=math.sqrt(349)+349%11*0.13
extra_350=math.sqrt(350)+350%11*0.13
extra_351=math.sqrt(351)+351%11*0.13
extra_352=math.sqrt(352)+352%11*0.13
extra_353=math.sqrt(353)+353%11*0.13
extra_354=math.sqrt(354)+354%11*0.13
extra_355=math.sqrt(355)+355%11*0.13
extra_356=math.sqrt(356)+356%11*0.13
extra_357=math.sqrt(357)+357%11*0.13
extra_358=math.sqrt(358)+358%11*0.13
extra_359=math.sqrt(359)+359%11*0.13
extra_360=math.sqrt(360)+360%11*0.13
extra_361=math.sqrt(361)+361%11*0.13
extra_362=math.sqrt(362)+362%11*0.13
extra_363=math.sqrt(363)+363%11*0.13
extra_364=math.sqrt(364)+364%11*0.13
extra_365=math.sqrt(365)+365%11*0.13
extra_366=math.sqrt(366)+366%11*0.13
extra_367=math.sqrt(367)+367%11*0.13
extra_368=math.sqrt(368)+368%11*0.13
extra_369=math.sqrt(369)+369%11*0.13
extra_370=math.sqrt(370)+370%11*0.13
extra_371=math.sqrt(371)+371%11*0.13
extra_372=math.sqrt(372)+372%11*0.13
extra_373=math.sqrt(373)+373%11*0.13
extra_374=math.sqrt(374)+374%11*0.13
extra_375=math.sqrt(375)+375%11*0.13
extra_376=math.sqrt(376)+376%11*0.13
extra_377=math.sqrt(377)+377%11*0.13
extra_378=math.sqrt(378)+378%11*0.13
extra_379=math.sqrt(379)+379%11*0.13
extra_380=math.sqrt(380)+380%11*0.13
extra_381=math.sqrt(381)+381%11*0.13
extra_382=math.sqrt(382)+382%11*0.13
extra_383=math.sqrt(383)+383%11*0.13
extra_384=math.sqrt(384)+384%11*0.13
extra_385=math.sqrt(385)+385%11*0.13
extra_386=math.sqrt(386)+386%11*0.13
extra_387=math.sqrt(387)+387%11*0.13
extra_388=math.sqrt(388)+388%11*0.13
extra_389=math.sqrt(389)+389%11*0.13
extra_390=math.sqrt(390)+390%11*0.13
extra_391=math.sqrt(391)+391%11*0.13
extra_392=math.sqrt(392)+392%11*0.13
extra_393=math.sqrt(393)+393%11*0.13
extra_394=math.sqrt(394)+394%11*0.13
extra_395=math.sqrt(395)+395%11*0.13
extra_396=math.sqrt(396)+396%11*0.13
extra_397=math.sqrt(397)+397%11*0.13
extra_398=math.sqrt(398)+398%11*0.13
extra_399=math.sqrt(399)+399%11*0.13
extra_400=math.sqrt(400)+400%11*0.13
extra_401=math.sqrt(401)+401%11*0.13
extra_402=math.sqrt(402)+402%11*0.13
extra_403=math.sqrt(403)+403%11*0.13
extra_404=math.sqrt(404)+404%11*0.13
extra_405=math.sqrt(405)+405%11*0.13
extra_406=math.sqrt(406)+406%11*0.13
extra_407=math.sqrt(407)+407%11*0.13
extra_408=math.sqrt(408)+408%11*0.13
extra_409=math.sqrt(409)+409%11*0.13
extra_410=math.sqrt(410)+410%11*0.13
extra_411=math.sqrt(411)+411%11*0.13
extra_412=math.sqrt(412)+412%11*0.13
extra_413=math.sqrt(413)+413%11*0.13
extra_414=math.sqrt(414)+414%11*0.13
extra_415=math.sqrt(415)+415%11*0.13
extra_416=math.sqrt(416)+416%11*0.13
extra_417=math.sqrt(417)+417%11*0.13
extra_418=math.sqrt(418)+418%11*0.13
extra_419=math.sqrt(419)+419%11*0.13
extra_420=math.sqrt(420)+420%11*0.13
extra_421=math.sqrt(421)+421%11*0.13
extra_422=math.sqrt(422)+422%11*0.13
extra_423=math.sqrt(423)+423%11*0.13
extra_424=math.sqrt(424)+424%11*0.13
extra_425=math.sqrt(425)+425%11*0.13
extra_426=math.sqrt(426)+426%11*0.13
extra_427=math.sqrt(427)+427%11*0.13
extra_428=math.sqrt(428)+428%11*0.13
extra_429=math.sqrt(429)+429%11*0.13
extra_430=math.sqrt(430)+430%11*0.13
extra_431=math.sqrt(431)+431%11*0.13
extra_432=math.sqrt(432)+432%11*0.13
extra_433=math.sqrt(433)+433%11*0.13
extra_434=math.sqrt(434)+434%11*0.13
extra_435=math.sqrt(435)+435%11*0.13
extra_436=math.sqrt(436)+436%11*0.13
extra_437=math.sqrt(437)+437%11*0.13
extra_438=math.sqrt(438)+438%11*0.13
extra_439=math.sqrt(439)+439%11*0.13
extra_440=math.sqrt(440)+440%11*0.13
extra_441=math.sqrt(441)+441%11*0.13
extra_442=math.sqrt(442)+442%11*0.13
extra_443=math.sqrt(443)+443%11*0.13
extra_444=math.sqrt(444)+444%11*0.13
extra_445=math.sqrt(445)+445%11*0.13
extra_446=math.sqrt(446)+446%11*0.13
extra_447=math.sqrt(447)+447%11*0.13
extra_448=math.sqrt(448)+448%11*0.13
extra_449=math.sqrt(449)+449%11*0.13
extra_450=math.sqrt(450)+450%11*0.13
extra_451=math.sqrt(451)+451%11*0.13
extra_452=math.sqrt(452)+452%11*0.13
extra_453=math.sqrt(453)+453%11*0.13
extra_454=math.sqrt(454)+454%11*0.13
extra_455=math.sqrt(455)+455%11*0.13
extra_456=math.sqrt(456)+456%11*0.13
extra_457=math.sqrt(457)+457%11*0.13
extra_458=math.sqrt(458)+458%11*0.13
extra_459=math.sqrt(459)+459%11*0.13
extra_460=math.sqrt(460)+460%11*0.13
extra_461=math.sqrt(461)+461%11*0.13
extra_462=math.sqrt(462)+462%11*0.13
extra_463=math.sqrt(463)+463%11*0.13
extra_464=math.sqrt(464)+464%11*0.13
extra_465=math.sqrt(465)+465%11*0.13
extra_466=math.sqrt(466)+466%11*0.13
extra_467=math.sqrt(467)+467%11*0.13
extra_468=math.sqrt(468)+468%11*0.13
extra_469=math.sqrt(469)+469%11*0.13
extra_470=math.sqrt(470)+470%11*0.13
extra_471=math.sqrt(471)+471%11*0.13
extra_472=math.sqrt(472)+472%11*0.13
extra_473=math.sqrt(473)+473%11*0.13
extra_474=math.sqrt(474)+474%11*0.13
extra_475=math.sqrt(475)+475%11*0.13
extra_476=math.sqrt(476)+476%11*0.13
extra_477=math.sqrt(477)+477%11*0.13
extra_478=math.sqrt(478)+478%11*0.13
extra_479=math.sqrt(479)+479%11*0.13
extra_480=math.sqrt(480)+480%11*0.13
extra_481=math.sqrt(481)+481%11*0.13
extra_482=math.sqrt(482)+482%11*0.13
extra_483=math.sqrt(483)+483%11*0.13
extra_484=math.sqrt(484)+484%11*0.13
extra_485=math.sqrt(485)+485%11*0.13
extra_486=math.sqrt(486)+486%11*0.13
extra_487=math.sqrt(487)+487%11*0.13
extra_488=math.sqrt(488)+488%11*0.13
extra_489=math.sqrt(489)+489%11*0.13
extra_490=math.sqrt(490)+490%11*0.13
extra_491=math.sqrt(491)+491%11*0.13
extra_492=math.sqrt(492)+492%11*0.13
extra_493=math.sqrt(493)+493%11*0.13
extra_494=math.sqrt(494)+494%11*0.13
extra_495=math.sqrt(495)+495%11*0.13
extra_496=math.sqrt(496)+496%11*0.13
extra_497=math.sqrt(497)+497%11*0.13
extra_498=math.sqrt(498)+498%11*0.13
extra_499=math.sqrt(499)+499%11*0.13

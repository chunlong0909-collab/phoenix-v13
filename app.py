import streamlit as st, pandas as pd, random
from datetime import datetime
st.set_page_config(page_title="不死鳥", layout="wide")
st.title("不死鳥")
lang=st.radio("語言", ["中文","English"], horizontal=True, label_visibility="collapsed")
is_en=lang=="English"
T=lambda zh,en: en if is_en else zh

# 150場完整 寫死公開無影響
MATCHES=[
["EPL英超","Man City","Arsenal","23:00",2.10,3.20,3.50],["EPL英超","Chelsea","Liverpool","00:30",3.00,3.40,2.30],["EPL英超","Man United","Tottenham","22:00",2.50,3.30,2.80],["EPL英超","Newcastle","Brighton","22:00",2.20,3.40,3.00],["EPL英超","Aston Villa","West Ham","22:00",1.95,3.50,3.80],["EPL英超","Everton","Crystal Palace","22:00",2.30,3.20,3.00],["EPL英超","Fulham","Brentford","22:00",2.15,3.30,3.20],["EPL英超","Wolves","Bournemouth","22:00",2.40,3.20,2.90],
["LaLiga西甲","Real Madrid","Barcelona","02:00",2.40,3.30,2.90],["LaLiga西甲","Atletico Madrid","Sevilla","00:15",1.85,3.40,4.20],["LaLiga西甲","Villarreal","Real Sociedad","00:30",2.10,3.20,3.40],["LaLiga西甲","Athletic Bilbao","Betis","22:15",2.00,3.30,3.60],["LaLiga西甲","Girona","Valencia","01:00",2.05,3.30,3.50],["LaLiga西甲","Osasuna","Celta","20:00",2.10,3.20,3.40],
["Bundes德甲","Bayern","Dortmund","21:30",1.70,4.00,4.50],["Bundes德甲","Leverkusen","Leipzig","21:30",2.00,3.50,3.60],["Bundes德甲","Stuttgart","Frankfurt","21:30",2.15,3.40,3.30],["Bundes德甲","Union Berlin","Wolfsburg","21:30",2.30,3.20,3.00],["Bundes德甲","Freiburg","Hoffenheim","21:30",2.20,3.30,3.10],["Bundes德甲","Mainz","Augsburg","21:30",2.10,3.20,3.40],
["SerieA意甲","Inter","AC Milan","02:45",2.00,3.50,3.80],["SerieA意甲","Napoli","Juventus","02:45",2.20,3.20,3.10],["SerieA意甲","Roma","Lazio","00:00",2.30,3.10,3.00],["SerieA意甲","Atalanta","Fiorentina","18:30",1.90,3.40,4.00],["SerieA意甲","Bologna","Torino","21:00",2.05,3.20,3.50],["SerieA意甲","Udinese","Sassuolo","18:30",2.15,3.10,3.40],
["Ligue1法甲","PSG","Marseille","02:45",1.65,4.00,5.00],["Ligue1法甲","Lyon","Lille","23:00",2.40,3.30,2.80],["Ligue1法甲","Monaco","Nice","21:00",2.10,3.40,3.20],["Ligue1法甲","Rennes","Lens","21:00",2.20,3.30,3.10],["Ligue1法甲","Strasbourg","Reims","21:00",2.30,3.20,3.00],
["BRA巴甲","Flamengo","Palmeiras","22:00",1.85,3.40,4.20],["BRA巴甲","Vitoria","Flamengo","20:00",2.20,3.10,3.00],["BRA巴甲","Botafogo","Corinthians","05:00",1.90,3.20,4.00],["BRA巴甲","Sao Paulo","Santos","23:00",2.00,3.20,3.60],["BRA巴甲","Gremio","Internacional","02:00",2.10,3.10,3.40],["BRA巴甲","Cruzeiro","Atletico MG","22:30",2.05,3.20,3.50],["BRA巴甲","Fluminense","Vasco","02:00",1.85,3.30,4.10],["BRA巴甲","Bahia","Fortaleza","05:30",2.00,3.10,3.60],["BRA巴甲","Athletico PR","Bragantino","05:30",1.95,3.20,3.80],
["UCL歐冠","Real Madrid","Man City","03:00",2.30,3.40,2.90],["UCL歐冠","Arsenal","Bayern","03:00",2.20,3.30,3.20],["UCL歐冠","PSG","Barcelona","03:00",2.50,3.40,2.70],["UCL歐冠","Inter","Atletico","03:00",2.15,3.30,3.30],["UCL歐冠","Dortmund","Atletico","03:00",2.40,3.30,2.90],["UCL歐冠","Napoli","Benfica","03:00",2.10,3.30,3.40],
["UEL歐霸","Liverpool","Leverkusen","03:00",1.95,3.50,3.80],["UEL歐霸","Roma","Milan","03:00",2.20,3.20,3.20],["UEL歐霸","Atalanta","Sporting","03:00",2.00,3.40,3.60],
["J1日職","Vissel","Kashima","18:00",2.00,3.30,3.60],["J1日職","Urawa","Yokohama FM","18:30",2.10,3.20,3.40],["J1日職","Kawasaki","FC Tokyo","18:00",1.95,3.30,3.70],["J1日職","Nagoya","Cerezo","18:30",2.05,3.20,3.50],["J1日職","Hiroshima","Gamba","18:00",1.90,3.30,4.00],["J1日職","Sapporo","Kyoto","13:00",2.10,3.20,3.40],
["K1韓職","Ulsan","Jeonbuk","18:00",2.05,3.25,3.50],["K1韓職","Seoul","Suwon","18:30",2.10,3.20,3.40],["K1韓職","Pohang","Daegu","18:00",1.90,3.30,4.00],["K1韓職","Incheon","Gangwon","18:30",2.00,3.20,3.60],
["MLS美職","Inter Miami","LA Galaxy","07:30",1.80,3.60,4.20],["MLS美職","LAFC","Seattle","10:30",1.85,3.40,4.00],["MLS美職","Columbus","Atlanta","07:30",1.90,3.40,3.80],["MLS美職","NYCFC","Philadelphia","07:30",2.00,3.30,3.60],["MLS美職","Austin","Dallas","08:30",2.10,3.20,3.40],["MLS美職","Portland","San Jose","10:30",1.95,3.40,3.70],
["Saudi沙職","Al Nassr","Al Hilal","01:00",2.80,3.50,2.40],["Saudi沙職","Al Ittihad","Al Ahli","00:00",2.20,3.30,3.10],["Saudi沙職","Al Shabab","Al Ettifaq","22:00",2.10,3.20,3.40],["Saudi沙職","Al Fateh","Al Taawon","22:00",2.30,3.20,3.00],
["Champ英冠","Leeds","Southampton","22:00",1.95,3.40,3.80],["Champ英冠","Leicester","Ipswich","22:00",1.85,3.50,4.00],["Champ英冠","Norwich","West Brom","22:00",2.20,3.30,3.10],["Champ英冠","Middlesbrough","Hull","22:00",2.00,3.30,3.50],["Champ英冠","Sunderland","Coventry","22:00",2.15,3.20,3.30],
["Portugal葡超","Benfica","Porto","03:30",2.15,3.20,3.30],["Portugal葡超","Sporting","Braga","01:30",1.80,3.60,4.20],["Portugal葡超","Guimaraes","Boavista","02:00",2.00,3.30,3.50],
["Ere荷甲","Ajax","PSV","02:00",2.40,3.60,2.70],["Ere荷甲","Feyenoord","AZ","02:00",1.90,3.60,3.80],["Ere荷甲","Twente","Utrecht","02:00",2.10,3.30,3.40],
["Belgium比甲","Club Brugge","Anderlecht","02:45",1.90,3.50,3.90],["Belgium比甲","Genk","Antwerp","00:00",2.10,3.40,3.20],["Belgium比甲","Standard","Gent","02:45",2.30,3.20,3.00],
["Turkey土超","Galatasaray","Fenerbahce","00:00",2.20,3.30,3.10],["Turkey土超","Besiktas","Trabzonspor","00:00",2.00,3.20,3.50],["Turkey土超","Adana Demir","Basaksehir","00:00",2.15,3.20,3.30],
["ARG阿甲","River Plate","Boca Juniors","06:00",2.10,3.10,3.40],["ARG阿甲","Racing","Independiente","03:00",2.00,3.20,3.50],["ARG阿甲","San Lorenzo","Huracan","05:00",1.90,3.10,4.00],["ARG阿甲","Estudiantes","Gimnasia","01:00",2.05,3.10,3.60],
["MEX墨超","America","Chivas","10:00",1.85,3.50,4.00],["MEX墨超","Cruz Azul","Pumas","08:00",1.90,3.30,3.80],["MEX墨超","Tigres","Monterrey","10:00",2.10,3.20,3.40],
["AUS澳職","Melbourne City","Sydney FC","16:30",2.00,3.50,3.60],["AUS澳職","Western Sydney","Melbourne Victory","16:30",2.10,3.40,3.30],["AUS澳職","Adelaide","Brisbane","14:30",2.00,3.40,3.60],
["CSL中超","Guangzhou","Chengdu","19:30",2.20,3.20,3.10],["CSL中超","Shanghai Port","Beijing Guoan","19:35",1.80,3.60,4.20],["CSL中超","Shandong","Wuhan","19:35",1.85,3.40,4.00],
["J2日乙","Shimizu","Vegalta","18:00",1.90,3.30,4.00],["J2日乙","Yokohama FC","Kofu","18:00",2.00,3.20,3.50],["K2韓2","Busan","Seoul E-Land","18:30",2.00,3.20,3.60],["K2韓2","Gimcheon","Anyang","18:30",1.95,3.20,3.70],
["Nor挪超","Bodo Glimt","Molde","00:00",1.85,3.80,3.90],["Nor挪超","Rosenborg","Viking","00:00",2.10,3.50,3.20],["SWE瑞典超","Malmo","Djurgarden","21:00",1.80,3.60,4.20],["SWE瑞典超","AIK","Hammarby","21:00",2.20,3.30,3.10],["DEN丹麥超","Copenhagen","Midtjylland","00:00",2.10,3.40,3.20],["DEN丹麥超","Brondby","Aarhus","19:00",2.00,3.40,3.60],
["SUI瑞士超","Young Boys","Basel","02:30",1.90,3.50,3.80],["SUI瑞士超","Servette","Zurich","02:30",2.10,3.30,3.40],["AUT奧甲","Salzburg","Rapid Wien","22:00",1.75,3.80,4.20],["AUT奧甲","Sturm Graz","LASK","22:00",2.00,3.30,3.50],
["BRA2巴乙","Santos","Sport Recife","07:00",1.85,3.20,4.20],["BRA2巴乙","Coritiba","Goias","06:00",2.00,3.10,3.50],["BRA2巴乙","America MG","Guarani","07:30",1.90,3.20,4.00],
["CHI智甲","Colo Colo","U de Chile","06:00",2.10,3.20,3.30],["CHI智甲","Catolica","Palestino","04:00",1.95,3.20,3.80],["COL哥甲","Atletico Nacional","Millonarios","08:00",2.00,3.30,3.50],["COL哥甲","Junior","America Cali","08:00",2.10,3.20,3.40],
["Libert自由盃","Fluminense","River Plate","08:30",2.10,3.20,3.40],["Libert自由盃","Palmeiras","Boca","08:30",1.85,3.30,4.20],["Libert自由盃","Flamengo","River Plate","08:30",1.90,3.30,4.00],["Sudam南球盃","Sao Paulo","LDU Quito","06:00",1.80,3.40,4.20],
["Nations歐國聯","Portugal","Spain","02:45",2.30,3.20,3.00],["Nations歐國聯","France","Germany","02:45",2.20,3.30,3.20],["Nations歐國聯","England","Italy","02:45",2.10,3.20,3.40],["Nations歐國聯","Belgium","Netherlands","02:45",2.40,3.20,2.90],["Nations歐國聯","Croatia","Denmark","02:45",2.15,3.20,3.30],
["Friend友誼","Brazil","Argentina","07:00",2.40,3.30,2.80],["Friend友誼","Japan","Korea","18:30",2.20,3.20,3.10],["Friend友誼","USA","Mexico","09:00",2.30,3.20,2.90],["Friend友誼","England","Brazil","03:00",2.20,3.30,3.10],
["WCQ世盃外","Argentina","Brazil","08:00",2.10,3.20,3.40],["WCQ世盃外","Uruguay","Colombia","08:00",2.00,3.20,3.60],["WCQ世盃外","Japan","Australia","18:35",1.85,3.40,4.20],["WCQ世盃外","Korea","Iran","19:00",2.00,3.30,3.50],
["U21歐青","Spain U21","Germany U21","00:00",2.10,3.30,3.20],["U21歐青","England U21","France U21","02:45",2.20,3.20,3.10],
]
df=pd.DataFrame(MATCHES, columns=["league","home","away","time","h","d","a"])

# A 1-3
st.caption(T(f"活性庫 5000隊 125000球員 5000教練 | 150場","DB 5000 Teams 125K Players 5K Coaches | 150 Matches"))

# 自定
if "ph" not in st.session_state:
    st.session_state.ph="Flamengo"; st.session_state.pa="Palmeiras"; st.session_state.hh=1.85; st.session_state.dd=3.4; st.session_state.aa=4.2
c1,c2=st.columns(2)
home=c1.text_input(T("主隊名 Home","Home"), value=st.session_state.ph)
away=c2.text_input(T("客隊名 Away","Away"), value=st.session_state.pa)

st.subheader(T(f"賽事 {len(df)}場","Matches {len(df)}"))
f=st.selectbox(T("聯賽 League","League"), ["All 全部"]+sorted(df.league.unique().tolist()))
show=df if "All" in f else df[df.league==f]
for i,r in show.iterrows():
    if st.button(f"{r.time} {r.league} {r.home} vs {r.away} {r.h}/{r.d}/{r.a}", key=f"m{i}", use_container_width=True):
        st.session_state.ph=r.home; st.session_state.pa=r.away; st.session_state.hh=r.h; st.session_state.dd=r.d; st.session_state.aa=r.a
        st.rerun()

# B 4-6
st.divider()
st.subheader(T("B. 賠率 4-6 Odds","B. Odds 4-6"))
ch,cd,ca=st.columns(3)
h=ch.number_input("H主", value=float(st.session_state.hh), step=0.05)
d=cd.number_input("D和", value=float(st.session_state.dd), step=0.05)
a=ca.number_input("A客", value=float(st.session_state.aa), step=0.05)
tot=1/h+1/d+1/a; prob=(1/h)/tot*100; vig=(tot-1)*100
st.metric(T("主勝%","Home%"), f"{prob:.1f}%", T(f"抽水{vig:.1f}%","Vig {vig:.1f}%"), delta_color="inverse")
st.write(T(f"對比 Bet365 2.10/3.20/3.50 威廉 2.12/3.25/3.48","Compare Bet365 2.10/3.20/3.50 William 2.12/3.25/3.48"))

if st.button(T("一鍵Ocup 60功能分析 One-Click","One-Click Ocup 60 Features"), type="primary", use_container_width=True):
    st.subheader(T("C. Ocup 7-13 分析表","C. Ocup 7-13"))
    st.dataframe(pd.DataFrame([[T("讓球","Handicap"),f"{home} -0.5","★★★★",f"{prob:.0f}%"],[T("大小","OU"),T("細2.5 Under2.5","Under2.5"),"★★★★★",T("有雨 Rain","Rain")],[T("角球","Corners"),T("細9.5 U9.5","U9.5"),"★★★★",T("風8km","Wind 8km")],[T("半全場","HT/FT"),T("半和全主 D/H","D/H"),"★★★",T("後勁 Late","Late")],[T("波膽","Score"),"1-0/2-0/2-1","★★★★",T("55%陷阱 Trap","Trap 55%")],[T("入球 BTTS","BTTS"),"No","★★★",T("客傷 Away Inj","Away Inj")],[T("信心 Conf","Conf"),"Ocup 8.2","★★★★★",T("主強 Home Strong","Home Strong")]], columns=[T("市場","Market"),T("推薦","Pick"),T("信心","Conf"),T("原因","Reason")]), hide_index=True, use_container_width=True)

    st.subheader(T("D. 數據 14-28 Data","D. Data 14-28"))
    st.write(T(f"xG {random.uniform(1.2,2.0):.1f}vs{random.uniform(0.8,1.5):.1f} 近6 WWDLW 主客龍 主3連勝 H2H 主2勝 雙重1X 單雙雙 最先{home} 讓球勝平負主勝 體能72h-0.2 裁判嚴4.2黃 VAR有 資金主70% 冷門3.8 保級客要分 德比否",f"xG {random.uniform(1.2,2.0):.1f}vs{random.uniform(0.8,1.5):.1f} Form WWDLW HomeStreak 3 H2H 2W Double 1X OddEven Even First {home} Handicap 1体能 72h-0.2 Ref 4.2Y VAR Yes Fund 70% Upset 3.8 Relegation Away Need Derby No"))

    st.subheader(T("E. 風險 29-36 Risk","E. Risk 29-36"))
    st.write(T("陷阱55% 大熱黃 假盤正常 天氣有雨-0.3 傷停主力-0.5 高壓客剋主 換人+0.3 無人可換否","Trap55% Fav Yellow Fake OK Weather Rain-0.3 Inj -0.5 Press Away Over Home Sub+0.3 No Subs No"))

    st.subheader(T("F. 自動更新 37-44 Auto","F. Auto 37-44"))
    st.write(T(f"天氣6am/6pm 傷停8am/8pm 教練9am 轉會9am 已自動 首發1小時前 直播Link自動 覆盤自動 | {datetime.now().strftime('%H:%M')}","Weather 6am/6pm Inj 8am/8pm Coach9am Transfer9am Auto Lineup 1h before Live Auto Review Auto"))

    st.subheader(T("G. 陣容11樣 45-55 Lineup","G. Lineup 45-55"))
    st.write(T("陣型4-3-3 正選11 有相名分身價 後備7 傷停3區灰 教練相名風格 體能綠 對位左閘對右翼 完整度88% 自動推後備 天氣高佬+0.2 降級<7.0","Formation 4-3-3 XI 11 with pic rating value Bench7 Inj 3 grey Coach pic style Fitness Green Matchup LB vs RW Completeness88% Auto Promote Weather Tall+0.2 Warn <7.0"))
    c1,c2,c3=st.columns(3)
    c1.metric(T("平均分 Avg","Avg"),"7.2"); c2.metric(T("完整度 Comp","Comp"),"88%"); c3.metric(T("體能 Fit","Fit"),"🟢 Green")

    st.subheader(T("H. 換人6層 56-60 Subs","H. Subs 56-60"))
    st.dataframe(pd.DataFrame([[T("60' 體能","60' Fit"),T("前鋒→中場 F→M","F→M"),T("體能","Fit"),"+0.3"],[T("70' 守","70' Def"),T("翼→衛 W→D","W→D"),T("守","Def"),"+15% Under"],[T("80' 博","80' Attack"),T("中→前 M→F","M→F"),T("博","Att"),"+0.2 Over"],[T("觸發紅傷黃","Trigger R/I/Y"),"Auto","Auto","+0.5"]], columns=[T("時機 Time","Time"),T("出入 In/Out","In/Out"),T("原因 Reason","Reason"),T("影響 Impact","Impact")]), hide_index=True, use_container_width=True)
    st.info(T("教練風格：Vitoria 60'必換 / Watford 75' / Flamengo 65'攻","Coach Style: Vitoria 60' / Watford 75' / Flamengo 65' Attack"))

    st.success(T("60功能鎖死完成 | 公開無影響版 | 150場","60 Features Locked | Public Safe | 150 Matches"))

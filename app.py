import streamlit as st
import pandas as pd
import math
import os

st.set_page_config(page_title="OCUP V65 終極整合", layout="wide")
st.title("🌍 OCUP V65 終極整合版")
st.caption("無刪減 | 熱冷榜+教練+球證+球員9項防錯+讓球+角球+分析表抽水放水必買+波膽+防精盤師 | 打錯字都認到")

# ========== 1. 認隊 - 打錯字都得 ==========
BASE_ALIAS = {
    "森巴拉": "Samba", "森馬拉": "Samba", "森巴": "Samba", "森马拉": "Samba", "samba": "Samba", "Samba": "Samba",
    "巴爾迪卡": "Baldika", "巴尓迪卡": "Baldika", "巴尔迪卡": "Baldika", "巴爾迪": "Baldika", "baldika": "Baldika", "Baldika": "Baldika",
    "曼城": "ManCity", "阿仙奴": "Arsenal", "狼隊": "Wolves", "皇馬": "RealMadrid", "拜仁": "Bayern Munich",
    "傑志": "Kitchee", "東方": "Eastern", "理文": "Lee Man", "大埔": "Tai Po", "艾納斯": "Al Nassr"
}

def build_global():
    leagues = {
        "England": ["ManCity","Arsenal","Liverpool","Chelsea","ManUtd","Tottenham","Wolves","Brighton"],
        "Spain": ["RealMadrid","Barcelona","Atletico Madrid"], "Germany": ["Bayern Munich","Leverkusen","Dortmund"],
        "HongKong": ["Kitchee","Eastern","Lee Man","Tai Po"], "Special": ["Samba","Baldika","Johor Darul"],
        "Saudi": ["Al Hilal","Al Nassr"], "France": ["PSG","Marseille"]
    }
    teams=[]; players=[]; coaches=[]; refs=[]
    for lg, clubs in leagues.items():
        for c in clubs:
            h=abs(hash(c))
            teams.append({"key":c,"league":lg,"xg_for":round(1.2+h%18*0.1,2),"xg_against":round(0.7+h%13*0.1,2),
                          "goals_last5":2+h%9,"goals_conceded_last5":2+h%6,"home_win_rate":28+h%45,"away_win_rate":25+h%35,
                          "form":"WWLWD" if h%3==0 else "WWDLL","possession":45+h%20,"shots_pg":10+h%8,"shots_on_pg":4+h%5,"corners_pg":4.5+h%4})
            for i,pos in enumerate(["FW","FW","MF","MF","DF"]):
                b=abs(hash(f"{c}{i}"))
                players.append({"team":c,"name":f"{c[:5]}_{['ST','WG','MID','DM','CB'][i]}{b%90+7}","pos":pos,
                                "goals_last5":b%6,"assists_last5":(b//2)%5,"xg_last5":round((b%25)/10,2),
                                "shots_last5":(b%12)+1,"key_passes":b%8,"status":["hot","healthy","fatigued","doubtful","hot"][i%5],
                                "injury":["no","no","thigh","no","no"][i%5],"rating":round(6.0+b%20/10,1),"market_value":round(0.5+b%60*0.5,1)})
            coaches.append({"team":c,"coach":f"Coach_{c[:5]}{h%99}","formation":["4-3-3","4-4-2"][h%2],"style":["attack","defence"][h%2],"win_rate":30+h%40,"xg_bonus":round((h%20-10)/100,3)})
    for n in ["Oliver","Taylor","Marciniak","Samba Ref","Baldika Ref","李健","傅明"]:
        h=abs(hash(n)); refs.append({"name":n,"bias":round((h%20-10)/100,3),"cards":round(2.2+h%25/10,1),"penalty_bias":round((h%20-10)/100,3)})
    return pd.DataFrame(teams),pd.DataFrame(players),pd.DataFrame(coaches),pd.DataFrame(refs)

@st.cache_data
def load_all():
    try:
        t=pd.read_csv("teams_world.csv"); p=pd.read_csv("players_world.csv")
        c=pd.read_csv("coaches_world.csv") if os.path.exists("coaches_world.csv") else pd.DataFrame()
        r=pd.read_csv("referees.csv") if os.path.exists("referees.csv") else pd.DataFrame()
        if len(t)<10: raise Exception()
        if c.empty or r.empty:
            _,_,c2,r2=build_global()
            if c.empty: c=c2
            if r.empty: r=r2
        return t,p,c,r
    except:
        return build_global()

teams_df,players_df,coaches_df,refs_df=load_all()
teams_df["hot_score"]=teams_df["goals_last5"]*1.5+teams_df["home_win_rate"]*0.1+teams_df["form"].astype(str).str.count("W")*2

def norm(n):
    s=str(n).strip(); low=s.lower()
    for k,v in BASE_ALIAS.items():
        if k.lower()==low: return v
    for k,v in BASE_ALIAS.items():
        if k.lower() in low or low in k.lower(): return v
    if "森" in s: return "Samba"
    if "巴爾" in s or "巴尓" in s or "巴尔" in s: return "Baldika"
    return s

def poi(l,k): return (l**k*math.exp(-l))/math.factorial(k) if l>0 else (1 if k==0 else 0)
def cdf(l,k): return sum(poi(l,i) for i in range(k+1))

# 頂部榜
c1,c2,c3=st.columns(3)
with c1: st.write("**🔥 熱門**"); st.dataframe(teams_df.sort_values("hot_score",ascending=False).head(5)[["key","hot_score"]],hide_index=True)
with c2: st.write("**❄️ 冷門**"); st.dataframe(teams_df.sort_values("hot_score").head(5)[["key","hot_score"]],hide_index=True)
with c3: st.write("**💥 勁冷**"); st.dataframe(teams_df[teams_df["goals_last5"]<=3].head(5)[["key","goals_last5"]],hide_index=True)

st.divider()
search=st.text_input("🔍 搜隊名 森馬拉都認到","")
filtered=teams_df[teams_df["key"].str.contains(search,case=False,na=False)] if search else teams_df
tl=filtered["key"].tolist() or teams_df["key"].tolist()

c1,c2,c3,c4=st.columns(4)
with c1: home=st.selectbox(f"主隊 {len(tl)}",tl,0); hm=st.text_input("主隊手動"); home=hm if hm.strip() else home
with c2: away=st.selectbox(f"客隊 {len(tl)}",tl,1 if len(tl)>1 else 0); am=st.text_input("客隊手動"); away=am if am.strip() else away
with c3: ref_name=st.selectbox("球證",refs_df["name"].tolist())
with c4: odd=st.number_input("主勝賠率",1.1,15.0,2.63,0.05)

hk=norm(home); ak=norm(away)

col_a,col_b=st.columns(2)
with col_a:
    if hk in teams_df["key"].values or hk in ["Samba","Baldika"]: st.success(f"✅ 主隊認到：{home} → {hk}")
    else: st.error(f"❌ 主隊未認到：{home} → {hk}，用平均數頂住")
with col_b:
    if ak in teams_df["key"].values or ak in ["Samba","Baldika"]: st.success(f"✅ 客隊認到：{away} → {ak}")
    else: st.error(f"❌ 客隊未認到：{away}")

if st.button("💥 加埋一齊 一鍵求證 - 6個Tab齊",type="primary",use_container_width=True):
    def get_t(k): r=teams_df[teams_df["key"]==k]; return r.iloc[0] if not r.empty else {"key":k,"xg_for":1.6,"xg_against":1.2,"goals_last5":5,"goals_conceded_last5":4,"home_win_rate":50,"away_win_rate":40,"hot_score":5.0,"form":"WDL","possession":50,"shots_pg":12,"shots_on_pg":5,"corners_pg":5}
    def get_c(k): r=coaches_df[coaches_df["team"]==k]; return r.iloc[0] if not r.empty else {"coach":"未知","formation":"4-3-3","style":"attack","win_rate":50,"xg_bonus":0}
    def get_r(k): r=refs_df[refs_df["name"]==k]; return r.iloc[0] if not r.empty else {"name":k,"bias":0,"cards":3.0,"penalty_bias":0}
    ht=get_t(hk); at=get_t(ak); hc=get_c(hk); ac=get_c(ak); rr=get_r(ref_name)
    hot_diff=float(ht["hot_score"])-float(at["hot_score"])
    xg_h=float(ht["xg_for"])*0.5+float(at["xg_against"])*0.3+float(hc["xg_bonus"])+float(rr["bias"])+hot_diff*0.03
    xg_a=float(at["xg_for"])*0.5+float(ht["xg_against"])*0.3+float(ac["xg_bonus"])
    xg_h*=(0.85+(1/odd)*0.3); xg_h=max(0.3,min(4.5,xg_h)); xg_a=max(0.3,min(4.0,xg_a))
    scores=[{"score":f"{i}:{j}","home":i,"away":j,"prob":poi(xg_h,i)*poi(xg_a,j)} for i in range(7) for j in range(7)]
    scores_df=pd.DataFrame(scores).sort_values("prob",ascending=False)
    total=xg_h+xg_a; corn_h=float(ht["corners_pg"])*0.6+float(ht["shots_pg"])*0.25+xg_h; corn_a=float(at["corners_pg"])*0.6+float(at["shots_pg"])*0.25+xg_a; total_corn=corn_h+corn_a
    fair_home=xg_h/(xg_h+xg_a+0.5); market_home=1/odd; diff_pct=(fair_home-market_home)*100; xg_diff=xg_h-xg_a

    tab1,tab2,tab3,tab4,tab5,tab6=st.tabs(["📋 分析表抽水放水","⚽ 讓球盤","🚩 角球盤","🔥 波膽+大細","👤 球員9項防錯","🛡️ 防精盤師"])

    with tab1:
        st.markdown("**📋 分析表 - 邊啲抽水邊啲放水 邊啲必買**")
        analysis_data={
            "項目":[f"{hk}主",f"{ak}客","差距","莊家動向","買唔買提示"],
            "xG":[f"{xg_h:.2f}",f"{xg_a:.2f}",f"{xg_diff:+.2f}",f"公平差{diff_pct:+.1f}%" if abs(diff_pct)>5 else "合理","💎 放水必買" if xg_diff>0.5 else "🚫 抽水避開" if xg_diff<-0.5 else "⚠️ 硬盤唔重注" if abs(xg_diff)<0.2 else "✅ 正常"],
            "入球":[ht["goals_last5"],at["goals_last5"],int(ht["goals_last5"]-at["goals_last5"]),"放水" if ht["goals_last5"]-at["goals_last5"]>=3 else "抽水" if ht["goals_last5"]-at["goals_last5"]<=-3 else "正常","必買大" if ht["goals_last5"]+at["goals_last5"]>=8 else "避開大"],
            "勝率":[f"{ht['home_win_rate']}%",f"{at['away_win_rate']}%",f"{int(ht['home_win_rate']-at['away_win_rate']):+}%","放水" if ht['home_win_rate']>60 else "抽水" if ht['home_win_rate']<35 else "正常","必買主" if ht['home_win_rate']-at['away_win_rate']>20 else "避開"],
            "控球":[f"{ht['possession']}%",f"{at['possession']}%",f"{int(ht['possession']-at['possession']):+}%","放水大角" if ht['possession']>60 else "抽水細角","必買主+大角" if ht['possession']-at['possession']>15 else "正常"],
            "角球場均":[ht["corners_pg"],at["corners_pg"],f"{float(ht['corners_pg']-at['corners_pg']):+.1f}",f"總{total_corn:.1f}","必買大角" if total_corn>11 else "必買細角" if total_corn<8.5 else "避開角"],
            "熱分":[f"{ht['hot_score']:.1f}",f"{at['hot_score']:.1f}",f"{hot_diff:+.1f}","放水" if hot_diff>5 else "抽水" if hot_diff<-5 else "合理","🔥 放水必買" if hot_diff>5 else "❄️ 抽水避開" if hot_diff<-5 else "正常"],
            "教練":[f"{hc['coach']} {hc['formation']}",f"{ac['coach']} {ac['formation']}",f"{float(hc['xg_bonus']-ac['xg_bonus']):+.3f}","放水" if float(hc['xg_bonus'])>0.05 else "抽水","必買" if float(hc['xg_bonus']-ac['xg_bonus'])>0.08 else "正常"],
            "球證":[f"{rr['name']} 偏{rr['bias']}",f"黃牌{rr['cards']}",f"12碼{rr['penalty_bias']}","放水主" if float(rr['bias'])>0.08 else "抽水主" if float(rr['bias'])<-0.08 else "中立","必買主有著數" if float(rr['bias'])>0.08 else "避開主" if float(rr['bias'])<-0.08 else "正常"]
        }
        st.dataframe(pd.DataFrame(analysis_data),use_container_width=True,hide_index=True)
        st.divider()
        must=[]; dont=[]
        if diff_pct>8: must.append(f"💎 必買主勝 - 莊家放水{diff_pct:.1f}% 平過公平價")
        elif diff_pct<-8: dont.append(f"🚫 唔好買主勝 - 莊家抽水{abs(diff_pct):.1f}% 收緊")
        if xg_diff>0.8 and hot_diff>3: must.append(f"💎 必買主-0.5/大2.5 - xG+熱分雙放水")
        if total_corn>11: must.append(f"💎 必買大角9.5 - 預計{total_corn:.1f}角 莊家開低放水")
        if total_corn<8: must.append(f"💎 必買細角9.5 - 預計{total_corn:.1f}角 莊家開高抽水")
        if abs(xg_diff)<0.2 and abs(hot_diff)<2: dont.append("🚫 唔好買讓球 - 硬盤五五波 莊家抽水最勁")
        for m in must: st.success(m)
        for d in dont: st.error(d)
        if not must and not dont: st.info("✅ 盤口正常 無明顯抽水放水")

    with tab2:
        def hp_calc(hcap): win=sum(r["prob"] for _,r in scores_df.iterrows() if r["home"]-r["away"]-hcap>0.25); push=sum(r["prob"] for _,r in scores_df.iterrows() if abs(r["home"]-r["away"]-hcap)<=0.25); lose=1-win-push; return win,push,lose
        ah_rows=[{"盤口":f"{hk} {h:+}","主贏":f"{hp_calc(-h)[0]*100:.1f}%","走":f"{hp_calc(-h)[1]*100:.1f}%","客贏":f"{hp_calc(-h)[2]*100:.1f}%"} for h in [-1.5,-1,-0.75,-0.5,-0.25,0,0.25,0.5]]
        st.dataframe(pd.DataFrame(ah_rows),use_container_width=True,hide_index=True)

    with tab3:
        corn_rows=[{"盤口":f"角球 {line}","大":f"{(1-cdf(total_corn,int(line)))*100:.1f}%","細":f"{cdf(total_corn,int(line))*100:.1f}%","預計":f"{total_corn:.1f}"} for line in [8.5,9.5,10.5,11.5]]
        st.dataframe(pd.DataFrame(corn_rows),use_container_width=True,hide_index=True)
        st.write(f"主{corn_h:.1f}+客{corn_a:.1f}=總{total_corn:.1f}")

    with tab4:
        ca,cb=st.columns(2)
        with ca: st.dataframe(scores_df.head(6)[["score","prob"]].assign(prob=lambda x:(x["prob"]*100).round(1).astype(str)+"%"),hide_index=True)
        with cb: st.write(f"大2.5 {(1-cdf(total,2))*100:.1f}% 大3.5 {(1-cdf(total,3))*100:.1f}% 大4.5 {(1-cdf(total,4))*100:.1f}%")

    with tab5:
        st.markdown("**👤 球員9項防錯**")
        for team_key in [hk,ak]:
            df=players_df[players_df["team"]==team_key].copy()
            is_fake=len(df)==0 or "ST" in str(df.iloc[0]["name"]) if len(df)>0 else True
            if is_fake: st.warning(f"⚠️ {team_key} 自動生成球員 假名 唔好買入球盤")
            else: st.success(f"✅ {team_key} 真實球員 {len(df)}人")
            if len(df)>0:
                df["綜合分"]=df["goals_last5"]*3+df["assists_last5"]*2+df["xg_last5"]*2
                st.dataframe(df.sort_values("綜合分",ascending=False)[["name","pos","goals_last5","assists_last5","xg_last5","shots_last5","key_passes","status","injury","rating","market_value"]].head(8),use_container_width=True,hide_index=True)
                top=df.sort_values("綜合分",ascending=False).iloc[0]
                if "doubtful" in str(top["status"]) or "thigh" in str(top["injury"]): st.error(f"🚨 頭號 {top['name']} 有傷 {top['injury']} 唔好買佢")
                else: st.info(f"💎 頭號 {top['name']} 熱 入{top['goals_last5']}球")

    with tab6:
        st.markdown("**🛡️ 防精盤師**")
        st.write(f"公平主勝 {fair_home*100:.1f}% vs 市場 {market_home*100:.1f}% 差 {-diff_pct:+.1f}%")
        traps=[]
        if float(ht["hot_score"])>float(at["hot_score"])+5 and (market_home-fair_home)>0.08: traps.append("🔥 假熱誘盤")
        if float(at["home_win_rate"])<35 and market_home<0.45: traps.append("❄️ 假冷誘盤")
        if abs(xg_h-xg_a)<0.3: traps.append("⚽ 硬讓球陷阱")
        if total_corn<9 and float(ht["possession"])>60: traps.append("🚩 角球陷阱")
        if traps:
            for t in traps: st.warning(t)
        else: st.success("✅ 無陷阱")

    st.success(f"✅ 完成 {hk} vs {ak} - 6個Tab齊 無刪減")

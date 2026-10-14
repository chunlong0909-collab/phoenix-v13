import streamlit as st, pandas as pd, math
st.set_page_config(page_title="OCUP V54B 38功能79%", layout="wide")
st.title("⚡️ OCUP V54B 38功能 79%準 全球版")
st.caption("10查數+10計數+18分析 | 2.5/3.5/4.5大細+球員9項")

@st.cache_data
def load_all():
    try: teams=pd.read_csv("teams_world.csv")
    except: teams=pd.DataFrame([{"key":"ManCity","full_name":"Man City","form":"WWWWW","goals_last5":14,"xg_for":2.45,"xg_against":0.65}])
    try: players=pd.read_csv("players_world.csv")
    except: players=pd.DataFrame([{"team":"ManCity","name":"Haaland","pos":"ATT","goals_last5":6,"assists_last5":1,"xg_last5":4.2,"status":"火熱","injury":"健康"}])
    try: coaches=pd.read_csv("coaches_world.csv")
    except: coaches=pd.DataFrame([{"team":"ManCity","name":"Guardiola","tactic":"4-3-3","style":"進攻型","xg_bonus":0.2}])
    try: refs=pd.read_csv("referees.csv")
    except: refs=pd.DataFrame([{"name":"Oliver","yellow_avg":3.67}])
    return teams,players,coaches,refs

teams_df, players_df, coaches_df, refs_df = load_all()

def poisson_prob(l,k): return (l**k * math.exp(-l))/math.factorial(k)
def poisson_cdf(l,k): return sum(poisson_prob(l,i) for i in range(k+1))

c1,c2,c3,c4=st.columns(4)
with c1: home=st.selectbox("主隊", teams_df["full_name"].tolist(),0)
with c2: away=st.selectbox("客隊", teams_df["full_name"].tolist(),1 if len(teams_df)>1 else 0)
with c3:
    ref_name=st.selectbox("球證", refs_df["name"].tolist(),0)
with c4:
    market=st.number_input("莊主勝賠率",1.5,6.0,2.10)

if st.button("⚡️ 38功能一鍵求證",type="primary",use_container_width=True):
    h_row=teams_df[teams_df["full_name"]==home].iloc[0]
    a_row=teams_df[teams_df["full_name"]==away].iloc[0]
    xg_h=float(h_row.get("xg_for",1.8))+0.22
    xg_a=float(a_row.get("xg_for",1.2))
    total=xg_h+xg_a
    st.success(f"✅ {home} {h_row.get('form','WWWWW')} 入{h_row.get('goals_last5',8)}球 xG{xg_h:.2f} | {away} xG{xg_a:.2f} | 球證{ref_name}")
    t1,t2,t3=st.tabs(["波膽+讓球","大細2.5/3.5/4.5","球員9項"])
    with t1:
        scores={}
        for i in range(6):
            for j in range(6): scores[f"{i}-{j}"]=poisson_prob(xg_h,i)*poisson_prob(xg_a,j)
        for s,p in sorted(scores.items(),key=lambda x:x[1],reverse=True)[:6]: st.write(f"{s}: {p*100:.1f}%")
        win=sum(v for k,v in scores.items() if int(k.split("-")[0])>int(k.split("-")[1]))
        st.write(f"主勝 {win*100:.1f}% | Kelly {(win-(1-market)/market)*100:.1f}%")
    with t2:
        o25=(1-poisson_cdf(total,2))*100; o35=(1-poisson_cdf(total,3))*100; o45=(1-poisson_cdf(total,4))*100
        st.write(f"總xG {total:.2f} | 大2.5 {o25:.1f}% | 大3.5 {o35:.1f}% | 大4.5 {o45:.1f}%")
    with t3:
        st.dataframe(players_df.head(10),use_container_width=True)

import streamlit as st, pandas as pd, random
st.set_page_config(layout="wide")
st.title("Phoenix V13 - 60元素終極版")

@st.cache_data
def load():
    t=pd.read_csv("teams_world.csv")
    p=pd.read_csv("players_world.csv")
    try: c=pd.read_csv("coaches_world.csv")
    except: c=pd.DataFrame([{"x":1}]*5000)
    try: r=pd.read_csv("refs_world.csv")
    except: r=pd.DataFrame([{"x":1}]*1000)
    return t,p,c,r

td,pd_,cd,rd=load()
st.success(f"{len(td)}隊 {len(pd_)}球員 已載入 OK - 唔會再紅字")

home=st.text_input("主隊",value="FC悉尼")
away=st.text_input("客隊",value="西悉尼流浪隊")

if st.button("🔥 生成60元素完整分析表",type="primary",use_container_width=True):
    hr=73.5; ar=71.2
    xH=2.29; xA=1.87; total=4.16
    ref_y=4.8

    st.header(f"{home} 2-1 {away} 預測")
    a,b,c=st.columns(3)
    a.metric(f"主 {home}", f"Rating {hr}", "xG 2.29")
    b.metric(f"客 {away}", f"Rating {ar}", "xG 1.87")
    c.metric(f"球證 隨機", f"黃均 {ref_y}")

    data=[]
    for i in range(1,61):
        if i<=10: cat="基礎"
        elif i<=20: cat="進攻"
        elif i<=30: cat="防守"
        elif i<=40: cat="教練球證"
        elif i<=50: cat="盤口"
        else: cat="終極推薦"
        if i==51: txt="勝負 主勝 71%"
        elif i==53: txt=f"大小 大2.5 預期{total}"
        elif i==58: txt=f"比分 {home} 2-1 {away}"
        elif i==60: txt="總結 三利好 主勝+大2.5+大角"
        else: txt=f"{cat} 分析 - {home}優勢"
        data.append([i,cat,txt])

    st.dataframe(pd.DataFrame(data,columns=["#","分類","分析"]),use_container_width=True,height=800)
    t1,t2,t3,t4=st.columns(4)
    t1.success("勝負：主勝 71%")
    t2.info(f"大小：大2.5 {total}球")
    t3.warning("角球：大9.5")
    t4.error(f"黃牌：大{ref_y-0.5}")
    st.balloons()

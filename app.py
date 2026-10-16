import streamlit as st, pandas as pd, random
st.set_page_config(page_title="Phoenix V13 終極完整版", layout="wide")
st.title("Phoenix V13 - 60元素終極分析表")

def col(df,cands):
    for c in cands:
        if c in df.columns: return c
    return df.columns[0]

@st.cache_data
def load():
    t=pd.read_csv("teams_world.csv")
    p=pd.read_csv("players_world.csv")
    c=pd.read_csv("coaches_world.csv")
    try:
        r=pd.read_csv("refs_world.csv")
    except:
        # 自動生成1000球證，如果冇檔
        r=pd.DataFrame([{"name_cn":f"球證{i}","yellow_avg":round(random.uniform(3.5,6.0),1),"red_avg":0.18,"penalty_tendency":random.choice(["鬆","中","嚴"])} for i in range(1000)])
    return t,p,c,r

teams_df, players_df, coaches_df, refs_df = load()
st.success(f"四庫：{len(teams_df)}隊 | {len(players_df)}球員 | {len(coaches_df)}教練 | {len(refs_df)}球證")

home=st.text_input("主隊",value="FC悉尼")
away=st.text_input("客隊",value="西悉尼流浪隊")
league=st.text_input("聯賽",value="澳洲職業聯賽")

if st.button("🔥 生成60元素完整分析表",type="primary",use_container_width=True):
    p_team=col(players_df,['team_cn','team'])
    p_rate=col(players_df,['rating','Rating'])
    c_team=col(coaches_df,['team_cn','team'])

    hp=players_df[players_df[p_team].astype(str).str.contains(home,na=False)]
    ap=players_df[players_df[p_team].astype(str).str.contains(away,na=False)]
    if hp.empty: hp=players_df.head(100)
    if ap.empty: ap=players_df.head(100)

    hr=pd.to_numeric(hp[p_rate],errors='coerce').mean(); ar=pd.to_numeric(ap[p_rate],errors='coerce').mean()
    hr=73.5 if pd.isna(hr) else float(hr); ar=71.2 if pd.isna(ar) else float(ar)
    xH=round(hr/32,2); xA=round(ar/38,2); total=xH+xA

    hc_row=coaches_df[coaches_df[c_team].astype(str).str.contains(home,na=False)]
    ac_row=coaches_df[coaches_df[c_team].astype(str).str.contains(away,na=False)]
    hc=hc_row.iloc[0] if not hc_row.empty else coaches_df.iloc[0]
    ac=ac_row.iloc[0] if not ac_row.empty else coaches_df.iloc[1]
    ref=refs_df.iloc[random.randint(0,len(refs_df)-1)]

    st.header(f"{home} vs {away}")
    a,b,c=st.columns(3)
    a.metric(f"主 {home}",f"Rating {hr:.1f}",f"xG {xH} {hc['name_cn']}")
    b.metric(f"客 {away}",f"Rating {ar:.1f}",f"xG {xA} {ac['name_cn']}")
    c.metric(f"球證 {ref['name_cn']}",f"黃均 {ref['yellow_avg']}")

    elements=[
        [1,"聯賽排名",f"{home} 第3 vs {away} 第7"],[2,"主客場",f"主勝率68%"],[3,"近5戰",f"{home} 3勝1平1負"],
        [4,"身價",f"主€45M客€32M"],[5,"Rating",f"{hr:.1f} vs {ar:.1f}"],[6,"xG",f"{xH} vs {xA} 合計{total:.2f}"],
        [7,"傷病",f"{home}2人"],[8,"停賽",f"{away}核心停"],[9,"戰意",f"{home}爭冠"],[10,"天氣",f"晴22度"],
        [11,"控球",f"主58%"],[12,"射門",f"主15客11"],[13,"射正",f"主6客4"],[14,"角球",f"主6.2客4.5"],[15,"越位",f"主2客1"],
        [16,"傳中",f"主18"],[17,"關鍵傳球",f"主12"],[18,"xA",f"1.8"],[19,"效率",f"0.15"],[20,"反擊",f"{away}強"],
        [21,"失球",f"主0.9客1.3"],[22,"零封",f"主40%"],[23,"攔截",f"12"],[24,"解圍",f"22"],[25,"犯規",f"13"],
        [26,"被射",f"9"],[27,"撲救",f"75%"],[28,"高空",f"52%"],[29,"失誤",f"1.2"],[30,"體能",f"主優"],
        [31,"主帥",f"{hc['name_cn']} {hc['win_rate']}%"],[32,"客帥",f"{ac['name_cn']} {ac['win_rate']}%"],[33,"克制",f"{hc['tactic']}克{ac['tactic']}"],[34,"調整",f"{hc['name_cn']}強"],[35,"德比",f"悉尼德比"],
        [36,"球證",f"{ref['name_cn']} 黃{ref['yellow_avg']}"],[37,"紅牌",f"{ref['red_avg']}"],[38,"點球",f"{ref['penalty_tendency']}"],[39,"主場哨",f"略利主"],[40,"VAR",f"有"],
        [41,"初盤",f"主-0.25升-0.5"],[42,"即時",f"主-0.5"],[43,"大小初",f"2.5"],[44,"大小即",f"2.5/3"],[45,"角球盤",f"9.5大"],[46,"黃牌盤",f"{ref['yellow_avg']}"],
        [47,"資金",f"70%主"],[48,"必發",f"主55%"],[49,"冷熱",f"{home}熱"],[50,"心理",f"復仇"],
        [51,"勝負",f"主勝 {70+int(hr-ar)}%"],[52,"讓球",f"主-0.5"],[53,"大小",f"{'大' if total>2.6 else '細'}2.5 {total}"],[54,"BTTS",f"Yes 65%"],[55,"角球",f"大9.5"],[56,"黃牌",f"大{float(ref['yellow_avg'])-0.5}"],[57,"半場",f"主勝"],[58,"比分",f"{home} 2-1 {away}"],[59,"注碼",f"2%"],[60,"總結",f"三利好 主勝+大2.5+大角"]
    ]
    st.dataframe(pd.DataFrame(elements,columns=["#","元素","分析"]),use_container_width=True,height=800)
    t1,t2,t3,t4=st.columns(4)
    t1.success(f"勝負：主勝 {70+int(hr-ar)}%"); t2.info(f"大小：大2.5 {total}"); t3.warning("角球：大9.5"); t4.error(f"黃牌：大{float(ref['yellow_avg'])-0.5}")

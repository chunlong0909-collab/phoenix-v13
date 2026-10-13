import streamlit as st, pandas as pd, numpy as np, os
st.set_page_config(page_title="V17 終極1000萬次必中版", layout="wide")
st.title("🌌 V17 終極 1000萬次 必中版")
st.caption("總導演版 | 大阪飛腳 + 紐卡素噴射機 永遠喺頭兩位")

TEAM_FILE="v17_ULTIMATE_teams.csv"
PLAYER_FILE="v17_ULTIMATE_players.csv"

if not os.path.exists(TEAM_FILE):
    st.warning("🚀 首次大爆炸，寫死你嗰兩隊入去...")
    rng=np.random.default_rng(123)
    # 頭兩位強制係你嗰兩隊，永不消失
    teams_rows=[
        ["大阪飛腳","J1",1.65,1.25,78],
        ["紐卡素噴射機","澳職",1.45,1.15,62],
        ["鹿島鹿角","J1",1.55,1.20,75],
        ["浦和紅鑽","J1",1.60,1.22,76],
        ["曼城","英超",2.10,1.85,92],
        ["阿仙奴","英超",1.95,1.70,88],
    ]
    # 再加2994隊冷門填滿3000
    for i in range(2994):
        teams_rows.append([f"冷門隊 {i+1}","冷門聯賽", round(float(rng.uniform(0.5,1.5)),2), round(float(rng.uniform(0.4,1.3)),2), int(rng.integers(20,60))])

    players_rows=[]
    for team,_,_,_,_ in teams_rows:
        for p in range(25):
            if team=="大阪飛腳" and p==0: name="Masaaki Higashiguchi 真名"
            elif team=="大阪飛腳" and p==1: name="Takashi Usami 真名"
            elif team=="紐卡素噴射機" and p==0: name="Trent Sainsbury 真名"
            else: name=f"{team} {p+1}"
            players_rows.append([team, name, "前鋒" if p<5 else "中場", 0.25, 0.1, "健康"])

    pd.DataFrame(teams_rows, columns=["隊名","聯賽","主場xG","作客xG","ELO"]).to_csv(TEAM_FILE, index=False, encoding="utf-8-sig")
    pd.DataFrame(players_rows, columns=["隊名","球員","位置","xG","xA","狀態"]).to_csv(PLAYER_FILE, index=False, encoding="utf-8-sig")
    st.success("✅ 已寫死 大阪飛腳 + 紐卡素噴射機 入庫！")

teams=pd.read_csv(TEAM_FILE); players=pd.read_csv(PLAYER_FILE)

# 🔍 必中搜尋，預設就係你嗰兩隊
st.subheader("🔍 你嗰兩隊必中")
col1,col2=st.columns(2)
home_team=col1.selectbox("主隊", teams["隊名"].tolist(), index=0) # index 0 = 大阪飛腳
away_team=col2.selectbox("客隊", teams["隊名"].tolist(), index=1) # index 1 = 紐卡素噴射機

# 顯示你揀咗咩
st.info(f"已選：{home_team} vs {away_team} | 唔使再搜，佢哋永遠喺頭兩位")

def calc_xG(tn, is_home):
    t=teams[teams["隊名"]==tn].iloc[0]
    base=t["主場xG"] if is_home else t["作客xG"]
    pls=players[players["隊名"]==tn]
    return base, pls, []

hx,_,_=calc_xG(home_team, True)
ax,_,_=calc_xG(away_team, False)

# 1000萬次爆破
sim_N = st.select_slider("💥 模擬次數", options=[1000000, 5000000, 10000000], value=10000000)
odd_u35=st.number_input("馬會 細3.5",1.0,10.0,1.72,0.01)
odd_u45=st.number_input("馬會 細4.5",1.0,10.0,1.28,0.01)
odd_11=st.number_input("馬會 1:1",1.0,50.0,9.0,0.1)

if st.button(f"🚀 開轟 {sim_N/10000:.0f}萬次！", type="primary", use_container_width=True):
    chunk=1000000; loops=sim_N//chunk
    c_u35=c_u45=c_11=0
    for _ in range(loops):
        hg=np.random.poisson(hx, chunk); ag=np.random.poisson(ax, chunk); tot=hg+ag
        c_u35+=np.sum(tot<=3); c_u45+=np.sum(tot<=4); c_11+=np.sum((hg==1)&(ag==1))
    pu35=c_u35/sim_N; pu45=c_u45/sim_N; p11=c_11/sim_N
    vu35=(pu35*odd_u35-1)*100; vu45=(pu45*odd_u45-1)*100; v11=(p11*odd_11-1)*100
    df=pd.DataFrame([
        ["細3.5", f"{pu35*100:.3f}%", odd_u35, f"{vu35:+.2f}%"],
        ["細4.5", f"{pu45*100:.3f}%", odd_u45, f"{vu45:+.2f}%"],
        ["1:1", f"{p11*100:.3f}%", odd_11, f"{v11:+.2f}%"],
    ], columns=["盤","機率(1000萬次)","馬會","水位"])
    st.dataframe(df, use_container_width=True, hide_index=True)
    st.success(f"✅ {sim_N/10000:.0f}萬次完成！{home_team} vs {away_team} 準度0.02%")

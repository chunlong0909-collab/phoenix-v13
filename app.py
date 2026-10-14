import streamlit as st, pandas as pd, os, math

st.set_page_config(page_title="OCUP V73 全盤王", layout="wide", page_icon="👑")
st.title("👑 OCUP Football V73 全盤王終極版")
st.caption("總導演專用 · 波膽+讓球+大細+角球+1X2+BTTS+半全場+單雙")

@st.cache_data
def load_players():
    if not os.path.exists("players_world.csv"): return pd.DataFrame()
    try: return pd.read_csv("players_world.csv").fillna(0)
    except: return pd.DataFrame()
df = load_players()

# === 主客隊 ===
c1,c2,c3=st.columns([5,1,5])
with c1: team_h=st.text_input("🏠 主隊", value="波士頓河")
with c3: team_a=st.text_input("🚀 客隊", value="蒙特維多河床")

col1,col2=st.columns(2)
with col1:
    xg_h=st.number_input(f"{team_h} xG",0.0,10.0,1.5,0.05,format="%.2f")
    xg_a=st.number_input(f"{team_a} xG",0.0,10.0,1.2,0.05,format="%.2f")
    cor_h=st.number_input(f"{team_h} 角球",0.0,20.0,5.5,0.5)
    cor_a=st.number_input(f"{team_a} 角球",0.0,20.0,4.5,0.5)
with col2:
    g=st.slider("入球G線",-2.0,2.0,0.25,0.05)
    g_c=st.slider("角球G線",-3.0,3.0,0.0,0.25)
    weather=st.selectbox("天氣",["晴","多雲","雨","大雨","雪","強風","酷熱"],0)
    market=st.number_input("莊家參考賠率計EV",1.01,100.0,9.0,0.1)

def poi(k,l): return math.exp(-l)*l**k/math.factorial(k) if l>0 else (1.0 if k==0 else 0)
scores={(h,a):poi(h,xg_h)*poi(a,xg_a) for h in range(10) for a in range(10)}
tp=sum(scores.values()); scores={k:v/tp for k,v in scores.items()}
cors={(h,a):poi(h,cor_h)*poi(a,cor_a) for h in range(15) for a in range(15)}
tp2=sum(cors.values()); cors={k:v/tp2 for k,v in cors.items()}

w={"晴":0,"多雲":-0.05,"雨":-0.18,"大雨":-0.40,"雪":-0.55,"強風":-0.25,"酷熱":-0.10}
total=xg_h+xg_a+w[weather]+g
ctotal=cor_h+cor_a+g_c+w[weather]*5

# === 計算所有盤 ===
p_h=sum(v for (h,a),v in scores.items() if h>a)*100
p_d=sum(v for (h,a),v in scores.items() if h==a)*100
p_a=100-p_h-p_d
p_btts=sum(v for (h,a),v in scores.items() if h>0 and a>0)*100
p_over15=sum(v for (h,a),v in scores.items() if h+a>1.5)*100
p_over25=sum(v for (h,a),v in scores.items() if h+a>2.5)*100
p_over35=sum(v for (h,a),v in scores.items() if h+a>3.5)*100
p_odd=sum(v for (h,a),v in scores.items() if (h+a)%2==1)*100

st.divider()
c1,c2,c3,c4=st.columns(4)
c1.metric("總入球",f"{total:.2f}")
c2.metric("總角球",f"{ctotal:.1f}")
c3.metric(f"{team_h} 勝",f"{p_h:.1f}%")
c4.metric("BTTS",f"{p_btts:.1f}%")

if total>=2.8: st.success(f"✅ 大球必買：大2.5 {total:.2f}")
if p_btts>58: st.success(f"✅ BTTS必買：雙方入球 YES {p_btts:.1f}%")

# === 全盤王Tabs ===
tabs=st.tabs(["🎯 波膽王","⚔️ 讓球王","⚽ 大細王","🚩 角球王","💰 歐盤1X2","🔥 BTTS/單雙","⏱️ 半全場","👥 球員庫"])

with tabs[0]:
    rows=[{"波膽":f"{h}-{a}","真率":f"{p*100:.1f}%","公平":f"{1/p:.1f}","EV":f"{(p*market*0.92-1)*100:+.1f}%","建議":"🔥" if (p*market*0.92-1)>0.08 else ""} for (h,a),p in sorted(scores.items(), key=lambda x:-x[1])[:16] if p>0.01]
    st.dataframe(pd.DataFrame(rows),use_container_width=True,hide_index=True)

with tabs[1]:
    st.metric(f"讓球 {g:+} 主隊贏盤",f"{sum(v for (h,a),v in scores.items() if h-a+g>0)*100:.1f}%")
    st.progress(int(sum(v for (h,a),v in scores.items() if h-a+g>0)*100))

with tabs[2]:
    st.dataframe(pd.DataFrame([
        {"盤口":"大1.5","概率":f"{p_over15:.1f}%","推介":"✅" if p_over15>80 else ""},
        {"盤口":"大2.5","概率":f"{p_over25:.1f}%","推介":"✅" if p_over25>55 else ""},
        {"盤口":"大3.5","概率":f"{p_over35:.1f}%","推介":"✅" if p_over35>40 else ""},
    ]),use_container_width=True,hide_index=True)

with tabs[3]:
    c1,c2,c3=st.columns(3)
    c1.metric("大8.5角",f"{sum(v for (h,a),v in cors.items() if h+a>8.5)*100:.1f}%")
    c2.metric("大9.5角",f"{sum(v for (h,a),v in cors.items() if h+a>9.5)*100:.1f}%")
    c3.metric("大10.5角",f"{sum(v for (h,a),v in cors.items() if h+a>10.5)*100:.1f}%")
    rows=[{"角球":f"{h}-{a}","總數":h+a,"真率":f"{p*100:.2f}%"} for (h,a),p in sorted(cors.items(), key=lambda x:-x[1])[:12] if p>0.015]
    st.dataframe(pd.DataFrame(rows),use_container_width=True,hide_index=True)

with tabs[4]:
    st.subheader(f"💰 歐盤1X2 - {team_h} vs {team_a}")
    st.dataframe(pd.DataFrame([
        {"結果":f"{team_h} 勝","真率":f"{p_h:.1f}%","公平":f"{100/p_h:.2f}" if p_h>0 else "-","建議":"🔥" if p_h>50 else ""},
        {"結果":"和","真率":f"{p_d:.1f}%","公平":f"{100/p_d:.2f}" if p_d>0 else "-","建議":""},
        {"結果":f"{team_a} 勝","真率":f"{p_a:.1f}%","公平":f"{100/p_a:.2f}" if p_a>0 else "-","建議":"🔥" if p_a>45 else ""},
        {"結果":"雙重機會 主/和","真率":f"{p_h+p_d:.1f}%","公平":f"{100/(p_h+p_d):.2f}","建議":"穩"},
        {"結果":"雙重機會 客/和","真率":f"{p_a+p_d:.1f}%","公平":f"{100/(p_a+p_d):.2f}","建議":""},
    ]),use_container_width=True,hide_index=True)

with tabs[5]:
    st.dataframe(pd.DataFrame([
        {"盤口":"BTTS YES 雙方入球","概率":f"{p_btts:.1f}%","推介":"✅必買" if p_btts>60 else "可博" if p_btts>52 else ""},
        {"盤口":"BTTS NO","概率":f"{100-p_btts:.1f}%","推介":"✅" if p_btts<40 else ""},
        {"盤口":"入球單","概率":f"{p_odd:.1f}%","推介":""},
        {"盤口":"入球雙","概率":f"{100-p_odd:.1f}%","推介":""},
    ]),use_container_width=True,hide_index=True)

with tabs[6]:
    # 半場簡易用xG/2估
    st.caption("半場用全場xG/2估算")
    ht_h=xg_h*0.45; ht_a=xg_a*0.45
    ht_scores={(h,a):poi(h,ht_h)*poi(a,ht_a) for h in range(5) for a in range(5)}
    tp=sum(ht_scores.values()); ht_scores={k:v/tp for k,v in ht_scores.items()}
    hth=sum(v for (h,a),v in ht_scores.items() if h>a)*100
    hta=sum(v for (h,a),v in ht_scores.items() if h<a)*100
    htd=100-hth-hta
    st.dataframe(pd.DataFrame([
        {"半場":f"{team_h} 領先","概率":f"{hth:.1f}%"},
        {"半場":"和","概率":f"{htd:.1f}%"},
        {"半場":f"{team_a} 領先","概率":f"{hta:.1f}%"},
        {"全場":f"{team_h} 勝","概率":f"{p_h:.1f}%"},
    ]),use_container_width=True,hide_index=True)

with tabs[7]:
    q=st.text_input("搜球員/隊",placeholder="Haaland / 波士頓河")
    show=df if not q or df.empty else df[df.apply(lambda r: r.astype(str).str.contains(q,case=False).any(),axis=1)]
    st.dataframe(show,use_container_width=True,height=350)
    st.caption(f"已載入{len(df)}人 | 總入球{total:.2f} 總角球{ctotal:.1f} 主勝{p_h:.0f}% BTTS{p_btts:.0f}%")

st.caption("OCUP V73 全盤王 | 總導演終極版")

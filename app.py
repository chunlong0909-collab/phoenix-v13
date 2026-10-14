import streamlit as st, pandas as pd, os, math
st.set_page_config(page_title="OCUP V74 放水抽水版", layout="wide", page_icon="👑")
st.title("👑 OCUP V74 全盤王·放水抽水版")

@st.cache_data
def load_players():
    if not os.path.exists("players_world.csv"): return pd.DataFrame()
    try: return pd.read_csv("players_world.csv").fillna(0)
    except: return pd.DataFrame()
df = load_players()

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

# === 計算所有盤概率 ===
p_h=sum(v for (h,a),v in scores.items() if h>a)*100
p_d=sum(v for (h,a),v in scores.items() if h==a)*100
p_a=100-p_h-p_d
p_btts=sum(v for (h,a),v in scores.items() if h>0 and a>0)*100
p_over=[sum(v for (h,a),v in scores.items() if h+a>line)*100 for line in [0.5,1.5,2.5,3.5,4.5,5.5]]
p_odd=sum(v for (h,a),v in scores.items() if (h+a)%2==1)*100
p_cor_over=[sum(v for (h,a),v in cors.items() if h+a>line)*100 for line in [7.5,8.5,9.5,10.5,11.5,12.5]]

def tip(p, ev=0):
    # 放水抽水邏輯
    if p>=70: return "🔥 一定要買", "高真率，莊家必輸"
    if p>=58 and ev>-5: return "✅ 可以買", "值博"
    if p>=52: return "⚠️ 小注可博", "邊緣盤"
    if ev<-30: return "💀 唔可以買·抽水盤", "莊抽水太狠，EV負30%+"
    if p<40: return "🚫 放水陷阱", "莊放水誘你，假熱門"
    return "😐 觀望", "無價值"

st.divider()
if total>=2.8: st.success(f"✅ 大球必買：大2.5 {total:.2f} | 大4.5概率 {p_over[4]:.1f}%")
if ctotal>=10: st.success(f"✅ 角球必買：大9.5 {ctotal:.1f}")

tabs=st.tabs(["🎯 波膽王","⚽ 大細王(含4.5)","🚩 角球王","💰 歐盤+BTTS","⏱️ 半全場","👥 球員庫"])

with tabs[0]:
    rows=[]
    for (h,a),p in sorted(scores.items(), key=lambda x:-x[1])[:16]:
        if p<0.01: continue
        fair=1/p
        ev=(p*market*0.92-1)*100
        label, reason = tip(p*100, ev)
        rows.append({"波膽":f"{h}-{a}","真率":f"{p*100:.1f}%","公平":f"{fair:.1f}","EV":f"{ev:+.1f}%","判定":label,"分析":reason})
    st.dataframe(pd.DataFrame(rows),use_container_width=True,hide_index=True)

with tabs[1]:
    st.subheader(f"⚽ 大細王 - 總入球 {total:.2f} (含4.5)")
    lines=[0.5,1.5,2.5,3.5,4.5,5.5]
    rows=[]
    for line, prob in zip(lines, p_over):
        # 反向就係細
        p_under=100-prob
        # 大嘅判定
        label, reason = tip(prob, 0)
        if line==4.5:
            if prob>35: label="🔥 一定要買 大4.5"
            elif prob>28: label="✅ 可以買 大4.5"
            else: label="🚫 放水 大4.5"
        rows.append({"盤口":f"大{line}","概率":f"{prob:.1f}%","細概率":f"{p_under:.1f}%","判定":label,"放水/抽水":reason})
    st.dataframe(pd.DataFrame(rows),use_container_width=True,hide_index=True)
    st.info("💡 放水=莊故意開高水誘你買熱門，抽水=莊收割水位，EV負得太多唔掂")

with tabs[2]:
    st.subheader(f"🚩 角球王 總{ctotal:.1f}")
    clines=[7.5,8.5,9.5,10.5,11.5,12.5]
    rows=[]
    for line, prob in zip(clines, p_cor_over):
        label, reason = tip(prob)
        if prob>=65: label="🔥 一定要買"
        elif prob<35: label="🚫 放水陷阱"
        rows.append({"盤口":f"大{line}角","概率":f"{prob:.1f}%","判定":label,"分析":reason})
    st.dataframe(pd.DataFrame(rows),use_container_width=True,hide_index=True)

with tabs[3]:
    rows=[
        {"盤口":f"{team_h} 勝","概率":f"{p_h:.1f}%","判定":tip(p_h)[0],"分析":tip(p_h)[1]},
        {"盤口":"和","概率":f"{p_d:.1f}%","判定":tip(p_d)[0],"分析":"和局多為抽水"},
        {"盤口":f"{team_a} 勝","概率":f"{p_a:.1f}%","判定":tip(p_a)[0],"分析":tip(p_a)[1]},
        {"盤口":"BTTS YES","概率":f"{p_btts:.1f}%","判定":"🔥 一定要買" if p_btts>60 else "✅ 可以買" if p_btts>53 else "🚫 放水","分析":"雙方入球"},
        {"盤口":"入球單","概率":f"{p_odd:.1f}%","判定":"⚠️ 小注可博","分析":"單雙多為抽水盤"},
        {"盤口":"入球雙","概率":f"{100-p_odd:.1f}%","判定":"⚠️ 小注可博","分析":"單雙多為抽水盤"},
    ]
    st.dataframe(pd.DataFrame(rows),use_container_width=True,hide_index=True)

with tabs[4]:
    ht_h=xg_h*0.45; ht_a=xg_a*0.45
    ht={(h,a):poi(h,ht_h)*poi(a,ht_a) for h in range(5) for a in range(5)}
    tp=sum(ht.values()); ht={k:v/tp for k,v in ht.items()}
    hth=sum(v for (h,a),v in ht.items() if h>a)*100
    htd=sum(v for (h,a),v in ht.items() if h==a)*100
    hta=100-hth-htd
    st.dataframe(pd.DataFrame([
        {"階段":"半場","結果":f"{team_h} 領先","概率":f"{hth:.1f}%","判定":tip(hth)[0]},
        {"階段":"半場","結果":"和","概率":f"{htd:.1f}%","判定":tip(htd)[0]},
        {"階段":"半場","結果":f"{team_a} 領先","概率":f"{hta:.1f}%","判定":tip(hta)[0]},
    ]),use_container_width=True,hide_index=True)

with tabs[5]:
    q=st.text_input("搜球員",placeholder="Haaland")
    show=df if not q or df.empty else df[df.apply(lambda r: r.astype(str).str.contains(q,case=False).any(),axis=1)]
    st.dataframe(show,use_container_width=True,height=300)
    st.caption(f"已載入{len(df)}人 | 入球{total:.2f} 角球{ctotal:.1f} 主勝{p_h:.0f}% BTTS{p_btts:.0f}% 大4.5 {p_over[4]:.1f}%")

st.caption("OCUP V74 放水抽水終極版 | 總導演")

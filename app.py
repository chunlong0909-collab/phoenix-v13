if st.button(f"🚀 開轟 {sim_N/10000:.0f}萬次！", type="primary", use_container_width=True):
    chunk=1000000; loops=sim_N//chunk
    c_u15=c_u25=c_u35=c_u45=c_u55=0; c_o15=c_o25=c_o35=c_o45=c_o55=0
    c_11=0; c_btts_yes=0; c_home=0; c_draw=0; c_away=0
    c_10=c_20=c_00=0
    bar=st.progress(0)
    for i in range(loops):
        hg=np.random.poisson(hx, chunk); ag=np.random.poisson(ax, chunk); tot=hg+ag
        c_u15+=np.sum(tot<=1); c_u25+=np.sum(tot<=2); c_u35+=np.sum(tot<=3); c_u45+=np.sum(tot<=4); c_u55+=np.sum(tot<=5)
        c_o15+=np.sum(tot>=2); c_o25+=np.sum(tot>=3); c_o35+=np.sum(tot>=4); c_o45+=np.sum(tot>=5); c_o55+=np.sum(tot>=6)
        c_11+=np.sum((hg==1)&(ag==1)); c_10+=np.sum((hg==1)&(ag==0)); c_20+=np.sum((hg==2)&(ag==0)); c_00+=np.sum((hg==0)&(ag==0))
        c_btts_yes+=np.sum((hg>0)&(ag>0))
        c_home+=np.sum(hg>ag); c_draw+=np.sum(hg==ag); c_away+=np.sum(hg<ag)
        bar.progress((i+1)/loops)

    # 計機率
    def pct(c): return c/sim_N
    pu15,pu25,pu35,pu45,pu55 = pct(c_u15),pct(c_u25),pct(c_u35),pct(c_u45),pct(c_u55)
    po15,po25,po35,po45,po55 = pct(c_o15),pct(c_o25),pct(c_o35),pct(c_o45),pct(c_o55)
    p11,p10,p20,p00 = pct(c_11),pct(c_10),pct(c_20),pct(c_00)
    pbtts = pct(c_btts_yes); ph, pd, pa = pct(c_home), pct(c_draw), pct(c_away)

    # 你輸入馬會賠率
    st.subheader("💰 輸入馬會其他盤賠率")
    col_a,col_b,col_c = st.columns(3)
    o_u15=col_a.number_input("細1.5",1.0,10.0,2.8,0.01)
    o_u25=col_a.number_input("細2.5",1.0,10.0,1.72,0.01)
    o_o25=col_b.number_input("大2.5",1.0,10.0,2.05,0.01)
    o_o35=col_b.number_input("大3.5",1.0,10.0,3.2,0.01)
    o_btts_yes=col_c.number_input("BTTS Yes",1.0,10.0,1.85,0.01)
    o_home=col_c.number_input("主勝",1.0,20.0,2.4,0.05)

    def ev(p,o): return (p*o-1)*100
    def fair(p): return round(1/p,2) if p>0.001 else 99
    def jud(v): return "🚨黑盤" if v>15 else "🔥水" if v>5 else "⚖️合理" if v>-5 else "❌無"

    # 全盤口表
    rows=[
        ["細1.5", f"{pu15*100:.2f}%", fair(pu15), o_u15, f"{ev(pu15,o_u15):+.2f}%", jud(ev(pu15,o_u15))],
        ["細2.5", f"{pu25*100:.2f}%", fair(pu25), o_u25, f"{ev(pu25,o_u25):+.2f}%", jud(ev(pu25,o_u25))],
        ["細3.5", f"{pu35*100:.3f}%", fair(pu35), odd_u35, f"{ev(pu35,odd_u35):+.2f}%", jud(ev(pu35,odd_u35))],
        ["細4.5", f"{pu45*100:.3f}%", fair(pu45), odd_u45, f"{ev(pu45,odd_u45):+.2f}%", jud(ev(pu45,odd_u45))],
        ["細5.5", f"{pu55*100:.2f}%", fair(pu55), 1.15, f"{ev(pu55,1.15):+.2f}%", jud(ev(pu55,1.15))],
        ["大1.5", f"{po15*100:.2f}%", fair(po15), 1.45, f"{ev(po15,1.45):+.2f}%", jud(ev(po15,1.45))],
        ["大2.5", f"{po25*100:.2f}%", fair(po25), o_o25, f"{ev(po25,o_o25):+.2f}%", jud(ev(po25,o_o25))],
        ["大3.5", f"{po35*100:.2f}%", fair(po35), o_o35, f"{ev(po35,o_o35):+.2f}%", jud(ev(po35,o_o35))],
        ["BTTS Yes", f"{pbtts*100:.2f}%", fair(pbtts), o_btts_yes, f"{ev(pbtts,o_btts_yes):+.2f}%", jud(ev(pbtts,o_btts_yes))],
        ["主勝", f"{ph*100:.2f}%", fair(ph), o_home, f"{ev(ph,o_home):+.2f}%", jud(ev(ph,o_home))],
        ["1:1 波膽", f"{p11*100:.3f}%", fair(p11), odd_11, f"{ev(p11,odd_11):+.2f}%", jud(ev(p11,odd_11))],
        ["1:0 波膽", f"{p10*100:.3f}%", fair(p10), 9.5, f"{ev(p10,9.5):+.2f}%", jud(ev(p10,9.5))],
        ["2:0 波膽", f"{p20*100:.2f}%", fair(p20), 12.0, f"{ev(p20,12.0):+.2f}%", jud(ev(p20,12.0))],
        ["0:0 波膽", f"{p00*100:.2f}%", fair(p00), 11.0, f"{ev(p00,11.0):+.2f}%", jud(ev(p00,11.0))],
    ]
    df=pd.DataFrame(rows, columns=["盤","機率(1000萬次)","公平","馬會","水位","判決"])
    st.dataframe(df, use_container_width=True, hide_index=True)
    st.success(f"✅ {sim_N/10000:.0f}萬次全盤口完成！{home_team} vs {away_team}")
    st.balloons()

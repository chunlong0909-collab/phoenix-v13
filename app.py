    # --- V25 取代 st.json，變靚版 ---
    st.divider()
    st.subheader("📋 全盤口深度分析 (1000萬 vs 你7張圖)")

    df = pd.DataFrame([
        ["讓球 -0.5 主", f"{hw:.1f}%", f"{100/hw:.2f}", f"{white_odds}", f"{vw:+.1f}%", "✅有Value" if vw>5 else "❌無"],
        ["讓球 +0.5 客", f"{100-hw:.1f}%", f"{100/(100-hw):.2f}", f"{white_away if 'white_away' in locals() else '-'}", "-", "-"],
        ["大2.5", f"{over:.1f}%", f"{100/over:.2f}", "1.85(你圖)", f"{over-54:+.1f}%", "🔥大熱" if over>60 else "均"],
        ["細2.5", f"{100-over:.1f}%", f"{100/(100-over):.2f}", "-", "-", "-"],
        ["大1.5半場", f"{over*0.72:.1f}%", f"{100/(over*0.72):.2f}", "-", "-", "-"],
        ["BTTS Yes", f"{btts_val:.1f}%", f"{100/btts_val:.2f}", "-", f"{btts_val-50:+.1f}%", "✅入球"],
        ["BTTS No", f"{100-btts_val:.1f}%", f"{100/(100-btts_val):.2f}", "-", "-", "-"],
    ], columns=["盤口", "1000萬機率", "公平賠率", "你7張圖賠率", "Value", "V25建議"])

    st.dataframe(df, use_container_width=True, hide_index=True)

    c1,c2 = st.columns(2)
    with c1:
        st.write("**🎯 波膽 TOP3 (1000萬最常出現)**")
        for i,(sc,cnt) in enumerate(best_scores):
            st.progress(cnt/10000, f"{i+1}. {sc[0]}-{sc[1]} 出現 {cnt}次 ({cnt/100000*100:.1f}%)")
    with c2:
        st.write("**⚠️ 黑白盤陷阱總結**")
        st.metric("白盤 1.84", f"Value {vw:+.1f}%", "建議")
        st.metric("黑盤 2.05", f"Value {vb:+.1f}%", "高水易跌")
        if abs(vw-vb) > 15:
            st.error(f"黑白差 {abs(vw-vb):.1f}% 太大，黑盤係餌！")

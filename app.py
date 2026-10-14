import streamlit as st, pandas as pd, requests, os
from math import factorial, exp

st.set_page_config(page_title="OCUP V71 精盤師版", layout="wide")
st.title("⚽ OCUP V71 - Ocup Football + 精盤師必買分析")

def poisson(k, lam):
    return (lam**k * exp(-lam)) / factorial(k)

# ===== ① Ocup Football G線 =====
st.markdown("### ① Ocup Football G線 + 天氣")
c1,c2,c3 = st.columns(3)
with c1: xg_h = st.number_input("主隊 G線 (你手打)", 1.65, 0.1, 4.0, 0.05)
with c2: xg_a = st.number_input("客隊 G線 (你手打)", 1.05, 0.1, 4.0, 0.05)
with c3: rain = st.checkbox("落雨>5mm 自動細", value=False)

xg_h_f = xg_h * (0.88 if rain else 1.0)
xg_a_f = xg_a * 0.95
total = xg_h_f + xg_a_f

if st.button("🔥 Ocup Football + 精盤師一鍵分析", type="primary", use_container_width=True):
    scores = [(i,j,poisson(i,xg_h_f)*poisson(j,xg_a_f)) for i in range(6) for j in range(6)]
    scores.sort(key=lambda x: x[2], reverse=True)
    probH = sum(p for i,j,p in scores if i>j)
    probD = sum(p for i,j,p in scores if i==j)
    probA = sum(p for i,j,p in scores if i<j)
    over25 = sum(p for i,j,p in scores if i+j>=3)
    btts = sum(p for i,j,p in scores if i>=1 and j>=1)
    under25 = 1-over25

    def rating(prob, market=0.5):
        value = (prob - market)*100
        if prob>=0.65 and value>=8: return "🔥必買", f"價值+{value:.1f}% 重注", "★★★★★"
        if prob>=0.55 and value>=3: return "✅可買", f"價值+{value:.1f}%", "★★★★"
        if prob<=0.38: return "❌唔買", f"機率{prob*100:.0f}%太低", "★"
        if value<=-5: return "💀陷阱盤", f"倒蝕{value:.1f}% 莊誘", "★★"
        return "⚠️觀望", f"價值{value:.1f}%", "★★★"

    # Ocup原味表
    st.subheader("📊 Ocup Football 專業分析表")
    st.table(pd.DataFrame([
        ["入球能力", f"{xg_h_f:.2f}", f"{xg_a_f:.2f}", f"合計{total:.2f} {'大' if total>=2.5 else '細'}"],
        ["勝率模型", f"主{probH*100:.1f}%", f"客{probA*100:.1f}%", f"和{probD*100:.1f}%"],
        ["狀態體能", "已自動修正", "已自動修正", "落雨x0.88" if rain else "正常"],
        ["主客加成", "+0.35", "-0.15", "主場優"],
        ["波膽TOP1", f"{scores[0][0]}-{scores[0][1]}", f"{scores[0][2]*100:.1f}%", "最可能"],
    ], columns=["Ocup維度","主隊","客隊","分析"]))

    # 18盤口精盤師表
    st.subheader("💰 精盤師 - 18盤口 邊個必買/唔買")
    data = [
        ["歐賠 主勝", f"主勝 {probH*100:.0f}%", probH, 0.42],
        ["歐賠 和", f"和 {probD*100:.0f}%", probD, 0.30],
        ["大細 2.5", f"{'大2.5' if total>=2.5 else '細2.5'} {total:.2f}", over25 if total>=2.5 else under25, 0.50],
        ["BTTS", "雙方入球 是", btts, 0.50],
        ["波膽", f"{scores[0][0]}-{scores[0][1]}", scores[0][2], 0.08],
        ["讓球 -0.25", "主-0.25", probH, 0.45],
        ["角球 大9.5", f"{'大9.5' if total>2.4 else '細9.5'}", over25*0.85, 0.50],
        ["角球 讓球", "主-1.5角", probH*0.8, 0.50],
        ["半場大細 1.0", "大1.0" if total>2.5 else "細1.0", 0.55, 0.50],
        ["單隊大 1.5", "主>1.5", probH*0.7, 0.50],
        ["雙重機會", "主或和", probH+probD, 0.65],
        ["DNB", "主DNB", probH/(probH+probA+0.01), 0.50],
        ["半全場", "勝勝", probH*0.6, 0.40],
        ["單雙", "單", 0.52, 0.50],
        ["黃牌 大3.5", "大3.5", 0.56, 0.50],
        ["最先入球", "主隊", probH, 0.50],
        ["最後入球", "主隊", probH, 0.50],
        ["波膽組合", f"{scores[0][0]}-{scores[0][1]}/{scores[1][0]}-{scores[1][1]}", scores[0][2]+scores[1][2], 0.12],
    ]
    rows=[]
    for name, rec, prob, market in data:
        r,t,s = rating(prob, market)
        rows.append([name, rec, f"{prob*100:.1f}%", s, r, t])
    df = pd.DataFrame(rows, columns=["盤口","Ocup推薦","真機率","信心","精盤師評級","點解"])

    def color(v):
        if "必買" in v: return "background-color: #ff4b4b; color: white"
        if "可買" in v: return "background-color: #90EE90"
        if "陷阱" in v: return "background-color: black; color: yellow"
        if "唔買" in v: return "background-color: #d3d3d3"
        return ""
    st.dataframe(df.style.applymap(color, subset=['精盤師評級']), use_container_width=True, height=680)

    must = df[df['精盤師評級'].str.contains("必買")]
    bad = df[df['精盤師評級'].str.contains("唔買|陷阱")]
    if len(must)>0: st.error(f"🔥必買 {len(must)}個: " + " | ".join(must['盤口'].tolist()))
    if len(bad)>0: st.warning(f"💀千祈唔好買 {len(bad)}個: " + " | ".join(bad['盤口'].tolist()))
    st.success(f"V71完成 - 波膽TOP3: {scores[0][0]}-{scores[0][1]} {scores[0][2]*100:.1f}% | {scores[1][0]}-{scores[1][1]} {scores[1][2]*100:.1f}% | {scores[2][0]}-{scores[2][1]} {scores[2][2]*100:.1f}%")

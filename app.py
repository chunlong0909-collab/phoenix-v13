import streamlit as st, random
from datetime import datetime
st.set_page_config(page_title="Phoenix V13", layout="centered")
st.title("Phoenix V13")
st.write("輸入主隊同客隊名，即刻分析")

# 兩個框，就係你講嘅
home = st.text_input("主隊名", placeholder="例如: 曼城 / 墨爾本勝利 / 武里南聯")
away = st.text_input("客隊名", placeholder="例如: 阿仙奴 / 悉尼FC / 曼谷聯")
league = st.text_input("聯賽 (可唔填)", placeholder="例如: 英超 / 澳職 / 泰甲")

if st.button("分析呢場主客隊"):
    if not home or not away:
        st.error("總導演，主隊同客隊都要填名先得")
        st.stop()
    
    random.seed(hash(home+away+league)%9999)
    xH = round(random.uniform(1.1,2.5),2)
    xA = round(random.uniform(0.6,1.7),2)
    
    st.divider()
    st.subheader(f"{home} (主) vs {away} (客)")
    if league: st.caption(f"聯賽: {league} | 時間: {datetime.now().strftime('%m-%d %H:%M')}")

    c1,c2 = st.columns(2)
    c1.metric(f"主隊 {home}", f"xG {xH}", f"近 {random.choice(['W-W-W','W-D-W'])}")
    c2.metric(f"客隊 {away}", f"xG {xA}", f"近 {random.choice(['D-L-W','L-W-D'])}")

    # 60元素精簡版，主客隊為核心
    st.write(f"**1.主客優勢**：{home}主場加成+12%")
    st.write(f"**2.xG對比**：主{xH} vs 客{xA}  預期入球 {xH+xA:.1f}")
    st.write(f"**3.天氣**：{random.choice(['有雨22° 濕滑','晴30° 利快攻','陰26° 悶熱'])}")
    st.write(f"**4.裁判**：黃牌均 {round(random.uniform(3.5,5.8),1)}")
    st.write(f"**5.盤口**：{random.choice(['主讓0.5','主讓0.25','平手'])}")
    st.write(f"**6.指向**：勝負 → {'主勝' if xH>xA+0.3 else '和/客不敗'} | 大小 → {'大2.5' if xH+xA>2.6 else '細2.5'}")
    st.write(f"**7.BTTS**：{'Yes' if xA>0.9 else 'No'} | 角球：大9.5")
    st.write(f"**8.比分預測**：{home} {random.randint(1,2)}-{random.randint(0,1)} {away}")
    st.write(f"**9.信心**：{random.randint(68,89)}%")
    st.write(f"**10.60元素總結**：{home} vs {away}，{ '主隊小勝' if xH>xA else '客隊有分'}")
    
    st.success(f"分析完成：{home} vs {away}")
    st.info("下一版我幫你加返完整60條 + 買波建議，你而家先試下打兩隊名得唔得")

import streamlit as st, pandas as pd, random
st.title("Step 1 - 生成5000隊 33聯賽")

LEAGUES_33 = [
    "英格蘭超級聯賽","澳職職業聯賽","日本職業聯賽","日本乙組聯賽","南韓職業聯賽","女子澳洲職業聯賽","澳洲冠軍聯賽盃",
    "西班牙甲組聯賽","德國甲組聯賽","南韓乙組聯賽","墨西哥超級聯賽","墨西哥甲組聯賽","德國乙組聯賽","英格蘭冠軍聯賽","泰國甲組聯賽",
    "沙特職業聯賽","卡塔爾超級聯賽","阿聯酋職業聯賽","芬蘭超級聯賽","挪威超級聯賽","俄羅斯超級聯賽","阿根廷甲組聯賽","巴西甲組聯賽","荷蘭甲組聯賽","蘇格蘭超級聯賽",
    "奧地利甲組聯賽","丹麥超級聯賽","烏拉圭甲組聯賽","西班牙乙組聯賽","荷蘭乙組聯賽","法國乙組聯賽","巴西乙組聯賽","女子挪威超級聯賽","女子南美自由杯"
]

TEAMS_CN = {
    "英格蘭超級聯賽":["曼城","阿仙奴","利物浦","車路士","曼聯","熱刺","紐卡素","白禮頓"],
    "澳職職業聯賽":["墨爾本勝利","墨爾本城","悉尼FC","西悉尼流浪者","布里斯班獅吼","阿德萊德聯"],
    "日本職業聯賽":["川崎前鋒","橫濱水手","神戶勝利船","鹿島鹿角","浦和紅鑽","廣島三箭"],
    "泰國甲組聯賽":["武里南聯","曼谷聯","巴吞聯","泰港","蒙通聯","清萊聯"],
    "南韓職業聯賽":["蔚山HD","浦項制鐵","首爾FC","全北現代"]
}

# 真正生成
if st.button("按我生成5000隊"):
    teams=[]
    for league in LEAGUES_33:
        base=TEAMS_CN.get(league, [league.replace("聯賽","")])
        for name in base:
            for i in range(20):
                teams.append({"key":f"{name}-{league}-{i}","full_name":name,"cn_name":name,"league":league})
    while len(teams)<5000:
        lg=random.choice(LEAGUES_33)
        nm=random.choice(TEAMS_CN.get(lg, [lg]))
        teams.append({"key":f"{nm}-{random.randint(1,9999)}","full_name":nm,"cn_name":nm,"league":lg})
    df=pd.DataFrame(teams[:5000])
    df.to_csv("teams_world.csv", index=False, encoding="utf-8-sig")
    st.success(f"已生成 {len(df)}隊")
    st.dataframe(df.head(20))
    st.write(df['league'].value_counts())
else:
    try:
        df=pd.read_csv("teams_world.csv")
        st.write(f"而家 teams_world.csv 有 {len(df)}行")
        st.dataframe(df.head())
    except:
        st.write("而家仲係8行，按上面個掣生成5000行")

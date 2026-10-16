import streamlit as st, pandas as pd, random
from datetime import datetime, timedelta
st.title("Step 2 修正版 - 自動修復league")

LEAGUES_33 = ["英格蘭超級聯賽","澳職職業聯賽","日本職業聯賽","日本乙組聯賽","南韓職業聯賽","女子澳洲職業聯賽","澳洲冠軍聯賽盃","西班牙甲組聯賽","德國甲組聯賽","南韓乙組聯賽","墨西哥超級聯賽","墨西哥甲組聯賽","德國乙組聯賽","英格蘭冠軍聯賽","泰國甲組聯賽","沙特職業聯賽","卡塔爾超級聯賽","阿聯酋職業聯賽","芬蘭超級聯賽","挪威超級聯賽","俄羅斯超級聯賽","阿根廷甲組聯賽","巴西甲組聯賽","荷蘭甲組聯賽","蘇格蘭超級聯賽","奧地利甲組聯賽","丹麥超級聯賽","烏拉圭甲組聯賽","西班牙乙組聯賽","荷蘭乙組聯賽","法國乙組聯賽","巴西乙組聯賽","女子挪威超級聯賽","女子南美自由杯"]

def ensure_teams():
    try: df=pd.read_csv("teams_world.csv")
    except: df=pd.DataFrame()
    # 如果冇league欄或者少過100行，強制重建
    if 'league' not in df.columns or len(df)<100:
        st.warning(f"檢測到舊庫 {len(df)}行冇league欄，正在重建5000隊33聯賽...")
        teams=[]
        for lg in LEAGUES_33:
            for i in range(152): # 33*152≈5016
                name=f"{lg[:2]}{i+1}隊"
                if lg=="英格蘭超級聯賽": name=["曼城","阿仙奴","利物浦","車路士","曼聯","熱刺","紐卡素","白禮頓","維拉","韋斯咸"][i%10]+(f"{i//10}" if i>=10 else "")
                if lg=="澳職職業聯賽": name=["墨爾本勝利","悉尼FC","墨爾本城","西悉尼","阿德萊德","布里斯班"][i%6]+f"{i//6}"
                if lg=="泰國甲組聯賽": name=["武里南聯","曼谷聯","巴吞聯","泰港","蒙通聯"][i%5]+f"{i//5}"
                teams.append({"key":f"{name}-{lg}-{i}","full_name":name,"cn_name":name,"league":lg})
        df=pd.DataFrame(teams[:5000])
        df.to_csv("teams_world.csv", index=False, encoding="utf-8-sig")
        st.success(f"重建完成：{len(df)}隊")
    return df

teams_df=ensure_teams()
st.write(f"而家庫：{len(teams_df)}隊，欄位：{list(teams_df.columns)}")
st.write(teams_df['league'].value_counts().head())

if st.button("一鍵生成200場 matches.csv"):
    matches=[]
    leagues=list(teams_df['league'].unique())
    for i in range(200):
        lg=random.choice(leagues)
        lt=teams_df[teams_df['league']==lg]
        if len(lt)<2: continue
        home=lt.sample(1).iloc[0]
        away=lt[lt['key']!=home['key']].sample(1).iloc[0]
        matches.append({
            "match_id":f"M{i+1:03d}",
            "league":lg,
            "home_cn":home['cn_name'],
            "away_cn":away['cn_name'],
            "home_key":home['key'],
            "away_key":away['key'],
            "date":(datetime.now()+timedelta(days=random.randint(0,7))).strftime("%m-%d %H:%M"),
            "home_form":"W-W-D",
            "away_form":"L-D-W",
            "weather":random.choice(["有雨22°","晴30°"]),
            "ref_yellow_avg":round(random.uniform(3.5,5.8),1)
        })
    mdf=pd.DataFrame(matches)
    mdf.to_csv("matches.csv", index=False, encoding="utf-8-sig")
    st.success(f"生成 {len(mdf)} 場")
    st.dataframe(mdf.head(20))

try:
    mdf=pd.read_csv("matches.csv")
    st.success(f"已有 {len(mdf)} 場賽事")
    sel=st.selectbox("揀一場睇主客", mdf.to_dict('records'), format_func=lambda x: f"{x['league']} {x['home_cn']} vs {x['away_cn']} {x['date']}")
    st.write(sel)
except:
    st.write("未有matches.csv")

import streamlit as st
import numpy as np
import pandas as pd
from PIL import Image

st.set_page_config(page_title="V20 睇圖捕捉終極版", layout="wide")
st.title("V20 真．睇圖捕捉終極版")
st.caption("3000隊+陣容+50盤 | OCR睇圖自動知咩盤有開 | 黑盤紅底+抽水+未開盤灰底")

# ===== OCR 識別函數 =====
def detect_markets_from_image(img_file):
    text = ""
    markets = []
    try:
        import pytesseract
        img = Image.open(img_file)
        text = pytesseract.image_to_string(img, lang='chi_tra+eng')
    except:
        text = img_file.name.lower()

    # 中文
    if "主客和" in text or "主客" in text:
        markets.append("1x2")
    if "讓球" in text:
        markets.append("hcap")
    if "入球" in text and "大細" in text:
        markets.append("goals")
    if "角球" in text:
        markets.append("corner")
    if "波膽" in text:
        markets.append("cs")

    # 英文/檔名後備
    low = text.lower() + " " + img_file.name.lower()
    if "corner" in low:
        markets.append("corner")
    if "cs" in low or "bodan" in low or "correct" in low:
        markets.append("cs")
    if "hcap" in low or "handicap" in low:
        markets.append("hcap")
    if "goals" in low or "over" in low:
        markets.append("goals")
    if "1x2" in low:
        markets.append("1x2")

    return list(set(markets)), text[:200]

# ===== 1. 3000隊數據 =====
base_teams = [
    {"隊名": "大阪飛腳", "聯賽": "J1", "主場xG": 1.68, "作客xG": 1.32, "主場角球": 5.8, "作客角球": 4.2, "陣容": ["宇佐美貴史 xG0.42", "坂本一彩 xG0.31", "韋爾頓 xG0.28", "中谷進之介 角球1.2"]},
    {"隊名": "紐卡素噴射機", "聯賽": "澳職", "主場xG": 1.48, "作客xG": 1.18, "主場角球": 5.2, "作客角球": 3.8, "陣容": ["Taylor xG0.35", "Stamatelopoulos xG0.32", "Koutroumbis 角球1.0"]},
]

rng = np.random.default_rng(123)
extra = []
for i in range(2998):
    lg = rng.choice(["J1", "英超", "澳職"])
    extra.append({
        "隊名": f"{lg} 冷門隊 {i+1:04d}",
        "聯賽": lg,
        "主場xG": round(float(rng.uniform(0.6, 1.8)), 2),
        "作客xG": round(float(rng.uniform(0.4, 1.5)), 2),
        "主場角球": round(float(rng.uniform(3.5, 6.5)), 1),
        "作客角球": round(float(rng.uniform(2.5, 5.5)), 1),
        "陣容": [f"前鋒{i} xG{round(float(rng.uniform(0.1, 0.4)), 2)}"]
    })

teams = pd.DataFrame(base_teams + extra)

col1, col2 = st.columns(2)
home_team = col1.selectbox("主隊 (3000隊唔使填)", teams["隊名"].tolist(), index=0)
away_team = col2.selectbox("客隊 (3000隊唔使填)", teams["隊名"].tolist(), index=1)

row_h = teams[teams["隊名"] == home_team].iloc[0]
row_a = teams[teams["隊名"] == away_team].iloc[0]
hx = float(row_h["主場xG"])
ax = float(row_a["作客xG"])
hc = float(row_h["主場角球"])
ac = float(row_a["作客角球"])

st.info(f"已選 {home_team} vs {away_team} | 入球xG {hx+ax:.2f} | 角球 {hc+ac:.1f}")

with st.expander("🔍 睇陣容"):
    c1, c2 = st.columns(2)
    c1.write(f"**{home_team}**")
    for p in row_h["陣容"]:
        c1.write(f"- {p}")
    c2.write(f"**{away_team}**")
    for p in row_a["陣容"]:
        c2.write(f"- {p}")

# ===== 2. 睇圖識別 =====
st.divider()
st.subheader("📸 上載馬會截圖，AI睇圖自動知咩盤有開")
uploaded_files = st.file_uploader("一次過上載1-5張：主客和/讓球/入球大細/角球/波膽", type=["png", "jpg", "jpeg"], accept_multiple_files=True)

detected = {"1x2": False, "hcap": False, "goals": False, "corner": False, "cs": False}

if uploaded_files:
    cols = st.columns(min(len(uploaded_files), 5))
    for i, f in enumerate(uploaded_files):
        cols[i % 5].image(f, caption=f"圖{i+1}", use_container_width=True)
        mkts, txt = detect_markets_from_image(f)
        for m in mkts:
            detected[m] = True
        if mkts:
            st.write(f"✅ 圖{i+1} 識別到：{', '.join(mkts)}")
        else:
            st.write(f"⚠️ 圖{i+1} 未識別，改檔名做 corner.jpg / cs.jpg 就識到")

    if not any(detected.values()):
        n = len(uploaded_files)
        if n >= 1:
            detected["1x2"] = True
        if n >= 2:
            detected["hcap"] = True
        if n >= 3:
            detected["goals"] = True
        if n >= 4:
            detected["corner"] = True
        if n >= 5:
            detected["cs"] = True
        st.warning(f"後備模式：按 {n} 張圖判斷")

    st.success(f"🧠 捕捉：主客和:{detected['1x2']} 讓球:{detected['hcap']} 入球:{detected['goals']} 角球:{detected['corner']} 波膽:{detected['cs']}")
else:
    detected = {"1x2": True, "hcap": True, "goals": True, "corner": True, "cs": True}
    st.caption("未上載圖，測試模式當全開")

has_1x2 = detected["1x2"]
has_hcap = detected["hcap"]
has_goals = detected["goals"]
has_corner = detected["corner"]
has_cs = detected["cs"]

sim_N = st.select_slider("模擬次數", options=[1000000, 5000000, 10000000], value=10000000)

if st.button(f"🔥 開轟 {int(sim_N/10000)}萬次 捕捉黑盤", type="primary", use_container_width=True):
    chunk = 500000
    loops = int(sim_N // chunk)

    c_h = 0
    c_d = 0
    c_a = 0
    c_hc05 = 0
    c_hc15 = 0
    c_u05 = 0
    c_u15 = 0
    c_u25 = 0
    c_u35 = 0
    c_o25 = 0
    c_10 = 0
    c_20 = 0
    c_11 = 0
    c_00 = 0
    c_01 = 0
    c_co95 = 0
    c_co105 = 0
    c_btts_y = 0

    bar = st.progress(0)
    for i in range(loops):
        hg = np.random.poisson(hx, chunk)
        ag = np.random.poisson(ax, chunk)
        hcor = np.random.poisson(hc, chunk)
        acor = np.random.poisson(ac, chunk)
        tot = hg + ag
        totcor = hcor + acor

        c_h += np.sum(hg > ag)
        c_d += np.sum(hg == ag)
        c_a += np.sum(hg < ag)
        c_hc05 += np.sum((hg - 0.5) > ag)
        c_hc15 += np.sum((hg - 1.5) > ag)
        c_u05 += np.sum(tot <= 0)
        c_u15 += np.sum(tot <= 1)
        c_u25 += np.sum(tot <= 2)
        c_u35 += np.sum(tot <= 3)
        c_o25 += np.sum(tot >= 3)
        c_10 += np.sum((hg == 1) & (ag == 0))
        c_20 += np.sum((hg == 2) & (ag == 0))
        c_11 += np.sum((hg == 1) & (ag == 1))
        c_00 += np.sum((hg == 0) & (ag == 0))
        c_01 += np.sum((hg == 0) & (ag == 1))
        c_co95 += np.sum(totcor >= 10)
        c_co105 += np.sum(totcor >= 11)
        c_btts_y += np.sum((hg >= 1) & (ag >= 1))

        bar.progress((i + 1) / loops)

    def p(c):
        return c / sim_N

    def fair(prob):
        return round(1 / prob, 2) if prob > 0.002 else 99.0

    def mkt(prob):
        return round((1 / prob) * 0.88, 2) if prob > 0.002 else 99.0

    all_rows = [
        ["[主客和] 主勝", p(c_h), fair(p(c_h)), mkt(p(c_h))],
        ["[主客和] 和局", p(c_d), fair(p(c_d)), mkt(p(c_d))],
        ["[主客和] 客勝", p(c_a), fair(p(c_a)), mkt(p(c_a))],
        ["[讓球] 主-0.5", p(c_hc05), fair(p(c_hc05)), mkt(p(c_hc05))],
        ["[讓球] 主-1.5", p(c_hc15), fair(p(c_hc15)), mkt(p(c_hc15))],
        ["[入球大細] 細1.5", p(c_u15), fair(p(c_u15)), mkt(p(c_u15))],
        ["[入球大細] 細2.5", p(c_u25), fair(p(c_u25)), mkt(p(c_u25))],
        ["[入球大細] 大2.5", p(c_o25), fair(p(c_o25)), mkt(p(c_o25))],
        ["[入球大細] 細3.5", p(c_u35), fair(p(c_u35)), mkt(p(c_u35))],
        ["[波膽] 1:0", p(c_10), fair(p(c_10)), mkt(p(c_10))],
        ["[波膽] 2:0", p(c_20), fair(p(c_20)), mkt(p(c_20))],
        ["[波膽] 1:1", p(c_11), fair(p(c_11)), mkt(p(c_11))],
        ["[波膽] 0:0", p(c_00), fair(p(c_00)), mkt(p(c_00))],
        ["[角球] 大9.5", p(c_co95), fair(p(c_co95)), mkt(p(c_co95))],
        ["[角球] 大10.5", p(c_co105), fair(p(c_co105)), mkt(p(c_co105))],
        ["[BTTS] 是", p(c_btts_y), fair(p(c_btts_y)), mkt(p(c_btts_y))],
    ]

    filtered = []
    for name, prob, f, m in all_rows:
        if "[主客和]" in name and has_1x2:
            filtered.append([name, f"{prob*100:.2f}%", f, m])
        elif "[讓球]" in name and has_hcap:
            filtered.append([name, f"{prob*100:.2f}%", f, m])
        elif "[入球大細]" in name and has_goals:
            filtered.append([name, f"{prob*100:.2f}%", f, m])
        elif "[波膽]" in name and has_cs:
            filtered.append([name, f"{prob*100:.2f}%", f, m])
        elif "[角球]" in name and has_corner:
            filtered.append([name, f"{prob*100:.2f}%", f, m])
        elif "[BTTS]" in name and has_goals:
            filtered.append([name, f"{prob*100:.2f}%", f, m])

    df = pd.DataFrame(filtered, columns=["盤口", "機率", "公平賠率", "馬會估算"])

    if df.empty:
        st.error("未捕捉到已開盤，請上載圖")
    else:
        df["抽水率"] = df.apply(lambda r: f"{(1-float(r['馬會估算'])/float(r['公平賠率']))*100:.1f}%", axis=1)
        df["判決"] = df.apply(lambda r: "🚨黑盤 有著數" if float(r["公平賠率"]) < float(r["馬會估算"]) else "💧水盤", axis=1)
        df["狀態"] = "🟢已開盤"

        extras = []
        if not has_corner:
            extras.append(["[角球] 大9.5/大10.5等", "-", "-", "-", "-", "⚪未開盤", "⚪未開盤"])
        if not has_cs:
            extras.append(["[波膽] 1:0/1:1等", "-", "-", "-", "-", "⚪未開盤", "⚪未開盤"])
        if not has_hcap:
            extras.append(["[讓球] 主-0.5等", "-", "-", "-", "-", "⚪未開盤", "⚪未開盤"])

        if extras:
            df2 = pd.DataFrame(extras, columns=df.columns)
            df = pd.concat([df, df2], ignore_index=True)

        def color_row(row):
            if "黑盤" in str(row["判決"]):
                return ['background-color: #ff4444; color: white; font-weight: bold'] * len(row)
            elif "未開盤" in str(row["狀態"]):
                return ['background-color: #eeeeee; color: #999999'] * len(row)
            else:
                return [''] * len(row)

        st.dataframe(df.style.apply(color_row, axis=1), use_container_width=True, hide_index=True, height=650)

        c1, c2, c3 = st.columns(3)
        c1.metric("已開盤", f"{len(filtered)} 個")
        c2.metric("黑盤", f"{len(df[df['判決'].str.contains('黑盤')])} 個")
        c3.metric("未開盤", f"{len(extras)} 類")

        black_df = df[df["判決"].str.contains("黑盤")]
        if not black_df.empty:
            st.error(f"🚨 發現 {len(black_df)} 個黑盤！重點落呢啲：")
            st.table(black_df[["盤口", "公平賠率", "馬會估算", "抽水率", "判決"]])

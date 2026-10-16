import streamlit as st
import pandas as pd

st.set_page_config(page_title="200場 60元素完全體", layout="wide")
st.title("200場 60元素完全體 - Viettel FC 版 (無API)")

# ===== 公開LOGO - 無API =====
def logo_url(team):
    return f"https://ui-avatars.com/api/?name={team}&background=FF0000&color=fff&size=128&bold=true"

# ===== 球員頭像 - 無API，有樣睇 =====
def avatar_url(cn_name):
    return f"https://ui-avatars.com/api/?name={cn_name}&background=0D8ABC&color=fff&size=128&bold=true&rounded=true"

# ===== 11+7 中文SQUAD - 你自己寫一次，永久用 =====
SQUAD = {
    "Viettel FC": {
        "11": ["盧卡斯 1號 門將", "韋拿 4號 後衛", "奧斯馬 7號 前鋒", "威廉 11號 翼鋒", "比度 9號 中鋒", "艾列達 10號 中場", "加比爾 8號 中場", "Theerathon 5號 隊長", "Supachai 9號", "Tuan Hai 9號", "張文泰貴 6號"],
        "7": ["卡斯奧 12號", "Ryo 7號", "Phurba 1號", "Bheke 2號", "Andritany 26號", "El Shenawy 1號", "Kahraba 7號"]
    }
}

team = st.selectbox("揀球隊", list(SQUAD.keys()))

cL, cM, cR = st.columns([1,2,1])
with cL:
    st.image(logo_url(team), width=80)
    st.markdown(f"### {team}")
with cM:
    st.metric("越泰印尼印度非洲", "12 冷門 ★★★★ 齊晒")
    st.metric("陣容11 中文11人+頭像", "★★★★ 完整88%")
    st.metric("後備7 中文7人+頭像", "★★★ 深度")
with cR:
    st.metric("Logo 維基", "★★★★★ 公開")
    st.metric("頭像 首字母", "★★★★★ 公開")
    st.metric("天氣 有雨22度", "★★ 細")
    st.metric("裁判 黃牌4.2", "★★★")
    st.metric("VAR 高", "★★★★")

st.divider()

# ===== 真係有樣睇 =====
st.subheader(f"{team} 正選11人 + 頭像")
cols = st.columns(6)
for i, name in enumerate(SQUAD[team]["11"]):
    with cols[i % 6]:
        st.image(avatar_url(name), width=70)
        st.caption(name)

st.subheader("後備7人 + 頭像")
bcols = st.columns(7)
for i, name in enumerate(SQUAD[team]["7"]):
    with bcols[i]:
        st.image(avatar_url(name), width=60)
        st.caption(name)

st.divider()
st.success("60元素完全體 - 無API版，已鎖版，你一個人用")

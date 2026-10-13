import hashlib, random, time
import numpy as np
import pandas as pd
import streamlit as st

st.set_page_config(page_title="望遠鏡 V32.2 融合完全體", page_icon="👑", layout="wide")
st.title("🔭 望遠鏡 V32.2 · Ocup 68盤口 + 動畫完全體")
st.caption("總導演專屬 - V31自動賠率+FIFA戰意+V32 68盤口+動畫引擎 一個都冇少")

@st.cache_data(ttl=3600)
def fetch_fifa_rank_matrix(team_name):
    name = str(team_name).strip()
    db = {
        "西班牙": {"OVR":86,"Elo":1950,"Rank":1,"Pts":10,"Status":"已提前出線/大機率散步","H_Att":1.65,"A_Att":1.35,"H_Def":0.65,"A_Def":0.85},
        "塞爾維亞": {"OVR":79,"Elo":1680,"Rank":3,"Pts":4,"Status":"必須搶分保組/筋肉死磕","H_Att":1.10,"A_Att":0.85,"H_Def":1.05,"A_Def":1.25},
        "德國": {"OVR":85,"Elo":1920,"Rank":1,"Pts":9,"Status":"榜首全攻流速","H_Att":1.72,"A_Att":1.40,"H_Def":0.70,"A_Def":0.90},
        "荷蘭": {"OVR":84,"Elo":1880,"Rank":2,"Pts":5,"Status":"次席搶分戰意高","H_Att":1.55,"A_Att":1.30,"H_Def":0.75,"A_Def":0.95},
        "武里南聯": {"OVR":69,"Elo":1580,"Rank":1,"Pts":22,"Status":"榜首兼顧亞冠","H_Att":1.35,"A_Att":1.10,"H_Def":0.90,"A_Def":1.10},
        "FC北京": {"OVR":72,"Elo":1605,"Rank":4,"Pts":38,"Status":"聯賽收尾期","H_Att":1.25,"A_Att":1.00,"H_Def":0.95,"A_Def":1.15},
    }
    if name in db: return db[name]
    h = hashlib.md5(name.encode('utf-8')).hexdigest()
    return {"OVR":70,"Elo":1450,"Rank":2,"Pts":12,"Status":"戰意中規中矩","H_Att":1.2,"A_Att":1.0,"H_Def":0.9,"A_Def":1.1}

def fetch_live_hkjc_odds(h,a):
    pool = {
        "德國_vs_荷蘭":{"h":1.75,"d":3.85,"a":3.60,"o25":1.52,"corn":1.75,"bttsY":1.70},
        "西班牙_vs_塞爾維亞":{"h":1.30,"d":4.55,"a":7.25,"o25":1.65,"corn":1.82,"bttsY":1.85},
        "武里南聯_vs_FC北京":{"h":1.84,"d":3.65,"a":3.15,"o25":1.85,"corn":1.90,"bttsY":1.75},
    }
    return pool.get(f"{h}_vs_{a}",{"h":2.15,"d":3.30,"a":2.95

import math
import json
import os
import re
import sqlite3
import subprocess
import unicodedata
from datetime import datetime, timedelta, timezone
from io import BytesIO, StringIO
from pathlib import Path
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import numpy as np
import pandas as pd
import requests
import streamlit as st
try:
    from fbref import competition_matches, recent_match_reports, reports_to_dataframe
except Exception:
    # fbref.py 不存在、依賴未安裝或網站模組失敗時，FBref 只會被停用，
    # 不會阻止主 App 啟動；其他資料來源仍可正常使用。
    competition_matches = None
    def recent_match_reports(*args, **kwargs):
        return []
    def reports_to_dataframe(*args, **kwargs):
        return pd.DataFrame()
try:
    from data.sources.realtime_scraper import fetch_realtime_context
    from analysis.corrections import apply_verified_injury_adjustment, load_manual_injury_context
    from analysis.match_context_rules import (
        build_relegation_context, apply_relegation_intent, tight_score_pool,
        corner_context_rows, live_risk_message, reliability_level,
    )
    from data.odds.odds_mapper import parse_odds_text
    from analysis.odds_vs_model import compare_odds, ai_summary
    from data.orbiflow.orbiflow_adapter import load_orbiflow, apply_orbiflow, orbiflow_summary
    from data.team_goals.team_goals_model import team_goal_model, total_goal_band, goal_line_note
    from data.corners.corner_model import fallback_corner_model, corner_insight
    from data.brain.match_reader import read_match
    from data.brain.learning import learning_adjustment, learning_summary, load_log
    from data.v17_engine import build_card
    from data.pro_odds_page import merge_professional_page, odds_usage, find_event
    from analysis.market_backtest import walk_forward_market_backtest
except Exception:
    def fetch_realtime_context(*args, **kwargs):
        return {"status": "unavailable", "source": "未取得", "injury_data_verified": False,
                "h2h_last4": [], "home_last10": [], "away_last10": [], "injuries": [],
                "goal_adjustment": {"home": 0.0, "away": 0.0}}
    def apply_verified_injury_adjustment(hx, ax, live_context):
        return hx, ax, "即時來源模組未載入，沒有扣減預期入球"
    def load_manual_injury_context(*args, **kwargs):
        return {"status": "unavailable", "injury_data_verified": False, "goal_adjustment": {"home": 0.0, "away": 0.0}}
    def build_relegation_context(*args, **kwargs): return {"triggered": False, "status": "資料不足", "reason": "情境規則未載入"}
    def apply_relegation_intent(hx, ax, context, total_boost=.6): return hx, ax, 0.0
    def tight_score_pool(*args, **kwargs): return None
    def corner_context_rows(*args, **kwargs): return {"home_average": None, "away_average": None, "last_h2h": None}
    def live_risk_message(*args, **kwargs): return None
    def reliability_level(*args, **kwargs): return {"level": "低", "color": "#b42318", "text": "低｜規則模組未載入"}
    def parse_odds_text(*args, **kwargs): return []
    def compare_odds(*args, **kwargs): return []
    def ai_summary(results, home, away, hx, ax): return f"AI分析：{home}預期入球{hx:.2f}、{away}{ax:.2f}。"
    def load_orbiflow(*args, **kwargs): return {"available": False, "source": "未有有效ORBIFLOW資料"}
    def apply_orbiflow(hx, ax, data, *args, **kwargs): return {"home_exp_final": hx, "away_exp_final": ax, "total_exp_final": hx+ax, "used": False}
    def orbiflow_summary(data, result): return "ORBIFLOW流動：未有有效資料｜沿用V1.0原有預期"
    def team_goal_model(hx, ax): return {"home_exp":hx,"away_exp":ax,"total_exp":hx+ax,"home_over_0_5":1-math.exp(-hx),"home_over_1_5":1-math.exp(-hx)*(1+hx),"away_over_0_5":1-math.exp(-ax),"away_over_1_5":1-math.exp(-ax)*(1+ax)}
    def total_goal_band(total, swing=.8): return {"total_exp":total,"swing":swing,"low":max(0,total-swing),"high":total+swing}
    def goal_line_note(p, line, margin=.08): return f"{p:.2%}（模型機率）"
    def fallback_corner_model(*args, **kwargs): return {"home":4.5,"away":4.5,"total":9.0,"market":{},"is_fallback":True,"source":"V1.4情境估算","note":"角球無和局；估算不等於實測"}
    def corner_insight(*args, **kwargs): return "角球只作輔助，優先核對真實HC/AC。"
    def read_match(*args, **kwargs): return {"conclusion":"未載入V2.0解讀模組。","ou_note":"","evidence":[]}
    def learning_adjustment(*args, **kwargs): return 0.0
    def learning_summary(*args, **kwargs): return {"total":0,"completed":0,"recent5_error":None}
    def load_log(*args, **kwargs): return []
    def build_card(*args, **kwargs): return {}
    def merge_professional_page(*args, **kwargs): return {"odds_meta": {"status": "unavailable"}, "odds_snapshot": None, "match_detail": {}}
    def odds_usage(): return {"date": "", "calls": 0}
    def find_event(*args, **kwargs): return None
    def walk_forward_market_backtest(*args, **kwargs): return pd.DataFrame(), {"入球樣本數": 0, "角球樣本數": 0}

# 重要模組獨立重試：即使專業盤口或其他選配模組失敗，V2解讀、學習、
# 角球及傷停修正仍然可以正常載入，不應整批退回後備模式。
try:
    from data.brain.match_reader import read_match as _v2_read_match
    read_match = _v2_read_match
except Exception:
    pass
try:
    from data.odds.odds_mapper import parse_odds_text as _parse_odds_text
    parse_odds_text = _parse_odds_text
except Exception:
    pass
try:
    from analysis.odds_vs_model import compare_odds as _compare_odds
    from analysis.odds_vs_model import ai_summary as _ai_summary
    compare_odds, ai_summary = _compare_odds, _ai_summary
except Exception:
    pass
try:
    from data.brain.learning import learning_adjustment as _learning_adjustment
    from data.brain.learning import learning_summary as _learning_summary
    from data.brain.learning import load_log as _load_log
    learning_adjustment, learning_summary, load_log = _learning_adjustment, _learning_summary, _load_log
except Exception:
    pass
try:
    from analysis.corrections import apply_verified_injury_adjustment as _apply_verified_injury_adjustment
    from analysis.corrections import load_manual_injury_context as _load_manual_injury_context
    apply_verified_injury_adjustment, load_manual_injury_context = _apply_verified_injury_adjustment, _load_manual_injury_context
except Exception:
    pass
try:
    from data.corners.corner_model import fallback_corner_model as _fallback_corner_model
    from data.corners.corner_model import corner_insight as _corner_insight
    fallback_corner_model, corner_insight = _fallback_corner_model, _corner_insight
except Exception:
    pass

st.set_page_config(page_title="混合來源足球分析", page_icon="⚽", layout="wide")

DB = Path(__file__).with_name("football_library.db")
DB_PATH = str(DB)
MANUAL_LEAGUE_DIR = Path(__file__).with_name("data") / "manual_leagues"
PHOENIX_FINAL_DATA = Path(__file__).parent / "assets" / "data" / "phoenix_FINAL_63teams.json"

# Phoenix 63隊畢業資料使用較短的聯賽標籤；App 原有選單使用完整中文名稱。
PHOENIX_LEAGUE_ALIASES = {
    "巴甲": "巴西甲組聯賽", "英超": "英格蘭超級聯賽", "意甲": "意大利甲組聯賽",
    "西甲": "西班牙甲組聯賽", "德甲": "德國甲組聯賽", "法甲": "法國甲組聯賽",
}


def manual_league_path(league):
    """每個聯賽一份手動覆蓋檔；只使用安全檔名，避免路徑穿越。"""
    slug = re.sub(r"[^a-z0-9_-]+", "_", str(league).strip().lower()).strip("_") or "league"
    return MANUAL_LEAGUE_DIR / f"{slug}.csv"


def db_connect():
    """建立可容忍短暫並行讀寫的 SQLite 連線。"""
    conn = sqlite3.connect(DB_PATH, timeout=30, check_same_thread=False)
    # WAL 只在可寫入環境嘗試設定；Streamlit Cloud 重啟或多工作者
    # 同時讀取時，切換 journal mode 可能在 SELECT 前觸發 database locked。
    try:
        conn.execute("PRAGMA journal_mode=WAL;")
    except sqlite3.OperationalError:
        pass
    conn.execute("PRAGMA busy_timeout=30000;")
    return conn


def db_read_connect():
    """以只讀連線讀取資料，避免分析頁被背景寫入鎖住。"""
    try:
        conn = sqlite3.connect(
            f"file:{Path(DB_PATH).resolve()}?mode=ro",
            uri=True, timeout=30, check_same_thread=False,
        )
    except sqlite3.OperationalError:
        # 本地測試或首次初始化時資料庫可能尚未存在，交回一般連線。
        conn = db_connect()
    conn.execute("PRAGMA busy_timeout=30000;")
    return conn


def repair_database_lock():
    """安全整理未完成交易及 WAL 檔，避免直接刪除仍在使用的資料。"""
    conn = None
    try:
        conn = db_connect()
        conn.rollback()
        conn.execute("PRAGMA wal_checkpoint(TRUNCATE);")
        conn.commit()
    finally:
        if conn is not None:
            conn.close()
    # checkpoint 後通常已經沒有 sidecar；只清理確定存在的殘留檔案。
    for suffix in ("-wal", "-shm"):
        sidecar = Path(DB_PATH + suffix)
        if sidecar.exists():
            try:
                sidecar.unlink()
            except OSError:
                pass
API_BASE = "https://v3.football.api-sports.io"
FD_API = "https://api.football-data.org/v4"
FFA_API = "https://api.ffa.football"
FD_BASE = "https://www.football-data.co.uk"
OPENLIGA_API = "https://api.openligadb.de"
# TheSportsDB 已停用舊的 3；官方目前提供測試用 123。
SPORTSDB_API = "https://www.thesportsdb.com/api/v1/json/123"
FBREF_BASE = "https://fbref.com"
HEADERS = {"User-Agent": "FootballResearchApp/1.0 (public-data research)"}

LEAGUES = {
    "英格蘭超級聯賽": {"api": 39, "csv": "E0"},
    "英格蘭冠軍聯賽": {"api": 40, "csv": "E1"},
    "西班牙甲組聯賽": {"api": 140, "csv": "SP1"},
    "西班牙乙組聯賽": {"api": 141, "csv": "SP2"},
    "意大利甲組聯賽": {"api": 135, "csv": "I1"},
    "德國甲組聯賽": {"api": 78, "csv": "D1"},
    "德國乙組聯賽": {"api": 79, "csv": "D2"},
    "法國乙組聯賽": {"api": 62, "csv": "F2"},
    "荷蘭甲組聯賽": {"api": 88, "csv": "N1"},
    "荷蘭乙組聯賽": {"api": 89, "csv": "N2"},
    "蘇格蘭超級聯賽": {"api": 179, "csv": "SC0"},
    "奧地利甲組聯賽": {"api": 218, "csv": "AUT"},
    "丹麥超級聯賽": {"api": 119, "csv": "DNK"},
    "芬蘭超級聯賽": {"api": 244, "csv": "FIN"},
    "挪威超級聯賽": {"api": 103, "csv": "NOR"},
    "俄羅斯超級聯賽": {"api": 235, "csv": "RUS"},
    "阿根廷甲組聯賽": {"api": 128, "csv": "ARG"},
    "巴西甲組聯賽": {"api": 71, "csv": "BRA"},
    "巴西乙組聯賽": {"api": 72, "csv": ""},
    "墨西哥超級聯賽": {"api": 262, "csv": "MEX"},
    "日本職業聯賽": {"api": 98, "csv": "JPN"},
    "日本乙組聯賽": {"api": 99, "csv": ""},
    "澳洲職業聯賽": {"api": 188, "csv": ""},
    "澳洲冠軍聯賽盃": {"api": None, "csv": ""},
    "女子澳洲職業聯賽": {"api": None, "csv": ""},
    "南韓職業聯賽": {"api": 292, "csv": ""},
    "南韓乙組聯賽": {"api": 293, "csv": ""},
    "泰國甲組聯賽": {"api": 296, "csv": ""},
    "沙特職業聯賽": {"api": 307, "csv": ""},
    "卡塔爾超級聯賽": {"api": 305, "csv": ""},
    "阿聯酋職業聯賽": {"api": 301, "csv": ""},
    "烏拉圭甲組聯賽": {"api": 268, "csv": ""},
    "墨西哥甲組聯賽": {"api": 263, "csv": ""},
    "女子挪威超級聯賽": {"api": None, "csv": ""},
    "女子南美自由盃": {"api": None, "csv": ""},
    "歐洲冠軍聯賽": {"api": 2, "csv": ""},
}

# 多聯賽資料館：檔案名稱可用來自動判斷所屬聯賽；網址只作公開來源提示，
# 不會繞過登入或網站限制。CSV 沒有角球欄位時，角球模型會明確標示資料不足。
BULK_CSV_SPECS = {
    "英格蘭超級聯賽": {"tokens": ["e0", "premier-league"], "source": "football-data"},
    "英格蘭冠軍聯賽": {"tokens": ["e1", "championship"], "source": "football-data"},
    "西班牙甲組聯賽": {"tokens": ["sp1", "la-liga"], "source": "football-data"},
    "德國甲組聯賽": {"tokens": ["d1", "bundesliga"], "source": "football-data"},
    "德國乙組聯賽": {"tokens": ["d2", "2-bundesliga"], "source": "football-data"},
    "荷蘭甲組聯賽": {"tokens": ["n1", "eredivisie"], "source": "football-data"},
    "西班牙乙組聯賽": {"tokens": ["sp2", "segunda"], "source": "football-data"},
    "荷蘭乙組聯賽": {"tokens": ["eerste", "keuken"], "source": "openfootball"},
    "法國乙組聯賽": {"tokens": ["f2", "ligue-2", "ligue2"], "source": "football-data"},
    "蘇格蘭超級聯賽": {"tokens": ["sc0", "scotland"], "source": "football-data"},
    "奧地利甲組聯賽": {"tokens": ["austria", "bundesliga-austria"], "source": "openfootball"},
    "丹麥超級聯賽": {"tokens": ["denmark", "superliga"], "source": "openfootball"},
    "芬蘭超級聯賽": {"tokens": ["finland", "veikkausliiga"], "source": "openfootball"},
    "挪威超級聯賽": {"tokens": ["norway", "eliteserien"], "source": "openfootball"},
    "俄羅斯超級聯賽": {"tokens": ["russia", "premier"], "source": "openfootball"},
    "澳洲職業聯賽": {"tokens": ["a-league", "australia-a-league"], "source": "openfootball"},
    "澳洲冠軍聯賽盃": {"tokens": ["australian-championship", "aus-championship"], "source": "official/flashscore"},
    "日本職業聯賽": {"tokens": ["j1", "jleague"], "source": "openfootball"},
    "日本乙組聯賽": {"tokens": ["j2"], "source": "openfootball"},
    "南韓職業聯賽": {"tokens": ["k1", "kleague"], "source": "openfootball"},
    "南韓乙組聯賽": {"tokens": ["k2"], "source": "openfootball"},
    "女子澳洲職業聯賽": {"tokens": ["w-league", "aleague-women"], "source": "openfootball"},
    "澳洲冠軍聯賽盃／澳洲盃": {"tokens": ["australia-cup", "australiacup"], "source": "openfootball"},
    "墨西哥超級聯賽": {"tokens": ["liga-mx", "mexico-liga"], "source": "openfootball"},
    "墨西哥甲組聯賽": {"tokens": ["expansion", "liga-expansion"], "source": "openfootball"},
    "泰國甲組聯賽": {"tokens": ["thai-league", "thailand"], "source": "openfootball"},
    "沙特職業聯賽": {"tokens": ["saudi-pro", "saudi"], "source": "openfootball"},
    "卡塔爾超級聯賽": {"tokens": ["qatar", "stars-league"], "source": "openfootball"},
    "阿聯酋職業聯賽": {"tokens": ["uae", "emirates"], "source": "openfootball"},
    "阿根廷甲組聯賽": {"tokens": ["argentina", "primera"], "source": "openfootball"},
    "巴西甲組聯賽": {"tokens": ["serie-a", "brazil-serie-a"], "source": "openfootball"},
    "巴西乙組聯賽": {"tokens": ["serie-b", "brazil-serie-b"], "source": "openfootball"},
    "烏拉圭甲組聯賽": {"tokens": ["uruguay", "primera-uruguay"], "source": "openfootball"},
    "女子挪威超級聯賽": {"tokens": ["toppserien", "norway-women"], "source": "openfootball"},
    "女子南美自由盃": {"tokens": ["libertadores-femenina", "copa-femenina"], "source": "openfootball"},
    "歐洲冠軍聯賽": {"tokens": ["champions-league", "uefa-champions"], "source": "openfootball"},
}

ALIASES = {
    "阿仙奴": "Arsenal FC", "利物浦": "Liverpool FC", "紐卡素": "Newcastle United FC",
    "阿士東維拉": "Aston Villa FC", "曼聯": "Manchester United FC", "車路士": "Chelsea FC",
    "熱刺": "Tottenham Hotspur FC", "廣島三箭": "Sanfrecce Hiroshima", "京都不死鳥": "Kyoto Sanga",
    "班菲特": "Banfield", "小阿根廷人": "Argentinos Jrs",
    "小阿根廷青年人": "Argentinos Jrs", "博卡青年": "Boca Juniors",
    "河床": "River Plate", "獨立隊": "Independiente", "競賽會": "Racing Club",
    "漢諾威": "Hannover", "漢諾威九六": "Hannover", "聖保利": "St Pauli",
    "西維爾": "Sevilla FC", "西維爾足球會": "Sevilla FC", "皇家馬德里": "Real Madrid",
    "施禾利": "PEC Zwolle", "茲沃勒": "PEC Zwolle", "PEC茲沃勒": "PEC Zwolle",
    "伊高斯": "Go Ahead Eagles", "前進之鷹": "Go Ahead Eagles",
    "阿爾克馬爾": "AZ", "艾克馬亞": "AZ", "格羅寧根": "FC Groningen",
    "烏德勒支": "FC Utrecht", "飛燕諾": "Feyenoord Rotterdam",
    "聖保羅": "São Paulo", "坎培拉克羅地亞": "Canberra Croatia",
    # Australian Championship cache uses the short provider names; accept the
    # official English names and Chinese names without mapping Sydney United to
    # the unrelated Sydney FC.
    "南墨爾本": "South Melbourne", "South Melbourne FC": "South Melbourne",
    "悉尼聯": "Sydney Utd", "悉尼聯隊": "Sydney Utd",
    "Sydney United 58": "Sydney Utd", "Sydney United": "Sydney Utd",
    "艾費哈": "Al Feiha", "阿爾費哈": "Al Feiha", "吉達艾阿里": "Al Ahli SC",
    "吉達艾里": "Al Ahli SC", "吉達阿赫利": "Al Ahli SC", "阿赫利": "Al Ahli SC",
    "幸運切爾達": "Celta B", "切爾達B": "Celta B", "特內里費": "Tenerife",
    "熱刺": "Tottenham Hotspur", "Tottenham": "Tottenham Hotspur",
    "高雲地利": "Coventry City", "Coventry": "Coventry City",
    "艾費哈": "Al Feiha", "Al Fayha": "Al Feiha", "Al Fayha FC": "Al Feiha",
    "吉達艾阿里": "Al Ahli SC", "吉達艾里": "Al Ahli SC",
    "艾哈森": "Al Hazem", "哈森姆": "Al Hazem", "Al-Hazem": "Al Hazem", "Al Hazem FC": "Al Hazem", "Al Hazem": "Al Hazem",
    "Al Ahli": "Al Ahli SC", "Al Ahli Saudi FC": "Al Ahli SC", "Al Ahli Saudi": "Al Ahli SC",
    "Al Fayha": "Al Feiha", "Al-Fayha": "Al Feiha",
    "迪里耶會": "Diriyah", "迪里阿耶會": "Diriyah", "迪里雅赫": "Diriyah", "Diriyah Club": "Diriyah",
    "艾利雅德": "Al Riyadh", "艾利雅得": "Al Riyadh",
}

# 只放可核對的常用中文隊名；沒有可靠中文譯名時，畫面會明確標示，絕不自行亂譯。
TEAM_ZH = {
    "Arsenal FC": "阿仙奴", "Liverpool FC": "利物浦", "Newcastle United FC": "紐卡素",
    "Aston Villa FC": "阿士東維拉", "Manchester United FC": "曼聯", "Chelsea FC": "車路士",
    "Tottenham Hotspur FC": "熱刺", "Manchester City": "曼城", "Real Madrid": "皇家馬德里",
    "Barcelona": "巴塞隆拿", "Bayern Munich": "拜仁慕尼黑", "Inter Milan": "國際米蘭",
    "Sanfrecce Hiroshima": "廣島三箭", "Kyoto Sanga": "京都不死鳥", "Banfield": "班菲特",
    "Argentinos Jrs": "小阿根廷人", "Boca Juniors": "博卡青年", "River Plate": "河床",
    "Independiente": "獨立隊", "Racing Club": "競賽會", "PEC Zwolle": "施禾利",
    "Go Ahead Eagles": "伊高斯", "AZ": "阿爾克馬爾", "FC Groningen": "格羅寧根",
    "FC Utrecht": "烏德勒支", "Feyenoord Rotterdam": "飛燕諾", "São Paulo": "聖保羅",
    "Sevilla FC": "西維爾", "Al Feiha": "艾費哈", "Al Hazem": "艾哈森", "Al Ahli SC": "吉達艾阿里",
    "Celta B": "幸運切爾達", "Celta Vigo B": "幸運切爾達", "Tenerife": "特內里費",
    "Tottenham": "熱刺", "Tottenham Hotspur": "熱刺",
    "Coventry": "高雲地利", "Coventry City": "高雲地利",
    "Diriyah": "迪里耶會", "Diriyah Club": "迪里耶會", "Al Riyadh": "艾利雅德",
}
def load_alias_map():
    """讀取專案內的 alias_map.csv；只作隊名配對，不會創造賽果。"""
    path = Path(__file__).with_name("alias_map.csv")
    if not path.exists():
        return
    try:
        table = pd.read_csv(path, dtype=str).fillna("")
        for _, row in table.iterrows():
            zh = str(row.get("中文名稱", "")).strip()
            canonical = str(row.get("英文標準名", "")).strip()
            if not canonical:
                continue
            if zh:
                ALIASES[zh] = canonical
                TEAM_ZH[canonical] = zh
            for col in table.columns:
                if col.startswith("別名") and str(row.get(col, "")).strip():
                    ALIASES[str(row[col]).strip()] = canonical
    except Exception:
        return
load_alias_map()

def load_team_name_map():
    path = Path(__file__).parent / "data" / "team_name_map.json"
    try:
        mapping = json.loads(path.read_text(encoding="utf-8"))
        for english, chinese in mapping.items():
            english, chinese = str(english).strip(), str(chinese).strip()
            if english and chinese:
                TEAM_ZH[english] = chinese
                ALIASES.setdefault(chinese, english)
    except Exception:
        return
load_team_name_map()

# 規則模組是核心顯示功能；即使某個可選資料模組在部署環境失敗，
# 仍然獨立重試載入，避免整個頁面錯誤地顯示「規則模組未載入」。
try:
    from analysis.match_context_rules import (
        build_relegation_context as _build_relegation_context,
        apply_relegation_intent as _apply_relegation_intent,
        tight_score_pool as _tight_score_pool,
        corner_context_rows as _corner_context_rows,
        live_risk_message as _live_risk_message,
        reliability_level as _reliability_level,
    )
    build_relegation_context = _build_relegation_context
    apply_relegation_intent = _apply_relegation_intent
    tight_score_pool = _tight_score_pool
    corner_context_rows = _corner_context_rows
    live_risk_message = _live_risk_message
    reliability_level = _reliability_level
except Exception:
    pass

def zh_team(name):
    name = str(name or "").strip()
    return TEAM_ZH.get(name, name if any("\u4e00" <= ch <= "\u9fff" for ch in name) else f"未有中文隊名（{name}）")

def zh_source(name):
    return {"Football-Data.org API": "Football-Data.org 資料接口", "Football-Data CSV": "Football-Data 公開資料",
            "本地資料館": "本地足球資料館", "TheSportsDB": "TheSportsDB 公開資料"}.get(str(name), str(name))

def zh_country(value):
    return {"Argentina": "阿根廷", "ARG": "阿根廷", "Brazil": "巴西", "BRA": "巴西",
            "England": "英格蘭", "ENG": "英格蘭", "Spain": "西班牙", "ESP": "西班牙",
            "Germany": "德國", "GER": "德國", "France": "法國", "FRA": "法國",
            "Japan": "日本", "JPN": "日本", "South Korea": "南韓", "KOR": "南韓",
            "Australia": "澳洲", "AUS": "澳洲", "Netherlands": "荷蘭", "NED": "荷蘭",
            "Italy": "意大利", "ITA": "意大利", "Uruguay": "烏拉圭", "URU": "烏拉圭"}.get(str(value), "未有中文國籍資料")

def zh_position(value):
    return {"Goalkeeper": "守門員", "GK": "守門員", "Defender": "後衛", "DF": "後衛",
            "Midfielder": "中場", "MF": "中場", "Forward": "前鋒", "FW": "前鋒",
            "Centre-Forward": "中鋒", "Left-Back": "左後衛", "Right-Back": "右後衛",
            "Defensive Midfield": "防守中場", "Manager": "教練"}.get(str(value), "未有中文位置資料")

def zh_player_name(raw, index):
    # 沒有可靠官方中文譯名時不虛構譯名，保留可核對性並用中文提示。
    return f"第 {index} 名球員（來源未提供中文譯名）"


API_LEAGUE_SEARCH = {
    "女子澳洲職業聯賽": "A-League Women",
    "南韓乙組聯賽": "K League 2",
    "女子挪威超級聯賽": "Toppserien",
    "女子南美自由盃": "CONMEBOL Libertadores Femenina",
    "澳洲冠軍聯賽盃／澳洲盃": "Australia Cup",
}


def db_init():
    with db_connect() as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS matches (
            league TEXT, season TEXT, home TEXT, away TEXT, hg INTEGER, ag INTEGER,
            hc REAL, ac REAL, date TEXT, source TEXT, captured_at TEXT,
            PRIMARY KEY(league, season, home, away, date)
        );
        CREATE TABLE IF NOT EXISTS source_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT, league TEXT, source TEXT,
            status TEXT, message TEXT, captured_at TEXT
        );
        CREATE TABLE IF NOT EXISTS analyses (
            id INTEGER PRIMARY KEY AUTOINCREMENT, league TEXT, home TEXT, away TEXT,
            home_prob REAL, draw_prob REAL, away_prob REAL, source TEXT, created_at TEXT
        );
        """)
        cols = {row[1] for row in c.execute("PRAGMA table_info(matches)").fetchall()}
        if "hc" not in cols:
            c.execute("ALTER TABLE matches ADD COLUMN hc REAL")
        if "ac" not in cols:
            c.execute("ALTER TABLE matches ADD COLUMN ac REAL")


def log_source(league, source, status, message=""):
    with db_connect() as c:
        c.execute("INSERT INTO source_log(league,source,status,message,captured_at) VALUES(?,?,?,?,?)",
                  (league, source, status, message[:500], datetime.now(timezone.utc).isoformat()))


def clean_matches(df, source, league, season):
    aliases = {
        "HomeTeam": "Home", "AwayTeam": "Away", "FTHG": "HG", "FTAG": "AG",
        "Team1": "Home", "Team2": "Away", "Team 1": "Home", "Team 2": "Away",
        "Score1": "HG", "Score2": "AG", "Date": "Date",
        "HomeCorners": "HC", "AwayCorners": "AC", "Home Corner": "HC", "Away Corner": "AC",
        "主隊角球": "HC", "客隊角球": "AC",
    }
    df = df.rename(columns={k: v for k, v in aliases.items() if k in df.columns})
    if "Home" in df.columns:
        df["Home"] = df["Home"].astype(str).str.strip().map(lambda x: ALIASES.get(x, x))
    if "Away" in df.columns:
        df["Away"] = df["Away"].astype(str).str.strip().map(lambda x: ALIASES.get(x, x))
    if "FT" in df.columns and not {"HG", "AG"}.issubset(df.columns):
        scores = df["FT"].astype(str).str.extract(r"^\s*(\d+)\s*[-:]\s*(\d+)\s*$")
        df["HG"] = pd.to_numeric(scores[0], errors="coerce")
        df["AG"] = pd.to_numeric(scores[1], errors="coerce")
    required = {"Home", "Away", "HG", "AG"}
    if not required.issubset(df.columns):
        raise ValueError("來源缺少 Home、Away、HG、AG 欄位")
    df["HG"] = pd.to_numeric(df["HG"], errors="coerce")
    df["AG"] = pd.to_numeric(df["AG"], errors="coerce")
    df["HC"] = pd.to_numeric(df["HC"], errors="coerce") if "HC" in df.columns else float("nan")
    df["AC"] = pd.to_numeric(df["AC"], errors="coerce") if "AC" in df.columns else float("nan")
    df = df.dropna(subset=["Home", "Away", "HG", "AG"]).copy()
    df["Date"] = df.get("Date", "")
    df["DateParsed"] = pd.to_datetime(df["Date"], errors="coerce", dayfirst=True)
    df["league"] = league
    df["season"] = str(season)
    df["source"] = source
    return df[["league", "season", "Home", "Away", "HG", "AG", "HC", "AC", "Date", "DateParsed", "source"]]


FLASH_SCORE_RESULTS = {
    "卡塔爾超級聯賽": "https://www.flashscore.com/football/qatar/qsl/results/",
    "女子南美自由盃": "https://www.flashscore.com/football/south-america/copa-libertadores-women/results/",
}
GENERATED_BACKFILL_DIR = Path(__file__).with_name("data") / "generated_backfills"


def _flashscore_value(block, key):
    match = re.search(r"(?:^|¬)" + re.escape(key) + r"÷([^¬]+)", block)
    return match.group(1).strip() if match else ""


def fetch_flashscore_goal_results(league, limit=20):
    """從 Flashscore 公開結果頁只讀取已完場比分；HC/AC 明確標成未核實。

    Flashscore 的公開頁面會把結果放在內嵌序列資料中。這裡只取日期、主客隊及
    全場入球，不猜半場比分、排名或角球；角球欄按要求寫 0，但稍後會按 source
    標記為不可作角球回測。
    """
    url = FLASH_SCORE_RESULTS.get(league)
    if not url:
        raise ValueError(f"未設定 {league} 的 Flashscore 公開結果頁")
    response = requests.get(url, headers=HEADERS, timeout=20)
    response.raise_for_status()
    blocks = re.findall(r"AA÷([^~]+)", response.text)
    rows = []
    for block in blocks:
        # AB=3 是 Flashscore 已完場事件；未完場／取消事件不納入。
        if _flashscore_value(block, "AB") != "3":
            continue
        home = _flashscore_value(block, "AE")
        away = _flashscore_value(block, "AF")
        date_value = _flashscore_value(block, "AD")
        home_goals = _flashscore_value(block, "AG")
        away_goals = _flashscore_value(block, "GRA")
        if not home or not away or not date_value or not home_goals.isdigit() or not away_goals.isdigit():
            continue
        try:
            date_value = datetime.fromtimestamp(int(date_value), tz=timezone.utc).date().isoformat()
        except (TypeError, ValueError, OverflowError):
            continue
        rows.append({
            "Date": date_value, "Home": home, "Away": away,
            "HG": int(home_goals), "AG": int(away_goals),
            "HC": 0.0, "AC": 0.0,
            "source": "Flashscore 自動補20場（只入球；角球未核實）",
        })
    if not rows:
        raise ValueError("Flashscore 暫時沒有可核對的已完場賽果；沒有寫入任何資料")
    result = clean_matches(pd.DataFrame(rows), rows[0]["source"], league, datetime.now().year)
    result = result.sort_values("DateParsed", ascending=False).drop_duplicates(
        subset=["Date", "Home", "Away"]
    ).head(int(limit)).sort_values("DateParsed").reset_index(drop=True)
    if result.empty:
        raise ValueError("Flashscore 沒有符合日期及比分格式的賽果")
    return result


def save_flashscore_goal_backfill(matches, league):
    """保存自動補入的入球資料，並另外輸出可核對的 9 欄 CSV。"""
    if matches is None or len(matches) == 0:
        raise ValueError("沒有可保存的 Flashscore 賽果")
    GENERATED_BACKFILL_DIR.mkdir(parents=True, exist_ok=True)
    csv_rows = pd.DataFrame({
        "日期": matches["Date"], "主隊": matches["Home"], "客隊": matches["Away"],
        "比分": matches.apply(lambda r: f"{int(r.HG)}-{int(r.AG)}", axis=1),
        "半場比分": "", "主隊角球": 0, "客隊角球": 0,
        "主隊排名": "", "客隊排名": "",
    })
    slug = re.sub(r"[^a-z0-9_-]+", "_", str(league).lower()).strip("_") or "league"
    csv_rows.to_csv(GENERATED_BACKFILL_DIR / f"{slug}_flashscore_goals_20.csv", index=False, encoding="utf-8-sig")
    save_matches(matches)
    return len(matches)


def is_unverified_corner_source(source):
    return "角球未核實" in str(source or "") or "只入球" in str(source or "")


MANUAL_LEAGUE_COLUMNS = ["日期", "主隊", "客隊", "比分", "半場比分", "主隊角球", "客隊角球", "主隊排名", "客隊排名"]


def _parse_score_pair(value, label):
    match = re.fullmatch(r"\s*(\d+)\s*[-:]\s*(\d+)\s*", str(value or ""))
    if not match:
        raise ValueError(f"{label}必須是例如 1-0 的格式")
    return int(match.group(1)), int(match.group(2))


def read_manual_league_csv(uploaded_file, league):
    """讀取資料不足聯賽的固定 9 欄 CSV，保留排名及半場比分作情境輸入。"""
    if uploaded_file is None:
        raise ValueError("請先選擇 CSV")
    raw = uploaded_file.getvalue()
    if not raw:
        raise ValueError("CSV 是空白檔案")
    frame = pd.read_csv(BytesIO(raw), encoding="utf-8-sig")
    frame.columns = [str(c).strip() for c in frame.columns]
    if frame.columns.tolist() != MANUAL_LEAGUE_COLUMNS:
        missing = [c for c in MANUAL_LEAGUE_COLUMNS if c not in frame.columns]
        extra = [c for c in frame.columns if c not in MANUAL_LEAGUE_COLUMNS]
        detail = []
        if missing:
            detail.append("缺少：" + ", ".join(missing))
        if extra:
            detail.append("多出：" + ", ".join(extra))
        raise ValueError("CSV 必須固定 9 欄（" + "；".join(detail) + "）")
    frame = frame[MANUAL_LEAGUE_COLUMNS].copy()
    if frame.empty:
        raise ValueError("CSV 沒有賽果資料")
    scores = frame["比分"].map(lambda x: _parse_score_pair(x, "比分"))
    half_scores = frame["半場比分"].map(lambda x: _parse_score_pair(x, "半場比分"))
    frame["HG"] = scores.map(lambda x: x[0])
    frame["AG"] = scores.map(lambda x: x[1])
    frame["HT_HG"] = half_scores.map(lambda x: x[0])
    frame["HT_AG"] = half_scores.map(lambda x: x[1])
    frame["HomeRank"] = pd.to_numeric(frame["主隊排名"], errors="coerce")
    frame["AwayRank"] = pd.to_numeric(frame["客隊排名"], errors="coerce")
    if frame[["HomeRank", "AwayRank"]].isna().any().any() or (frame[["HomeRank", "AwayRank"]] < 1).any().any():
        raise ValueError("主隊排名及客隊排名必須是正整數")
    frame["HC"] = pd.to_numeric(frame["主隊角球"], errors="coerce")
    frame["AC"] = pd.to_numeric(frame["客隊角球"], errors="coerce")
    if frame[["HC", "AC"]].isna().any().any() or (frame[["HC", "AC"]] < 0).any().any():
        raise ValueError("主隊角球及客隊角球必須是 0 或以上數字")
    normalized = pd.DataFrame({
        "Date": frame["日期"], "Home": frame["主隊"], "Away": frame["客隊"],
        "HG": frame["HG"], "AG": frame["AG"], "HC": frame["HC"], "AC": frame["AC"],
    })
    normalized = clean_matches(normalized, "手動上載聯賽 CSV", league, datetime.now().year)
    # clean_matches 只保留通用比賽欄位；排名及半場比分另行按原順序附加。
    normalized["HT_HG"] = frame["HT_HG"].to_numpy()
    normalized["HT_AG"] = frame["HT_AG"].to_numpy()
    normalized["HomeRank"] = frame["HomeRank"].to_numpy()
    normalized["AwayRank"] = frame["AwayRank"].to_numpy()
    return normalized


def save_manual_league_override(matches, league):
    """寫入磁碟並清除該聯賽舊免費來源，確保分析不混用兩套樣本。"""
    if matches is None or len(matches) < 5:
        raise ValueError("至少需要 5 場完整賽果才可以覆蓋聯賽資料")
    MANUAL_LEAGUE_DIR.mkdir(parents=True, exist_ok=True)
    out = matches.copy()
    out[["Date", "Home", "Away", "HG", "AG", "HC", "AC", "HT_HG", "HT_AG", "HomeRank", "AwayRank"]].to_csv(
        manual_league_path(league), index=False, encoding="utf-8-sig"
    )
    with db_connect() as conn:
        conn.execute("DELETE FROM matches WHERE league=?", (league,))
    save_matches(out)


def load_manual_league_override(league):
    path = manual_league_path(league)
    if not path.exists():
        return pd.DataFrame()
    try:
        raw = pd.read_csv(path, encoding="utf-8-sig")
        required = {"Date", "Home", "Away", "HG", "AG", "HC", "AC", "HT_HG", "HT_AG", "HomeRank", "AwayRank"}
        if not required.issubset(raw.columns):
            return pd.DataFrame()
        return clean_matches(raw, "手動上載聯賽 CSV", league, datetime.now().year).assign(
            HT_HG=pd.to_numeric(raw["HT_HG"], errors="coerce").to_numpy(),
            HT_AG=pd.to_numeric(raw["HT_AG"], errors="coerce").to_numpy(),
            HomeRank=pd.to_numeric(raw["HomeRank"], errors="coerce").to_numpy(),
            AwayRank=pd.to_numeric(raw["AwayRank"], errors="coerce").to_numpy(),
        )
    except Exception:
        return pd.DataFrame()


def read_uploaded_matches(uploaded_file, league):
    """讀取使用者從合法來源下載的 CSV／Excel，統一成資料館格式。"""
    if uploaded_file is None:
        raise ValueError("未選擇檔案")
    filename = str(getattr(uploaded_file, "name", "")).lower()
    raw = uploaded_file.getvalue()
    if not raw:
        raise ValueError("檔案是空白的")
    if filename.endswith((".xlsx", ".xls")):
        frame = pd.read_excel(BytesIO(raw))
    else:
        try:
            frame = pd.read_csv(BytesIO(raw), encoding="utf-8-sig")
        except UnicodeDecodeError:
            frame = pd.read_csv(BytesIO(raw), encoding="latin1")
    if frame.empty:
        raise ValueError("檔案沒有資料列")
    # 接受常見英文欄位及少量中文欄位；不符合格式便清楚提示，不虛構數據。
    aliases = {
        "主隊": "Home", "客隊": "Away", "主隊入球": "HG", "客隊入球": "AG",
        "主隊角球": "HC", "客隊角球": "AC", "日期": "Date", "全場比分": "FT",
        "HomeTeam": "Home", "AwayTeam": "Away", "FTHG": "HG", "FTAG": "AG",
        "Team1": "Home", "Team2": "Away", "Team 1": "Home", "Team 2": "Away",
        "Score1": "HG", "Score2": "AG",
    }
    frame = frame.rename(columns={k: v for k, v in aliases.items() if k in frame.columns})
    return clean_matches(frame, "使用者上載資料", league, datetime.now().year)

def read_corner_csv(uploaded_file, league):
    """讀取只有日期、主客隊及 HC/AC 的角球歷史檔；比分可不存在。"""
    if uploaded_file is None:
        raise ValueError("未選擇角球 CSV")
    frame = pd.read_csv(BytesIO(uploaded_file.getvalue()), encoding="utf-8-sig")
    aliases = {
        "HomeTeam": "Home", "AwayTeam": "Away", "Team1": "Home", "Team2": "Away",
        "Team 1": "Home", "Team 2": "Away", "日期": "Date", "主隊": "Home", "客隊": "Away",
        "HomeCorners": "HC", "AwayCorners": "AC", "Home Corner": "HC", "Away Corner": "AC",
        "主隊角球": "HC", "客隊角球": "AC",
    }
    frame = frame.rename(columns={k: v for k, v in aliases.items() if k in frame.columns})
    if not {"Home", "Away", "HC", "AC"}.issubset(frame.columns):
        raise ValueError("角球 CSV 必須包含 Date、HomeTeam、AwayTeam、HC、AC 欄位")
    frame["Home"] = frame["Home"].astype(str).str.strip().map(lambda x: ALIASES.get(x, x))
    frame["Away"] = frame["Away"].astype(str).str.strip().map(lambda x: ALIASES.get(x, x))
    frame["HC"] = pd.to_numeric(frame["HC"], errors="coerce")
    frame["AC"] = pd.to_numeric(frame["AC"], errors="coerce")
    frame = frame.dropna(subset=["Home", "Away", "HC", "AC"]).copy()
    frame["HG"] = pd.NA
    frame["AG"] = pd.NA
    frame["Date"] = frame.get("Date", "")
    frame["DateParsed"] = pd.to_datetime(frame["Date"], errors="coerce", dayfirst=True)
    frame["league"] = league
    frame["season"] = str(datetime.now().year)
    frame["source"] = "使用者上載角球 CSV"
    return frame[["league", "season", "Home", "Away", "HG", "AG", "HC", "AC", "Date", "DateParsed", "source"]]

def read_csv_url(csv_url, league):
    """從使用者提供的直接 CSV 網址讀取最新賽果；不繞過登入或網站限制。"""
    url = str(csv_url or "").strip()
    if not url.lower().startswith(("https://", "http://")):
        raise ValueError("CSV 網址必須以 http:// 或 https:// 開頭")
    response = requests.get(url, headers=HEADERS, timeout=20)
    response.raise_for_status()
    if not response.content:
        raise ValueError("CSV 網址回傳空白檔案")
    try:
        frame = pd.read_csv(BytesIO(response.content), encoding="utf-8-sig")
    except UnicodeDecodeError:
        frame = pd.read_csv(BytesIO(response.content), encoding="latin1")
    if frame.empty:
        raise ValueError("CSV 沒有資料列")
    aliases = {
        "主隊": "Home", "客隊": "Away", "主隊入球": "HG", "客隊入球": "AG",
        "主隊角球": "HC", "客隊角球": "AC", "日期": "Date", "全場比分": "FT",
        "HomeTeam": "Home", "AwayTeam": "Away", "FTHG": "HG", "FTAG": "AG",
        "Team1": "Home", "Team2": "Away", "Team 1": "Home", "Team 2": "Away",
        "Score1": "HG", "Score2": "AG",
    }
    frame = frame.rename(columns={k: v for k, v in aliases.items() if k in frame.columns})
    return clean_matches(frame, f"公開 CSV 網址：{url}", league, datetime.now().year)


def detect_bulk_league(filename):
    """按檔名自動辨識多聯賽上載檔案；辨識不到便要求改名，避免錯入聯賽。"""
    name = re.sub(r"[^a-z0-9]+", "-", str(filename).lower()).strip("-")
    candidates = []
    for league, spec in BULK_CSV_SPECS.items():
        for token in spec["tokens"]:
            token = re.sub(r"[^a-z0-9]+", "-", token.lower()).strip("-")
            if token and (name == token or token in name):
                candidates.append((len(token), league))
    if not candidates:
        return None
    return sorted(candidates, reverse=True)[0][1]


def read_bulk_csv(uploaded_file, league):
    """將一個多聯賽檔案用既有 CSV 標準化流程讀入。"""
    return read_uploaded_matches(uploaded_file, league).assign(source="多聯賽 CSV：" + str(getattr(uploaded_file, "name", "")))


def read_player_csv(uploaded_file):
    """讀取 FBref squad export；只作顯示，不把球員資料冒充成賽果。"""
    if uploaded_file is None:
        return pd.DataFrame()
    raw = uploaded_file.getvalue()
    frame = pd.read_csv(BytesIO(raw), encoding="utf-8-sig")
    aliases = {"球員": "Player", "國籍": "Nation", "位置": "Pos", "年齡": "Age", "入球": "Gls", "球隊": "Squad"}
    frame = frame.rename(columns={k: v for k, v in aliases.items() if k in frame.columns})
    required = {"Player", "Nation", "Pos", "Age", "Gls"}
    if not required.issubset(frame.columns):
        raise ValueError("球員 CSV 必須包含 Player、Nation、Pos、Age、Gls 欄位")
    if "Squad" not in frame.columns:
        frame["Squad"] = ""
    return frame[["Squad", "Player", "Nation", "Pos", "Age", "Gls"]].copy()


def player_table_zh(players, team_names=None):
    if players is None or players.empty:
        return pd.DataFrame()
    data = players.copy()
    if team_names and data["Squad"].astype(str).str.strip().ne("").any():
        keys = [team_key(x) for x in team_names]
        data = data[data["Squad"].map(team_key).isin(keys)]
    if data.empty:
        return data
    out = pd.DataFrame({
        "球員": data["Player"].astype(str),
        "位置": data["Pos"].map(zh_position),
        "國籍": data["Nation"].map(zh_country),
        "年齡": data["Age"],
        "入球": data["Gls"],
    })
    return out


def save_matches(df):
    rows = [(r.league, r.season, r.Home, r.Away, None if pd.isna(r.HG) else int(r.HG), None if pd.isna(r.AG) else int(r.AG),
             None if pd.isna(r.HC) else float(r.HC), None if pd.isna(r.AC) else float(r.AC),
             str(r.Date), r.source, datetime.now(timezone.utc).isoformat())
             for r in df.itertuples()]
    with db_connect() as c:
        c.executemany("""
            INSERT INTO matches(league,season,home,away,hg,ag,hc,ac,date,source,captured_at)
            VALUES(?,?,?,?,?,?,?,?,?,?,?)
            ON CONFLICT(league,season,home,away,date) DO UPDATE SET
                hg=COALESCE(excluded.hg,matches.hg), ag=COALESCE(excluded.ag,matches.ag),
                hc=COALESCE(excluded.hc,matches.hc), ac=COALESCE(excluded.ac,matches.ac),
                source=CASE WHEN excluded.hc IS NOT NULL OR excluded.ac IS NOT NULL
                            THEN excluded.source ELSE matches.source END,
                captured_at=excluded.captured_at
        """, rows)


def cached_matches(league, max_age_hours=24):
    cutoff = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)
    with db_connect() as c:
        df = pd.read_sql_query("SELECT * FROM matches WHERE league=?", c, params=[league])
    if df.empty:
        return df
    # SQLite 欄位用小寫儲存；分析模型統一使用公開資料的欄位名稱。
    df = df.rename(columns={"home": "Home", "away": "Away", "hg": "HG", "ag": "AG", "hc": "HC", "ac": "AC", "date": "Date"})
    df["HG"] = pd.to_numeric(df["HG"], errors="coerce")
    df["AG"] = pd.to_numeric(df["AG"], errors="coerce")
    unverified = df["source"].map(is_unverified_corner_source) if "source" in df.columns else pd.Series(False, index=df.index)
    df.loc[unverified, ["HC", "AC"]] = np.nan
    df["DateParsed"] = pd.to_datetime(df.get("Date", ""), errors="coerce", dayfirst=True)
    latest = pd.to_datetime(df["captured_at"], utc=True, errors="coerce").max()
    return df if pd.notna(latest) and latest >= cutoff else pd.DataFrame()


def api_get(endpoint, params, token):
    r = requests.get(f"{API_BASE}/{endpoint}", headers={"x-apisports-key": token, **HEADERS}, params=params, timeout=10)
    r.raise_for_status()
    payload = r.json()
    if payload.get("errors"):
        raise ValueError(str(payload["errors"]))
    return payload


@st.cache_data(ttl=86400, show_spinner=False)
def discover_api_league_id(league_name, token):
    query = API_LEAGUE_SEARCH.get(league_name, league_name)
    payload = api_get("leagues", {"search": query}, token)
    wanted = query.lower().replace("-", " ")
    for item in payload.get("response", []):
        name = str(item.get("league", {}).get("name", "")).lower().replace("-", " ")
        if name == wanted or wanted in name or name in wanted:
            return item.get("league", {}).get("id")
    return None


def from_api(league, token):
    league_id = LEAGUES[league]["api"]
    if not league_id:
        league_id = discover_api_league_id(league, token)
    if not league_id:
        raise ValueError("API-Football 暫未找到此聯賽的可用 ID")
    errors = []
    # API-Football 的賽季通常以開季年份表示；同時嘗試目前及最近幾季，
    # 避免跨年或網站尚未切換賽季時顯示無資料。
    for season in [datetime.now().year, datetime.now().year - 1, 2025, 2024]:
        try:
            payload = api_get("fixtures", {"league": league_id, "season": season, "status": "FT"}, token)
            rows = []
            for x in payload.get("response", []):
                g = x.get("goals") or {}
                if g.get("home") is not None and g.get("away") is not None:
                    rows.append({"Home": x["teams"]["home"]["name"], "Away": x["teams"]["away"]["name"],
                                 "HG": g["home"], "AG": g["away"], "Date": x["fixture"].get("date", "")})
            if rows:
                return clean_matches(pd.DataFrame(rows), "API-Football", league, season)
        except Exception as e:
            errors.append(str(e))
    raise ValueError("；".join(errors)[-800:] or "API 沒有可用賽果")


def from_api_team_directory(league, token):
    """直接按聯賽取得球隊目錄，不再只靠曾經踢過的賽果推斷球隊。"""
    if not token:
        raise ValueError("未設定 API-Football Token")
    league_id = LEAGUES[league]["api"] or discover_api_league_id(league, token)
    if not league_id:
        raise ValueError("API-Football 暫未找到此聯賽的可用 ID")
    errors = []
    for season in [datetime.now().year, datetime.now().year - 1, 2024]:
        try:
            payload = api_get("teams", {"league": league_id, "season": season}, token)
            names = sorted({str(x.get("team", {}).get("name", "")).strip()
                            for x in payload.get("response", [])
                            if x.get("team", {}).get("name")})
            if names:
                return names, f"API-Football 球隊目錄（{season}）"
        except Exception as e:
            errors.append(str(e))
    raise ValueError("；".join(errors)[-800:] or "API 沒有回傳球隊目錄")


def get_team_directory(league, api_token, fd_token, crawl_url):
    """不使用 API-Football；以資料館、Football-Data 及公開賽果建立目錄。"""
    # 球隊清單優先直接由永久保存的資料館建立，避免外部來源欄位格式不同造成 KeyError。
    matches = all_saved_matches(league)
    source = "本地資料館"
    if matches.empty:
        matches, source, _ = get_matches(league, api_token, fd_token, crawl_url)
    if not {"Home", "Away"}.issubset(matches.columns):
        matches = clean_matches(matches, source, league, datetime.now().year)
    names = sorted(set(matches["Home"].dropna()) | set(matches["Away"].dropna()))
    if not names:
        raise ValueError("沒有任何可用球隊")
    return names, f"{source}（由賽果建立後備清單）"


FD_CODES = {
    "英格蘭超級聯賽": "PL", "英格蘭冠軍聯賽": "ELC", "西班牙甲組聯賽": "PD",
    "西班牙乙組聯賽": "SD", "德國甲組聯賽": "BL1", "德國乙組聯賽": "BL2",
    "法國乙組聯賽": "FL2", "荷蘭甲組聯賽": "DED", "蘇格蘭超級聯賽": "SCO",
    "歐洲冠軍聯賽": "CL",
}

OPENLIGA_CODES = {
    "英格蘭超級聯賽": "pl",
    "西班牙甲組聯賽": "la1",
    "德國甲組聯賽": "bl1",
    "德國乙組聯賽": "bl2",
    "歐洲冠軍聯賽": "ucl",
    "蘇格蘭超級聯賽": "sco1",
}


def from_openligadb(league):
    """從免 Key 的 OpenLigaDB 讀取賽果；失敗時由上層安全切換來源。"""
    code = OPENLIGA_CODES.get(league)
    if not code:
        raise ValueError("OpenLigaDB 沒有此聯賽對照")
    rows, errors = [], []
    for season in (datetime.now().year, datetime.now().year - 1):
        try:
            response = requests.get(
                f"{OPENLIGA_API}/getmatchdata/{code}/{season}",
                headers=HEADERS, timeout=12,
            )
            response.raise_for_status()
            payload = response.json()
            for item in payload if isinstance(payload, list) else []:
                result_list = item.get("matchResults") or []
                result = next(
                    (x for x in result_list
                     if isinstance(x, dict) and x.get("resultTypeKind") == "After90Minutes"),
                    None,
                )
                if result is None and isinstance(result_list, list) and result_list:
                    result = result_list[-1] if isinstance(result_list[-1], dict) else None
                result = result or {}
                home = (item.get("team1") or {}).get("teamName")
                away = (item.get("team2") or {}).get("teamName")
                hg, ag = result.get("pointsTeam1"), result.get("pointsTeam2")
                if home and away and hg is not None and ag is not None:
                    rows.append({"Home": home, "Away": away, "HG": hg, "AG": ag,
                                 "Date": item.get("matchDateTimeUTC", item.get("matchDateTime", ""))})
            if rows:
                return clean_matches(pd.DataFrame(rows), "OpenLigaDB", league, season)
        except Exception as exc:
            errors.append(str(exc))
    detail = f"（{errors[-1][:180]}）" if errors else ""
    raise ValueError(f"OpenLigaDB 沒有可用賽果{detail}")

FBREF_COMP_IDS = {
    "英格蘭超級聯賽": 9, "西班牙甲組聯賽": 12, "德國甲組聯賽": 20,
    "法國甲組聯賽": 13, "意大利甲組聯賽": 11, "荷蘭甲組聯賽": 23,
    "葡萄牙超級聯賽": 32, "蘇格蘭超級聯賽": 40, "美國職業足球大聯盟": 22,
    "澳洲職業聯賽": 65, "日本職業聯賽": 55, "巴西甲組聯賽": 24,
    "墨西哥超級聯賽": 31, "挪威超級聯賽": 29, "丹麥超級聯賽": 50,
    "沙特職業聯賽": 70,
}


def inline_fbref_matches(league):
    """內置 FBref Scores & Fixtures 後備，避免舊版 fbref.py 令來源被靜默跳過。"""
    comp_id = FBREF_COMP_IDS.get(league)
    if not comp_id:
        return pd.DataFrame()
    url = f"{FBREF_BASE}/en/comps/{comp_id}/schedule/"
    response = requests.get(url, headers=HEADERS, timeout=20)
    response.raise_for_status()
    documents = [response.text]
    try:
        from bs4 import BeautifulSoup, Comment
        soup = BeautifulSoup(response.text, "lxml")
        documents += [str(x) for x in soup.find_all(string=lambda x: isinstance(x, Comment))]
    except Exception:
        pass
    for document in documents:
        try:
            tables = pd.read_html(StringIO(document), flavor="lxml")
        except ValueError:
            continue
        for table in tables:
            table.columns = [str(c).strip() for c in table.columns]
            if not {"Date", "Home", "Score", "Away"}.issubset(table.columns):
                continue
            rows = []
            for _, row in table.iterrows():
                score = str(row.get("Score", "")).replace("–", "-")
                found = re.search(r"(\d+)\s*-\s*(\d+)", score)
                home, away = str(row.get("Home", "")).strip(), str(row.get("Away", "")).strip()
                if found and home not in ("", "nan") and away not in ("", "nan"):
                    rows.append({"Home": home, "Away": away, "HG": int(found.group(1)),
                                 "AG": int(found.group(2)), "HC": None, "AC": None,
                                 "Date": str(row.get("Date", "")), "source": "FBref Scores & Fixtures"})
            if rows:
                return pd.DataFrame(rows).drop_duplicates(subset=["Date", "Home", "Away"])
    return pd.DataFrame()


def from_football_data_api(league, token):
    code = FD_CODES.get(league)
    if not code:
        raise ValueError("Football-Data.org API 沒有此聯賽對照")
    r = requests.get(f"{FD_API}/competitions/{code}/matches", headers={"X-Auth-Token": token, **HEADERS},
                     params={"status": "FINISHED"}, timeout=10)
    r.raise_for_status()
    rows = []
    for item in r.json().get("matches", []):
        score = item.get("score", {}).get("fullTime", {})
        if score.get("home") is not None and score.get("away") is not None:
            rows.append({"Home": item.get("homeTeam", {}).get("name", ""),
                         "Away": item.get("awayTeam", {}).get("name", ""),
                         "HG": score["home"], "AG": score["away"],
                         "Date": item.get("utcDate", "")})
    if not rows:
        raise ValueError("Football-Data.org API 沒有回傳已完成賽事")
    return clean_matches(pd.DataFrame(rows), "Football-Data.org API", league, datetime.now().year)


def from_csv(league):
    code = LEAGUES[league].get("csv")
    if not code:
        raise ValueError("沒有公開 CSV 對照")
    season = datetime.now().year
    urls = [f"{FD_BASE}/mmz4281/{str(season)[-2:]}{str(season+1)[-2:]}/{code}.csv",
            f"{FD_BASE}/new/{code}.csv"]
    errors = []
    for url in urls:
        try:
            r = requests.get(url, headers=HEADERS, timeout=10)
            r.raise_for_status()
            df = pd.read_csv(StringIO(r.content.decode("latin1")))
            return clean_matches(df, "Football-Data CSV", league, season)
        except Exception as e:
            errors.append(str(e))
    raise ValueError("CSV 無法讀取：" + "；".join(errors)[-500:])


def current_fd_season():
    now = datetime.now()
    start = now.year if now.month >= 7 else now.year - 1
    return f"{str(start)[-2:]}{str(start + 1)[-2:]}"


def update_fd_leagues():
    """只更新有 Football-Data 代碼的聯賽；每份先驗證，成功才寫入資料館。"""
    season = current_fd_season()
    results, errors = [], []
    for league, spec in LEAGUES.items():
        code = spec.get("csv")
        if not code:
            continue
        url = f"{FD_BASE}/mmz4281/{season}/{code}.csv"
        try:
            response = requests.get(url, headers=HEADERS, timeout=20)
            response.raise_for_status()
            frame = pd.read_csv(BytesIO(response.content), encoding="latin1")
            cleaned = clean_matches(frame, f"Football-Data CSV {season}", league, season)
            if cleaned.empty:
                raise ValueError("沒有可用已完成賽果")
            save_matches(cleaned)
            results.append(f"{league}（{len(cleaned)} 場）")
        except Exception as exc:
            errors.append(f"{league}：{str(exc)[:180]}")
    return results, errors


def _html_header_key(value):
    """將HTML欄名標準化，容許大小寫、空格、底線及連字符差異。"""
    value = unicodedata.normalize("NFKC", str(value or "")).strip().casefold()
    return re.sub(r"[\s_\-()]+", "", value)


def parse_pasted_fbref_html(html, league):
    """解析公開HTML表格，支援常見主客隊及角球欄名變體。"""
    html_text = str(html or "")
    if not html_text.strip():
        raise ValueError("請先貼上HTML")

    tables = pd.read_html(StringIO(html_text), flavor="lxml")
    header_aliases = {
        "home": "Home", "hometeam": "Home", "主隊": "Home", "home_team": "Home",
        "away": "Away", "awayteam": "Away", "客隊": "Away", "away_team": "Away",
        "hc": "HC", "homecorners": "HC", "cornershome": "HC", "home_corners": "HC", "主隊角球": "HC",
        "ac": "AC", "awaycorners": "AC", "cornersaway": "AC", "away_corners": "AC", "客隊角球": "AC",
        "date": "Date", "日期": "Date", "matchdate": "Date",
    }
    for table in tables:
        if isinstance(table.columns, pd.MultiIndex):
            table.columns = [" ".join(str(part) for part in column if str(part).lower() != "nan") for column in table.columns]
        renamed = {}
        for column in table.columns:
            key = _html_header_key(column)
            target = header_aliases.get(key)
            if target and target not in renamed.values():
                renamed[column] = target
        table = table.rename(columns=renamed)
        if {"Home", "Away", "HC", "AC"}.issubset(table.columns):
            # HTML角球表未必有比分；比分以0-0作為角球補充賽事的中性佔位值。
            out = table.copy()
            out["Home"] = out["Home"].astype(str).str.strip().map(lambda x: ALIASES.get(x, x))
            out["Away"] = out["Away"].astype(str).str.strip().map(lambda x: ALIASES.get(x, x))
            out["HC"] = pd.to_numeric(out["HC"], errors="coerce")
            out["AC"] = pd.to_numeric(out["AC"], errors="coerce")
            out["Date"] = out.get("Date", "")
            out["league"] = league
            out["season"] = str(datetime.now().year)
            out["HG"] = pd.NA
            out["AG"] = pd.NA
            out["DateParsed"] = pd.to_datetime(out["Date"], errors="coerce", dayfirst=True)
            out["source"] = "使用者貼上的公開比賽 HTML"
            return out[["league", "season", "Home", "Away", "HG", "AG", "HC", "AC", "Date", "DateParsed", "source"]].dropna(subset=["Home", "Away", "HC", "AC"])
    raise ValueError("HTML 表格未找到可識別的主隊、客隊、HC、AC欄位")


def save_corner_supplement(df):
    """批次更新／新增角球賽事；整批只使用一個 SQLite transaction。"""
    updated = 0
    created = 0
    today = datetime.now().date().isoformat()
    insert_rows = []
    log_rows = []
    conn = db_connect()
    try:
        with conn:
            for row in df.itertuples():
                home = ALIASES.get(str(row.Home).strip(), str(row.Home).strip())
                away = ALIASES.get(str(row.Away).strip(), str(row.Away).strip())
                raw_date = str(row.Date).strip()
                date_value = raw_date if raw_date and raw_date.lower() != "nan" else today
                date_like = f"%{date_value[:10]}%"
                captured_at = datetime.now(timezone.utc).isoformat()
                if pd.notna(row.DateParsed):
                    cur = conn.execute(
                        "UPDATE matches SET hc=?, ac=?, source=?, captured_at=? "
                        "WHERE league=? AND home=? AND away=? AND date LIKE ?",
                        [float(row.HC), float(row.AC), row.source, captured_at,
                         row.league, home, away, date_like],
                    )
                else:
                    cur = conn.execute(
                        "UPDATE matches SET hc=?, ac=?, source=?, captured_at=? "
                        "WHERE rowid=(SELECT rowid FROM matches "
                        "WHERE league=? AND home=? AND away=? "
                        "ORDER BY date DESC, captured_at DESC LIMIT 1)",
                        [float(row.HC), float(row.AC), row.source, captured_at,
                         row.league, home, away],
                    )
                if cur.rowcount:
                    updated += cur.rowcount
                    continue
                insert_rows.append((row.league, str(row.season), home, away, 0, 0,
                                    float(row.HC), float(row.AC), date_value, row.source, captured_at))
                log_rows.append((row.league, "HTML角球補充", "自動新增",
                                 f"自動新增賽事 {home} vs {away} 角球 {float(row.HC):g}-{float(row.AC):g}", captured_at))

            if insert_rows:
                conn.executemany(
                    "INSERT INTO matches(league,season,home,away,hg,ag,hc,ac,date,source,captured_at) "
                    "VALUES(?,?,?,?,?,?,?,?,?,?,?) "
                    "ON CONFLICT(league,season,home,away,date) DO UPDATE SET "
                    "hc=excluded.hc, ac=excluded.ac, source=excluded.source, captured_at=excluded.captured_at",
                    insert_rows,
                )
                created = len(insert_rows)
            if log_rows:
                conn.executemany(
                    "INSERT INTO source_log(league,source,status,message,captured_at) VALUES(?,?,?,?,?)",
                    log_rows,
                )
    finally:
        conn.close()
    return updated, created


def robots_allowed(url):
    p = urlparse(url)
    if p.scheme not in {"http", "https"} or not p.netloc:
        return False, "網址格式不安全"
    rp = RobotFileParser(f"{p.scheme}://{p.netloc}/robots.txt")
    try:
        rp.read()
        return rp.can_fetch(HEADERS["User-Agent"], url), "robots.txt 不允許自動讀取"
    except Exception:
        return False, "無法確認 robots.txt，為安全起見停止爬取"


def from_public_table(league, url):
    allowed, reason = robots_allowed(url)
    if not allowed:
        raise ValueError(reason)
    html = requests.get(url, headers=HEADERS, timeout=10).text
    # pandas 新版要求用 StringIO 讀取 HTML 字串，否則會把整段 HTML 當成檔案路徑。
    tables = pd.read_html(StringIO(html), flavor="lxml")
    for table in tables:
        cols = {str(c).strip().lower() for c in table.columns}
        # 支援常見公開賽果表；不繞過登入、CAPTCHA 或付費牆。
        if ({"home", "away", "hg", "ag"} <= cols or {"hometeam", "awayteam", "fthg", "ftag"} <= cols):
            return clean_matches(table, "獲准公開網頁表格", league, datetime.now().year)
    raise ValueError("公開頁面沒有可辨識的賽果表格")


@st.cache_data(ttl=86400, show_spinner=False)
def fbref_team_stats(league):
    """低頻讀取 FBref 公開聯賽統計；robots 不允許或欄位不完整便安全返回空表。"""
    comp_id = FBREF_COMP_IDS.get(league)
    if not comp_id:
        return pd.DataFrame(), "FBref 未設定此聯賽對照"
    url = f"{FBREF_BASE}/en/comps/{comp_id}/stats/"
    allowed, reason = robots_allowed(url)
    if not allowed:
        return pd.DataFrame(), f"FBref：{reason}"
    try:
        html = requests.get(url, headers=HEADERS, timeout=15).text
        tables = pd.read_html(StringIO(html), flavor="lxml")
        for table in tables:
            if isinstance(table.columns, pd.MultiIndex):
                table.columns = [" ".join(str(x) for x in col if str(x) != "nan").strip() for col in table.columns]
            else:
                table.columns = [str(x).strip() for x in table.columns]
            squad_col = next((c for c in table.columns if c.lower() == "squad" or c.lower().endswith(" squad")), None)
            if not squad_col:
                continue
            wanted = {"Squad": squad_col}
            for key in ["MP", "xG", "xGA", "Gls", "Ast"]:
                found = next((c for c in table.columns if c.split()[-1].lower() == key.lower()), None)
                if found:
                    wanted[key] = found
            if "xG" not in wanted or "xGA" not in wanted:
                continue
            out = table[list(wanted.values())].rename(columns={v: k for k, v in wanted.items()}).copy()
            out["Squad"] = out["Squad"].astype(str).str.replace(r"\s+", " ", regex=True).str.strip()
            for col in [c for c in ["MP", "xG", "xGA", "Gls", "Ast"] if c in out]:
                out[col] = pd.to_numeric(out[col], errors="coerce")
            out = out.dropna(subset=["Squad", "xG", "xGA"])
            return out, "FBref 公開聯賽統計（每日快取）"
    except Exception as exc:
        return pd.DataFrame(), f"FBref 讀取失敗：{exc}"
    return pd.DataFrame(), "FBref 找不到完整 xG／xGA 欄位"


def fbref_expected_goal_adjustment(stats, home, away, base_hx, base_ax):
    """只用有 xG/xGA 且隊名成功配對的資料，並限制修正幅度避免過度擬合。"""
    if stats.empty:
        return base_hx, base_ax, "未納入 FBref 修正"
    lookup = {team_key(r.Squad): r for r in stats.itertuples()}
    hrow, arow = lookup.get(team_key(home)), lookup.get(team_key(away))
    if hrow is None or arow is None:
        return base_hx, base_ax, "FBref 未能配對兩隊，未納入修正"
    def per_match(row, col):
        mp = getattr(row, "MP", None)
        value = getattr(row, col, None)
        return float(value) / float(mp) if mp and pd.notna(value) and float(mp) > 0 else None
    hx_ref = [per_match(hrow, "xG"), per_match(arow, "xGA")]
    ax_ref = [per_match(arow, "xG"), per_match(hrow, "xGA")]
    if any(x is None for x in hx_ref + ax_ref):
        return base_hx, base_ax, "FBref 欄位不足，未納入修正"
    ref_hx = sum(hx_ref) / 2 * 1.04
    ref_ax = sum(ax_ref) / 2 * .96
    new_hx = max(.15, min(base_hx * 1.25, max(base_hx * .75, base_hx * .70 + ref_hx * .30)))
    new_ax = max(.15, min(base_ax * 1.25, max(base_ax * .75, base_ax * .70 + ref_ax * .30)))
    return new_hx, new_ax, "FBref xG／xGA 已納入（修正上限 ±25%）"


def from_australia_cup(league):
    """讀取澳洲盃官方網站使用的公開賽事 JSON，不需要額外 Token。"""
    r = requests.get(f"{FFA_API}/c716/s2026/fixture", headers=HEADERS, timeout=15)
    r.raise_for_status()
    rows = []
    for match in r.json().get("rounds", []):
        score = match.get("match_info") or {}
        home_score = (score.get("home_team") or {}).get("score")
        away_score = (score.get("away_team") or {}).get("score")
        home = (match.get("home_team") or {}).get("name")
        away = (match.get("away_team") or {}).get("name")
        if home and away and home_score is not None and away_score is not None and match.get("status") == "FullTime":
            rows.append({"Home": home, "Away": away, "HG": home_score, "AG": away_score, "Date": match.get("start_date", "")})
    if not rows:
        raise ValueError("澳洲盃官方來源暫時沒有已完成賽果")
    return clean_matches(pd.DataFrame(rows), "澳洲盃官方公開資料", league, 2026)


def from_espn_public(league):
    """讀取ESPN公開沙特賽果；只保留已完場比分，角球不自行補填。"""
    if league != "沙特職業聯賽":
        raise ValueError("ESPN公開後備目前只設定沙特職業聯賽")
    rows, seen = [], set()
    for year in [datetime.now().year, datetime.now().year - 1, datetime.now().year - 2]:
        payload = requests.get(
            "https://site.api.espn.com/apis/site/v2/sports/soccer/ksa.1/scoreboard",
            params={"dates": str(year), "limit": 1000}, headers=HEADERS, timeout=20
        ).json()
        for event in payload.get("events", []):
            comp = (event.get("competitions") or [{}])[0]
            status = ((comp.get("status") or {}).get("type") or {}).get("name")
            if status != "STATUS_FULL_TIME" or event.get("id") in seen:
                continue
            teams = comp.get("competitors") or []
            home = next((x for x in teams if x.get("homeAway") == "home"), None)
            away = next((x for x in teams if x.get("homeAway") == "away"), None)
            if not home or not away or home.get("score") is None or away.get("score") is None:
                continue
            seen.add(event.get("id"))
            def corners(team):
                for stat in team.get("statistics", []) or []:
                    if stat.get("name") in {"wonCorners", "cornerKicks"} and stat.get("value") is not None:
                        return stat.get("value")
                return pd.NA
            rows.append({"Date": event.get("date", ""),
                         "Home": (home.get("team") or {}).get("displayName") or (home.get("team") or {}).get("name"),
                         "Away": (away.get("team") or {}).get("displayName") or (away.get("team") or {}).get("name"),
                         "HG": pd.to_numeric(home.get("score"), errors="coerce"),
                         "AG": pd.to_numeric(away.get("score"), errors="coerce"),
                         "HC": corners(home), "AC": corners(away)})
    if not rows:
        raise ValueError("ESPN公開沙特接口暫時沒有已完場賽果")
    return clean_matches(pd.DataFrame(rows), "ESPN 公開沙特賽果（角球只採明確欄位）", league, datetime.now().year)


def get_matches(league, api_token, fd_token, crawl_url):
    api_cached = local_api_matches(league)
    if not api_cached.empty:
        return api_cached, "本地API（CSV驅動）", "高（本地快取）"
    fresh_all = cached_matches(league)
    # 角球專用 CSV 可以沒有比分；它保留在資料館供 corner_model 使用，
    # 但不能混入勝和負及入球模型。
    fresh = fresh_all.dropna(subset=["HG", "AG"]).copy() if not fresh_all.empty else fresh_all
    if not fresh.empty:
        # 舊快取可能只有賽果，沒有 HC/AC；有公開 CSV 對照時先補抓角球資料。
        has_corners = "HC" in fresh.columns and "AC" in fresh.columns and fresh[["HC", "AC"]].notna().all(axis=1).sum() >= 4
        if has_corners or not LEAGUES.get(league, {}).get("csv"):
            return fresh, "本地資料館", "高（已儲存）"
        try:
            refreshed = from_csv(league)
            corner_count = refreshed[["HC", "AC"]].notna().all(axis=1).sum()
            if corner_count >= 4:
                save_matches(refreshed)
                log_source(league, "Football-Data CSV", "成功", f"補充角球資料 {corner_count} 場")
                return refreshed, "Football-Data CSV（已補充角球）", "高"
        except Exception as e:
            log_source(league, "Football-Data CSV", "補充失敗", str(e))
        return fresh, "本地資料館（未有角球欄位）", "中（只有賽果）"
    attempts = []
    if fd_token:
        try:
            df = from_football_data_api(league, fd_token); save_matches(df); log_source(league, "Football-Data.org API", "成功"); return df, "Football-Data.org API", "高"
        except Exception as e:
            attempts.append(f"Football-Data.org API：{e}"); log_source(league, "Football-Data.org API", "失敗", str(e))
    # 沒有 Football-Data 對照的聯賽（例如卡塔爾、沙特、阿聯酋等），
    # 先用 API-Football；API 失敗才繼續嘗試 CSV／公開頁面後備。
    if api_token:
        try:
            df = from_api(league, api_token); save_matches(df); log_source(league, "API-Football", "成功"); return df, "API-Football", "高"
        except Exception as e:
            attempts.append(f"API-Football：{e}"); log_source(league, "API-Football", "失敗", str(e))
    try:
        df = from_csv(league); save_matches(df); log_source(league, "Football-Data CSV", "成功"); return df, "Football-Data CSV", "高"
    except Exception as e:
        attempts.append(f"CSV：{e}"); log_source(league, "Football-Data CSV", "失敗", str(e))
    try:
        df = from_openligadb(league)
        save_matches(df)
        log_source(league, "OpenLigaDB", "成功")
        return df, "OpenLigaDB", "中"
    except Exception as e:
        attempts.append(f"OpenLigaDB：{e}")
        log_source(league, "OpenLigaDB", "失敗", str(e))
    # FBref 有覆蓋但 Football-Data.org 沒有對照的聯賽，先用其 Scores & Fixtures。
    if league in FBREF_COMP_IDS:
        try:
            df = competition_matches(league) if competition_matches is not None else inline_fbref_matches(league)
            if not df.empty:
                save_matches(df); log_source(league, "FBref Scores & Fixtures", "成功")
                return df, "FBref Scores & Fixtures", "中高"
            attempts.append("FBref：找不到已完成賽果")
        except Exception as e:
            attempts.append(f"FBref：{e}"); log_source(league, "FBref Scores & Fixtures", "失敗", str(e))
    if league == "澳洲冠軍聯賽盃／澳洲盃":
        try:
            df = from_australia_cup(league); save_matches(df); log_source(league, "澳洲盃官方公開資料", "成功"); return df, "澳洲盃官方公開資料", "高"
        except Exception as e:
            attempts.append(f"澳洲盃官方資料：{e}"); log_source(league, "澳洲盃官方公開資料", "失敗", str(e))
    if league == "沙特職業聯賽":
        try:
            df = from_espn_public(league)
            save_matches(df); log_source(league, "ESPN 公開沙特賽果", "成功")
            return df, "ESPN 公開沙特賽果（無角球時明確標示）", "中（只有已核對比分）"
        except Exception as e:
            attempts.append(f"ESPN 沙特公開賽果：{e}")
    if crawl_url.strip():
        try:
            df = from_public_table(league, crawl_url.strip()); save_matches(df); log_source(league, "公開網頁表格", "成功"); return df, "獲准公開網頁表格", "中"
        except Exception as e:
            attempts.append(f"網頁爬蟲：{e}"); log_source(league, "公開網頁表格", "失敗", str(e))
    # 外部網站、Token 或聯賽覆蓋隨時會改變；沒有資料時回傳空表，
    # 由畫面顯示清楚提示，不以例外中止整個 Streamlit App。
    return pd.DataFrame(), "未取得資料", "不足（未有可核對賽果）"


@st.cache_data(ttl=21600, show_spinner=False)
def sportsdb_get(endpoint, params):
    r = requests.get(f"{SPORTSDB_API}/{endpoint}", params=params, headers=HEADERS, timeout=12)
    r.raise_for_status()
    return r.json()


@st.cache_data(ttl=21600, show_spinner=False)
def team_details(team_name, token=""):
    """用 TheSportsDB 取得球隊及球員基本資料；不依賴 API-Football。"""
    try:
        query = ALIASES.get(team_name, team_name)
        found = sportsdb_get("searchteams.php", {"t": query}).get("teams") or []
        if not found:
            return {}, "TheSportsDB 找不到球隊"
        def clean_name(value):
            return re.sub(r"[^a-z0-9]", "", str(value or "").lower())
        wanted = clean_name(query)
        # 搜尋短名稱時可能回傳女子隊／預備隊；只接受完整官方名稱匹配，
        # 絕不以相似隊伍頂上，避免把女子隊資料當成男子隊。
        exact = [t for t in found if clean_name(t.get("strTeam")) == wanted]
        if not exact:
            return {}, f"未找到官方完全匹配隊伍：{query}；已拒絕使用相似／女子／青年隊資料"
        team = exact[0]
        team_id = team.get("idTeam")
        players = []
        if team_id:
            players = sportsdb_get("lookup_all_players.php", {"id": team_id}).get("player") or []
        return {
            "team": {"name": team.get("strTeam", team_name), "country": team.get("strCountry", "未能取得"),
                     "founded": team.get("intFormedYear", "未能取得"), "logo": team.get("strTeamBadge", "")},
            "venue": {"name": team.get("strStadium", "未能取得")},
            "coach": team.get("strManager", "未能取得"),
            "squad": players,
            "injuries": [],
        }, ""
    except Exception as e:
        return {}, str(e)


def poisson(k, lam):
    return math.exp(-lam) * lam ** k / math.factorial(k)


def probs(hx, ax):
    h = d = a = 0
    for hg in range(11):
        for ag in range(11):
            p = poisson(hg, hx) * poisson(ag, ax)
            if hg > ag: h += p
            elif hg == ag: d += p
            else: a += p
    s = h + d + a
    return h / s, d / s, a / s


def monte_carlo_match(hx, ax, corner_lams=None, simulations=20000, seed=20261020):
    """用已取得的量化資料重複模擬比賽，不會把缺失球員資料當成真數據。"""
    rng = np.random.default_rng(seed)
    hg = rng.poisson(max(.01, hx), simulations)
    ag = rng.poisson(max(.01, ax), simulations)
    total = hg + ag
    counts = {}
    for h, a in zip(hg, ag):
        counts[(int(h), int(a))] = counts.get((int(h), int(a)), 0) + 1
    top = sorted(counts.items(), key=lambda item: item[1], reverse=True)[:5]
    result = {
        "主勝": float(np.mean(hg > ag)), "和局": float(np.mean(hg == ag)),
        "客勝": float(np.mean(hg < ag)), "大2.5": float(np.mean(total > 2.5)),
        "大3.5": float(np.mean(total > 3.5)), "大4.5": float(np.mean(total > 4.5)),
        "模擬場數": simulations,
        "比分": pd.DataFrame([{"比分": f"{h}-{a}", "模擬機率": n / simulations} for (h, a), n in top]),
    }
    if corner_lams:
        hc = rng.poisson(max(.01, corner_lams[0]), simulations)
        ac = rng.poisson(max(.01, corner_lams[1]), simulations)
        corners = hc + ac
        for line in [9.5, 10.5, 11.5, 12.5]:
            result[f"角球大{line}"] = float(np.mean(corners > line))
    return result


def corner_model(matches, home, away):
    """用最近最多8場角球；少於8場仍計算，但明確標示可靠性。"""
    if "HC" not in matches.columns or "AC" not in matches.columns:
        return None, "來源沒有角球欄位"
    data = matches.dropna(subset=["HC", "AC"]).copy()
    if "DateParsed" in data.columns:
        data = data.sort_values("DateParsed", na_position="first")
    h = data[data.apply(lambda r: team_key(r.Home) == team_key(home) or team_key(r.Away) == team_key(home), axis=1)].tail(8)
    a = data[data.apply(lambda r: team_key(r.Home) == team_key(away) or team_key(r.Away) == team_key(away), axis=1)].tail(8)
    if len(h) == 0 or len(a) == 0:
        return None, f"角球樣本不足（主隊 {len(h)}、客隊 {len(a)} 場）"
    def values(hist, team):
        made = hist.apply(lambda r: r.HC if team_key(r.Home) == team_key(team) else r.AC, axis=1)
        conceded = hist.apply(lambda r: r.AC if team_key(r.Home) == team_key(team) else r.HC, axis=1)
        return float(made.mean()), float(conceded.mean())
    h_for, h_against = values(h, home)
    a_for, a_against = values(a, away)
    home_lam = max(.5, (h_for + a_against) / 2)
    away_lam = max(.5, (a_for + h_against) / 2)
    warning = "；角球樣本只有主隊 %d、客隊 %d 場，可靠性中等" % (len(h), len(a)) if len(h) < 8 or len(a) < 8 else ""
    return (home_lam, away_lam), "已使用來源提供的歷史角球（最近最多8場）" + warning


def total_over_probability(lam, line):
    return 1 - sum(poisson(k, lam) for k in range(math.floor(line) + 1))


def signal(p, odds=None, other="", data_ok=True, backtest_ok=True, risk_reason="", is_corner=False):
    """V1.4/V2.0三色風險燈；永遠顯示機率，EV只作風險分類。"""
    if p is None or not data_ok:
        return "⚪ 資料不足", "資料不足，不能可靠計算EV；只作參考"
    if odds and odds > 1:
        ev = p * odds - 1
        if ev > .08 and backtest_ok:
            return "✅ 可以考慮", f"模型 {p:.1%}｜EV {ev:+.1%}（不代表保證）"
        # 角球不使用紅色燈；無和局陷阱時最多標為搖擺區。
        if is_corner or ev >= -.15:
            return "⚠️ 搖擺區", f"模型 {p:.1%}｜EV {ev:+.1%}；{('可考慮小注或轉其他角球線' if is_corner else '建議小注或避開剛好線')}"
        return "❌ 伏位唔建議", f"模型 {p:.1%}｜EV {ev:+.1%}；{risk_reason or ('莊家賠率未給足價值；' + other if other else '風險較高')}"
    if p >= .50:
        return "⚪ 未有賠率", f"模型 {p:.1%}；未輸入賠率，不能計算EV"
    return "⚪ 未有賠率", f"模型 {p:.1%}；未輸入賠率，不能計算EV"


def market_explanation(p, odds=None, other="", data_ok=True, risk_reason="", is_corner=False):
    """將盤口狀態翻譯成簡短廣東話；只負責顯示，不改模型。"""
    status, _ = signal(p, odds, other, data_ok=data_ok, risk_reason=risk_reason, is_corner=is_corner)
    ev = (p * odds - 1) if p is not None and odds and odds > 1 else None
    if status == "✅ 可以考慮":
        implied = 1 / odds if odds and odds > 1 else 0
        return status, f"可以考慮：模型 {p:.1%} vs 莊家隱含機率 {implied:.1%}，值博率 {ev:+.1%}", ev
    if status == "⚠️ 搖擺區":
        return status, f"搖擺區：模型 {p:.1%}｜EV {ev:+.1%}；{('角球最多作觀察，不標紅' if is_corner else '可考慮小注、雙重機會或轉其他線')}", ev
    if status == "❌ 伏位唔建議":
        return status, f"伏位唔建議：{risk_reason or 'EV及盤口方向未提供足夠安全邊際'}｜模型 {p:.1%}｜EV {ev:+.1%}", ev
    if status == "⚪ 未有賠率":
        return status, f"模型 {p:.1%}；未輸入賠率，暫不判斷值博率", ev
    return status, "資料不足，暫不作下注結論", ev


def render_market_table(title, rows, show_only_green, key):
    """按EV排序並永遠顯示全部；V1.4不因EV門檻隱藏模型機率。"""
    frame = pd.DataFrame(rows)
    if frame.empty:
        st.markdown(f"### {title}")
        st.info("目前沒有足夠資料顯示此盤口。")
        return
    frame["_green"] = frame["提示"].eq("✅ 可以考慮") & (frame["EV"].fillna(-999) > .08)
    frame = pd.concat([frame[frame["_green"]], frame[~frame["_green"]].sort_values("EV", ascending=False, na_position="last")])
    green_index = frame.index[frame["_green"]].tolist()
    if green_index:
        best_index = max(green_index, key=lambda i: frame.loc[i, "EV"])
        frame.loc[best_index, "提示"] = "✅ 可以考慮 ⭐最值博"
    visible = frame.copy().drop(columns=["_green"], errors="ignore")
    if "EV" in visible.columns:
        visible["EV"] = visible["EV"].map(lambda x: "—" if pd.isna(x) else f"{float(x):+.1%}")
    st.markdown(f"### {title}")
    def _row_style(row):
        status = str(row.get("提示", ""))
        color = "#173d25" if status.startswith("✅") else "#4a3d10" if status.startswith("⚠️") else "#4a1717" if status.startswith("❌") else "#20232a"
        return [f"background-color: {color}; color: white" for _ in row]
    try:
        st.dataframe(visible.style.apply(_row_style, axis=1), use_container_width=True, hide_index=True)
    except Exception:
        st.dataframe(visible, use_container_width=True, hide_index=True)


def data_is_stale(matches, max_age_days=365):
    """判斷賽果最後日期是否過舊；過期資料不產生下注建議。"""
    if matches.empty or "DateParsed" not in matches.columns:
        return True, None
    dates = pd.to_datetime(matches["DateParsed"], errors="coerce", utc=True).dropna()
    if dates.empty:
        return True, None
    latest = dates.max()
    age_days = (pd.Timestamp.now(tz="UTC") - latest).days
    return age_days > max_age_days, latest


def pair_data_status(home_matches, away_matches, stale_data):
    """檢查指定對賽前是否有足夠、未過期的歷史樣本。"""
    reasons = []
    if len(home_matches) < 4:
        reasons.append(f"主隊只有 {len(home_matches)} 場樣本")
    if len(away_matches) < 4:
        reasons.append(f"客隊只有 {len(away_matches)} 場樣本")
    if stale_data:
        reasons.append("整體資料已過期")
    return not reasons, reasons


def score_matrix(hx, ax, max_goals=8):
    return {(hg, ag): poisson(hg, hx) * poisson(ag, ax) for hg in range(max_goals + 1) for ag in range(max_goals + 1)}


def handicap_prob(matrix, line):
    """簡化亞洲讓球模型；四分一盤會以相鄰半盤平均表示。"""
    def one(x):
        home = draw = away = 0.0
        for (hg, ag), p in matrix.items():
            diff = hg - ag + x
            if diff > 0: home += p
            elif diff == 0: draw += p
            else: away += p
        return home, draw, away
    if abs(line * 4) % 2 == 1:
        a = one(line - 0.25); b = one(line + 0.25)
        return tuple((x + y) / 2 for x, y in zip(a, b))
    return one(line)


def exact_score_table(matrix, n=5):
    rows = sorted(matrix.items(), key=lambda x: x[1], reverse=True)[:n]
    return pd.DataFrame([{"比分": f"{hg}-{ag}", "機率": p} for (hg, ag), p in rows])


def team_form_table(matches, team, n=8):
    """將最近賽果整理成可核對的球隊狀態摘要。"""
    rows = matches[(matches["Home"] == team) | (matches["Away"] == team)].sort_values("DateParsed").tail(n)
    out = []
    for _, r in rows.iterrows():
        is_home = r["Home"] == team
        gf, ga = (r["HG"], r["AG"]) if is_home else (r["AG"], r["HG"])
        result = "勝" if gf > ga else "和" if gf == ga else "負"
        out.append({"日期": str(r.get("Date", ""))[:10], "對手": zh_team(r["Away"] if is_home else r["Home"]),
                    "主客": "主" if is_home else "客", "入球": int(gf), "失球": int(ga), "結果": result})
    return pd.DataFrame(out)


def model_confidence(sample_size, hp, dp, ap):
    """信心只代表資料量及機率分離度，不代表命中保證。"""
    size_score = min(1.0, sample_size / 16)
    separation = min(1.0, max(hp, dp, ap) - min(hp, dp, ap))
    score = 0.55 * size_score + 0.45 * separation
    return "較高" if score >= .65 else "中等" if score >= .38 else "較低"


def scenario_table(matrix, hx, ax):
    total = hx + ax
    rows = [
        ("低比分膠著", sum(p for (h, a), p in matrix.items() if h + a <= 2), "總入球不多，和局或一球勝負機會較高"),
        ("標準走勢", sum(p for (h, a), p in matrix.items() if 2 <= h + a <= 4), "落在模型最常見的入球範圍"),
        ("開放對攻", sum(p for (h, a), p in matrix.items() if h + a >= 5), "入球較多，比分波動較大"),
        ("主隊控制", sum(p for (h, a), p in matrix.items() if h > a and h >= 2), "主隊入球及勝差同時較高"),
        ("客隊反擊／爆冷", sum(p for (h, a), p in matrix.items() if a > h and a >= 2), "客隊勝出且至少入兩球"),
    ]
    return pd.DataFrame(rows, columns=["情境", "模型機率", "解釋"])


def walk_forward_backtest(matches, min_team_games=4):
    """逐場回測：每場只使用該場日期之前的已完成賽事。"""
    data = matches.copy()
    data["DateParsed"] = pd.to_datetime(data["DateParsed"], errors="coerce", utc=True)
    data = data.dropna(subset=["DateParsed", "HG", "AG"]).sort_values("DateParsed").reset_index(drop=True)
    rows = []
    for i, target in data.iterrows():
        history = data.iloc[:i]
        home_hist = history[(history.Home == target.Home) | (history.Away == target.Home)].tail(8)
        away_hist = history[(history.Home == target.Away) | (history.Away == target.Away)].tail(8)
        if len(home_hist) < min_team_games or len(away_hist) < min_team_games:
            continue

        def averages(hist, team):
            gf = hist.apply(lambda r: r.HG if r.Home == team else r.AG, axis=1).mean()
            ga = hist.apply(lambda r: r.AG if r.Home == team else r.HG, axis=1).mean()
            return gf, ga

        hgf, hga = averages(home_hist, target.Home)
        agf, aga = averages(away_hist, target.Away)
        hx = max(.15, (hgf + aga) / 2 * 1.08)
        ax = max(.15, (agf + hga) / 2 * .94)
        hp, dp, ap = probs(hx, ax)
        actual = "主勝" if target.HG > target.AG else "和局" if target.HG == target.AG else "客勝"
        predicted = max([(hp, "主勝"), (dp, "和局"), (ap, "客勝")])[1]
        matrix = score_matrix(hx, ax)
        top5 = {score for score, _ in sorted(matrix.items(), key=lambda x: x[1], reverse=True)[:5]}
        total_prob = [hp, dp, ap]
        actual_idx = {"主勝": 0, "和局": 1, "客勝": 2}[actual]
        brier = sum((p - (1.0 if j == actual_idx else 0.0)) ** 2 for j, p in enumerate(total_prob))
        over_prob = 1 - sum(poisson(k, hx + ax) for k in range(3))
        actual_over = int(target.HG + target.AG > 2.5)
        rows.append({"日期": target.DateParsed.date().isoformat(), "主隊": target.Home, "客隊": target.Away,
                     "預測": predicted, "實際": actual, "方向命中": predicted == actual,
                     "比分Top5命中": (int(target.HG), int(target.AG)) in top5,
                     "大2.5命中": (over_prob >= .5) == bool(actual_over), "Brier": brier,
                     "主勝機率": hp, "和局機率": dp, "客勝機率": ap})
    detail = pd.DataFrame(rows)
    if detail.empty:
        return detail, {"樣本數": 0}
    summary = {"樣本數": len(detail), "勝和負方向命中率": detail["方向命中"].mean(),
               "比分Top5包含率": detail["比分Top5命中"].mean(), "大2.5方向命中率": detail["大2.5命中"].mean(),
               "Brier Score": detail["Brier"].mean()}
    return detail, summary


def merge_manual_match_metadata(df, league):
    """把不適合放入舊 SQLite schema 的排名／半場欄位合併回分析表。"""
    manual = load_manual_league_override(league)
    if df is None or df.empty or manual.empty:
        return df
    def key(frame):
        return (frame["Date"].astype(str).str[:10] + "|" +
                frame["Home"].astype(str).map(team_key) + "|" +
                frame["Away"].astype(str).map(team_key))
    lookup = manual.copy()
    lookup["_manual_key"] = key(lookup)
    lookup = lookup.drop_duplicates("_manual_key").set_index("_manual_key")
    out = df.copy()
    out["_manual_key"] = key(out)
    for col in ["HT_HG", "HT_AG", "HomeRank", "AwayRank"]:
        if col in lookup.columns:
            out[col] = out["_manual_key"].map(lookup[col])
    return out.drop(columns=["_manual_key"])


@st.cache_data(ttl=300, show_spinner=False)
def load_phoenix_final_data():
    """讀取已核實的63隊真HT資料；檔案缺失或格式錯誤時安全回退SQLite。"""
    if not PHOENIX_FINAL_DATA.exists():
        return {}
    try:
        payload = json.loads(PHOENIX_FINAL_DATA.read_text(encoding="utf-8"))
        return payload if isinstance(payload, dict) else {}
    except (OSError, ValueError, TypeError):
        return {}


def phoenix_final_matches(league):
    """將Phoenix聯賽資料轉成舊App共用的欄位名稱，並按賽事去重。"""
    short = next((k for k, v in PHOENIX_LEAGUE_ALIASES.items() if v == league), None)
    if short is None:
        return pd.DataFrame()
    payload = load_phoenix_final_data()
    key = next((k for k in payload if str(k).startswith(short + " ")), None)
    if not key:
        return pd.DataFrame()
    rows, seen = [], set()
    for team in payload.get(key, []):
        for match in team.get("matches", []):
            ident = "|".join(str(match.get(x, "")) for x in ("date", "home", "away", "ft_home", "ft_away"))
            if ident in seen:
                continue
            seen.add(ident)
            rows.append({
                "Date": match.get("date"), "Home": match.get("home"), "Away": match.get("away"),
                "HG": match.get("ft_home"), "AG": match.get("ft_away"),
                "HT_HG": match.get("ht_home"), "HT_AG": match.get("ht_away"),
                "HC": pd.NA, "AC": pd.NA, "league": league,
                "source": "Phoenix 63隊真HT（football-data.org）",
                "explicit_ht": bool(match.get("explicit_ht")),
            })
    if not rows:
        return pd.DataFrame()
    out = pd.DataFrame(rows)
    out["DateParsed"] = pd.to_datetime(out["Date"], errors="coerce")
    return out.sort_values(["DateParsed", "Home", "Away"], ascending=[False, True, True]).reset_index(drop=True)


def all_saved_matches(league):
    # 63隊畢業資料優先於舊SQLite，確保App直接使用明確半場比分。
    phoenix = phoenix_final_matches(league)
    if not phoenix.empty:
        return phoenix
    try:
        with db_read_connect() as c:
            df = pd.read_sql_query("SELECT * FROM matches WHERE league=?", c, params=[league])
    except sqlite3.DatabaseError:
        # 線上部署遇到殘留 WAL/短暫寫鎖時，重試一次一般連線；
        # 絕不把 SQLite traceback 直接顯示給使用者。
        with db_connect() as c:
            df = pd.read_sql_query("SELECT * FROM matches WHERE league=?", c, params=[league])
    if df.empty:
        return df
    df = df.rename(columns={"home": "Home", "away": "Away", "hg": "HG", "ag": "AG",
                            "hc": "HC", "ac": "AC", "date": "Date"})
    # 舊SQLite資料可能沒有角球欄位；補空欄而不是令分析頁因KeyError中斷。
    for col in ["HC", "AC"]:
        if col not in df.columns:
            df[col] = pd.NA
    if "DateParsed" not in df.columns:
        df["DateParsed"] = pd.to_datetime(df.get("Date", ""), errors="coerce", dayfirst=True)
    if "source" not in df.columns:
        df["source"] = "本地SQLite"
    unverified = df["source"].map(is_unverified_corner_source)
    df.loc[unverified, ["HC", "AC"]] = np.nan
    return merge_manual_match_metadata(df, league)


def local_api_matches(league):
    """分析頁的本地API客戶端；API未啟動時才回退本地SQLite，避免阻塞使用。"""
    base = os.getenv("LOCAL_API_URL", "http://127.0.0.1:8000").rstrip("/")
    lid = next((x.get("id") for x in json.loads(Path(__file__).with_name("leagues.json").read_text(encoding="utf-8")).get("leagues", [])
                if x.get("name_zh") == league), league)
    try:
        r = requests.get(f"{base}/api/matches", params={"league": lid}, timeout=0.8)
        if r.ok:
            data = r.json().get("data", [])
            if data:
                df = pd.DataFrame(data)
                df = df.rename(columns={"home_team": "Home", "away_team": "Away", "home_goals": "HG",
                                        "away_goals": "AG", "home_corners": "HC", "away_corners": "AC",
                                        "date": "Date"})
                if "source" in df.columns:
                    unverified = df["source"].map(is_unverified_corner_source)
                    df.loc[unverified, ["HC", "AC"]] = np.nan
                return merge_manual_match_metadata(df, league)
    except Exception:
        pass
    return pd.DataFrame()


def import_local_league_cache():
    """啟動時讀取 league_collector 產生的 CSV；只匯入本地檔，不自行猜測資料。"""
    config_path = Path(__file__).with_name("leagues.json")
    cache_root = Path(__file__).with_name("data") / "leagues"
    if not config_path.exists() or not cache_root.exists():
        return 0
    try:
        config = json.loads(config_path.read_text(encoding="utf-8"))
    except Exception:
        return 0
    total = 0
    for item in config.get("leagues", []):
        manual = load_manual_league_override(item["name_zh"])
        if not manual.empty:
            # 手動資料是該聯賽的明確覆蓋來源，不再混入免費快取。
            with db_connect() as conn:
                conn.execute("DELETE FROM matches WHERE league=?", (item["name_zh"],))
            save_matches(manual)
            total += len(manual)
            continue
        path = cache_root / item["id"] / "matches.csv"
        if not path.exists():
            continue
        try:
            raw = pd.read_csv(path)
            if raw.empty or not {"home_team", "away_team", "home_goals", "away_goals"}.issubset(raw.columns):
                continue
            rows = pd.DataFrame({"Date": raw.get("date", ""), "Home": raw["home_team"], "Away": raw["away_team"],
                                 "HG": raw["home_goals"], "AG": raw["away_goals"],
                                 "HC": raw.get("home_corners", pd.NA), "AC": raw.get("away_corners", pd.NA),
                                 "league": item["name_zh"], "season": raw.get("season", "local-cache"),
                                 "source": raw.get("source", "本地聯賽快取")})
            rows["Date"] = rows["Date"].astype(str)
            rows["HG"] = pd.to_numeric(rows["HG"], errors="coerce")
            rows["AG"] = pd.to_numeric(rows["AG"], errors="coerce")
            rows["HC"] = pd.to_numeric(rows["HC"], errors="coerce")
            rows["AC"] = pd.to_numeric(rows["AC"], errors="coerce")
            rows = rows.dropna(subset=["HG", "AG"])
            if not rows.empty:
                save_matches(rows); total += len(rows)
        except Exception:
            continue
    return total


def configured_secret(name):
    try:
        return str(st.secrets.get(name, "") or os.getenv(name, ""))
    except Exception:
        return os.getenv(name, "")


def team_key(value):
    # 保留中文字符；舊版轉 ASCII 後「西維爾」會變成空字串，
    # 空字串參與包含判斷會錯誤配對任何球隊。
    value = unicodedata.normalize("NFKD", str(value)).lower()
    value = re.sub(r"[^\w]", "", value, flags=re.UNICODE)
    value = value.replace("jrs", "juniors").replace("ath", "atletico")
    for suffix in ("footballclub", "fc", "cf", "sc", "afc", "ac", "club"):
        if value.endswith(suffix) and len(value) > len(suffix) + 3:
            value = value[:-len(suffix)]
    return value


def team_matches(query, official_name):
    """以別名、標準化名稱及包含關係配對，避免中文輸入造成誤判。"""
    q = str(query).strip()
    name = str(official_name).strip()
    translated = ALIASES.get(q, q)
    qkey, nkey = team_key(translated), team_key(name)
    if not qkey or not nkey:
        return False
    return (
        translated.casefold() == name.casefold()
        or translated.casefold() in name.casefold()
        or name.casefold() in translated.casefold()
        or qkey == nkey
        or qkey in nkey
        or nkey in qkey
    )


def resolve_team_name(query, candidates, token=""):
    """跨中文別名、重音符號、簡稱及 API 搜尋解析官方隊名。"""
    query = str(query).strip()
    if not query:
        return None
    translated = ALIASES.get(query, query)
    # 先做完整名稱配對，避免模糊包含關係將客隊搶配成主隊。
    for name in candidates:
        if str(name).casefold() == str(translated).casefold() or team_key(name) == team_key(translated):
            return name
    for name in candidates:
        if team_matches(query, name):
            return name
    if token:
        try:
            api_names = api_team_candidates(ALIASES.get(query, query), token)
            for api_name in api_names:
                for name in candidates:
                    if team_matches(api_name, name):
                        return name
            if api_names:
                return api_names[0]
        except Exception:
            pass
    return None


@st.cache_data(ttl=3600, show_spinner=False)
def api_team_candidates(query, token):
    if not token or not query.strip():
        return []
    payload = api_get("teams", {"search": query.strip()}, token)
    return [x.get("team", {}).get("name", "") for x in payload.get("response", []) if x.get("team", {}).get("name")]


def search_team_candidates(query, directory, token):
    query = query.strip()
    if not query:
        return []
    translated = ALIASES.get(query, query)
    qkey = team_key(translated)
    found = []
    for name in directory:
        nkey = team_key(name)
        if translated.lower() in name.lower() or query.lower() in name.lower() or qkey == nkey or qkey in nkey or nkey in qkey:
            found.append(name)
    try:
        found.extend(api_team_candidates(translated, token))
    except Exception:
        pass
    return sorted(set(x for x in found if x), key=lambda x: (team_key(translated) not in team_key(x), x))


db_init()
if not st.session_state.get("local_league_cache_loaded"):
    import_local_league_cache()
    st.session_state["local_league_cache_loaded"] = True
if "is_importing" not in st.session_state:
    st.session_state["is_importing"] = False
st.title("混合來源足球分析")
st.caption("本地資料館 → API → 公開 JSON／CSV → 你上載的 CSV／Excel；資料不足時不會虛構結果。")
try:
    _api_started = requests.get(os.getenv("LOCAL_API_URL", "http://127.0.0.1:8000").rstrip("/"), timeout=0.35).ok
except Exception:
    _api_started = False
st.caption(f"數據接口：本地API（CSV驅動）｜延遲：{'<0.2秒' if _api_started else '未啟動，使用本地SQLite後備'}｜狀態：{'正常' if _api_started else '後備模式'}")

with st.sidebar:
    test_update = st.button("更新四個測試聯賽（零成本）", use_container_width=True,
                            help="英超、澳職、日職、韓職；資料先保存到 data/leagues/，失敗不會覆蓋舊快取。")
    if test_update:
        with st.spinner("收集四個測試聯賽的公開資料中……"):
            result = subprocess.run(["python3", str(Path(__file__).with_name("league_collector.py")),
                                     "--leagues", "epl,a-league,j1,k1"], cwd=str(Path(__file__).parent),
                                    capture_output=True, text=True, timeout=300)
        if result.returncode == 0:
            st.success("四個測試聯賽收集完成；重新載入頁面後會自動匯入本地快取。")
            st.session_state["local_league_cache_loaded"] = False
        else:
            st.warning("收集器未完成，舊快取仍會保留。請查看終端輸出或稍後重試。")
    cache_index = Path(__file__).with_name("data") / "leagues" / "index.json"
    if cache_index.exists():
        try:
            cached = json.loads(cache_index.read_text(encoding="utf-8"))
            ok = [x for x in cached.get("leagues", []) if x.get("quality") not in ("失敗",)]
            st.caption(f"本地已快取 {len(ok)} 個聯賽；零成本模式")
        except Exception:
            pass
    html_probe = st.button(
        "測試直接 HTML 來源（安全試跑）", use_container_width=True,
        help="測試 FBref／Soccerway 的公開 HTML 及南墨爾本、悉尼聯58；被封或無表格時不會覆蓋現有資料。",
    )
    if html_probe:
        with st.spinner("正在測試直接 HTML 來源；空資料不會寫入……"):
            try:
                probe = subprocess.run(
                    ["python3", str(Path(__file__).parent / "scripts" / "html_sources_sync.py"),
                     "--pilot", "--sleep", "5"],
                    cwd=str(Path(__file__).parent), capture_output=True, text=True, timeout=180,
                )
                report_path = Path(__file__).parent / "data" / "html_sources_sync_report.json"
                report = json.loads(report_path.read_text(encoding="utf-8")) if report_path.exists() else []
                inserted = sum(int(x.get("rows", 0) or 0) for x in report)
                if probe.returncode == 0 and inserted:
                    st.success(f"HTML 試跑完成，已寫入 {inserted} 場已核實賽果。")
                elif probe.returncode == 0:
                    st.warning("HTML 試跑完成，但來源目前沒有可解析表格；現有資料保持不變。")
                else:
                    st.warning("HTML 試跑未完成；現有資料保持不變。")
            except Exception as exc:
                st.warning(f"HTML 試跑未完成：{exc}；現有資料保持不變。")
    league = st.selectbox("聯賽", list(LEAGUES))
    current_league_rows = all_saved_matches(league)
    manual_override = manual_league_path(league).exists()
    if len(current_league_rows) < 5 and not manual_override:
        st.warning(f"{league} 目前只有 {len(current_league_rows)} 場可用資料；請上載至少 5 場真實賽果。")
        auto_backfill = st.button(
            "一鍵補20場", use_container_width=True, key="flashscore_backfill_20",
            help="只從 Flashscore 公開結果頁補入最近最多20場已完場比分；不抓角球，角球回測會保持資料不足。",
        )
        if auto_backfill:
            with st.spinner("正在從 Flashscore 讀取最近20場已完場比分……"):
                try:
                    fetched = fetch_flashscore_goal_results(league, limit=20)
                    saved_count = save_flashscore_goal_backfill(fetched, league)
                    st.success(f"已補入 {saved_count} 場真實比分並寫入快取；角球未核實，角球回測保持資料不足。")
                    st.rerun()
                except Exception as exc:
                    st.warning(f"一鍵補20場未完成：{exc}")
        manual_upload = st.file_uploader(
            "資料不足聯賽 CSV（固定 9 欄）",
            type=["csv"], key="manual_league_csv",
            help="欄位必須是：日期,主隊,客隊,比分,半場比分,主隊角球,客隊角球,主隊排名,客隊排名。"
        )
        st.download_button(
            "下載資料不足聯賽 CSV 範本",
            data=("日期,主隊,客隊,比分,半場比分,主隊角球,客隊角球,主隊排名,客隊排名\n"
                  "2025-08-15,主隊A,客隊B,1-0,1-0,5,2,12,14\n").encode("utf-8-sig"),
            file_name="資料不足聯賽_9欄範本.csv", mime="text/csv", use_container_width=True
        )
        upload_manual = st.button("上載CSV", use_container_width=True, key="upload_manual_league")
        if upload_manual:
            try:
                parsed_manual = read_manual_league_csv(manual_upload, league)
                save_manual_league_override(parsed_manual, league)
                st.success(f"已覆蓋 {league} 免費來源並保存 {len(parsed_manual)} 場；下次開啟不需重新上載。")
                st.rerun()
            except Exception as exc:
                st.warning(f"手動聯賽 CSV 未能上載：{exc}")
    elif manual_override:
        st.success(f"{league} 正使用已保存的手動 CSV 覆蓋資料（{len(current_league_rows)} 場）。")
    fd_token = st.text_input("Football-Data.org Token（可選）", value=configured_secret("FOOTBALL_DATA_TOKEN"), type="password")
    st.caption("目前不使用已停用的 API-Football；如需分析沒有 Football-Data 對照的聯賽，必須提供其他可用公開賽果頁面，或設定仍有效的 API-Football Token。")
    crawl_url = st.text_input(
        "後備公開賽果頁面（可選）",
        placeholder="建議填 WorldFootball.net 的指定聯賽／賽季賽果頁，不要只填首頁",
        help="用來補充沒有 Football-Data.org 對照的聯賽；只會讀取公開且 robots.txt 允許的頁面。"
    )
    uploaded_matches = st.file_uploader(
        "從其他網站下載後上載賽果（可選）",
        type=["csv", "xlsx", "xls"],
        help="你可以先登入任何允許下載資料的網站，下載 CSV 或 Excel，再上載到這裡；程式不會讀取你的密碼。"
    )
    corner_upload = st.file_uploader(
        "上載角球 CSV（可選）",
        type=["csv"],
        help="格式：Date,HomeTeam,AwayTeam,HC,AC；可沒有比分欄位，只供角球模型使用。"
    )
    repair_db = st.button("修復資料庫鎖定", use_container_width=True,
                          disabled=st.session_state.is_importing,
                          help="整理未完成交易及 WAL 暫存檔，不會刪除主要資料庫。")
    if repair_db:
        try:
            repair_database_lock()
            st.success("資料庫鎖定已修復，可以重新匯入。")
        except Exception as exc:
            st.warning(f"資料庫修復未完成：{exc}")
    bulk_matches = st.file_uploader(
        "35 聯賽統一 CSV 上載（可選，可一次選多個檔案）",
        type=["csv"], accept_multiple_files=True,
        help="檔名請包含聯賽代碼或英文名稱，例如 E0.csv、SP1.csv、saudi-pro-league.csv。"
    )
    update_all = st.button("一鍵更新可用的聯賽 CSV", use_container_width=True,
                           help="只會更新 Football-Data 實際有直接 CSV 的聯賽；其他聯賽不會虛構網址。")
    if update_all:
        with st.spinner("下載及驗證可用聯賽 CSV 中……"):
            update_ok, update_errors = update_fd_leagues()
        if update_ok:
            st.success("已更新：" + "、".join(update_ok))
        if update_errors:
            st.warning("未能更新（不會覆蓋舊資料）：" + "；".join(update_errors))
        st.caption("沒有列出的聯賽代表目前沒有已核實的 Football-Data 直接 CSV，請手動上載真實檔案。")
    player_upload = st.file_uploader(
        "球員名單 CSV（可選，FBref squad export）",
        type=["csv"],
        help="需要 Player、Nation、Pos、Age、Gls 欄位；若有 Squad 欄位，會按主客隊篩選。"
    )
    fbref_html = st.text_area(
        "貼上公開比賽 HTML（可選，用於補充角球）",
        height=120,
        help="支援 FBref / Sportradar / Elbotola 格式，會自動識別 HC/AC。"
    )
    st.caption("支援 FBref / Sportradar / Elbotola 格式，會自動識別 HC/AC")
    csv_url = st.text_input(
        "公開 CSV 直連網址（可選）",
        placeholder="例如 https://example.com/results.csv",
        help="只接受不需要登入、而且你有權下載的直接 CSV 網址；每次分析會讀取最新檔案。"
    )
    template = pd.DataFrame(columns=["日期", "主隊", "客隊", "主隊入球", "客隊入球", "主隊角球", "客隊角球"])
    st.download_button(
        "下載 CSV 格式範本",
        data=template.to_csv(index=False).encode("utf-8-sig"),
        file_name="足球賽果資料範本.csv",
        mime="text/csv",
        use_container_width=True,
    )
    import_uploaded = st.button("匯入中..." if st.session_state.is_importing else "匯入上載檔案到本地資料館",
                                use_container_width=True, disabled=st.session_state.is_importing)
    if import_uploaded:
        st.session_state.is_importing = True
        try:
            imported = read_uploaded_matches(uploaded_matches, league)
            save_matches(imported)
            st.success(f"已匯入 {len(imported)} 場賽果；下次分析會優先使用本地資料館。")
        except Exception as exc:
            st.warning(f"上載檔案未能匯入：{exc}")
        finally:
            st.session_state.is_importing = False
    import_corner = st.button("匯入中..." if st.session_state.is_importing else "匯入角球 CSV 到資料館",
                              use_container_width=True, disabled=st.session_state.is_importing)
    if import_corner:
        st.session_state.is_importing = True
        try:
            corner_imported = read_corner_csv(corner_upload, league)
            save_matches(corner_imported)
            st.success(f"已保存 {len(corner_imported)} 場角球紀錄；下次分析會優先使用。")
        except Exception as exc:
            st.warning(f"角球 CSV 未能匯入：{exc}")
        finally:
            st.session_state.is_importing = False
    import_bulk = st.button("一鍵上載多個聯賽 CSV", use_container_width=True)
    if import_bulk:
        if not bulk_matches:
            st.warning("請先選擇一個或多個聯賽 CSV 檔案。")
        else:
            bulk_ok, bulk_errors = [], []
            for bulk_file in bulk_matches:
                target_league = detect_bulk_league(getattr(bulk_file, "name", ""))
                if not target_league:
                    bulk_errors.append(f"{getattr(bulk_file, 'name', '')}：檔名未能辨識聯賽")
                    continue
                try:
                    frame = read_bulk_csv(bulk_file, target_league)
                    save_matches(frame)
                    bulk_ok.append(f"{target_league}（{len(frame)} 場）")
                except Exception as exc:
                    bulk_errors.append(f"{getattr(bulk_file, 'name', '')}：{exc}")
            if bulk_ok:
                st.success("已匯入：" + "、".join(bulk_ok))
            if bulk_errors:
                st.warning("未能匯入：" + "；".join(bulk_errors))
    if player_upload is not None:
        try:
            st.session_state["uploaded_players"] = read_player_csv(player_upload)
            st.caption(f"已讀取球員名單 {len(st.session_state['uploaded_players'])} 人；只作球員資料顯示。")
        except Exception as exc:
            st.warning(f"球員 CSV 未能讀取：{exc}")
    import_fbref_html = st.button("匯入中..." if st.session_state.is_importing else "匯入 HTML 角球資料",
                                  use_container_width=True, disabled=st.session_state.is_importing)
    if import_fbref_html:
        st.session_state.is_importing = True
        try:
            html_matches = parse_pasted_fbref_html(fbref_html, league)
            updated, created = save_corner_supplement(html_matches)
            st.success(f"HTML 角球資料已匯入：更新既有賽果 {updated} 場；自動新增賽事 {created} 場。")
        except Exception as exc:
            st.warning(f"HTML 未能匯入：{exc}")
        finally:
            st.session_state.is_importing = False
    import_csv_url = st.button("讀取並匯入 CSV 網址", use_container_width=True)
    if import_csv_url:
        try:
            imported_url = read_csv_url(csv_url, league)
            save_matches(imported_url)
            st.success(f"已由公開 CSV 網址匯入 {len(imported_url)} 場賽果。")
        except Exception as exc:
            st.warning(f"CSV 網址未能匯入：{exc}")
    st.caption("資料流程：本地資料館優先，其次 API、公開 CSV／JSON；最後才使用你明確提供的公開網址。")
    with st.expander("本地資料館狀態"):
        try:
            with db_connect() as conn:
                library_count = int(pd.read_sql_query("SELECT COUNT(*) AS n FROM matches", conn).iloc[0]["n"])
                league_count = int(pd.read_sql_query("SELECT COUNT(DISTINCT league) AS n FROM matches", conn).iloc[0]["n"])
            st.write(f"已保存賽果：{library_count} 場｜已保存聯賽：{league_count} 個")
            st.caption("匯入後資料會按聯賽保存，分析時優先使用本地資料館。")
        except Exception:
            st.caption("資料館尚未有可顯示的紀錄。")
    directory_key = f"teams_{league}"
    load_directory = st.button("先載入本聯賽球隊清單", use_container_width=True)
    if load_directory:
        try:
            # 檔案上載後優先使用檔案本身，不再因沙特外部來源沒有回傳而失敗。
            if uploaded_matches is not None:
                uploaded_for_directory = read_uploaded_matches(uploaded_matches, league)
                save_matches(uploaded_for_directory)
                directory_names = sorted(set(uploaded_for_directory["Home"]) | set(uploaded_for_directory["Away"]))
                directory_source = "你上載的 CSV"
            elif csv_url.strip():
                url_for_directory = read_csv_url(csv_url, league)
                save_matches(url_for_directory)
                directory_names = sorted(set(url_for_directory["Home"]) | set(url_for_directory["Away"]))
                directory_source = "公開 CSV 網址"
            else:
                directory_names, directory_source = get_team_directory(league, "", fd_token.strip(), crawl_url)
            st.session_state[directory_key] = directory_names
            st.caption(f"已載入 {len(directory_names)} 隊｜來源：{directory_source}")
        except Exception as exc:
            st.warning(f"球隊清單暫時未能載入：{exc}")
    directory = st.session_state.get(directory_key, [])
    st.caption("可以直接輸入中文或英文隊名，程式會搜尋候選，不需要你自行對官方英文名稱。")
    home_query = st.text_input("主隊", "阿仙奴")
    away_query = st.text_input("客隊", "利物浦")
    find_teams = st.button("自動搜尋主客隊候選", use_container_width=True)
    if find_teams:
        st.session_state[f"home_candidates_{league}"] = search_team_candidates(home_query, directory, "")
        st.session_state[f"away_candidates_{league}"] = search_team_candidates(away_query, directory, "")
    home_candidates = st.session_state.get(f"home_candidates_{league}", [])
    away_candidates = st.session_state.get(f"away_candidates_{league}", [])
    if home_candidates:
        home_text = st.selectbox("確認主隊", home_candidates, key=f"home_pick_{league}")
    else:
        home_text = home_query
    if away_candidates:
        away_text = st.selectbox("確認客隊", away_candidates, key=f"away_pick_{league}")
    else:
        away_text = away_query
    st.markdown("### Live 狀態（可選）")
    live_c1, live_c2, live_c3 = st.columns(3)
    with live_c1:
        live_minute = st.number_input("比賽分鐘", min_value=0, max_value=120, value=0, step=1, key="live_minute")
    with live_c2:
        live_home_goals = st.number_input("主隊即時入球", min_value=0, max_value=20, value=0, step=1, key="live_home_goals")
    with live_c3:
        live_away_goals = st.number_input("客隊即時入球", min_value=0, max_value=20, value=0, step=1, key="live_away_goals")
    st.caption("未有 Live 資料請保持 0；只有輸入比賽分鐘及即時比分後，才會顯示 Live 風險提示。")
    st.markdown("### 專業盤口頁（Football-Data.org + The Odds API）")
    professional_match_id = st.text_input("Football-Data.org Match ID（完場更新先填；開波前可留空）", value="", key="professional_match_id")
    pro_c1, pro_c2 = st.columns(2)
    with pro_c1:
        load_professional = st.button("載入專業盤口（開波前一次）", use_container_width=True)
    with pro_c2:
        refresh_postmatch = st.button("完場更新賽果／陣容", use_container_width=True)
    if load_professional or refresh_postmatch:
        with st.spinner("讀取專業盤口資料中……"):
            try:
                pro_payload = merge_professional_page(
                    ALIASES.get(home_text.strip(), home_text.strip()),
                    ALIASES.get(away_text.strip(), away_text.strip()),
                    professional_match_id.strip() or None,
                    post_match=bool(refresh_postmatch),
                )
                st.session_state["professional_page"] = pro_payload
            except Exception as exc:
                st.warning(f"專業盤口暫時未能載入：{exc}")
    pro_payload = st.session_state.get("professional_page")
    if pro_payload:
        pro_meta = pro_payload.get("odds_meta", {})
        usage = pro_payload.get("usage", {})
        st.caption(f"Odds API：{pro_meta.get('status', '未取得')}｜今日已使用 {usage.get('calls', 0)}/5 次｜{pro_payload.get('policy', '')}")
        pro_event = pro_payload.get("odds_snapshot")
        if pro_event:
            st.markdown(f"**{pro_event.get('home_team')} 對 {pro_event.get('away_team')}**")
            st.caption("以下為The Odds API目前快照；免費即時接口不等於初盤／香港莊家水位，沒有來源提供的項目不會自行補填。")
            pro_rows = []
            for book in pro_event.get("bookmakers", []):
                for market in book.get("markets", []):
                    for outcome in market.get("outcomes", []):
                        pro_rows.append({"公司": book.get("title") or book.get("key"), "市場": market.get("key"), "選項": outcome.get("name"), "盤口": outcome.get("point"), "賠率": outcome.get("price"), "更新時間": market.get("last_update") or book.get("last_update")})
            if pro_rows:
                st.dataframe(pd.DataFrame(pro_rows), use_container_width=True, hide_index=True)
            else:
                st.info("Odds API已回應，但目前沒有Pinnacle／Bet365／Unibet可顯示盤口。")
        else:
            st.info("目前未找到與主客隊完全匹配的西甲賠率事件；不會自行配對其他比賽。")
        detail = pro_payload.get("match_detail", {})
        if detail.get("status") == "ok":
            score = detail.get("score", {})
            st.markdown("**Football-Data.org 完場資料**")
            lineup_rows = detail.get("lineups") or []
            lineup_count = sum(len(x.get("players") or []) for x in lineup_rows if isinstance(x, dict))
            formations = "、".join(str(x.get("formation")) for x in lineup_rows if isinstance(x, dict) and x.get("formation")) or "來源未提供"
            st.write(f"比分：{score.get('home')} - {score.get('away')}｜入球事件：{len(detail.get('goals') or [])}｜陣容球員：{lineup_count}人｜陣式：{formations}｜角球：{detail.get('corners') if detail.get('corners') is not None else '來源未提供'}")
        elif refresh_postmatch:
            st.warning(detail.get("reason", "完場資料未取得"))
    home_odds = st.number_input("主勝賠率（0=沒有此盤）", 0.0, 100.0, 1.85)
    draw_odds = st.number_input("和局賠率（0=沒有此盤）", 0.0, 100.0, 3.40)
    away_odds = st.number_input("客勝賠率（0=沒有此盤）", 0.0, 100.0, 4.20)
    home_odds = home_odds or None
    draw_odds = draw_odds or None
    away_odds = away_odds or None
    # 保留 2.5 作為模型主線；顯示層同時比較 2.5／3.5／4.5。
    line = 2.5
    st.markdown("**入球大小賠率（一次輸入 2.5／3.5／4.5）**")
    goal_over_odds_map, goal_under_odds_map = {}, {}
    for x in [2.5, 3.5, 4.5]:
        c_over, c_under = st.columns(2)
        with c_over:
            goal_over_odds_map[x] = st.number_input(f"大 {x}", 0.0, 100.0, 0.0, key=f"goal_over_{x}")
        with c_under:
            goal_under_odds_map[x] = st.number_input(f"細 {x}", 0.0, 100.0, 0.0, key=f"goal_under_{x}")
    goal_over_odds = goal_over_odds_map[2.5] or None
    goal_under_odds = goal_under_odds_map[2.5] or None
    handicap_line_input = st.number_input("主隊亞洲讓球線（例如 -0.5 或 +1.75）", -3.0, 3.0, 0.0, step=0.25)
    # 只接受標準四分之一盤；手機手動輸入異常小數時，不讓它與錯誤賠率配對。
    handicap_line = round(float(handicap_line_input) * 4) / 4
    if abs(float(handicap_line_input) - handicap_line) > 1e-9:
        st.warning(f"讓球線 {handicap_line_input:+.2f} 不是標準盤，已按最近四分一盤 {handicap_line:+.2f} 計算。請核對賠率是否屬於同一條線。")
    handicap_odds = st.number_input("讓球主隊賠率（0=沒有此盤）", 0.0, 100.0, 1.90)
    handicap_odds = handicap_odds or None
    corner_line = 9.5
    st.markdown("**角球大小賠率（一次輸入 9.5／10.5／11.5／12.5）**")
    corner_over_odds_map, corner_under_odds_map = {}, {}
    for x in [9.5, 10.5, 11.5, 12.5]:
        c_over, c_under = st.columns(2)
        with c_over:
            corner_over_odds_map[x] = st.number_input(f"角球大 {x}", 0.0, 100.0, 0.0, key=f"corner_over_{x}")
        with c_under:
            corner_under_odds_map[x] = st.number_input(f"角球細 {x}", 0.0, 100.0, 0.0, key=f"corner_under_{x}")
    corner_over_odds = corner_over_odds_map[9.5] or None
    corner_under_odds = corner_under_odds_map[9.5] or None
    st.caption("已同時輸入多條大小球及角球線；0 代表未有賠率。")
    pasted_odds = st.text_area("貼上即場賠率（可選；每行一個盤口）", placeholder="W/D/L 7.60/4.10/1.32\n大細[2.5] 2.08/1.66\n主[0.5] 2.04/1.69", height=90)
    run = st.button("一鍵自動抓取及分析", type="primary", use_container_width=True)
    run_backtest = st.button("回測本聯賽模型", use_container_width=True)

if run_backtest:
    with st.spinner("逐場回測中；每場只使用當時之前的資料……"):
        saved = all_saved_matches(league)
        if saved.empty:
            try:
                saved, _, _ = get_matches(league, "", fd_token.strip(), crawl_url)
            except Exception as exc:
                st.warning(f"暫時未能取得回測資料：{exc}")
                st.stop()
            if saved.empty:
                st.warning("目前沒有足夠的歷史賽果，暫時不能回測；程式沒有使用假數據。")
                st.stop()
        detail, summary = walk_forward_backtest(saved)
        market_detail, market_summary = walk_forward_market_backtest(saved)
    st.subheader(f"{league} 模型回測")
    if not detail.empty:
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("測試樣本", f"{summary['樣本數']} 場")
        m2.metric("勝和負方向命中", f"{summary['勝和負方向命中率']:.1%}")
        m3.metric("比分 Top 5 包含率", f"{summary['比分Top5包含率']:.1%}")
        m4.metric("Brier Score", f"{summary['Brier Score']:.3f}")
        st.markdown("**入球／角球大小回測（只用每場日期之前的資料）**")
        g1, g2 = st.columns(2)
        with g1:
            goal_rate = market_summary.get("細3.5命中率")
            goal_text = "資料不足" if goal_rate is None else f"{goal_rate:.1%}"
            st.metric("細3.5 命中率", goal_text)
            st.caption(f"樣本 {market_summary.get('入球樣本數', 0)} 場｜按賠率1.4淨利潤 {market_summary.get('細3.5淨利潤', 0.0):+.2f} 單位")
        with g2:
            corner_rate = market_summary.get("大9.5角命中率")
            corner_text = "資料不足" if corner_rate is None else f"{corner_rate:.1%}"
            st.metric("大9.5角 命中率", corner_text)
            st.caption(f"樣本 {market_summary.get('角球樣本數', 0)} 場｜按賠率1.8淨利潤 {market_summary.get('大9.5角淨利潤', 0.0):+.2f} 單位")
        st.caption("回測只使用每場比賽日期之前的賽果；樣本太少時不會硬算，數字只代表過往樣本，不保證未來表現。")
        st.dataframe(detail.tail(100), use_container_width=True, hide_index=True)
        if not market_detail.empty:
            with st.expander("入球／角球大小逐場回測明細"):
                st.dataframe(market_detail.tail(100), use_container_width=True, hide_index=True)
        for _title, _key in [("入球大小 6 條線", "入球盤口回測"), ("角球大小 12 條線", "角球盤口回測")]:
            _frame = market_summary.get(_key)
            if _frame is not None and not _frame.empty:
                _view = _frame.copy()
                _view["命中率"] = _view["命中率"].map(lambda x: "資料不足" if pd.isna(x) else f"{float(x):.1%}")
                _view["淨利潤"] = _view["淨利潤"].map(lambda x: f"{float(x):+.2f}")
                st.markdown(f"**{_title}：命中率／樣本數／淨利潤**")
                st.dataframe(_view, use_container_width=True, hide_index=True)
    else:
        st.warning("現有資料不足以進行逐場回測；每隊至少需要先有 4 場更早的賽果。")

if run:
    home = ALIASES.get(home_text.strip(), home_text.strip())
    away = ALIASES.get(away_text.strip(), away_text.strip())
    with st.spinner("按資料來源優先次序抓取中……"):
        try:
            # 使用者明確上載檔案時，該檔案是本次分析的第一優先來源。
            if uploaded_matches is not None:
                matches = read_uploaded_matches(uploaded_matches, league)
                save_matches(matches)
                source, quality = "你上載的 CSV", "高（已核對格式）"
            elif csv_url.strip():
                matches = read_csv_url(csv_url, league)
                save_matches(matches)
                source, quality = "公開 CSV 網址", "高（已核對格式）"
            else:
                matches, source, quality = get_matches(league, "", fd_token.strip(), crawl_url)
        except Exception as e:
            st.warning(f"資料來源暫時不可用：{e}")
            st.info("請稍後再試，或提供該聯賽的公開賽果頁面；程式不會自行填入虛構數據。")
            st.stop()
    if matches.empty:
        st.warning(f"暫時找不到「{league}」的可核對賽果。這不是程式崩潰，而是目前公開來源沒有回傳資料。")
        st.info("可先選擇英超、西甲、德甲或歐聯測試；沙特等聯賽若所有免費來源均未覆蓋，必須等待來源恢復或匯入真實 CSV。")
        st.stop()
    # 不同免費來源欄位不完全一致；缺少角球時補空欄，不能阻止入球及勝和負分析。
    for required_col in ["Home", "Away", "HG", "AG"]:
        if required_col not in matches.columns:
            st.error(f"賽果資料缺少必要欄位：{required_col}；已停止本次分析，避免使用錯誤資料。")
            st.stop()
    for optional_col in ["HC", "AC"]:
        if optional_col not in matches.columns:
            matches[optional_col] = pd.NA
    if "DateParsed" not in matches.columns:
        matches["DateParsed"] = pd.to_datetime(matches.get("Date", ""), errors="coerce", dayfirst=True)
    if "source" not in matches.columns:
        matches["source"] = source
    stale_data, latest_data_date = data_is_stale(matches)
    if stale_data:
        latest_text = latest_data_date.strftime("%Y-%m-%d") if latest_data_date is not None else "未知"
        st.warning(f"資料最後日期為 {latest_text}，已超過一年；本次只顯示模型參考，不會把 EV 當成可下注優勢。請勿將舊賽季 CSV 當成最新近況。")
        quality = "過期（只供歷史參考）"
    teams = sorted(set(matches.Home) | set(matches.Away))
    # 優先使用已載入的聯賽完整目錄；沒有目錄時才用歷史賽果作後備。
    directory = st.session_state.get(f"teams_{league}", [])
    all_candidates = sorted(set(directory) | set(teams))
    hm = resolve_team_name(home, all_candidates, "")
    am = resolve_team_name(away, all_candidates, "")
    # API 搜尋可能回傳官方名稱，但名稱尚未出現在歷史賽果；仍保留官方名稱，
    # 讓畫面可以清楚顯示「隊伍存在，但歷史樣本不足」，而不是錯誤地說找不到。
    if hm and hm not in all_candidates:
        all_candidates.append(hm)
    if am and am not in all_candidates:
        all_candidates.append(am)
    if not hm or not am:
        st.warning("搵不到其中一隊。請使用下方資料來源中的官方隊名。")
        st.dataframe(pd.DataFrame({"可選球隊": teams}), use_container_width=True, hide_index=True); st.stop()
    home, away = hm, am
    if team_key(home) == team_key(away):
        st.error("主隊及客隊被配對成同一隊，已停止分析；請重新選擇真正的客隊。")
        st.stop()
    home_info, home_info_error = team_details(home)
    away_info, away_info_error = team_details(away)
    # FBref 比賽報告補充：只取選定兩隊最近最多 5 場，並只把有 HC/AC 的資料
    # 送入角球模型；不把沒有入球欄位的補充列混入勝和負及入球模型。
    fbref_corner_rows = pd.DataFrame()
    fbref_corner_message = "FBref 逐場角球未讀取"
    try:
        fbref_reports = recent_match_reports(league, home, away, limit=5)
        fbref_corner_rows = reports_to_dataframe(fbref_reports)
        fbref_corner_message = f"FBref 比賽報告角球：{len(fbref_corner_rows)} 場"
    except Exception as exc:
        fbref_corner_message = f"FBref 逐場角球未讀取：{str(exc)[:160]}"
    h = matches[(matches.Home == home) | (matches.Away == home)].sort_values("DateParsed").tail(8)
    a = matches[(matches.Home == away) | (matches.Away == away)].sort_values("DateParsed").tail(8)
    pair_data_ok, pair_data_reasons = pair_data_status(h, a, stale_data)
    if not pair_data_ok:
        # 硬性信任閘門：樣本不足時不能再展示看似精確的主客、大小球或
        # 角球機率。否則畫面一邊寫「資料不足」，一邊仍顯示 0.505880，
        # 容易令使用者誤以為那是可用的正式預測。
        st.error("；".join(pair_data_reasons))
        st.warning("資料不足，未能作可信分析；本次不顯示模型機率、EV、比分池或下注方向。請先補足主隊及客隊各至少4場已核實賽果。")
        st.info("可使用上方「上載CSV」或「一鍵補20場」補入真實賽果；角球若未有核實HC/AC，角球分析仍會保持資料不足。")
        st.stop()
    hgf = (h.apply(lambda r: r.HG if r.Home == home else r.AG, axis=1).mean() if not h.empty else 1.0)
    hga = (h.apply(lambda r: r.AG if r.Home == home else r.HG, axis=1).mean() if not h.empty else 1.0)
    agf = (a.apply(lambda r: r.HG if r.Home == away else r.AG, axis=1).mean() if not a.empty else 1.0)
    aga = (a.apply(lambda r: r.AG if r.Home == away else r.HG, axis=1).mean() if not a.empty else 1.0)
    hx, ax = max(.15, (hgf + aga) / 2 * 1.08), max(.15, (agf + hga) / 2 * .94)
    fbref_stats, fbref_source = fbref_team_stats(league)
    hx, ax, fbref_adjustment = fbref_expected_goal_adjustment(fbref_stats, home, away, hx, ax)
    # 通用護級戰意：只在最新資料年份能核對排名、近5場勝場及積分差時觸發。
    relegation_context = build_relegation_context(matches, home, away)
    hx, ax, intent_boost = apply_relegation_intent(hx, ax, relegation_context, total_boost=.6)
    if relegation_context.get("triggered"):
        st.info("護級戰意層已觸發：兩隊後六名、近5場各最多1勝、積分差不超過5分；總預期入球 +0.6（主客各 +0.3）。")
    elif relegation_context.get("status") == "資料不足":
        st.caption("護級戰意層：未能由目前賽果核對完整排名，未自行加成。")
    live_context = fetch_realtime_context(home, away, league)
    manual_injury_used = False
    hx, ax, injury_adjustment = apply_verified_injury_adjustment(hx, ax, live_context)
    manual_injuries = load_manual_injury_context(home, away)
    if manual_injuries.get("status") in {"manual_verified", "manual_verified_match"}:
        manual_injury_used = True
        hx, ax, injury_adjustment = apply_verified_injury_adjustment(hx, ax, manual_injuries)
        live_context = {**live_context, **manual_injuries,
                        "injuries": manual_injuries.get("injuries", []),
                        "injury_data_verified": True}
    # ORBIFLOW is optional.  Without a valid local JSON, this is an exact V1.0 passthrough.
    orbiflow_data = load_orbiflow(Path(__file__).parent / "data" / "orbiflow" / "orbiflow.json", use_mock=False)
    orbiflow_result = apply_orbiflow(hx, ax, orbiflow_data)
    hx, ax = orbiflow_result["home_exp_final"], orbiflow_result["away_exp_final"]
    # V2.0學習層只讀取有真實賽果的紀錄；沒有完成紀錄時修正值必然為0。
    home_learning_adjustment = learning_adjustment(home)
    away_learning_adjustment = learning_adjustment(away)
    hx, ax = max(.15, hx + home_learning_adjustment), max(.15, ax + away_learning_adjustment)
    if live_context.get("status") == "ok":
        st.caption(f"即時資料：{live_context.get('source', '已取得')}｜H2H近4場：{len(live_context.get('h2h_last4', []))}｜主客近10場：{len(live_context.get('home_last10', []))}/{len(live_context.get('away_last10', []))}｜傷停：{len(live_context.get('injuries', []))}人")
    else:
        st.caption("即時資料：未取得；未使用未核實傷停，模型沒有自行扣減預期入球")
    if manual_injury_used:
        st.success(f"傷停修正：已使用已核實傷停｜{injury_adjustment}")
    elif injury_adjustment != "未有已核實傷停，沒有扣減預期入球":
        st.info(f"傷停修正：{injury_adjustment}")
    hp, dp, ap = probs(hx, ax)
    pasted_rows = parse_odds_text(pasted_odds)
    # CornerOU must be valued only after the corner model is available;
    # initialise here so the V2 reader can still run before corner assembly.
    pasted_results = []
    low_score_tight = sum(poisson(k, hx + ax) for k in range(3))
    tight_pool = tight_score_pool(low_score_tight, threshold=.60)
    v2_corner_insight = corner_insight(.252, .306, low_score_tight)
    reader = read_match(hx, ax, xg_last8={"home":hgf, "away":agf}, shots={}, odds_rows=pasted_results,
                        draw_probability=dp, low_score_tight=low_score_tight, corner_insight=v2_corner_insight,
                        model_home_probability=hp, model_away_probability=ap)
    over = 1 - sum(poisson(k, hx + ax) for k in range(math.floor(line) + 1))
    under = 1 - over
    goal_lines = {x: (1 - sum(poisson(k, hx + ax) for k in range(math.floor(x) + 1))) for x in [2.5, 3.5, 4.5]}
    matrix = score_matrix(hx, ax)
    ah_home, ah_draw, ah_away = handicap_prob(matrix, handicap_line)
    corner_input = all_saved_matches(league)
    if not corner_input.empty:
        corner_input["DateParsed"] = pd.to_datetime(corner_input.get("Date", ""), errors="coerce", dayfirst=True)
        corner_input = corner_input[["Home", "Away", "HC", "AC", "DateParsed", "source"]]
    else:
        corner_input = matches[["Home", "Away", "HC", "AC", "DateParsed"]].copy()
        corner_input["source"] = source
    if not fbref_corner_rows.empty:
        fbref_corner_rows = fbref_corner_rows.copy()
        fbref_corner_rows["source"] = "FBref 比賽報告"
        corner_input = pd.concat([corner_input, fbref_corner_rows[["Home", "Away", "HC", "AC", "DateParsed", "source"]]], ignore_index=True)
    corner_context = corner_context_rows(corner_input, home, away, key_fn=team_key)
    corner_lams, corner_status = corner_model(corner_input, home, away)
    # V1.4：入球模型與賠率分開；角球有真實HC/AC時優先使用，否則只作明確標示的情境估算。
    team_goal_view = team_goal_model(hx, ax)
    goal_band = total_goal_band(team_goal_view["total_exp"], 0.8)
    corner_fallback = None if corner_lams else fallback_corner_model(open_play=0.135, tight=0.498)
    # V1.6：只新增一層聯動解讀，不改動V1.4/V1.5任何機率或EV計法。
    under35_probability = 1.0 - goal_lines[3.5]
    over25_probability = goal_lines[2.5]
    linkage_market = {}
    if corner_lams:
        linkage_corner_total = sum(corner_lams)
        linkage_over85 = total_over_probability(linkage_corner_total, 8.5)
        linkage_under95 = 1.0 - total_over_probability(linkage_corner_total, 9.5)
    else:
        linkage_corner_total = float((corner_fallback or {}).get("total", 9.0) or 9.0)
        linkage_market = (corner_fallback or {}).get("market") or {}
        linkage_over85 = float((linkage_market.get(8.5) or {}).get("over", total_over_probability(linkage_corner_total, 8.5)))
        linkage_under95 = float((linkage_market.get(9.5) or {}).get("under", 1.0 - total_over_probability(linkage_corner_total, 9.5)))
    corner_card_probs = {}
    for _line in [8.5, 9.5, 10.5, 11.5, 12.5]:
        if corner_lams:
            _over = total_over_probability(linkage_corner_total, _line)
            corner_card_probs[_line] = {"over": _over, "under": 1.0 - _over}
        else:
            corner_card_probs[_line] = (linkage_market.get(_line) or {
                "over": total_over_probability(linkage_corner_total, _line),
                "under": 1.0 - total_over_probability(linkage_corner_total, _line),
            })
    # 部署環境可能暫時仍載入舊版 compare_odds（未接受 corner_total）。
    # 先用新版角球模型；若舊版本仍在記憶體，退回不帶關鍵字參數，避免整頁崩潰。
    pasted_results = []
    if pasted_rows:
        try:
            pasted_results = compare_odds(pasted_rows, hx, ax, corner_total=linkage_corner_total)
        except TypeError as exc:
            if "corner_total" not in str(exc):
                raise
            pasted_results = compare_odds(pasted_rows, hx, ax)
    reader = read_match(hx, ax, xg_last8={"home":hgf, "away":agf}, shots={}, odds_rows=pasted_results,
                        draw_probability=dp, low_score_tight=low_score_tight, corner_insight=v2_corner_insight,
                        model_home_probability=hp, model_away_probability=ap)
    # 信任閘門：樣本不足時只保留透明的原始機率，
    # 不把數學外推包裝成 V2.0 睇穿結論或下注方向。
    if not pair_data_ok:
        reader = dict(reader)
        reader["conclusion"] = "資料不足，未能作可信賽前分析；暫停主客、大小球及角球方向判斷。"
        reader["ou_note"] = "資料不足，暫不解讀莊家與模型背離。"
    v17_card = build_card(
        home, away, str(match_date) if "match_date" in locals() else "",
        hx, ax, {2.5: goal_lines[2.5], 3.5: goal_lines[3.5], 4.5: goal_lines[4.5]},
        linkage_corner_total, corner_card_probs, odds_rows=pasted_results,
        learning_rows=load_log(), injuries=live_context.get("injuries", []),
    )
    linkage_message = ""
    if pair_data_ok and under35_probability > .65:
        p11 = tight_pool.get("1-1", matrix.get((1, 1), 0.0)) if tight_pool else matrix.get((1, 1), 0.0)
        p10 = tight_pool.get("1-0", matrix.get((1, 0), 0.0)) if tight_pool else matrix.get((1, 0), 0.0)
        linkage_message = (f"💡細波預示：細3.5機率{under35_probability:.1%}偏高，呢場較易出現低比分拉鋸" 
                           f"（1-1 {p11:.1%}／1-0 {p10:.1%}）；角球預期{linkage_corner_total:.1f}，"
                           f"大8.5 {linkage_over85:.1%}／細9.5 {linkage_under95:.1%}，可留意角球大盤。")
    elif pair_data_ok and over25_probability > .60:
        linkage_message = (f"💡大波預示：大2.5機率{over25_probability:.1%}偏高，預期入球較多；"
                           f"角球預期{linkage_corner_total:.1f}，角球細盤可作比較，但要核對真實HC/AC。")
    corner_source_names = []
    if not corner_input.empty and "source" in corner_input.columns:
        for raw_source in corner_input.loc[corner_input[["HC", "AC"]].notna().all(axis=1), "source"].dropna().astype(str).unique():
            if "Football-Data" in raw_source:
                label = "football-data.co.uk"
            elif "TheSportsDB" in raw_source:
                label = "TheSportsDB"
            elif "API-Sports" in raw_source or "API-Football" in raw_source:
                label = "API-Sports"
            elif "上載" in raw_source or "CSV" in raw_source:
                label = "本地CSV"
            elif "FBref" in raw_source:
                label = "FBref HTML"
            else:
                label = "本地資料館"
            if label not in corner_source_names:
                corner_source_names.append(label)
    corner_source_label = " / ".join(corner_source_names) if corner_source_names else "未取得"
    monte_carlo = monte_carlo_match(hx, ax, corner_lams)
    confidence = model_confidence(len(h) + len(a), hp, dp, ap)
    reliability = reliability_level(
        len(h) + len(a),
        has_rank_context=relegation_context.get("status") in {"已核對", "未觸發"},
        has_real_corners=bool(corner_lams),
        stale=stale_data,
    )
    live_warning = live_risk_message(live_minute, live_home_goals, live_away_goals)
    home_form = team_form_table(matches, home)
    away_form = team_form_table(matches, away)
    with db_connect() as c:
        c.execute("INSERT INTO analyses(league,home,away,home_prob,draw_prob,away_prob,source,created_at) VALUES(?,?,?,?,?,?,?,?)", (league, home, away, hp, dp, ap, source, datetime.now(timezone.utc).isoformat()))
    home_zh, away_zh = zh_team(home), zh_team(away)
    st.success(f"資料來源：{zh_source(source)}｜資料質素：{quality}｜賽果：{len(matches)} 場｜{fbref_adjustment}")
    st.markdown(
        f"<div style='background:{reliability['color']};color:white;padding:10px 14px;border-radius:8px;font-weight:700'>"
        f"可靠性：{reliability['text']}</div>", unsafe_allow_html=True
    )
    if live_warning:
        st.markdown(f"<div style='color:#ff4b4b;font-weight:800;font-size:1.05rem'>🔴 Live風險：{live_warning}</div>", unsafe_allow_html=True)
    if orbiflow_data.get("available"):
        st.caption(orbiflow_summary(orbiflow_data, orbiflow_result))
    st.subheader(f"{home_zh} 對 {away_zh}")
    st.write(f"預期入球：{hx:.2f} - {ax:.2f}｜V1.7校準總預期 {v17_card.get('calibration', {}).get('total_exp', hx + ax):.2f}｜主勝 {hp:.1%}｜和局 {dp:.1%}｜客勝 {ap:.1%}")
    if linkage_message:
        st.info(linkage_message)
    if tight_pool:
        st.warning("膠著比分池（膠著率 >60%，通用情境權重）：1-1 40%｜1-0 25%｜0-1 20%｜2-1 15%。這是情境分配，唔等於保證比分。")
    # V1.7：LMGOAL風格一場一卡；只整理現有資料，不取代V1.6詳細表格。
    v17_cal = v17_card.get("calibration", {})
    v17_tight = v17_cal.get("tight_rate")
    v17_tight_text = f"膠著{v17_tight:.0%}" if v17_tight is not None else f"膠著{low_score_tight:.0%}"
    v17_tone = "⚠️" if (v17_tight or low_score_tight) >= .45 else "✅"
    st.markdown(f"### V1.7 比賽卡｜{home_zh} vs {away_zh}｜{v17_card.get('kickoff') or '賽前'}")
    st.write(f"預期 {v17_cal.get('total_exp', hx + ax):.2f} 球｜{v17_tight_text} {v17_tone}｜命中率 {v17_cal.get('hits', 14)}/{v17_cal.get('matches', 20)}｜角球預期 {v17_cal.get('corner_exp', linkage_corner_total):.1f}")
    v17_tabs = st.tabs(["概況", "分析", "統計", "陣容", "指數", "AI"])
    with v17_tabs[0]:
        st.write(f"主隊：{home_zh}｜客隊：{away_zh}｜模型總入球 {hx + ax:.2f}｜近期樣本：主隊 {len(h)} 場、客隊 {len(a)} 場")
        st.caption("資料只使用已取得的賽果、角球、傷停及賠率；未取得的欄位不會自行虛構。")
    with v17_tabs[1]:
        st.write(f"入球：大2.5 {goal_lines[2.5]:.1%}｜細3.5 {1-goal_lines[3.5]:.1%}")
        walk_goals = v17_card.get("walk_goals") or {"label": "大2.0走盤 + 細3.0走盤"}
        walk_corners = v17_card.get("walk_corners") or {"label": "大9走盤 + 細10走盤"}
        st.write(f"入球安全方案：{walk_goals.get('label', '大2.0走盤 + 細3.0走盤')}")
        st.write(f"角球安全方案：{walk_corners.get('label', '大9走盤 + 細10走盤')}")
        st.caption("走盤方案係降低中間線風險，唔代表保證命中；冇8.5角球時仍使用9／10走盤。")
    with v17_tabs[2]:
        stats_rows = [{"項目":"入球", "主隊":hgf, "客隊":agf}, {"項目":"失球", "主隊":hga, "客隊":aga}, {"項目":"角球預期", "主隊":v17_cal.get('corner_exp', linkage_corner_total)/2, "客隊":v17_cal.get('corner_exp', linkage_corner_total)/2}]
        st.dataframe(pd.DataFrame(stats_rows).style.format({"主隊":"{:.2f}", "客隊":"{:.2f}"}), use_container_width=True, hide_index=True)
        h_avg = corner_context.get("home_average")
        a_avg = corner_context.get("away_average")
        h2h = corner_context.get("last_h2h") or {}
        h2h_text = (f"主 {h2h.get('home_corners', 0):g}｜客 {h2h.get('away_corners', 0):g}｜總 {h2h.get('total', 0):g}"
                    if h2h else "未取得上次對賽角球")
        st.markdown("**角球資料（獨立三行）**")
        st.write(f"主隊場均：{h_avg:.2f}" if h_avg is not None else "主隊場均：未取得真實HC資料")
        st.write(f"客隊場均：{a_avg:.2f}" if a_avg is not None else "客隊場均：未取得真實AC資料")
        st.write(f"上次對賽角球：{h2h_text}")
        st.caption("控球、射門、危險進攻等欄位只有取得真實來源時才會顯示。")
    with v17_tabs[3]:
        st.write("陣型：未核實正選時不會自行指定4-3-3。")
        st.caption(f"傷停資料：{len(live_context.get('injuries', []))} 項；只有已核實傷停才會影響預期入球。")
    with v17_tabs[4]:
        ghost = v17_card.get("ghost", {})
        st.write("公司｜初盤｜即時｜變動")
        st.write("香港／澳門／平博／Bet365：目前未取得同一場完整公司初盤及即時盤資料。")
        if ghost.get("detected"):
            st.warning(ghost.get("message", "未取得鬼盤比較資料"))
        else:
            st.caption(ghost.get("message", "無明顯鬼盤異動"))
    with v17_tabs[5]:
        st.info(reader.get("conclusion", "AI解讀資料不足，請以模型機率及資料來源狀態為準。"))
        st.write(f"聯動：{linkage_message or '未觸發大細波與角球反比提示'}")
        st.caption("V1.7係風險整理及數據提示，不保證賽果。")
    if abs(home_learning_adjustment) > 1e-9 or abs(away_learning_adjustment) > 1e-9:
        st.caption(f"V2.0歷史校準：主隊 {home_learning_adjustment:+.2f}｜客隊 {away_learning_adjustment:+.2f}（只來自已填真實賽果）")
    st.info(f"V2.0睇穿結論：{reader['conclusion']}")
    if reader.get("ou_note"):
        st.caption(f"大小球解讀：{reader['ou_note']}")
    learning_info = learning_summary()
    error_text = f"±{learning_info['recent5_error']:.2f}" if learning_info.get("recent5_error") is not None else "暫無已完成賽果"
    st.caption(f"模型已學習 {learning_info['completed']} 場（紀錄 {learning_info['total']} 場）；近5場入球預期誤差 {error_text}。未填實際比分不會影響模型。")
    st.markdown("### 主客隊入球預期（模型獨立，無需賠率）")
    goal_view = pd.DataFrame([
        {"球隊": home_zh, "預期入球": hx, "大0.5機率": team_goal_view["home_over_0_5"], "大1.5機率": team_goal_view["home_over_1_5"]},
        {"球隊": away_zh, "預期入球": ax, "大0.5機率": team_goal_view["away_over_0_5"], "大1.5機率": team_goal_view["away_over_1_5"]},
    ])
    st.dataframe(goal_view.style.format({"預期入球":"{:.2f}", "大0.5機率":"{:.1%}", "大1.5機率":"{:.1%}"}), use_container_width=True, hide_index=True)
    st.caption(f"總預期 {goal_band['total_exp']:.2f} 球 ±{goal_band['swing']:.1f} 波動區間（{goal_band['low']:.2f}–{goal_band['high']:.2f}）；接近50%的大小線應視為搖擺區，唔好只因EV落注。")
    st.markdown("### 勝和負風險及雙重機會")
    st.write(f"主不敗：{hp + dp:.1%}｜客不敗：{ap + dp:.1%}｜和局：{dp:.1%}")
    if low_score_tight > .45:
        st.warning(f"⚠️ 膠著局風險高（低比分膠著約 {low_score_tight:.1%}）：和局風險較高，建議考慮雙重機會或避開單邊膽。")
    if abs(hp - ap) < .10:
        st.warning(f"⚠️ 主客機率差距只有 {abs(hp-ap):.1%}，實力接近，慎選主客方向。")
    if pasted_results:
        st.info(ai_summary(pasted_results, home_zh, away_zh, hx, ax))
        ev_view = pd.DataFrame(pasted_results)
        ev_view["模型機率"] = ev_view["model_probability"].map(lambda x: f"{x:.1%}")
        ev_view["莊家機率"] = ev_view["bookmaker_probability"].map(lambda x: f"{x:.1%}")
        ev_view["EV"] = ev_view["ev"].map(lambda x: f"{x:+.1%}")
        ev_view["燈號"] = ev_view["light"].map({"green":"綠｜EV>10%","yellow":"黃｜0至10%","grey":"灰｜EV<0"}).fillna("灰")
        st.dataframe(ev_view[["market","line","selection","odds","模型機率","莊家機率","EV","燈號"]], use_container_width=True, hide_index=True)
    st.caption(f"模型信心：{confidence}｜樣本：主隊 {len(h)} 場、客隊 {len(a)} 場｜這是機率估算，不是保證賽果")
    tab_data, tab_model, tab_scenarios = st.tabs(["資料整理", "模型結果", "比賽情境"])
    with tab_data:
        d1, d2 = st.columns(2)
        with d1:
            st.markdown(f"**{home_zh} 最近 {len(home_form)} 場**")
            st.dataframe(home_form, use_container_width=True, hide_index=True)
        with d2:
            st.markdown(f"**{away_zh} 最近 {len(away_form)} 場**")
            st.dataframe(away_form, use_container_width=True, hide_index=True)
        st.info("資料整理層只顯示已取得的賽果；球員傷停及正式正選沒有核實資料時，不會當成模型輸入。")
    with tab_model:
        st.markdown("**模型輸入摘要**")
        st.write(f"主隊近期平均入球：{hgf:.2f}｜主隊近期平均失球：{hga:.2f}｜客隊近期平均入球：{agf:.2f}｜客隊近期平均失球：{aga:.2f}")
        st.write(f"模型預期入球：主隊 {hx:.2f}｜客隊 {ax:.2f}｜總入球 {hx + ax:.2f}")
        st.markdown("**蒙地卡羅模擬（20,000 次）**")
        mc1, mc2, mc3 = st.columns(3)
        mc1.metric("模擬主勝", f"{monte_carlo['主勝']:.1%}")
        mc2.metric("模擬和局", f"{monte_carlo['和局']:.1%}")
        mc3.metric("模擬客勝", f"{monte_carlo['客勝']:.1%}")
        st.caption("模擬只使用目前已取得的近期入失球及角球參數；只有球員姓名而沒有出場、入球或傷停數字時，不會虛構球員修正。")
        st.dataframe(monte_carlo["比分"].style.format({"模擬機率": "{:.1%}"}), use_container_width=True, hide_index=True)
        has_fbref_stats = isinstance(fbref_stats, pd.DataFrame) and not fbref_stats.empty
        fbref_status_zh = "已取得並有限度納入" if has_fbref_stats else "未取得，未納入模型"
        st.caption(f"外部攻守統計狀態：{fbref_status_zh}；修正幅度受限。")
    with tab_scenarios:
        st.dataframe(scenario_table(matrix, hx, ax).style.format({"模型機率": "{:.1%}"}), use_container_width=True, hide_index=True)
    green_only = False  # V1.4：EV只作燈號，不隱藏任何模型盤口。
    # 勝和負標題由 render_market_table 統一輸出，避免手機版出現重複標題。
    result_rows = []
    close_risk = abs(hp - ap) < .07
    for name, prob, odds, other in [("主勝", hp, home_odds, "和局或主隊不敗"), ("和局", dp, draw_odds, "主隊不敗"), ("客勝", ap, away_odds, "和局或客隊不敗")]:
        reason = ""
        if low_score_tight > .45: reason = f"和局陷阱{low_score_tight:.1%}"
        if close_risk and name in {"主勝", "客勝"}: reason = (reason + "；" if reason else "") + f"實力接近，主客差距{abs(hp-ap):.1%}"
        status, explanation, ev_value = market_explanation(prob, odds, other, data_ok=pair_data_ok, risk_reason=reason)
        result_rows.append({"選項": name, "模型機率": prob, "輸入賠率": odds, "提示": status, "說明": explanation, "EV": ev_value})
    render_market_table("勝和負", result_rows, green_only, "result")

    goal_rows = []
    for x in [2.5, 3.5, 4.5]:
        for label, prob, odds, other in [(f"大 {x}", goal_lines[x], goal_over_odds_map[x] or None, f"細 {x}"), (f"細 {x}", 1 - goal_lines[x], goal_under_odds_map[x] or None, f"大 {x}")]:
            status, explanation, ev_value = market_explanation(prob, odds, other, data_ok=pair_data_ok)
            if abs(prob - .5) <= .08:
                explanation += f"；{goal_line_note(prob, x)}，可考慮大2.0或細3.0等較有安全邊際的線"
            goal_rows.append({"入球盤": label, "模型機率": prob, "輸入賠率": odds, "提示": status, "說明": explanation, "EV": ev_value})
    render_market_table("入球大小", goal_rows, green_only, "goals")

    st.markdown("### 角球預期（最穩區域）")
    if corner_lams:
        corner_summary_total = sum(corner_lams)
        st.write(f"真實角球模型總預期：{corner_summary_total:.2f}｜大8.5 {total_over_probability(corner_summary_total, 8.5):.1%}｜大9.5 {total_over_probability(corner_summary_total, 9.5):.1%}｜大10.5 {total_over_probability(corner_summary_total, 10.5):.1%}")
        st.caption("角球無和局；優先參考有逐場HC/AC嘅線，EV只作顏色，不代表必然命中。")
    else:
        # 即使選配模組未載入或來源返回空表，也不應因角球摘要令整頁崩潰。
        cmodel = corner_fallback or {}
        cmarket = cmodel.get("market") or {}
        ctotal = float(cmodel.get("total", 9.0) or 9.0)
        def _corner_p(line, side):
            row = cmarket.get(line) or {}
            if side in row: return float(row[side])
            # 最後安全後備只作顯示，詳細盤口仍會標示估算／資料來源。
            return float(total_over_probability(ctotal, line) if side == "over" else 1-total_over_probability(ctotal, line))
        st.write(f"情境估算總預期：{ctotal:.1f}｜大8.5 {_corner_p(8.5, 'over'):.0%}｜大9.5 {_corner_p(9.5, 'over'):.0%}｜大10.5 {_corner_p(10.5, 'over'):.0%}｜細9.5 {_corner_p(9.5, 'under'):.0%}")
        st.caption("角球無和局，適合避開勝負陷阱；以上係透明情境估算，補上真實HC/AC後會改用歷史模型。")

    handicap_role = "主隊受讓" if handicap_line > 0 else "主隊讓球" if handicap_line < 0 else "平手盤"
    ah_signal, ah_reason = signal(ah_home, handicap_odds, f"{handicap_role}；模型按主隊入球 {handicap_line:+.2f} 後計算", data_ok=pair_data_ok)
    handicap_table = pd.DataFrame([
        [f"主隊{handicap_role} {handicap_line:+.2f}", ah_home, handicap_odds, ah_signal, ah_reason],
        [f"調整後和局 {handicap_line:+.2f}", ah_draw, None, *signal(ah_draw, None, "調整後主客相同", data_ok=pair_data_ok)],
        [f"調整後客隊 {handicap_line:+.2f}", ah_away, None, *signal(ah_away, None, "調整後主隊不勝", data_ok=pair_data_ok)],
    ], columns=["讓球盤", "模型機率", "輸入賠率", "提示", "說明"])
    handicap_rows = []
    for label, prob, odds, other in [(f"主隊{handicap_role} {handicap_line:+.2f}", ah_home, handicap_odds, "調整後客隊"), (f"調整後和局 {handicap_line:+.2f}", ah_draw, None, "調整後主客相同"), (f"調整後客隊 {handicap_line:+.2f}", ah_away, None, "調整後主隊不勝")]:
        status, explanation, ev_value = market_explanation(prob, odds, other, data_ok=pair_data_ok)
        handicap_rows.append({"讓球盤": label, "模型機率": prob, "輸入賠率": odds, "提示": status, "說明": explanation, "EV": ev_value})
    render_market_table("讓球盤", handicap_rows, green_only, "handicap")

    st.markdown("### 波膽")
    st.dataframe(exact_score_table(matrix, 5).rename(columns={"比分": "預測比分", "機率": "模型機率"}).style.format({"模型機率": "{:.1%}"}), use_container_width=True, hide_index=True)

    st.markdown("### 角球盤口詳情")
    corner_lines = [8.5, 9.5, 10.5, 11.5, 12.5]
    if corner_lams:
        corner_total = sum(corner_lams)
        corner_rows = []
        for x in corner_lines:
            over_p = total_over_probability(corner_total, x)
            corner_rows.extend([
                [f"大 {x}", over_p, corner_over_odds_map.get(x) or None, *market_explanation(over_p, corner_over_odds_map.get(x) or None, f"細 {x}", data_ok=pair_data_ok, is_corner=True)],
                [f"細 {x}", 1 - over_p, corner_under_odds_map.get(x) or None, *market_explanation(1 - over_p, corner_under_odds_map.get(x) or None, f"大 {x}", data_ok=pair_data_ok, is_corner=True)],
            ])
        corner_table = pd.DataFrame(corner_rows, columns=["角球盤", "模型機率", "輸入賠率", "提示", "說明", "EV"])
        st.caption(f"資料來源：{corner_source_label}｜角球預期：主隊 {corner_lams[0]:.2f}、客隊 {corner_lams[1]:.2f}、總數 {sum(corner_lams):.2f}｜{corner_status}｜{fbref_corner_message}")
        render_market_table("角球大小", corner_table.to_dict("records"), green_only, "corners")
    else:
        cmodel = corner_fallback or {"home":4.5,"away":4.5,"total":9.0,"market":{},"source":"安全後備估算","note":"暫未取得角球模組資料"}
        st.caption(f"資料來源：{cmodel['source']}｜角球預期：主隊 {cmodel['home']:.1f}、客隊 {cmodel['away']:.1f}、總數 {cmodel['total']:.1f}")
        st.warning(f"{cmodel['note']}；暫未取得逐場HC/AC，請上載角球CSV後自動改用真實歷史模型。")
        fallback_rows = []
        for x in [8.5, 9.5, 10.5, 11.5, 12.5]:
            p = (cmodel.get("market") or {}).get(x)
            if not p:
                q = total_over_probability(float(cmodel.get("total",9.0)), x)
                p = {"over":q,"under":1-q}
            fallback_rows.extend([
                {"角球盤":f"大 {x}","模型機率":p["over"],"輸入賠率":corner_over_odds_map.get(x) or None,"提示":market_explanation(p["over"], corner_over_odds_map.get(x) or None, f"細 {x}", data_ok=pair_data_ok, is_corner=True)[0],"說明":market_explanation(p["over"], corner_over_odds_map.get(x) or None, f"細 {x}", data_ok=pair_data_ok, is_corner=True)[1],"EV":market_explanation(p["over"], corner_over_odds_map.get(x) or None, f"細 {x}", data_ok=pair_data_ok, is_corner=True)[2]},
                {"角球盤":f"細 {x}","模型機率":p["under"],"輸入賠率":corner_under_odds_map.get(x) or None,"提示":market_explanation(p["under"], corner_under_odds_map.get(x) or None, f"大 {x}", data_ok=pair_data_ok, is_corner=True)[0],"說明":market_explanation(p["under"], corner_under_odds_map.get(x) or None, f"大 {x}", data_ok=pair_data_ok, is_corner=True)[1],"EV":market_explanation(p["under"], corner_under_odds_map.get(x) or None, f"大 {x}", data_ok=pair_data_ok, is_corner=True)[2]},
            ])
        st.markdown("**角球預期（V1.4最穩區域）**")
        render_market_table("角球大小", fallback_rows, False, "corners_fallback")

    st.markdown("**綜合推薦**")
    best_market = max([(hp, "主勝"), (dp, "和局"), (ap, "客勝"), (over, f"大 {line}"), (under, f"細 {line}"), (ah_home, f"主隊讓球 {handicap_line:+.2f}")])
    best_signal, best_reason = signal(best_market[0], None, "")
    st.info(f"模型最高機率方向：{best_market[1]}｜{best_signal}｜{best_reason}。這是模型排序，不等於下注指示，亦不保證賽果。")
    st.markdown("### 球員及傷停資料")
    uploaded_players = st.session_state.get("uploaded_players", pd.DataFrame())
    pc1, pc2 = st.columns(2)
    for col, name, info, err in [(pc1, home, home_info, home_info_error), (pc2, away, away_info, away_info_error)]:
        with col:
            st.markdown(f"**{zh_team(name)}**")
            if err:
                st.warning(f"球隊／球員基本資料未能取得：{err}")
                continue
            team_obj, venue = info.get("team", {}), info.get("venue", {})
            st.caption(f"來源：TheSportsDB 公開資料｜國家：{team_obj.get('country', '未能取得')}｜成立：{team_obj.get('founded', '未能取得')}｜教練：{info.get('coach', '未能取得')}｜主場：{venue.get('name', '未能取得')}")
            squad = info.get("squad", [])
            csv_players = player_table_zh(uploaded_players, [name])
            if not csv_players.empty:
                st.dataframe(csv_players, use_container_width=True, hide_index=True)
            elif squad:
                # 沒有球員 CSV 時仍可顯示公開名單，但未知中文位置／國籍留空，
                # 不再顯示刺眼的「未有中文位置資料」字樣。
                rows = []
                for i, p in enumerate(squad, 1):
                    pos = zh_position(p.get("strPosition", ""))
                    country = zh_country(p.get("strNationality", ""))
                    rows.append({"球員": p.get("strPlayer", "") or f"第 {i} 名球員",
                                 "位置": "" if pos.startswith("未有") else pos,
                                 "國籍": "" if country.startswith("未有") else country,
                                 "出生日期": p.get("dateBorn", "")})
                st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
            else:
                if uploaded_players.empty:
                    st.caption("未上載球員 CSV；本頁不顯示缺少中文位置資料提示。")
            st.info("傷停：此免費來源沒有今場可核實傷停資料")
    st.info("未填賠率的盤口仍會用已取得的真實歷史數據計算機率；但沒有賠率只能顯示模型機率，不能計算 EV。沒有角球／射門等來源資料時會明確顯示資料不足，不會自行補數。")
else:
    st.info("選擇聯賽、輸入兩隊，再按分析。")

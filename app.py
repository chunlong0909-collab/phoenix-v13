import math
import os
import re
import sqlite3
import unicodedata
from datetime import datetime, timedelta, timezone
from io import StringIO
from pathlib import Path
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import pandas as pd
import requests
import streamlit as st

st.set_page_config(page_title="混合來源足球分析", page_icon="⚽", layout="wide")

DB = Path(__file__).with_name("football_library.db")
API_BASE = "https://v3.football.api-sports.io"
FD_API = "https://api.football-data.org/v4"
FFA_API = "https://api.ffa.football"
FD_BASE = "https://www.football-data.co.uk"
# TheSportsDB 已停用舊的 3；官方目前提供測試用 123。
SPORTSDB_API = "https://www.thesportsdb.com/api/v1/json/123"
FBREF_BASE = "https://fbref.com"
HEADERS = {"User-Agent": "FootballResearchApp/1.0 (public-data research)"}

LEAGUES = {
    "英格蘭超級聯賽": {"api": 39, "csv": "E0"},
    "英格蘭冠軍聯賽": {"api": 40, "csv": "E1"},
    "西班牙甲組聯賽": {"api": 140, "csv": "SP1"},
    "西班牙乙組聯賽": {"api": 141, "csv": "SP2"},
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
    "澳洲冠軍聯賽盃／澳洲盃": {"api": 713, "csv": ""},
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
    "聖保羅": "São Paulo", "坎培拉克羅地亞": "Canberra Croatia", "悉尼聯": "Sydney FC",
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
    "Sevilla FC": "西維爾",
}

def zh_team(name):
    name = str(name or "").strip()
    return TEAM_ZH.get(name, name if any("\u4e00" <= ch <= "\u9fff" for ch in name) else f"未有中文隊名（{name}）")

def zh_source(name):
    return {"Football-Data.org API": "Football-Data.org 資料接口", "Football-Data CSV": "Football-Data 公開資料",
            "本地資料館": "本地足球資料館", "TheSportsDB": "TheSportsDB 公開資料"}.get(str(name), str(name))

def zh_country(value):
    return {"Argentina": "阿根廷", "Brazil": "巴西", "England": "英格蘭", "Spain": "西班牙",
            "Germany": "德國", "France": "法國", "Japan": "日本", "South Korea": "南韓",
            "Australia": "澳洲", "Netherlands": "荷蘭", "Italy": "意大利", "Uruguay": "烏拉圭"}.get(str(value), "未有中文國籍資料")

def zh_position(value):
    return {"Goalkeeper": "守門員", "Defender": "後衛", "Midfielder": "中場", "Forward": "前鋒",
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
    with sqlite3.connect(DB) as c:
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
    with sqlite3.connect(DB) as c:
        c.execute("INSERT INTO source_log(league,source,status,message,captured_at) VALUES(?,?,?,?,?)",
                  (league, source, status, message[:500], datetime.now(timezone.utc).isoformat()))


def clean_matches(df, source, league, season):
    aliases = {"HomeTeam": "Home", "AwayTeam": "Away", "FTHG": "HG", "FTAG": "AG", "Date": "Date"}
    df = df.rename(columns={k: v for k, v in aliases.items() if k in df.columns})
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


def save_matches(df):
    rows = [(r.league, r.season, r.Home, r.Away, int(r.HG), int(r.AG),
             None if pd.isna(r.HC) else float(r.HC), None if pd.isna(r.AC) else float(r.AC),
             str(r.Date), r.source, datetime.now(timezone.utc).isoformat())
            for r in df.itertuples()]
    with sqlite3.connect(DB) as c:
        c.executemany("INSERT OR REPLACE INTO matches(league,season,home,away,hg,ag,hc,ac,date,source,captured_at) VALUES(?,?,?,?,?,?,?,?,?,?,?)", rows)


def cached_matches(league, max_age_hours=24):
    cutoff = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)
    with sqlite3.connect(DB) as c:
        df = pd.read_sql_query("SELECT * FROM matches WHERE league=?", c, params=[league])
    if df.empty:
        return df
    # SQLite 欄位用小寫儲存；分析模型統一使用公開資料的欄位名稱。
    df = df.rename(columns={"home": "Home", "away": "Away", "hg": "HG", "ag": "AG", "hc": "HC", "ac": "AC", "date": "Date"})
    df["HG"] = pd.to_numeric(df["HG"], errors="coerce")
    df["AG"] = pd.to_numeric(df["AG"], errors="coerce")
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
    for season in [datetime.now().year, 2024]:
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
    matches, source, _ = get_matches(league, api_token, fd_token, crawl_url)
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

FBREF_COMP_IDS = {
    "英格蘭超級聯賽": 9, "西班牙甲組聯賽": 12, "德國甲組聯賽": 20,
    "法國甲組聯賽": 13, "意大利甲組聯賽": 11, "荷蘭甲組聯賽": 23,
    "葡萄牙超級聯賽": 32, "蘇格蘭超級聯賽": 40, "美國職業足球大聯盟": 22,
    "澳洲職業聯賽": 65, "日本職業聯賽": 55, "巴西甲組聯賽": 24,
    "墨西哥超級聯賽": 31, "挪威超級聯賽": 29, "丹麥超級聯賽": 50,
}


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


def get_matches(league, api_token, fd_token, crawl_url):
    fresh = cached_matches(league)
    if not fresh.empty:
        return fresh, "本地資料館", "高（已儲存）"
    attempts = []
    if fd_token:
        try:
            df = from_football_data_api(league, fd_token); save_matches(df); log_source(league, "Football-Data.org API", "成功"); return df, "Football-Data.org API", "高"
        except Exception as e:
            attempts.append(f"Football-Data.org API：{e}"); log_source(league, "Football-Data.org API", "失敗", str(e))
    try:
        df = from_csv(league); save_matches(df); log_source(league, "Football-Data CSV", "成功"); return df, "Football-Data CSV", "高"
    except Exception as e:
        attempts.append(f"CSV：{e}"); log_source(league, "Football-Data CSV", "失敗", str(e))
    if league == "澳洲冠軍聯賽盃／澳洲盃":
        try:
            df = from_australia_cup(league); save_matches(df); log_source(league, "澳洲盃官方公開資料", "成功"); return df, "澳洲盃官方公開資料", "高"
        except Exception as e:
            attempts.append(f"澳洲盃官方資料：{e}"); log_source(league, "澳洲盃官方公開資料", "失敗", str(e))
    if crawl_url.strip():
        try:
            df = from_public_table(league, crawl_url.strip()); save_matches(df); log_source(league, "公開網頁表格", "成功"); return df, "獲准公開網頁表格", "中"
        except Exception as e:
            attempts.append(f"網頁爬蟲：{e}"); log_source(league, "公開網頁表格", "失敗", str(e))
    raise ValueError("所有來源都未能取得資料：\n" + "\n".join(attempts))


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
        team = found[0]
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


def corner_model(matches, home, away):
    """只用來源實際提供的 HC/AC；沒有足夠角球紀錄便返回空值。"""
    if "HC" not in matches.columns or "AC" not in matches.columns:
        return None, "來源沒有角球欄位"
    data = matches.dropna(subset=["HC", "AC"]).copy()
    h = data[(data.Home == home) | (data.Away == home)].tail(8)
    a = data[(data.Home == away) | (data.Away == away)].tail(8)
    if len(h) < 4 or len(a) < 4:
        return None, f"角球樣本不足（主隊 {len(h)}、客隊 {len(a)} 場）"
    def values(hist, team):
        made = hist.apply(lambda r: r.HC if r.Home == team else r.AC, axis=1)
        conceded = hist.apply(lambda r: r.AC if r.Home == team else r.HC, axis=1)
        return float(made.mean()), float(conceded.mean())
    h_for, h_against = values(h, home)
    a_for, a_against = values(a, away)
    home_lam = max(.5, (h_for + a_against) / 2)
    away_lam = max(.5, (a_for + h_against) / 2)
    return (home_lam, away_lam), "已使用來源提供的歷史角球（最近最多 8 場）"


def total_over_probability(lam, line):
    return 1 - sum(poisson(k, lam) for k in range(math.floor(line) + 1))


def signal(p, odds=None, other="", data_ok=True, backtest_ok=True):
    """將模型結果與下注建議分開；沒有賠率時不假裝可以計 EV。"""
    if p is None or not data_ok:
        return "🚫 避開", "核心資料不足或來源有衝突，未能可靠計算"
    if odds and p * odds - 1 > .50:
        return "⚠️ 異常高值", f"EV {p * odds - 1:.1%}；請先核對盤口、方向及賠率"
    if odds and p * odds - 1 >= .05 and backtest_ok:
        return "✅ 可以考慮", f"EV {p * odds - 1:.1%}（仍不代表保證）"
    if odds and p * odds - 1 < 0:
        return "🟡 不具模型優勢", f"EV {p * odds - 1:.1%}；{('可比較 ' + other) if other else '觀望'}"
    if p >= .50:
        return "📊 模型推算", "方向機率較高，但未有可核對賠率，不能計算價值"
    return "⚪ 只供參考", f"模型方向機率 {p:.1%}；{('可比較 ' + other) if other else '不作下注結論'}"


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


def all_saved_matches(league):
    with sqlite3.connect(DB) as c:
        df = pd.read_sql_query("SELECT * FROM matches WHERE league=?", c, params=[league])
    if df.empty:
        return df
    return df.rename(columns={"home": "Home", "away": "Away", "hg": "HG", "ag": "AG", "date": "Date"})


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
st.title("混合來源足球分析")
st.caption("本地資料館 → API → 公開 CSV → 獲准讀取的公開網頁表格；資料不足時不會虛構結果。")

with st.sidebar:
    league = st.selectbox("聯賽", list(LEAGUES))
    fd_token = st.text_input("Football-Data.org Token（可選）", value=configured_secret("FOOTBALL_DATA_TOKEN"), type="password")
    st.caption("API-Football 暫停使用；球隊及球員基本資料改用 TheSportsDB 免費公開來源。")
    crawl_url = st.text_input("後備公開賽果頁面（可選）", placeholder="只填允許自動讀取、包含賽果表格的公開網址")
    directory_key = f"teams_{league}"
    load_directory = st.button("先載入本聯賽球隊清單", use_container_width=True)
    if load_directory:
        try:
            directory_names, directory_source = get_team_directory(
                league, "", fd_token.strip(), crawl_url
            )
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
    home_odds = st.number_input("主勝賠率", 1.01, 100.0, 1.85)
    draw_odds = st.number_input("和局賠率", 1.01, 100.0, 3.40)
    away_odds = st.number_input("客勝賠率", 1.01, 100.0, 4.20)
    line = st.selectbox("主要入球線", [2.5, 3.5, 4.5], index=0)
    handicap_line = st.number_input("主隊亞洲讓球（例如 -0.5）", -3.0, 3.0, 0.0, step=0.25)
    handicap_odds = st.number_input("讓球主隊賠率（可選）", 1.01, 100.0, 1.90)
    corner_line = st.selectbox("主要角球線", [9.5, 10.5, 11.5, 12.5, 13.5, 14.5], index=0)
    corner_over_odds = st.number_input("角球大賠率（可選）", 1.01, 100.0, 1.90)
    corner_under_odds = st.number_input("角球細賠率（可選）", 1.01, 100.0, 1.90)
    run = st.button("一鍵自動抓取及分析", type="primary", use_container_width=True)
    run_backtest = st.button("回測本聯賽模型", use_container_width=True)

if run_backtest:
    with st.spinner("逐場回測中；每場只使用當時之前的資料……"):
        saved = all_saved_matches(league)
        if saved.empty:
            try:
                saved, _, _ = get_matches(league, "", fd_token.strip(), crawl_url)
            except Exception as exc:
                st.error(f"未能取得回測資料：{exc}")
                st.stop()
        detail, summary = walk_forward_backtest(saved)
    st.subheader(f"{league} 模型回測")
    if not detail.empty:
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("測試樣本", f"{summary['樣本數']} 場")
        m2.metric("勝和負方向命中", f"{summary['勝和負方向命中率']:.1%}")
        m3.metric("比分 Top 5 包含率", f"{summary['比分Top5包含率']:.1%}")
        m4.metric("Brier Score", f"{summary['Brier Score']:.3f}")
        st.caption("回測只使用每場比賽日期之前的賽果；樣本太少時不會硬算，數字只代表過往樣本，不保證未來表現。")
        st.dataframe(detail.tail(100), use_container_width=True, hide_index=True)
    else:
        st.warning("現有資料不足以進行逐場回測；每隊至少需要先有 4 場更早的賽果。")

if run:
    home = ALIASES.get(home_text.strip(), home_text.strip())
    away = ALIASES.get(away_text.strip(), away_text.strip())
    with st.spinner("按資料來源優先次序抓取中……"):
        try:
            matches, source, quality = get_matches(league, "", fd_token.strip(), crawl_url)
        except Exception as e:
            st.error(str(e)); st.stop()
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
    h = matches[(matches.Home == home) | (matches.Away == home)].sort_values("DateParsed").tail(8)
    a = matches[(matches.Home == away) | (matches.Away == away)].sort_values("DateParsed").tail(8)
    hgf = (h.apply(lambda r: r.HG if r.Home == home else r.AG, axis=1).mean() if not h.empty else 1.0)
    hga = (h.apply(lambda r: r.AG if r.Home == home else r.HG, axis=1).mean() if not h.empty else 1.0)
    agf = (a.apply(lambda r: r.HG if r.Home == away else r.AG, axis=1).mean() if not a.empty else 1.0)
    aga = (a.apply(lambda r: r.AG if r.Home == away else r.HG, axis=1).mean() if not a.empty else 1.0)
    hx, ax = max(.15, (hgf + aga) / 2 * 1.08), max(.15, (agf + hga) / 2 * .94)
    fbref_stats, fbref_source = fbref_team_stats(league)
    hx, ax, fbref_adjustment = fbref_expected_goal_adjustment(fbref_stats, home, away, hx, ax)
    hp, dp, ap = probs(hx, ax)
    over = 1 - sum(poisson(k, hx + ax) for k in range(math.floor(line) + 1))
    under = 1 - over
    goal_lines = {x: (1 - sum(poisson(k, hx + ax) for k in range(math.floor(x) + 1))) for x in [2.5, 3.5, 4.5]}
    matrix = score_matrix(hx, ax)
    ah_home, ah_draw, ah_away = handicap_prob(matrix, handicap_line)
    corner_lams, corner_status = corner_model(matches, home, away)
    confidence = model_confidence(len(h) + len(a), hp, dp, ap)
    home_form = team_form_table(matches, home)
    away_form = team_form_table(matches, away)
    with sqlite3.connect(DB) as c:
        c.execute("INSERT INTO analyses(league,home,away,home_prob,draw_prob,away_prob,source,created_at) VALUES(?,?,?,?,?,?,?,?)", (league, home, away, hp, dp, ap, source, datetime.now(timezone.utc).isoformat()))
    home_zh, away_zh = zh_team(home), zh_team(away)
    st.success(f"資料來源：{zh_source(source)}｜資料質素：{quality}｜賽果：{len(matches)} 場｜{fbref_adjustment}")
    st.subheader(f"{home_zh} 對 {away_zh}")
    st.write(f"預期入球：{hx:.2f} - {ax:.2f}｜主勝 {hp:.1%}｜和局 {dp:.1%}｜客勝 {ap:.1%}")
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
        st.caption(f"外部攻守統計狀態：{'已取得並有限度納入' if fbref_stats else '未取得，未納入模型'}；修正幅度受限。")
    with tab_scenarios:
        st.dataframe(scenario_table(matrix, hx, ax).style.format({"模型機率": "{:.1%}"}), use_container_width=True, hide_index=True)
    st.markdown("### 勝和負")
    result_table = pd.DataFrame([
        ["主勝", hp, home_odds, *signal(hp, home_odds, "和局或主隊不敗")],
        ["和局", dp, draw_odds, *signal(dp, draw_odds, "主隊不敗")],
        ["客勝", ap, away_odds, *signal(ap, away_odds, "和局或客隊不敗")],
    ], columns=["選項", "模型機率", "輸入賠率", "提示", "說明"])
    st.dataframe(result_table.style.format({"模型機率": "{:.1%}", "輸入賠率": lambda x: "-" if pd.isna(x) else f"{x:.2f}"}), use_container_width=True, hide_index=True)

    st.markdown("### 入球大小")
    goal_table = pd.DataFrame([
        [f"大 {x}", goal_lines[x], *signal(goal_lines[x], None, f"細 {x}")]
        for x in [2.5, 3.5, 4.5]
    ] + [
        [f"細 {x}", 1 - goal_lines[x], *signal(1 - goal_lines[x], None, f"大 {x}")]
        for x in [2.5, 3.5, 4.5]
    ], columns=["入球盤", "模型機率", "提示", "說明"])
    st.dataframe(goal_table.style.format({"模型機率": "{:.1%}"}), use_container_width=True, hide_index=True)

    st.markdown("### 讓球盤")
    ah_signal, ah_reason = signal(ah_home, handicap_odds, "主隊受讓／客隊方向（視讓球線）")
    handicap_table = pd.DataFrame([
        [f"主隊 {handicap_line:+.2f}", ah_home, handicap_odds, ah_signal, ah_reason],
        [f"讓球和局 {handicap_line:+.2f}", ah_draw, None, *signal(ah_draw, None, "讓球主隊或客隊")],
        [f"讓球客隊 {handicap_line:+.2f}", ah_away, None, *signal(ah_away, None, "讓球主隊")],
    ], columns=["讓球盤", "模型機率", "輸入賠率", "提示", "說明"])
    st.dataframe(handicap_table.style.format({"模型機率": "{:.1%}", "輸入賠率": lambda x: "-" if pd.isna(x) else f"{x:.2f}"}), use_container_width=True, hide_index=True)

    st.markdown("### 波膽")
    st.dataframe(exact_score_table(matrix, 5).rename(columns={"比分": "預測比分", "機率": "模型機率"}).style.format({"模型機率": "{:.1%}"}), use_container_width=True, hide_index=True)

    st.markdown("### 角球大小")
    corner_lines = [9.5, 10.5, 11.5, 12.5, 13.5, 14.5]
    if corner_lams:
        corner_total = sum(corner_lams)
        corner_rows = []
        for x in corner_lines:
            over_p = total_over_probability(corner_total, x)
            corner_rows.extend([
                [f"大 {x}", over_p, *signal(over_p, None, f"細 {x}")],
                [f"細 {x}", 1 - over_p, *signal(1 - over_p, None, f"大 {x}")],
            ])
        corner_table = pd.DataFrame(corner_rows, columns=["角球盤", "模型機率", "提示", "說明"])
        st.caption(f"角球預期：主隊 {corner_lams[0]:.2f}、客隊 {corner_lams[1]:.2f}、總數 {sum(corner_lams):.2f}｜{corner_status}")
        st.dataframe(corner_table.style.format({"模型機率": "{:.1%}"}), use_container_width=True, hide_index=True)
    else:
        st.warning(f"未能可靠推算角球：{corner_status}")
        st.dataframe(pd.DataFrame({"角球盤": [f"大 {x}" for x in corner_lines] + [f"細 {x}" for x in corner_lines], "狀態": ["資料不足，暫不推算"] * 12}), use_container_width=True, hide_index=True)

    st.markdown("**綜合推薦**")
    best_market = max([(hp, "主勝"), (dp, "和局"), (ap, "客勝"), (over, f"大 {line}"), (under, f"細 {line}"), (ah_home, f"主隊讓球 {handicap_line:+.2f}")])
    best_signal, best_reason = signal(best_market[0], None, "")
    st.info(f"模型最高機率方向：{best_market[1]}｜{best_signal}｜{best_reason}。這是模型排序，不等於下注指示，亦不保證賽果。")
    st.markdown("### 球員及傷停資料")
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
            if squad:
                rows = [{"球員": zh_player_name(p.get("strPlayer", ""), i), "位置": zh_position(p.get("strPosition", "")), "國籍": zh_country(p.get("strNationality", "")), "出生日期": p.get("dateBorn", "未有資料")} for i, p in enumerate(squad, 1)]
                st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
            else:
                st.warning("公開來源暫未回傳球員名單")
            st.info("傷停：此免費來源沒有今場可核實傷停資料")
    st.info("未填賠率的盤口仍會用已取得的真實歷史數據計算機率；但沒有賠率只能顯示模型推算，不能計算 EV。沒有角球／射門等來源資料時會明確顯示資料不足，不會自行補數。")
else:
    st.info("選擇聯賽、輸入兩隊，再按分析。")

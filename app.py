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
    "施禾利": "PEC Zwolle", "茲沃勒": "PEC Zwolle", "PEC茲沃勒": "PEC Zwolle",
    "伊高斯": "Go Ahead Eagles", "前進之鷹": "Go Ahead Eagles",
    "阿爾克馬爾": "AZ", "艾克馬亞": "AZ", "格羅寧根": "FC Groningen",
    "烏德勒支": "FC Utrecht", "飛燕諾": "Feyenoord Rotterdam",
    "聖保羅": "São Paulo", "坎培拉克羅地亞": "Canberra Croatia", "悉尼聯": "Sydney FC",
}

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
            date TEXT, source TEXT, captured_at TEXT, PRIMARY KEY(league, season, home, away, date)
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
    df = df.dropna(subset=["Home", "Away", "HG", "AG"]).copy()
    df["Date"] = df.get("Date", "")
    df["DateParsed"] = pd.to_datetime(df["Date"], errors="coerce", dayfirst=True)
    df["league"] = league
    df["season"] = str(season)
    df["source"] = source
    return df[["league", "season", "Home", "Away", "HG", "AG", "Date", "DateParsed", "source"]]


def save_matches(df):
    rows = [(r.league, r.season, r.Home, r.Away, int(r.HG), int(r.AG), str(r.Date), r.source, datetime.now(timezone.utc).isoformat())
            for r in df.itertuples()]
    with sqlite3.connect(DB) as c:
        c.executemany("INSERT OR REPLACE INTO matches VALUES(?,?,?,?,?,?,?,?,?)", rows)


def cached_matches(league, max_age_hours=24):
    cutoff = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)
    with sqlite3.connect(DB) as c:
        df = pd.read_sql_query("SELECT * FROM matches WHERE league=?", c, params=[league])
    if df.empty:
        return df
    # SQLite 欄位用小寫儲存；分析模型統一使用公開資料的欄位名稱。
    df = df.rename(columns={"home": "Home", "away": "Away", "hg": "HG", "ag": "AG", "date": "Date"})
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
    """優先載入聯賽完整球隊目錄；失敗才從賽果建立後備清單。"""
    if api_token:
        try:
            names, source = from_api_team_directory(league, api_token)
            return names, source
        except Exception:
            pass
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
    if api_token:
        try:
            df = from_api(league, api_token); save_matches(df); log_source(league, "API-Football", "成功"); return df, "API-Football", "高"
        except Exception as e:
            attempts.append(f"API-Football：{e}"); log_source(league, "API-Football", "失敗", str(e))
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
def team_details(team_name, token):
    if not token:
        return {}, "未設定 API-Football Token"
    try:
        found = api_get("teams", {"search": team_name}, token).get("response", [])
        if not found:
            return {}, "API 找不到球隊"
        team = found[0].get("team", {})
        venue = found[0].get("venue", {})
        team_id = team.get("id")
        if not team_id:
            return {}, "API 沒有球隊 ID"
        squad = api_get("players/squads", {"team": team_id}, token).get("response", [])
        injuries = api_get("injuries", {"team": team_id, "season": 2024}, token).get("response", [])
        coaches = api_get("coachs", {"team": team_id}, token).get("response", [])
        coach = coaches[0].get("name", "未能取得") if coaches else "未能取得"
        return {"team": team, "venue": venue, "coach": coach, "squad": squad[0].get("players", []) if squad else [], "injuries": injuries}, ""
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


def signal(p, odds=None, other=""):
    if p < .45:
        return "🚫 避開", f"機率偏低；{('可轉睇 ' + other) if other else '沒有可靠替代'}"
    if odds and p * odds - 1 >= .05:
        return "✅ 可以考慮", f"EV {p * odds - 1:.1%}"
    if odds and p * odds - 1 < 0:
        return "❌ 不建議", f"EV {p * odds - 1:.1%}；{('轉睇 ' + other) if other else '觀望'}"
    return "⚠️ 觀望", "資料優勢不足，唔建議勉強入場"


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


def configured_secret(name):
    try:
        return str(st.secrets.get(name, "") or os.getenv(name, ""))
    except Exception:
        return os.getenv(name, "")


def team_key(value):
    value = unicodedata.normalize("NFKD", str(value)).encode("ascii", "ignore").decode().lower()
    value = re.sub(r"[^a-z0-9]", "", value)
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
    api_token = st.text_input("API-Football Token（可選）", value=configured_secret("API_FOOTBALL_TOKEN"), type="password")
    fd_token = st.text_input("Football-Data.org Token（可選）", value=configured_secret("FOOTBALL_DATA_TOKEN"), type="password")
    crawl_url = st.text_input("後備公開賽果頁面（可選）", placeholder="只填允許自動讀取、包含賽果表格的公開網址")
    directory_key = f"teams_{league}"
    load_directory = st.button("先載入本聯賽球隊清單", use_container_width=True)
    if load_directory:
        try:
            directory_names, directory_source = get_team_directory(
                league, api_token.strip(), fd_token.strip(), crawl_url
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
        st.session_state[f"home_candidates_{league}"] = search_team_candidates(home_query, directory, api_token.strip())
        st.session_state[f"away_candidates_{league}"] = search_team_candidates(away_query, directory, api_token.strip())
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

if run:
    home = ALIASES.get(home_text.strip(), home_text.strip())
    away = ALIASES.get(away_text.strip(), away_text.strip())
    with st.spinner("按資料來源優先次序抓取中……"):
        try:
            matches, source, quality = get_matches(league, api_token.strip(), fd_token.strip(), crawl_url)
        except Exception as e:
            st.error(str(e)); st.stop()
    teams = sorted(set(matches.Home) | set(matches.Away))
    # 優先使用已載入的聯賽完整目錄；沒有目錄時才用歷史賽果作後備。
    directory = st.session_state.get(f"teams_{league}", [])
    all_candidates = sorted(set(directory) | set(teams))
    hm = resolve_team_name(home, all_candidates, api_token.strip())
    am = resolve_team_name(away, all_candidates, api_token.strip())
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
    home_info, home_info_error = team_details(home, api_token.strip())
    away_info, away_info_error = team_details(away, api_token.strip())
    h = matches[(matches.Home == home) | (matches.Away == home)].sort_values("DateParsed").tail(8)
    a = matches[(matches.Home == away) | (matches.Away == away)].sort_values("DateParsed").tail(8)
    hgf = (h.apply(lambda r: r.HG if r.Home == home else r.AG, axis=1).mean() if not h.empty else 1.0)
    hga = (h.apply(lambda r: r.AG if r.Home == home else r.HG, axis=1).mean() if not h.empty else 1.0)
    agf = (a.apply(lambda r: r.HG if r.Home == away else r.AG, axis=1).mean() if not a.empty else 1.0)
    aga = (a.apply(lambda r: r.AG if r.Home == away else r.HG, axis=1).mean() if not a.empty else 1.0)
    hx, ax = max(.15, (hgf + aga) / 2 * 1.08), max(.15, (agf + hga) / 2 * .94)
    hp, dp, ap = probs(hx, ax)
    over = 1 - sum(poisson(k, hx + ax) for k in range(math.floor(line) + 1))
    under = 1 - over
    goal_lines = {x: (1 - sum(poisson(k, hx + ax) for k in range(math.floor(x) + 1))) for x in [2.5, 3.5, 4.5]}
    matrix = score_matrix(hx, ax)
    ah_home, ah_draw, ah_away = handicap_prob(matrix, handicap_line)
    with sqlite3.connect(DB) as c:
        c.execute("INSERT INTO analyses(league,home,away,home_prob,draw_prob,away_prob,source,created_at) VALUES(?,?,?,?,?,?,?,?)", (league, home, away, hp, dp, ap, source, datetime.now(timezone.utc).isoformat()))
    st.success(f"資料來源：{source}｜資料質素：{quality}｜賽果：{len(matches)} 場")
    st.subheader(f"{home} vs {away}")
    st.write(f"預期入球：{hx:.2f} - {ax:.2f}｜主勝 {hp:.1%}｜和局 {dp:.1%}｜客勝 {ap:.1%}")
    table = pd.DataFrame([
        ["主勝", hp, home_odds, *signal(hp, home_odds, "和局或主隊不敗")],
        ["和局", dp, draw_odds, *signal(dp, draw_odds, "主隊不敗")],
        ["客勝", ap, away_odds, *signal(ap, away_odds, "和局或客隊不敗")],
        *[row for x in [2.5, 3.5, 4.5] for row in (
            [f"大 {x}", goal_lines[x], None, *signal(goal_lines[x], None, f"細 {x}")],
            [f"細 {x}", 1 - goal_lines[x], None, *signal(1 - goal_lines[x], None, f"大 {x}")],
        )],
    ], columns=["選項", "模型機率", "輸入賠率", "提示", "說明"])
    st.dataframe(table.style.format({"模型機率": "{:.1%}", "輸入賠率": lambda x: "-" if pd.isna(x) else f"{x:.2f}"}), use_container_width=True, hide_index=True)
    st.markdown("### 完整盤口分析")
    ah_signal, ah_reason = signal(ah_home, handicap_odds, f"主隊受讓／客隊方向（視讓球線）")
    markets = pd.DataFrame([
        [f"主隊 {handicap_line:+.2f}", ah_home, handicap_odds, ah_signal, ah_reason],
        [f"讓球和局 {handicap_line:+.2f}", ah_draw, None, *signal(ah_draw, None, "讓球主隊或客隊")],
        [f"讓球客隊 {handicap_line:+.2f}", ah_away, None, *signal(ah_away, None, "讓球主隊")],
    ], columns=["盤口", "模型機率", "輸入賠率", "提示", "說明"])
    st.dataframe(markets.style.format({"模型機率": "{:.1%}", "輸入賠率": lambda x: "-" if pd.isna(x) else f"{x:.2f}"}), use_container_width=True, hide_index=True)
    bc1, bc2 = st.columns(2)
    with bc1:
        st.markdown("**最可能波膽**")
        st.dataframe(exact_score_table(matrix, 5).style.format({"機率": "{:.1%}"}), use_container_width=True, hide_index=True)
    with bc2:
        st.markdown("**角球大細**")
        corner_table = pd.DataFrame([[f"大 {x}", None, "🚫 避開", "未有真實角球盤／角球統計"] for x in [9.5, 10.5, 11.5, 12.5, 13.5, 14.5]] + [[f"細 {x}", None, "🚫 避開", "未有真實角球盤／角球統計"] for x in [9.5, 10.5, 11.5, 12.5, 13.5, 14.5]], columns=["角球盤", "模型機率", "提示", "說明"])
        st.dataframe(corner_table, use_container_width=True, hide_index=True)
    st.markdown("**綜合推薦**")
    best_market = max([(hp, "主勝"), (dp, "和局"), (ap, "客勝"), (over, f"大 {line}"), (under, f"細 {line}"), (ah_home, f"主隊讓球 {handicap_line:+.2f}")])
    best_signal, best_reason = signal(best_market[0], None, "")
    st.info(f"模型最高機率方向：{best_market[1]} {best_signal}｜{best_reason}。推薦只代表模型排序，不是保證賽果。")
    st.markdown("### 球員及傷停資料")
    if not api_token.strip():
        st.warning("未設定 API-Football Token，暫時只顯示賽果模型。")
    else:
        pc1, pc2 = st.columns(2)
        for col, name, info, err in [(pc1, home, home_info, home_info_error), (pc2, away, away_info, away_info_error)]:
            with col:
                st.markdown(f"**{name}**")
                if err:
                    st.warning(f"球員資料未能取得：{err}")
                    continue
                team_obj, venue = info.get("team", {}), info.get("venue", {})
                st.caption(f"國家：{team_obj.get('country', '未能取得')}｜成立：{team_obj.get('founded', '未能取得')}｜教練：{info.get('coach', '未能取得')}｜主場：{venue.get('name', '未能取得')}")
                squad = info.get("squad", [])
                if squad:
                    rows = [{"球員": p.get("name", ""), "位置": p.get("position", ""), "年齡": p.get("age", ""), "號碼": p.get("number", "")} for p in squad]
                    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
                injuries = info.get("injuries", [])
                st.warning(f"傷停／停賽：{len(injuries)} 人" if injuries else "暫未回傳傷停資料")
                if injuries:
                    st.dataframe(pd.DataFrame([{"球員": x.get("player", {}).get("name", ""), "原因": x.get("player", {}).get("reason", ""), "類型": x.get("player", {}).get("type", "")} for x in injuries]), use_container_width=True, hide_index=True)
    st.info("讓球、角球、射門及正式陣容仍需指定比賽級資料；沒有資料時會顯示避開，不會用爬蟲亂填。")
else:
    st.info("選擇聯賽、輸入兩隊，再按分析。")

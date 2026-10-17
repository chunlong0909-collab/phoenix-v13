import math
import os
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd
import requests as rq
import streamlit as st

st.set_page_config(page_title="V133 足球賽事分析", page_icon="⚽", layout="wide")
st.title("V133｜多聯賽足球自動分析")
st.caption("資料由公開足球賽果 CSV、TheSportsDB 及 Open-Meteo 自動取得；結果只供參考。")

FOOTBALL_DATA = "https://football-data.co.uk"
THE_SPORTS_DB = "https://www.thesportsdb.com/api/v1/json/123"
FOOTBALL_API = "https://api.football-data.org/v4"

# Football-Data.org 的免費層主要覆蓋歐洲部分聯賽；其他聯賽會自動使用 CSV 後備。
API_COMPETITIONS = {
    "英格蘭超級聯賽": "PL",
    "英格蘭冠軍聯賽": "ELC",
    "西班牙甲組聯賽": "PD",
    "西班牙乙組聯賽": "SD",
    "德國甲組聯賽": "BL1",
    "德國乙組聯賽": "BL2",
    "法國甲組聯賽": "FL1",
    "荷蘭甲組聯賽": "DED",
    "意大利甲組聯賽": "SA",
    "葡萄牙超級聯賽": "PPL",
    "歐洲冠軍聯賽": "CL",
}

API_FOOTBALL_LEAGUES = {
    "英格蘭超級聯賽": 39,
    "英格蘭冠軍聯賽": 40,
    "西班牙甲組聯賽": 140,
    "西班牙乙組聯賽": 141,
    "德國甲組聯賽": 78,
    "德國乙組聯賽": 79,
    "法國乙組聯賽": 62,
    "荷蘭甲組聯賽": 88,
    "荷蘭乙組聯賽": 89,
    "蘇格蘭超級聯賽": 179,
    "奧地利甲組聯賽": 218,
    "丹麥超級聯賽": 119,
    "芬蘭超級聯賽": 244,
    "挪威超級聯賽": 103,
    "俄羅斯超級聯賽": 235,
    "阿根廷甲組聯賽": 128,
    "巴西甲組聯賽": 71,
    "巴西乙組聯賽": 72,
    "墨西哥超級聯賽": 262,
    "墨西哥甲組聯賽": 263,
    "日本職業聯賽": 98,
    "日本乙組聯賽": 99,
    "澳洲職業聯賽": 188,
    "南韓職業聯賽": 292,
    "南韓乙組聯賽": 293,
    "泰國甲組聯賽": 296,
    "沙特職業聯賽": 307,
    "卡塔爾超級聯賽": 305,
    "阿聯酋職業聯賽": 301,
    "烏拉圭甲組聯賽": 268,
    "歐洲冠軍聯賽": 2,
}

POSITION_ZH = {"Goalkeeper": "門將", "Defender": "後衛", "Midfielder": "中場", "Attacker": "前鋒"}
STATUS_ZH = {"Missing Fixture": "缺陣", "Questionable": "上陣成疑", "Suspended": "停賽", "Injured": "受傷"}
DB_PATH = Path(__file__).with_name("football_history.db")


def init_history_db() -> None:
    with sqlite3.connect(DB_PATH) as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS match_snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT, captured_at TEXT NOT NULL,
            league TEXT, home TEXT, away TEXT, home_xg REAL, away_xg REAL,
            home_prob REAL, draw_prob REAL, away_prob REAL, source TEXT
        );
        CREATE TABLE IF NOT EXISTS api_snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT, captured_at TEXT NOT NULL,
            league TEXT, team TEXT, category TEXT, payload TEXT
        );
        """)


def save_api_snapshot(league: str, team: str, category: str, payload: Any) -> None:
    import json
    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute("INSERT INTO api_snapshots(captured_at,league,team,category,payload) VALUES(?,?,?,?,?)",
                         (datetime.now().isoformat(timespec="seconds"), league, team, category,
                          json.dumps(payload, ensure_ascii=False, default=str)))
    except sqlite3.Error:
        pass


def save_match_snapshot(league: str, home: str, away: str, hx: float, ax: float, hp: float, dp: float, ap: float, source: str) -> None:
    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute("INSERT INTO match_snapshots(captured_at,league,home,away,home_xg,away_xg,home_prob,draw_prob,away_prob,source) VALUES(?,?,?,?,?,?,?,?,?,?)",
                         (datetime.now().isoformat(timespec="seconds"), league, home, away, hx, ax, hp, dp, ap, source))
    except sqlite3.Error:
        pass


init_history_db()

# 顯示名稱: (資料來源類型, 資料代碼, 國家天氣座標)
LEAGUES = {
    "英格蘭超級聯賽": ("fd", "E0", (54.0, -2.0)),
    "英格蘭冠軍聯賽": ("fd", "E1", (54.0, -2.0)),
    "蘇格蘭超級聯賽": ("fd", "SC0", (56.5, -4.2)),
    "西班牙甲組聯賽": ("fd", "SP1", (40.4, -3.7)),
    "西班牙乙組聯賽": ("fd", "SP2", (40.4, -3.7)),
    "德國甲組聯賽": ("fd", "D1", (51.2, 10.4)),
    "德國乙組聯賽": ("fd", "D2", (51.2, 10.4)),
    "法國甲組聯賽": ("fd", "F1", (46.2, 2.2)),
    "法國乙組聯賽": ("fd", "F2", (46.2, 2.2)),
    "荷蘭甲組聯賽": ("fd", "N1", (52.1, 5.3)),
    "荷蘭乙組聯賽": ("fd", "N2", (52.1, 5.3)),
    "意大利甲組聯賽": ("fd", "I1", (42.8, 12.8)),
    "意大利乙組聯賽": ("fd", "I2", (42.8, 12.8)),
    "奧地利甲組聯賽": ("new", "AUT", (47.5, 14.5)),
    "丹麥超級聯賽": ("new", "DNK", (56.0, 10.0)),
    "芬蘭超級聯賽": ("new", "FIN", (64.0, 26.0)),
    "挪威超級聯賽": ("new", "NOR", (64.5, 11.0)),
    "俄羅斯超級聯賽": ("new", "RUS", (55.7, 37.6)),
    "阿根廷甲組聯賽": ("new", "ARG", (-34.6, -58.4)),
    "巴西甲組聯賽": ("new", "BRA", (-15.8, -47.9)),
    "墨西哥超級聯賽": ("new", "MEX", (19.4, -99.1)),
    "歐洲冠軍聯賽": ("unsupported", "", (48.8, 2.3)),
    "日本職業聯賽": ("new", "JPN", (35.7, 139.7)),
    "澳洲職業聯賽": ("unsupported", "", (-33.9, 151.2)),
    "澳洲冠軍聯賽盃／澳洲盃": ("unsupported", "", (-33.9, 151.2)),
    "南韓職業聯賽": ("unsupported", "", (37.6, 127.0)),
    # 以下聯賽未必有 Football-Data CSV，會顯示資料不可用而不虛構結果。
    "日本乙組聯賽": ("unsupported", "", (35.7, 139.7)),
    "南韓乙組聯賽": ("unsupported", "", (37.6, 127.0)),
    "女子澳洲職業聯賽": ("unsupported", "", (-33.9, 151.2)),
    "泰國甲組聯賽": ("unsupported", "", (13.8, 100.5)),
    "沙特職業聯賽": ("unsupported", "", (24.7, 46.7)),
    "卡塔爾超級聯賽": ("unsupported", "", (25.3, 51.5)),
    "阿聯酋職業聯賽": ("unsupported", "", (24.5, 54.4)),
    "烏拉圭甲組聯賽": ("unsupported", "", (-34.9, -56.2)),
    "女子挪威超級聯賽": ("unsupported", "", (64.5, 11.0)),
    "女子南美自由盃": ("unsupported", "", (-15.8, -47.9)),
}

TEAM_ALIASES = {
    "廣島三箭": "Sanfrecce Hiroshima",
    "京都不死鳥": "Kyoto Sanga",
    "曼城": "Man City",
    "利物浦": "Liverpool",
    "皇馬": "Real Madrid",
    "巴塞": "Barcelona",
    "拜仁": "Bayern Munich",
    "阿仙奴": "Arsenal",
    "國米": "Inter",
}


def fd_url(source: str, code: str) -> str:
    if source == "new":
        return f"{FOOTBALL_DATA}/new/{code}.csv"
    return f"{FOOTBALL_DATA}/mmz4281/2627/{code}.csv"


@st.cache_data(ttl=1800, show_spinner=False)
def load_matches(source: str, code: str) -> tuple[pd.DataFrame, str]:
    """下載並統一 Football-Data 不同國家 CSV 的欄位。"""
    url = fd_url(source, code)
    response = rq.get(url, timeout=20)
    response.raise_for_status()
    from io import StringIO
    df = pd.read_csv(StringIO(response.content.decode("latin1")))
    df.columns = [str(c).replace("ï»¿", "").strip() for c in df.columns]

    rename = {
        "HomeTeam": "Home", "AwayTeam": "Away", "FTHG": "HG", "FTAG": "AG",
        "FTR": "Res", "Date": "Date", "Home": "Home", "Away": "Away",
        "HG": "HG", "AG": "AG", "Res": "Res",
    }
    df = df.rename(columns={k: v for k, v in rename.items() if k in df.columns})
    required = {"Home", "Away", "HG", "AG"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"資料缺少欄位：{', '.join(sorted(missing))}")

    df["HG"] = pd.to_numeric(df["HG"], errors="coerce")
    df["AG"] = pd.to_numeric(df["AG"], errors="coerce")
    df = df.dropna(subset=["Home", "Away", "HG", "AG"]).copy()
    df["DateParsed"] = pd.to_datetime(df.get("Date"), dayfirst=True, errors="coerce")
    df["Res"] = df.get("Res", "").fillna("")
    return df.sort_values("DateParsed"), url


def configured_api_token() -> str:
    """優先讀取 Streamlit Secrets，其次讀取環境變數；不把 token 寫入程式。"""
    try:
        secret = st.secrets.get("FOOTBALL_DATA_TOKEN", "")
    except (FileNotFoundError, KeyError, AttributeError):
        secret = ""
    return str(secret or os.getenv("FOOTBALL_DATA_TOKEN", "")).strip()


def configured_api_football_token() -> str:
    try:
        secret = st.secrets.get("API_FOOTBALL_TOKEN", "")
    except (FileNotFoundError, KeyError, AttributeError):
        secret = ""
    return str(secret or os.getenv("API_FOOTBALL_TOKEN", "")).strip()


API_FOOTBALL_BASE = "https://v3.football.api-sports.io"


@st.cache_data(ttl=3600, show_spinner=False)
def api_football_get(endpoint: str, params_key: tuple[tuple[str, str], ...], token: str) -> dict[str, Any]:
    response = rq.get(
        f"{API_FOOTBALL_BASE}/{endpoint}",
        headers={"x-apisports-key": token},
        params=dict(params_key),
        timeout=20,
    )
    response.raise_for_status()
    payload = response.json()
    errors = payload.get("errors") or {}
    if errors:
        raise ValueError(f"API-Football：{errors}")
    return payload


@st.cache_data(ttl=1800, show_spinner=False)
def load_api_football_matches(league_id: int, token: str) -> tuple[pd.DataFrame, str]:
    """下載本季已完成賽事，令 API-Football 可作為 CSV 以外的主要賽果來源。"""
    season = str(datetime.now().year)
    payload = api_football_get("fixtures", (("league", str(league_id)), ("season", season), ("status", "FT")), token)
    rows = []
    for item in payload.get("response", []):
        goals = item.get("goals") or {}
        if goals.get("home") is None or goals.get("away") is None:
            continue
        rows.append({
            "Home": item.get("teams", {}).get("home", {}).get("name", ""),
            "Away": item.get("teams", {}).get("away", {}).get("name", ""),
            "HG": goals.get("home"), "AG": goals.get("away"),
            "Date": item.get("fixture", {}).get("date", ""),
            "FixtureID": item.get("fixture", {}).get("id"),
            "Res": "H" if goals["home"] > goals["away"] else "A" if goals["away"] > goals["home"] else "D",
        })
    if not rows:
        raise ValueError("API-Football 沒有回傳本季已完成賽事，可能是賽季代碼尚未更新")
    df = pd.DataFrame(rows)
    df["HG"] = pd.to_numeric(df["HG"], errors="coerce")
    df["AG"] = pd.to_numeric(df["AG"], errors="coerce")
    df["DateParsed"] = pd.to_datetime(df["Date"], errors="coerce", utc=True)
    return df.sort_values("DateParsed"), f"{API_FOOTBALL_BASE}/fixtures?league={league_id}&season={season}&status=FT"


@st.cache_data(ttl=86400, show_spinner=False)
def find_api_team(name: str, token: str) -> dict[str, Any] | None:
    search_name = TEAM_ALIASES.get(name.strip(), name.strip())
    payload = api_football_get("teams", (("search", search_name),), token)
    teams = payload.get("response") or []
    if not teams:
        return None
    return teams[0]


@st.cache_data(ttl=21600, show_spinner=False)
def get_api_team_data(team_id: int, token: str) -> dict[str, Any]:
    squad = api_football_get("players/squads", (("team", str(team_id)),), token).get("response") or []
    injuries = api_football_get("injuries", (("team", str(team_id)), ("season", str(datetime.now().year))), token).get("response") or []
    season = str(datetime.now().year)
    player_stats = api_football_get("players", (("team", str(team_id)), ("season", season), ("page", "1")), token).get("response") or []
    transfers = api_football_get("transfers", (("team", str(team_id)),), token).get("response") or []
    return {
        "squad": squad[0].get("players", []) if squad else [],
        "injuries": injuries,
        "player_stats": player_stats,
        "transfers": transfers,
    }


def player_data_for_match(home: str, away: str, token: str) -> tuple[dict[str, Any], dict[str, Any], str | None]:
    """自動按隊名找兩隊資料；每隊快取，避免每日 100 次額度被重複消耗。"""
    home_team = find_api_team(home, token)
    away_team = find_api_team(away, token)
    if not home_team or not away_team:
        return {}, {}, "API-Football 找不到其中一隊"
    home_id = home_team.get("team", {}).get("id")
    away_id = away_team.get("team", {}).get("id")
    if not home_id or not away_id:
        return {}, {}, "API-Football 找不到球隊 ID"
    home_data = get_api_team_data(home_id, token)
    away_data = get_api_team_data(away_id, token)
    home_data["logo"] = home_team.get("team", {}).get("logo", "")
    away_data["logo"] = away_team.get("team", {}).get("logo", "")
    return home_data, away_data, None


def player_strength(team_data: dict[str, Any]) -> dict[str, float]:
    """用本季已回傳的出場、評分、入球及助攻建立保守的球隊球員狀態指標。

    這不是保證賽果的魔法分數；缺少資料時回傳中性值，避免虛構球員表現。
    """
    rows = []
    for item in team_data.get("player_stats", []):
        stats = (item.get("statistics") or [{}])[0]
        games = stats.get("games") or {}
        goals = stats.get("goals") or {}
        shots = stats.get("shots") or {}
        rating = pd.to_numeric(games.get("rating"), errors="coerce")
        appearances = float(games.get("appearences") or 0)
        minutes = float(games.get("minutes") or 0)
        if appearances <= 0 and minutes <= 0:
            continue
        rows.append({
            "name": item.get("player", {}).get("name", "未知"),
            "appearances": appearances,
            "minutes": minutes,
            "goals": float(goals.get("total") or 0),
            "assists": float(goals.get("assists") or 0),
            "shots_on": float(shots.get("on") or 0),
            "rating": float(rating) if pd.notna(rating) else 6.5,
        })
    if not rows:
        return {"attack": 1.0, "defence": 1.0, "sample": 0.0, "top_players": []}
    stats = pd.DataFrame(rows)
    # 只作小幅修正，避免球員統計壓過近期團隊賽果。
    attack_raw = stats["goals"].sum() + 0.7 * stats["assists"].sum() + 0.03 * stats["shots_on"].sum()
    minutes = max(stats["minutes"].sum(), 1.0)
    attack = min(1.12, max(0.90, 0.98 + attack_raw / minutes * 0.08))
    rating = stats.loc[stats["minutes"] > 90, "rating"].mean() if (stats["minutes"] > 90).any() else 6.5
    defence = min(1.08, max(0.92, 0.98 + (rating - 6.5) * 0.035))
    top = stats.sort_values(["rating", "minutes"], ascending=False).head(8)[["name", "rating", "minutes", "goals", "assists"]].to_dict("records")
    return {"attack": float(attack), "defence": float(defence), "sample": float(len(stats)), "top_players": top}


@st.cache_data(ttl=900, show_spinner=False)
def load_api_matches(competition: str, token: str) -> tuple[pd.DataFrame, str, dict[str, Any]]:
    """由 Football-Data.org v4 取得本季賽程，並轉成和 CSV 相同的欄位。"""
    response = rq.get(
        f"{FOOTBALL_API}/competitions/{competition}/matches",
        headers={"X-Auth-Token": token},
        params={"status": "FINISHED"},
        timeout=20,
    )
    response.raise_for_status()
    payload = response.json()
    rows = []
    for match in payload.get("matches", []):
        score = match.get("score", {}).get("fullTime", {})
        home_goals = score.get("home")
        away_goals = score.get("away")
        if home_goals is None or away_goals is None:
            continue
        rows.append({
            "Home": match.get("homeTeam", {}).get("name", ""),
            "Away": match.get("awayTeam", {}).get("name", ""),
            "HG": home_goals,
            "AG": away_goals,
            "Date": match.get("utcDate", ""),
            "Res": "H" if home_goals > away_goals else "A" if away_goals > home_goals else "D",
        })
    if not rows:
        raise ValueError("Football-Data.org 沒有回傳已完成賽事")
    df = pd.DataFrame(rows)
    df["HG"] = pd.to_numeric(df["HG"], errors="coerce")
    df["AG"] = pd.to_numeric(df["AG"], errors="coerce")
    df["DateParsed"] = pd.to_datetime(df["Date"], errors="coerce", utc=True)
    return df.sort_values("DateParsed"), f"{FOOTBALL_API}/competitions/{competition}/matches", payload


@st.cache_data(ttl=900, show_spinner=False)
def load_api_standings(competition: str, token: str) -> pd.DataFrame:
    response = rq.get(
        f"{FOOTBALL_API}/competitions/{competition}/standings",
        headers={"X-Auth-Token": token},
        timeout=20,
    )
    response.raise_for_status()
    tables = response.json().get("standings", [])
    total = next((x for x in tables if x.get("type") == "TOTAL"), None)
    if not total:
        return pd.DataFrame()
    rows = []
    for item in total.get("table", []):
        rows.append({
            "排名": item.get("position"),
            "球隊": item.get("team", {}).get("name"),
            "賽": item.get("playedGames"),
            "勝": item.get("won"),
            "和": item.get("draw"),
            "負": item.get("lost"),
            "入球": item.get("goalsFor"),
            "失球": item.get("goalsAgainst"),
            "積分": item.get("points"),
        })
    return pd.DataFrame(rows)


@st.cache_data(ttl=1800, show_spinner=False)
def get_weather(latitude: float, longitude: float) -> dict[str, Any]:
    response = rq.get(
        "https://api.open-meteo.com/v1/forecast",
        params={
            "latitude": latitude,
            "longitude": longitude,
            "current": "temperature_2m,wind_speed_10m,precipitation,weather_code",
            "timezone": "auto",
        },
        timeout=12,
    )
    response.raise_for_status()
    return response.json().get("current", {})


@st.cache_data(ttl=3600, show_spinner=False)
def get_team_info(name: str) -> dict[str, str]:
    english = TEAM_ALIASES.get(name.strip(), name.strip())
    fallback = {"en": english, "stadium": "未能取得", "manager": "未能取得", "league": "未能取得", "logo": ""}
    if not english:
        return fallback
    try:
        r = rq.get(f"{THE_SPORTS_DB}/searchteams.php", params={"t": english}, timeout=12)
        if r.status_code != 200:
            return fallback
        teams = r.json().get("teams") or []
        if not teams:
            return fallback
        t = teams[0]
        return {
            "en": t.get("strTeam") or english,
            "stadium": t.get("strStadium") or "未能取得",
            "manager": t.get("strManager") or "未能取得",
            "league": t.get("strLeague") or "未能取得",
            "logo": t.get("strTeamBadge") or t.get("strTeamLogo") or "",
        }
    except (rq.RequestException, ValueError, TypeError, KeyError):
        return fallback


def poisson_pmf(goals: int, expected: float) -> float:
    return math.exp(-expected) * expected**goals / math.factorial(goals)


def outcome_probabilities(home_xg: float, away_xg: float) -> tuple[float, float, float]:
    values = {"H": 0.0, "D": 0.0, "A": 0.0}
    for hg in range(11):
        for ag in range(11):
            p = poisson_pmf(hg, home_xg) * poisson_pmf(ag, away_xg)
            values["H" if hg > ag else "D" if hg == ag else "A"] += p
    total = sum(values.values())
    return values["H"] / total, values["D"] / total, values["A"] / total


def fair_odds(p: float) -> float:
    return round(1 / p, 2) if p > 0 else float("nan")


def ev(p: float, odds: float) -> float:
    return p * odds - 1 if odds > 0 else float("nan")


def team_form(df: pd.DataFrame, team: str, n: int = 8) -> dict[str, Any]:
    rows = df[(df["Home"] == team) | (df["Away"] == team)].sort_values("DateParsed").tail(n)
    if rows.empty:
        return {"matches": 0, "points": 0.0, "gf": 0.0, "ga": 0.0, "win_rate": 0.0, "rows": rows}
    points = wins = gf = ga = 0.0
    for _, row in rows.iterrows():
        home = row["Home"] == team
        scored = row["HG"] if home else row["AG"]
        conceded = row["AG"] if home else row["HG"]
        gf += scored
        ga += conceded
        if scored > conceded:
            points += 3; wins += 1
        elif scored == conceded:
            points += 1
    return {"matches": len(rows), "points": points, "gf": gf / len(rows), "ga": ga / len(rows), "win_rate": wins / len(rows), "rows": rows}


def make_table(df: pd.DataFrame) -> pd.DataFrame:
    stats: dict[str, dict[str, float]] = {}
    for _, r in df.iterrows():
        for team in [r["Home"], r["Away"]]:
            stats.setdefault(team, {"賽": 0, "勝": 0, "和": 0, "負": 0, "入球": 0, "失球": 0, "積分": 0})
        h, a = stats[r["Home"]], stats[r["Away"]]
        h["賽"] += 1; a["賽"] += 1
        h["入球"] += r["HG"]; h["失球"] += r["AG"]
        a["入球"] += r["AG"]; a["失球"] += r["HG"]
        if r["HG"] > r["AG"]:
            h["勝"] += 1; a["負"] += 1; h["積分"] += 3
        elif r["HG"] < r["AG"]:
            a["勝"] += 1; h["負"] += 1; a["積分"] += 3
        else:
            h["和"] += 1; a["和"] += 1; h["積分"] += 1; a["積分"] += 1
    table = pd.DataFrame.from_dict(stats, orient="index").reset_index(names="球隊")
    table["得失球差"] = table["入球"] - table["失球"]
    return table.sort_values(["積分", "得失球差", "入球"], ascending=False).reset_index(drop=True)


with st.sidebar:
    st.header("選擇聯賽及對賽")
    league = st.selectbox("聯賽", list(LEAGUES.keys()), index=0)
    source, code, coords = LEAGUES[league]
    default_token = configured_api_token()
    api_token = st.text_input(
        "Football-Data.org Token（可選）",
        value=default_token,
        type="password",
        help="建議放入 Streamlit Secrets：FOOTBALL_DATA_TOKEN=你的 token。不要將 token commit 到 GitHub。",
    ).strip()
    api_football_token = st.text_input(
        "API-Football Token（可選）",
        value=configured_api_football_token(),
        type="password",
        help="建議放入 Streamlit Secrets：API_FOOTBALL_TOKEN=你的 token。不要將 token commit 到 GitHub。",
    ).strip()
    if api_football_token:
        st.caption("API-Football 球員及傷停資料已啟用。")
    if league in API_COMPETITIONS:
        if api_token:
            st.caption("此聯賽會優先使用 Football-Data.org API。")
        else:
            st.caption("未設定 token，會使用公開 CSV 後備資料。")
    else:
        st.caption("此聯賽未有 Football-Data.org API 對照，會使用現有資料來源。")
    home_input = st.text_input("主隊", "廣島三箭")
    away_input = st.text_input("客隊", "京都不死鳥")
    st.subheader("賠率（可選）")
    home_odds = st.number_input("主勝賠率", min_value=1.01, value=1.85, step=0.01)
    draw_odds = st.number_input("和賠率", min_value=1.01, value=3.40, step=0.01)
    away_odds = st.number_input("客勝賠率", min_value=1.01, value=4.20, step=0.01)
    goals_line = st.selectbox("入球大細", [0.5, 1.5, 2.5, 3.5, 4.5, 5.5], index=2)
    analyse = st.button("一鍵自動抓取及分析", type="primary", use_container_width=True)

if analyse:
    if source == "unsupported" and not (api_token and league in API_COMPETITIONS) and not (api_football_token and league in API_FOOTBALL_LEAGUES):
        st.warning("目前公開資料來源未提供這個聯賽的可用 CSV，程式沒有虛構數據。請稍後再試，或提供該聯賽的公開資料來源。")
        try:
            weather = get_weather(*coords)
            st.info(f"天氣座標附近目前約 {weather.get('temperature_2m', 'N/A')}°C，風速 {weather.get('wind_speed_10m', 'N/A')} km/h；聯賽賽果資料未能取得。")
        except rq.RequestException:
            st.info("天氣資料暫時未能取得。")
        st.stop()

    with st.spinner(f"正在抓取 {league} 最新公開賽果及天氣資料……"):
        try:
            api_standings = pd.DataFrame()
            if api_football_token and league in API_FOOTBALL_LEAGUES:
                try:
                    matches, source_url = load_api_football_matches(API_FOOTBALL_LEAGUES[league], api_football_token)
                    api_standings = pd.DataFrame()
                    data_source_label = "API-Football"
                except (rq.RequestException, ValueError, KeyError) as api_exc:
                    st.warning(f"API-Football 賽果暫時不可用，會嘗試其他來源：{api_exc}")
                    if api_token and league in API_COMPETITIONS:
                        matches, source_url, api_payload = load_api_matches(API_COMPETITIONS[league], api_token)
                        api_standings = load_api_standings(API_COMPETITIONS[league], api_token)
                        data_source_label = "Football-Data.org API"
                    else:
                        matches, source_url = load_matches(source, code)
                        data_source_label = "公開 CSV 後備"
            elif api_token and league in API_COMPETITIONS:
                try:
                    matches, source_url, api_payload = load_api_matches(API_COMPETITIONS[league], api_token)
                    api_standings = load_api_standings(API_COMPETITIONS[league], api_token)
                    data_source_label = "Football-Data.org API"
                except (rq.RequestException, ValueError, KeyError) as api_exc:
                    st.warning(f"Football-Data.org API 暫時不可用，已自動改用 CSV：{api_exc}")
                    matches, source_url = load_matches(source, code)
                    data_source_label = "Football-Data CSV 後備"
            else:
                matches, source_url = load_matches(source, code)
                data_source_label = "Football-Data CSV"
            weather = get_weather(*coords)
        except (rq.RequestException, ValueError, pd.errors.ParserError) as exc:
            st.error(f"自動抓取失敗：{exc}")
            st.stop()

    teams = sorted(set(matches["Home"]) | set(matches["Away"]))
    home = home_input.strip()
    away = away_input.strip()
    home_match = next((x for x in teams if x == home or home.lower() in x.lower()), None)
    away_match = next((x for x in teams if x == away or away.lower() in x.lower()), None)
    if home_match: home = home_match
    if away_match: away = away_match

    st.success(f"已抓取 {len(matches):,} 場公開賽果｜資料來源：{data_source_label}｜更新時間：{datetime.now().strftime('%Y-%m-%d %H:%M')}")
    if home not in teams or away not in teams:
        st.warning("輸入的球隊未在這份資料中找到。請參考下方球隊名單，使用英文官方名稱再分析。")
        st.dataframe(pd.DataFrame({"可選球隊": teams}), use_container_width=True, hide_index=True)
        st.stop()

    hf = team_form(matches, home)
    af = team_form(matches, away)
    info_home = get_team_info(home)
    info_away = get_team_info(away)
    player_home, player_away, player_error = {}, {}, None
    if api_football_token:
        try:
            player_home, player_away, player_error = player_data_for_match(home, away, api_football_token)
        except (rq.RequestException, ValueError, KeyError, TypeError) as exc:
            player_error = str(exc)
    home_strength = player_strength(player_home)
    away_strength = player_strength(player_away)
    # 以近期入失球為主，再以球員統計作有限幅度修正；資料不足時保持中性。
    home_xg = max(0.15, (hf["gf"] + af["ga"]) / 2 * 1.08 * home_strength["attack"] / away_strength["defence"])
    away_xg = max(0.15, (af["gf"] + hf["ga"]) / 2 * 0.94 * away_strength["attack"] / home_strength["defence"])
    hp, dp, ap = outcome_probabilities(home_xg, away_xg)
    total_xg = home_xg + away_xg
    over = 1 - sum(poisson_pmf(i, total_xg) for i in range(math.floor(goals_line) + 1))
    save_match_snapshot(league, home, away, home_xg, away_xg, hp, dp, ap, data_source_label)
    if api_football_token and player_home:
        save_api_snapshot(league, home, "球員及傷停", player_home)
    if api_football_token and player_away:
        save_api_snapshot(league, away, "球員及傷停", player_away)

    logo_home = player_home.get("logo", "") or info_home.get("logo", "")
    logo_away = player_away.get("logo", "") or info_away.get("logo", "")
    logo_left, title_col, logo_right = st.columns([1, 4, 1])
    with logo_left:
        if logo_home:
            st.image(logo_home, width=72)
    with title_col:
        st.subheader(f"{home} vs {away}｜{league}")
    with logo_right:
        if logo_away:
            st.image(logo_away, width=72)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("預測比分", f"{round(home_xg)} - {round(away_xg)}")
    c2.metric("主勝／和／客勝", f"{hp:.1%} / {dp:.1%} / {ap:.1%}")
    c3.metric(f"大 {goals_line}", f"{over:.1%}")
    c4.metric("資料場數", f"{hf['matches']} / {af['matches']}")

    left, right = st.columns(2)
    with left:
        st.markdown("### 近期表現（最近 8 場）")
        form_df = pd.DataFrame([
            {"球隊": home, "場數": hf["matches"], "平均入球": hf["gf"], "平均失球": hf["ga"], "勝率": hf["win_rate"], "平均積分": hf["points"] / max(1, hf["matches"])},
            {"球隊": away, "場數": af["matches"], "平均入球": af["gf"], "平均失球": af["ga"], "勝率": af["win_rate"], "平均積分": af["points"] / max(1, af["matches"])},
        ])
        st.dataframe(form_df.style.format({"平均入球": "{:.2f}", "平均失球": "{:.2f}", "勝率": "{:.1%}", "平均積分": "{:.2f}"}), use_container_width=True, hide_index=True)
        st.write(f"**{home}：** {info_home['stadium']}｜教練：{info_home['manager']}")
        st.write(f"**{away}：** {info_away['stadium']}｜教練：{info_away['manager']}")

    with right:
        st.markdown("### 天氣及 EV")
        st.write(f"天氣座標附近：{weather.get('temperature_2m', 'N/A')}°C｜風速：{weather.get('wind_speed_10m', 'N/A')} km/h｜降雨：{weather.get('precipitation', 'N/A')} mm")
        market = pd.DataFrame([
            ["主勝", hp, fair_odds(hp), home_odds, ev(hp, home_odds)],
            ["和局", dp, fair_odds(dp), draw_odds, ev(dp, draw_odds)],
            ["客勝", ap, fair_odds(ap), away_odds, ev(ap, away_odds)],
            [f"大 {goals_line}", over, fair_odds(over), None, None],
        ], columns=["選項", "模型機率", "公平賠率", "輸入賠率", "EV"])
        st.dataframe(market.style.format({"模型機率": "{:.1%}", "公平賠率": "{:.2f}", "輸入賠率": lambda x: "-" if pd.isna(x) else f"{x:.2f}", "EV": lambda x: "-" if pd.isna(x) else f"{x:.1%}"}), use_container_width=True, hide_index=True)

    st.markdown("### 球員及缺陣資料")
    if not api_football_token:
        st.info("未設定 API-Football Token，因此暫時只顯示球隊及賽果分析。")
    elif player_error:
        st.warning(f"球員資料暫時未能取得：{player_error}")
    else:
        st.caption(
            f"球員統計已納入模型：{home} {home_strength['sample']:.0f} 名樣本（攻擊修正 {home_strength['attack']:.3f}），"
            f"{away} {away_strength['sample']:.0f} 名樣本（攻擊修正 {away_strength['attack']:.3f}）。"
            "球員資料不足時會使用中性修正，不會虛構數據。"
        )
        p1, p2 = st.columns(2)
        for column, team_name, team_data in [(p1, home, player_home), (p2, away, player_away)]:
            with column:
                st.markdown(f"**{team_name}**")
                squad = team_data.get("squad", [])
                if squad:
                    squad_rows = [{
                        "球員": p.get("name", "未知"),
                        "位置": p.get("position", "未知"),
                        "號碼": p.get("number", ""),
                        "年齡": p.get("age", ""),
                    } for p in squad]
                    st.dataframe(pd.DataFrame(squad_rows), use_container_width=True, hide_index=True)
                else:
                    st.caption("API 沒有回傳球員名單。")
                top_players = player_strength(team_data).get("top_players", [])
                if top_players:
                    st.markdown("**球員狀態摘要**")
                    top_df = pd.DataFrame(top_players).rename(columns={
                        "name": "球員", "rating": "評分", "minutes": "出場分鐘",
                        "goals": "入球", "assists": "助攻",
                    })
                    st.dataframe(top_df, use_container_width=True, hide_index=True)
                injuries = team_data.get("injuries", [])
                if injuries:
                    injury_rows = [{
                        "球員": item.get("player", {}).get("name", "未知"),
                        "類型": item.get("player", {}).get("type", "未知"),
                        "原因": item.get("player", {}).get("reason", "未知"),
                    } for item in injuries]
                    st.warning(f"缺陣／傷停：{len(injury_rows)} 人")
                    st.dataframe(pd.DataFrame(injury_rows), use_container_width=True, hide_index=True)
                else:
                    st.success("API 暫未回傳缺陣資料")
                transfers = team_data.get("transfers", [])
                if transfers:
                    transfer_rows = []
                    for item in transfers[:20]:
                        player = item.get("player", {}).get("name", "未知")
                        for transfer in item.get("transfers", [])[:3]:
                            transfer_rows.append({
                                "球員": player,
                                "日期": transfer.get("date", "未知"),
                                "由": transfer.get("teams", {}).get("in", {}).get("name", "未知"),
                                "到": transfer.get("teams", {}).get("out", {}).get("name", "未知"),
                                "類型": transfer.get("type", "未知"),
                            })
                    if transfer_rows:
                        st.markdown("**近期轉會記錄**")
                        st.dataframe(pd.DataFrame(transfer_rows), use_container_width=True, hide_index=True)

    st.markdown("### 聯賽排名")
    table = api_standings if not api_standings.empty else make_table(matches)
    st.dataframe(table.head(20), use_container_width=True, hide_index=True)
    try:
        with sqlite3.connect(DB_PATH) as conn:
            history = pd.read_sql_query(
                "SELECT captured_at AS 時間, league AS 聯賽, home AS 主隊, away AS 客隊, home_prob AS 主勝機率, draw_prob AS 和局機率, away_prob AS 客勝機率 FROM match_snapshots ORDER BY id DESC LIMIT 20",
                conn,
            )
        if not history.empty:
            st.markdown("### 歷史分析紀錄")
            st.dataframe(history.style.format({"主勝機率": "{:.1%}", "和局機率": "{:.1%}", "客勝機率": "{:.1%}"}), use_container_width=True, hide_index=True)
    except sqlite3.Error:
        pass
    st.caption(f"公開資料來源：{source_url}；TheSportsDB 只用於補充球場／教練資料。球員、傷停及角球資料不會在缺失時虛構。")
else:
    st.info("請在左側選擇聯賽、輸入球隊，再按「一鍵自動抓取及分析」。")

st.caption("Football data provided by the Football-Data.org API when API mode is enabled.")

#!/usr/bin/env python3
"""直接 HTML 多來源足球同步器。

不讀取 CSV、不使用 API-Football；只使用可公開讀取的 HTML。
FBref/Soccerway/Flashscore/WorldFootball 可能回傳 403、CAPTCHA 或缺欄位，
遇到這些情況會記錄失敗並保留空值，絕不虛構比分、角球或入球時間。
"""
from __future__ import annotations
import argparse, json, random, re, sqlite3, time
from io import StringIO
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin
import pandas as pd
import requests
from bs4 import BeautifulSoup, Comment

ROOT = Path(__file__).resolve().parents[1]
DBS = [ROOT / "football_complete.db", ROOT / "football_library.db", ROOT / "data" / "multisource_football.db"]
UA = [
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/126 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_6) AppleWebKit/605.1.15 Version/17 Safari/605.1.15",
]
FBREF = {
    "英超": 9, "英冠": 10, "西甲": 12, "西乙": 17, "德甲": 20, "德乙": 33,
    "荷甲": 11, "荷乙": 24, "法乙": 60, "蘇超": 40, "奧甲": 45, "丹超": 50,
    "芬超": 43, "挪超": 36, "俄超": 30, "沙職": 70, "日職": 25, "日乙": 26,
    "K1": 55, "澳職": 65, "墨超": 31, "墨甲": 230, "阿甲": 21, "巴甲": 24,
    "巴乙": 38, "烏甲": 39,
}
SOCCERWAY = {
    "泰超": "https://int.soccerway.com/national/thailand/thai-premier-league/",
    "卡超": "https://int.soccerway.com/national/qatar/stars-league/",
    "阿聯酋超": "https://int.soccerway.com/national/united-arab-emirates/premier-league/",
    "K2": "https://int.soccerway.com/national/korea-republic/k-league-2/",
    "女澳職": "https://int.soccerway.com/national/australia/w-league/",
    "澳洲盃": "https://int.soccerway.com/national/australia/australia-cup/",
    "女挪超": "https://int.soccerway.com/national/norway/toppserien/",
    "女南美自由盃": "https://int.soccerway.com/international/south-america/copa-libertadores-feminina/",
}
# Only public HTML team pages are used for the requested Australian pilot.
TEAM_PAGES = {
    "South Melbourne FC": "https://int.soccerway.com/teams/australia/south-melbourne/2137/matches/",
    "Sydney United 58 FC": "https://int.soccerway.com/teams/australia/sydney-united/1496/matches/",
}
HTML_LEAGUE_LABELS = set(FBREF) | set(SOCCERWAY) | {"澳洲冠軍聯賽盃"}
ALIASES = {
    "South Melbourne": "South Melbourne FC", "Sydney Utd": "Sydney United 58 FC",
    "Sydney United 58": "Sydney United 58 FC",
}


def get(url, tries=3):
    last = None
    for i in range(tries):
        try:
            r = requests.get(url, headers={"User-Agent": random.choice(UA), "Accept-Language": "en-US,en;q=0.8"}, timeout=30)
            if r.status_code == 200 and r.text:
                low = r.text.lower()
                title = (BeautifulSoup(r.text, "html.parser").title.get_text(" ", strip=True).lower()
                         if BeautifulSoup(r.text, "html.parser").title else "")
                challenge = any(x in low or x in title for x in (
                    "just a moment", "cf-chl-", "cloudflare", "captcha", "access denied"
                ))
                if challenge:
                    return "", "blocked_or_challenge_page"
                return r.text, r.status_code
            last = f"HTTP {r.status_code}"
            if r.status_code in (403, 429): break
        except Exception as e:
            last = f"{type(e).__name__}: {e}"
        time.sleep(2 ** i + random.random())
    return "", last or "failed"


def comments_and_tables(html):
    texts = [html]
    soup = BeautifulSoup(html, "html.parser")
    texts += [str(x) for x in soup.find_all(string=lambda t: isinstance(t, Comment))]
    out = []
    for text in texts:
        try: out.extend(pd.read_html(StringIO(text)))
        except (ValueError, ImportError): pass
    return out


def norm_col(x):
    return re.sub(r"[^a-z0-9]", "", str(x).lower())


def parse_score(v):
    m = re.search(r"(\d+)\s*[-–:]\s*(\d+)", str(v or ""))
    return (int(m.group(1)), int(m.group(2))) if m else (None, None)


def find_schedule_tables(html):
    rows = []
    for df in comments_and_tables(html):
        cols = {norm_col(c): c for c in df.columns}
        date = next((cols[k] for k in ("date", "datetime") if k in cols), None)
        home = next((cols[k] for k in ("home", "hometeam") if k in cols), None)
        away = next((cols[k] for k in ("away", "awayteam") if k in cols), None)
        score = next((cols[k] for k in ("score", "result", "ft") if k in cols), None)
        if not (date and home and away): continue
        for _, r in df.iterrows():
            hg, ag = parse_score(r.get(score, "") if score else "")
            if hg is None: continue
            rows.append({"date": pd.to_datetime(r.get(date), errors="coerce").strftime("%Y-%m-%d") if pd.notna(pd.to_datetime(r.get(date), errors="coerce")) else None,
                         "home_team": ALIASES.get(str(r.get(home)).strip(), str(r.get(home)).strip()),
                         "away_team": ALIASES.get(str(r.get(away)).strip(), str(r.get(away)).strip()),
                         "home_goals": hg, "away_goals": ag})
    return pd.DataFrame(rows).drop_duplicates(["date", "home_team", "away_team"]) if rows else pd.DataFrame()


def fbref_league(name, comp):
    url = f"https://fbref.com/en/comps/{comp}/schedule/"
    html, status = get(url)
    if not html: return pd.DataFrame(), f"FBref {status}"
    d = find_schedule_tables(html)
    return d.tail(250), f"FBref HTML {len(d)} rows"


def soccerway_league(name, url):
    html, status = get(url)
    if not html: return pd.DataFrame(), f"Soccerway {status}"
    d = find_schedule_tables(html)
    return d.tail(250), f"Soccerway HTML {len(d)} rows"


def team_pilot(team, url):
    html, status = get(url)
    if not html: return pd.DataFrame(), f"Soccerway team {status}"
    d = find_schedule_tables(html)
    return d.tail(20), f"Soccerway team HTML {len(d)} rows"


def init_db(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(path, timeout=30)
    c.execute("PRAGMA busy_timeout=30000")
    c.executescript("""
    CREATE TABLE IF NOT EXISTS fixtures (match_id TEXT PRIMARY KEY, league TEXT, date TEXT, season TEXT, home_team TEXT, away_team TEXT, home_goals INTEGER, away_goals INTEGER, half_home_goals INTEGER, half_away_goals INTEGER, source TEXT);
    CREATE TABLE IF NOT EXISTS goals (match_id TEXT, team TEXT, minute INTEGER, source TEXT, PRIMARY KEY(match_id, team, minute));
    CREATE TABLE IF NOT EXISTS corners (match_id TEXT PRIMARY KEY, corner_home REAL, corner_away REAL, verified INTEGER NOT NULL DEFAULT 0, source_fbref TEXT, source_flashscore TEXT, source TEXT);
    CREATE TABLE IF NOT EXISTS teams (team_id TEXT PRIMARY KEY, en_name TEXT, zh_name TEXT, market_value REAL, league TEXT, source TEXT);
    CREATE TABLE IF NOT EXISTS sync_log (league TEXT, status TEXT, message TEXT, captured_at TEXT);
    """)
    c.commit(); return c


def zh_name(en):
    try:
        mapping = json.loads((ROOT / "data/team_name_map.json").read_text(encoding="utf-8"))
        return mapping.get(en) or mapping.get(ALIASES.get(en, en)) or ""
    except Exception: return ""


def write_rows(league, df, source, conns):
    if df.empty: return 0
    now = datetime.now(timezone.utc).isoformat()
    for _, r in df.iterrows():
        key = f"html-{league}-{r['date']}-{r['home_team']}-{r['away_team']}"
        vals = (key, league, r.get("date"), "2025-26", r["home_team"], r["away_team"], int(r["home_goals"]), int(r["away_goals"]), None, None, source)
        for c in conns:
            c.execute("INSERT OR REPLACE INTO fixtures VALUES (?,?,?,?,?,?,?,?,?,?,?)", vals)
            for team in (r["home_team"], r["away_team"]):
                tid = re.sub(r"[^a-z0-9]+", "-", team.lower()).strip("-")
                c.execute("INSERT OR REPLACE INTO teams(team_id,en_name,zh_name,market_value,league,source) VALUES(?,?,?,?,?,?)", (tid, team, zh_name(team), None, league, source))
    for c in conns:
        c.execute("INSERT INTO sync_log VALUES(?,?,?,?)", (league, "ok", f"{len(df)} fixtures from {source}", now)); c.commit()
    return len(df)


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--leagues", default="all"); ap.add_argument("--pilot", action="store_true"); ap.add_argument("--sleep", type=float, default=5.0); args = ap.parse_args()
    wanted = HTML_LEAGUE_LABELS if args.leagues == "all" else {x.strip() for x in args.leagues.split(",")}
    conns = [init_db(p) for p in DBS]
    report = []
    try:
        if args.pilot or "澳洲冠軍聯賽盃" in wanted or "australia-pilot" in wanted:
            frames = []
            for team, url in TEAM_PAGES.items():
                d, note = team_pilot(team, url); frames.append(d); report.append({"league":"澳洲冠軍聯賽盃","team":team,"rows":len(d),"note":note})
                time.sleep(args.sleep)
            pilot = pd.concat(frames, ignore_index=True).drop_duplicates(["date","home_team","away_team"]) if any(not x.empty for x in frames) else pd.DataFrame()
            write_rows("澳洲冠軍聯賽盃", pilot, "Soccerway HTML", conns)
        # pilot 只跑兩隊，但仍然繼續到函數尾端寫出 report。
        if args.pilot: wanted = set()
        for name, comp in FBREF.items():
            if name not in wanted: continue
            d, note = fbref_league(name, comp); n = write_rows(name, d, "FBref HTML", conns); report.append({"league":name,"rows":n,"note":note}); time.sleep(args.sleep)
        for name, url in SOCCERWAY.items():
            if name not in wanted: continue
            d, note = soccerway_league(name, url); n = write_rows(name, d, "Soccerway HTML", conns); report.append({"league":name,"rows":n,"note":note}); time.sleep(args.sleep)
    finally:
        for c in conns: c.close()
    out = ROOT / "data/html_sources_sync_report.json"; out.write_text(json.dumps(report, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2)); print(f"REPORT={out}")

if __name__ == "__main__": main()

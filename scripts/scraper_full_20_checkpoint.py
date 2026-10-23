#!/usr/bin/env python3
"""真實資料 checkpoint 爬蟲：每輪最多處理五隊，缺少明確 HT 便記錄失敗。

本腳本不會把 FT 推算成 HT，也不會以 0 填補未知欄位。
"""
from __future__ import annotations

import argparse
import json
import re
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "football_library.db"
AUDIT = ROOT / "data" / "local_completeness_audit.json"
CHECKPOINT = ROOT / "checkpoint.json"
FAILED = ROOT / "failed_teams.log"
LEAGUE_URLS = {"卡塔爾超級聯賽": "https://www.flashscore.com/football/qatar/qsl/results/"}


def ensure_schema(conn):
    cols = {r[1] for r in conn.execute("pragma table_info(matches)")}
    for col in ("ht_home", "ht_away"):
        if col not in cols:
            conn.execute(f"alter table matches add column {col} integer null")
    conn.commit()


def load_targets(limit, league_filter=None):
    audit = json.loads(AUDIT.read_text(encoding="utf-8"))
    rows = []
    for league, teams in audit.get("leagues", {}).items():
        if league_filter and league != league_filter:
            continue
        for item in teams:
            if int(item.get("matches", 0)) < 20:
                rows.append((league, item["team_name"]))
    return rows[:limit]


def parse_score(text):
    m = re.search(r"(?:^|\s)(\d+)\s*[-:]\s*(\d+)(?:\s|$)", text or "")
    return (int(m.group(1)), int(m.group(2))) if m else None


def parse_ht(text):
    text = re.sub(r"\s+", " ", text or "")
    patterns = [r"1ST\s+HALF[^0-9]*(\d+)\s*[-:]\s*(\d+)", r"HT[^0-9]*(\d+)\s*[-:]\s*(\d+)", r"\((\d+)\s*[-:]\s*(\d+)\)"]
    for pat in patterns:
        m = re.search(pat, text, re.I)
        if m:
            return int(m.group(1)), int(m.group(2))
    return None


def team_page_url(page, team_name):
    page.goto("https://www.flashscore.com/search/?q=" + quote(team_name), wait_until="domcontentloaded", timeout=45000)
    page.wait_for_timeout(5000)
    hrefs = page.locator('a[href*="/team/"]').evaluate_all("els => els.map(e => e.href)")
    return next((x.split("/results")[0] + "/results/" for x in hrefs if "/team/" in x), None)


def collect_team(page, league, team_name, max_matches=20):
    url = team_page_url(page, team_name)
    if not url:
        return [], f"team page not found: {team_name}"
    page.goto(url, wait_until="domcontentloaded", timeout=45000)
    page.wait_for_timeout(5000)
    links = page.locator('a[href*="/match/football/"]')
    seen = set(); matches = []
    for i in range(links.count()):
        href = links.nth(i).get_attribute("href") or ""
        mid = re.search(r"/match/football/[^/]+/([^/]+)/", href)
        if not mid or mid.group(1) in seen:
            continue
        seen.add(mid.group(1))
        card = links.nth(i).locator("xpath=..")
        text = card.inner_text()
        ft = parse_score(text)
        if not ft:
            continue
        detail_url = "https://www.flashscore.com/match/football/" + mid.group(1) + "/#/match-summary/match-summary"
        page.goto(detail_url, wait_until="domcontentloaded", timeout=45000)
        page.wait_for_timeout(5000)
        body = page.locator("body").inner_text(timeout=10000)
        ht = parse_ht(body)
        if not ht:
            continue
        # Read visible team names from the detail page; only accept the target team.
        lines = [x.strip() for x in body.splitlines() if x.strip()]
        names = []
        for line in lines:
            if re.fullmatch(r"[A-Za-zÀ-ÿ0-9 .&'()_-]{2,60}", line):
                names.append(line)
        if len(names) < 2:
            continue
        home, away = names[0], names[1]
        date = datetime.now().date().isoformat()
        matches.append((league, "current", home, away, ft[0], ft[1], ht[0], ht[1], date, "Flashscore explicit FT+HT"))
        if len(matches) >= max_matches:
            break
    return matches, None if len(matches) >= max_matches else f"only {len(matches)} explicit HT matches found for {team_name}"


def write_rows(conn, rows):
    for row in rows:
        league, season, home, away, hg, ag, ht_home, ht_away, date, source = row
        stamp = datetime.now(timezone.utc).isoformat()
        existing = conn.execute(
            "SELECT rowid FROM matches WHERE league=? AND home=? AND away=? AND date=? LIMIT 1",
            (league, home, away, date),
        ).fetchone()
        if existing:
            conn.execute(
                "UPDATE matches SET hg=?, ag=?, ht_home=?, ht_away=?, source=?, captured_at=? WHERE rowid=?",
                (hg, ag, ht_home, ht_away, source, stamp, existing[0]),
            )
        else:
            conn.execute(
                "INSERT INTO matches (league,season,home,away,hg,ag,ht_home,ht_away,date,source,captured_at) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                (league, season, home, away, hg, ag, ht_home, ht_away, date, source, stamp),
            )
    conn.commit()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit-teams", type=int, default=5)
    ap.add_argument("--wait-ms", type=int, default=5000)
    ap.add_argument("--league", default=None)
    args = ap.parse_args()
    targets = load_targets(args.limit_teams, args.league)
    report = {"updated_at": datetime.now(timezone.utc).isoformat(), "requested": targets, "completed": [], "failed": []}
    conn = sqlite3.connect(DB, timeout=30)
    conn.execute("pragma busy_timeout=30000")
    ensure_schema(conn)
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise SystemExit("playwright is required") from exc
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page()
        for league, team in targets:
            rows, error = collect_team(page, league, team)
            if len(rows) >= 20:
                write_rows(conn, rows)
                report["completed"].append({"league": league, "team": team, "matches": len(rows)})
            else:
                msg = f"{datetime.now(timezone.utc).isoformat()} | {league} | {team} | {error}\n"
                FAILED.open("a", encoding="utf-8").write(msg)
                report["failed"].append({"league": league, "team": team, "matches": len(rows), "reason": error})
        browser.close()
    conn.close()
    old = json.loads(CHECKPOINT.read_text(encoding="utf-8")) if CHECKPOINT.exists() else {}
    done = int(old.get("done_teams", 0)) + len(report["completed"])
    CHECKPOINT.write_text(json.dumps({"updated_at": report["updated_at"], "done_teams": done, "total_teams": int(old.get("total_teams", 865)), "last_batch": report, "status": "incomplete" if done < int(old.get("total_teams", 865)) else "candidate"}, ensure_ascii=False, indent=2) + "\n")
    (ROOT / "data").mkdir(exist_ok=True)
    (ROOT / "data" / "scraper_checkpoint_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

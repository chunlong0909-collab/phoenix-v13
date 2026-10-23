#!/usr/bin/env python3
"""補充 football_complete.db 的真實半場比分。

只會使用 fixtures.flashscore_match_id 建立 Flashscore 詳情網址。
沒有 match ID、被封鎖、頁面沒有可核實 HT 文本時，保持 NULL，絕不由全場比分推算。
"""
from __future__ import annotations

import argparse
import json
import re
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB = ROOT / "football_complete.db"
REPORT = ROOT / "data" / "flashscore_ht_report.json"
FOCUS_TEAM_PAGES = {
    "South Melbourne FC": "https://www.flashscore.com/team/south-melbourne/6ciKPSEO/results/",
    "Sydney United 58 FC": "https://www.flashscore.com/team/sydney-utd/2RROTa1R/results/",
}


def ensure_columns(conn: sqlite3.Connection) -> None:
    cols = {r[1] for r in conn.execute("PRAGMA table_info(fixtures)")}
    for col in ("ht_home", "ht_away"):
        if col not in cols:
            conn.execute(f"ALTER TABLE fixtures ADD COLUMN {col} INTEGER NULL")
    conn.commit()


def parse_ht(text: str):
    """Parse explicit half-time text such as '(1-0)' or 'HT (1-0)'."""
    if not text:
        return None
    compact = re.sub(r"\s+", " ", text)
    m = re.search(r"\b1ST\s+HALF\b\s*(\d+)\s*[-–:]\s*(\d+)", compact, re.I)
    if m:
        return int(m.group(1)), int(m.group(2))
    m = re.search(r"\(\s*(\d+)\s*[-–:]\s*(\d+)\s*\)", text)
    if not m:
        m = re.search(r"\bHT\b[^0-9]*(\d+)\s*[-–:]\s*(\d+)", text, re.I)
    return (int(m.group(1)), int(m.group(2))) if m else None


def fetch_one(page, match_id: str, wait_ms: int = 6000):
    url = f"https://www.flashscore.com/match/{match_id}/#/match-summary/match-summary"
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=45000)
        page.wait_for_timeout(wait_ms)
        selectors = [
            '[data-testid="wcl-scores-simpleText-01"]',
            '[data-testid*="score"]',
            'div[class*="period"]',
            'div[class*="halfTime"]',
        ]
        texts = []
        for selector in selectors:
            try:
                texts.extend(page.locator(selector).all_inner_texts())
            except Exception:
                pass
        # Also inspect visible body text, but only accept explicit HT-shaped text.
        try:
            texts.append(page.locator("body").inner_text(timeout=5000))
        except Exception:
            pass
        for text in texts:
            parsed = parse_ht(text)
            if parsed:
                return {"status": "updated", "ht_home": parsed[0], "ht_away": parsed[1], "url": url}
        return {"status": "no_explicit_ht", "url": url}
    except Exception as exc:
        return {"status": "error", "error": f"{type(exc).__name__}: {exc}", "url": url}


def select_rows(conn, limit: int | None):
    sql = """SELECT id, flashscore_match_id FROM fixtures
             WHERE flashscore_match_id IS NOT NULL AND TRIM(flashscore_match_id) <> ''
             ORDER BY date DESC, id DESC"""
    if limit:
        sql += f" LIMIT {int(limit)}"
    return conn.execute(sql).fetchall()


def canonical_name(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", (value or "").lower().replace("fc", ""))


def extract_mid(href: str):
    values = parse_qs(urlparse(href).query).get("mid", [])
    return values[0] if values else None


def resolve_focus_ids(conn, page):
    """Read real `mid` values from team result cards and bind by date/team.

    A team page can contain several cards for the same date in the canonical DB.
    Since flashscore_match_id is UNIQUE, only one canonical row receives the ID;
    duplicate rows are reported instead of receiving a fabricated/shared ID.
    """
    result = {"pages": [], "resolved_ids": 0, "duplicate_rows_skipped": 0, "no_fixture_match": 0}
    for team, url in FOCUS_TEAM_PAGES.items():
        team_rows = conn.execute(
            "SELECT id FROM teams WHERE en_name=? OR en_name LIKE ? ORDER BY id LIMIT 1",
            (team, team.replace(" FC", "%")),
        ).fetchall()
        if not team_rows:
            result["pages"].append({"team": team, "status": "team_not_found"})
            continue
        team_id = team_rows[0][0]
        page.goto(url, wait_until="domcontentloaded", timeout=45000)
        page.wait_for_timeout(6000)
        links = page.locator('a[href*="/match/football/"]')
        seen = set(); page_resolved = 0
        for i in range(links.count()):
            href = links.nth(i).get_attribute("href") or ""
            mid = extract_mid(href)
            if not mid or mid in seen or conn.execute(
                "SELECT 1 FROM fixtures WHERE flashscore_match_id=?", (mid,)
            ).fetchone():
                continue
            seen.add(mid)
            text = links.nth(i).locator("xpath=..").inner_text()
            first = text.splitlines()[0].strip() if text.splitlines() else ""
            m = re.search(r"(\d{1,2})\.(\d{1,2})\.", first)
            if not m:
                continue
            date_candidates = [f"2026-{int(m.group(2)):02d}-{int(m.group(1)):02d}",
                               f"2025-{int(m.group(2)):02d}-{int(m.group(1)):02d}"]
            candidates = []
            for date in date_candidates:
                candidates = conn.execute(
                    "SELECT id FROM fixtures WHERE date=? AND (home_id=? OR away_id=?) "
                    "AND flashscore_match_id IS NULL ORDER BY id LIMIT 2",
                    (date, team_id, team_id),
                ).fetchall()
                if candidates:
                    break
            if not candidates:
                # It may already have an ID, or the canonical source has no row.
                continue
            conn.execute("UPDATE fixtures SET flashscore_match_id=? WHERE id=?", (mid, candidates[0][0]))
            page_resolved += 1; result["resolved_ids"] += 1
            if len(candidates) > 1:
                result["duplicate_rows_skipped"] += len(candidates) - 1
        result["pages"].append({"team": team, "url": url, "links": links.count(), "resolved": page_resolved})
    conn.commit()
    return result


def run(db_path: Path, limit: int | None, only_ids=None, wait_ms: int = 6000, resolve_focus: bool = False):
    db_path = Path(db_path)
    conn = sqlite3.connect(str(db_path), timeout=30)
    conn.execute("PRAGMA busy_timeout=30000")
    ensure_columns(conn)
    resolve_report = {"resolved_ids": 0, "duplicate_rows_skipped": 0, "no_fixture_match": 0, "pages": []}
    if resolve_focus:
        try:
            from playwright.sync_api import sync_playwright
        except ImportError as exc:
            conn.close(); raise RuntimeError("需要安裝 playwright 才能讀取 Flashscore 結果列表") from exc
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            resolve_report = resolve_focus_ids(conn, browser.new_page())
            browser.close()

    rows = select_rows(conn, limit)
    if only_ids:
        wanted = {int(x) for x in only_ids}
        rows = [r for r in rows if r[0] in wanted]

    report = {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "database": str(db_path.name), "requested": len(rows),
        "updated": 0, "no_explicit_ht": 0, "errors": 0,
        "missing_match_id": 0, "ht_coverage": None, "results": [],
        "with_id": 0, "id_resolution": resolve_report,
    }

    # Playwright is imported only when actual rows with IDs exist.
    if rows:
        try:
            from playwright.sync_api import sync_playwright
        except ImportError as exc:
            conn.close()
            raise RuntimeError("需要安裝 playwright 才能抓取 Flashscore 半場資料") from exc
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            page = browser.new_page()
            for fixture_id, match_id in rows:
                result = fetch_one(page, str(match_id), wait_ms)
                result.update({"fixture_id": fixture_id, "flashscore_match_id": match_id})
                if result["status"] == "updated":
                    conn.execute("UPDATE fixtures SET ht_home=?, ht_away=? WHERE id=?",
                                 (result["ht_home"], result["ht_away"], fixture_id))
                    report["updated"] += 1
                elif result["status"] == "no_explicit_ht":
                    report["no_explicit_ht"] += 1
                else:
                    report["errors"] += 1
                report["results"].append(result)
                conn.commit()
            browser.close()

    # Explicitly report fixtures that cannot be visited because no source ID exists.
    total_with_scores = conn.execute(
        "SELECT COUNT(*) FROM fixtures WHERE ft_home IS NOT NULL AND ft_away IS NOT NULL").fetchone()[0]
    with_ht = conn.execute("SELECT COUNT(*) FROM fixtures WHERE ht_home IS NOT NULL AND ht_away IS NOT NULL").fetchone()[0]
    total = conn.execute("SELECT COUNT(*) FROM fixtures").fetchone()[0]
    no_id = conn.execute("SELECT COUNT(*) FROM fixtures WHERE flashscore_match_id IS NULL OR TRIM(flashscore_match_id)='' ").fetchone()[0]
    report["missing_match_id"] = no_id
    report["with_id"] = total - no_id
    focus_sql = """SELECT COUNT(*),
        SUM(CASE WHEN f.flashscore_match_id IS NOT NULL THEN 1 ELSE 0 END),
        SUM(CASE WHEN f.ht_home IS NOT NULL AND f.ht_away IS NOT NULL THEN 1 ELSE 0 END)
        FROM fixtures f JOIN teams h ON h.id=f.home_id JOIN teams a ON a.id=f.away_id
        WHERE h.en_name LIKE '%South Melbourne%' OR a.en_name LIKE '%South Melbourne%'
           OR h.en_name LIKE '%Sydney United%' OR a.en_name LIKE '%Sydney United%'"""
    focus_total, focus_ids, focus_ht = conn.execute(focus_sql).fetchone()
    report["focus_fixtures"] = int(focus_total or 0)
    report["focus_with_id"] = int(focus_ids or 0)
    report["focus_with_ht"] = int(focus_ht or 0)
    report["focus_ht_coverage"] = (focus_ht / focus_total) if focus_total else 0.0
    report["total_fixtures"] = total
    report["fixtures_with_scores"] = total_with_scores
    report["with_ht"] = with_ht
    report["ht_coverage"] = (with_ht / total) if total else 0.0
    report["ht_coverage_of_scored"] = (with_ht / total_with_scores) if total_with_scores else 0.0
    report["league_coverage"] = [
        {
            "league_id": league_id,
            "total": total_count,
            "with_ht": ht_count,
            "coverage": (ht_count / total_count) if total_count else 0.0,
        }
        for league_id, total_count, ht_count in conn.execute(
            "SELECT league_id, COUNT(*), SUM(CASE WHEN ht_home IS NOT NULL AND ht_away IS NOT NULL THEN 1 ELSE 0 END) "
            "FROM fixtures GROUP BY league_id ORDER BY league_id"
        ).fetchall()
    ]
    conn.commit(); conn.close()
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default=str(DEFAULT_DB))
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--fixture-id", action="append", dest="fixture_ids")
    ap.add_argument("--wait-ms", type=int, default=6000)
    ap.add_argument("--resolve-focus", action="store_true", help="先由兩隊結果列表頁補入真實 match ID")
    ap.add_argument("--teams", default=None, help="兼容定點測試名稱，例如 south-melbourne,sydney-united-58")
    ap.add_argument("--with-id", action="store_true", help="定點測試別名：先補焦點隊伍的真實 match ID")
    ap.add_argument("--with-ht", action="store_true", help="定點測試別名：抓取已有 match ID 的明確半場比分")
    args = ap.parse_args()
    result = run(Path(args.db), args.limit, args.fixture_ids, args.wait_ms, args.resolve_focus or args.with_id)
    print(json.dumps({k: v for k, v in result.items() if k != "results"}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

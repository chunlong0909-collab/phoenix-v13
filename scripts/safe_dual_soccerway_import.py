from __future__ import annotations
import argparse
import csv
import json
import re
import sqlite3
import sys
import time
from datetime import datetime, timezone
from difflib import SequenceMatcher
from pathlib import Path

from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from database_core import clean_team_name

TEAMS = [
    {"name": "Canberra Croatia", "id": "xfRgXB6e", "league_id": 18872, "league": "澳洲盃", "country": "australia"},
    {"name": "South Melbourne", "id": "6ciKPSE0", "league_id": 18872, "league": "澳洲盃", "country": "australia"},
    {"name": "Inter Turku", "id": "QwkNUoNH", "league_id": 149, "league": "芬超", "country": "finland"},
    {"name": "HJK Helsinki", "id": "nmjJVR7B", "league_id": 149, "league": "芬超", "country": "finland"},
    {"name": "LASK Linz", "id": "MipWYeKQ", "league_id": 184, "league": "奧地利盃", "country": "austria"},
    {"name": "SV Ried", "id": "6c17idcf", "league_id": 184, "league": "奧地利盃", "country": "austria"},
]
RAW_DIR = ROOT / "data" / "raw" / "soccerway_safe_probe_2026-10-29"
REPORT = ROOT / "safe_soccerway_import_report_2026-10-29.json"


def candidate_urls(team):
    tid, country = team["id"], team["country"]
    return [
        f"https://int.soccerway.com/teams/{country}/{tid}/results/",
        f"https://www.soccerway.com/teams/{country}/{tid}/results/",
        f"https://int.soccerway.com/teams/-/teams/{tid}/",
    ]


def normalize_date(raw):
    raw = re.sub(r"\s+", " ", str(raw or "").strip())
    for fmt in ("%d/%m/%y", "%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y"):
        try:
            return datetime.strptime(raw, fmt).strftime("%Y-%m-%d")
        except ValueError:
            pass
    # Soccerway may include a time after the date.
    m = re.search(r"(\d{1,2}/\d{1,2}/\d{2,4}|\d{4}-\d{2}-\d{2})", raw)
    if m:
        return normalize_date(m.group(1))
    return None


def parse_score(raw):
    s = str(raw or "").strip().upper()
    if any(x in s for x in ("POSTP", "CANC", "TBD", "AWARDED", "PEN.")):
        return None
    m = re.search(r"(?:^|\s)(\d+)\s*[-:]\s*(\d+)(?:\s|$)", s)
    return (int(m.group(1)), int(m.group(2))) if m else None


def parse_page(html, team, source_url):
    soup = BeautifulSoup(html, "html.parser")
    tables = soup.select("table.matches, table")
    rows = []
    for table in tables:
        for tr in table.select("tbody tr, tr"):
            cells = [re.sub(r"\s+", " ", x.get_text(" ", strip=True)) for x in tr.select("td, th")]
            if len(cells) < 4:
                continue
            date = normalize_date(cells[0]) or (normalize_date(cells[1]) if len(cells) > 1 else None)
            score_idx = next((i for i, c in enumerate(cells) if parse_score(c) is not None), None)
            if not date or score_idx is None or score_idx == 0 or score_idx + 1 >= len(cells):
                continue
            score = parse_score(cells[score_idx])
            # Soccerway layouts generally place home/score/away together. Reject
            # obvious labels to avoid writing navigation or league-table rows.
            home, away = cells[score_idx - 1], cells[score_idx + 1]
            if not home or not away or home.lower() in {"home", "team"} or away.lower() in {"away", "team"}:
                continue
            rows.append({
                "league_id": team["league_id"], "league": team["league"], "date": date,
                "home_name": home, "away_name": away,
                "ft_home": score[0], "ft_away": score[1],
                "ht_home": None, "ht_away": None,
                "corners_home": None, "corners_away": None,
                "corners_verified": 0, "source_url": source_url,
                "source": "Soccerway public results (not independently verified)",
            })
    # Natural dedupe, preserving first occurrence.
    unique, seen = [], set()
    for row in rows:
        key = (row["league_id"], row["date"], clean_team_name(row["home_name"]), clean_team_name(row["away_name"]))
        if key not in seen:
            seen.add(key); unique.append(row)
    return unique


def fetch_team(page, team):
    last = ""
    for url in candidate_urls(team):
        try:
            response = page.goto(url, wait_until="domcontentloaded", timeout=40000)
            page.wait_for_timeout(3500)
            html = page.content()
            status = response.status if response else None
            rows = parse_page(html, team, page.url)
            if rows:
                return {"status": "ok", "url": page.url, "http_status": status, "rows": rows}
            last = f"{url} status={status} rows=0"
        except Exception as exc:
            last = f"{url}: {exc}"
    return {"status": "failed", "error": last, "rows": []}


def existing_keys_complete(conn):
    rows = conn.execute("select f.league_id,f.date,t1.en_name,t2.en_name from fixtures f join teams t1 on t1.id=f.home_id join teams t2 on t2.id=f.away_id").fetchall()
    return {(int(lid), date, clean_team_name(h), clean_team_name(a)) for lid, date, h, a in rows}


def write_complete(rows):
    from database_core import init_ultimate_db, save_match_data
    conn = init_ultimate_db(ROOT / "football_complete.db")
    before = existing_keys_complete(conn)
    inserted = 0
    for row in rows:
        key = (row["league_id"], row["date"], clean_team_name(row["home_name"]), clean_team_name(row["away_name"]))
        if key in before:
            continue
        save_match_data(conn, row)
        before.add(key); inserted += 1
    conn.close()
    return inserted


def write_library(rows):
    import contextlib, io
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        import app
    import pandas as pd
    frame = pd.DataFrame([{
        "Date": r["date"], "Home": r["home_name"], "Away": r["away_name"],
        "HG": r["ft_home"], "AG": r["ft_away"], "HC": r["corners_home"], "AC": r["corners_away"],
        "HT_HG": r["ht_home"], "HT_AG": r["ht_away"], "league": r["league"], "source": r["source"],
    } for r in rows])
    if frame.empty:
        return 0
    source_label = str(rows[0].get("source", "Soccerway public results (not independently verified)"))
    norm = app.clean_matches(frame, source_label, frame.iloc[0]["league"], datetime.now().year)
    # clean_matches intentionally keeps only the common score fields.
    norm["HT_HG"] = frame["HT_HG"].to_numpy(); norm["HT_AG"] = frame["HT_AG"].to_numpy()
    app.save_matches(norm)
    return len(norm)


def import_fixtures_from_csv(csv_path, commit=False, expected_league_id=98, expected_league="日職J1", source_label="使用者提供CSV（未獨立核實）"):
    """Validate a supplied FT CSV, then optionally write both database stores."""
    path = Path(csv_path)
    if not path.is_absolute():
        path = ROOT / path
    required = {"date", "home", "away", "ft_home", "ft_away", "league_id"}
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        if set(reader.fieldnames or []) != required:
            raise ValueError(f"CSV欄位必須正好是 {sorted(required)}")
        raw = list(reader)
    rows, seen = [], set()
    for n, r in enumerate(raw, 2):
        if str(r["league_id"]).strip() != str(expected_league_id):
            raise ValueError(f"第{n}行league_id不是{expected_league_id}")
        date = normalize_date(r["date"])
        if not date:
            raise ValueError(f"第{n}行日期無效")
        home, away = str(r["home"]).strip(), str(r["away"]).strip()
        if not home or not away or clean_team_name(home) == clean_team_name(away):
            raise ValueError(f"第{n}行隊名無效或相同")
        try:
            hg, ag = int(r["ft_home"]), int(r["ft_away"])
        except ValueError as exc:
            raise ValueError(f"第{n}行FT比分無效") from exc
        if hg < 0 or ag < 0:
            raise ValueError(f"第{n}行FT比分不可為負數")
        key = (expected_league_id, date, clean_team_name(home), clean_team_name(away))
        if key in seen:
            raise ValueError(f"CSV內有重複自然鍵：{key}")
        seen.add(key)
        rows.append({
            "league_id": expected_league_id, "league": expected_league, "date": date,
            "home_name": home, "away_name": away, "ft_home": hg, "ft_away": ag,
            "ht_home": None, "ht_away": None, "corners_home": None, "corners_away": None,
            "corners_verified": 0, "source_url": str(path.relative_to(ROOT)),
            "source": source_label,
        })
    conn = sqlite3.connect(ROOT / "football_complete.db")
    try:
        existing = existing_keys_complete(conn)
    finally:
        conn.close()
    existing_rows = sum((expected_league_id, r["date"], clean_team_name(r["home_name"]), clean_team_name(r["away_name"])) in existing for r in rows)
    result = {"csv": str(path.relative_to(ROOT)), "league_id": expected_league_id,
              "league": expected_league, "rows_read": len(rows),
              "existing_natural_keys": existing_rows, "new_natural_keys": len(rows) - existing_rows,
              "corners_verified": 0, "passed": True, "committed": False}
    if commit:
        result["complete_new"] = write_complete(rows)
        result["library_rows_written"] = write_library(rows)
        # No verified corners were supplied, so update provenance explicitly
        # for these exact seed keys rather than mislabeling them as Soccerway.
        conn = sqlite3.connect(ROOT / "football_library.db")
        conn.execute(
            "UPDATE matches SET source=? WHERE league=? AND date=? AND source LIKE ?",
            (rows[0]["source"], rows[0]["league"], rows[0]["date"], "Soccerway public results%"),
        )
        conn.commit(); conn.close()
        result["committed"] = True
    return result


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--commit", action="store_true", help="only write after all six teams pass")
    args = ap.parse_args()
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    results, all_rows = [], []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(user_agent="Mozilla/5.0 Chrome/120.0.0.0", viewport={"width": 1920, "height": 1080})
        page = context.new_page()
        for i, team in enumerate(TEAMS):
            result = fetch_team(page, team)
            rows = result.pop("rows", [])
            result.update({"team": team["name"], "league_id": team["league_id"], "row_count": len(rows)})
            results.append(result); all_rows.extend(rows)
            time.sleep(2 if i == len(TEAMS)-1 else 3)
        browser.close()
    # Hard gate: no partial commit. A page must yield at least one valid FT row.
    passed = all(x["status"] == "ok" and x["row_count"] > 0 for x in results)
    duplicate_keys = []
    seen = set()
    for r in all_rows:
        key = (r["league_id"], r["date"], clean_team_name(r["home_name"]), clean_team_name(r["away_name"]))
        if key in seen: duplicate_keys.append(key)
        seen.add(key)
    if duplicate_keys:
        passed = False
    commit_result = {"committed": False, "reason": "dry-run or six-team gate failed"}
    if args.commit and passed:
        # Both stores receive the same validated batch only after the all-team gate.
        c1 = write_complete(all_rows)
        c2 = write_library(all_rows)
        commit_result = {"committed": True, "complete_new": c1, "library_rows_written": c2}
    report = {"created_at": datetime.now(timezone.utc).isoformat(), "mode": "commit" if args.commit else "dry-run", "passed": passed, "teams": results, "total_rows": len(all_rows), "duplicate_keys": duplicate_keys, "commit": commit_result}
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    print(f"REPORT={REPORT}")
    raise SystemExit(0 if passed else 2)

if __name__ == "__main__":
    main()

from __future__ import annotations

import csv
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATE = "2026-10-31"
HOME = "Newport County"
AWAY = "Chesterfield"
LEAGUE_ZH = "英格蘭乙組聯賽"
SEASON = "2026/27"
MATCH_ID = "FB7955"
SOURCE = "user-provided match result (FT/corners)"
REPORTED_AMOUNT = 62.7

MATCH = {
    "date": DATE, "home_team": HOME, "away_team": AWAY,
    "home_goals": 4, "away_goals": 1,
    "home_corners": 6, "away_corners": 4,
    "league": LEAGUE_ZH, "season": SEASON, "source": SOURCE,
    "source_url": "", "verified_ft": 1, "corner_verified": 1,
    "match_id": MATCH_ID,
}


def append_csv(path: Path, row: dict, keys: tuple[str, ...]) -> bool:
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = []
    if path.exists():
        with path.open("r", encoding="utf-8-sig", newline="") as fh:
            rows = list(csv.DictReader(fh))
        rows = [{str(k).lstrip("\ufeff"): v for k, v in r.items()} for r in rows]
    key = tuple(str(row.get(k, "")) for k in keys)
    if any(tuple(str(r.get(k, "")) for k in keys) == key for r in rows):
        return False
    fields = list(rows[0].keys()) if rows else list(row.keys())
    for k in row:
        if k not in fields:
            fields.append(k)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader(); writer.writerows(rows); writer.writerow(row)
    return True


def update_library() -> dict:
    db = ROOT / "football_library.db"
    conn = sqlite3.connect(db)
    try:
        conn.execute("""CREATE TABLE IF NOT EXISTS match_notes (
            match_id TEXT PRIMARY KEY, date TEXT, league TEXT, home_team TEXT,
            away_team TEXT, reported_amount REAL, amount_type TEXT, source TEXT,
            created_at TEXT
        )""")
        conn.execute("""CREATE TABLE IF NOT EXISTS teams_stats (
            date TEXT, league_id TEXT, team TEXT, goals REAL,
            corners_avg REAL, injury_status TEXT, form TEXT, source TEXT
        )""")
        conn.execute("""CREATE TABLE IF NOT EXISTS corners (
            match_id TEXT PRIMARY KEY, corner_home REAL, corner_away REAL,
            verified INTEGER NOT NULL DEFAULT 0, source_fbref TEXT,
            source_flashscore TEXT, source TEXT
        )""")
        conn.execute("""INSERT OR IGNORE INTO matches
            (league, season, home, away, hg, ag, date, source, captured_at, hc, ac)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (LEAGUE_ZH, SEASON, HOME, AWAY, 4, 1, DATE, SOURCE,
             datetime.now(timezone.utc).isoformat(), 6, 4))
        conn.execute("""INSERT OR IGNORE INTO fixtures
            (match_id, league, date, season, home_team, away_team,
             home_goals, away_goals, source)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (MATCH_ID, LEAGUE_ZH, DATE, SEASON, HOME, AWAY, 4, 1, SOURCE))
        conn.execute("""INSERT OR IGNORE INTO corners
            (match_id, corner_home, corner_away, verified, source)
            VALUES (?, ?, ?, 1, ?)""", (MATCH_ID, 6, 4, SOURCE))
        conn.execute("""INSERT OR IGNORE INTO match_notes
            (match_id, date, league, home_team, away_team, reported_amount,
             amount_type, source, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (MATCH_ID, DATE, LEAGUE_ZH, HOME, AWAY, REPORTED_AMOUNT,
             "unclassified_user_reported_amount", SOURCE,
             datetime.now(timezone.utc).isoformat()))
        # One-match observed rows only; these are not season estimates.
        for team, goals, corners in ((HOME, 4.0, 6.0), (AWAY, 1.0, 4.0)):
            conn.execute("""DELETE FROM teams_stats
                WHERE date=? AND league_id=? AND team=? AND source=?""",
                (DATE, "league-two", team, SOURCE))
            conn.execute("""INSERT INTO teams_stats
                (date, league_id, team, goals, corners_avg, injury_status, form, source)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (DATE, "league-two", team, goals, corners, None, None, SOURCE))
        conn.commit()
        return {"library": "updated"}
    finally:
        conn.close()


def update_complete() -> dict:
    db = ROOT / "football_complete.db"
    conn = sqlite3.connect(db)
    try:
        # Do not create fictional teams. Only write if both canonical teams exist.
        rows = conn.execute("""SELECT id, lower(en_name) FROM teams
            WHERE lower(en_name) IN (?, ?, ?, ?) LIMIT 4""",
            (HOME.lower(), AWAY.lower(), "newport (eng)", "chesterfield (eng)"),).fetchall()
        ids = {name: tid for tid, name in rows}
        home_id = next((tid for name, tid in ids.items() if "newport" in name), None)
        away_id = next((tid for name, tid in ids.items() if "chesterfield" in name), None)
        if not home_id or not away_id:
            return {"complete": "skipped_no_canonical_teams", "written": False}
        conn.execute("""INSERT OR IGNORE INTO fixtures
            (league_id, date, home_id, away_id, ft_home, ft_away,
             corners_home, corners_away, corners_verified, flashscore_match_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, ?)""",
            ("league-two", DATE, home_id, away_id, 4, 1, 6, 4, MATCH_ID))
        conn.commit()
        return {"complete": "updated", "written": True}
    finally:
        conn.close()


def main() -> None:
    history = ROOT / "data/match_history/league_efl_league_two_2026_27.csv"
    added_history = append_csv(history, MATCH, ("date", "home_team", "away_team"))
    notes = ROOT / "data/match_learning_notes.csv"
    added_note = append_csv(notes, {
        "match_id": MATCH_ID, "date": DATE, "league": LEAGUE_ZH,
        "home_team": HOME, "away_team": AWAY,
        "reported_amount": REPORTED_AMOUNT,
        "amount_type": "unclassified_user_reported_amount",
        "source": SOURCE,
    }, ("match_id",))
    result = {"history_added": added_history, "note_added": added_note}
    result.update(update_library())
    result.update(update_complete())
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

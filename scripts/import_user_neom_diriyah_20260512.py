from __future__ import annotations

import csv
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATE = "2026-05-12"
HOME = "Neom SC"
AWAY = "Diriyah"
LEAGUE_ZH = "沙職"
LEAGUE_ID = 307
SEASON = "2026/27"
SOURCE = "user-provided WhatsApp (現場核實)"
MATCH_ID = "user-20260512-neom-sc-diriyah"

MATCH = {
    "date": DATE,
    "season": SEASON,
    "home_team": HOME,
    "away_team": AWAY,
    "home_goals": 2,
    "away_goals": 1,
    "home_corners": 2,
    "away_corners": 5,
    "half_home_goals": 1,
    "half_away_goals": 1,
    "source": SOURCE,
    "verified_ft": 1,
    "verified_ht": 1,
    "corner_verified": 1,
    "source_note": "用戶提供：Neom SC 2-1 Al-Diriyah；半場1-1；角球2-5",
}

BETS = [
    {"bet_id": MATCH_ID + "-u25", "market": "入球大小", "selection": "細2.5", "odds": 1.94, "stake": 10.0, "result": "輸", "payout": 0.0, "net": -10.0},
    {"bet_id": MATCH_ID + "-u35", "market": "入球大小", "selection": "細3.5", "odds": 1.34, "stake": 20.0, "result": "贏", "payout": 26.8, "net": 6.8},
]


def natural_key(row: dict) -> tuple[str, str, str, str]:
    return (str(row.get("date", ""))[:10], str(row.get("home_team", "")).strip().lower(), str(row.get("away_team", "")).strip().lower(), str(LEAGUE_ID))


def append_csv(path: Path, row: dict, key_fields: tuple[str, ...]) -> bool:
    path.parent.mkdir(parents=True, exist_ok=True)
    exists = path.exists()
    rows = []
    if exists:
        with path.open("r", encoding="utf-8-sig", newline="") as fh:
            rows = list(csv.DictReader(fh))
        rows = [{str(k).lstrip("\ufeff"): v for k, v in old.items()} for old in rows]
    key = tuple(str(row.get(k, "")) for k in key_fields)
    if any(tuple(str(old.get(k, "")) for k in key_fields) == key for old in rows):
        return False
    fieldnames = list(rows[0].keys()) if rows else list(row.keys())
    for k in row:
        if k not in fieldnames:
            fieldnames.append(k)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
        writer.writerow(row)
    return True


def upsert_library(conn: sqlite3.Connection) -> None:
    conn.execute("""CREATE TABLE IF NOT EXISTS bet_records (
        bet_id TEXT PRIMARY KEY, match_id TEXT NOT NULL, league TEXT, date TEXT,
        home_team TEXT, away_team TEXT, market TEXT, selection TEXT,
        odds REAL, stake REAL, result TEXT, payout REAL, net REAL,
        source TEXT, created_at TEXT
    )""")
    conn.execute("""INSERT OR IGNORE INTO matches
        (league, season, home, away, hg, ag, date, source, captured_at, hc, ac, ht_home, ht_away)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (LEAGUE_ZH, SEASON, HOME, AWAY, 2, 1, DATE, SOURCE,
         datetime.now(timezone.utc).isoformat(), 2, 5, 1, 1))
    conn.execute("""INSERT OR IGNORE INTO fixtures
        (match_id, league, date, season, home_team, away_team, home_goals, away_goals,
         half_home_goals, half_away_goals, source)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (MATCH_ID, LEAGUE_ZH, DATE, SEASON, HOME, AWAY, 2, 1, 1, 1, SOURCE))
    conn.execute("""CREATE TABLE IF NOT EXISTS corners (
        match_id TEXT PRIMARY KEY, corner_home REAL, corner_away REAL,
        verified INTEGER NOT NULL DEFAULT 0, source TEXT
    )""")
    conn.execute("""INSERT OR IGNORE INTO corners
        (match_id, corner_home, corner_away, verified, source)
        VALUES (?, ?, ?, ?, ?)""", (MATCH_ID, 2, 5, 1, SOURCE))
    now = datetime.now(timezone.utc).isoformat()
    for bet in BETS:
        conn.execute("""INSERT OR IGNORE INTO bet_records
            (bet_id, match_id, league, date, home_team, away_team, market, selection,
             odds, stake, result, payout, net, source, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (bet["bet_id"], MATCH_ID, LEAGUE_ZH, DATE, HOME, AWAY, bet["market"],
             bet["selection"], bet["odds"], bet["stake"], bet["result"], bet["payout"], bet["net"], SOURCE, now))


def upsert_complete(conn: sqlite3.Connection) -> None:
    # Team IDs already exist in the complete DB from the Saudi directory import.
    home_id = conn.execute("SELECT id FROM teams WHERE lower(en_name) IN ('neom sc','neom (sau)') LIMIT 1").fetchone()
    away_id = conn.execute("SELECT id FROM teams WHERE lower(en_name) IN ('diriyah','diriyah club (sau)') LIMIT 1").fetchone()
    if not home_id or not away_id:
        raise RuntimeError("complete DB缺少Neom/Diriyah隊伍ID，拒絕寫入避免建假隊")
    conn.execute("""INSERT OR IGNORE INTO fixtures
        (league_id, date, home_id, away_id, ft_home, ft_away, ht_home, ht_away,
         corners_home, corners_away, corners_verified, flashscore_match_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (LEAGUE_ID, DATE, home_id[0], away_id[0], 2, 1, 1, 1, 2, 5, 1, MATCH_ID))
    conn.execute("""CREATE TABLE IF NOT EXISTS bet_records (
        bet_id TEXT PRIMARY KEY, match_id TEXT NOT NULL, league TEXT, date TEXT,
        home_team TEXT, away_team TEXT, market TEXT, selection TEXT,
        odds REAL, stake REAL, result TEXT, payout REAL, net REAL,
        source TEXT, created_at TEXT
    )""")
    now = datetime.now(timezone.utc).isoformat()
    for bet in BETS:
        conn.execute("""INSERT OR IGNORE INTO bet_records
            (bet_id, match_id, league, date, home_team, away_team, market, selection,
             odds, stake, result, payout, net, source, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (bet["bet_id"], MATCH_ID, LEAGUE_ZH, DATE, HOME, AWAY, bet["market"],
             bet["selection"], bet["odds"], bet["stake"], bet["result"], bet["payout"], bet["net"], SOURCE, now))


def main() -> None:
    # Durable local source files used by the App.
    csv_path = ROOT / "data/leagues/saudi-pro/matches.csv"
    csv_row = {
        "date": DATE, "season": SEASON, "home_team": HOME, "away_team": AWAY,
        "home_goals": 2, "away_goals": 1, "home_corners": 2, "away_corners": 5,
        "source": SOURCE, "verified_ft": 1, "verified_ht": 1, "corner_verified": 1,
    }
    added_csv = append_csv(csv_path, csv_row, ("date", "home_team", "away_team"))

    json_path = ROOT / "data/leagues/saudi-pro/matches.json"
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    json_added = False
    if not any(str(x.get("date", ""))[:10] == DATE and x.get("home_team") == HOME and x.get("away_team") == AWAY for x in payload):
        payload.append({**MATCH, "match_id": MATCH_ID, "status": "finished"})
        json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        json_added = True

    # History ledger for user-facing audit and totals.
    bet_csv = ROOT / "data/betting_history.csv"
    bet_added = sum(append_csv(bet_csv, {
        "bet_id": b["bet_id"], "match_id": MATCH_ID, "league": LEAGUE_ZH, "date": DATE,
        "home_team": HOME, "away_team": AWAY, **b, "source": SOURCE,
    }, ("bet_id",)) for b in BETS)

    for db_name in ("football_library.db", "football_complete.db"):
        conn = sqlite3.connect(ROOT / db_name)
        try:
            if db_name == "football_library.db":
                upsert_library(conn)
            else:
                upsert_complete(conn)
            conn.commit()
        finally:
            conn.close()

    print(json.dumps({
        "match_key": natural_key(MATCH), "match_csv_added": added_csv,
        "match_json_added": json_added, "bet_rows_added": bet_added,
        "total_stake": sum(x["stake"] for x in BETS),
        "total_payout": sum(x["payout"] for x in BETS),
        "net": sum(x["net"] for x in BETS), "verified_ft": 1,
        "verified_ht": 1, "corner_verified": 1, "source": SOURCE,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

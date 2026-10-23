#!/usr/bin/env python3
"""Import the user-supplied 2026 South Melbourne/Sydney United results safely.

The rows are stored as user-provided data. Corner values are deliberately marked
unverified until independently cross-checked, so the app can use goals/forms but
will not present the corners as authoritative.
"""
from __future__ import annotations
import csv
import json
import shutil
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LIB = ROOT / "football_library.db"
MULTI = ROOT / "data" / "multisource_football.db"
CACHE = ROOT / "data" / "leagues" / "australian-championship" / "matches.csv"
LEAGUE = "澳洲冠軍聯賽盃"
SEASON = "2026"
SOURCE = "user-provided match list; 角球未核實"
CAPTURED = datetime.now(timezone.utc).isoformat()

ROWS = [
("2026-10-17","Sutherland Sharks","South Melbourne FC",0,1,5,4),
("2026-10-10","South Melbourne FC","Melbourne Victory",1,1,6,3),
("2026-09-15","South Melbourne FC","Lions FC",3,1,7,2),
("2026-09-11","Oakleigh","South Melbourne FC",2,1,4,5),
("2026-09-06","South Melbourne FC","Heidelberg",2,1,8,3),
("2026-08-29","Caroline Springs","South Melbourne FC",1,0,3,4),
("2026-08-23","South Melbourne FC","Heidelberg",1,2,5,6),
("2026-08-15","Melbourne City II","South Melbourne FC",0,3,2,7),
("2026-08-02","South Melbourne FC","St Albans",2,0,9,1),
("2026-07-18","South Melbourne FC","Preston Lions",0,0,6,2),
("2026-10-18","Sydney United 58 FC","Canberra Croatia",1,1,4,5),
("2026-09-13","APIA Leichhardt","Sydney United 58 FC",1,3,3,6),
("2026-09-06","Sydney United 58 FC","Manly United",3,1,7,4),
("2026-08-30","Sydney United 58 FC","St George Saints",6,0,10,1),
("2026-08-23","Sydney United 58 FC","APIA Leichhardt",0,0,5,4),
("2026-08-15","Sydney Olympic","Sydney United 58 FC",1,2,4,5),
("2026-08-09","Wollongong","Sydney United 58 FC",1,2,3,6),
("2026-08-02","Sydney United 58 FC","NWS Spirit",2,0,6,2),
("2026-07-25","St George City","Sydney United 58 FC",1,0,5,3),
("2026-07-19","Marconi","Sydney United 58 FC",0,1,2,4),
]


def backup(path: Path):
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    dst = path.with_name(path.name + ".bak-" + stamp)
    shutil.copy2(path, dst)
    return dst


def main():
    for path in (LIB, MULTI):
        if not path.exists():
            raise SystemExit(f"missing database: {path}")
    backups = [backup(LIB), backup(MULTI)]

    with sqlite3.connect(LIB, timeout=30) as c:
        c.execute("PRAGMA journal_mode=WAL")
        c.execute("PRAGMA busy_timeout=30000")
        c.executemany(
            """INSERT INTO matches
               (league,season,home,away,hg,ag,hc,ac,date,source,captured_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?)
               ON CONFLICT(league,season,home,away,date) DO UPDATE SET
                 hg=excluded.hg, ag=excluded.ag, hc=excluded.hc, ac=excluded.ac,
                 source=excluded.source, captured_at=excluded.captured_at""",
            [(LEAGUE, SEASON, h, a, hg, ag, hc, ac, d, SOURCE, CAPTURED)
             for d,h,a,hg,ag,hc,ac in ROWS],
        )
        counts = {}
        for team in ("South Melbourne FC", "Sydney United 58 FC"):
            counts[team] = c.execute(
                "SELECT COUNT(*) FROM matches WHERE league=? AND (home=? OR away=?)",
                (LEAGUE, team, team),
            ).fetchone()[0]
        c.execute("INSERT INTO source_log(league,source,status,message,captured_at) VALUES(?,?,?,?,?)",
                  (LEAGUE, SOURCE, "imported", json.dumps(counts, ensure_ascii=False), CAPTURED))

    # Keep the multisource fixture/teams database consistent for API consumers.
    with sqlite3.connect(MULTI, timeout=30) as c:
        c.execute("PRAGMA journal_mode=WAL")
        c.execute("PRAGMA busy_timeout=30000")
        c.executemany(
            """INSERT OR REPLACE INTO fixtures
               (league_id,fixture_id,date,season,home_team,away_team,home_goals,away_goals,home_corners,away_corners,source)
               VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            [("australian-championship", f"user-2026-{i:02d}", d, SEASON, h, a, hg, ag, hc, ac, SOURCE)
             for i,(d,h,a,hg,ag,hc,ac) in enumerate(ROWS, 1)],
        )
        c.executemany(
            """INSERT OR REPLACE INTO teams(league_id,team_id,team_name,slug,source)
               VALUES(?,?,?,?,?)""",
            [("australian-championship", "south-melbourne-fc", "South Melbourne FC", "south-melbourne-fc", SOURCE),
             ("australian-championship", "sydney-united-58-fc", "Sydney United 58 FC", "sydney-united-58-fc", SOURCE)],
        )

    # Append/update the local league cache without duplicating the same date/team pair.
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    existing = []
    if CACHE.exists():
        with CACHE.open(encoding="utf-8-sig", newline="") as f:
            existing = list(csv.DictReader(f))
    keys = {(r.get("date"), r.get("home_team"), r.get("away_team")) for r in existing}
    for d,h,a,hg,ag,hc,ac in ROWS:
        if (d,h,a) not in keys:
            existing.append({"date":d,"home_team":h,"away_team":a,"home_goals":hg,"away_goals":ag,
                             "home_corners":"","away_corners":"","source":SOURCE})
    fields = ["date","home_team","away_team","home_goals","away_goals","home_corners","away_corners","source"]
    with CACHE.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields); w.writeheader(); w.writerows(existing)

    print(json.dumps({"imported": len(ROWS), "counts": counts,
                      "backups": [str(x) for x in backups], "source": SOURCE}, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()

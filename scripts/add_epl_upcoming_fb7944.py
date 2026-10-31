from __future__ import annotations

import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MATCHES = ROOT / "data/leagues/epl/matches.csv"
FIXTURE = {
    "fixture_id": "FB7944",
    "date": "2026-10-31T12:30:00Z",
    "season": "2026",
    "home_team": "Chelsea",
    "away_team": "Manchester United",
    "home_goals": "",
    "away_goals": "",
    "home_corners": "",
    "away_corners": "",
    "source": "user screenshot (Jockey Club fixture board); upcoming only",
}
FIELDS = list(FIXTURE)

existing = []
if MATCHES.exists():
    with MATCHES.open(newline="", encoding="utf-8-sig") as f:
        existing = list(csv.DictReader(f))

if "FB7944" in {r.get("fixture_id", "") for r in existing}:
    added = 0
else:
    with MATCHES.open("a", newline="", encoding="utf-8") as f:
        if MATCHES.stat().st_size == 0:
            csv.DictWriter(f, fieldnames=FIELDS).writeheader()
        csv.DictWriter(f, fieldnames=FIELDS).writerow(FIXTURE)
    added = 1

print({"fixture_id": "FB7944", "added": added, "status": "upcoming_only_no_ft_or_corners"})

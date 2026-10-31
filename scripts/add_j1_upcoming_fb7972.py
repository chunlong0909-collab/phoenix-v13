from __future__ import annotations

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
J1_MATCHES = ROOT / "data/leagues/j1/matches.csv"
ODDS = ROOT / "data/odds/manual_odds.csv"

fixture = {
    "fixture_id": "FB7972",
    "date": "2026-10-31T05:00:00Z",
    "season": "2026",
    "home_team": "Kyoto Sanga",
    "away_team": "Shimizu S-Pulse",
    "home_goals": "",
    "away_goals": "",
    "home_corners": "",
    "away_corners": "",
    "source": "J.League official fixture + user screenshot odds",
}

odds_rows = [
    {"fixture_id":"FB7972","captured_at":"2026-10-31T10:22:00+08:00","market":"1X2","selection":"home","line":"","odds":"2.23","source":"user screenshot"},
    {"fixture_id":"FB7972","captured_at":"2026-10-31T10:22:00+08:00","market":"1X2","selection":"draw","line":"","odds":"3.25","source":"user screenshot"},
    {"fixture_id":"FB7972","captured_at":"2026-10-31T10:22:00+08:00","market":"1X2","selection":"away","line":"","odds":"2.66","source":"user screenshot"},
    {"fixture_id":"FB7972","captured_at":"2026-10-31T10:22:00+08:00","market":"goals_ou","selection":"over","line":"2.5","odds":"1.86","source":"user screenshot"},
    {"fixture_id":"FB7972","captured_at":"2026-10-31T10:22:00+08:00","market":"goals_ou","selection":"under","line":"2.5","odds":"1.84","source":"user screenshot"},
    {"fixture_id":"FB7972","captured_at":"2026-10-31T10:22:00+08:00","market":"corners_ou","selection":"over","line":"9.5","odds":"1.90","source":"user screenshot"},
    {"fixture_id":"FB7972","captured_at":"2026-10-31T10:22:00+08:00","market":"corners_ou","selection":"under","line":"9.5","odds":"1.80","source":"user screenshot"},
    {"fixture_id":"FB7972","captured_at":"2026-10-31T10:22:00+08:00","market":"corners_ou","selection":"over","line":"10.5","odds":"2.38","source":"user screenshot"},
    {"fixture_id":"FB7972","captured_at":"2026-10-31T10:22:00+08:00","market":"corners_ou","selection":"under","line":"10.5","odds":"1.51","source":"user screenshot"},
    {"fixture_id":"FB7972","captured_at":"2026-10-31T10:22:00+08:00","market":"corners_ou","selection":"over","line":"13.5","odds":"4.75","source":"user screenshot"},
    {"fixture_id":"FB7972","captured_at":"2026-10-31T10:22:00+08:00","market":"corners_ou","selection":"under","line":"13.5","odds":"1.13","source":"user screenshot"},
]


def append_unique(path: Path, rows: list[dict], fieldnames: list[str], key_fields: tuple[str, ...]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    existing = []
    if path.exists() and path.stat().st_size:
        with path.open(newline="", encoding="utf-8-sig") as f:
            existing = list(csv.DictReader(f))
    keys = {tuple(r.get(k, "") for k in key_fields) for r in existing}
    added = [r for r in rows if tuple(r.get(k, "") for k in key_fields) not in keys]
    if existing or added:
        with path.open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=fieldnames)
            w.writeheader()
            w.writerows(existing + added)
    return len(added)


if __name__ == "__main__":
    match_fields = list(fixture)
    n_fixture = append_unique(J1_MATCHES, [fixture], match_fields, ("fixture_id",))
    odds_fields = list(odds_rows[0])
    n_odds = append_unique(ODDS, odds_rows, odds_fields, ("fixture_id", "market", "selection", "line", "odds"))
    print(json.dumps({"fixture_added": n_fixture, "odds_added": n_odds, "fixture_id": "FB7972", "status": "upcoming_only_no_ft_or_corners"}, ensure_ascii=False))

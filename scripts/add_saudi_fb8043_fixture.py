from __future__ import annotations

import csv
import json
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
LEAGUE_DIR = ROOT / "data" / "leagues" / "saudi-pro"
TEAMS_CSV = LEAGUE_DIR / "teams.csv"
TEAMS_JSON = LEAGUE_DIR / "teams.json"
MATCHES_CSV = LEAGUE_DIR / "matches.csv"
MATCHES_JSON = LEAGUE_DIR / "matches.json"

# User supplied HKJC screenshot confirms the fixture and displayed market odds.
# It is intentionally stored as an upcoming fixture only: no FT/HT/corners are inferred.
TEAMS = [
    {
        "team_name": "Diriyah Club (Sau)",
        "team_id": "diriyah_club_sau",
        "country": "Saudi Arabia",
        "stadium": "",
        "crest_url": "",
        "espn_team_id": "",
        "source": "user-provided screenshot FB8043; directory_only",
        "lastUpdated": "2026-10-30T00:00:00+00:00",
        "dataSource": "directory_only",
    },
    {
        "team_name": "NEOM (Sau)",
        "team_id": "neom_sau",
        "country": "Saudi Arabia",
        "stadium": "",
        "crest_url": "",
        "espn_team_id": "",
        "source": "user-provided screenshot FB8043; directory_only",
        "lastUpdated": "2026-10-30T00:00:00+00:00",
        "dataSource": "directory_only",
    },
]

FIXTURE = {
    "date": "2026-10-30T14:50:00Z",  # 22:50 HKT
    "season": "2026",
    "home_team": "Diriyah",
    "away_team": "Neom SC",
    "home_goals": None,
    "away_goals": None,
    "home_corners": None,
    "away_corners": None,
    "source": "user-provided screenshot FB8043 (upcoming fixture; no FT)",
    "match_id": "FB8043",
    "status": "scheduled",
    "odds_only": {
        "home_win": 2.30,
        "draw": 3.15,
        "away_win": 2.63,
        "source": "user-provided screenshot",
        "not_ft": True,
    },
}


def load_rows(path: Path):
    with path.open(encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def save_csv(path: Path, rows, fieldnames):
    with path.open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def main():
    team_rows = load_rows(TEAMS_CSV)
    existing_names = {str(r.get("team_name", "")).casefold() for r in team_rows}
    for team in TEAMS:
        if team["team_name"].casefold() not in existing_names:
            team_rows.append(team)
    save_csv(TEAMS_CSV, team_rows, list(team_rows[0].keys()))
    TEAMS_JSON.write_text(json.dumps(team_rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    match_rows = load_rows(MATCHES_CSV)
    if not any(str(r.get("source", "")).find("FB8043") >= 0 for r in match_rows):
        match_rows.append({
            "date": FIXTURE["date"],
            "season": FIXTURE["season"],
            "home_team": FIXTURE["home_team"],
            "away_team": FIXTURE["away_team"],
            "home_goals": "",
            "away_goals": "",
            "home_corners": "",
            "away_corners": "",
            "source": FIXTURE["source"],
        })
    save_csv(MATCHES_CSV, match_rows, list(match_rows[0].keys()))

    existing_json = json.loads(MATCHES_JSON.read_text(encoding="utf-8-sig"))
    if not any(str(r.get("source", "")).find("FB8043") >= 0 for r in existing_json):
        existing_json.append(FIXTURE)
    MATCHES_JSON.write_text(json.dumps(existing_json, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print("SAUDI_DIRECTORY_ADDED", [x["team_name"] for x in TEAMS])
    print("FB8043_FIXTURE", FIXTURE["date"], FIXTURE["home_team"], "vs", FIXTURE["away_team"])
    print("FT_FIELDS", FIXTURE["home_goals"], FIXTURE["away_goals"], "HT=missing", "corners=missing")
    print("ODDS_ONLY", FIXTURE["odds_only"])


if __name__ == "__main__":
    main()

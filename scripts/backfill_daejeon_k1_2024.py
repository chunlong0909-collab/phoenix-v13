from __future__ import annotations

import json
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SOURCE_URL = (
    "https://fbref.com/en/squads/2075253c/2024/matchlogs/c55/schedule/"
    """Daejeon-Hana-Citizen-Scores-and-Fixtures-K-League-1"""
)

# 20 rows transcribed from the cited FBref Scores & Fixtures table.
# HC/AC are deliberately blank: that table exposes no verified per-match corners.
ROWS = [
    ("2024-03-01", "Jeonbuk Hyundai Motors", "Daejeon Hana Citizen", 1, 1),
    ("2024-03-10", "Jeju United", "Daejeon Hana Citizen", 1, 3),
    ("2024-03-16", "Daejeon Hana Citizen", "Gangwon FC", 1, 1),
    ("2024-03-30", "Incheon United", "Daejeon Hana Citizen", 0, 2),
    ("2024-04-02", "Daejeon Hana Citizen", "Ulsan HD", 2, 0),
    ("2024-04-07", "Daejeon Hana Citizen", "Pohang Steelers", 1, 2),
    ("2024-04-14", "Suwon FC", "Daejeon Hana Citizen", 0, 1),
    ("2024-04-21", "Daegu FC", "Daejeon Hana Citizen", 0, 0),
    ("2024-04-27", "Daejeon Hana Citizen", "FC Seoul", 3, 1),
    ("2024-04-30", "Daejeon Hana Citizen", "Gimcheon Sangmu", 0, 0),
    ("2024-05-06", "Gwangju FC", "Daejeon Hana Citizen", 2, 1),
    ("2024-05-11", "Gangwon FC", "Daejeon Hana Citizen", 3, 3),
    ("2024-05-18", "Daejeon Hana Citizen", "Incheon United", 0, 1),
    ("2024-05-25", "Ulsan HD", "Daejeon Hana Citizen", 1, 4),
    ("2024-05-29", "Daejeon Hana Citizen", "Jeju United", 0, 1),
    ("2024-06-02", "Daejeon Hana Citizen", "Daegu FC", 1, 0),
    ("2024-06-15", "Pohang Steelers", "Daejeon Hana Citizen", 1, 1),
    ("2024-06-22", "Daejeon Hana Citizen", "Gwangju FC", 2, 1),
    ("2024-06-25", "Gimcheon Sangmu", "Daejeon Hana Citizen", 2, 0),
    ("2024-06-29", "Daejeon Hana Citizen", "Suwon FC", 0, 2),
]

columns = ["date", "home_team", "away_team", "home_goals", "away_goals",
           "home_corners", "away_corners", "league", "season", "source_url"]
df = pd.DataFrame([
    {"date": d, "home_team": h, "away_team": a, "home_goals": hg, "away_goals": ag,
     "home_corners": pd.NA, "away_corners": pd.NA, "league": "韓職K1", "season": "2024",
     "source_url": SOURCE_URL}
    for d, h, a, hg, ag in ROWS
], columns=columns)

# Keep both canonical local league files and the App match_history mirrors in sync.
for path in [ROOT / "data/leagues/k1/matches.csv", ROOT / "data/match_history/k1.csv",
             ROOT / "assets/data/match_history/k1.csv"]:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)

# JSON evidence for the K1 loader and a stable source/audit record.
for path in [ROOT / "data/leagues/k1/matches.json"]:
    path.write_text(json.dumps([
        {"date": r[0], "home_team": r[1], "away_team": r[2], "home_goals": r[3],
         "away_goals": r[4], "home_corners": None, "away_corners": None,
         "league": "韓職K1", "season": "2024", "source": SOURCE_URL}
        for r in ROWS
    ], ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

metadata_path = ROOT / "data/leagues/k1/metadata.json"
metadata = json.loads(metadata_path.read_text(encoding="utf-8")) if metadata_path.exists() else {}
metadata.update({"league": "韓職K1", "season": "2024", "matches_rows": len(df),
                 "teams_in_matches": len(set(df.home_team) | set(df.away_team)),
                 "ft_valid_rows": len(df), "corners_verified_rows": 0,
                 "corners_policy": "NULL: source table does not expose verified per-match HC/AC",
                 "source_url": SOURCE_URL})
metadata_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

print(f"K1_DAEJEON_ROWS={len(df)} FT_OK={len(df)} HC_AC_VERIFIED=0")
print(f"SOURCE={SOURCE_URL}")

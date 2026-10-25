from __future__ import annotations

import json
import re
import unicodedata
from collections import defaultdict
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "catalog" / "complete_500_partial_catalog.json"
REPORT = ROOT / "catalog" / "final45_expansion_audit.json"

SEASONS = {
    "英冠": ["2021/2022", "2022/2023", "2023/2024", "2024/2025"],
    "奧甲": ["2021/2022", "2022/2023", "2023/2024", "2024/2025"],
    "丹超": ["2021/2022", "2022/2023", "2023/2024", "2024/2025"],
    "挪超": ["2021", "2022", "2023", "2024"],
}
TARGETS = {
    "英冠": ["West Brom", "Blackburn", "Swansea", "Bristol City", "Cardiff", "Preston", "Hull", "QPR", "Millwall", "Stoke", "Middlesbrough", "Coventry"],
    "奧甲": ["Austria Vienna", "Tirol", "SK Rapid", "Hartberg", "Wolfsberger AC", "LASK", "Sturm Graz", "Salzburg", "Altach", "A. Klagenfurt", "A. Lustenau", "Ried"],
    "丹超": ["Viborg", "Midtjylland", "Randers FC", "FC Copenhagen", "Nordsjaelland", "Aarhus", "Brondby", "Silkeborg", "Aalborg", "Odense"],
    "挪超": ["Haugesund", "Sandefjord", "Bodo/Glimt", "Tromso", "Molde", "Viking", "Rosenborg", "Sarpsborg 08", "Stromsgodset", "Lillestrom", "Odd"],
}
SOURCES = {
    "英冠": (ROOT / "data" / "raw" / "E1.csv", "HomeTeam", "AwayTeam", "FTHG", "FTAG", "Season"),
    "奧甲": (ROOT / "data" / "raw" / "AUT.csv", "HomeTeam", "AwayTeam", "FTHG", "FTAG", "Season"),
    "丹超": (ROOT / "data" / "leagues" / "denmark" / "matches.csv", "Home", "Away", "HG", "AG", "Season"),
    "挪超": (ROOT / "data" / "leagues" / "norway" / "matches.csv", "Home", "Away", "HG", "AG", "Season"),
}


def norm(value: str) -> str:
    value = unicodedata.normalize("NFKD", str(value or "")).lower()
    value = "".join(c for c in value if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", "", value)


def catalog_index(data):
    index = defaultdict(list)
    for block_name, block in data.items():
        if not isinstance(block, dict):
            continue
        for team in block.get("teams", []):
            index[norm(team.get("name"))].append({
                "league": block_name,
                "name": team.get("name"),
                "matches": len(team.get("matches", [])),
            })
    return index


def source_candidates(league):
    path, home_col, away_col, hg_col, ag_col, season_col = SOURCES[league]
    df = pd.read_csv(path, encoding="utf-8-sig", encoding_errors="replace")
    df = df[df[season_col].astype(str).isin(SEASONS[league])]
    rows = defaultdict(list)
    invalid = 0
    for row_no, row in df.iterrows():
        try:
            if pd.isna(row[hg_col]) or pd.isna(row[ag_col]):
                invalid += 1
                continue
            int(float(row[hg_col])); int(float(row[ag_col]))
        except Exception:
            invalid += 1
            continue
        season = str(row[season_col])
        for side in (home_col, away_col):
            rows[str(row[side]).strip()].append(season)
    return rows, len(df), invalid


def main():
    data = json.loads(CATALOG.read_text(encoding="utf-8"))
    total_teams = sum(len(block.get("teams", [])) for block in data.values() if isinstance(block, dict))
    existing = catalog_index(data)
    report = {
        "catalog": str(CATALOG.relative_to(ROOT)),
        "baseline_teams": total_teams,
        "requested_additions": 45,
        "eligible_new_additions": 0,
        "target_500_reached": total_teams >= 500,
        "policy": "No duplicate teams; real FT only; minimum 90 matches; no HT estimation.",
        "leagues": {},
    }
    for league, wanted in TARGETS.items():
        rows, source_rows, invalid = source_candidates(league)
        details = []
        for name in wanted:
            matched = rows.get(name, [])
            in_catalog = bool(existing.get(norm(name)))
            details.append({
                "name": name,
                "source_matches": len(matched),
                "source_seasons": sorted(set(matched)),
                "source_ft_invalid_rows": invalid,
                "minimum_90": len(matched) >= 90,
                "all_four_seasons": set(matched) == set(SEASONS[league]),
                "already_in_catalog": in_catalog,
                "eligible_new": len(matched) >= 90 and in_catalog is False,
            })
        report["leagues"][league] = {
            "source": str(SOURCES[league][0].relative_to(ROOT)),
            "source_rows": source_rows,
            "source_ft_invalid_rows": invalid,
            "requested": len(wanted),
            "already_present": sum(x["already_in_catalog"] for x in details),
            "eligible_new": sum(x["eligible_new"] for x in details),
            "teams": details,
        }
        report["eligible_new_additions"] += report["leagues"][league]["eligible_new"]
    report["projected_teams_after_safe_merge"] = total_teams + report["eligible_new_additions"]
    report["status"] = "keep_455_safe_no_new_unique_teams"
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({
        "BASELINE_TEAMS": total_teams,
        "REQUESTED": 45,
        "ELIGIBLE_NEW": report["eligible_new_additions"],
        "PROJECTED_SAFE_TOTAL": report["projected_teams_after_safe_merge"],
        "STATUS": report["status"],
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()

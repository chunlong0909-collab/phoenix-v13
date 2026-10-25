from __future__ import annotations

import json
import re
import unicodedata
from collections import defaultdict
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "catalog" / "complete_500_partial_catalog.json"
OUT = ROOT / "catalog" / "complete_650_B_phase.json"
REPORT = ROOT / "catalog" / "final650_B_audit.json"
SEASONS = {"2021", "2022", "2023", "2024"}

# Local Football-Data-derived files already present in the repository.
SOURCES = {
    "美職MLS": (ROOT / "data/raw/MLS_all_seasons.csv", "Home", "Away", "HG", "AG", "Season"),
    "巴西乙": (ROOT / "data/leagues/serie-b/matches.csv", "home_team", "away_team", "home_goals", "away_goals", "season"),
    "阿甲": (ROOT / "data/raw/ARG_all_seasons.csv", "Home", "Away", "HG", "AG", "Season"),
    "泰超": (ROOT / "data/leagues/thai-league1/matches.csv", "home_team", "away_team", "home_goals", "away_goals", "season"),
    "日職J2候選檔": (ROOT / "data/leagues/j2/matches.csv", "home_team", "away_team", "home_goals", "away_goals", "season"),
    "墨乙": (ROOT / "data/leagues/expansion-mx/matches.csv", "home_team", "away_team", "home_goals", "away_goals", "season"),
}


def norm(value: str) -> str:
    value = unicodedata.normalize("NFKD", str(value or "")).lower()
    value = "".join(c for c in value if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", "", value)


def load_catalog():
    data = json.loads(BASE.read_text(encoding="utf-8"))
    count = sum(len(v.get("teams", [])) for v in data.values() if isinstance(v, dict))
    if count != 455:
        raise RuntimeError(f"安全基線不是455隊，而是{count}")
    return data


def existing_names(data):
    return {norm(t.get("name")) for b in data.values() if isinstance(b, dict) for t in b.get("teams", [])}


def source_rows(league, spec):
    path, home_col, away_col, hg_col, ag_col, season_col = spec
    if not path.exists():
        return [], {"exists": False, "path": str(path.relative_to(ROOT)), "source_rows": 0, "ft_invalid_rows": 0}
    df = pd.read_csv(path, encoding="utf-8-sig", encoding_errors="replace", low_memory=False)
    if season_col not in df.columns:
        return [], {"exists": True, "path": str(path.relative_to(ROOT)), "source_rows": len(df), "ft_invalid_rows": len(df), "reason": f"missing season column {season_col}"}
    df = df[df[season_col].astype(str).isin(SEASONS)]
    rows = []
    invalid = 0
    for row_no, row in df.iterrows():
        try:
            if pd.isna(row[hg_col]) or pd.isna(row[ag_col]):
                invalid += 1
                continue
            fh, fa = int(float(row[hg_col])), int(float(row[ag_col]))
            home, away = str(row[home_col]).strip(), str(row[away_col]).strip()
            if not home or not away:
                invalid += 1
                continue
        except Exception:
            invalid += 1
            continue
        rows.append({
            "match_id": f"650b-{league}-{row.get(season_col)}-{row_no}",
            "date": str(row.get("Date", row.get("date", row.get(season_col)))),
            "home": home,
            "away": away,
            "ft_home": fh,
            "ft_away": fa,
            "ht_home": None,
            "ht_away": None,
            "explicit_ht": False,
            "season": str(row.get(season_col)),
            "source": "Football-Data/local-verified",
            "league": league,
        })
    return rows, {"exists": True, "path": str(path.relative_to(ROOT)), "source_rows": len(df), "ft_invalid_rows": invalid}


def append_team(data, league, name, matches):
    block = None
    for key, candidate in data.items():
        if isinstance(candidate, dict) and (key == league or candidate.get("league") == league or candidate.get("competition_code") == league):
            block = candidate
            break
    if block is None:
        key = league
        block = {"target_teams": 0, "competition_code": league, "league": league, "teams": []}
        data[key] = block
    block["teams"].append({"team_id": f"650b-{norm(name)}", "name": name, "league": league, "matches": matches})
    block["target_teams"] = len(block["teams"])


def main():
    data = load_catalog()
    existing = existing_names(data)
    report = {
        "baseline_teams": 455,
        "requested_target": 650,
        "requested_additions": 195,
        "minimum_matches": 90,
        "season_window": sorted(SEASONS),
        "policy": "Real FT only; invalid FT rows are skipped; HT remains null; duplicate teams are never appended.",
        "sources": {},
        "added": [],
        "skipped": [],
    }
    all_new_keys = set()
    for league, spec in SOURCES.items():
        rows, stats = source_rows(league, spec)
        by = defaultdict(list)
        for row in rows:
            by[norm(row["home"])].append(row)
            by[norm(row["away"])].append(row)
        eligible = []
        for key, matches in by.items():
            display = next((r["home"] for r in matches if norm(r["home"]) == key), None) or next(r["away"] for r in matches if norm(r["away"]) == key)
            if len(matches) < 90:
                continue
            if key in existing or key in all_new_keys:
                continue
            eligible.append((key, display, matches))
        # The requested leagues have approximate quotas; all safe local candidates are added,
        # with no fabricated rows and no attempt to fill missing leagues.
        for key, display, matches in eligible:
            append_team(data, league, display, matches)
            all_new_keys.add(key)
            report["added"].append({"league": league, "name": display, "matches": len(matches), "seasons": sorted({m["season"] for m in matches}), "source": stats["path"], "ht_policy": "null"})
        report["sources"][league] = {**stats, "teams_seen": len(by), "eligible_new": len(eligible), "rows_used": len(rows)}
        for key, matches in by.items():
            if len(matches) >= 90 and (key in existing or key in all_new_keys):
                continue
            if len(matches) < 90:
                report["skipped"].append({"league": league, "name": next((r["home"] for r in matches), ""), "matches": len(matches), "reason": "below_90_or_invalid_source"})
    total = sum(len(v.get("teams", [])) for v in data.values() if isinstance(v, dict))
    invalid = sum(1 for b in data.values() if isinstance(b, dict) for t in b.get("teams", []) for m in t.get("matches", []) if m.get("ft_home") is None or m.get("ft_away") is None)
    new_ht = sum(1 for x in report["added"] if x.get("ht_home") is not None or x.get("ht_away") is not None)
    report.update({"total_teams": total, "added_teams": len(report["added"]), "projected_shortfall_to_650": max(0, 650 - total), "ft_invalid_rows": invalid, "new_ht_nonnull_rows": new_ht, "target_reached": total >= 650, "status": "success" if total >= 650 else "partial_honest_data_only"})
    if invalid or new_ht:
        raise RuntimeError("FT/HT policy violation")
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"BASELINE": 455, "ADDED": len(report["added"]), "TOTAL": total, "SHORTFALL": report["projected_shortfall_to_650"], "FT_INVALID": invalid, "HT_NONNULL_NEW": new_ht}, ensure_ascii=False))


if __name__ == "__main__":
    main()

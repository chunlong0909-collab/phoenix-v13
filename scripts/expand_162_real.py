from __future__ import annotations

import csv
import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "catalog" / "complete_5_leagues_catalog.json"
DATA = ROOT / "data" / "leagues"

# These are source labels, not invented scores. Turkish/Belgian files are
# Football-Data historical result files; Brazil is the provider's BRA.csv
# archive filtered to Season=2023 because no BSA.csv endpoint exists there.
SPECS = [
    {
        "key": "土超", "code": "T1", "file": DATA / "super_lig" / "matches.csv",
        "source_file": DATA / "super_lig" / "matches.csv",
        "column_mode": "football_data",
        "teams": {
            "Galatasaray": "Galatasaray", "Fenerbahce": "Fenerbahce",
            "Besiktas": "Besiktas", "Trabzonspor": "Trabzonspor",
            "Basaksehir": "Buyuksehyr", "Adana Demirspor": "Ad. Demirspor",
        },
    },
    {
        "key": "比甲", "code": "B1", "file": DATA / "jupiler" / "matches.csv",
        "source_file": DATA / "jupiler" / "matches.csv",
        "column_mode": "football_data",
        "teams": {
            "Club Brugge": "Club Brugge", "Anderlecht": "Anderlecht",
            "Genk": "Genk", "Antwerp": "Antwerp", "Union SG": "St. Gilloise",
            "Gent": "Gent",
        },
    },
    {
        "key": "巴甲", "code": "BSA", "file": DATA / "brasileirao" / "matches.csv",
        "source_file": DATA / "brasileirao" / "matches.csv",
        "column_mode": "brazil_archive",
        "teams": {
            "Flamengo": "Flamengo RJ", "Palmeiras": "Palmeiras",
            "Atletico Mineiro": "Atletico-MG", "Corinthians": "Corinthians",
            "Fluminense": "Fluminense", "Gremio": "Gremio",
            "Botafogo": "Botafogo RJ", "Athletico-PR": "Athletico-PR",
            "Internacional": "Internacional", "Fortaleza": "Fortaleza",
            "Sao Paulo": "Sao Paulo", "Cruzeiro": "Cruzeiro",
            "Bragantino": "Bragantino", "Santos": "Santos",
            "Bahia": "Bahia", "Vasco": "Vasco",
        },
    },
]


def read_rows(spec):
    with spec["source_file"].open(newline="", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    if spec["column_mode"] == "brazil_archive":
        rows = [r for r in rows if str(r.get("Season", "")).strip() == "2023"]
    return rows


def nonempty_int(value):
    if value is None or str(value).strip() == "":
        return None
    try:
        return int(float(value))
    except ValueError:
        return None


def normalized_match(row, mode, idx, code):
    if mode == "football_data" or "HomeTeam" in row:
        date = row.get("Date", "")
        home, away = row.get("HomeTeam", ""), row.get("AwayTeam", "")
        fh, fa = nonempty_int(row.get("FTHG")), nonempty_int(row.get("FTAG"))
        hh, ha = nonempty_int(row.get("HTHG")), nonempty_int(row.get("HTAG"))
    else:
        date = row.get("Date", "")
        home, away = row.get("Home", ""), row.get("Away", "")
        fh, fa = nonempty_int(row.get("HG")), nonempty_int(row.get("AG"))
        hh = ha = None
    if not home or not away or fh is None or fa is None:
        return None
    return {
        "match_id": f"football-data.co.uk-{code}-2023-{idx}",
        "date": date,
        "home": home,
        "away": away,
        "ft_home": fh,
        "ft_away": fa,
        "ht_home": hh,
        "ht_away": ha,
        "explicit_ht": hh is not None and ha is not None,
        "season": 2023 if code == "BSA" else 2024,
        "source": "football-data.co.uk",
    }


def validate_source(spec, rows):
    if spec["column_mode"] == "football_data" or (rows and "HomeTeam" in rows[0]):
        ft_ok = sum(all(str(r.get(c, "")).strip() != "" for c in ("HomeTeam", "AwayTeam", "FTHG", "FTAG")) for r in rows)
        teams = {r.get("HomeTeam") for r in rows} | {r.get("AwayTeam") for r in rows}
    else:
        ft_ok = sum(all(str(r.get(c, "")).strip() != "" for c in ("Home", "Away", "HG", "AG")) for r in rows)
        teams = {r.get("Home") for r in rows} | {r.get("Away") for r in rows}
    teams.discard(None)
    return len(rows), len(teams), ft_ok


def main():
    if not CATALOG.exists():
        raise SystemExit("CATALOG_MISSING")
    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
    base_teams = sum(len(v.get("teams", [])) for v in catalog.values() if isinstance(v, dict))
    if base_teams != 134:
        raise SystemExit(f"SAFE_STOP_BASE_TEAMS={base_teams}, expected 134")

    additions = {}
    reports = []
    for spec in SPECS:
        if not spec["source_file"].exists():
            raise SystemExit(f"SOURCE_MISSING {spec['source_file']}")
        rows = read_rows(spec)
        raw_rows, raw_teams, ft_ok = validate_source(spec, rows)
        print(f"SOURCE {spec['key']} ROWS={raw_rows} TEAMS={raw_teams} FT_OK={ft_ok}")
        # Correct real-world validation: Turkey is 20x38=380, Belgium's
        # source includes regular season plus playoffs (312), Brazil 2023 is 380.
        expected = {"土超": (380, 20), "比甲": (312, 16), "巴甲": (380, 20)}[spec["key"]]
        if (raw_rows, raw_teams, ft_ok) != (expected[0], expected[1], expected[0]):
            raise SystemExit(f"SAFE_STOP_INVALID_SOURCE {spec['key']} got={(raw_rows, raw_teams, ft_ok)} expected={(expected[0], expected[1], expected[0])}")

        normalized = [normalized_match(r, spec["column_mode"], i, spec["code"]) for i, r in enumerate(rows)]
        normalized = [m for m in normalized if m]
        teams_out = []
        for display_name, source_name in spec["teams"].items():
            team_matches = [m for m in normalized if m["home"] == source_name or m["away"] == source_name]
            if not team_matches:
                raise SystemExit(f"SAFE_STOP_TEAM_NOT_FOUND {spec['key']} {display_name} source={source_name}")
            if any(m["ft_home"] is None or m["ft_away"] is None for m in team_matches):
                raise SystemExit(f"SAFE_STOP_FT_NULL {spec['key']} {display_name}")
            teams_out.append({
                "team_id": re.sub(r"[^a-z0-9]+", "-", display_name.lower()).strip("-"),
                "name": display_name,
                "league": spec["key"],
                "matches": team_matches,
            })
            print(f"  TEAM {display_name} MATCHES={len(team_matches)} HT_EXPLICIT={sum(m['explicit_ht'] for m in team_matches)}")
        additions[spec["key"]] = {
            "target_teams": len(teams_out), "competition_code": spec["code"],
            "updated_at": datetime.now(timezone.utc).isoformat(), "teams": teams_out, "errors": []
        }
        reports.append({"league": spec["key"], "source_rows": raw_rows, "source_teams": raw_teams, "ft_ok": ft_ok, "added_teams": len(teams_out), "added_matches": sum(len(t["matches"]) for t in teams_out)})

    merged = dict(catalog)
    for key, value in additions.items():
        if key in merged:
            raise SystemExit(f"SAFE_STOP_LEAGUE_EXISTS {key}")
        merged[key] = value
    total_teams = sum(len(v.get("teams", [])) for v in merged.values() if isinstance(v, dict))
    total_matches = sum(len(t.get("matches", [])) for v in merged.values() if isinstance(v, dict) for t in v.get("teams", []))
    if total_teams != 162:
        raise SystemExit(f"SAFE_STOP_TOTAL_TEAMS={total_teams}")
    if any(m["ft_home"] is None or m["ft_away"] is None for v in merged.values() if isinstance(v, dict) for t in v.get("teams", []) for m in t.get("matches", [])):
        raise SystemExit("SAFE_STOP_CATALOG_FT_NULL")

    report = {"base_teams": base_teams, "final_teams": total_teams, "final_matches": total_matches, "ht_policy": "null when source has no HTHG/HTAG", "leagues": reports}
    out = ROOT / "catalog" / "expansion_162_report.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp = CATALOG.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(merged, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(CATALOG)
    print(f"FINAL TOTAL_TEAMS={total_teams} MATCHES={total_matches} HT_NULL_OK")


if __name__ == "__main__":
    main()

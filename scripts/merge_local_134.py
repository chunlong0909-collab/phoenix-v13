from __future__ import annotations
import csv, json, shutil
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "catalog" / "complete_5_leagues_catalog.json"
PT = ROOT / "data" / "leagues" / "primeira_liga" / "matches.csv"
NL = ROOT / "data" / "leagues" / "eredivisie" / "matches.csv"

PT_MAP = {
    "Porto": "Porto", "Benfica": "Benfica", "Sp Lisbon": "Sporting CP",
    "Sp Braga": "Braga", "Guimaraes": "Vitoria Guimaraes",
    "Moreirense": "Moreirense", "Arouca": "Arouca", "Famalicao": "Famalicao",
    "Casa Pia": "Casa Pia", "Farense": "Farense",
}
NL_MAP = {
    "Ajax": "Ajax", "PSV Eindhoven": "PSV Eindhoven", "Feyenoord": "Feyenoord",
    "AZ Alkmaar": "AZ Alkmaar", "Twente": "Twente", "Utrecht": "Utrecht",
}

def read_csv(path):
    with path.open(newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))

def ft(v):
    if v is None or str(v).strip() == "":
        return None
    return int(float(v))

def make_team(name, league, rows, home_col, away_col, hg_col, ag_col, alias_map, source):
    source_name = next((k for k, v in alias_map.items() if v == name), None)
    selected = [r for r in rows if r.get(home_col, "").strip() == source_name or r.get(away_col, "").strip() == source_name]
    matches = []
    for i, r in enumerate(selected):
        h, a = r[home_col].strip(), r[away_col].strip()
        fth, fta = ft(r.get(hg_col)), ft(r.get(ag_col))
        if fth is None or fta is None:
            continue
        matches.append({
            "match_id": f"{source}-2024-{r.get('Date', r.get('date', i))}-{i}",
            "date": r.get("Date", r.get("date", "")),
            "home": alias_map.get(h, h), "away": alias_map.get(a, a),
            "ft_home": fth, "ft_away": fta,
            "ht_home": None, "ht_away": None, "explicit_ht": False,
            "season": 2024, "source": source,
        })
    return {"team_id": name.lower().replace(" ", "-"), "name": name,
            "league": league, "matches": matches}

def validate_source(rows, label, home, away, hg, ag, expected_rows, expected_teams):
    teams = {r.get(home, "").strip() for r in rows} | {r.get(away, "").strip() for r in rows}
    ft_ok = sum(ft(r.get(hg)) is not None and ft(r.get(ag)) is not None for r in rows)
    print(f"{label} ROWS={len(rows)} TEAMS={len(teams)} FT_OK={ft_ok}")
    if len(rows) != expected_rows or len(teams) != expected_teams or ft_ok != expected_rows:
        raise SystemExit(f"{label} source validation failed")


def main():
    if not CATALOG.exists() or not PT.exists() or not NL.exists():
        raise SystemExit("missing catalog or source file; keep 118 safe")
    base = json.loads(CATALOG.read_text(encoding="utf-8"))
    base_count = sum(len(v.get("teams", [])) for v in base.values() if isinstance(v, dict))
    if base_count != 118:
        raise SystemExit(f"BASE_TOTAL_TEAMS={base_count}; expected 118")
    pt, nl = read_csv(PT), read_csv(NL)
    validate_source(pt, "PRIMEIRA", "HomeTeam", "AwayTeam", "FTHG", "FTAG", 306, 18)
    validate_source(nl, "EREDIVISIE", "HomeTeam", "AwayTeam", "FTHG", "FTAG", 306, 18)
    pt_teams = [make_team(n, "葡超", pt, "HomeTeam", "AwayTeam", "FTHG", "FTAG", PT_MAP, "football-data.co.uk") for n in PT_MAP.values()]
    nl_teams = [make_team(n, "荷甲", nl, "HomeTeam", "AwayTeam", "FTHG", "FTAG", NL_MAP, "football-data.co.uk") for n in NL_MAP.values()]
    if any(len(t["matches"]) == 0 for t in pt_teams + nl_teams):
        raise SystemExit("one or more selected teams have no verified FT matches")
    out = json.loads(json.dumps(base))
    now = datetime.now(timezone.utc).isoformat()
    out["葡超"] = {"target_teams": 10, "competition_code": "P1", "updated_at": now, "teams": pt_teams, "errors": []}
    out["荷甲"] = {"target_teams": 6, "competition_code": "N1", "updated_at": now, "teams": nl_teams, "errors": []}
    total = sum(len(v.get("teams", [])) for v in out.values() if isinstance(v, dict))
    matches = sum(len(t.get("matches", [])) for v in out.values() if isinstance(v, dict) for t in v.get("teams", []))
    if total != 134:
        raise SystemExit(f"FINAL_TOTAL_TEAMS={total}; refusing write")
    tmp = CATALOG.with_suffix(".134.tmp.json")
    tmp.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(CATALOG)
    print(f"FINAL CATALOG TOTAL_TEAMS={total} MATCHES={matches}")

if __name__ == "__main__":
    main()

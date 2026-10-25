from __future__ import annotations

import json
import re
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "catalog" / "complete_500_leagues_catalog.json"
REPORT = ROOT / "catalog" / "expansion_474_openfootball_report.json"
RAW = ROOT / "data" / "raw" / "secondary" / "openfootball"
RAW.mkdir(parents=True, exist_ok=True)

API_TREE = "https://api.github.com/repos/openfootball/world/git/trees/master?recursive=1"
RAW_BASE = "https://raw.githubusercontent.com/openfootball/world/master/"
SEASONS = ("2021-22", "2022-23", "2023-24", "2024-25")
MEX_PATHS = {s: f"north-america/mexico/{s}_mx1.txt" for s in SEASONS}

ALIASES = {
    "cfamerica": "clubamerica", "clubamerica": "clubamerica",
    "cfmonterrey": "monterrey", "cfpachuca": "pachuca", "clubpachuca": "pachuca",
    "uanltigres": "tigresuanl",
    "atlasguadalajara": "atlas", "atleticosanluis": "atlsanluis",
    "deportivotoluca": "toluca", "deportivoguadalajara": "guadalajarachivas",
    "clubnecaxa": "necaxa", "gallosblancos": "queretaro",
    "queretarofc": "queretaro", "cfjuarez": "juarez", "fcjuarez": "juarez",
    "pueblafc": "puebla", "clubleon": "leon", "clubtijuana": "tijuana",
    "mazatlanfc": "mazatlan", "mazatlan": "mazatlan", "unampumas": "pumas",
    "pumasunam": "pumas", "santoslaguna": "santoslaguna",
}


def norm(value: str) -> str:
    value = unicodedata.normalize("NFKD", str(value or ""))
    value = "".join(c for c in value if not unicodedata.combining(c)).lower()
    value = re.sub(r"[^a-z0-9]+", "", value)
    return ALIASES.get(value, value)


def parse_txt(text: str, league: str, season: str) -> list[dict]:
    date_re = re.compile(r"^\s{2,}(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun)\s+(.+?\s+\d{4})\s*$")
    match_re = re.compile(
        r"^\s+\d{1,2}:\d{2}\s+(.+?)\s+v\s+(.+?)\s+(\d+)\s*-\s*(\d+)"
        r"(?:\s*\((\d+)\s*-\s*(\d+)\))?\s*$"
    )
    rows: list[dict] = []
    current_date = ""
    for line_no, line in enumerate(text.splitlines(), 1):
        date_match = date_re.match(line)
        if date_match:
            current_date = date_match.group(1)
            continue
        match = match_re.match(line)
        if not match:
            continue
        home, away, fh, fa, hh, ha = match.groups()
        rows.append(
            {
                "match_id": f"openfootball-{league}-{season}-{line_no}",
                "date": current_date,
                "home": home.strip(),
                "away": away.strip(),
                "ft_home": int(fh),
                "ft_away": int(fa),
                "ht_home": int(hh) if hh is not None else None,
                "ht_away": int(ha) if ha is not None else None,
                "explicit_ht": hh is not None and ha is not None,
                "season": season,
                "source": "openfootball/world",
            }
        )
    return rows


def get_tree() -> tuple[list[str], dict]:
    response = requests.get(API_TREE, headers={"User-Agent": "PhoenixOpenFootballAudit/1.0"}, timeout=45)
    response.raise_for_status()
    items = response.json().get("tree", [])
    paths = [x["path"] for x in items if x.get("type") == "blob"]
    return paths, {x["path"]: x for x in items if x.get("type") == "blob"}


def download(path: str) -> tuple[str, int]:
    target = RAW / Path(path).name
    response = requests.get(RAW_BASE + path, headers={"User-Agent": "PhoenixOpenFootballAudit/1.0"}, timeout=45)
    response.raise_for_status()
    target.write_bytes(response.content)
    return str(target.relative_to(ROOT)), len(response.content)


def main() -> None:
    data = json.loads(CATALOG.read_text(encoding="utf-8"))
    base_teams = sum(len(v.get("teams", [])) for v in data.values() if isinstance(v, dict))
    if base_teams != 444:
        raise RuntimeError(f"Expected safe 444-team baseline, found {base_teams}")

    paths, _ = get_tree()
    korea_paths = [
        p for p in paths
        if ("korea" in p.lower() or "k-league" in p.lower() or "k1" in p.lower())
        and p.endswith(".txt")
    ]
    # OpenFootball/world currently has no South Korea match TXT. Club metadata
    # is not match data and is therefore never treated as fixtures.
    k1_match_paths = [p for p in korea_paths if re.search(r"20\d\d", p)]

    source_audit = {
        "repository": "https://github.com/openfootball/world",
        "tree_checked": API_TREE,
        "K1": {"candidate_match_paths": k1_match_paths, "rows": 0, "teams": 0},
        "墨西超": {},
    }

    mexico_rows: list[dict] = []
    for season, path in MEX_PATHS.items():
        relative, size = download(path)
        text = (ROOT / relative).read_text(encoding="utf-8", errors="replace")
        rows = parse_txt(text, "墨西超", season)
        mexico_rows.extend(rows)
        source_audit["墨西超"][season] = {
            "path": path,
            "file": relative,
            "bytes": size,
            "rows": len(rows),
            "ft_invalid_rows": sum(1 for r in rows if r["ft_home"] is None or r["ft_away"] is None),
        }

    existing_names = [t.get("name", "") for block in data.values() for t in block.get("teams", [])]
    existing_keys = {norm(x) for x in existing_names}
    by_team: dict[str, list[dict]] = defaultdict(list)
    season_counts: dict[str, Counter] = defaultdict(Counter)
    display_name: dict[str, str] = {}
    for row in mexico_rows:
        for side in ("home", "away"):
            key = norm(row[side])
            by_team[key].append(row)
            season_counts[key][row["season"]] += 1
            display_name[key] = row[side]

    mexico_candidates = []
    for key, rows in by_team.items():
        # User's minimum is >=120 FT across the four seasons; require every
        # season to contribute at least one match as an additional integrity check.
        if len(rows) < 120 or any(season_counts[key][s] == 0 for s in SEASONS):
            continue
        if key in existing_keys:
            continue
        mexico_candidates.append((len(rows), display_name[key], key))
    mexico_candidates.sort(reverse=True)
    source_audit["墨西超"]["candidate_new_full4"] = [
        {"name": name, "matches": count} for count, name, _ in mexico_candidates
    ]

    # Transaction rule: do not partially add Mexico if K1 cannot supply all 12.
    selected_k1: list[str] = []
    selected_mexico = mexico_candidates[:18]
    ready = len(k1_match_paths) >= 12 and len(selected_mexico) >= 18
    report = {
        "base_teams": base_teams,
        "target_total": 474,
        "total_teams": base_teams,
        "target_reached": False,
        "added_teams": 0,
        "added": [],
        "source": "OpenFootball world / Football.TXT only",
        "source_audit": source_audit,
        "k1_candidates": len(k1_match_paths),
        "k1_selected": selected_k1,
        "mexico_candidates": len(mexico_candidates),
        "mexico_selected": [name for _, name, _ in selected_mexico],
        "ft_invalid_rows": 0,
        "new_ht_nonnull_rows": 0,
        "transaction": "commit only when K1=12 and Mexico=18; otherwise preserve 444 baseline",
        "policy": "Real FT only; no FBref; no HT estimation; no partial merge on failed target",
        "status": "ready" if ready else "blocked_keep_444",
        "notes": [
            "K1 match TXT is absent from the inspected openfootball/world tree; club metadata is not used as fixtures.",
            "Mexico files are parsed and audited, but a partial 1-team addition is not committed when the combined 30-team target fails.",
        ],
    }
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"BASE_TEAMS": base_teams, "K1_CANDIDATE_FILES": len(k1_match_paths), "MEXICO_CANDIDATES": len(mexico_candidates), "TARGET_REACHED": False, "ACTION": "KEEP_444"}, ensure_ascii=False))


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Build 3-5 season historical match caches from public OpenFootball sources.
OpenFootball normally has scores but not event-level scorers; scorers is [] unless a source provides it.
"""
from __future__ import annotations
import argparse, json, re
from datetime import datetime, timezone
from pathlib import Path
import requests

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "leagues.json"
OUT = ROOT / "data" / "history"
HEADERS = {"User-Agent": "FootballAnalysisApp/1.0"}
WORLD_TREE = "https://api.github.com/repos/openfootball/world/git/trees/master?recursive=1"
RAW_WORLD = "https://raw.githubusercontent.com/openfootball/world/master/{}"
# world repository paths that are known to exist; other leagues are discovered by configured path.
PATH_OVERRIDES = {"saudi-pro": "middle-east/saudi-arabia"}

def parse_txt(text: str, source: str, season: str) -> list[dict]:
    rows, current_date = [], None
    date_re = re.compile(r"^\s{2,}(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun)\s+([A-Z][a-z]{2})\s+(\d{1,2})(?:\s+(20\d{2}))?")
    match_re = re.compile(r"^\s{4,}(?:\d{1,2}:\d{2}\s+)?(.+?)\s+v\s+(.+?)\s+(\d+)\s*-\s*(\d+)(?:\s+\([^)]*\))?\s*$")
    months = {"Jan":1,"Feb":2,"Mar":3,"Apr":4,"May":5,"Jun":6,"Jul":7,"Aug":8,"Sep":9,"Oct":10,"Nov":11,"Dec":12}
    season_year = int(re.search(r"20\d{2}", season).group()) if re.search(r"20\d{2}", season) else datetime.now().year
    for line in text.splitlines():
        dm = date_re.match(line)
        if dm:
            mon, day, year = dm.group(1), int(dm.group(2)), int(dm.group(3) or season_year)
            current_date = f"{year:04d}-{months[mon]:02d}-{day:02d}"
            continue
        mm = match_re.match(line)
        if mm and current_date:
            rows.append({"date": current_date, "season": season, "home_team": mm.group(1).strip(),
                         "away_team": mm.group(2).strip(), "score": [int(mm.group(3)), int(mm.group(4))],
                         "scorers": [], "source": f"openfootball:{source}"})
    return rows

def discover_files() -> list[str]:
    r = requests.get(WORLD_TREE, headers=HEADERS, timeout=30); r.raise_for_status()
    return [x["path"] for x in r.json().get("tree", []) if x.get("type") == "blob" and x["path"].endswith(".txt")]

def collect_one(league: dict, all_paths: list[str], seasons: int) -> dict:
    lid = league["id"]
    hints = PATH_OVERRIDES.get(lid) or league.get("openfootball_paths", [""])[0]
    candidates = [p for p in all_paths if hints.lower() in p.lower() and re.search(r"20\d{2}", p)]
    # newest distinct season-like files, capped to the requested history depth
    candidates = sorted(set(candidates), reverse=True)[:seasons]
    rows = []
    for path in candidates:
        try:
            r = requests.get(RAW_WORLD.format(path), headers=HEADERS, timeout=30)
            if r.ok: rows.extend(parse_txt(r.text, path, path.split("/")[-1].split("_")[0]))
        except requests.RequestException:
            continue
    rows.sort(key=lambda x: (x["date"], x["home_team"], x["away_team"]))
    payload = {"league": lid, "name_zh": league["name_zh"], "updated_at": datetime.now(timezone.utc).isoformat(),
               "dataSource": "OpenFootball/world", "seasons_requested": seasons, "season_files": candidates,
               "scorers_available": False, "matches": rows,
               "note": "OpenFootball比分資料通常不含逐球射手；scorers留空，避免虛構資料。"}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"{lid}_history.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(lid, len(rows), candidates)
    return payload

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--leagues", default="all"); ap.add_argument("--seasons", type=int, default=5)
    args = ap.parse_args(); cfg = json.loads(CONFIG.read_text(encoding="utf-8"))["leagues"]
    paths = discover_files(); wanted = {x.strip() for x in args.leagues.split(",")} if args.leagues != "all" else None
    for league in cfg:
        if wanted is None or league["id"] in wanted: collect_one(league, paths, max(3, min(args.seasons, 5)))

if __name__ == "__main__": main()

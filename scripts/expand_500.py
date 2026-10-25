from __future__ import annotations
import csv, json, re, unicodedata
from collections import Counter, defaultdict
from datetime import datetime
from difflib import SequenceMatcher
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
CATALOG_IN = ROOT / "catalog" / "complete_5_leagues_catalog.json"
CATALOG_OUT = ROOT / "catalog" / "complete_world_500_catalog.json"
REPORT_OUT = ROOT / "catalog" / "expansion_500_report.json"

# These are the official Football-Data extra-league aggregate CSVs. They
# contain historical seasons and FT scores (HG/AG); HT is intentionally not
# inferred from them.
SOURCES = {
    "阿甲": {
        "target": 28, "code": "ARG", "url": "https://football-data.co.uk/new/ARG.csv",
        "seasons": {"2021": "2021", "2022": "2022", "2023": "2023", "2024": "2024"},
    },
    "巴甲": {
        "target": 20, "code": "BRA", "url": "https://football-data.co.uk/new/BRA.csv",
        "seasons": {"2021": "2021", "2022": "2022", "2023": "2023", "2024": "2024"},
    },
    "美職MLS": {
        "target": 29, "code": "MLS", "url": "https://football-data.co.uk/new/USA.csv",
        "seasons": {"2021": "2021", "2022": "2022", "2023": "2023", "2024": "2024"},
    },
    "墨西超": {
        "target": 18, "code": "MEX", "url": "https://football-data.co.uk/new/MEX.csv",
        "seasons": {"2021-22": "2021/2022", "2022-23": "2022/2023", "2023-24": "2023/2024", "2024-25": "2024/2025"},
    },
    "J1聯賽": {
        "target": 20, "code": "JPN", "url": "https://football-data.co.uk/new/JPN.csv",
        "seasons": {"2021": "2021", "2022": "2022", "2023": "2023", "2024": "2024"},
    },
}

# Minimum completed league matches per team in each season. Partial/current
# season files are not accepted as a complete four-season source.
MIN_PER_SEASON = {
    "阿甲": {"2021": 30, "2022": 30, "2023": 30, "2024": 27},
    "巴甲": {"2021": 38, "2022": 38, "2023": 38, "2024": 38},
    "美職MLS": {"2021": 34, "2022": 34, "2023": 34, "2024": 34},
    "墨西超": {"2021-22": 34, "2022-23": 34, "2023-24": 34, "2024-25": 34},
    "J1聯賽": {"2021": 38, "2022": 34, "2023": 34, "2024": 38},
}

ALIASES = {
    "flamengorj": "flamengo", "atleticomg": "atleticomineiro", "atleticopr": "athleticoparanaense",
    "bragantino": "redbullbragantino", "gremio": "gremio", "saopaulo": "saopaulo",
    "vasco": "vascodagama", "urawareddiamonds": "urawaredds", "urawaredds": "urawaredds",
    "yokohamafmarinos": "yokohamamarinos", "sanfreccehiroshima": "sanfreccehiroshima",
    "fc東京": "fctokyo", "tokyoverdy": "tokyoverdy", "machidazelvia": "machidazelvia",
}

def norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", str(s or ""))
    s = "".join(c for c in s if not unicodedata.combining(c)).lower()
    s = re.sub(r"[^a-z0-9]+", "", s)
    for suffix in ("footballclub", "football", "fc", "cf", "sc", "club"):
        if s.endswith(suffix) and len(s) > len(suffix) + 3:
            s = s[:-len(suffix)]
    return ALIASES.get(s, s)

def similar(a: str, b: str) -> float:
    na, nb = norm(a), norm(b)
    if not na or not nb: return 0.0
    if na == nb or na in nb or nb in na: return 1.0
    return SequenceMatcher(None, na, nb).ratio()

def fetch(url: str, path: Path) -> None:
    if path.exists() and path.stat().st_size > 1000:
        return
    req = Request(url, headers={"User-Agent": "Mozilla/5.0 (compatible; PhoenixDataAudit/1.0)"})
    with urlopen(req, timeout=45) as r:
        data = r.read()
    if len(data) <= 1000:
        raise RuntimeError(f"source too small: {url}")
    path.write_bytes(data)

def parse_csv(path: Path, league: str, season: str, source_season: str | None = None):
    text = path.read_text(encoding="utf-8-sig", errors="replace")
    rows = list(csv.DictReader(text.splitlines()))
    out=[]; invalid=0
    for idx, r in enumerate(rows, 1):
        # Football-Data aggregate files use Season/Home/Away/HG/AG;
        # archived cache files use Date/Team 1/Team 2/FT. Support both.
        raw_season=(r.get("Season") or "").strip()
        if raw_season and raw_season != (source_season or season): continue
        home=(r.get("Home") or r.get("Team 1") or r.get("HomeTeam") or "").strip()
        away=(r.get("Away") or r.get("Team 2") or r.get("AwayTeam") or "").strip()
        ft=(r.get("FT") or "").strip()
        if not ft and (r.get("HG") or "").strip() != "" and (r.get("AG") or "").strip() != "":
            ft=f"{r.get('HG')}-{r.get('AG')}"
        m=re.fullmatch(r"(\d+)\s*[-:]\s*(\d+)", ft)
        if not home or not away or not m:
            invalid += 1; continue
        date=(r.get("Date") or "").strip()
        out.append({
            "match_id": f"football-data-cache-{league}-{season}-{idx}",
            "date": date, "home": home, "away": away,
            "ft_home": int(m.group(1)), "ft_away": int(m.group(2)),
            "ht_home": None, "ht_away": None, "explicit_ht": False,
            "season": season, "source": "football-data.co.uk",
        })
    return out, invalid

def existing_team_names(data):
    return [t.get("name", "") for block in data.values() for t in block.get("teams", [])]

def already_present(name, existing):
    return any(similar(name, x) >= 0.90 for x in existing)

def slug(league, name):
    return re.sub(r"[^a-z0-9]+", "-", f"{league}-{name}".lower()).strip("-")

def main():
    data=json.loads(CATALOG_IN.read_text(encoding="utf-8"))
    original_team_count=sum(len(v.get("teams", [])) for v in data.values())
    existing=existing_team_names(data)
    source_audit={}; parsed={}
    for league, spec in SOURCES.items():
        source_audit[league]={"source_type":"football-data.co.uk official aggregate CSV", "url":spec["url"], "seasons":{}}
        parsed[league]={}
        fn=f"{spec['code']}_all_seasons.csv"
        path=RAW/fn
        fetch(spec["url"],path)
        for season, source_season in spec["seasons"].items():
            rows,bad=parse_csv(path,league,season,source_season)
            parsed[league][season]=rows
            source_audit[league]["seasons"][season]={"source_season":source_season,"file":f"data/raw/{fn}","rows":len(rows),"ft_invalid_rows":bad,"bytes":path.stat().st_size}
    added=[]; skipped={}; selected_by_league={}
    for league,spec in SOURCES.items():
        by_team=defaultdict(list); seasons_by_team=defaultdict(set)
        for season, rows in parsed[league].items():
            for row in rows:
                by_team[row["home"]].append(row); by_team[row["away"]].append(row)
                seasons_by_team[row["home"]].add(season); seasons_by_team[row["away"]].add(season)
        candidates=[]
        for source_name, rows in by_team.items():
            if len(seasons_by_team[source_name]) != 4: continue
            if any(sum(1 for r in rows if r["season"]==s) < MIN_PER_SEASON[league][s] for s in parsed[league]): continue
            if already_present(source_name, existing): continue
            candidates.append((len(rows), source_name))
        candidates.sort(reverse=True)
        selected=[name for _,name in candidates[:spec["target"]]]
        selected_by_league[league]=selected
        skipped[league]={"available_new_full4":len(candidates),"target":spec["target"],"not_added_due_to_cap":max(0,len(candidates)-len(selected)),"minimum_matches_per_team_by_season":MIN_PER_SEASON[league],"reason_if_zero":"No team met all four complete-season FT thresholds; partial/current-season rows were excluded."}
        if not selected: continue
        block=data.setdefault(league,{"target_teams":spec["target"],"competition_code":spec["code"],"updated_at":datetime.utcnow().isoformat()+"+00:00","teams":[],"errors":[]})
        for source_name in selected:
            rows=sorted(by_team[source_name],key=lambda r:r["date"])
            team={"team_id":slug(league,source_name),"name":source_name,"league":league,"matches":rows}
            block["teams"].append(team); existing.append(source_name); added.append({"league":league,"name":source_name,"matches":len(rows),"seasons":sorted({r['season'] for r in rows})})
    total=sum(len(v.get("teams", [])) for v in data.values())
    report={"base_teams":original_team_count,"total_teams":total,"added_teams":len(added),"target_total":500,"target_reached":total>=500,"ft_invalid_rows":sum(x["ft_invalid_rows"] for a in source_audit.values() for x in a["seasons"].values()),"new_ht_nonnull_rows":0,"source_audit":source_audit,"selected_by_league":selected_by_league,"skipped_or_limited":skipped,"added":added,"policy":"Real FT only; HT remains null; no score estimation. Teams must appear in all four source seasons and meet the configured completed-season FT threshold. Partial/current-season files are excluded."}
    CATALOG_OUT.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding="utf-8")
    REPORT_OUT.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps({"BASE_TEAMS":original_team_count,"ADDED_TEAMS":len(added),"TOTAL_TEAMS":total,"TARGET_REACHED":total>=500,"FT_INVALID_ROWS":report["ft_invalid_rows"],"LEAGUES":{k:len(v) for k,v in selected_by_league.items()}},ensure_ascii=False,indent=2))

if __name__ == "__main__": main()

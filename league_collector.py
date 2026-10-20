#!/usr/bin/env python3
"""零成本足球資料收集器。

來源優先順序：Football-Data.co.uk（有比分／部分有角球）及 OpenFootball/world
（公開歷史比分），再用 TheSportsDB 的免費測試接口補充球隊及球員資料。
所有失敗都會寫入 metadata.json，絕不以空資料冒充成功。
"""
from __future__ import annotations
import argparse, json, re, time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import pandas as pd
import requests

ROOT = Path(__file__).resolve().parent
CONFIG = ROOT / "leagues.json"
DATA = ROOT / "data" / "leagues"
WORLD_TREE = "https://api.github.com/repos/openfootball/world/git/trees/master?recursive=1"
ENGLAND_TREE = "https://api.github.com/repos/openfootball/england/git/trees/master?recursive=1"
RAW = "https://raw.githubusercontent.com/{repo}/master/{path}"
SPORTSDB_KEYS = ()  # 已放棄TheSportsDB，不再作球員主力或後備。
ESPN_LEAGUES = {
    "epl": "eng.1", "championship": "eng.2", "laliga": "esp.1", "laliga2": "esp.2",
    "bundesliga": "ger.1", "bundesliga2": "ger.2", "serie-a": "ita.1", "ligue1": "fra.1",
    "ligue2": "fra.2", "eredivisie": "ned.1", "eerste": "ned.2", "a-league": "aus.1",
    "j1": "jpn.1", "j2": "jpn.2", "k1": "kor.1", "k2": "kor.2", "liga-mx": "mex.1",
    "serie-b": "bra.2", "argentina-primera": "arg.1", "saudi-pro": "sau.1",
    "eliteserien": "nor.1", "veikkausliiga": "fin.1", "russian-prem": "rus.1",
    "thai-league1": "tha.1", "austrian-bundesliga": "aut.1", "danish-superliga": "den.1",
}
# ESPN某些roster回應曾把其他隊球員混入；先以球員ID及隊伍ID雙重防線排除。
ESPN_TEAM_EXCLUSIONS = {"epl": {"359": {"218522", "231859"}}}
HEADERS = {"User-Agent": "FootballResearchApp/1.0 (public-data research)"}


def get_json(url: str, params: dict | None = None) -> dict:
    r = requests.get(url, params=params, headers=HEADERS, timeout=6)
    r.raise_for_status()
    return r.json()


def sportsdb_json(endpoint: str, params: dict | None = None) -> dict:
    """依次嘗試指定免費 key；key 被停用時不破壞舊快取。"""
    for key in SPORTSDB_KEYS:
        try:
            r = requests.get(f"https://www.thesportsdb.com/api/v1/json/{key}/{endpoint}",
                             params=params, headers=HEADERS, timeout=6)
            if r.status_code == 200:
                return r.json()
        except Exception:
            continue
    return {}


def norm(s: Any) -> str:
    return re.sub(r"[^a-z0-9]", "", str(s or "").lower())


def espn_team(league_id: str, name: str) -> dict:
    slug = ESPN_LEAGUES.get(league_id)
    if not slug:
        return {}
    try:
        payload = get_json(f"https://site.api.espn.com/apis/site/v2/sports/soccer/{slug}/teams")
        teams = []
        for sport in payload.get("sports", []):
            for league in sport.get("leagues", []):
                teams.extend(x.get("team", x) for x in league.get("teams", []))
        wanted = norm(name)
        ranked = sorted(teams, key=lambda x: (wanted not in norm(x.get("displayName") or x.get("name")),
                                               len(norm(x.get("displayName") or x.get("name")))))
        return ranked[0] if ranked and (wanted in norm(ranked[0].get("displayName") or ranked[0].get("name"))) else {}
    except Exception:
        return {}


def espn_players(league_id: str, team_id: str) -> list[dict]:
    slug = ESPN_LEAGUES.get(league_id)
    if not slug or not team_id:
        return []
    try:
        payload = get_json(f"https://site.api.espn.com/apis/site/v2/sports/soccer/{slug}/teams/{team_id}/roster")
        out = []
        for entry in payload.get("athletes", []):
            player_id = str(entry.get("id", ""))
            default_ref = str((entry.get("defaultTeam") or {}).get("$ref", ""))
            ref_team = re.search(r"/teams/(\d+)", default_ref)
            if ref_team and ref_team.group(1) != str(int(float(team_id))):
                continue
            if player_id in ESPN_TEAM_EXCLUSIONS.get(league_id, {}).get(str(int(float(team_id))), set()):
                continue
            position = (entry.get("position") or {}).get("abbreviation", "")
            position = {"G": "GK", "D": "DF", "M": "MF", "F": "FW"}.get(position, position)
            if position not in {"GK", "DF", "MF", "FW", "DM", "AM"}:
                continue
            citizenship = entry.get("citizenshipCountry") or {}
            country = citizenship.get("displayName", "") if isinstance(citizenship, dict) else str(citizenship)
            country = country or (entry.get("flag") or {}).get("alt", "")
            out.append({"idPlayer": player_id, "strPlayer": entry.get("displayName") or entry.get("fullName", ""),
                        "strPosition": position, "strNationality": country,
                        "dateBorn": entry.get("dateOfBirth", ""), "age": entry.get("age", ""),
                        "strThumb": (entry.get("headshot") or {}).get("href", "")})
        return out
    except Exception:
        return []


def season_codes(n=8):
    now = datetime.now().year
    # football-data uses the ending two years, e.g. 2526 for 2025/26.
    return [f"{(y-1)%100:02d}{y%100:02d}" for y in range(now, now-n, -1)]


def load_config():
    return json.loads(CONFIG.read_text(encoding="utf-8"))


def read_fd(league: dict) -> pd.DataFrame:
    rows = []
    code = league.get("fd_code")
    if not code:
        return pd.DataFrame()
    for season in season_codes():
        url = f"https://www.football-data.co.uk/mmz4281/{season}/{code}.csv"
        try:
            r = requests.get(url, headers=HEADERS, timeout=25)
            if r.status_code != 200 or len(r.content) < 80:
                continue
            df = pd.read_csv(__import__("io").BytesIO(r.content), encoding="latin1")
            required = {"HomeTeam", "AwayTeam", "FTHG", "FTAG"}
            if not required.issubset(df.columns):
                continue
            out = pd.DataFrame({
                "date": pd.to_datetime(df.get("Date"), dayfirst=True, errors="coerce"),
                "season": season,
                "home_team": df["HomeTeam"].astype(str).str.strip(),
                "away_team": df["AwayTeam"].astype(str).str.strip(),
                "home_goals": pd.to_numeric(df["FTHG"], errors="coerce"),
                "away_goals": pd.to_numeric(df["FTAG"], errors="coerce"),
                "home_corners": pd.to_numeric(df["HC"], errors="coerce") if "HC" in df else pd.NA,
                "away_corners": pd.to_numeric(df["AC"], errors="coerce") if "AC" in df else pd.NA,
                "source": "football-data.co.uk",
            })
            rows.append(out.dropna(subset=["home_goals", "away_goals"]))
        except Exception:
            continue
    return pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()


def tree_for(league: dict) -> tuple[str, list[str]]:
    paths = league.get("openfootball_paths", [])
    if any(p.startswith("europe/england") for p in paths):
        repo, url = "openfootball/england", ENGLAND_TREE
    else:
        repo, url = "openfootball/world", WORLD_TREE
    try:
        tree = get_json(url).get("tree", [])
        return repo, [x["path"] for x in tree if x.get("type") == "blob"]
    except Exception:
        return repo, []


def parse_openfootball(text: str, season_name: str, source_path: str) -> pd.DataFrame:
    rows = []
    year_default = int(re.search(r"(20\d{2})", season_name).group(1)) if re.search(r"(20\d{2})", season_name) else datetime.now().year
    current_date = None
    # Match lines have a flexible time prefix and a v separator.
    pat = re.compile(r"^\s*(?:\d{1,2}:\d{2}\s+)?(.+?)\s+v\s+(.+?)\s+(\d+)\s*-\s*(\d+)(?:\s|$)")
    for raw in text.splitlines():
        line = raw.rstrip()
        dm = re.match(r"^\s{2,}(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun)\s+([A-Z][a-z]{2})\s+(\d{1,2})(?:\s+(20\d{2}))?", line)
        if dm:
            mon, day, year = dm.group(1), int(dm.group(2)), int(dm.group(3) or year_default)
            current_date = pd.to_datetime(f"{day} {mon} {year}", format="%d %b %Y", errors="coerce")
            continue
        m = pat.match(line)
        if not m or current_date is None:
            continue
        rows.append({"date": current_date, "season": season_name, "home_team": m.group(1).strip(),
                     "away_team": m.group(2).strip(), "home_goals": int(m.group(3)),
                     "away_goals": int(m.group(4)), "home_corners": pd.NA,
                     "away_corners": pd.NA, "source": f"openfootball ({source_path})"})
    return pd.DataFrame(rows)


def read_openfootball(league: dict) -> pd.DataFrame:
    repo, paths = tree_for(league)
    fragments = []
    hints = [p.lower().split("/")[-1] for p in league.get("openfootball_paths", [])]
    # Take the newest available season files matching the configured country path.
    candidates = []
    for p in paths:
        low = p.lower()
        if not low.endswith(".txt") or "/" not in low:
            continue
        if not any(part in low for part in hints):
            continue
        if not re.search(r"20\d{2}", low):
            continue
        # Avoid README/notes and club lists.
        if any(x in low for x in ("readme", "notes", "clubs", "conf")):
            continue
        candidates.append(p)
    candidates = sorted(candidates, reverse=True)[:10]
    for path in candidates:
        try:
            r = requests.get(RAW.format(repo=repo, path=path), headers=HEADERS, timeout=25)
            if r.ok:
                part = parse_openfootball(r.text, path.split("/")[0], path)
                if not part.empty:
                    fragments.append(part)
        except Exception:
            continue
    return pd.concat(fragments, ignore_index=True) if fragments else pd.DataFrame()


def sportsdb_team(name: str, women: bool = False) -> dict:
    try:
        teams = sportsdb_json("searchteams.php", {"t": name}).get("teams") or []
        target = norm(name)
        ranked = sorted(teams, key=lambda x: (norm(x.get("strTeam")) != target, "women" in norm(x.get("strTeam"))))
        for team in ranked:
            if women and "women" not in norm(team.get("strTeam")) and "ladies" not in norm(team.get("strTeam")):
                continue
            if not women and ("women" in norm(team.get("strTeam")) or "ladies" in norm(team.get("strTeam"))):
                continue
            return team
    except Exception:
        pass
    return {}


def collect_players(teams: pd.DataFrame, women: bool, league_id: str) -> pd.DataFrame:
    rows = []
    for team in teams.to_dict("records"):
        # ESPN 是球員唯一主力來源；無結果時交由防覆蓋邏輯保留舊檔。
        players = espn_players(league_id, str(team.get("espn_team_id", "")))
        team_id = str(team.get("team_id", ""))
        for p in players:
            source = "ESPN" if team.get("espn_team_id") and p.get("idPlayer") else "TheSportsDB"
            rows.append({"team_id": team_id, "team_name": team["team_name"],
                         "idPlayer": p.get("idPlayer", ""), "player_name": p.get("strPlayer", ""),
                         "strPlayer": p.get("strPlayer", ""), "position": p.get("strPosition", ""),
                         "strPosition": p.get("strPosition", ""), "age": p.get("age", p.get("dateBorn", "")),
                         "dateBorn": p.get("dateBorn", ""), "nationality": p.get("strNationality", ""),
                         "strNationality": p.get("strNationality", ""), "strThumb": p.get("strThumb", ""),
                         "market_value": p.get("strWage", ""), "source": source})
        time.sleep(0.35)
    return pd.DataFrame(rows, columns=["team_id","team_name","idPlayer","player_name","strPlayer",
                                       "position","strPosition","age","dateBorn","nationality",
                                       "strNationality","strThumb","market_value","source"])


def collect_one(league: dict, max_matches=60, with_players=True) -> dict:
    league_id = league["id"]
    outdir = DATA / league_id
    outdir.mkdir(parents=True, exist_ok=True)
    matches = read_fd(league) if league.get("provider") == "football-data" else read_openfootball(league)
    if matches.empty and league.get("provider") != "football-data":
        matches = read_fd(league)
    if not matches.empty:
        matches["date"] = pd.to_datetime(matches["date"], errors="coerce")
        matches = matches.sort_values("date").drop_duplicates(subset=["date","home_team","away_team"], keep="last")
        # max_matches 是每隊的歷史上限；API 再按指定球隊截取近60場。
        home_part = matches.groupby("home_team", group_keys=False).tail(max_matches)
        away_part = matches.groupby("away_team", group_keys=False).tail(max_matches)
        matches = pd.concat([home_part, away_part]).drop_duplicates(subset=["date","home_team","away_team"])
        team_names = sorted(set(matches.home_team) | set(matches.away_team))
    else:
        team_names = []
    teams = pd.DataFrame({"team_name": team_names})
    teams["team_id"] = ""
    teams["country"] = ""
    teams["stadium"] = ""
    teams["crest_url"] = ""
    teams["espn_team_id"] = ""
    teams["source"] = "openfootball/football-data"
    for i, name in enumerate(team_names):
        e = espn_team(league_id, name)
        if e:
            teams.loc[i, "espn_team_id"] = e.get("id", "")
            teams.loc[i, "crest_url"] = (e.get("logos") or [{}])[0].get("href", "")
        time.sleep(0.35)
    stamp = datetime.now(timezone.utc).isoformat()
    if with_players:
        players = collect_players(teams, "women" in league["id"] or "femenina" in league["id"] or "toppserien" in league["id"], league_id)
    else:
        old_players = outdir / "players.csv"
        players = pd.read_csv(old_players).fillna("") if old_players.exists() else pd.DataFrame()
    old_players_path = outdir / "players.csv"
    protected = False
    new_player_count = len(players)
    if with_players and len(players) < 15 and old_players_path.exists():
        players = pd.read_csv(old_players_path).fillna("")
        protected = True
        with (DATA / "update.log").open("a", encoding="utf-8") as log:
            log.write(json.dumps({"time": stamp, "league_id": league_id, "event": "players_update_rejected",
                                  "new_count": new_player_count, "reason": "new roster fewer than 15; old cache retained"}, ensure_ascii=False) + "\n")
    if not teams.empty:
        teams["lastUpdated"] = stamp
        teams["dataSource"] = teams.get("source", "ESPN")
    if not players.empty:
        players["lastUpdated"] = stamp if not protected else players.get("lastUpdated", stamp)
        players["dataSource"] = players.get("source", "ESPN")
    matches.to_csv(outdir / "matches.csv", index=False, encoding="utf-8-sig")
    teams.to_csv(outdir / "teams.csv", index=False, encoding="utf-8-sig")
    players.to_csv(outdir / "players.csv", index=False, encoding="utf-8-sig")
    # JSON 是接口交換格式；CSV 保留作可人工檢查及再匯入的原始快取。
    matches.to_json(outdir / "matches.json", orient="records", force_ascii=False, date_format="iso")
    teams.to_json(outdir / "teams.json", orient="records", force_ascii=False)
    players.to_json(outdir / "players.json", orient="records", force_ascii=False)
    # 保留使用者要求的扁平路徑，並同時保留現有 data/leagues/<id>/ 結構。
    for filename, frame in ((f"{league_id}_teams.json", teams), (f"{league_id}_players.json", players),
                            (f"{league_id}_matches.json", matches)):
        (DATA.parent / filename).write_text(frame.to_json(orient="records", force_ascii=False, date_format="iso"), encoding="utf-8")
    corner_count = int(matches[["home_corners","away_corners"]].notna().all(axis=1).sum()) if not matches.empty else 0
    metadata = {"league_id": league_id, "name_zh": league["name_zh"], "updated_at": stamp,
                "sources": sorted(set(matches.source.astype(str))) if not matches.empty else [],
                "teams": len(teams), "players": len(players), "matches": len(matches), "corner_matches": corner_count,
                "quality": "高" if len(matches) >= 10 and len(teams) >= 4 else "樣本不足", "dataSource": "ESPN／football-data／openfootball",
                "lastUpdated": stamp, "players_update_protected": protected, "errors": []}
    (outdir / "metadata.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    return metadata


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--leagues", default="epl,a-league,j1,k1", help="逗號分隔ID；用 all 更新全部設定")
    ap.add_argument("--max-matches", type=int, default=60)
    ap.add_argument("--with-players", action="store_true", help="每週球員更新時使用；每日比分更新可省略")
    args = ap.parse_args()
    config = load_config()["leagues"]
    wanted = {x["id"] for x in config} if args.leagues == "all" else set(args.leagues.split(","))
    results = []
    for league in config:
        if league["id"] not in wanted:
            continue
        print(f"收集 {league['name_zh']} ({league['id']}) ...", flush=True)
        try:
            result = collect_one(league, args.max_matches, args.with_players)
        except Exception as exc:
            result = {"league_id": league["id"], "name_zh": league["name_zh"], "quality": "失敗", "errors": [str(exc)]}
        results.append(result)
        print(json.dumps(result, ensure_ascii=False), flush=True)
    (DATA / "index.json").parent.mkdir(parents=True, exist_ok=True)
    (DATA / "index.json").write_text(json.dumps({"updated_at": datetime.now(timezone.utc).isoformat(), "leagues": results}, ensure_ascii=False, indent=2), encoding="utf-8")

if __name__ == "__main__":
    main()

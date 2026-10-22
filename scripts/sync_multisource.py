#!/usr/bin/env python3
"""多來源足球資料同步器。

來源優先級：
1) football-data.co.uk：有比分及部分真實 HC/AC；
2) ESPN 公開 scoreboard/teams/roster：補充指定年度的比分、球隊及球員；
3) OpenFootball：ESPN 無端點時補充公開歷史比分。

所有來源分開標記；缺少角球時保留 NULL，絕不以 0 冒充真實角球。
輸出：data/leagues/<id>/{matches,teams,players}.csv，以及 data/multisource_football.db
"""
from __future__ import annotations
import argparse, concurrent.futures, io, json, re, sqlite3, time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import pandas as pd
import requests

try:
    from league_collector import read_openfootball
except Exception:
    read_openfootball = None

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "leagues.json"
DATA = ROOT / "data" / "leagues"
DB = ROOT / "data" / "multisource_football.db"
HEADERS = {"User-Agent": "FootballResearchApp/2.0 (multi-source public data sync)"}
ESPN = {
    "epl":"eng.1", "championship":"eng.2", "laliga":"esp.1", "laliga2":"esp.2",
    "bundesliga":"ger.1", "bundesliga2":"ger.2", "ligue2":"fra.2", "eredivisie":"ned.1",
    "eerste":"ned.2", "scottish-prem":"sco.1", "austrian-bundesliga":"aut.1",
    "danish-superliga":"den.1", "a-league":"aus.1", "j1":"jpn.1", "k1":"kor.1",
    "k2":"kor.2", "liga-mx":"mex.1", "expansion-mx":"mex.2", "serie-b":"bra.2",
    "argentina-primera":"arg.1", "saudi-pro":"sau.1", "eliteserien":"nor.1",
    "veikkausliiga":"fin.1", "russian-prem":"rus.1", "thai-league1":"tha.1",
    "a-league-women":"aus.w", "australia-cup":"aus.cup", "qatar-stars":"qat.1",
    "uae-pro":"are.1", "serie-a":"bra.1", "uruguay-primera":"uru.1",
    "toppserien":"nor.w", "libertadores-femenina":"conmebol.libertadores-femenina",
}
SUPPORTED_FD = {"epl","championship","laliga","laliga2","bundesliga","bundesliga2","ligue2","eredivisie","scottish-prem","serie-a"}
SEASONS = [2023, 2024, 2025]


def get_json(url: str, params: dict[str, Any] | None = None, timeout=30) -> dict:
    r = requests.get(url, params=params, headers=HEADERS, timeout=timeout)
    if r.status_code != 200:
        return {"_status": r.status_code, "_url": r.url}
    try: return r.json()
    except Exception: return {"_status": r.status_code, "_url": r.url}


def read_football_data(league: dict) -> pd.DataFrame:
    code = league.get("fd_code")
    if not code or league.get("id") not in SUPPORTED_FD: return pd.DataFrame()
    out = []
    for y in SEASONS:
        code_season = f"{str(y)[-2:]}{str(y+1)[-2:]}"
        url = f"https://www.football-data.co.uk/mmz4281/{code_season}/{code}.csv"
        try:
            r = requests.get(url, headers=HEADERS, timeout=30)
            if r.status_code != 200 or len(r.content) < 80: continue
            d = pd.read_csv(io.BytesIO(r.content), encoding="latin1")
            if not {"HomeTeam","AwayTeam","FTHG","FTAG"}.issubset(d.columns): continue
            out.append(pd.DataFrame({
                "fixture_id": "fd-" + d.index.astype(str), "date": pd.to_datetime(d.get("Date"), dayfirst=True, errors="coerce"),
                "season": str(y), "home_team": d.HomeTeam.astype(str).str.strip(), "away_team": d.AwayTeam.astype(str).str.strip(),
                "home_goals": pd.to_numeric(d.FTHG, errors="coerce"), "away_goals": pd.to_numeric(d.FTAG, errors="coerce"),
                "home_corners": pd.to_numeric(d.HC, errors="coerce") if "HC" in d else pd.NA,
                "away_corners": pd.to_numeric(d.AC, errors="coerce") if "AC" in d else pd.NA,
                "source": "football-data.co.uk",
            }).dropna(subset=["home_goals","away_goals"]))
        except Exception: continue
    return pd.concat(out, ignore_index=True) if out else pd.DataFrame()


def read_espn(league_id: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    slug = ESPN.get(league_id)
    if not slug or slug.startswith("conmebol"): return pd.DataFrame(), pd.DataFrame()
    fixtures, team_rows = [], {}
    for year in SEASONS:
        j = get_json(f"https://site.api.espn.com/apis/site/v2/sports/soccer/{slug}/scoreboard", {"dates": str(year), "limit": 1000})
        for ev in j.get("events", []):
            comp = (ev.get("competitions") or [{}])[0]
            teams = comp.get("competitors") or []
            if len(teams) < 2: continue
            home = next((x for x in teams if x.get("homeAway") == "home"), teams[0])
            away = next((x for x in teams if x.get("homeAway") == "away"), teams[1])
            hs, aws = home.get("score"), away.get("score")
            if hs in (None, "") or aws in (None, ""): continue
            ht, at = home.get("team") or {}, away.get("team") or {}
            for t, side in [(ht,"home"),(at,"away")]:
                if t.get("id"): team_rows[t["id"]] = {"team_id": str(t.get("id")), "team_name": t.get("displayName") or t.get("name", ""), "slug": t.get("slug", ""), "source": "ESPN"}
            fixtures.append({"fixture_id": str(ev.get("id")), "date": ev.get("date"), "season": str(year),
                "home_team": ht.get("displayName") or ht.get("name", ""), "away_team": at.get("displayName") or at.get("name", ""),
                "home_goals": float(hs), "away_goals": float(aws), "home_corners": pd.NA, "away_corners": pd.NA, "source": "ESPN scoreboard"})
    return pd.DataFrame(fixtures), pd.DataFrame(team_rows.values())


def read_rosters(league_id: str, teams: pd.DataFrame) -> pd.DataFrame:
    slug = ESPN.get(league_id)
    if not slug or teams.empty: return pd.DataFrame()
    rows=[]
    for t in teams.to_dict("records"):
        j=get_json(f"https://site.api.espn.com/apis/site/v2/sports/soccer/{slug}/teams/{t['team_id']}/roster")
        for p in j.get("athletes",[]):
            pos=(p.get("position") or {}).get("abbreviation", "")
            rows.append({"team_id":t["team_id"],"team_name":t["team_name"],"player_id":str(p.get("id","")),
                         "player_name":p.get("displayName") or p.get("fullName",""),"position":pos,
                         "date_born":p.get("dateOfBirth",""),"nationality":(p.get("citizenshipCountry") or {}).get("displayName","") if isinstance(p.get("citizenshipCountry"),dict) else "",
                         "source":"ESPN roster","season":"2025"})
        time.sleep(0.12)
    return pd.DataFrame(rows)


def read_existing_cache(league_id: str) -> pd.DataFrame:
    path = DATA / league_id / "matches.csv"
    if not path.exists(): return pd.DataFrame()
    try:
        d = pd.read_csv(path)
        required = {"home_team", "away_team", "home_goals", "away_goals"}
        if not required.issubset(d.columns): return pd.DataFrame()
        for c in ["fixture_id", "date", "season", "home_corners", "away_corners", "source"]:
            if c not in d.columns: d[c] = pd.NA
        d["fixture_id"] = d["fixture_id"].fillna("cache-" + d.index.astype(str))
        d["source"] = d["source"].fillna("existing local cache")
        return d[["fixture_id", "date", "season", "home_team", "away_team", "home_goals", "away_goals", "home_corners", "away_corners", "source"]]
    except Exception:
        return pd.DataFrame()


def init_db():
    DB.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB, timeout=30) as c:
        c.execute("PRAGMA journal_mode=WAL")
        c.execute("CREATE TABLE IF NOT EXISTS fixtures (league_id TEXT, fixture_id TEXT, date TEXT, season TEXT, home_team TEXT, away_team TEXT, home_goals REAL, away_goals REAL, home_corners REAL, away_corners REAL, source TEXT, PRIMARY KEY (league_id, fixture_id))")
        c.execute("CREATE TABLE IF NOT EXISTS teams (league_id TEXT, team_id TEXT, team_name TEXT, slug TEXT, source TEXT, PRIMARY KEY (league_id, team_id))")
        c.execute("CREATE TABLE IF NOT EXISTS players (league_id TEXT, team_id TEXT, team_name TEXT, player_id TEXT, player_name TEXT, position TEXT, date_born TEXT, nationality TEXT, source TEXT, season TEXT, PRIMARY KEY (league_id, team_id, player_id, season))")


def save_one(league, fixtures, teams, players):
    lid=league["id"]; outdir=DATA/lid; outdir.mkdir(parents=True,exist_ok=True)
    if fixtures is not None and not fixtures.empty:
        fixtures = fixtures.copy()
        if "date" in fixtures:
            fixtures["date"] = pd.to_datetime(fixtures["date"], errors="coerce", utc=True).dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    if teams is not None and not teams.empty: teams = teams.copy()
    if players is not None and not players.empty: players = players.copy()
    for df,fn in [(fixtures,"matches.csv"),(teams,"teams.csv"),(players,"players.csv")]:
        if df is not None and not df.empty: df.to_csv(outdir/fn,index=False,encoding="utf-8-sig")
        elif not (outdir/fn).exists(): pd.DataFrame().to_csv(outdir/fn,index=False)
    meta={"league_id":lid,"name_zh":league.get("name_zh"),"updated_at":datetime.now(timezone.utc).isoformat(),
          "fixtures":len(fixtures),"teams":len(teams),"players":len(players),
          "corner_fixtures":int(fixtures[["home_corners","away_corners"]].notna().all(axis=1).sum()) if not fixtures.empty else 0,
          "sources":sorted(set(fixtures.source.astype(str))) if not fixtures.empty else [],"status":"ok" if len(fixtures)>=5 else "insufficient"}
    (outdir/"metadata.json").write_text(json.dumps(meta,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    with sqlite3.connect(DB,timeout=30) as c:
        for table,df in [("fixtures",fixtures),("teams",teams),("players",players)]:
            if df.empty: continue
            x=df.copy(); x.insert(0,"league_id",lid)
            cols=list(x.columns)
            if table=="fixtures": cols=["league_id","fixture_id","date","season","home_team","away_team","home_goals","away_goals","home_corners","away_corners","source"]
            elif table=="teams": cols=["league_id","team_id","team_name","slug","source"]
            else: cols=["league_id","team_id","team_name","player_id","player_name","position","date_born","nationality","source","season"]
            for col in cols:
                if col not in x: x[col]=None
            x=x[cols].where(pd.notna(x),None)
            # sqlite3 不接受 pandas.Timestamp / numpy scalar；統一轉成 Python 基本型別。
            x = x.astype(object)
            x = x.map(lambda v: v.item() if hasattr(v, "item") else v)
            placeholders=','.join('?'*len(cols)); c.executemany(f"INSERT OR REPLACE INTO {table} ({','.join(cols)}) VALUES ({placeholders})", x.itertuples(index=False,name=None))
    return meta


def sync_one(league):
    lid=league["id"]
    fd=read_football_data(league)
    ep, et=read_espn(lid)
    of = pd.DataFrame()
    if fd.empty and ep.empty and read_openfootball is not None:
        try: of = read_openfootball(league)
        except Exception: of = pd.DataFrame()
    existing = read_existing_cache(lid)
    # Prefer football-data for supported leagues because it includes verified HC/AC; use ESPN only for missing dates.
    if fd.empty and ep.empty and of.empty: fixtures,teams=existing,et
    elif fd.empty and ep.empty: fixtures,teams=of,et
    elif fd.empty: fixtures,teams=ep,et
    elif ep.empty: fixtures,teams=fd,et
    else:
        # football-data.co.uk 對支援聯賽已有完整三季賽果，優先使用它，避免
        # ESPN 隊名格式不同造成同一場被計兩次；ESPN 仍用來提供球隊及球員。
        if lid in SUPPORTED_FD:
            fixtures = fd
        else:
            fixtures=pd.concat([fd,ep],ignore_index=True).drop_duplicates(subset=["date","home_team","away_team"],keep="first")
        teams=et
    if fixtures.empty and not existing.empty:
        fixtures = existing
    players=read_rosters(lid,teams)
    meta=save_one(league,fixtures,teams,players)
    return meta


def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--leagues",default="all"); ap.add_argument("--workers",type=int,default=4); ap.add_argument("--no-players",action="store_true"); args=ap.parse_args()
    cfg=json.loads(CONFIG.read_text(encoding="utf-8")); rows=cfg["leagues"]
    wanted={x.strip() for x in args.leagues.split(",")} if args.leagues!="all" else {x["id"] for x in rows}
    selected=[x for x in rows if x["id"] in wanted]
    init_db(); results=[]
    # Network bounded; each league writes independently with SQLite transactions.
    def run(x):
        if args.no_players:
            old=read_rosters
            globals()["read_rosters"]=lambda *_: pd.DataFrame()
            try: return sync_one(x)
            finally: globals()["read_rosters"]=old
        return sync_one(x)
    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1,args.workers)) as ex:
        for fut in concurrent.futures.as_completed([ex.submit(run,x) for x in selected]):
            try:
                m=fut.result(); results.append(m); print(json.dumps(m,ensure_ascii=False),flush=True)
            except Exception as e:
                print(json.dumps({"status":"failed","error":str(e)},ensure_ascii=False),flush=True)
    report=ROOT/"data"/"multisource_sync_report.json"; report.write_text(json.dumps(sorted(results,key=lambda x:x.get("league_id","")),ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(f"DONE {len(results)}/{len(selected)}; report={report}")

if __name__=="__main__": main()

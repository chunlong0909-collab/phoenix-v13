#!/usr/bin/env python3
"""無 API Key 的每日足球資料同步。

主來源：soccerdata/FBref（可支援的聯賽，賽果、入球、球員季統計）。
後備：現有 football-data.co.uk、ESPN 公開賽果／名單及 OpenFootball 快取。
角球只接受來源實際提供 HC/AC；缺失保持空值，絕不填 0。

注意：FBref 的 soccerdata schedule 並不保證提供角球欄位；因此角球會由
football-data.co.uk 或既有已核實快取補入，沒有就標示 corner_data_missing。
"""
from __future__ import annotations
import argparse, json, re, subprocess, sys
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "leagues"
CONFIG = ROOT / "leagues.json"
SEASONS = [2024, 2025]  # 近兩個完整/當前年度；每日更新會保留舊檔
FBREF = {
    "epl": "ENG-Premier League", "championship": "ENG-Championship",
    "laliga": "ESP-La Liga", "laliga2": "ESP-Segunda-Division",
    "bundesliga": "GER-Bundesliga", "bundesliga2": "GER-2-Bundesliga",
    "ligue2": "FRA-Ligue-2", "eredivisie": "NED-Eredivisie",
    "serie-a": "ITA-Serie-A", "scottish-prem": "SCO-Premiership",
}


def parse_score(value):
    m = re.search(r"(\d+)\s*[–-]\s*(\d+)", str(value or ""))
    return (float(m.group(1)), float(m.group(2))) if m else (None, None)


def read_fbref(league_id):
    alias = FBREF.get(league_id)
    if not alias:
        return pd.DataFrame(), pd.DataFrame(), "FBref unavailable for configured league"
    try:
        import soccerdata as sd
        fb = sd.FBref(leagues=alias, seasons=SEASONS, no_cache=False, data_dir=ROOT/"data"/"soccerdata")
        sch = fb.read_schedule()
        if sch is None or sch.empty: return pd.DataFrame(), pd.DataFrame(), "FBref returned no schedule"
        rows=[]
        for idx,row in sch.reset_index().iterrows():
            hg,ag=parse_score(row.get("score"))
            if hg is None: continue
            rows.append({"fixture_id":str(row.get("game_id") or f"fbref-{league_id}-{idx}"),"date":row.get("date"),
                "season":str(row.get("season","")),"home_team":row.get("home_team",""),"away_team":row.get("away_team",""),
                "home_goals":hg,"away_goals":ag,"home_corners":pd.NA,"away_corners":pd.NA,"source":"FBref/soccerdata"})
        fixtures=pd.DataFrame(rows)
        try:
            ps=fb.read_player_season_stats(stat_type="standard").reset_index()
            players=ps.rename(columns={"team":"team_name","player":"player_name","pos":"position","born":"date_born"})
            players["source"]="FBref player stats"; players["season"]=players.get("season","").astype(str)
        except Exception:
            players=pd.DataFrame()
        return fixtures,players,"ok"
    except BaseException as e:
        return pd.DataFrame(),pd.DataFrame(),f"FBref error: {type(e).__name__}: {e}"


def merge_corners(league_id, fixtures):
    """只從現有本地核實快取補角球，按日期及主客隊對應。"""
    if fixtures.empty: return fixtures
    p=DATA/league_id/"matches.csv"
    if not p.exists(): return fixtures
    try: old=pd.read_csv(p)
    except Exception: return fixtures
    needed={"home_team","away_team","home_corners","away_corners"}
    if not needed.issubset(old.columns): return fixtures
    old=old.copy(); old["_d"]=pd.to_datetime(old.get("date"),errors="coerce").dt.date
    fixtures=fixtures.copy(); fixtures["_d"]=pd.to_datetime(fixtures.get("date"),errors="coerce").dt.date
    key=["_d","home_team","away_team"]
    z=old[key+['home_corners','away_corners']].drop_duplicates(key)
    out=fixtures.merge(z,on=key,how="left",suffixes=("","_old"))
    out["home_corners"]=out["home_corners"].where(out["home_corners"].notna(),out["home_corners_old"])
    out["away_corners"]=out["away_corners"].where(out["away_corners"].notna(),out["away_corners_old"])
    return out.drop(columns=["_d","home_corners_old","away_corners_old"],errors="ignore")


def run_fallback(league_id):
    # Reuse the already audited public-source collector; it never fabricates corners.
    try:
        from sync_multisource import sync_one
        cfg=json.loads(CONFIG.read_text(encoding="utf-8"))
        league=next(x for x in cfg["leagues"] if x["id"]==league_id)
        return sync_one(league)
    except Exception as e:
        return {"league_id":league_id,"status":"failed","error":str(e)}


def save_fbref(league, fixtures, players, note):
    lid=league["id"]; out=DATA/lid; out.mkdir(parents=True,exist_ok=True)
    fixtures=merge_corners(lid,fixtures)
    if not fixtures.empty:
        fixtures["date"]=pd.to_datetime(fixtures["date"],errors="coerce",utc=True).dt.strftime("%Y-%m-%d")
        fixtures.to_csv(out/"matches.csv",index=False,encoding="utf-8-sig")
    if not players.empty:
        players.to_csv(out/"players.csv",index=False,encoding="utf-8-sig")
    oldmeta={}
    try: oldmeta=json.loads((out/"metadata.json").read_text(encoding="utf-8"))
    except Exception: pass
    meta={"league_id":lid,"name_zh":league.get("name_zh"),"updated_at":pd.Timestamp.utcnow().isoformat(),
          "fixtures":int(len(fixtures)),"players":int(len(players)),"corner_fixtures":int(fixtures[["home_corners","away_corners"]].notna().all(axis=1).sum()) if not fixtures.empty else 0,
          "dataSource":"FBref/soccerdata","fallback_note":note,"corner_data_missing":bool(fixtures.empty or fixtures[["home_corners","away_corners"]].isna().any(axis=1).all())}
    (out/"metadata.json").write_text(json.dumps(meta,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    return meta


def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--leagues",default="all"); args=ap.parse_args()
    cfg=json.loads(CONFIG.read_text(encoding="utf-8")); ids={x.strip() for x in args.leagues.split(",")} if args.leagues!="all" else {x["id"] for x in cfg["leagues"]}
    results=[]
    for league in cfg["leagues"]:
        if league["id"] not in ids: continue
        lid=league["id"]; f,p,note=read_fbref(lid)
        # Australian Championship has no FBref/soccerdata mapping. Preserve the
        # separately audited public-results cache instead of letting the generic
        # fallback overwrite it with an empty/incorrect competition.
        if lid == "australian-championship":
            cached = DATA / lid / "metadata.json"
            if cached.exists():
                try:
                    meta = json.loads(cached.read_text(encoding="utf-8"))
                except Exception:
                    meta = {"league_id": lid, "name_zh": league.get("name_zh"), "fixtures": 0}
                meta["status"] = "ok"
                meta["preserved_cache"] = True
                meta["fallback_note"] = "保留已核實澳洲冠軍聯賽公開賽果快取"
                results.append(meta)
                print(json.dumps(meta, ensure_ascii=False), flush=True)
                continue
        if not f.empty:
            meta=save_fbref(league,f,p,note); results.append(meta)
        else:
            meta=run_fallback(lid); meta["primary_source_note"]=note; results.append(meta)
        print(json.dumps(results[-1],ensure_ascii=False),flush=True)
    report=ROOT/"data"/"free_source_sync_report.json"; report.write_text(json.dumps(results,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(f"DONE {len(results)}; report={report}")

if __name__=="__main__": main()

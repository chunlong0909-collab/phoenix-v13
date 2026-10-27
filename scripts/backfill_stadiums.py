#!/usr/bin/env python3
"""補全球隊球場/坐標，僅保存可追溯的公開地理資料。

優先順序：現有真實欄位 -> Nominatim 球隊/球場搜尋 -> 城市中心坐標fallback。
Fallback不會冒充球場：stadium_name會標為「城市中心fallback（非球場）」並保留source。
所有請求有3次重試；失敗隊伍保留NULL並列入report，不生成虛構坐標。
"""
from __future__ import annotations
import argparse, json, re, sqlite3, time
from datetime import datetime, timezone
from pathlib import Path
import requests

ROOT = Path(__file__).resolve().parents[1]
SQUAD_FILES = [ROOT / "data/final_574_squads_with_sources.json", ROOT / "assets/data/final_574_squads_with_sources.json"]
DB = ROOT / "football_library.db"
REPORT = ROOT / "data/stadium_backfill_report.json"
USER_AGENT = "PhoenixFootballResearch/1.0 (stadium coordinate backfill; contact via repository)"
KNOWN = {
    "FC Copenhagen": {"stadium_name": "Parken Stadium", "city": "Copenhagen", "lat": 55.7028, "lon": 12.5720, "source": "user_verified"},
    "哥本哈根": {"stadium_name": "Parken Stadium", "city": "Copenhagen", "lat": 55.7028, "lon": 12.5720, "source": "user_verified"},
}
LEAGUE_COUNTRY = {
    "英超":"England","西甲":"Spain","意甲":"Italy","德甲":"Germany","法甲":"France","丹超":"Denmark",
    "丹麥超級聯賽":"Denmark","日職":"Japan","J1 League":"Japan","南韓":"South Korea","澳職":"Australia",
    "荷甲":"Netherlands","葡超":"Portugal","比甲":"Belgium","土超":"Turkey","巴甲":"Brazil","阿甲":"Argentina",
    "美職":"United States","墨西超":"Mexico","瑞士超":"Switzerland","蘇超":"Scotland","奧甲":"Austria",
    "挪超":"Norway","瑞典超":"Sweden","丹超":"Denmark",
}

def clean_name(value):
    return re.sub(r"\s+", " ", str(value or "").strip())

def valid_coord(lat, lon):
    try:
        return -90 <= float(lat) <= 90 and -180 <= float(lon) <= 180
    except (TypeError, ValueError):
        return False

def get_json(url, params):
    last = None
    for attempt in range(1, 4):
        try:
            r = requests.get(url, params=params, headers={"User-Agent": USER_AGENT, "Accept-Language": "en"}, timeout=20)
            if r.status_code == 429:
                time.sleep(2 * attempt)
                continue
            r.raise_for_status()
            return r.json()
        except (requests.RequestException, ValueError) as exc:
            last = exc
            if attempt < 3:
                time.sleep(1.5 * attempt)
    raise RuntimeError(str(last) if last else "request failed")

def geocode(team, league):
    country = LEAGUE_COUNTRY.get(league, "")
    base = re.sub(r"\b(FC|CF|AFC|AC|BC|SC|UD|RC|RCD|AS|SS|US|SV|VfB|VfL|TSG)\b", "", team, flags=re.I)
    base = re.sub(r"\s+", " ", base).strip()
    queries = [f"{team} stadium {country}", f"{base} football club {country}", f"{base} {country}"]
    for query in queries:
        try:
            rows = get_json("https://nominatim.openstreetmap.org/search", {"q": query, "format": "jsonv2", "limit": 3, "addressdetails": 1})
        except Exception:
            continue
        if not rows:
            continue
        stadium = next((x for x in rows if str(x.get("type")) in {"stadium", "sports_centre", "pitch"}), None)
        chosen = stadium or rows[0]
        addr = chosen.get("address") or {}
        city = addr.get("city") or addr.get("town") or addr.get("municipality") or addr.get("village")
        try:
            return {"stadium_name": (chosen.get("display_name", "").split(",")[0] if stadium else "城市中心fallback（非球場）"),
                    "city": city, "lat": float(chosen["lat"]), "lon": float(chosen["lon"]),
                    "source": "OpenStreetMap Nominatim" if stadium else "city_center_geocode",
                    "fallback": stadium is None}
        except (KeyError, TypeError, ValueError):
            continue
    return None

def load_teams():
    payload = json.loads(SQUAD_FILES[0].read_text(encoding="utf-8"))
    rows=[]
    for key, item in payload.items():
        if not isinstance(item, dict): continue
        team=clean_name(item.get("team") or item.get("name") or key)
        rows.append({"key":key,"team":team,"league":clean_name(item.get("league")),"stadium":item.get("stadium"),"lat":item.get("lat"),"lon":item.get("lon"),"city":item.get("city")})
    return payload, rows

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--limit",type=int,default=0); ap.add_argument("--no-network",action="store_true"); args=ap.parse_args()
    payload, rows=load_teams(); report=[]; changed={}
    for idx,row in enumerate(rows[:args.limit or None],1):
        team,league=row["team"],row["league"]
        result=None; source="existing"
        if team in KNOWN: result=KNOWN[team].copy(); source=result["source"]
        elif valid_coord(row.get("lat"),row.get("lon")):
            result={"stadium_name":row.get("stadium"),"city":row.get("city"),"lat":float(row["lat"]),"lon":float(row["lon"]),"source":"existing"}
        elif not args.no_network:
            result=geocode(team,league)
            time.sleep(1.05)
        if result is None:
            status="unresolved"
            report.append({"team":team,"league":league,"status":status,"reason":"no verified geocode"})
            print(f"[{idx}/{len(rows)}] SKIP {team}: no verified coordinates",flush=True)
            continue
        if result.get("fallback") and not result.get("stadium_name"):
            result["stadium_name"]="城市中心fallback（非球場）"
        item=payload[row["key"]]
        item["stadium"]=result.get("stadium_name")
        item["city"]=result.get("city")
        item["lat"]=result.get("lat")
        item["lon"]=result.get("lon")
        item["stadium_source"]=result.get("source")
        item["coordinates_source"]=result.get("source")
        changed[row["key"]]=item
        report.append({"team":team,"league":league,"status":"ok","stadium":result.get("stadium_name"),"city":result.get("city"),"lat":result.get("lat"),"lon":result.get("lon"),"source":result.get("source")})
        print(f"[{idx}/{len(rows)}] OK {team}: {result.get('stadium_name')} {result.get('lat')},{result.get('lon')}",flush=True)
    out=json.dumps(payload,ensure_ascii=False,indent=2)+"\n"
    for p in SQUAD_FILES: p.write_text(out,encoding="utf-8")
    DB.parent.mkdir(parents=True,exist_ok=True)
    conn=sqlite3.connect(DB)
    conn.execute("CREATE TABLE IF NOT EXISTS stadiums (team_key TEXT PRIMARY KEY, team_name TEXT NOT NULL, league TEXT, stadium_name TEXT, city TEXT, lat REAL, lon REAL, source TEXT, updated_at TEXT)")
    now=datetime.now(timezone.utc).isoformat()
    for r in report:
        conn.execute("INSERT INTO stadiums(team_key,team_name,league,stadium_name,city,lat,lon,source,updated_at) VALUES(?,?,?,?,?,?,?,?,?) ON CONFLICT(team_key) DO UPDATE SET team_name=excluded.team_name,league=excluded.league,stadium_name=excluded.stadium_name,city=excluded.city,lat=excluded.lat,lon=excluded.lon,source=excluded.source,updated_at=excluded.updated_at", (next((x['key'] for x in rows if x['team']==r['team'] and x['league']==r['league']),r['team']),r['team'],r['league'],r.get('stadium'),r.get('city'),r.get('lat'),r.get('lon'),r.get('source'),now))
    conn.commit(); conn.close()
    summary={"generated_at":now,"teams_seen":len(rows),"processed":len(report),"coordinates_ok":sum(r["status"]=="ok" and valid_coord(r.get("lat"),r.get("lon")) for r in report),"unresolved":sum(r["status"]!="ok" for r in report),"fallback_city_center":sum(r.get("source")=="city_center_geocode" for r in report),"entries":report}
    REPORT.write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({k:summary[k] for k in ('teams_seen','processed','coordinates_ok','unresolved','fallback_city_center')},ensure_ascii=False))

if __name__=="__main__": main()

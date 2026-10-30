#!/usr/bin/env python3
"""Import verified English League Two FT results from ESPN's public scoreboard.

Default is dry-run. Only STATUS_FULL_TIME events are accepted; no HT/corners are
invented. Commit writes the append-only Phoenix match_history CSV.
"""
from __future__ import annotations
import argparse, csv, datetime as dt, json, time
from pathlib import Path
import requests

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data/match_history/league_efl_league_two_2026_27.csv"
ASSET_OUT = ROOT / "assets/data/match_history/league_efl_league_two_2026_27.csv"
SOURCE = "ESPN public scoreboard"
SOURCE_URL = "https://site.api.espn.com/apis/site/v2/sports/soccer/eng.4/scoreboard"
FIELDS = ["date", "home_team", "away_team", "home_goals", "away_goals", "home_corners", "away_corners", "league", "season", "source", "source_url", "verified_ft", "match_id"]


def day_range(start: dt.date, end: dt.date):
    d = start
    while d <= end:
        yield d
        d += dt.timedelta(days=1)


def fetch(start: dt.date, end: dt.date):
    session = requests.Session()
    session.headers.update({"User-Agent": "Phoenix/2.0 verified FT importer"})
    rows = {}
    for day in day_range(start, end):
        r = session.get(SOURCE_URL, params={"dates": day.strftime("%Y%m%d")}, timeout=30)
        r.raise_for_status()
        payload = r.json()
        for event in payload.get("events", []):
            comp = (event.get("competitions") or [{}])[0]
            status = ((comp.get("status") or {}).get("type") or {})
            if status.get("name") != "STATUS_FULL_TIME" and not status.get("completed"):
                continue
            competitors = comp.get("competitors") or []
            home = next((x for x in competitors if x.get("homeAway") == "home"), None)
            away = next((x for x in competitors if x.get("homeAway") == "away"), None)
            if not home or not away:
                continue
            home_name = ((home.get("team") or {}).get("displayName") or "").strip()
            away_name = ((away.get("team") or {}).get("displayName") or "").strip()
            try:
                hg = int(float(home.get("score")))
                ag = int(float(away.get("score")))
            except (TypeError, ValueError):
                continue
            event_id = str(event.get("id") or "").strip()
            if not event_id or not home_name or not away_name:
                continue
            date = str(event.get("date") or "")[:10] or day.isoformat()
            rows[event_id] = {
                "date": date, "home_team": home_name, "away_team": away_name,
                "home_goals": hg, "away_goals": ag, "home_corners": "", "away_corners": "",
                "league": "英格蘭乙組聯賽", "season": "2026/27", "source": SOURCE,
                "source_url": f"{SOURCE_URL}?dates={day:%Y%m%d}", "verified_ft": 1, "match_id": event_id,
            }
        time.sleep(0.05)
    return sorted(rows.values(), key=lambda x: (x["date"], x["home_team"], x["away_team"]))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--commit", action="store_true")
    ap.add_argument("--start", default="2026-08-15")
    ap.add_argument("--end", default="2026-10-29")
    args = ap.parse_args()
    rows = fetch(dt.date.fromisoformat(args.start), dt.date.fromisoformat(args.end))
    print(json.dumps({"mode": "commit" if args.commit else "dry_run", "rows": len(rows), "newport": sum("Newport" in (r["home_team"]+r["away_team"]) for r in rows), "chesterfield": sum("Chesterfield" in (r["home_team"]+r["away_team"]) for r in rows), "source": SOURCE}, ensure_ascii=False))
    if not args.commit:
        return
    for path in (OUT, ASSET_OUT):
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=FIELDS)
            writer.writeheader(); writer.writerows(rows)
        print("wrote", path, len(rows))


if __name__ == "__main__":
    main()

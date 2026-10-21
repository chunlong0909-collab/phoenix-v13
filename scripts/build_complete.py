#!/usr/bin/env python3
"""Merge historical matches and current squad/stat caches into data/complete/."""
from __future__ import annotations
import argparse, json, re
import sys
from datetime import datetime, timezone
from pathlib import Path
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from analysis.corrections import adjusted_strength

HISTORY = ROOT / "data" / "history"
LEAGUES = ROOT / "data" / "leagues"
FALLBACK = ROOT / "data" / "players" / "fallback"
OUT = ROOT / "data" / "complete"
TEAM_IDS = {"Al Nassr": "817", "Al-Nassr": "817"}
ESPN_SQUAD = {"Al Nassr": "https://www.espn.com/soccer/team/squad/_/id/817/team.al_nassr"}
ESPN_SCORING = {"Al Nassr": "https://www.espn.com/soccer/team/stats/_/id/817/league/KSA.1/view/scoring"}

def clean_name(value):
    return re.sub(r"\s*\d+$", "", str(value or "")).strip()

def read_json(path, default):
    try: return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default
    except Exception: return default

def scoring_for_team(team: str) -> dict[str, dict]:
    url = ESPN_SCORING.get(team)
    if not url: return {}
    try:
        tables = pd.read_html(url)
        if not tables: return {}
        df = tables[0]
        out = {}
        for _, row in df.iterrows():
            name = clean_name(row.get("Name", ""))
            if name: out[name] = {"appearances": row.get("P", ""), "goals": row.get("G", ""), "source": "ESPN team stats"}
        return out
    except Exception:
        return {}

def squad_for_team(team: str) -> list[dict]:
    url = ESPN_SQUAD.get(team)
    if not url: return []
    try:
        rows = []
        for df in pd.read_html(url):
            if "Name" not in df.columns: continue
            for _, r in df.iterrows():
                name = clean_name(r.get("Name", ""))
                if name: rows.append({"player_name": name, "position": r.get("POS", ""), "age": r.get("Age", ""), "nationality": r.get("NAT", "")})
        return rows
    except Exception:
        return []

def current_squad(league_id: str, team: str) -> list[dict]:
    sources = [LEAGUES / league_id / "players.csv", FALLBACK / f"{league_id}_players.csv"]
    for p in sources:
        if not p.exists(): continue
        try:
            df = pd.read_csv(p).fillna("")
            key = "team" if "team" in df.columns else "team_name" if "team_name" in df.columns else None
            if key: df = df[df[key].astype(str).map(lambda x: team.lower() in x.lower() or x.lower() in team.lower())]
            rows = df.to_dict("records")
            stats = scoring_for_team(team)
            for row in rows:
                name = clean_name(row.get("strPlayer") or row.get("player_name") or row.get("player_name_en"))
                row["player_name"] = name
                if name in stats: row.update(stats[name])
                row.setdefault("goals", None); row.setdefault("appearances", None)
                row["dataSource"] = row.get("dataSource") or row.get("source") or "local fallback"
            if rows: return rows
        except Exception: pass
    stats = scoring_for_team(team)
    roster = squad_for_team(team)
    if roster:
        for row in roster:
            row.update(stats.get(row["player_name"], {"appearances": None, "goals": None, "source": "ESPN team stats"}))
            row.update({"team": team, "dataSource": "ESPN squad + team stats"})
        return roster
    return [{"player_name": n, **v, "team": team, "dataSource": "ESPN team stats"} for n, v in stats.items()]

def build_one(history_file: Path, team: str | None = None) -> dict:
    hist = read_json(history_file, {})
    matches = hist.get("matches", [])
    teams = sorted(({x.get("home_team") for x in matches} | {x.get("away_team") for x in matches}) - {None})
    target_teams = [team] if team else teams
    squads = {t: current_squad(hist.get("league", ""), t) for t in target_teams}
    seasons = [str(x.get("season", "")) for x in matches if x.get("season")]
    current_season = max(seasons) if seasons else None
    # These fields are optional because the free sources may not publish them.
    # When absent, corrections.py records "not_provided" and does not guess.
    team_flags = hist.get("team_adjustments", {}) if isinstance(hist.get("team_adjustments", {}), dict) else {}
    def strength_for(t):
        flags = team_flags.get(t, {}) if isinstance(team_flags.get(t, {}), dict) else {}
        return adjusted_strength(t, matches, squads.get(t, []), current_season=current_season,
                                 coach_changed=flags.get("coach_changed"),
                                 lineup_change_pct=flags.get("lineup_change_pct"),
                                 injuries_known=flags.get("injuries_known"),
                                 injuries_impact=flags.get("injuries_impact"))
    strengths = {t: strength_for(t) for t in target_teams}
    payload = {"league": hist.get("league"), "team": team, "history": matches,
               "current_squad": squads.get(team, []) if team else squads,
               "adjusted_strength": strengths.get(team) if team else strengths,
               "last_updated": datetime.now(timezone.utc).isoformat(),
               "history_source": hist.get("dataSource", "OpenFootball/world"),
               "squad_source": "ESPN/local fallback", "scorers_available": hist.get("scorers_available", False)}
    OUT.mkdir(parents=True, exist_ok=True)
    name = f"{hist.get('league','unknown')}_{clean_name(team).lower().replace(' ','_')}_complete.json" if team else f"{hist.get('league','unknown')}_complete.json"
    out = OUT / name; out.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    return payload

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--league", default="all"); ap.add_argument("--team", default=None)
    args = ap.parse_args(); HISTORY.mkdir(parents=True, exist_ok=True)
    files = sorted(HISTORY.glob("*_history.json"))
    for p in files:
        if args.league != "all" and p.name != f"{args.league}_history.json": continue
        obj = build_one(p, args.team if args.team else None); print(p.name, len(obj.get("history", [])))

if __name__ == "__main__": main()

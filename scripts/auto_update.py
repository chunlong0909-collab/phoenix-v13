#!/usr/bin/env python3
"""Phoenix daily FT updater.

Sources are deliberately conservative:
- local league matches CSVs are accepted only when they contain date, home,
  away, and final home/away goals;
- API-Football is optional and used only when API_FOOTBALL_TOKEN is set;
- no league-average or fabricated match is ever written as a real FT.

The updater writes a dated teams_stats snapshot to both local SQLite databases,
keeps an append-only run log, and never modifies historical match rows.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import sqlite3
import subprocess
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
LOG_PATH = Path("/logs/auto_update.log")
REPORT_PATH = ROOT / "data" / "auto_update_last_report.json"
GAP_PATH = ROOT / "data" / "coverage_gap_tracker.json"
CONFIG_PATH = ROOT / "data" / "auto_update_config.json"
DBS = [ROOT / "football_complete.db", ROOT / "football_library.db"]
SAUDI_TEAMS = ROOT / "data" / "leagues" / "saudi-pro" / "teams.csv"
API_BASE = "https://v3.football.api-sports.io"
ESPN_LEAGUES = {
    "epl": ("英超", "eng.1"),
    "laliga": ("西甲", "esp.1"),
    "serie-a": ("意甲", "ita.1"),
    "bundesliga": ("德甲", "ger.1"),
    "ligue-1": ("法甲", "fra.1"),
    "j1": ("日職J1", "jpn.1"),
    "brasileirao": ("巴甲", "bra.1"),
    "liga-mx": ("墨超", "mex.1"),
}


def load_config() -> dict:
    try:
        return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except Exception as exc:
        log(f"CONFIG status=error reason={str(exc)[:180]}")
        return {}


def run_worldfootball_probe(config: dict) -> dict:
    """Probe the configured public source; never commits probe rows directly."""
    sources = config.get("sources", [])
    if "worldfootball" not in sources:
        return {"status": "disabled", "reason": "worldfootball_not_configured"}
    mode = str(config.get("live_probe", "pilot")).lower()
    cmd = ["/usr/bin/python3", str(ROOT / "scripts" / "safe_dual_worldfootball_import.py")]
    if mode == "all":
        cmd.append("--all")
    try:
        proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=180)
        report_path = ROOT / "worldfootball_safe_import_report_2026-10-29.json"
        report = json.loads(report_path.read_text(encoding="utf-8")) if report_path.exists() else {}
        result = {
            "status": "available" if report.get("pilot_pass") else "blocked_or_insufficient",
            "mode": mode,
            "exit_code": proc.returncode,
            "pilot_pass": report.get("pilot_pass", False),
            "all_pass": report.get("all_pass", False),
            "total_rows": report.get("total_rows", 0),
            "results": report.get("results", []),
        }
        if result["status"] != "available":
            log(f"LIVE_SOURCE source=worldfootball status={result['status']} rows={result['total_rows']}")
        return result
    except Exception as exc:
        log(f"LIVE_SOURCE source=worldfootball status=error reason={str(exc)[:180]}")
        return {"status": "error", "mode": mode, "reason": str(exc)[:240]}


def _csv_team_names(path: Path) -> set[str]:
    try:
        frame = pd.read_csv(path, dtype=str)
    except Exception:
        return set()
    cols = [c for c in frame.columns if str(c).strip().lower() in {"team", "team_name", "squad", "club", "en_name"}]
    if not cols:
        return set()
    return {norm(v) for v in frame[cols[0]].dropna() if norm(v)}


def _csv_row_count(path: Path) -> int:
    try:
        return int(len(pd.read_csv(path, dtype=str))) if path.exists() else 0
    except Exception:
        return 0


def build_coverage_gap_report(matches: pd.DataFrame) -> dict:
    """Record missing directory/roster coverage without inventing records."""
    leagues = []
    for directory_file in sorted((ROOT / "data" / "leagues").glob("*/teams.csv")):
        slug = directory_file.parent.name
        expected = _csv_team_names(directory_file)
        observed = set()
        if not matches.empty and "league_id" in matches.columns:
            group = matches[matches["league_id"].astype(str).map(lambda x: LEAGUE_IDS.get(x, x) == slug)]
            observed = {norm(x) for x in group.get("home_team", pd.Series(dtype=str)).dropna()}
            observed |= {norm(x) for x in group.get("away_team", pd.Series(dtype=str)).dropna()}
        player_file = directory_file.parent / "players.csv"
        coach_file = directory_file.parent / "coaches.csv"
        players = _csv_team_names(player_file) if player_file.exists() else set()
        coaches = _csv_team_names(coach_file) if coach_file.exists() else set()
        missing_ft = sorted(expected - observed)
        leagues.append({
            "league": slug,
            "directory_teams": len(expected),
            "ft_teams_seen": len(observed),
            "missing_ft_teams": missing_ft[:100],
            "missing_ft_team_count": len(missing_ft),
            "player_roster_rows": _csv_row_count(player_file),
            "coach_roster_rows": _csv_row_count(coach_file),
            "last_checked": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        })
    previous = {}
    if GAP_PATH.exists():
        try:
            previous = json.loads(GAP_PATH.read_text(encoding="utf-8"))
        except Exception:
            previous = {}
    report = {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "rule": "只追蹤真實來源缺口；不以估算、賠率或聯賽平均冒充FT/球員/教練",
        "league_count": len(leagues),
        "leagues": leagues,
        "history_runs": int(previous.get("history_runs", 0)) + 1,
    }
    GAP_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"league_count": len(leagues), "leagues_with_gaps": sum(bool(x["missing_ft_teams"]) for x in leagues), "tracker": str(GAP_PATH)}

# Explicit aliases for league files already present in this project.
LEAGUE_IDS = {
    "j1": "j1", "j2": "j2", "k1": "k1", "k2": "k2",
    "saudi-pro": "saudi-pro", "epl": "epl", "laliga": "laliga",
    "serie-a": "serie-a", "bundesliga": "bundesliga",
    "afc-champions-league-elite": "afc-champions-league-elite",
    "australia-cup": "australia-cup", "veikkausliiga": "veikkausliiga",
    "austria": "austria", "brasileirao": "brasileirao", "br": "br",
}


def log(message: str) -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
    line = f"{stamp} {message}\n"
    with LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(line)
    print(line, end="")


def norm(value) -> str:
    return re.sub(r"\s+", " ", str(value or "").replace("\ufeff", "")).strip()


def refresh_official_metadata(config: dict, commit: bool = False) -> dict:
    """Check official squad/coach/standings pages without inventing missing facts."""
    sources = config.get("metadata_sources", {}) or {}
    result = {"checked_at": datetime.now(timezone.utc).isoformat(), "leagues": {}}
    for league, item in sources.items():
        entry = {"provider": item.get("provider"), "teams": {}, "standings": {}}
        for team, url in (item.get("teams", {}) or {}).items():
            try:
                r = requests.get(url, headers={"User-Agent": "Phoenix-safe-updater/1.0"}, timeout=25)
                soup = BeautifulSoup(r.text, "html.parser")
                text = soup.get_text(" ", strip=True)
                links = sorted({a.get("href", "") for a in soup.select('a[href*="/players/"]') if a.get("href")})
                entry["teams"][team] = {"status": "reachable" if r.ok else "blocked", "http_status": r.status_code, "player_link_count": len(links), "coach_field_found": "Coach" in text, "content_sha256": hashlib.sha256(r.content).hexdigest(), "source_url": url}
            except Exception as exc:
                entry["teams"][team] = {"status": "error", "reason": str(exc)[:180], "source_url": url}
        url = item.get("standings")
        if url:
            try:
                r = requests.get(url, headers={"User-Agent": "Phoenix-safe-updater/1.0"}, timeout=25)
                text = BeautifulSoup(r.text, "html.parser").get_text(" ", strip=True)
                entry["standings"] = {"status": "reachable" if r.ok else "blocked", "http_status": r.status_code, "diriyah_present": (True if "diriyah" in text.lower() else None), "neom_present": (True if "neom" in text.lower() else None), "parser_note": "null means the page rendered standings client-side and did not expose team names in static HTML", "content_sha256": hashlib.sha256(r.content).hexdigest(), "source_url": url}
            except Exception as exc:
                entry["standings"] = {"status": "error", "reason": str(exc)[:180], "source_url": url}
        result["leagues"][league] = entry
    path = ROOT / "data" / "official_metadata_health.json"
    if commit or not path.exists():
        path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return result


def team_id(name: str) -> str:
    key = re.sub(r"[^a-z0-9]+", "_", norm(name).lower()).strip("_")
    return key or hashlib.sha1(norm(name).encode()).hexdigest()[:12]


def league_id_for(path: Path) -> str:
    slug = path.parent.name if path.parent.name != "match_history" else path.stem
    return LEAGUE_IDS.get(slug, slug)


def empty_schema() -> pd.DataFrame:
    return pd.DataFrame(columns=["date", "home_team", "away_team", "home_goals", "away_goals", "home_corners", "away_corners", "source"])


def read_ft_csv(path: Path) -> pd.DataFrame:
    """Read only rows with verified final scores; silently excludes odds-only CSVs."""
    try:
        raw = pd.read_csv(path, dtype=str)
    except Exception as exc:
        log(f"SKIP file={path.relative_to(ROOT)} reason=read_error:{exc}")
        return empty_schema()
    raw.columns = [norm(c).lower() for c in raw.columns]
    aliases = {
        "date": ["date", "match_date", "日期"],
        "home_team": ["home_team", "home", "hometeam", "主隊"],
        "away_team": ["away_team", "away", "awayteam", "客隊"],
        "home_goals": ["home_goals", "ft_home", "fthg", "hg", "主隊入球"],
        "away_goals": ["away_goals", "ft_away", "ftag", "ag", "客隊入球"],
        "home_corners": ["home_corners", "hc", "主隊角球"],
        "away_corners": ["away_corners", "ac", "客隊角球"],
    }
    found = {}
    for target, options in aliases.items():
        for option in options:
            if option in raw.columns:
                found[target] = option
                break
    required = {"date", "home_team", "away_team", "home_goals", "away_goals"}
    if not required.issubset(found):
        return empty_schema()
    out = pd.DataFrame({k: raw[v].map(norm) for k, v in found.items()})
    out["date"] = pd.to_datetime(out["date"], errors="coerce", dayfirst=True, format="mixed").dt.strftime("%Y-%m-%d")
    out["home_goals"] = pd.to_numeric(out["home_goals"], errors="coerce")
    out["away_goals"] = pd.to_numeric(out["away_goals"], errors="coerce")
    for c in ("home_corners", "away_corners"):
        if c not in out:
            out[c] = pd.NA
        out[c] = pd.to_numeric(out[c], errors="coerce")
    out = out.dropna(subset=["date", "home_team", "away_team", "home_goals", "away_goals"])
    out = out[(out["home_team"] != "") & (out["away_team"] != "")]
    return out.reset_index(drop=True)


def collect_local_ft() -> tuple[pd.DataFrame, list[dict]]:
    rows, report = [], []
    candidates = []
    for p in [ROOT / "matches.csv", ROOT / "data" / "matches.csv"]:
        if p.exists():
            candidates.append(p)
    candidates += sorted((ROOT / "data" / "leagues").glob("*/matches.csv"))
    candidates += sorted((ROOT / "data" / "match_history").glob("*.csv"))
    seen = set()
    for path in candidates:
        if path.resolve() in seen:
            continue
        seen.add(path.resolve())
        frame = read_ft_csv(path)
        if frame.empty:
            report.append({"file": str(path.relative_to(ROOT)), "ft_rows": 0, "status": "skipped_no_verified_ft"})
            continue
        lid = league_id_for(path)
        frame["league_id"] = lid
        frame["source"] = str(path.relative_to(ROOT))
        rows.append(frame)
        report.append({"file": str(path.relative_to(ROOT)), "league_id": lid, "ft_rows": len(frame), "status": "accepted_real_ft"})
    if not rows:
        return empty_schema().assign(league_id=pd.Series(dtype=str)), report
    all_rows = pd.concat(rows, ignore_index=True)
    all_rows = all_rows.drop_duplicates(subset=["date", "home_team", "away_team", "home_goals", "away_goals", "league_id"])
    return all_rows, report


def api_football_ft() -> tuple[pd.DataFrame, list[dict]]:
    """Optional API source. Empty without a configured token; never invents IDs or scores."""
    token = os.environ.get("API_FOOTBALL_TOKEN", "").strip()
    if not token:
        return pd.DataFrame(), [{"status": "skipped_no_API_FOOTBALL_TOKEN"}]
    # League IDs/seasons must be explicitly configured by the operator; do not guess.
    configured = os.environ.get("PHOENIX_API_LEAGUES", "").strip()
    if not configured:
        return pd.DataFrame(), [{"status": "skipped_no_PHOENIX_API_LEAGUES"}]
    out, report = [], []
    headers = {"x-apisports-key": token}
    for item in configured.split(","):
        try:
            league, season = item.strip().split(":", 1)
            response = requests.get(f"{API_BASE}/fixtures", headers=headers, params={"league": league, "season": season, "status": "FT"}, timeout=25)
            response.raise_for_status()
            payload = response.json()
            for item in payload.get("response", []):
                fixture = item.get("fixture", {})
                teams = item.get("teams", {})
                goals = item.get("goals", {})
                if goals.get("home") is None or goals.get("away") is None:
                    continue
                out.append({"date": str(fixture.get("date", ""))[:10], "home_team": norm(teams.get("home", {}).get("name")), "away_team": norm(teams.get("away", {}).get("name")), "home_goals": goals["home"], "away_goals": goals["away"], "home_corners": pd.NA, "away_corners": pd.NA, "league_id": f"api:{league}", "source": "API-Football verified FT"})
            report.append({"league": league, "season": season, "status": "accepted", "ft_rows": len(out)})
        except Exception as exc:
            report.append({"league": item, "status": "skipped_error", "reason": str(exc)[:180]})
    return pd.DataFrame(out), report


def espn_public_ft(days_back: int = 3) -> tuple[pd.DataFrame, list[dict]]:
    """Read completed scores from ESPN's public scoreboard JSON.

    This is deliberately limited to configured competition slugs and recent
    dates. A row is accepted only when ESPN marks it post/complete and both
    scores are integer values. No standings or odds are converted into FT.
    """
    if not ESPN_LEAGUES:
        return pd.DataFrame(), [{"status": "skipped_no_ESPN_leagues"}]
    rows, report = [], []
    now = datetime.now(timezone.utc)
    for league_id, (league_name, slug) in ESPN_LEAGUES.items():
        before = len(rows)
        errors = []
        for delta in range(max(1, days_back)):
            day = (now - pd.Timedelta(days=delta)).strftime("%Y%m%d")
            try:
                r = requests.get(
                    f"https://site.api.espn.com/apis/site/v2/sports/soccer/{slug}/scoreboard",
                    params={"dates": day},
                    headers={"User-Agent": "Phoenix-safe-updater/1.0"},
                    timeout=25,
                )
                r.raise_for_status()
                payload = r.json()
                for event in payload.get("events", []):
                    competition = (event.get("competitions") or [{}])[0]
                    status = competition.get("status", {}).get("type", {})
                    if status.get("state") != "post" or not status.get("completed"):
                        continue
                    competitors = competition.get("competitors") or []
                    if len(competitors) != 2:
                        continue
                    home = next((x for x in competitors if x.get("homeAway") == "home"), competitors[0])
                    away = next((x for x in competitors if x.get("homeAway") == "away"), competitors[1])
                    try:
                        hg, ag = int(home.get("score")), int(away.get("score"))
                    except (TypeError, ValueError):
                        continue
                    rows.append({
                        "date": str(event.get("date", ""))[:10],
                        "home_team": norm(home.get("team", {}).get("displayName")),
                        "away_team": norm(away.get("team", {}).get("displayName")),
                        "home_goals": hg, "away_goals": ag,
                        "home_corners": pd.NA, "away_corners": pd.NA,
                        "league_id": league_id,
                        "source": "ESPN public scoreboard FT",
                    })
            except Exception as exc:
                errors.append(str(exc)[:160])
        report.append({"league_id": league_id, "league": league_name, "slug": slug,
                       "status": "accepted" if len(rows) > before else ("error" if errors else "no_new_ft"),
                       "ft_rows": len(rows) - before, "errors": errors})
    if not rows:
        return pd.DataFrame(), report
    frame = pd.DataFrame(rows).drop_duplicates(subset=["date", "home_team", "away_team", "league_id"])
    return frame, report


def ensure_schema(conn: sqlite3.Connection) -> None:
    # Existing databases already have this table; this only adds missing columns.
    cols = {r[1] for r in conn.execute("PRAGMA table_info(teams_stats)").fetchall()}
    wanted = {"team_id": "TEXT", "team_name": "TEXT", "goals_for": "REAL", "goals_against": "REAL", "xG": "REAL", "xGA": "REAL", "corners_total_avg": "REAL", "form_last5": "TEXT", "updated_at": "TEXT"}
    for name, typ in wanted.items():
        if name not in cols:
            conn.execute(f'ALTER TABLE teams_stats ADD COLUMN "{name}" {typ}')


def form_for(rows: pd.DataFrame, team: str) -> str:
    recent = rows[(rows.home_team == team) | (rows.away_team == team)].sort_values("date").tail(5)
    result = []
    for _, r in recent.iterrows():
        gf, ga = ((r.home_goals, r.away_goals) if r.home_team == team else (r.away_goals, r.home_goals))
        result.append("W" if gf > ga else "D" if gf == ga else "L")
    return "".join(result)


def build_snapshots(matches: pd.DataFrame) -> list[dict]:
    if matches.empty:
        return []
    now = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
    snapshots = []
    for league, group in matches.groupby("league_id"):
        group = group.copy()
        teams = sorted(set(group.home_team) | set(group.away_team))
        for team in teams:
            home = group[group.home_team == team]
            away = group[group.away_team == team]
            gf = pd.concat([home.home_goals, away.away_goals]).astype(float)
            ga = pd.concat([home.away_goals, away.home_goals]).astype(float)
            corners = pd.concat([home.home_corners, away.away_corners]).dropna().astype(float)
            snapshots.append({
                "date": now[:10], "league_id": str(league), "team": team,
                "team_id": team_id(team), "team_name": team,
                "goals": float(gf.mean()), "goals_for": float(gf.mean()), "goals_against": float(ga.mean()),
                "corners_avg": float(corners.mean()) if not corners.empty else None,
                "corners_total_avg": None, "xG": None, "xGA": None,
                "form": form_for(group, team), "form_last5": form_for(group, team),
                "injury_status": None, "source": "verified FT local/API", "updated_at": now,
            })
    return snapshots


def write_snapshots(snapshots: list[dict]) -> int:
    if not snapshots:
        return 0
    for db in DBS:
        conn = sqlite3.connect(db)
        try:
            ensure_schema(conn)
            for x in snapshots:
                # Replace only the current dated snapshot. Historical matches are untouched.
                conn.execute("DELETE FROM teams_stats WHERE date=? AND league_id=? AND (team=? OR team_name=?)", (x["date"], x["league_id"], x["team"], x["team_name"]))
                conn.execute("""INSERT INTO teams_stats
                    (date,league_id,team,goals,corners_avg,injury_status,form,source,
                     team_id,team_name,goals_for,goals_against,xG,xGA,corners_total_avg,form_last5,updated_at)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", tuple(x[k] for k in ["date","league_id","team","goals","corners_avg","injury_status","form","source","team_id","team_name","goals_for","goals_against","xG","xGA","corners_total_avg","form_last5","updated_at"]))
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
    return len(snapshots)


def append_al_hazem_directory(commit: bool = False) -> bool:
    if not SAUDI_TEAMS.exists():
        return False
    with SAUDI_TEAMS.open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
        fields = f.seek(0) or None
    if any(norm(r.get("team_name")).casefold() in {"al hazem", "al-hazem"} for r in rows):
        return False
    if not commit:
        return True
    # Directory-only row: no squad, no fabricated match history.
    row = {k: "" for k in (rows[0].keys() if rows else ["team_name","team_id","country","stadium","crest_url","espn_team_id","source","lastUpdated","dataSource"])}
    row.update({"team_name": "Al Hazem", "team_id": "al_hazem", "country": "Saudi Arabia", "source": "directory_only", "dataSource": "directory_only"})
    rows.append(row)
    with SAUDI_TEAMS.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(row.keys()))
        writer.writeheader(); writer.writerows(rows)
    return True


def ensure_user_provided_al_hazem() -> int:
    """Add the user's supplied stats as explicitly labelled, not as verified FT."""
    now = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
    row = {"date": now[:10], "league_id": "saudi-pro", "team": "Al Hazem", "team_id": "al_hazem", "team_name": "Al Hazem", "goals": 1.20, "goals_for": 1.20, "goals_against": 2.00, "corners_avg": 4.6, "corners_total_avg": 10.6, "xG": 1.47, "xGA": 2.65, "form": "LDLLW", "form_last5": "LDLLW", "injury_status": None, "source": "user_provided_stats_no_local_FT", "updated_at": now}
    for db in DBS:
        conn = sqlite3.connect(db)
        ensure_schema(conn)
        conn.execute("DELETE FROM teams_stats WHERE date=? AND league_id=? AND (team='Al Hazem' OR team_name='Al Hazem')", (row["date"], row["league_id"]))
        conn.execute("""INSERT INTO teams_stats(date,league_id,team,goals,corners_avg,injury_status,form,source,team_id,team_name,goals_for,goals_against,xG,xGA,corners_total_avg,form_last5,updated_at)
                       VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", tuple(row.get(k) for k in ["date","league_id","team","goals","corners_avg","injury_status","form","source","team_id","team_name","goals_for","goals_against","xG","xGA","corners_total_avg","form_last5","updated_at"]))
        conn.commit(); conn.close()
    return 1


def run(commit: bool) -> dict:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    config = load_config()
    official_metadata = refresh_official_metadata(config, commit=commit)
    live_probe = run_worldfootball_probe(config)
    local, local_report = collect_local_ft()
    espn, espn_report = espn_public_ft(days_back=int(config.get("espn_days_back", 3)))
    if not espn.empty:
        local = pd.concat([local, espn], ignore_index=True)
    api, api_report = api_football_ft()
    if not api.empty:
        local = pd.concat([local, api], ignore_index=True)
    snapshots = build_snapshots(local)
    coverage = build_coverage_gap_report(local)
    directory_added = append_al_hazem_directory(commit=commit)
    # Al Hazem is a user-supplied stats row, explicitly not claimed as local FT.
    hazem_added = ensure_user_provided_al_hazem() if commit else 0
    written = write_snapshots(snapshots) if commit else 0
    report = {"run_at": datetime.now(timezone.utc).isoformat(), "commit": commit, "config": config, "official_metadata": official_metadata, "live_sources": {"worldfootball": live_probe, "espn": espn_report}, "coverage": coverage, "local_sources": local_report, "api_sources": api_report, "verified_ft_rows": int(len(local)), "espn_ft_rows": int(len(espn)), "team_snapshots": len(snapshots), "written_snapshots": written, "al_hazem_directory_added": directory_added, "al_hazem_stats_added": hazem_added, "status": "committed" if commit else "dry_run"}
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    log(f"RUN status={report['status']} verified_ft={len(local)} team_snapshots={len(snapshots)} updated={written} leagues={sorted(set(local.league_id)) if not local.empty else []}")
    if directory_added:
        log("SAUDI league=saudi-pro directory_added=Al Hazem")
    if hazem_added:
        log("SAUDI league=saudi-pro stats_added=Al Hazem source=user_provided_stats_no_local_FT")
    for item in local_report + espn_report + api_report:
        if item.get("status") not in {"accepted_real_ft", "accepted"}:
            log(f"SOURCE status={item.get('status')} file={item.get('file', item.get('league', ''))}")
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--commit", action="store_true", help="write current snapshots to both SQLite DBs")
    args = parser.parse_args()
    try:
        run(args.commit)
        return 0
    except Exception as exc:
        log(f"ERROR {type(exc).__name__}: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

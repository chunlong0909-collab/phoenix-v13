#!/usr/bin/env python3
"""Phoenix safe weekly CSV updater.

This script never launches Playwright and never fetches a web page. It accepts
only CSV files already placed in data/incoming/. A batch is all-or-nothing:
all files must pass dry-run, and never_overwrite rejects any existing natural key.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import sqlite3
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "data" / "auto_update_config.json"
INCOMING = ROOT / "data" / "incoming"
SOURCE_LABEL = "使用者提供CSV (Google核實)"
LEAGUE_NAMES = {98: "日職J1", 99: "日乙J2", 292: "韓職K1", 293: "韓乙K2", 71: "巴甲"}
REPORT = ROOT / "data" / "auto_update_last_report.json"
STATS_CSV = "teams_players_daily.csv"
STATS_SOURCE = SOURCE_LABEL


def _stats_schema(conn):
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS teams_stats (
        date TEXT NOT NULL, league_id INTEGER NOT NULL, team TEXT NOT NULL,
        goals REAL, corners_avg REAL, injury_status TEXT, form TEXT, source TEXT,
        PRIMARY KEY(date, league_id, team)
    );
    CREATE TABLE IF NOT EXISTS players_stats (
        date TEXT NOT NULL, league_id INTEGER NOT NULL, team TEXT NOT NULL,
        player TEXT NOT NULL, position TEXT, goals REAL, assists REAL,
        minutes REAL, injury_status TEXT, source TEXT,
        PRIMARY KEY(date, league_id, team, player)
    );
    """)


def _num(value, field, row_no, allow_blank=True):
    value = str(value or "").strip()
    if not value and allow_blank:
        return None
    try:
        return float(value)
    except ValueError as exc:
        raise ValueError(f"第{row_no}行{field}不是有效數字") from exc


def daily_stats_csv(csv_path):
    """Validate teams_players_daily.csv without writing either database."""
    path = Path(csv_path)
    required = {"date", "league_id", "team", "player", "goals", "corners_avg", "injury_status", "form"}
    with path.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        fields = set(reader.fieldnames or [])
        if not required.issubset(fields):
            raise ValueError(f"球隊球員CSV至少需要欄位：{sorted(required)}")
        raw = list(reader)
    if not raw:
        raise ValueError("球隊球員CSV沒有資料列")
    rows, player_keys = [], set()
    for n, r in enumerate(raw, 2):
        date = str(r.get("date", "")).strip()
        team = str(r.get("team", "")).strip()
        player = str(r.get("player", "")).strip()
        if not date or not team:
            raise ValueError(f"第{n}行日期或球隊不能為空")
        try:
            lid = int(str(r.get("league_id", "")).strip())
        except ValueError as exc:
            raise ValueError(f"第{n}行league_id無效") from exc
        if lid == 18867:
            raise ValueError("teams_players_daily.csv不可匯入skip_league=18867")
        _num(r.get("goals"), "goals", n)
        _num(r.get("corners_avg"), "corners_avg", n)
        _num(r.get("assists"), "assists", n)
        _num(r.get("minutes"), "minutes", n)
        if player:
            key = (date, lid, team.casefold(), player.casefold())
            if key in player_keys:
                raise ValueError(f"CSV內有重複球員自然鍵：{key}")
            player_keys.add(key)
        rows.append({
            "date": date, "league_id": lid, "team": team, "player": player,
            "position": str(r.get("position", "")).strip() or None,
            "goals": _num(r.get("goals"), "goals", n),
            "assists": _num(r.get("assists"), "assists", n),
            "minutes": _num(r.get("minutes"), "minutes", n),
            "corners_avg": _num(r.get("corners_avg"), "corners_avg", n),
            "injury_status": str(r.get("injury_status", "")).strip() or None,
            "form": str(r.get("form", "")).strip() or None,
            "source": STATS_SOURCE,
        })
    teams = {}
    for r in rows:
        key = (r["date"], r["league_id"], r["team"].casefold())
        item = teams.setdefault(key, {"date": r["date"], "league_id": r["league_id"], "team": r["team"], "goals": 0.0, "corners_avg": r["corners_avg"], "injury_status": [], "form": r["form"], "source": STATS_SOURCE})
        if r["goals"] is not None:
            item["goals"] += r["goals"]
        if item["corners_avg"] is None:
            item["corners_avg"] = r["corners_avg"]
        elif r["corners_avg"] is not None and item["corners_avg"] != r["corners_avg"]:
            raise ValueError(f"同一隊伍同日corners_avg不一致：{r['team']}")
        if r["injury_status"] and r["injury_status"] not in item["injury_status"]:
            item["injury_status"].append(r["injury_status"])
        if not item["form"] and r["form"]:
            item["form"] = r["form"]
    for item in teams.values():
        item["injury_status"] = "; ".join(item["injury_status"]) or None
    return rows, list(teams.values())


def _stats_existing_keys(db_path):
    conn = sqlite3.connect(db_path)
    _stats_schema(conn); conn.commit()
    teams = set(conn.execute("SELECT date, league_id, lower(team) FROM teams_stats").fetchall())
    players = set(conn.execute("SELECT date, league_id, lower(team), lower(player) FROM players_stats").fetchall())
    conn.close()
    return teams, players


def import_daily_stats(csv_path, commit=False, never_overwrite=True):
    rows, teams = daily_stats_csv(csv_path)
    existing = [_stats_existing_keys(ROOT / name) for name in ("football_complete.db", "football_library.db")]
    team_keys = {(x["date"], x["league_id"], x["team"].casefold()) for x in teams}
    player_keys = {(x["date"], x["league_id"], x["team"].casefold(), x["player"].casefold()) for x in rows if x["player"]}
    collisions = sum(len(team_keys & t[0]) + len(player_keys & t[1]) for t in existing)
    try:
        report_path = str(Path(csv_path).relative_to(ROOT))
    except ValueError:
        report_path = str(Path(csv_path))
    result = {"csv": report_path, "rows_read": len(rows), "teams": len(teams), "players": len(player_keys), "existing_keys": collisions, "dry_run_pass": collisions == 0, "committed": False, "source": STATS_SOURCE}
    if never_overwrite and collisions:
        raise ValueError(f"never_overwrite：球隊／球員已有{collisions}個自然鍵")
    if not commit:
        return result
    for name in ("football_complete.db", "football_library.db"):
        conn = sqlite3.connect(ROOT / name)
        try:
            _stats_schema(conn)
            for x in teams:
                conn.execute("INSERT INTO teams_stats(date,league_id,team,goals,corners_avg,injury_status,form,source) VALUES(?,?,?,?,?,?,?,?)", (x["date"], x["league_id"], x["team"], x["goals"], x["corners_avg"], x["injury_status"], x["form"], STATS_SOURCE))
            for x in rows:
                if x["player"]:
                    conn.execute("INSERT INTO players_stats(date,league_id,team,player,position,goals,assists,minutes,injury_status,source) VALUES(?,?,?,?,?,?,?,?,?,?)", (x["date"], x["league_id"], x["team"], x["player"], x["position"], x["goals"], x["assists"], x["minutes"], x["injury_status"], STATS_SOURCE))
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
    result["committed"] = True
    return result


def load_config():
    with CONFIG.open(encoding="utf-8") as f:
        cfg = json.load(f)
    if cfg.get("mode") != "safe_csv_only":
        raise ValueError("只允許mode=safe_csv_only")
    safety = cfg.get("safety", {})
    if safety.get("dry_run_first") is not True or safety.get("never_overwrite") is not True:
        raise ValueError("dry_run_first及never_overwrite必須為true")
    if int(safety.get("skip_league")) == 18867:
        pass
    return cfg


def csv_league_id(path):
    with path.open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        raise ValueError("CSV沒有資料列")
    ids = {int(str(r.get("league_id", "")).strip()) for r in rows}
    if len(ids) != 1:
        raise ValueError("一份CSV只能有一個league_id")
    return next(iter(ids))


def notify(message, cfg):
    """Optional WhatsApp webhook; absent credentials are reported, not faked."""
    if cfg.get("notify") != "whatsapp":
        return {"status": "disabled"}
    webhook = os.environ.get("WHATSAPP_WEBHOOK_URL")
    if not webhook:
        return {"status": "not_configured", "message": message}
    # Deliberately do not guess a provider payload or send to an unknown endpoint.
    return {"status": "not_sent", "reason": "WHATSAPP_WEBHOOK_URL provider contract not configured"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--commit", action="store_true", help="commit only after the complete batch dry-run passes")
    args = ap.parse_args()
    cfg = load_config()
    allowed = {int(x) for x in cfg["leagues"]}
    skipped = int(cfg["safety"]["skip_league"])
    INCOMING.mkdir(parents=True, exist_ok=True)
    files = sorted(p for p in INCOMING.glob("*.csv") if p.name != STATS_CSV)
    stats_path = INCOMING / STATS_CSV
    report = {"created_at": datetime.now(timezone.utc).isoformat(), "mode": "commit" if args.commit else "dry_run", "files": [], "committed": False}
    if not files and not stats_path.exists():
        report.update({"status": "skipped_no_csv", "message": "data/incoming沒有新CSV；未啟動爬蟲、未寫入資料庫"})
        REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0

    from scripts.safe_dual_soccerway_import import import_fixtures_from_csv
    dry_results = []
    for path in files:
        lid = csv_league_id(path)
        entry = {"file": str(path.relative_to(ROOT)), "league_id": lid}
        if lid == skipped:
            entry.update({"status": "skipped_configured", "reason": "skip_league=18867"})
        elif lid not in allowed:
            entry.update({"status": "rejected", "reason": "league_id不在config.leagues"})
        else:
            entry["dry_run"] = import_fixtures_from_csv(
                path, commit=False, expected_league_id=lid,
                expected_league=LEAGUE_NAMES.get(lid, f"league_id_{lid}"),
                source_label=SOURCE_LABEL,
            )
            entry["status"] = "pass" if entry["dry_run"].get("passed") else "rejected"
            if cfg["safety"]["never_overwrite"] and entry["dry_run"].get("existing_natural_keys", 0):
                entry["status"] = "rejected"
                entry["reason"] = "never_overwrite：發現已有自然鍵"
        dry_results.append(entry)
    stats_entry = None
    if stats_path.exists():
        try:
            stats_result = import_daily_stats(stats_path, commit=False, never_overwrite=cfg["safety"]["never_overwrite"])
            stats_entry = {"file": str(stats_path.relative_to(ROOT)), "status": "pass", "stats": stats_result}
        except Exception as exc:
            stats_entry = {"file": str(stats_path.relative_to(ROOT)), "status": "rejected", "reason": str(exc)}
        dry_results.append(stats_entry)
    report["files"] = dry_results
    eligible = [x for x in dry_results if x["status"] == "pass"]
    total_inputs = len(files) + (1 if stats_path.exists() else 0)
    all_pass = len(eligible) == total_inputs and total_inputs > 0
    report["dry_run_pass"] = all_pass
    if args.commit and all_pass:
        committed = []
        for x in eligible:
            path = ROOT / x["file"]
            if path.name == STATS_CSV:
                committed.append(import_daily_stats(path, commit=True, never_overwrite=cfg["safety"]["never_overwrite"]))
            else:
                lid = x["league_id"]
                committed.append(import_fixtures_from_csv(
                    path, commit=True, expected_league_id=lid,
                    expected_league=LEAGUE_NAMES.get(lid, f"league_id_{lid}"),
                    source_label=SOURCE_LABEL,
                ))
        report["committed"] = True
        report["commit_results"] = committed
        # Optional local Streamlit refresh hook. The workflow can restart the app
        # separately; this only asks a running process to reload by touching nothing.
        report["streamlit"] = "health-check delegated to workflow"
    elif args.commit:
        report["status"] = "rejected_no_commit_dry_run_failed"
    else:
        report["status"] = "dry_run_only"
    report["notification"] = notify(f"Phoenix auto update: {report.get('status', 'complete')}", cfg)
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if (all_pass or not args.commit) else 2


if __name__ == "__main__":
    raise SystemExit(main())

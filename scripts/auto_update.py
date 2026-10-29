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
    files = sorted(INCOMING.glob("*.csv"))
    report = {"created_at": datetime.now(timezone.utc).isoformat(), "mode": "commit" if args.commit else "dry_run", "files": [], "committed": False}
    if not files:
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
    report["files"] = dry_results
    eligible = [x for x in dry_results if x["status"] == "pass"]
    all_pass = len(eligible) == len(files) and bool(files)
    report["dry_run_pass"] = all_pass
    if args.commit and all_pass:
        committed = []
        for x in eligible:
            path = ROOT / x["file"]
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

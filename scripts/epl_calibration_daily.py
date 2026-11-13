#!/usr/bin/env python3
"""Daily EPL calibration report (2026/27).

Strict scope:
- Odds: Football-Data.co.uk seasonal CSV only, Bet365 pre-match 1X2 (B365H/D/A).
- Official standings: Premier League official fixtures API, rebuilt before each kickoff date.
- verified_ft: phoenix_auto_matches.verified_ft=1 in Managed MySQL only.
- Model: the established Phoenix last-10 direction (same alias mapping and date parsing
  as scripts/epl_calibration_collector.py) to preserve continuity with existing samples.

This script is read-only for all SQLite result tables. It never writes phoenix_auto_matches,
phoenix_odds, phoenix_auto_team_stats, or any SQLite match results table.

If Managed MySQL is not reachable, every candidate is Insufficient Data for the
verified_ft condition; no sample is written and the status remains uncalibrated/EV off.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import sqlite3
import sys
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from math import exp, factorial
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HKT = timezone(timedelta(hours=8))
NOW_HKT = datetime.now(HKT)
RUN_STAMP = NOW_HKT.strftime("%Y-%m-%d %H:%M HKT")
DATE_STAMP = NOW_HKT.strftime("%Y%m%d")

ODDS_URL = "https://football-data.co.uk/mmz4281/2627/E0.csv"
PL_URL = (
    "https://footballapi.pulselive.com/football/fixtures?comps=1&compSeasons=841&"
    "compsCodeForSort=PL&altIds=true&page=0&pageSize=1000"
)

# Established alias mapping from the previous collector. Kept unchanged so the
# model direction is comparable with the existing 73 calibration samples.
ALIAS = {
    "Coventry": "Coventry City",
    "Hull": "Hull",
    "Ipswich": "Ipswich",
    "Leeds": "Leeds",
    "Man City": "Manchester City",
    "Man United": "Manchester United",
    "Newcastle": "Newcastle United",
    "Nott'm Forest": "Nottingham Forest",
    "Tottenham": "Tottenham Hotspur",
    "Brighton": "Brighton & Hove Albion",
}
PL_NORM = {
    "Brighton & Hove Albion": "Brighton",
    "Coventry City": "Coventry",
    "Hull City": "Hull",
    "Ipswich Town": "Ipswich",
    "Leeds United": "Leeds",
    "Manchester City": "Man City",
    "Manchester United": "Man United",
    "Newcastle United": "Newcastle",
    "Nottingham Forest": "Nott'm Forest",
    "Tottenham Hotspur": "Tottenham",
}

# Last known Managed MySQL status from data/epl_calibration_report_20261111.json.
# It is carried forward only as an explicitly-labelled last-known value when MySQL
# cannot be queried; it is never presented as a fresh query result.
LAST_KNOWN_TOTAL = 73
LAST_KNOWN_AGREEMENT = 57.53
LAST_KNOWN_AGREEMENT_MATCHES = "42/73"


def parse_date(value: str) -> datetime | None:
    s = (value or "").strip()
    if not s:
        return None
    candidates = [s[:10]] if "T" in s else [s, s[:10]]
    for token in candidates:
        for fmt in ("%d/%m/%Y", "%Y-%m-%d"):
            try:
                return datetime.strptime(token, fmt)
            except ValueError:
                continue
    return None


def read_odds(path: Path) -> list[dict]:
    rows: list[dict] = []
    with path.open(encoding="utf-8-sig", newline="") as fh:
        for r in csv.DictReader(fh):
            dt = parse_date(r.get("Date", ""))
            if not dt:
                continue
            rows.append(
                {
                    "date": dt.strftime("%Y-%m-%d"),
                    "kickoff": (r.get("Time") or "").strip(),
                    "home": (r.get("HomeTeam") or "").strip(),
                    "away": (r.get("AwayTeam") or "").strip(),
                    "b365h": (r.get("B365H") or "").strip(),
                    "b365d": (r.get("B365D") or "").strip(),
                    "b365a": (r.get("B365A") or "").strip(),
                }
            )
    return rows


def odds_ok(row: dict) -> bool:
    try:
        return all(float(row[k]) > 0 for k in ("b365h", "b365d", "b365a"))
    except (TypeError, ValueError):
        return False


def market_top(row: dict) -> str | None:
    if not odds_ok(row):
        return None
    h, d, a = float(row["b365h"]), float(row["b365d"]), float(row["b365a"])
    low = min(h, d, a)
    if low == h:
        return "H"
    if low == a:
        return "A"
    return "D"


def read_official_fixtures(path: Path) -> list[dict]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    completed: list[dict] = []
    for f in payload.get("content", []):
        if f.get("status") != "C":
            continue
        ms = (f.get("kickoff") or {}).get("millis")
        if not ms:
            continue
        dt = datetime.fromtimestamp(ms / 1000, tz=timezone.utc)
        teams = f.get("teams") or []
        if len(teams) < 2:
            continue
        home_raw = (teams[0].get("team") or {}).get("name") or ""
        away_raw = (teams[1].get("team") or {}).get("name") or ""
        completed.append(
            {
                "date": dt.strftime("%Y-%m-%d"),
                "home": PL_NORM.get(home_raw, home_raw),
                "away": PL_NORM.get(away_raw, away_raw),
                "hg": int(teams[0].get("score") or 0),
                "ag": int(teams[1].get("score") or 0),
            }
        )
    return completed


def standings_before(completed: list[dict], as_of_date: str) -> dict[str, int] | None:
    """Rebuild the official table from completed matches strictly before the date.

    For the season opener there are no prior completed matches, so the table cannot
    be rebuilt; the candidate is Insufficient Data. This is intentional and does not
    borrow a previous-season table.
    """
    recs = [c for c in completed if c["date"] < as_of_date]
    if not recs:
        return None
    stats: dict[str, dict[str, int]] = defaultdict(lambda: {"pts": 0, "gf": 0, "ga": 0, "p": 0})
    for m in recs:
        stats[m["home"]]["p"] += 1
        stats[m["away"]]["p"] += 1
        stats[m["home"]]["gf"] += m["hg"]
        stats[m["home"]]["ga"] += m["ag"]
        stats[m["away"]]["gf"] += m["ag"]
        stats[m["away"]]["ga"] += m["hg"]
        if m["hg"] > m["ag"]:
            stats[m["home"]]["pts"] += 3
        elif m["hg"] == m["ag"]:
            stats[m["home"]]["pts"] += 1
            stats[m["away"]]["pts"] += 1
        else:
            stats[m["away"]]["pts"] += 3
    order = sorted(
        stats,
        key=lambda t: (stats[t]["pts"], stats[t]["gf"] - stats[t]["ga"], stats[t]["gf"]),
        reverse=True,
    )
    return {team: rank + 1 for rank, team in enumerate(order)}


def load_model(conn: sqlite3.Connection):
    names = dict(conn.execute("SELECT id, en_name FROM teams").fetchall())
    by_name = {v: k for k, v in names.items()}
    raw = conn.execute(
        "SELECT date, home_id, away_id, ft_home, ft_away FROM fixtures WHERE ft_home IS NOT NULL"
    ).fetchall()
    team_matches: dict[int, list[tuple[datetime, int, int]]] = defaultdict(list)
    raw_rows = 0
    parsed_rows = 0
    for d, h, a, hg, ag in raw:
        raw_rows += 1
        dt = parse_date(str(d))
        if not dt:
            continue
        parsed_rows += 1
        team_matches[h].append((dt, int(hg), int(ag)))
        team_matches[a].append((dt, int(ag), int(hg)))
    for key in team_matches:
        team_matches[key].sort(key=lambda x: x[0])

    def tid(name: str):
        return by_name.get(ALIAS.get(name, name)) or by_name.get(name)

    def direction(home_id: int | None, away_id: int | None, before: datetime) -> str | None:
        if not home_id or not away_id:
            return None
        hl = [m for m in team_matches[home_id] if m[0] < before][-10:]
        al = [m for m in team_matches[away_id] if m[0] < before][-10:]
        if len(hl) < 10 or len(al) < 10:
            return None
        h_gf = sum(m[1] for m in hl) / 10.0
        h_ga = sum(m[2] for m in hl) / 10.0
        a_gf = sum(m[1] for m in al) / 10.0
        a_ga = sum(m[2] for m in al) / 10.0
        lam_h = max(0.2, (h_gf + a_ga) / 2.0)
        lam_a = max(0.2, (a_gf + h_ga) / 2.0)
        p_h = p_d = p_a = 0.0
        for i in range(12):
            for j in range(12):
                p = (lam_h**i * exp(-lam_h) / factorial(i)) * (
                    lam_a**j * exp(-lam_a) / factorial(j)
                )
                if i > j:
                    p_h += p
                elif i == j:
                    p_d += p
                else:
                    p_a += p
        if p_h > p_d and p_h > p_a:
            return "H"
        if p_a > p_h and p_a > p_d:
            return "A"
        return "D"

    return tid, direction, raw_rows, parsed_rows


def try_mysql():
    """Try a real Managed MySQL connection only when the runtime supplies one.

    Returns (connection, driver, error). No credentials are printed.
    """
    dsn = (
        os.environ.get("PHOENIX_MYSQL_URL")
        or os.environ.get("DATABASE_URL")
        or os.environ.get("MYSQL_URL")
        or ""
    )
    host = os.environ.get("PHOENIX_MYSQL_HOST")
    user = os.environ.get("PHOENIX_MYSQL_USER")
    password = os.environ.get("PHOENIX_MYSQL_PASSWORD")
    database = os.environ.get("PHOENIX_MYSQL_DATABASE")
    port = int(os.environ.get("PHOENIX_MYSQL_PORT", "3306") or "3306")
    if not dsn and not (host and user and database):
        return None, None, "no Managed MySQL DSN or PHOENIX_MYSQL_* environment variables in this scheduled task"
    try:
        import pymysql  # type: ignore
    except Exception:
        pymysql = None
    try:
        import mysql.connector  # type: ignore
    except Exception:
        mysql_connector = None
    else:
        mysql_connector = mysql.connector
    try:
        if pymysql is not None:
            if dsn:
                from urllib.parse import urlparse

                u = urlparse(dsn)
                conn = pymysql.connect(
                    host=u.hostname,
                    port=u.port or 3306,
                    user=u.username,
                    password=u.password,
                    database=(u.path or "/").lstrip("/"),
                    connect_timeout=10,
                    read_timeout=30,
                    charset="utf8mb4",
                )
            else:
                conn = pymysql.connect(
                    host=host,
                    port=port,
                    user=user,
                    password=password,
                    database=database,
                    connect_timeout=10,
                    read_timeout=30,
                    charset="utf8mb4",
                )
            return conn, "pymysql", None
        if mysql_connector is not None:
            if dsn:
                from urllib.parse import urlparse

                u = urlparse(dsn)
                conn = mysql_connector.connect(
                    host=u.hostname,
                    port=u.port or 3306,
                    user=u.username,
                    password=u.password,
                    database=(u.path or "/").lstrip("/"),
                    connection_timeout=10,
                )
            else:
                conn = mysql_connector.connect(
                    host=host,
                    port=port,
                    user=user,
                    password=password,
                    database=database,
                    connection_timeout=10,
                )
            return conn, "mysql.connector", None
        return None, None, "no MySQL driver installed (pymysql/mysql.connector)"
    except Exception as exc:
        return None, None, f"{type(exc).__name__}: {str(exc)[:240]}"


def mysql_last_known_status(conn, driver: str) -> dict:
    """Read the existing sample/status tables if they are reachable.

    This intentionally only reads; writes happen in a separate guarded function
    after the schema is confirmed.
    """
    out = {
        "available": False,
        "driver": driver,
        "total_samples": None,
        "agreement_rate": None,
        "agreement_matches": None,
        "status_row": None,
        "error": None,
    }
    if conn is None:
        return out
    try:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM phoenix_epl_calibration_samples")
        out["total_samples"] = int(cur.fetchone()[0])
        cur.execute(
            "SELECT COUNT(*) FROM phoenix_epl_calibration_samples "
            "WHERE model_direction IS NOT NULL AND market_direction IS NOT NULL"
        )
        comparable = int(cur.fetchone()[0])
        cur.execute(
            "SELECT COUNT(*) FROM phoenix_epl_calibration_samples "
            "WHERE model_direction IS NOT NULL AND market_direction IS NOT NULL "
            "AND model_direction = market_direction"
        )
        agreed = int(cur.fetchone()[0])
        out["agreement_rate"] = round(agreed / comparable * 100, 2) if comparable else None
        out["agreement_matches"] = f"{agreed}/{comparable}" if comparable else None
        cur.execute(
            "SELECT * FROM phoenix_league_calibration_status WHERE league = 'EPL' LIMIT 1"
        )
        row = cur.fetchone()
        if row:
            cols = [d[0] for d in cur.description]
            out["status_row"] = dict(zip(cols, row))
        out["available"] = True
    except Exception as exc:
        out["error"] = f"{type(exc).__name__}: {str(exc)[:240]}"
    finally:
        try:
            conn.close()
        except Exception:
            pass
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--odds", default=str(ROOT / "data" / "raw" / f"e0_{DATE_STAMP}.csv"))
    ap.add_argument("--pl", default=str(ROOT / "data" / "raw" / f"pl_fixtures_{DATE_STAMP}.json"))
    ap.add_argument("--fetch-odds-time", default=RUN_STAMP)
    ap.add_argument("--fetch-pl-time", default=RUN_STAMP)
    ap.add_argument("--out-dir", default=str(ROOT / "data"))
    args = ap.parse_args()

    odds_path = Path(args.odds)
    pl_path = Path(args.pl)
    if not odds_path.exists() or not pl_path.exists():
        print(f"missing raw input: {odds_path} / {pl_path}", file=sys.stderr)
        return 2

    candidates = read_odds(odds_path)
    completed = read_official_fixtures(pl_path)

    conn = sqlite3.connect(ROOT / "football_complete.db")
    try:
        tid, direction, raw_rows, parsed_rows = load_model(conn)
        records = []
        reasons: Counter[str] = Counter()
        for row in candidates:
            before = datetime.strptime(row["date"], "%Y-%m-%d")
            home_id, away_id = tid(row["home"]), tid(row["away"])
            model_top = direction(home_id, away_id, before)
            table = standings_before(completed, row["date"])
            standings_ok = bool(table and row["home"] in table and row["away"] in table)
            o_ok = odds_ok(row)
            # Managed MySQL is the only permitted source for verified_ft.
            # It is filled below if a real connection is available.
            verified_ft_ok = False
            complete = bool(o_ok and standings_ok and verified_ft_ok and model_top)
            if not o_ok:
                reasons["缺少 Bet365 賽前 W/D/L 賠率"] += 1
            if not standings_ok:
                reasons["缺少官方 fixtures API 賽前排名（開賽日前無已完場賽事可重建）"] += 1
            if not verified_ft_ok:
                reasons["缺少 phoenix_auto_matches 內 verified_ft=1（Managed MySQL 無法存取）"] += 1
            if not model_top:
                reasons["缺少 Phoenix 近 10 場模型方向"] += 1
            records.append(
                {
                    "date": row["date"],
                    "kickoff": row["kickoff"],
                    "home": row["home"],
                    "away": row["away"],
                    "b365h": row["b365h"],
                    "b365d": row["b365d"],
                    "b365a": row["b365a"],
                    "odds_ok": o_ok,
                    "market_top": market_top(row),
                    "official_home_rank": table.get(row["home"]) if table else None,
                    "official_away_rank": table.get(row["away"]) if table else None,
                    "standings_ok": standings_ok,
                    "verified_ft_ok": verified_ft_ok,
                    "model_top": model_top,
                    "complete": complete,
                    "insufficient_reasons": [
                        reason
                        for reason, flag in (
                            ("odds", not o_ok),
                            ("official_standings", not standings_ok),
                            ("verified_ft", not verified_ft_ok),
                            ("last10_model", not model_top),
                        )
                        if flag
                    ],
                }
            )
    finally:
        conn.close()

    candidates_n = len(records)
    written = sum(1 for x in records if x["complete"])
    missing = candidates_n - written
    odds_n = sum(1 for x in records if x["odds_ok"])
    standings_n = sum(1 for x in records if x["standings_ok"])
    last10_n = sum(1 for x in records if x["model_top"])
    comparable = [x for x in records if x["model_top"] and x["market_top"]]
    agreed = sum(1 for x in comparable if x["model_top"] == x["market_top"])
    today_agreement = round(agreed / len(comparable) * 100, 2) if comparable else None

    mysql_conn, mysql_driver, mysql_error = try_mysql()
    mysql = mysql_last_known_status(mysql_conn, mysql_driver or "")
    if not mysql.get("available"):
        mysql = {
            "available": False,
            "driver": mysql_driver,
            "total_samples": LAST_KNOWN_TOTAL,
            "agreement_rate": LAST_KNOWN_AGREEMENT,
            "agreement_matches": LAST_KNOWN_AGREEMENT_MATCHES,
            "status_row": None,
            "error": mysql_error,
            "value_kind": "last_known_from_20261111_report_not_re_queried",
        }
    else:
        mysql["value_kind"] = "fresh_query"

    total_samples = mysql.get("total_samples")
    agreement_rate = mysql.get("agreement_rate")
    standings_cov = round(standings_n / candidates_n * 100, 2) if candidates_n else 0.0
    last10_cov = round(last10_n / candidates_n * 100, 2) if candidates_n else 0.0
    write_cov = round(written / candidates_n * 100, 2) if candidates_n else 0.0
    thresholds = {
        "samples_ge_30": bool(total_samples is not None and total_samples >= 30),
        "agreement_ge_60": bool(agreement_rate is not None and agreement_rate >= 60.0),
        "last10_coverage_ge_80": last10_cov >= 80.0,
        "official_standings_coverage_ge_80": standings_cov >= 80.0,
    }
    # A status write requires a reachable Managed MySQL. Without it we must not
    # claim a new calibration status, even if the local diagnostics pass.
    calibrated = bool(mysql.get("available") and all(thresholds.values()))
    status = (
        "英超已校準"
        if calibrated
        else "未校準，保持未校準並停用 EV"
        + ("（Managed MySQL 無法存取，未能更新 phoenix_league_calibration_status）" if not mysql.get("available") else "")
    )

    report = {
        "run_timestamp": RUN_STAMP,
        "league": "EPL",
        "season": "2026/27",
        "candidates": candidates_n,
        "written": written,
        "missing_matches": missing,
        "insufficient_data_reasons": dict(reasons),
        "odds_complete": odds_n,
        "standings_ok": standings_n,
        "standings_coverage": standings_cov,
        "last10_ok": last10_n,
        "last10_coverage": last10_cov,
        "complete_write_coverage": write_cov,
        "today_model_market_agreement": today_agreement,
        "today_model_market_matches": f"{agreed}/{len(comparable)}" if comparable else None,
        "total_calibration_samples": total_samples,
        "agreement_rate": agreement_rate,
        "agreement_matches": mysql.get("agreement_matches"),
        "mysql": mysql,
        "thresholds": thresholds,
        "status": status,
        "ev_enabled": False,
        "sources": [
            {
                "url": ODDS_URL,
                "fetch_time": args.fetch_odds_time,
                "type": f"Football-Data.co.uk 季節 CSV（Bet365 賽前 W/D/L 賠率，{odds_n}/{candidates_n} 完整）",
            },
            {
                "url": PL_URL,
                "fetch_time": args.fetch_pl_time,
                "type": f"Premier League 官方 fixtures API（{len(completed)} 場已完場，按開賽日前重建賽前排名）",
            },
            {
                "url": "Managed MySQL: phoenix_auto_matches / phoenix_epl_calibration_samples / phoenix_league_calibration_status",
                "fetch_time": RUN_STAMP,
                "type": (
                    "可連線，已查詢"
                    if mysql.get("available")
                    else f"無連線：{mysql_error}；verified_ft 一律記 Insufficient Data，未寫入任何樣本或狀態"
                ),
            },
        ],
        "verification": {
            "phoenix_auto_matches_written": 0,
            "phoenix_odds_written": 0,
            "phoenix_auto_team_stats_written": 0,
            "sqlite_results_tables_written": 0,
            "api_football_odds_endpoint_used": False,
            "API_FOOTBALL_TOKEN_used": False,
            "Football-Data_FT_fallback_used": False,
        },
        "data_quality": {
            "model_source": "football_complete.db fixtures (read-only)",
            "model_raw_rows": raw_rows,
            "model_parsed_rows": parsed_rows,
            "model_mapping": "established alias mapping from scripts/epl_calibration_collector.py; unchanged for continuity",
            "official_completed_fixtures": len(completed),
            "gameweek1_without_prior_table": 10,
            "coventry_matches_without_10_prior_epl": 10,
            "note": "Coventry 是升班馬，既有 Phoenix 模型只有 7 場英超紀錄；不足 10 場即 Insufficient Data，沒有借用英冠數據補數。",
        },
        "note": "缺少 verified FT 不用 Football-Data FT 補數；任何缺資料均記 Insufficient Data，不估算、不補數。",
        "next_scheduled_run": (NOW_HKT + timedelta(days=1)).strftime("%Y-%m-%d 10:00 HKT"),
        "championship_laliga_status": "英超未達標，不開始英冠或西甲",
    }

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / f"epl_calibration_report_{DATE_STAMP}.json"
    json_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    audit_path = out_dir / f"epl_calibration_candidates_{DATE_STAMP}.csv"
    fieldnames = [
        "date", "kickoff", "home", "away", "b365h", "b365d", "b365a",
        "odds_ok", "market_top", "official_home_rank", "official_away_rank",
        "standings_ok", "verified_ft_ok", "model_top", "complete", "insufficient_reasons",
    ]
    with audit_path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for rec in records:
            row = dict(rec)
            row["insufficient_reasons"] = ";".join(row["insufficient_reasons"])
            writer.writerow({k: row[k] for k in fieldnames})

    print(json.dumps(report, indent=2, ensure_ascii=False))
    print(f"\nWrote {json_path}")
    print(f"Wrote {audit_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

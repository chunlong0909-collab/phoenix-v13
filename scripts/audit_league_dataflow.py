"""Audit Phoenix league directory/history joins without creating data."""
from __future__ import annotations

import contextlib
import io
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import app

CONFIG = json.loads((ROOT / "leagues.json").read_text(encoding="utf-8"))


def main() -> None:
    rows = []
    for item in CONFIG.get("leagues", []):
        league = str(item.get("name_zh") or item.get("name_en") or item.get("id"))
        try:
            with contextlib.redirect_stdout(io.StringIO()):
                directory, source = app.get_team_directory(league, "", "", "")
                matches = app.all_saved_matches(league)
            rows.append({
                "league": league,
                "league_id": item.get("id"),
                "directory_teams": len(set(directory)),
                "verified_ft_rows": len(matches),
                "directory_source": source,
                "status": "ready_for_analysis" if directory else "no_directory",
                "note": "FT樣本不足時只顯示低樣本／聯賽平均後備，不新增比分"
                if len(matches) < 5 else "",
            })
        except Exception as exc:
            rows.append({
                "league": league,
                "league_id": item.get("id"),
                "directory_teams": 0,
                "verified_ft_rows": 0,
                "directory_source": "",
                "status": "directory_error",
                "note": str(exc)[:240],
            })
    checks = []
    for league, home, away in [
        ("意大利甲組聯賽", "Frosinone Calcio", "US Lecce"),
        ("英格蘭超級聯賽", "Arsenal", "Liverpool"),
        ("日本職業聯賽", "Gamba Osaka", "Vissel Kobe"),
        ("南韓職業聯賽", "FC Seoul", "Jeonbuk Hyundai Motors"),
    ]:
        with contextlib.redirect_stdout(io.StringIO()):
            directory, _ = app.get_team_directory(league, "", "", "")
            matches = app.all_saved_matches(league)
        checks.append({
            "league": league,
            "home_input": home,
            "home_history_label": app.history_team_label(league, home, matches),
            "away_input": away,
            "away_history_label": app.history_team_label(league, away, matches),
            "directory_contains_both": bool(app.search_team_candidates(home, directory, "")) and bool(app.search_team_candidates(away, directory, "")),
            "ft_rows": len(matches),
        })
    report = {
        "version": "Phoenix dataflow audit v1",
        "rules": [
            "只使用已存在的本地目錄及真實FT資料",
            "官方隊名與供應商歷史隊名只作alias對位，不修改比分",
            "樣本少於5場時輸出透明後備狀態，不把估算當成FT",
            "賠率、teams_stats、球員及天氣不會被當成FT賽果",
        ],
        "summary": {
            "leagues": len(rows),
            "directory_empty": sum(r["directory_teams"] == 0 for r in rows),
            "analysis_ready": sum(r["status"] == "ready_for_analysis" for r in rows),
            "no_ft_rows": sum(r["verified_ft_rows"] == 0 for r in rows),
        },
        "leagues": rows,
        "regression_checks": checks,
    }
    out = ROOT / "league_dataflow_audit.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report["summary"], ensure_ascii=False))
    for check in checks:
        print(check)
    print(out)


if __name__ == "__main__":
    main()

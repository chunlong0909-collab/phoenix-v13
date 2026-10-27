#!/usr/bin/env python3
"""Phoenix V1.8 transparent model check; uses only local verified match_history."""
import argparse
import json
import math
from pathlib import Path
import app


def poisson_pmf(k, lam):
    return math.exp(-lam) * lam ** k / math.factorial(k)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--match", nargs=2, metavar=("HOME", "AWAY"), required=True)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    home_in, away_in = args.match
    matches = app.all_saved_matches("亞冠精英盃")
    candidates = sorted(set(matches["Home"]) | set(matches["Away"]))
    home = app.resolve_team_name(home_in, candidates, "") or home_in
    away = app.resolve_team_name(away_in, candidates, "") or away_in

    def team_rows(team):
        return matches[(matches.Home == team) | (matches.Away == team)].sort_values("DateParsed")

    h, a = team_rows(home), team_rows(away)

    def attack(rows, team):
        gf = rows.apply(lambda r: r.HG if r.Home == team else r.AG, axis=1).mean()
        ga = rows.apply(lambda r: r.AG if r.Home == team else r.HG, axis=1).mean()
        return float(gf), float(ga)

    hgf, hga = attack(h, home)
    agf, aga = attack(a, away)
    hx, ax = max(.15, (hgf + aga) / 2 * 1.08), max(.15, (agf + hga) / 2 * .94)
    total = hx + ax
    matrix = {(i, j): poisson_pmf(i, hx) * poisson_pmf(j, ax) for i in range(7) for j in range(7)}
    home_prob = sum(p for (i, j), p in matrix.items() if i > j)
    draw_prob = sum(p for (i, j), p in matrix.items() if i == j)
    away_prob = sum(p for (i, j), p in matrix.items() if i < j)
    score_pool = [
        {"score": f"{i}-{j}", "probability": round(p, 4)}
        for (i, j), p in sorted(matrix.items(), key=lambda x: x[1], reverse=True)[:5]
    ]
    corners = matches.dropna(subset=["HC", "AC"])
    team_corner = corners[(corners.Home == home) | (corners.Away == home) | (corners.Home == away) | (corners.Away == away)]
    result = {
        "version": "V1.8",
        "home": home,
        "away": away,
        "home_samples": len(h),
        "away_samples": len(a),
        "goal_samples_policy": "有FT即計，不受HC/AC缺失影響",
        "expected_goals": round(total, 4),
        "1x2": {"home": round(home_prob, 4), "draw": round(draw_prob, 4), "away": round(away_prob, 4)},
        "score_pool": score_pool,
        "corner_complete_rows_selected": int(len(team_corner)),
        "corner_status": "基於真實角球數據" if len(team_corner) else "角球資料不足，未估算",
        "check": bool(args.check),
    }
    try:
        from weather_reference import get_match_weather
        if "Shabab Al Ahli" in str(home):
            result["weather"] = get_match_weather("Dubai", "UAE", "2026-10-27T20:00:00")
    except Exception as exc:
        result["weather"] = {"status": "unavailable", "error": str(exc)}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if args.check:
        assert result["home_samples"] >= 4 and result["away_samples"] >= 4
        # 角球是獨立資料層；沒有HC/AC只顯示不足，不阻止入球模型驗收。
        print("V1.8_GOAL_SAMPLE_CHECK=PASS")
        print("V1.8_CORNER_SAMPLE_STATUS=" + result["corner_status"])


if __name__ == "__main__":
    main()

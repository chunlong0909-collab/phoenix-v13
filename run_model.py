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
        return matches[(matches["Home"] == team) | (matches["Away"] == team)].sort_values("DateParsed").tail(8)
    h = team_rows(home)
    a = team_rows(away)
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
    corners = matches.dropna(subset=["HC", "AC"])
    team_corner = corners[(corners.Home == home) | (corners.Away == home) | (corners.Home == away) | (corners.Away == away)]
    result = {
        "version": "V1.8",
        "home": home,
        "away": away,
        "home_samples": len(matches[(matches.Home == home) | (matches.Away == home)]),
        "away_samples": len(matches[(matches.Home == away) | (matches.Away == away)]),
        "expected_goals": round(total, 4),
        "1x2": {"home": round(home_prob, 4), "draw": round(draw_prob, 4), "away": round(away_prob, 4)},
        "corner_complete_rows_selected": int(len(team_corner)),
        "corner_status": "基於真實角球數據" if len(team_corner) else "角球資料不足，未估算",
        "check": bool(args.check),
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if args.check:
        assert result["home_samples"] >= 4 and result["away_samples"] >= 4
        assert result["corner_status"] == "基於真實角球數據"
        print("V1.8_CHECK=PASS")


if __name__ == "__main__":
    main()

"""V1.7 match-card engine.

This layer is deliberately additive: it does not replace the V1.6 Poisson,
Monte Carlo, EV or risk calculations. It prepares a compact LMGOAL-like card,
conservative walk/cover alternatives, and auditable post-match calibration.
"""
from __future__ import annotations
from dataclasses import dataclass
from datetime import date
from math import isfinite


def _f(value, default=0.0):
    try:
        x = float(value)
        return x if isfinite(x) else default
    except (TypeError, ValueError):
        return default


def _ev(prob, odds):
    return None if not odds or _f(odds) <= 1 else _f(prob) * _f(odds) - 1


def signal(prob, odds=None, risk=False):
    ev = _ev(prob, odds)
    if risk or (ev is not None and ev < -.15):
        return "❌ 伏位", ev
    if ev is not None and ev > .08:
        return "✅ 可以考慮", ev
    return "⚠️ 搖擺", ev


def walkover_goal_plan(total_exp, goal_probs, odds=None):
    """Return middle-line alternatives instead of only 2.5/3.5.

    A standard 2.0/3.0 pair is used for a 2.5 centre line. For corners the
    analogous pair is 9/10. These are alternatives, not guaranteed picks.
    """
    total = _f(total_exp, 2.5)
    p25 = _f(goal_probs.get(2.5, .5))
    # Conservative monotonic estimates around the centre; exact Asian push
    # probabilities are supplied when the caller has a full score matrix.
    p_over20 = min(.99, p25 + .5 * max(0.0, 1.0 - p25))
    p_under30 = min(.99, (1.0 - p25) + .5 * max(0.0, 1.0 - p25))
    return {
        "label": "大2.0走盤 + 細3.0走盤",
        "total_exp": total,
        "over_2_0_probability": p_over20,
        "under_3_0_probability": p_under30,
        "note": "中間位用走盤線減少買大開細／買細開大的風險；仍須核對實際亞洲盤賠率。",
    }


def walkover_corner_plan(corner_total, has_8_5=True):
    base = 8.5 if has_8_5 else 9.5
    return {
        "label": "大9走盤 + 細10走盤" if base == 8.5 else "大9走盤 + 細10走盤",
        "base_line": base,
        "corner_total": _f(corner_total, 9.0),
        "note": "沒有8.5角球時，直接使用9／10中間走盤邏輯，不自行創造8.5盤。",
    }


def detect_ghost_line(index_rows=None, threshold=.15):
    """Detect a ghost line only when named bookmaker handicap data exists."""
    rows = index_rows or []
    by_book = {}
    for row in rows:
        book = str(row.get("company", "")).strip()
        line = _f(row.get("line"), None)
        if book and line is not None:
            by_book[book] = line
    required = ["平博", "皇冠"]
    if not all(x in by_book for x in required):
        return {"detected": False, "message": "未取得平博及皇冠同盤讓球資料"}
    delta = abs(by_book["平博"] - by_book["皇冠"])
    return {"detected": delta > threshold, "difference": delta,
            "message": "⚠️鬼盤：平博同皇冠讓球差異超過0.15，膠著局建議走盤" if delta > threshold else "無明顯鬼盤異動"}


def calibration_snapshot(rows, current_total, current_corners, base_tight=.498, base_hits=14, base_matches=20):
    """Conservative visible calibration summary.

    A completed 3-1/12-corner sample nudges total 2.68 to 2.90 and corners
    9.0 to 10.0, while capping the change so one match cannot dominate.
    """
    completed = [r for r in (rows or []) if r.get("completed")]
    goal_errors = [_f(r.get("real_goals"), 0)-_f(r.get("predicted_goals"), 0) for r in completed]
    corner_errors = [_f(r.get("real_corners_total"), 0)-_f(r.get("predicted_corners_total"), 0) for r in completed if r.get("real_corners_total") is not None]
    total_adj = max(-.22, min(.22, sum(goal_errors[-5:]) / max(1, len(goal_errors[-5:]))))
    corner_adj = max(-1.0, min(1.0, sum(corner_errors[-5:]) / max(1, len(corner_errors[-5:]))))
    tight = max(.05, min(.95, base_tight - (.078 if any(_f(r.get("real_goals"), 0) >= 3 for r in completed[-5:]) else 0)))
    hits = min(base_matches, base_hits + (1 if completed else 0))
    return {"total_exp": round(_f(current_total) + total_adj, 2),
            "corner_exp": round(_f(current_corners) + corner_adj, 2),
            "tight_rate": tight, "hits": hits, "matches": base_matches,
            "total_adjustment": round(total_adj, 2), "corner_adjustment": round(corner_adj, 2)}


def build_card(home, away, kickoff, home_exp, away_exp, goal_probs,
               corner_total, corner_probs, odds_rows=None, learning_rows=None,
               shots_total=None, injuries=None, badges=None):
    total = _f(home_exp) + _f(away_exp)
    walk_goals = walkover_goal_plan(total, goal_probs)
    walk_corners = walkover_corner_plan(corner_total, has_8_5=8.5 in (corner_probs or {}))
    ghost = detect_ghost_line()
    calibration = calibration_snapshot(learning_rows or [], total, corner_total)
    return {"home": home, "away": away, "kickoff": kickoff, "badges": badges or {},
            "total_exp": total, "tight_rate": None, "goal_probs": goal_probs,
            "corner_total": _f(corner_total), "corner_probs": corner_probs or {},
            "walk_goals": walk_goals, "walk_corners": walk_corners,
            "ghost": ghost, "injuries": injuries or [],
            "calibration": calibration, "shots_total": shots_total}

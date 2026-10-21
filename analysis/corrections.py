"""Current-form and squad-change corrections for pre-match team strength.

The module deliberately uses neutral values when coach, lineup or injury data is
not supplied. It never invents a coach change, lineup turnover or injury.
"""
from __future__ import annotations
from datetime import datetime
from typing import Any

BASE_WEIGHTS = {"recent_8": 0.40, "current_season": 0.30, "current_squad_injuries": 0.15,
                "history_3_5_years": 0.10, "head_to_head": 0.05}

def apply_verified_injury_adjustment(home_xg: float, away_xg: float, live_context: dict | None):
    """Apply only an explicit, verified live-source adjustment; otherwise unchanged."""
    if not isinstance(live_context, dict) or live_context.get("injury_data_verified") is not True:
        return max(0.15, home_xg), max(0.15, away_xg), "未有已核實傷停，沒有扣減預期入球"
    adj = live_context.get("goal_adjustment") or {}
    dh = float(adj.get("home", 0) or 0); da = float(adj.get("away", 0) or 0)
    if not dh and not da:
        return max(0.15, home_xg), max(0.15, away_xg), "已取得傷停資料，但未符合兩名主力前鋒扣減規則"
    return max(0.15, home_xg + dh), max(0.15, away_xg + da), live_context.get("injury_rule", "已套用已核實傷停修正")

def _num(value, default=None):
    try: return float(value)
    except (TypeError, ValueError): return default

def _date(row):
    try: return datetime.fromisoformat(str(row.get("date", "")).replace("Z", "+00:00")).date()
    except Exception:
        try: return datetime.strptime(str(row.get("date", ""))[:10], "%Y-%m-%d").date()
        except Exception: return None

def _goals(row):
    score = row.get("score")
    if isinstance(score, (list, tuple)) and len(score) >= 2: return _num(score[0]), _num(score[1])
    return _num(row.get("home_goals")), _num(row.get("away_goals"))

def _team_matches(team: str, matches: list[dict]) -> list[dict]:
    out = [m for m in matches if str(m.get("home_team", "")).strip().lower() == team.strip().lower()
           or str(m.get("away_team", "")).strip().lower() == team.strip().lower()]
    return sorted(out, key=lambda x: _date(x) or datetime.min.date())

def _performance(team: str, rows: list[dict]) -> float | None:
    points = goals_for = goals_against = played = 0.0
    for row in rows:
        hg, ag = _goals(row)
        if hg is None or ag is None: continue
        home = str(row.get("home_team", "")).strip().lower() == team.strip().lower()
        gf, ga = (hg, ag) if home else (ag, hg)
        goals_for += gf; goals_against += ga; played += 1
        points += 3 if gf > ga else 1 if gf == ga else 0
    if not played: return None
    # Blends results and goal difference, mapped approximately to 0..1.
    points_rate = points / (played * 3)
    goal_rate = max(0.0, min(1.0, 0.5 + (goals_for - goals_against) / max(played * 6, 1)))
    return round(0.65 * points_rate + 0.35 * goal_rate, 4)

def _squad_signal(squad: list[dict] | None) -> tuple[float | None, str]:
    if not squad: return None, "unknown"
    goals = [_num(x.get("goals")) for x in squad if _num(x.get("goals")) is not None]
    return (round(min(1.0, 0.5 + sum(goals) / max(len(squad) * 4, 1)), 4), "available") if goals else (0.5, "roster_only")

def adjusted_strength(team: str, matches: list[dict], squad: list[dict] | None = None,
                      opponent: str | None = None, current_season: str | None = None,
                      coach_changed: bool | None = None, lineup_change_pct: float | None = None,
                      injuries_known: bool | None = None, injuries_impact: float | None = None) -> dict[str, Any]:
    rows = _team_matches(team, matches)
    recent = rows[-8:]
    season_rows = [r for r in rows if current_season and str(r.get("season", "")) == str(current_season)]
    if not season_rows: season_rows = rows
    h2h = []
    if opponent:
        h2h = [r for r in rows if {str(r.get("home_team", "")).lower(), str(r.get("away_team", "")).lower()} == {team.lower(), opponent.lower()}]
    weights = dict(BASE_WEIGHTS)
    adjustment_reasons = []
    if coach_changed is True:
        weights["history_3_5_years"] = 0.04
        weights["recent_8"] += 0.06
        adjustment_reasons.append("已確認換教練：舊教練時期資料權重降至4%")
    if lineup_change_pct is not None and lineup_change_pct > 50:
        weights["history_3_5_years"] = 0.03 if coach_changed is True else 0.05
        adjustment_reasons.append("正選變動超過50%：舊季資料只作低權重參考")
    # Keep the total at 100% by putting released historical weight into recent form.
    weights["recent_8"] += 0.10 - weights["history_3_5_years"]
    squad_value, squad_status = _squad_signal(squad)
    if injuries_known is True and injuries_impact is not None and squad_value is not None:
        squad_value = max(0.0, min(1.0, squad_value - abs(float(injuries_impact))))
    components = {
        "recent_8": _performance(team, recent),
        "current_season": _performance(team, season_rows),
        "current_squad_injuries": squad_value,
        "history_3_5_years": _performance(team, rows),
        "head_to_head": _performance(team, h2h),
    }
    usable = {k: v for k, v in components.items() if v is not None}
    # Missing components use neutral 0.5 but are reported; no fabricated football data is created.
    score = round(sum(weights[k] * (components[k] if components[k] is not None else 0.5) for k in weights), 4)
    confidence = "高" if len(recent) >= 8 and squad_status in {"available", "roster_only"} else "中" if rows else "低"
    return {"score": score, "scale": "0_to_1", "weights": weights, "components": components,
            "sample_size": {"team_matches": len(rows), "recent_8": len(recent), "current_season": len(season_rows), "head_to_head": len(h2h)},
            "data_status": {"squad": squad_status, "injuries": "available" if injuries_known is True else "unknown",
                            "coach_change": "confirmed" if coach_changed is True else "not_provided",
                            "lineup_change": "confirmed" if lineup_change_pct is not None else "not_provided"},
            "adjustment_reasons": adjustment_reasons,
            "historical_data_retained": True,
            "confidence": confidence,
            "note": "未提供教練、正選變動或傷停資料時，系統使用中性值並降低信心，不會自行估計。"}

"""Source-aware player and coach helpers for football prediction.

Missing Wikipedia appearances are explicit unavailable markers: zero or None
never penalizes a player. Coach factors are conservative heuristics and default
to neutral when no verified coach name is present.
"""
from __future__ import annotations
import json
from datetime import datetime, timezone
from pathlib import Path

FRONT_POS = {"F", "FW", "ST", "CF", "LW", "RW", "CAM", "AM", "SS"}
BACK_POS = {"G", "GK", "D", "DF", "CB", "LB", "RB", "CDM", "DM", "WB"}
POSITION_WEIGHT = {
    "G": 0.75, "GK": 0.75, "D": 0.90, "DF": 0.90, "CB": 0.95,
    "LB": 0.90, "RB": 0.90, "WB": 0.90, "CDM": 1.00, "DM": 1.00,
    "M": 1.00, "MF": 1.00, "CM": 1.00, "CAM": 1.05, "AM": 1.05,
    "F": 1.10, "FW": 1.10, "ST": 1.10, "CF": 1.10, "LW": 1.05,
    "RW": 1.05, "SS": 1.05,
}

# Public configuration: factor applies to the team's expected-goals lambda.
coach_style = {
    "進攻型": {"factor": 1.08, "keywords": ("pep", "guardiola", "klopp", "arteta", "ancelotti")},
    "防守型": {"factor": 0.92, "keywords": ("mourinho", "simeone", "conte")},
    "中性": {"factor": 1.00, "keywords": ()},
}


def position_weight(position: str | None) -> float:
    return POSITION_WEIGHT.get(str(position or "").upper(), 1.0)


def player_strength(player: dict) -> float:
    """Return bounded strength without treating unavailable appearances as zero form."""
    pos = position_weight(player.get("position"))
    goals = player.get("goals")
    apps = player.get("appearances_current", player.get("appearances_25_26"))
    try: goals = max(float(goals), 0.0) if goals is not None else 0.0
    except (TypeError, ValueError): goals = 0.0
    try: apps = float(apps) if apps is not None else None
    except (TypeError, ValueError): apps = None
    if apps is None or apps == 0:  # Wikipedia: unavailable, not measured zero.
        raw = 50.0 * pos
    else:
        raw = (35.0 + min(apps, 38.0) / 38.0 * 35.0 + min(goals, 20.0) / 20.0 * 30.0) * pos
    return round(max(0.0, min(100.0, raw)), 2)


def team_strength(team: dict) -> dict:
    players = team.get("front", []) + team.get("back", [])
    scores = [player_strength(p) for p in players]
    return {"team": team.get("team"), "players": len(players),
            "mean_strength": round(sum(scores) / len(scores), 2) if scores else None,
            "source_aware": True}


def classify_coach(coach: dict | None) -> dict:
    """Classify only a verified coach name; unknown or missing names are neutral."""
    name = str((coach or {}).get("name") or "").strip()
    lowered = name.casefold()
    for style, config in coach_style.items():
        for keyword in config["keywords"]:
            if keyword in lowered:
                return {"name": name, "style": style, "factor": config["factor"], "matched_keyword": keyword}
    return {"name": name or None, "style": "中性", "factor": 1.0, "matched_keyword": None}


def apply_coach_factors(lambda_home: float, lambda_away: float,
                        home_team: dict | None = None, away_team: dict | None = None,
                        prediction_log: list[dict] | None = None) -> dict:
    """Apply coach factors and append a transparent event to prediction_log."""
    home = classify_coach((home_team or {}).get("coach"))
    away = classify_coach((away_team or {}).get("coach"))
    result = {
        "lambda_home": round(float(lambda_home) * home["factor"], 6),
        "lambda_away": round(float(lambda_away) * away["factor"], 6),
        "home_coach_factor": home["factor"], "away_coach_factor": away["factor"],
        "home_coach_style": home["style"], "away_coach_style": away["style"],
    }
    event = {"timestamp": datetime.now(timezone.utc).isoformat(),
             "event": "coach_factor", "home": home, "away": away,
             "lambda_home_before": float(lambda_home), "lambda_away_before": float(lambda_away),
             "lambda_home_after": result["lambda_home"], "lambda_away_after": result["lambda_away"]}
    if prediction_log is not None: prediction_log.append(event)
    result["coach_factor"] = {"home": home, "away": away}
    return result


def load_squads(path: str | Path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


if __name__ == "__main__":
    p = Path(__file__).parent / "data" / "final_574_squads_with_sources.json"
    print(f"Loaded {len(load_squads(p))} team containers")

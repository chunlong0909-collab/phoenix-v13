"""Player-strength helper for prediction.

Wikipedia rows use appearances_25_26=0 as an explicit 'not supplied' marker.
A zero value therefore never penalizes a player; those rows use position weight only.
"""
from __future__ import annotations
import json
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

def position_weight(position: str | None) -> float:
    return POSITION_WEIGHT.get(str(position or "").upper(), 1.0)

def player_strength(player: dict) -> float:
    """Return a bounded strength score without treating missing appearances as zero form."""
    pos = position_weight(player.get("position"))
    goals = player.get("goals")
    apps = player.get("appearances_current", player.get("appearances_25_26"))
    try: goals = max(float(goals), 0.0) if goals is not None else 0.0
    except (TypeError, ValueError): goals = 0.0
    try: apps = float(apps) if apps is not None else None
    except (TypeError, ValueError): apps = None
    # Wikipedia's zero is an unavailable-stat marker, not a measured zero.
    if apps is None or apps == 0:
        raw = 50.0 * pos
    else:
        raw = (35.0 + min(apps, 38.0) / 38.0 * 35.0 + min(goals, 20.0) / 20.0 * 30.0) * pos
    return round(max(0.0, min(100.0, raw)), 2)

def team_strength(team: dict) -> dict:
    players = team.get("front", []) + team.get("back", [])
    scores = [player_strength(p) for p in players]
    return {"team": team.get("team"), "players": len(players), "mean_strength": round(sum(scores)/len(scores), 2) if scores else None, "source_aware": True}

def load_squads(path: str | Path):
    return json.loads(Path(path).read_text(encoding="utf-8"))

if __name__ == "__main__":
    p = Path(__file__).parent / "data" / "final_574_squads_with_sources.json"
    print(f"Loaded {len(load_squads(p))} team containers")

"""Small, auditable post-match calibration layer.
Only completed records with numeric real scores affect future predictions.
"""
from __future__ import annotations
import json
from pathlib import Path

DEFAULT_PATH=Path(__file__).with_name("learning_log.json")

def load_log(path=DEFAULT_PATH):
    try:
        obj=json.loads(Path(path).read_text(encoding="utf-8"))
        return obj if isinstance(obj,list) else obj.get("matches",[])
    except Exception: return []

def _num(x):
    try: return float(x)
    except (TypeError,ValueError): return None

def learning_adjustment(team: str, path=DEFAULT_PATH, max_adjustment=.10):
    errs=[]
    for row in load_log(path):
        if str(row.get("team","")).strip().lower()!=str(team).strip().lower(): continue
        predicted=_num(row.get("predicted_goals", row.get("predicted"))); real=_num(row.get("real_goals", row.get("real")))
        if predicted is not None and real is not None: errs.append(real-predicted)
    if not errs: return 0.0
    # real - predicted > 0 means the model underestimated; move the next
    # estimate upward, never beyond the conservative cap.
    return max(-max_adjustment,min(max_adjustment,sum(errs[-5:])/len(errs[-5:])))

def learning_summary(path=DEFAULT_PATH):
    rows=load_log(path); completed=[]; abs_errors=[]
    for r in rows:
        p=_num(r.get("predicted_goals", r.get("predicted"))); real=_num(r.get("real_goals", r.get("real")))
        if p is not None and real is not None: completed.append(r); abs_errors.append(abs(real-p))
    return {"total":len(rows),"completed":len(completed),"recent5_error":sum(abs_errors[-5:])/len(abs_errors[-5:]) if abs_errors else None}

def record_result(match: str, team: str, predicted_goals: float, real_goals: float|None=None, path=DEFAULT_PATH):
    rows=load_log(path); rows.append({"match":match,"team":team,"predicted":float(predicted_goals),"real":real_goals,"predicted_goals":float(predicted_goals),"real_goals":real_goals,"error":None if real_goals is None else float(real_goals)-float(predicted_goals)})
    Path(path).parent.mkdir(parents=True,exist_ok=True); Path(path).write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding="utf-8")

def record_match_result(match: str, home_team: str, away_team: str,
                        predicted_home_goals: float, predicted_away_goals: float,
                        real_home_goals: float, real_away_goals: float,
                        predicted_home_corners: float|None = None,
                        predicted_away_corners: float|None = None,
                        real_home_corners: float|None = None,
                        real_away_corners: float|None = None,
                        path=DEFAULT_PATH):
    """Append one completed match as two team calibration rows.

    Goal fields remain compatible with learning_adjustment(); corner fields are
    recorded for separate future corner calibration and never alter goal
    predictions automatically.
    """
    rows = load_log(path)
    stamp = {"match": match, "completed": True,
             "real_score": f"{int(real_home_goals)}-{int(real_away_goals)}",
             "match_corners": None if real_home_corners is None or real_away_corners is None else f"{int(real_home_corners)}-{int(real_away_corners)}",
             "predicted_corners_total": None if predicted_home_corners is None or predicted_away_corners is None else float(predicted_home_corners) + float(predicted_away_corners),
             "real_corners_total": None if real_home_corners is None or real_away_corners is None else float(real_home_corners) + float(real_away_corners)}
    for team, predicted, real, side, pc, rc in [
        (home_team, predicted_home_goals, real_home_goals, "home", predicted_home_corners, real_home_corners),
        (away_team, predicted_away_goals, real_away_goals, "away", predicted_away_corners, real_away_corners),
    ]:
        row = {**stamp, "team": team, "side": side,
               "predicted": float(predicted), "real": float(real),
               "predicted_goals": float(predicted), "real_goals": float(real),
               "error": float(real) - float(predicted),
               "predicted_corners": None if pc is None else float(pc),
               "real_corners": None if rc is None else float(rc),
               "corner_error": None if pc is None or rc is None else float(rc) - float(pc)}
        rows.append(row)
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")

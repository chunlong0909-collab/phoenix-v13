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
    return max(-max_adjustment,min(max_adjustment,-sum(errs[-5:])/len(errs[-5:])))

def learning_summary(path=DEFAULT_PATH):
    rows=load_log(path); completed=[]; abs_errors=[]
    for r in rows:
        p=_num(r.get("predicted_goals", r.get("predicted"))); real=_num(r.get("real_goals", r.get("real")))
        if p is not None and real is not None: completed.append(r); abs_errors.append(abs(real-p))
    return {"total":len(rows),"completed":len(completed),"recent5_error":sum(abs_errors[-5:])/len(abs_errors[-5:]) if abs_errors else None}

def record_result(match: str, team: str, predicted_goals: float, real_goals: float|None=None, path=DEFAULT_PATH):
    rows=load_log(path); rows.append({"match":match,"team":team,"predicted":float(predicted_goals),"real":real_goals,"predicted_goals":float(predicted_goals),"real_goals":real_goals,"error":None if real_goals is None else float(real_goals)-float(predicted_goals)})
    Path(path).parent.mkdir(parents=True,exist_ok=True); Path(path).write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding="utf-8")

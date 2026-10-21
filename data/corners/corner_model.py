"""Independent home/away team-goal probabilities.

This module deliberately does not require odds. EV belongs to the display layer.
"""
from __future__ import annotations
import math

def poisson_pmf(k: int, lam: float) -> float:
    lam=max(0.0,float(lam)); return math.exp(-lam)*lam**k/math.factorial(k)

def at_least_one(lam: float) -> float: return 1.0-poisson_pmf(0,lam)
def at_least_two(lam: float) -> float: return 1.0-poisson_pmf(0,lam)-poisson_pmf(1,lam)

def team_goal_model(home_exp: float, away_exp: float) -> dict:
    h,a=float(home_exp),float(away_exp)
    return {"home_exp":h,"away_exp":a,"total_exp":h+a,
            "home_over_0_5":at_least_one(h),"home_over_1_5":at_least_two(h),
            "away_over_0_5":at_least_one(a),"away_over_1_5":at_least_two(a)}

def total_goal_band(total_exp: float, swing: float=0.8) -> dict:
    total=float(total_exp); return {"total_exp":total,"swing":float(swing),"low":max(0,total-swing),"high":total+swing}

def goal_line_note(probability: float, line: float, margin: float=0.08) -> str:
    p=float(probability)
    if abs(p-0.5)<=margin:
        return f"{p:.2%} ±{margin:.0%}（搖擺區）：接近五五波，建議避開{line:g}呢條剛好線"
    return f"{p:.2%}（模型機率；實際會受臨場因素影響）"

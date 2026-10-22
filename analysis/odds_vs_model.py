"""Generic odds-vs-model calculator. Positive EV is a comparison signal, not a guarantee."""
from __future__ import annotations
import math
from typing import Any

def poisson_pmf(k, lam): return math.exp(-lam)*lam**k/math.factorial(k)
def _dist(hx, ax, n=14): return {(h,a):poisson_pmf(h,hx)*poisson_pmf(a,ax) for h in range(n+1) for a in range(n+1)}
def _p(x): return max(0.0,min(1.0,float(x)))

def probability_for_market(row: dict, home_exp: float, away_exp: float, monte_carlo: dict|None=None, corner_total: float|None=None) -> float:
    market=row.get("market"); sel=row.get("selection"); line=row.get("line")
    if market in {"1X2","Half1X2"}:
        if monte_carlo and market=="1X2":
            key={"home":"主勝","draw":"和局","away":"客勝"}.get(sel)
            if key in monte_carlo: return _p(monte_carlo[key])
        scale=.45 if market=="Half1X2" else 1.0
        d=_dist(home_exp*scale,away_exp*scale)
        return _p(sum(v for (h,a),v in d.items() if (sel=="home" and h>a) or (sel=="draw" and h==a) or (sel=="away" and h<a)))
    if market=="NextGoal":
        total=home_exp+away_exp
        if sel=="none": return _p(math.exp(-total))
        return _p((home_exp if sel=="home" else away_exp)/total*(1-math.exp(-total))) if total else 0.0
    if market=="HDP":
        d=_dist(home_exp,away_exp)
        return _p(sum(v for (h,a),v in d.items() if (sel=="home" and h+line>a) or (sel=="draw" and abs(h+line-a)<1e-9) or (sel=="away" and h+line<a)))
    if market=="OU":
        total=home_exp+away_exp
        return _p(sum(v for (h,a),v in _dist(home_exp,away_exp).items() if (h+a>line if sel=="over" else h+a<line)))
    if market=="CornerOU":
        total=float(corner_total if corner_total is not None else 9.0)
        return _p(sum(poisson_pmf(k,total) for k in range(0,31) if (k>line if sel=="over" else k<line)))
    if market=="TeamOU":
        lam=home_exp if row.get("team")=="home" else away_exp
        return _p(sum(poisson_pmf(k,lam) for k in range(0,15) if (k>line if sel=="over" else k<line)))
    return 0.0

def compare_odds(rows: list[dict], home_exp: float, away_exp: float, monte_carlo: dict|None=None, corner_total: float|None=None) -> list[dict[str,Any]]:
    out=[]
    for row in rows:
        p=probability_for_market(row,home_exp,away_exp,monte_carlo,corner_total); odds=float(row["odds"])
        ev=p*odds-1; light="green" if ev>.10 else "yellow" if ev>=0 else "grey"
        out.append({**row,"model_prob":p,"model_probability":p,"book_prob":1/odds,"bookmaker_probability":1/odds,"ev":ev,"light":light})
    return sorted(out,key=lambda x:x["ev"],reverse=True)

def ai_summary(results, home, away, home_exp, away_exp):
    total=home_exp+away_exp
    direction="大球" if total>=2.5 else "細球"
    best=(results[0].get("market")+" "+str(results[0].get("selection"))+f" EV {results[0]['ev']:+.1%}") if results else "未有可比較盤口"
    return f"AI分析：{home}預期{home_exp:.2f}球、{away}預期{away_exp:.2f}球，總數{total:.2f}球，模型傾向{direction}；最高EV盤口：{best}。正EV不等於高命中率。"

"""V2.0: interpret model data and market odds together.
It reports agreement/divergence; it does not treat odds as truth or guarantee a result.
"""
from __future__ import annotations
from typing import Any

def _odds(rows, market, selection, line=None):
    for r in rows or []:
        if r.get("market") != market or r.get("selection") != selection: continue
        if line is None or abs(float(r.get("line", 0) or 0)-float(line)) < 1e-9: return float(r["odds"])
    return None

def read_match(home_exp: float, away_exp: float, xg_last8: dict|None=None, shots: dict|None=None,
               odds_rows: list[dict]|None=None, draw_probability: float|None=None,
               low_score_tight: float|None=None, corner_insight: str|None=None,
               model_home_probability: float|None=None, model_away_probability: float|None=None) -> dict:
    """Return a human-readable, uncertainty-aware reading of one match."""
    rows=odds_rows or []; h,a=float(home_exp),float(away_exp)
    total=h+a; hp,ap = (1.0/(1.0+max(a,0.01)/max(h,0.01)), 1.0/(1.0+max(h,0.01)/max(a,0.01)))
    # Better model direction proxy is supplied by the caller when available.
    home_odds=_odds(rows,"1X2","home"); away_odds=_odds(rows,"1X2","away")
    points=[]
    if home_odds and away_odds:
        market_home=1/home_odds; market_away=1/away_odds
        data_home=float(model_home_probability) if model_home_probability is not None else (h/(h+a) if total else .5)
        data_away=float(model_away_probability) if model_away_probability is not None else (a/(h+a) if total else .5)
        gap_home=data_home-market_home; gap_away=data_away-market_away
        if data_home < data_away and market_home < market_away:
            conclusion="模型與莊家方向一致睇客隊稍強；但強弱差距未足以保證賽果，仍要防和局。"
        elif data_home > data_away and market_home > market_away:
            conclusion="模型與莊家方向一致睇主隊稍強；但強弱差距未足以保證賽果，仍要防和局。"
        elif abs(gap_home)<.07 and abs(gap_away)<.07:
            conclusion="莊家與模型方向大致一致；唔代表必然命中，避免將一致當成保證。"
        elif gap_home>.07:
            conclusion="數據相對支持主隊，但賠率未完全反映；屬數據與賠率背離，先核對陣容、主客場及樣本，唔好只靠EV。"
        elif gap_away>.07:
            conclusion="數據相對支持客隊，但賠率未完全反映；屬數據與賠率背離，先核對臨場資訊，唔好只靠EV。"
        else:
            conclusion="賠率方向較偏向其中一隊，但數據支持不足；避免盲追熱門，等待更多可靠資料。"
        points.append(f"主客數據比例 {data_home:.1%}/{data_away:.1%}；市場隱含比例約 {market_home:.1%}/{market_away:.1%}")
    else:
        conclusion="未有完整勝和負賠率，只能按真實數據方向分析，不能判斷賠率是否背離。"
    ou=[]
    ou25=next((r for r in rows if r.get("market")=="OU" and abs(float(r.get("line",0))-2.5)<1e-9 and r.get("selection")=="over"),None)
    if ou25:
        model_over=float(ou25.get("model_probability", ou25.get("model_prob", .5))); odds=float(ou25["odds"]); book=1/odds
        if abs(model_over-book)<=.04: ou.append(f"大2.5模型{model_over:.1%}、莊家隱含{book:.1%}接近，屬搖擺線，避開較穩陣。")
        elif model_over<book: ou.append(f"模型睇大約{model_over:.1%}但莊家隱含{book:.1%}；買細亦有反向風險，建議避開2.5剛好線。")
        else: ou.append(f"模型大2.5約{model_over:.1%}高過莊家隱含{book:.1%}；仍須核對入球樣本及陣容。")
    tight=float(low_score_tight or 0)
    if tight>.45: conclusion += " ⚠️低比分膠著風險高，和局陷阱指數高，單選主客風險大。"
    if corner_insight: conclusion += " " + corner_insight
    return {"conclusion":conclusion,"ou_note":" ".join(ou),"evidence":points,
            "home_odds":home_odds,"away_odds":away_odds,"total_exp":total,
            "xg_last8":xg_last8 or {},"shots":shots or {},"low_score_tight":tight}

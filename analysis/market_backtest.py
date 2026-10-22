"""入球大小及角球大小的可審計 walk-forward 回測。

每場目標賽事只使用日期之前的歷史資料；沒有真實角球欄位時不補假數據。
"""
from __future__ import annotations

import math
from collections import defaultdict
import pandas as pd


def _poisson(k, lam):
    return math.exp(-lam) * lam ** k / math.factorial(k)


def _date_col(data):
    if "DateParsed" in data.columns:
        return pd.to_datetime(data["DateParsed"], errors="coerce", utc=True)
    return pd.to_datetime(data.get("Date", ""), errors="coerce", utc=True, dayfirst=True)


def _team_averages(history, team, n=8):
    rows = history[(history["Home"] == team) | (history["Away"] == team)].tail(n)
    if len(rows) == 0:
        return None
    gf, ga = [], []
    for _, row in rows.iterrows():
        if row["Home"] == team:
            gf.append(float(row["HG"])); ga.append(float(row["AG"]))
        else:
            gf.append(float(row["AG"])); ga.append(float(row["HG"]))
    return sum(gf) / len(gf), sum(ga) / len(ga), len(rows)


def _standings(history):
    table = defaultdict(lambda: {"played": 0, "points": 0, "gd": 0})
    for _, row in history.iterrows():
        h, a = row["Home"], row["Away"]
        hg, ag = int(row["HG"]), int(row["AG"])
        table[h]["played"] += 1; table[a]["played"] += 1
        table[h]["gd"] += hg - ag; table[a]["gd"] += ag - hg
        if hg > ag: table[h]["points"] += 3
        elif ag > hg: table[a]["points"] += 3
        else: table[h]["points"] += 1; table[a]["points"] += 1
    ordered = sorted(table.items(), key=lambda x: (-x[1]["points"], -x[1]["gd"], x[0]))
    return {team: i + 1 for i, (team, _) in enumerate(ordered)}


def _corner_average(history, team, n=8):
    if not {"HC", "AC"}.issubset(history.columns):
        return None
    rows = history[(history["Home"] == team) | (history["Away"] == team)].copy()
    rows = rows.dropna(subset=["HC", "AC"]).tail(n)
    if rows.empty:
        return None
    values = [float(r["HC"] if r["Home"] == team else r["AC"]) for _, r in rows.iterrows()]
    return sum(values) / len(values)


def walk_forward_market_backtest(matches, min_team_games=4, goal_odds=1.40, corner_odds=1.80):
    """回傳細3.5及大9.5角的逐場結果和摘要。"""
    data = matches.copy()
    for col in ["Home", "Away", "HG", "AG"]:
        if col not in data.columns:
            return pd.DataFrame(), {"入球樣本數": 0, "角球樣本數": 0}
    data["DateParsed"] = _date_col(data)
    data["HG"] = pd.to_numeric(data["HG"], errors="coerce")
    data["AG"] = pd.to_numeric(data["AG"], errors="coerce")
    data = data.dropna(subset=["DateParsed", "HG", "AG"]).sort_values("DateParsed").reset_index(drop=True)
    rows = []
    for i, target in data.iterrows():
        history = data.iloc[:i]
        hm = _team_averages(history, target["Home"])
        am = _team_averages(history, target["Away"])
        if hm is None or am is None or hm[2] < min_team_games or am[2] < min_team_games:
            continue
        hx = max(.15, (hm[0] + am[1]) / 2 * 1.08)
        ax = max(.15, (am[0] + hm[1]) / 2 * .94)
        total_exp = hx + ax
        goal_prediction = "細3.5" if total_exp < 2.8 else "不下注"
        actual_total = int(target["HG"] + target["AG"])
        goal_hit = goal_prediction == "細3.5" and actual_total <= 3
        row = {"日期": target["DateParsed"].date().isoformat(), "主隊": target["Home"], "客隊": target["Away"],
               "預期入球": total_exp, "入球標籤": goal_prediction, "實際入球": actual_total,
               "細3.5命中": goal_hit if goal_prediction == "細3.5" else None,
               "細3.5淨利": (goal_odds - 1) if goal_hit else (-1 if goal_prediction == "細3.5" else 0)}
        ranks = _standings(history)
        hr, ar = ranks.get(target["Home"]), ranks.get(target["Away"])
        hc, ac = target.get("HC"), target.get("AC")
        hca, aca = _corner_average(history, target["Home"]), _corner_average(history, target["Away"])
        corner_prediction = bool(hr and ar and 13 <= hr <= 18 and 13 <= ar <= 18 and hca is not None and aca is not None)
        corner_total = None if pd.isna(hc) or pd.isna(ac) else float(hc) + float(ac)
        corner_hit = corner_prediction and corner_total is not None and corner_total > 9.5
        row.update({"主隊排名": hr, "客隊排名": ar, "角球預測": "大9.5角" if corner_prediction else "不下注",
                    "實際角球": corner_total, "大9.5角命中": corner_hit if corner_prediction and corner_total is not None else None,
                    "大9.5角淨利": (corner_odds - 1) if corner_hit else (-1 if corner_prediction and corner_total is not None else 0)})
        rows.append(row)
    detail = pd.DataFrame(rows)
    if detail.empty:
        return detail, {"入球樣本數": 0, "角球樣本數": 0}
    goal_rows = detail[detail["入球標籤"] == "細3.5"]
    corner_rows = detail[detail["角球預測"] == "大9.5角"].dropna(subset=["實際角球"])
    summary = {
        "入球樣本數": len(goal_rows),
        "細3.5命中率": float(goal_rows["細3.5命中"].mean()) if len(goal_rows) else None,
        "細3.5淨利潤": float(goal_rows["細3.5淨利"].sum()) if len(goal_rows) else 0.0,
        "角球樣本數": len(corner_rows),
        "大9.5角命中率": float(corner_rows["大9.5角命中"].mean()) if len(corner_rows) else None,
        "大9.5角淨利潤": float(corner_rows["大9.5角淨利"].sum()) if len(corner_rows) else 0.0,
    }
    return detail, summary

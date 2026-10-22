"""完整入球／角球大小盤 walk-forward 回測引擎。

每一場目標賽事只使用該場日期之前的賽果；沒有真實 HC/AC 或無法由
歷史賽果建立排名時，角球策略不會產生假命中率，而會回傳資料不足。
"""
from __future__ import annotations

from collections import defaultdict
import math
import pandas as pd

GOAL_LINES = {
    "細2.5": {"line": 2.5, "side": "under", "threshold": 2.6, "odds": 1.90},
    "細3.5": {"line": 3.5, "side": "under", "threshold": 3.3, "odds": 1.40},
    "細4.5": {"line": 4.5, "side": "under", "threshold": 4.2, "odds": 1.15},
    "大2.5": {"line": 2.5, "side": "over", "threshold": 2.6, "odds": 1.90},
    "大3.5": {"line": 3.5, "side": "over", "threshold": 3.3, "odds": 2.80},
    "大4.5": {"line": 4.5, "side": "over", "threshold": 4.2, "odds": 4.50},
}

CORNER_LINES = {
    **{f"大{x:.1f}": {"line": x, "side": "over", "odds": o}
       for x, o in zip((9.5, 10.5, 11.5, 12.5, 13.5, 14.5), (1.8, 2.0, 2.25, 2.6, 3.0, 3.5))},
    **{f"細{x:.1f}": {"line": x, "side": "under", "odds": o}
       for x, o in zip((9.5, 10.5, 11.5, 12.5, 13.5, 14.5), (1.8, 2.0, 2.25, 2.6, 3.0, 3.5))},
}


def _date_col(data):
    if "DateParsed" in data.columns:
        return pd.to_datetime(data["DateParsed"], errors="coerce", utc=True)
    return pd.to_datetime(data.get("Date", ""), errors="coerce", utc=True, dayfirst=True)


def _team_averages(history, team, n=8):
    rows = history[(history["Home"] == team) | (history["Away"] == team)].tail(n)
    if rows.empty:
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
        if hg > ag:
            table[h]["points"] += 3
        elif ag > hg:
            table[a]["points"] += 3
        else:
            table[h]["points"] += 1; table[a]["points"] += 1
    ordered = sorted(table.items(), key=lambda x: (-x[1]["points"], -x[1]["gd"], x[0]))
    return {team: i + 1 for i, (team, _) in enumerate(ordered)}


def _corner_average(history, team, n=8):
    if not {"HC", "AC"}.issubset(history.columns):
        return None
    rows = history[(history["Home"] == team) | (history["Away"] == team)].dropna(subset=["HC", "AC"]).tail(n)
    if len(rows) < 4:
        return None
    values = [float(r["HC"] if r["Home"] == team else r["AC"]) for _, r in rows.iterrows()]
    return sum(values) / len(values)


def _hit(actual, line, side):
    return actual < line if side == "under" else actual > line


def _profit(hit, odds):
    return float(odds - 1.0) if hit else -1.0


def _empty_summary():
    table = []
    for label, cfg in {**GOAL_LINES, **CORNER_LINES}.items():
        table.append({"盤口": label, "方向": "細" if cfg["side"] == "under" else "大",
                      "賠率": cfg["odds"], "命中率": None, "樣本數": 0,
                      "淨利潤": 0.0, "狀態": "資料不足"})
    return {"盤口回測": pd.DataFrame(table), "入球盤口回測": pd.DataFrame(table[:6]),
            "角球盤口回測": pd.DataFrame(table[6:]), "入球樣本數": 0, "角球樣本數": 0,
            "細3.5命中率": None, "細3.5淨利潤": 0.0,
            "大9.5角命中率": None, "大9.5角淨利潤": 0.0}


def walk_forward_market_backtest(matches, min_team_games=4):
    """回傳逐場明細及 6+12 條盤口的命中率、樣本數、淨利潤。

    入球方向依照指定預期入球閾值決定；角球只在雙方排名 12--18、兩隊
    都有至少 4 場更早的真實 HC/AC 時，才把護級對賽列為可下注樣本。
    """
    required = {"Home", "Away", "HG", "AG"}
    if matches is None or matches.empty or not required.issubset(matches.columns):
        return pd.DataFrame(), _empty_summary()
    data = matches.copy()
    data["DateParsed"] = _date_col(data)
    for col in ["HG", "AG", "HC", "AC"]:
        if col in data.columns:
            data[col] = pd.to_numeric(data[col], errors="coerce")
    data = data.dropna(subset=["DateParsed", "HG", "AG"]).sort_values("DateParsed").reset_index(drop=True)
    if data.empty:
        return pd.DataFrame(), _empty_summary()

    detail_rows = []
    line_records = {label: [] for label in {**GOAL_LINES, **CORNER_LINES}}
    for i, target in data.iterrows():
        history = data.iloc[:i]
        hm, am = _team_averages(history, target["Home"]), _team_averages(history, target["Away"])
        if hm is None or am is None or hm[2] < min_team_games or am[2] < min_team_games:
            continue
        hx = max(.15, (hm[0] + am[1]) / 2 * 1.08)
        ax = max(.15, (am[0] + hm[1]) / 2 * .94)
        total_exp = hx + ax
        actual_goals = int(target["HG"] + target["AG"])
        row = {"日期": target["DateParsed"].date().isoformat(), "主隊": target["Home"], "客隊": target["Away"],
               "預期入球": total_exp, "實際入球": actual_goals}
        for label, cfg in GOAL_LINES.items():
            side = "under" if total_exp < cfg["threshold"] else "over"
            # 每條線都依其指定閾值選擇細／大；threshold 以下是細，以上是大。
            hit = _hit(actual_goals, cfg["line"], side)
            rec = {"命中": hit, "淨利潤": _profit(hit, cfg["odds"])}
            line_records[label].append(rec)
            row[f"{label}預測"] = "細" if side == "under" else "大"
            row[f"{label}命中"] = hit
        ranks = _standings(history)
        hr, ar = ranks.get(target["Home"]), ranks.get(target["Away"])
        hca, aca = _corner_average(history, target["Home"]), _corner_average(history, target["Away"])
        corner_context = bool(hr and ar and 12 <= hr <= 18 and 12 <= ar <= 18 and hca is not None and aca is not None)
        hc, ac = target.get("HC"), target.get("AC")
        actual_corners = None if hc is None or ac is None or pd.isna(hc) or pd.isna(ac) else float(hc) + float(ac)
        row.update({"主隊排名": hr, "客隊排名": ar, "角球護級樣本": "是" if corner_context else "否", "實際角球": actual_corners})
        for label, cfg in CORNER_LINES.items():
            if corner_context and actual_corners is not None:
                hit = _hit(actual_corners, cfg["line"], cfg["side"])
                line_records[label].append({"命中": hit, "淨利潤": _profit(hit, cfg["odds"])})
                row[f"{label}命中"] = hit
            else:
                row[f"{label}命中"] = None
        detail_rows.append(row)

    detail = pd.DataFrame(detail_rows)
    summary_rows = []
    for label, cfg in {**GOAL_LINES, **CORNER_LINES}.items():
        records = line_records[label]
        n = len(records)
        summary_rows.append({"盤口": label, "方向": "細" if cfg["side"] == "under" else "大",
                             "賠率": cfg["odds"], "命中率": sum(r["命中"] for r in records) / n if n else None,
                             "樣本數": n, "淨利潤": sum(r["淨利潤"] for r in records),
                             "狀態": "可回測" if n else "資料不足"})
    table = pd.DataFrame(summary_rows)
    goal_table = table[table["盤口"].isin(GOAL_LINES)].reset_index(drop=True)
    corner_table = table[table["盤口"].isin(CORNER_LINES)].reset_index(drop=True)
    g35 = goal_table[goal_table["盤口"] == "細3.5"].iloc[0]
    c95 = corner_table[corner_table["盤口"] == "大9.5"].iloc[0]
    summary = {"盤口回測": table, "入球盤口回測": goal_table, "角球盤口回測": corner_table,
               "入球樣本數": int(g35["樣本數"]), "細3.5命中率": g35["命中率"], "細3.5淨利潤": float(g35["淨利潤"]),
               "角球樣本數": int(c95["樣本數"]), "大9.5角命中率": c95["命中率"], "大9.5角淨利潤": float(c95["淨利潤"])}
    return detail, summary

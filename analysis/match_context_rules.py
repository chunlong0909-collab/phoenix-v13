"""通用聯賽比賽情境規則。

所有判斷只依賴傳入的賽果資料，不寫死任何聯賽。資料不足時不觸發
護級戰意加成，避免把缺失排名當成真實訊號。
"""
from __future__ import annotations
from collections import defaultdict
from datetime import datetime
import math


def _num(value, default=None):
    try:
        if value is None or value == "":
            return default
        x = float(value)
        return x if math.isfinite(x) else default
    except (TypeError, ValueError):
        return default


def _date_year(row):
    raw = row.get("DateParsed", row.get("Date", "")) if hasattr(row, "get") else ""
    try:
        return datetime.fromisoformat(str(raw).replace("Z", "+00:00")).year
    except Exception:
        try:
            return int(str(raw)[:4])
        except Exception:
            return None


def _team(row, side):
    return str(row.get(side, "")).strip() if hasattr(row, "get") else ""


def _points_table(matches):
    """由最近一個資料年份的已完成賽果建立簡易積分榜。"""
    if matches is None or getattr(matches, "empty", True):
        return {}, None
    rows = []
    for _, row in matches.iterrows():
        hg, ag = _num(row.get("HG")), _num(row.get("AG"))
        home, away = _team(row, "Home"), _team(row, "Away")
        if not home or not away or hg is None or ag is None:
            continue
        year = _date_year(row)
        if year is not None:
            rows.append((year, row))
    if not rows:
        return {}, None
    season_year = max(year for year, _ in rows)
    table = defaultdict(lambda: {"played": 0, "points": 0, "gd": 0, "wins": 0})
    for year, row in rows:
        if year != season_year:
            continue
        home, away = _team(row, "Home"), _team(row, "Away")
        hg, ag = int(_num(row.get("HG"), 0)), int(_num(row.get("AG"), 0))
        table[home]["played"] += 1; table[away]["played"] += 1
        table[home]["gd"] += hg - ag; table[away]["gd"] += ag - hg
        if hg > ag:
            table[home]["points"] += 3; table[home]["wins"] += 1
        elif ag > hg:
            table[away]["points"] += 3; table[away]["wins"] += 1
        else:
            table[home]["points"] += 1; table[away]["points"] += 1
    ordered = sorted(table.items(), key=lambda kv: (kv[1]["points"], kv[1]["gd"], kv[0]))
    # 以最高分為榜首；後六名按聯賽當前資料排序。
    return {team: {**stats, "rank": len(ordered) - i} for i, (team, stats) in enumerate(ordered)}, season_year


def _recent_wins(matches, team, season_year, n=5):
    rows = []
    for _, row in (matches.iterrows() if matches is not None else []):
        if season_year is not None and _date_year(row) != season_year:
            continue
        if team not in {_team(row, "Home"), _team(row, "Away")}:
            continue
        hg, ag = _num(row.get("HG")), _num(row.get("AG"))
        if hg is not None and ag is not None:
            rows.append(row)
    rows = rows[-n:]
    wins = 0
    for row in rows:
        home = _team(row, "Home") == team
        hg, ag = int(_num(row.get("HG"), 0)), int(_num(row.get("AG"), 0))
        if (home and hg > ag) or (not home and ag > hg):
            wins += 1
    return wins, len(rows)


def build_relegation_context(matches, home, away, bottom_n=6):
    table, season_year = _points_table(matches)
    h, a = table.get(home), table.get(away)
    if not h or not a:
        return {"triggered": False, "status": "資料不足", "reason": "未能由本季賽果建立兩隊排名"}
    team_count = len(table)
    hw, hn = _recent_wins(matches, home, season_year)
    aw, an = _recent_wins(matches, away, season_year)
    bottom_start = max(1, team_count - bottom_n + 1)
    triggered = (h["rank"] >= bottom_start and a["rank"] >= bottom_start and
                 hn >= 5 and an >= 5 and hw <= 1 and aw <= 1 and
                 abs(h["points"] - a["points"]) <= 5)
    return {
        "triggered": triggered, "status": "已核對" if triggered else "未觸發",
        "season_year": season_year, "team_count": team_count,
        "home_rank": h["rank"], "away_rank": a["rank"],
        "home_points": h["points"], "away_points": a["points"],
        "points_gap": abs(h["points"] - a["points"]),
        "home_recent_wins": hw, "away_recent_wins": aw,
        "home_recent_sample": hn, "away_recent_sample": an,
        "bottom_n": bottom_n,
        "reason": ("兩隊後六名、近5場各最多1勝、分差不超過5分；啟用護級戰意加成"
                   if triggered else "未同時符合後六名／近5場勝場／積分差條件"),
    }


def apply_relegation_intent(home_exp, away_exp, context, total_boost=0.6):
    if not (context or {}).get("triggered"):
        return float(home_exp), float(away_exp), 0.0
    half = float(total_boost) / 2.0
    return float(home_exp) + half, float(away_exp) + half, float(total_boost)


def tight_score_pool(tight_probability, threshold=0.60):
    if _num(tight_probability, 0.0) <= threshold:
        return None
    return {"1-1": 0.40, "1-0": 0.25, "0-1": 0.20, "2-1": 0.15}


def corner_context_rows(matches, home, away, key_fn=None):
    """回傳主隊場均、客隊場均及最近一次交手角球；缺失則為 None。"""
    if matches is None or getattr(matches, "empty", True):
        return {"home_average": None, "away_average": None, "last_h2h": None}
    key_fn = key_fn or (lambda x: str(x).strip().casefold())
    valid = matches.dropna(subset=[c for c in ("HC", "AC") if c in matches.columns]).copy()
    def avg_for(team):
        vals = []
        for _, r in valid.iterrows():
            if key_fn(_team(r, "Home")) == key_fn(team): vals.append(_num(r.get("HC")))
            elif key_fn(_team(r, "Away")) == key_fn(team): vals.append(_num(r.get("AC")))
        vals = [v for v in vals if v is not None]
        return round(sum(vals) / len(vals), 2) if vals else None
    h2h = valid[((valid["Home"].map(key_fn) == key_fn(home)) & (valid["Away"].map(key_fn) == key_fn(away))) |
               ((valid["Home"].map(key_fn) == key_fn(away)) & (valid["Away"].map(key_fn) == key_fn(home)))]
    last = None
    if not h2h.empty:
        r = h2h.sort_values("DateParsed" if "DateParsed" in h2h.columns else "Date").iloc[-1]
        hc, ac = _num(r.get("HC")), _num(r.get("AC"))
        if hc is not None and ac is not None:
            last = {"home_corners": hc if key_fn(_team(r, "Home")) == key_fn(home) else ac,
                    "away_corners": ac if key_fn(_team(r, "Home")) == key_fn(home) else hc,
                    "total": hc + ac}
    return {"home_average": avg_for(home), "away_average": avg_for(away), "last_h2h": last}


def live_risk_message(minute, home_goals, away_goals):
    minute, hg, ag = _num(minute), _num(home_goals), _num(away_goals)
    if minute is None or hg is None or ag is None or minute > 30 or hg + ag < 2:
        return None
    return "若30分鐘內入2球，原有細2.5模型失效，建議轉看細4.5和角球大"


def reliability_level(sample_size, has_rank_context=False, has_real_corners=False, stale=False):
    if stale or sample_size < 8:
        return {"level": "低", "color": "#b42318", "text": "低｜資料不足或過期，建議避開"}
    if sample_size >= 16 and has_rank_context and has_real_corners:
        return {"level": "高", "color": "#137333", "text": "高｜資料較完整，可較積極考慮（不代表保證）"}
    return {"level": "中", "color": "#b26a00", "text": "中｜建議小注，仍要核對即時資訊"}

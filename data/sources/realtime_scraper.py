"""Best-effort realtime context collector with fail-closed behaviour.

No provider is treated as a free API unless it returns a documented public response.
Sportradar requires a user API key. 7M Sports and AiScore are public web pages,
not stable anonymous APIs, so their match URLs can be supplied through environment
variables. If a source is unavailable, the result is marked unknown and is never
invented or used to adjust expected goals.
"""
from __future__ import annotations
import json, os, re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import requests

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "data" / "complete"
UA = "FootballAnalysisApp/1.0 (+public-data; respectful rate limit)"
INJURY_WORDS = ("knee", "calf", "hamstring")

def _empty(source: str, reason: str) -> dict[str, Any]:
    return {"source": source, "status": "unavailable", "reason": reason,
            "h2h_last4": [], "home_last10": [], "away_last10": [], "injuries": [],
            "injury_data_verified": False, "goal_adjustment": {"home": 0.0, "away": 0.0}}

def _get_json(url: str, headers: dict | None = None) -> Any:
    r = requests.get(url, headers={"User-Agent": UA, **(headers or {})}, timeout=8)
    r.raise_for_status(); return r.json()

def _normalise_rows(payload: Any, home: str, away: str) -> dict[str, list]:
    """Accept only explicit JSON arrays with common result/injury fields."""
    if isinstance(payload, dict):
        for key in ("data", "events", "matches", "results", "response"):
            if isinstance(payload.get(key), list): payload = payload[key]; break
    if not isinstance(payload, list): return {"h2h": [], "home": [], "away": [], "injuries": []}
    h2h, hm, aw, injuries = [], [], [], []
    for x in payload:
        if not isinstance(x, dict): continue
        text = json.dumps(x, ensure_ascii=False).lower()
        injury = any(w in text for w in INJURY_WORDS)
        if injury and any(k in x for k in ("player", "player_name", "athlete", "name")):
            injuries.append(x)
        h = str(x.get("home_team") or x.get("home") or x.get("team_home") or "")
        a = str(x.get("away_team") or x.get("away") or x.get("team_away") or "")
        row = {"date": x.get("date"), "home_team": h, "away_team": a,
               "home_goals": x.get("home_goals", x.get("home_score")),
               "away_goals": x.get("away_goals", x.get("away_score")), "raw": x}
        if h and a and ({h.lower(), a.lower()} == {home.lower(), away.lower()}): h2h.append(row)
        if home.lower() in {h.lower(), a.lower()}: hm.append(row)
        if away.lower() in {h.lower(), a.lower()}: aw.append(row)
    return {"h2h": h2h[-4:], "home": hm[-10:], "away": aw[-10:], "injuries": injuries[:3]}

def _provider_json(name: str, url: str | None, home: str, away: str) -> dict:
    if not url: return _empty(name, "未設定公開網址；來源不是穩定免費API")
    try:
        parsed = _normalise_rows(_get_json(url), home, away)
        if not any(parsed.values()): return _empty(name, "回應沒有可核對的賽果或傷停欄位")
        return {"source": name, "status": "ok", "url": url, "updated_at": datetime.now(timezone.utc).isoformat(),
                "h2h_last4": parsed["h2h"], "home_last10": parsed["home"], "away_last10": parsed["away"],
                "injuries": parsed["injuries"], "injury_data_verified": bool(parsed["injuries"]),
                "goal_adjustment": {"home": 0.0, "away": 0.0}}
    except Exception as e:
        return _empty(name, f"讀取失敗：{type(e).__name__}")

def _combine(home: str, away: str, results: list[dict]) -> dict:
    usable = [x for x in results if x.get("status") == "ok"]
    merged = {"home": home, "away": away, "updated_at": datetime.now(timezone.utc).isoformat(),
              "providers": results, "source": "；".join(x["source"] for x in usable) or "未取得",
              "status": "ok" if usable else "unavailable", "h2h_last4": [], "home_last10": [],
              "away_last10": [], "injuries": [], "injury_data_verified": False,
              "goal_adjustment": {"home": 0.0, "away": 0.0},
              "note": "只合併來源明確回傳的資料；沒有資料時不作傷停扣減。"}
    for x in usable:
        for dst, src, limit in (("h2h_last4", "h2h_last4", 4), ("home_last10", "home_last10", 10), ("away_last10", "away_last10", 10), ("injuries", "injuries", 3)):
            if not merged[dst] and x.get(src): merged[dst] = x[src][:limit]
        if x.get("injury_data_verified"): merged["injury_data_verified"] = True
    # Requested rule is applied only when two verified primary forwards are explicitly returned.
    home_forward_injuries = sum(1 for i in merged["injuries"] if str(i.get("team", "")).lower() == home.lower()
                                and str(i.get("position", i.get("pos", ""))).upper() in {"F", "FW", "ST"})
    away_forward_injuries = sum(1 for i in merged["injuries"] if str(i.get("team", "")).lower() == away.lower()
                                and str(i.get("position", i.get("pos", ""))).upper() in {"F", "FW", "ST"})
    if merged["injury_data_verified"] and home_forward_injuries >= 2:
        merged["goal_adjustment"] = {"home": -0.4, "away": -0.2}
        merged["injury_rule"] = "主隊已核實至少2名主力前鋒傷停：主隊xG -0.4、客隊xG -0.2"
    elif merged["injury_data_verified"] and away_forward_injuries >= 2:
        merged["goal_adjustment"] = {"home": -0.2, "away": -0.4}
        merged["injury_rule"] = "客隊已核實至少2名主力前鋒傷停：主隊xG -0.2、客隊xG -0.4"
    return merged

def fetch_realtime_context(home: str, away: str, league: str = "") -> dict:
    """Fetch configured public JSON feeds and save a per-match live cache.

    Env vars: REALTIME_SPORTRADAR_URL, REALTIME_7M_URL, REALTIME_AISCORE_URL.
    Sportradar additionally needs SPORTRADAR_API_KEY; without it it is skipped.
    """
    results = []
    sr = os.getenv("REALTIME_SPORTRADAR_URL")
    if sr and os.getenv("SPORTRADAR_API_KEY"):
        results.append(_provider_json("Sportradar", sr, home, away))
    else:
        results.append(_empty("Sportradar", "需要API key；沒有匿名免費接口"))
    results.append(_provider_json("7M Sports", os.getenv("REALTIME_7M_URL"), home, away))
    results.append(_provider_json("AiScore", os.getenv("REALTIME_AISCORE_URL"), home, away))
    merged = _combine(home, away, results); merged["league"] = league
    OUT.mkdir(parents=True, exist_ok=True)
    safe = re.sub(r"[^A-Za-z0-9_-]+", "_", f"{home}_{away}").strip("_").lower()
    text = json.dumps(merged, ensure_ascii=False, indent=2)
    (OUT / f"{safe}_live.json").write_text(text, encoding="utf-8")
    # Also keep the requested per-team live cache. It contains the same verified
    # context and is useful to the team page without inventing team-only data.
    for team in (home, away):
        team_safe = re.sub(r"[^A-Za-z0-9_-]+", "_", team).strip("_").lower()
        (OUT / f"{team_safe}_live.json").write_text(text, encoding="utf-8")
    return merged

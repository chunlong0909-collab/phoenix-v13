"""Professional odds page data layer.

Reads keys from environment variables or Streamlit secrets. It never stores or
prints keys. Odds API calls are cached by event/date and capped at five calls
per Hong Kong day; Football-Data match details are fetched only on explicit
post-match refresh.
"""
from __future__ import annotations

import json
import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo
from typing import Any

import requests

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / "data" / "professional_cache"
CACHE.mkdir(parents=True, exist_ok=True)
FD_URL = "https://api.football-data.org/v4"
ODDS_URL = "https://api.the-odds-api.com/v4/sports/soccer_spain_la_liga/odds"
UA = "FootballAnalysisApp/1.7 (+public-data)"
HK = ZoneInfo("Asia/Hong_Kong")


def _secret(name: str) -> str:
    value = os.getenv(name, "").strip()
    if value:
        return value
    try:
        import streamlit as st
        value = str(st.secrets.get(name, "")).strip()
        return value
    except Exception:
        return ""


def _cache_path(kind: str, key: str) -> Path:
    safe = re.sub(r"[^A-Za-z0-9_.-]+", "_", key)
    return CACHE / f"{kind}_{safe}.json"


def _read(path: Path) -> dict | None:
    try:
        return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None
    except Exception:
        return None


def _write(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def _get(url: str, headers: dict, params: dict | None = None) -> dict:
    r = requests.get(url, headers={"User-Agent": UA, **headers}, params=params, timeout=15)
    r.raise_for_status()
    payload = r.json()
    if not isinstance(payload, dict):
        raise ValueError("API回應格式不是JSON物件")
    return payload


def _today_hk() -> str:
    return datetime.now(HK).date().isoformat()


def _odds_usage() -> dict:
    p = CACHE / f"odds_usage_{_today_hk()}.json"
    value = _read(p) or {"date": _today_hk(), "calls": 0}
    value["calls"] = int(value.get("calls", 0))
    return value


def _claim_odds_call() -> None:
    usage = _odds_usage()
    if usage["calls"] >= 5:
        raise RuntimeError("今日Odds API已達5次上限，使用本地快取，避免浪費免費額度")
    usage["calls"] += 1
    _write(CACHE / f"odds_usage_{_today_hk()}.json", usage)


def odds_usage() -> dict:
    return _odds_usage()


def fetch_match_detail(match_id: int | str, force: bool = False) -> dict:
    """Fetch Football-Data.org match detail, intended for post-match refresh."""
    key = str(match_id)
    path = _cache_path("football_data_match", key)
    if not force:
        cached = _read(path)
        if cached:
            return cached
    token = _secret("FOOTBALL_DATA_TOKEN")
    if not token:
        return {"status": "unavailable", "source": "Football-Data.org", "reason": "未設定FOOTBALL_DATA_TOKEN"}
    payload = _get(f"{FD_URL}/matches/{key}", {"X-Auth-Token": token})
    result = normalise_match_detail(payload)
    result.update({"status": "ok", "source": "Football-Data.org", "fetched_at": datetime.now(timezone.utc).isoformat()})
    _write(path, result)
    return result


def normalise_match_detail(payload: dict) -> dict:
    score = payload.get("score") or {}
    full = score.get("fullTime") or {}
    home = payload.get("homeTeam") or {}
    away = payload.get("awayTeam") or {}
    # football-data.org may not provide corners or a complete XI for every match;
    # preserve explicit fields only and never invent missing values.
    return {
        "match_id": payload.get("id"),
        "utc_date": payload.get("utcDate"),
        "status": payload.get("status"),
        "home": {"id": home.get("id"), "name": home.get("name"), "crest": home.get("crest")},
        "away": {"id": away.get("id"), "name": away.get("name"), "crest": away.get("crest")},
        "score": {"home": full.get("home"), "away": full.get("away")},
        "half_time": score.get("halfTime") or {},
        "goals": payload.get("goals") or [],
        "lineups": payload.get("lineups") or [],
        "referees": payload.get("referees") or [],
        "corners": payload.get("corners") or payload.get("statistics", {}).get("corners"),
        "head_to_head": payload.get("headToHead") or payload.get("h2h"),
        "raw_explicit_fields": {k: payload[k] for k in ("goals", "lineups", "corners", "statistics", "headToHead") if k in payload},
    }


def _normalise_bookmaker(book: dict) -> dict:
    out = {"key": book.get("key"), "title": book.get("title"), "last_update": book.get("last_update"), "markets": []}
    for market in book.get("markets", []) or []:
        rows = []
        for outcome in market.get("outcomes", []) or []:
            rows.append({"name": outcome.get("name"), "price": outcome.get("price"), "point": outcome.get("point"), "description": outcome.get("description")})
        out["markets"].append({"key": market.get("key"), "last_update": market.get("last_update"), "outcomes": rows})
    return out


def fetch_la_liga_odds(force: bool = False) -> dict:
    """Fetch one pre-match Odds API snapshot, cached per Hong Kong day."""
    path = _cache_path("odds", "soccer_spain_la_liga")
    if not force:
        cached = _read(path)
        if cached:
            return cached
    key = _secret("THE_ODDS_API_KEY")
    if not key:
        return {"status": "unavailable", "source": "The Odds API", "reason": "未設定THE_ODDS_API_KEY", "events": []}
    _claim_odds_call()
    payload = _get(ODDS_URL, {}, {"apiKey": key, "regions": "eu", "markets": "h2h,spreads,totals", "bookmakers": "pinnacle,bet365,unibet"})
    events = payload if isinstance(payload, list) else payload.get("events", [])
    # Odds API normally returns a list for this endpoint.
    if not isinstance(events, list):
        events = []
    result = {"status": "ok", "source": "The Odds API", "fetched_at": datetime.now(timezone.utc).isoformat(), "events": []}
    for event in events:
        result["events"].append({"id": event.get("id"), "commence_time": event.get("commence_time"), "home_team": event.get("home_team"), "away_team": event.get("away_team"), "bookmakers": [_normalise_bookmaker(x) for x in event.get("bookmakers", []) or []]})
    _write(path, result)
    return result


def find_event(odds_payload: dict, home: str, away: str) -> dict | None:
    aliases = {
        "bilbao": "athleticclub", "athleticbilbao": "athleticclub", "athleticclub": "athleticclub",
        "levante": "levanteud", "levanteud": "levanteud",
        "barca": "barcelonafc", "fcbarcelona": "barcelonafc", "barcelona": "barcelonafc",
        "realmadrid": "realmadrid", "real": "realmadrid",
    }
    def norm(x):
        value = re.sub(r"[^a-z0-9]", "", str(x).lower())
        return aliases.get(value, value)
    h, a = norm(home), norm(away)
    for event in odds_payload.get("events", []):
        eh, ea = norm(event.get("home_team")), norm(event.get("away_team"))
        if (h in eh or eh in h) and (a in ea or ea in a):
            return event
    return None


def merge_professional_page(home: str, away: str, match_id: int | str | None = None, post_match: bool = False) -> dict:
    """Build the page payload. Odds is pre-match cached; match detail is post-match."""
    odds = fetch_la_liga_odds(force=False)
    match = fetch_match_detail(match_id, force=True) if (post_match and match_id) else ({"status": "deferred", "reason": "開波前不讀取完場賽果"})
    return {"home": home, "away": away, "odds_snapshot": find_event(odds, home, away), "odds_meta": {k: odds.get(k) for k in ("status", "source", "fetched_at", "reason")}, "match_detail": match, "usage": odds_usage(), "policy": "Odds API開波前快取一次；Football-Data.org只在完場更新。"}

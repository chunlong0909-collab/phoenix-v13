"""Phoenix Team Registry V2.

隊伍目錄、別名和賽果是不同資料層。此模組只負責目錄與名稱解析，
不會建立或修改任何比賽結果。
"""
from __future__ import annotations

import csv
import difflib
import hashlib
import json
import re
import unicodedata
from pathlib import Path
from typing import Dict, Iterable, List, Optional

ROOT = Path(__file__).resolve().parent
REGISTRY_PATH = ROOT / "data" / "team_registry_v2.json"
REGISTRY_VERSION = 3


def normalize_name(value: str) -> str:
    value = unicodedata.normalize("NFKD", str(value or "")).casefold()
    return re.sub(r"[^\w]+", "", value, flags=re.UNICODE)


def canonical_league(league: str) -> str:
    aliases = {
        "意甲": "意大利甲組聯賽",
        "Serie A (Italy)": "意大利甲組聯賽",
        "巴甲": "巴西甲組聯賽",
        "英格蘭超級聯賽": "英超",
        "西班牙甲組聯賽": "西甲",
        "德國甲組聯賽": "德甲",
        "日本職業聯賽": "日職J1",
        "日本乙組聯賽": "日乙J2",
        "南韓職業聯賽": "韓職K1",
        "南韓乙組聯賽": "韓乙K2",
        "沙特職業聯賽": "沙職",
        "泰國甲組聯賽": "泰甲",
        "卡塔爾超級聯賽": "卡塔爾",
        "阿聯酋職業聯賽": "阿聯酋",
        "法國甲組聯賽": "法甲",
        "法甲": "法甲",
        "葡萄牙超級聯賽": "葡超",
        "荷蘭甲組聯賽": "荷甲",
        "荷蘭乙組聯賽": "荷乙",
        "奧地利甲組聯賽": "奧甲",
        "芬蘭超級聯賽": "芬超",
        "巴西甲組聯賽": "巴甲",
        "巴西乙組聯賽": "巴乙",
        "墨西哥超級聯賽": "墨超",
        "墨西哥甲組聯賽": "墨甲",
        "阿根廷甲組聯賽": "阿甲",
        "澳洲職業聯賽": "澳職",
        "澳洲冠軍聯賽盃": "澳洲冠軍聯賽盃",
    }
    return aliases.get(str(league).strip(), str(league).strip())


def _stable_id(league_key: str, name: str, source_id: str = "") -> str:
    raw = source_id.strip() or normalize_name(name)
    digest = hashlib.sha1(f"{league_key}:{raw}".encode("utf-8")).hexdigest()[:12]
    return f"{league_key}:{digest}"


def _add(rows: Dict[str, dict], league_key: str, league_name: str, name: str,
        source: str, source_url: str = "", source_id: str = "", aliases: Iterable[str] = (),
        season: str = "unknown", directory_only: bool = True) -> None:
    name = str(name or "").strip()
    if not name:
        return
    team_id = _stable_id(league_key, name, str(source_id or ""))
    row = rows.setdefault(team_id, {
        "team_id": team_id,
        "league_key": league_key,
        "league_name": league_name,
        "season": season or "unknown",
        "official_name": name,
        "aliases": [],
        "source": source or "local_directory",
        "source_url": source_url or "",
        "directory_only": directory_only,
    })
    if len(name) > len(row["official_name"]):
        row["official_name"] = name
    for alias in [name, *aliases]:
        alias = str(alias or "").strip()
        if alias and alias.casefold() not in {x.casefold() for x in row["aliases"]}:
            row["aliases"].append(alias)
    if source_url and not row.get("source_url"):
        row["source_url"] = source_url
    if season and row.get("season") in {"unknown", ""}:
        row["season"] = season


def _split_aliases(value: str) -> List[str]:
    return [x.strip() for x in re.split(r"[|,;]", str(value or "")) if x.strip()]


def _source_fingerprint() -> str:
    """Detect changed local directories/history so Streamlit never keeps an old registry."""
    paths = [ROOT / "leagues.json"]
    paths.extend(sorted((ROOT / "data" / "leagues").glob("*/teams.csv")))
    paths.extend([ROOT / "data" / "serie_a_teams.csv", ROOT / "data" / "serie-a_teams.json"])
    paths.extend(sorted((ROOT / "data" / "match_history").glob("*.csv")))
    digest = hashlib.sha256()
    for path in paths:
        try:
            stat = path.stat()
            digest.update(str(path.relative_to(ROOT)).encode("utf-8"))
            digest.update(f"{stat.st_mtime_ns}:{stat.st_size}".encode("ascii"))
        except OSError:
            continue
    return digest.hexdigest()[:16]


def build_registry() -> dict:
    """Build a traceable registry from existing local directory sources."""
    rows: Dict[str, dict] = {}
    league_meta = {}
    config_path = ROOT / "leagues.json"
    if config_path.exists():
        try:
            config = json.loads(config_path.read_text(encoding="utf-8"))
            for item in config.get("leagues", []):
                league_meta[str(item.get("id", ""))] = item
        except (OSError, ValueError, TypeError):
            pass

    for csv_path in sorted((ROOT / "data" / "leagues").glob("*/teams.csv")):
        slug = csv_path.parent.name
        meta = league_meta.get(slug, {})
        league_name = str(meta.get("name_zh") or slug)
        try:
            with csv_path.open(encoding="utf-8-sig", newline="") as fh:
                for item in csv.DictReader(fh):
                    name = item.get("official_name") or item.get("team_name") or item.get("team")
                    if not name:
                        continue
                    source_id = item.get("team_id") or item.get("espn_team_id") or ""
                    source = item.get("source") or item.get("dataSource") or "local_directory"
                    _add(rows, slug, league_name, name, source, item.get("source_url", ""), source_id,
                         _split_aliases(item.get("aliases", "")), item.get("season", "unknown"),
                         str(item.get("status", "")).casefold() != "match_history_only")
        except (OSError, csv.Error):
            continue

    # The repository contains an Italian Serie A cache under an ambiguous legacy
    # path. Use the explicit file instead of treating the Brazil cache as Italy.
    italy_csv = ROOT / "data" / "serie_a_teams.csv"
    if italy_csv.exists():
        try:
            with italy_csv.open(encoding="utf-8-sig", newline="") as fh:
                for item in csv.DictReader(fh):
                    _add(rows, "serie-a-italy", "意大利甲組聯賽", item.get("team_name", ""),
                         item.get("source", "local_directory"), item.get("source_url", ""),
                         item.get("team_id", ""), _split_aliases(item.get("aliases", "")),
                         item.get("season", "2026/27"))
                    team_id = _stable_id("serie-a-italy", item.get("team_name", ""), item.get("team_id", ""))
                    if team_id in rows:
                        rows[team_id]["season"] = item.get("season", "2026/27")
        except (OSError, csv.Error):
            pass

    # Configured directory-only teams are valid selectable teams, but never FT rows.
    for slug, meta in league_meta.items():
        league_name = str(meta.get("name_zh") or slug)
        for name in meta.get("team_directory") or []:
            _add(rows, slug, league_name, name, "leagues.json team_directory")

    # Make the Italian league explicit even if the legacy leagues.json label is wrong.
    for item in json.loads((ROOT / "data" / "serie-a_teams.json").read_text(encoding="utf-8")) if (ROOT / "data" / "serie-a_teams.json").exists() else []:
        _add(rows, "serie-a-italy", "意大利甲組聯賽", item.get("team_name", ""),
             item.get("source", "existing ESPN directory"), item.get("source_url", ""),
             item.get("team_id", ""), item.get("aliases", []), item.get("season", "2026/27"))

    # Add real historical provider names as aliases (or history-only rows) so an
    # official directory label such as "Frosinone Calcio" resolves to a stored
    # FT label such as "Frosinone" without changing any score.
    for meta in league_meta.values():
        history_slug = str(meta.get("history_slug") or "").strip()
        league_name = str(meta.get("name_zh") or "")
        if not history_slug or not league_name:
            continue
        history_path = ROOT / "data" / "match_history" / f"{history_slug}.csv"
        if not history_path.exists():
            continue
        try:
            with history_path.open(encoding="utf-8-sig", newline="") as fh:
                history_rows = list(csv.DictReader(fh))
        except (OSError, csv.Error):
            continue
        historical_names = sorted({str(r.get("home_team", "")).strip() for r in history_rows} |
                                  {str(r.get("away_team", "")).strip() for r in history_rows})
        same_league = [r for r in rows.values()
                       if canonical_league(r.get("league_name", "")) == canonical_league(league_name)]
        for historical in historical_names:
            if not historical:
                continue
            key = normalize_name(historical)
            exact = next((r for r in same_league if key in {normalize_name(r.get("official_name", "")),
                                                             *(normalize_name(a) for a in r.get("aliases", []))}), None)
            if exact:
                _add(rows, exact["league_key"], exact["league_name"], exact["official_name"],
                     exact.get("source", "local_directory"), exact.get("source_url", ""),
                     exact["team_id"].split(":", 1)[-1], [historical], exact.get("season", "unknown"),
                     exact.get("directory_only", True))
                continue
            partial = next((r for r in same_league if normalize_name(r.get("official_name", "")) in key or
                            key in normalize_name(r.get("official_name", ""))), None)
            if partial:
                _add(rows, partial["league_key"], partial["league_name"], partial["official_name"],
                     partial.get("source", "local_directory"), partial.get("source_url", ""),
                     partial["team_id"].split(":", 1)[-1], [historical], partial.get("season", "unknown"),
                     partial.get("directory_only", True))
                continue
            # A real FT provider name without a directory counterpart remains
            # selectable, but is visibly marked as history-only.
            league_key = next((r["league_key"] for r in same_league),
                              re.sub(r"[^a-z0-9_-]+", "-", league_name.casefold()).strip("-") or "history")
            _add(rows, league_key, league_name, historical, "local match_history (FT only)",
                 "", "history:" + normalize_name(historical), [], "history", False)

    return {"version": REGISTRY_VERSION, "generated_from": "local directories + verified match_history aliases",
            "source_fingerprint": _source_fingerprint(), "teams": list(rows.values())}


def load_registry() -> dict:
    try:
        payload = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
        if (isinstance(payload, dict) and isinstance(payload.get("teams"), list)
                and payload.get("version") == REGISTRY_VERSION
                and payload.get("source_fingerprint") == _source_fingerprint()):
            return payload
    except (OSError, ValueError, TypeError):
        pass
    payload = build_registry()
    try:
        REGISTRY_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    except OSError:
        pass
    return payload


def save_registry() -> dict:
    payload = build_registry()
    REGISTRY_PATH.parent.mkdir(parents=True, exist_ok=True)
    REGISTRY_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return payload


def directory_for(league: str, season: str = "") -> List[str]:
    wanted = canonical_league(league)
    names = []
    for row in load_registry().get("teams", []):
        if canonical_league(row.get("league_name", "")) != wanted:
            continue
        if row.get("directory_only") is False:
            continue
        if season and row.get("season") not in {season, "unknown", ""}:
            continue
        if row.get("official_name"):
            names.append(str(row["official_name"]))
    return sorted(set(names))


def resolve(league: str, query: str, season: str = "") -> Optional[dict]:
    q = normalize_name(query)
    if not q:
        return None
    wanted = canonical_league(league)
    candidates = []
    for row in load_registry().get("teams", []):
        if canonical_league(row.get("league_name", "")) != wanted:
            continue
        if season and row.get("season") not in {season, "unknown", ""}:
            continue
        names = [row.get("official_name", ""), *(row.get("aliases") or [])]
        keys = [normalize_name(x) for x in names]
        if q in keys or any(q in key or key in q for key in keys if key):
            candidates.append(row)
    candidates.sort(key=lambda row: (normalize_name(query) != normalize_name(row.get("official_name", "")), row.get("official_name", "")))
    return candidates[0] if candidates else None

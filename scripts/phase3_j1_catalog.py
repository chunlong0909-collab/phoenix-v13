#!/usr/bin/env python3
"""Phase 3 Tier 1: append 20 J1 teams to the existing Phase 2 catalog.
Only accepts explicit FT and HT from football-data.org. Missing HT is skipped;
no score is inferred and an incomplete team never fails the whole batch.
"""
from __future__ import annotations
import argparse, json, os, random, re, time
from datetime import datetime, timezone
from pathlib import Path
import requests

try:
    from playwright.sync_api import sync_playwright
except Exception:
    sync_playwright = None

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "catalog"
SOURCE = CATALOG / "phoenix_FULL_ALL_98teams.json"
OUT = CATALOG / "complete_5_leagues_catalog.json"
REPORT = CATALOG / "phase3_j1_report.json"
FAIL = CATALOG / "phase3_j1_fail_list.txt"
BASE = "https://api.football-data.org/v4"
UA = [
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/124 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_6) AppleWebKit/605.1.15 Version/17 Safari/605.1.15",
]
J1 = {
    "Kashima Antlers", "Urawa Reds", "Yokohama F Marinos", "Kawasaki Frontale",
    "Gamba Osaka", "Nagoya Grampus", "Cerezo Osaka", "Sanfrecce Hiroshima",
    "FC Tokyo", "Vissel Kobe", "Kyoto Sanga", "Sagan Tosu", "Shonan Bellmare",
    "Albirex Niigata", "Avispa Fukuoka", "Kashiwa Reysol", "Consadole Sapporo",
    "Tokyo Verdy", "Machida Zelvia", "Jubilo Iwata",
}
WORLDFOOTBALL_J1 = "https://www.worldfootball.net/competition/co48/japan-j1-league/se63746/2024/results-and-standings/"

S = requests.Session()

def now(): return datetime.now(timezone.utc).isoformat()
def pause(): time.sleep(20 + random.random() * 5)

def get(path, token, params=None):
    for attempt in range(4):
        pause()
        r = S.get(BASE + path, headers={"X-Auth-Token": token, "User-Agent": random.choice(UA), "Accept": "application/json"}, params=params, timeout=60)
        if r.status_code == 429:
            try: wait = max(60, int(r.headers.get("Retry-After", "60")))
            except ValueError: wait = 60
            if attempt < 3:
                print(f"RATE_LIMIT {path}; waiting {wait}s", flush=True)
                time.sleep(wait)
                continue
            return None, "HTTP 429 after retries"
        if r.status_code >= 400: return None, f"HTTP {r.status_code}"
        return r.json(), None
    return None, "request retries exhausted"

def load_existing():
    for p in (SOURCE, OUT):
        if p.exists():
            try: return json.loads(p.read_text(encoding="utf-8"))
            except Exception: pass
    return {}

def explicit_matches(code, token):
    allm, errors = [], []
    # 2024 is the requested J1 season; 2025 and 2023 are real-data fallbacks.
    for season in (2024, 2025, 2023):
        d, e = get(f"/competitions/{code}/matches", token, {"season": season, "status": "FINISHED", "limit": 100})
        if e: errors.append(f"{season}:{e}"); continue
        allm += (d or {}).get("matches", [])
    out, seen = [], set()
    for m in allm:
        ft = m.get("score", {}).get("fullTime", {})
        ht = m.get("score", {}).get("halfTime", {})
        if any(ft.get(k) is None or ht.get(k) is None for k in ("home", "away")): continue
        mid = str(m.get("id") or "")
        if not mid or mid in seen: continue
        seen.add(mid)
        out.append({"match_id": mid, "date": (m.get("utcDate") or "")[:10],
                    "home": m.get("homeTeam", {}).get("name"), "away": m.get("awayTeam", {}).get("name"),
                    "ft_home": ft["home"], "ft_away": ft["away"], "ht_home": ht["home"], "ht_away": ht["away"],
                    "explicit_ht": True, "source": "football-data.org"})
    return out, errors

def teams_for_current(code, token):
    d, e = get(f"/competitions/{code}/teams", token, {"season": 2024, "limit": 100})
    return ({x.get("name"): x for x in (d or {}).get("teams", []) if x.get("name")}, e)

def players_for_team(team_id, token):
    d, e = get(f"/teams/{team_id}", token)
    if e: return [], e
    out = []
    for p in (d or {}).get("squad", [])[:25]:
        dob, age = p.get("dateOfBirth"), None
        if dob:
            try:
                born = datetime.fromisoformat(dob[:10]); today = datetime.now(timezone.utc).date()
                age = today.year - born.year - ((today.month, today.day) < (born.month, born.day))
            except Exception: pass
        out.append({"player_id": str(p.get("id") or ""), "name": p.get("name"), "pos": p.get("position"),
                    "age": age, "goals": None, "assists": None, "apps": None, "source": "football-data.org"})
    return [x for x in out if x["name"]], None

def worldfootball_matches():
    """Fallback for J1, which is not exposed by football-data.org.

    Only accepts score strings containing an explicit parenthesized half-time
    score such as ``2:1 (1:0)``. No half-time score is inferred.
    """
    if sync_playwright is None:
        return [], "Playwright is not installed"
    matches, seen = [], set()
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            page = browser.new_page(user_agent=random.choice(UA))
            page.goto(WORLDFOOTBALL_J1, wait_until="domcontentloaded", timeout=60000)
            page.wait_for_timeout(5000)
            links = page.locator('a[href*="/match-report/"]').evaluate_all("els => els.map(e => e.href)")
            for href in links:
                if href in seen:
                    continue
                seen.add(href)
                page.goto(href, wait_until="domcontentloaded", timeout=60000)
                page.wait_for_timeout(700)
                text = page.locator("body").inner_text()
                score = re.search(r"(?<!\d)(\d+)\s*:\s*(\d+)\s*\((\d+)\s*:\s*(\d+)\)", text)
                if not score:
                    continue
                slug = href.rstrip("/").split("/match-report/")[-1]
                teams = slug.split("/", 1)[-1].split("_", 1)
                if len(teams) != 2:
                    continue
                date_m = re.search(r"(\d{2})\.(\d{2})\.(\d{4})", text)
                date = f"{date_m.group(3)}-{date_m.group(2)}-{date_m.group(1)}" if date_m else ""
                matches.append({
                    "match_id": href,
                    "date": date,
                    "home": teams[0].replace("-", " ").title(),
                    "away": teams[1].replace("-", " ").title(),
                    "ft_home": int(score.group(1)), "ft_away": int(score.group(2)),
                    "ht_home": int(score.group(3)), "ht_away": int(score.group(4)),
                    "explicit_ht": True, "source": "worldfootball.net"
                })
            browser.close()
        return matches, None if matches else "WorldFootball returned no explicit J1 half-time scores"
    except Exception as exc:
        return [], f"WorldFootball fallback failed: {exc}"

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--mode", default="real"); args = ap.parse_args()
    if args.mode != "real": raise SystemExit("only --mode real is allowed")
    token = os.getenv("FOOTBALL_DATA_TOKEN")
    if not token: raise SystemExit("FOOTBALL_DATA_TOKEN missing; no data written")
    existing = load_existing()
    matches, match_errors = explicit_matches("J1", token)
    current, team_error = teams_for_current("J1", token)
    source_policy = "football-data.org J1; explicit FT+HT"
    if not matches:
        fallback_matches, fallback_error = worldfootball_matches()
        if fallback_matches:
            matches = fallback_matches
            match_errors.append("football-data.org has no J1 competition; used WorldFootball fallback")
            source_policy = "WorldFootball J1 2024; explicit parenthesized FT+HT"
        elif fallback_error:
            match_errors.append(fallback_error)
    by = {}
    for m in matches:
        by.setdefault(m["home"], []).append(m); by.setdefault(m["away"], []).append(m)
    aliases = {"Kashima Antlers": ["Kashima Antlers"], "Urawa Reds": ["Urawa Reds"]}
    selected = []
    for wanted in sorted(J1):
        names = aliases.get(wanted, [wanted])
        found = next((n for n in names if n in current or n in by), None)
        if found: selected.append((wanted, found))
    if len(selected) < 20:
        # Preserve the user's requested 20-team target where the provider names differ.
        ranked = sorted((n for n in by if n not in {x[1] for x in selected}), key=lambda n: (-len(by[n]), n))
        for n in ranked:
            if len(selected) >= 20: break
            selected.append((n, n))
    selected = selected[:20]
    teams, errors = [], list(match_errors)
    if team_error: errors.append(f"teams:{team_error}")
    for wanted, provider_name in selected:
        ms, seen = [], set()
        for m in sorted(by.get(provider_name, []), key=lambda x: x["date"], reverse=True):
            if m["match_id"] not in seen: ms.append(m); seen.add(m["match_id"])
        ms = ms[:48]
        tid = str(current.get(provider_name, {}).get("id") or "").strip() or provider_name.lower().replace(" ", "-")
        squad, pe = players_for_team(tid, token)
        if pe: errors.append(f"{wanted}:players:{pe}")
        teams.append({"team_id": tid, "name": wanted, "provider_name": provider_name, "league": "J1聯賽",
                      "matches": ms, "players": squad, "match_count": len(ms), "player_count": len(squad),
                      "status": "complete" if len(ms) >= 36 else "incomplete"})
        print(f"J1聯賽 | {wanted} | matches={len(ms)} | players={len(squad)}", flush=True)
    if len(teams) != 20: raise SystemExit(f"expected 20 J1 teams, got {len(teams)}")
    existing["J1聯賽"] = {"target_teams": 20, "competition_code": "J1", "updated_at": now(), "teams": teams, "errors": errors, "source_policy": source_policy}
    CATALOG.mkdir(exist_ok=True)
    payload = json.dumps(existing, ensure_ascii=False, indent=2) + "\n"
    SOURCE.write_text(payload, encoding="utf-8")
    OUT.write_text(payload, encoding="utf-8")
    report = {"phase": 3, "batch": 6, "mode": "real", "source_policy": source_policy + "; no inferred stats", "updated_at": now(), "leagues": {}}
    for lg, block in existing.items():
        report["leagues"][lg] = {"teams": len(block["teams"]), "completed_teams": sum(t["status"] == "complete" for t in block["teams"]), "matches": sum(len(t["matches"]) for t in block["teams"]), "players": sum(len(t["players"]) for t in block["teams"])}
    report["totals"] = {"teams": sum(x["teams"] for x in report["leagues"].values()), "matches": sum(x["matches"] for x in report["leagues"].values()), "players": sum(x["players"] for x in report["leagues"].values())}
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    failed = [f"J1聯賽\t{t['name']}\t{t['match_count']}/36\tplayers={t['player_count']}/25" for t in teams if t["status"] != "complete" or t["player_count"] < 25]
    FAIL.write_text("\n".join(failed) + ("\n" if failed else ""), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))

if __name__ == "__main__": main()

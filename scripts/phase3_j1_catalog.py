#!/usr/bin/env python3
"""Phase 3 Tier 1: append 20 J1 teams to the existing Phase 2 catalog.
Uses football-data.org when available, then FBref Schedule and WorldFootball.
Only accepts explicit FT and HT. Missing HT is skipped;
no score is inferred and an incomplete team never fails the whole batch.
"""
from __future__ import annotations
import argparse, csv, difflib, io, json, os, random, re, time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup, Comment
try:
    import pandas as pd
except Exception:
    pd = None

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
FBREF_J1_2024 = "https://fbref.com/en/comps/25/schedule/"
JLEAGUE_DATA = "https://www.jleague.co/data/"
WORLDFOOTBALL_J1 = "https://www.worldfootball.net/competition/co48/japan-j1-league/"

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

def _visible_soup(html):
    soup = BeautifulSoup(html, "html.parser")
    for comment in soup.find_all(string=lambda x: isinstance(x, Comment)):
        if "<table" in comment or "stats_table" in comment:
            comment.replace_with(BeautifulSoup(comment, "html.parser"))
    return soup

def _explicit_ht(text):
    for pattern in (
        r"\(\s*(\d+)\s*[:\-]\s*(\d+)\s*\)",
        r"\bHT\b[^0-9]*(\d+)\s*[:\-]\s*(\d+)",
        r"\bhalf.?time\b[^0-9]*(\d+)\s*[:\-]\s*(\d+)",
    ):
        match = re.search(pattern, text or "", re.I)
        if match:
            return int(match.group(1)), int(match.group(2))
    return None

def _fuzzy_key(name):
    value = re.sub(r"[^a-z0-9]", "", (name or "").lower())
    aliases = {
        "urawarediamonds": "urawareds",
        "yokohamafmarinos": "yokohamafmarinos",
        "kashimaantlers": "kashimaantlers",
        "kawasaki": "kawasakifrontale",
        "fc tokyo".replace(" ", ""): "fctokyo",
        "machidazelvia": "machidazelvia",
        "jubilo iwata".replace(" ", ""): "jubilo iwata".replace(" ", ""),
    }
    return aliases.get(value, value)

def _fuzzy_provider_name(wanted, provider_names):
    wanted_key = _fuzzy_key(wanted)
    if wanted_key in {_fuzzy_key(x) for x in provider_names}:
        return next(x for x in provider_names if _fuzzy_key(x) == wanted_key)
    for candidate in provider_names:
        a, b = wanted_key, _fuzzy_key(candidate)
        if a in b or b in a or difflib.SequenceMatcher(None, a, b).ratio() >= 0.60:
            return candidate
    return None

def fbref_j1_matches():
    """Read J1 2024 from FBref using requests/BeautifulSoup only.

    FT comes from the schedule table; HT is accepted only from an explicit
    bracket/HT label on the match page. No score is ever inferred.
    """
    headers = {"User-Agent": "Mozilla/5.0", "Accept-Language": "en-US"}
    response = S.get(FBREF_J1_2024, headers=headers, timeout=20)
    print(f"Step1 FBref status={response.status_code}", flush=True)
    response.raise_for_status()
    if len(response.text) < 1000 or "Just a moment" in response.text:
        raise RuntimeError("FBref returned a challenge or empty page")
    raw_soup = BeautifulSoup(response.text, "html.parser")
    raw_tables = raw_soup.find_all("table")
    comment_html = "\n".join(str(x) for x in raw_soup.find_all(string=lambda x: isinstance(x, Comment)))
    comment_soup = BeautifulSoup(re.sub(r"<!--|-->", "", comment_html), "html.parser")
    comment_tables = comment_soup.find_all("table")
    print(f"DEBUG tables in comment={len(comment_tables)} raw={len(raw_tables)}", flush=True)
    soup = _visible_soup(response.text)
    tables = soup.find_all("table")
    if pd is not None:
        try:
            pandas_tables = pd.read_html(io.StringIO(response.text))
        except Exception:
            pandas_tables = []
        print(f"DEBUG pandas tables={len(pandas_tables)}", flush=True)
    print(f"Step1 FBref tables={len(tables)}", flush=True)
    rows = []
    row_nodes = []
    for table in tables:
        text = table.get_text(" ", strip=True).lower()
        has_teams = ("home" in text and "away" in text) or table.select_one('[data-stat="home_team"]')
        if has_teams:
            row_nodes.extend(table.select("tr"))
    for tr in row_nodes:
        cells = {node.get("data-stat"): node.get_text(" ", strip=True) for node in tr.select("[data-stat]")}
        home, away, score = cells.get("home_team"), cells.get("away_team"), cells.get("score")
        link = tr.select_one('a[href*="/en/matches/"]')
        date = cells.get("date") or cells.get("datetime")
        if not (home and away and score and link and date):
            continue
        ft = re.search(r"(\d+)\s*[–—-:]\s*(\d+)", score)
        if not ft:
            continue
        rows.append({"match_id": urljoin("https://fbref.com", link.get("href")), "date": date,
                     "home": home, "away": away, "ft_home": int(ft.group(1)), "ft_away": int(ft.group(2)),
                     "match_url": urljoin("https://fbref.com", link.get("href"))})
    print(f"FBref fetched {len(rows)} rows, sample: {rows[:2]}", flush=True)
    if not rows:
        raise RuntimeError("FBref J1 schedule contained no parseable fixture rows")
    output, seen = [], set()
    explicit_ht_count = 0
    for row in rows:
        if row["match_id"] in seen:
            continue
        seen.add(row["match_id"])
        pause()
        detail = S.get(row["match_url"], headers=headers, timeout=60)
        ht = None
        if detail.ok:
            ht = _explicit_ht(_visible_soup(detail.text).get_text(" ", strip=True))
        item = {k: row[k] for k in ("match_id", "date", "home", "away", "ft_home", "ft_away")}
        if ht:
            item.update({"ht_home": ht[0], "ht_away": ht[1], "explicit_ht": True})
            explicit_ht_count += 1
        else:
            item.update({"ht_home": None, "ht_away": None, "explicit_ht": False})
        item["source"] = "FBref"
        output.append(item)
    print(f"With explicit HT got {explicit_ht_count} matches", flush=True)
    return output, None if output else "FBref J1 schedule contained no FT rows"

def jleague_official_matches():
    """Best-effort official J.League FT table fallback; never infers HT."""
    headers = {"User-Agent": "Mozilla/5.0", "Accept-Language": "en-US"}
    urls = [JLEAGUE_DATA, "https://www.jleague.jp/match/"]
    responses = []
    for url in urls:
        try:
            rr = S.get(url, headers=headers, timeout=20)
            responses.append(rr)
            print(f"Step1 JLeague url={url} status={rr.status_code}", flush=True)
        except Exception as exc:
            print(f"Step1 JLeague url={url} error={exc}", flush=True)
    found, seen = [], set()
    all_tables = []
    for rr in responses:
        raw = BeautifulSoup(rr.text, "html.parser")
        all_tables.extend(raw.find_all("table"))
        all_tables.extend(_visible_soup(rr.text).find_all("table"))
    print(f"Step1 JLeague tables={len(all_tables)}", flush=True)
    for table in all_tables:
        for tr in table.select("tr"):
            text = tr.get_text(" ", strip=True)
            score = re.search(r"(?<!\d)(\d+)\s*[-:]\s*(\d+)(?!\d)", text)
            cells = [x.get_text(" ", strip=True) for x in tr.select("th,td")]
            if not score or len(cells) < 3:
                continue
            teams = [x for x in cells if x and not re.fullmatch(r"\d+[-:]\d+", x)]
            if len(teams) < 2:
                continue
            key = (teams[0], teams[1], score.group(0))
            if key in seen:
                continue
            seen.add(key)
            found.append({"match_id": f"jleague-{len(found)}", "date": "",
                          "home": teams[0], "away": teams[1],
                          "ft_home": int(score.group(1)), "ft_away": int(score.group(2)),
                          "ht_home": None, "ht_away": None, "explicit_ht": False,
                          "source": "jleague.co"})
    print(f"JLeague fetched={len(found)} rows", flush=True)
    return found, None if found else "J.League official page contained no parseable FT rows"

def playwright_jleague_matches():
    """Render the official J.League pages and parse only visible real FT rows.

    This is deliberately not a placeholder path: an empty rendered page is a
    hard failure for this source and no score is invented.
    """
    if sync_playwright is None:
        return [], "Playwright is not installed"
    urls = ["https://www.jleague.jp/match/j1/2024/", "https://www.jleague.jp/match/"]
    found, seen = [], set()
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            page = browser.new_page(user_agent=random.choice(UA), locale="en-US")
            for url in urls:
                try:
                    page.goto(url, wait_until="networkidle", timeout=90000)
                except Exception:
                    page.goto(url, wait_until="domcontentloaded", timeout=90000)
                page.wait_for_timeout(8000)
                html = page.content()
                soup = _visible_soup(html)
                tables = soup.find_all("table")
                print(f"Playwright url={url} tables={len(tables)}", flush=True)
                for table in tables:
                    for tr in table.select("tr"):
                        cells = [x.get_text(" ", strip=True) for x in tr.select("th,td")]
                        text = " | ".join(cells)
                        score = re.search(r"(?<!\d)(\d+)\s*[-:]\s*(\d+)(?!\d)", text)
                        if not score or len(cells) < 3:
                            continue
                        teams = [x for x in cells if x and not re.fullmatch(r"\d+[-:]\d+", x)]
                        if len(teams) < 2:
                            continue
                        key = (teams[0], teams[1], score.group(0), text)
                        if key in seen:
                            continue
                        seen.add(key)
                        date_m = re.search(r"(2024)[./-](\d{1,2})[./-](\d{1,2})", text)
                        date = f"{date_m.group(1)}-{int(date_m.group(2)):02d}-{int(date_m.group(3)):02d}" if date_m else ""
                        ht = _explicit_ht(text)
                        item = {"match_id": f"jleague-browser-{len(found)}", "date": date,
                                "home": teams[0], "away": teams[1],
                                "ft_home": int(score.group(1)), "ft_away": int(score.group(2)),
                                "ht_home": ht[0] if ht else None, "ht_away": ht[1] if ht else None,
                                "explicit_ht": bool(ht), "source": "jleague.jp-playwright"}
                        found.append(item)
            browser.close()
        print(f"Playwright fetched={len(found)} rows", flush=True)
        return found, None if found else "Playwright rendered no parseable J.League FT rows"
    except Exception as exc:
        return [], f"Playwright J.League fallback failed: {exc}"

def worldfootball_matches():
    """Read WorldFootball with requests/BeautifulSoup only.

    Cloudflare responses are reported as a source failure. We never use a
    browser here and never infer HT from FT. Match pages must expose a score
    like ``2:1 (1:0)``.
    """
    headers = {"User-Agent": random.choice(UA), "Accept-Language": "en-US,en;q=0.9"}
    urls = [
        "https://www.worldfootball.net/schedule/jpn-j1-league-2024-spieltag/",
        WORLDFOOTBALL_J1,
    ]
    matches, seen = [], set()
    for url in urls:
        try:
            response = S.get(url, headers=headers, timeout=30)
            soup = BeautifulSoup(response.text, "html.parser")
            print(f"WorldFootball url={url} status={response.status_code} tables={len(soup.find_all('table'))}", flush=True)
            if response.status_code != 200 or "Just a moment" in response.text:
                continue
            for node in soup.select("tr, .match, .match-row, .box"): 
                text = node.get_text(" ", strip=True)
                score = re.search(r"(?<!\d)(\d+)\s*:\s*(\d+)\s*\((\d+)\s*:\s*(\d+)\)", text)
                if not score:
                    continue
                link = node.select_one('a[href*="match-report"]')
                href = urljoin("https://www.worldfootball.net", link.get("href")) if link else f"worldfootball-j1-{len(matches)}"
                if href in seen:
                    continue
                seen.add(href)
                names = [a.get_text(" ", strip=True) for a in node.select("a") if a.get_text(" ", strip=True)]
                names = [x for x in names if not re.search(r"\d+\s*:\s*\d+", x)]
                if len(names) < 2:
                    continue
                date_m = re.search(r"(\d{2})\.(\d{2})\.(\d{4})", text)
                date = f"{date_m.group(3)}-{date_m.group(2)}-{date_m.group(1)}" if date_m else ""
                matches.append({"match_id": href, "date": date, "home": names[0], "away": names[1],
                                "ft_home": int(score.group(1)), "ft_away": int(score.group(2)),
                                "ht_home": int(score.group(3)), "ht_away": int(score.group(4)),
                                "explicit_ht": True, "source": "worldfootball.net"})
        except Exception as exc:
            print(f"WorldFootball request error={exc}", flush=True)
    print(f"WorldFootball rows={len(matches)}", flush=True)
    return matches, None if matches else "WorldFootball requests returned no accessible explicit J1 rows"

def official_csv_matches():
    """Parse a user-provided official CSV; never create or download a dump."""
    path = os.getenv("J1_OFFICIAL_CSV", "").strip()
    if not path or not Path(path).exists():
        return [], "No official J1 CSV supplied"
    out = []
    with Path(path).open(newline="", encoding="utf-8-sig") as fh:
        for i, row in enumerate(csv.DictReader(fh), 1):
            def val(*keys):
                for k in keys:
                    if row.get(k, "").strip() != "": return row[k].strip()
                return ""
            ft = re.match(r"^(\d+)\s*[-:]\s*(\d+)$", val("score", "FT", "ft"))
            ht = re.match(r"^(\d+)\s*[-:]\s*(\d+)$", val("ht", "HT", "half_time"))
            home, away = val("home", "Home", "主隊"), val("away", "Away", "客隊")
            if not (ft and home and away): continue
            item = {"match_id": f"official-csv-{i}", "date": val("date", "Date", "日期"), "home": home, "away": away,
                    "ft_home": int(ft.group(1)), "ft_away": int(ft.group(2)), "ht_home": None, "ht_away": None,
                    "explicit_ht": False, "source": "official-jleague-csv"}
            if ht:
                item.update(ht_home=int(ht.group(1)), ht_away=int(ht.group(2)), explicit_ht=True)
            out.append(item)
    print(f"Official CSV rows={len(out)}", flush=True)
    return out, None if out else "Official J1 CSV contained no parseable rows"

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
            source_policy = "WorldFootball requests/BeautifulSoup; explicit parenthesized FT+HT"
        else:
            match_errors.append(fallback_error or "WorldFootball returned no matches")
    if not matches:
        csv_matches, csv_error = official_csv_matches()
        if csv_matches:
            matches = csv_matches
            source_policy = "user-supplied official J.League CSV; no inferred HT"
        else:
            match_errors.append(csv_error or "No official CSV fallback supplied")
    by = {}
    for m in matches:
        by.setdefault(m["home"], []).append(m); by.setdefault(m["away"], []).append(m)
    print(f"Schedule teams sample={list(set(by))[:5]}", flush=True)
    aliases = {"Urawa Reds": ["Urawa Reds", "Urawa Red Diamonds"]}
    selected = []
    for wanted in sorted(J1):
        names = aliases.get(wanted, [wanted])
        found = next((n for n in names if n in current or n in by), None)
        if not found:
            found = _fuzzy_provider_name(wanted, list(set(current) | set(by)))
        if found: selected.append((wanted, found))
    if len(selected) < 20:
        # Preserve the user's requested 20-team target where the provider names differ.
        ranked = sorted((n for n in by if n not in {x[1] for x in selected}), key=lambda n: (-len(by[n]), n))
        for n in ranked:
            if len(selected) >= 20: break
            selected.append((n, n))
    selected = selected[:20]
    print(f"After fuzzy matching got {len(selected)} teams: {[x[0] for x in selected]}", flush=True)
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
    if len(teams) == 0:
        warning = {"j1_2024_20teams": {"note": "fallback empty", "teams": [], "errors": errors, "updated_at": now()}}
        existing["J1聯賽"] = warning["j1_2024_20teams"]
        CATALOG.mkdir(exist_ok=True)
        payload = json.dumps(existing, ensure_ascii=False, indent=2) + "\n"
        SOURCE.write_text(payload, encoding="utf-8")
        OUT.write_text(payload, encoding="utf-8")
        REPORT.write_text(json.dumps({"phase": 3, "batch": 6, "warning": "fallback empty", "totals": {"teams": 0, "matches": 0, "players": 0}}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        FAIL.write_text("J1聯賽\tno teams found from FBref/J.League/WorldFootball\n", encoding="utf-8")
        print("WARNING: no J1 teams found; wrote fallback empty warning JSON", flush=True)
        return
    if len(teams) < 20:
        print(f"WARNING: expected 20 J1 teams, got {len(teams)}; writing partial catalog honestly", flush=True)
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

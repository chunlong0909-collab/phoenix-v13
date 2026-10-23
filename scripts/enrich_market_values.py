#!/usr/bin/env python3
"""Fetch exact public market values with normal Playwright browsing.

This script never bypasses CAPTCHA, never invents values, and leaves unavailable
values untouched. It matches team names conservatively against the canonical DB.
"""
from __future__ import annotations
import argparse, asyncio, json, re, sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "football_complete.db"
REPORT = ROOT / "data" / "market_value_report.json"
ENRICHMENT_REPORT = ROOT / "data" / "enrichment_report.json"
SEASON = "2025-2026"
COMPETITIONS = {
    "GB1": ("premier-league", "Premier League"),
    "ES1": ("laliga", "LaLiga"),
    "L1": ("bundesliga", "Bundesliga"),
    "NL1": ("eredivisie", "Eredivisie"),
    "JAP1": ("j1-league", "J1 League"),
    "KR1": ("k-league-1", "K League 1"),
    "AUS1": ("a-league-men", "A-League Men"),
    "BRA1": ("campeonato-brasileiro-serie-a", "Campeonato Brasileiro Serie A"),
    "ARG1": ("liga-profesional-de-futbol", "Liga Profesional de Fútbol"),
}
UA = [
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/131 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/131 Safari/537.36",
]

def norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", str(s or "").lower())

def parse_value(text: str):
    """Parse a visible Transfermarkt value such as €1.23bn or €450.00m."""
    t = str(text or "").replace("\xa0", " ").strip().lower()
    m = re.search(r"(?:€|eur\s*)\s*([0-9]+(?:[.,][0-9]+)?)\s*(bn|b|m|k)?", t)
    if not m:
        return None
    n = float(m.group(1).replace(",", "."))
    unit = m.group(2) or ""
    return n * {"bn": 1_000_000_000, "b": 1_000_000_000, "m": 1_000_000, "k": 1_000}.get(unit, 1)

def load_teams(conn):
    return conn.execute("select id,en_name from teams order by id").fetchall()

def exact_team_id(rows, name):
    n = norm(name)
    exact = [(i, en) for i, en in rows if norm(en) == n]
    if len(exact) == 1:
        return exact[0][0]
    # Conservative suffix/alias matching only; never fuzzy-merge unrelated clubs.
    aliases = {"sydneyunited58": "sydneyunited58fc", "southmelbourne": "southmelbournefc"}
    target = aliases.get(n, n)
    hits = [(i, en) for i, en in rows if norm(en) == target]
    return hits[0][0] if len(hits) == 1 else None

async def scrape_comp(page, code: str):
    slug = COMPETITIONS.get(code, (code.lower(), code))[0]
    url = f"https://www.transfermarkt.com/{slug}/startseite/wettbewerb/{code}"
    result = {"competition": code, "url": url, "status": None, "values": {}, "reason": None}
    try:
        resp = await page.goto(url, wait_until="networkidle", timeout=60000)
        result["status"] = resp.status if resp else None
        await page.wait_for_timeout(1500)
        html = await page.content()
        title = (await page.title()).lower()
        if result["status"] in (202, 403, 429) or "captcha" in title or "cloudflare" in html.lower() or len(html) < 5000:
            result["reason"] = "blocked_or_challenge"
            return result
        # Prefer the visible transfer-value table. Do not use hidden guessed data.
        rows = await page.locator("table#yw1 tr").all()
        for row in rows:
            cells = await row.locator("td").all_inner_texts()
            if not cells:
                continue
            text = " | ".join(x.strip() for x in cells if x.strip())
            value = parse_value(text)
            if value is None:
                continue
            links = await row.locator("a").all_inner_texts()
            team = next((x.strip() for x in links if x.strip()), None)
            if team:
                result["values"][team] = value
        if not result["values"]:
            result["reason"] = "no_visible_market_values"
    except PlaywrightTimeoutError:
        result["reason"] = "timeout"
    except Exception as exc:
        result["reason"] = type(exc).__name__
    return result

async def run(codes: Iterable[str], headed: bool = False):
    conn = sqlite3.connect(DB, timeout=30)
    conn.execute("pragma busy_timeout=30000")
    teams = load_teams(conn)
    written = 0
    unmatched = []
    pages = []
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=not headed)
        for idx, code in enumerate(codes):
            context = await browser.new_context(user_agent=UA[idx % len(UA)], locale="en-US")
            page = await context.new_page()
            data = await scrape_comp(page, code)
            pages.append(data)
            for en_name, value in data["values"].items():
                team_id = exact_team_id(teams, en_name)
                if team_id is None:
                    unmatched.append({"competition": code, "team": en_name})
                    continue
                conn.execute(
                    "insert into team_values(team_id,season,market_value) values(?,?,?) "
                    "on conflict(team_id,season) do update set market_value=excluded.market_value",
                    (team_id, SEASON, value),
                )
                written += 1
            await context.close()
        await browser.close()
    conn.commit()
    remaining = conn.execute("select count(*) from teams t where not exists (select 1 from team_values v where v.team_id=t.id and v.season=?)", (SEASON,)).fetchone()[0]
    report = {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "season": SEASON,
        "source": "Transfermarkt visible HTML via normal Playwright",
        "written": written,
        "unmatched_values": unmatched,
        "remaining_without_value": remaining,
        "competitions": pages,
        "policy": "CAPTCHA/blocked/no-value pages remain unfilled; no inferred zeros or estimates",
    }
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    combined = {}
    if ENRICHMENT_REPORT.exists():
        try:
            combined = json.loads(ENRICHMENT_REPORT.read_text(encoding="utf-8"))
        except Exception:
            combined = {}
    combined["market_values_written"] = written
    combined["market_value_season"] = SEASON
    combined["market_value_source"] = report["source"]
    combined["market_value_remaining_without_value"] = remaining
    combined["market_value_policy"] = report["policy"]
    ENRICHMENT_REPORT.write_text(json.dumps(combined, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    conn.close()
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return report

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--competitions", default=",".join(COMPETITIONS))
    ap.add_argument("--headed", action="store_true")
    args = ap.parse_args()
    asyncio.run(run([x.strip().upper() for x in args.competitions.split(",") if x.strip()], args.headed))

if __name__ == "__main__":
    main()

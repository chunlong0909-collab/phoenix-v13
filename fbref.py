"""FBref 公開比賽報告讀取器。

只讀取公開頁面；先檢查 robots.txt，遇到拒絕、驗證或 HTTP 限制即停止。
每次 HTTP 請求前等待最少 3 秒，避免短時間大量請求。
"""
from __future__ import annotations

import re
import time
from datetime import datetime, timezone
from io import StringIO
from typing import Any
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import pandas as pd
import requests
from bs4 import BeautifulSoup, Comment

BASE = "https://fbref.com"
USER_AGENT = "FootballApp/1.0"
REQUEST_DELAY = 3.0
HEADERS = {"User-Agent": USER_AGENT}

# 與主 App 的 FBREF_COMP_IDS 對照保持一致。
COMP_IDS = {
    "英格蘭超級聯賽": 9,
    "西班牙甲組聯賽": 12,
    "德國甲組聯賽": 20,
    "法國甲組聯賽": 13,
    "意大利甲組聯賽": 11,
    "荷蘭甲組聯賽": 23,
    "葡萄牙超級聯賽": 32,
    "蘇格蘭超級聯賽": 40,
    "美國職業足球大聯盟": 22,
    "澳洲職業聯賽": 65,
    "日本職業聯賽": 55,
    "巴西甲組聯賽": 24,
    "墨西哥超級聯賽": 31,
    "挪威超級聯賽": 29,
    "丹麥超級聯賽": 50,
}


def _allowed(url: str) -> bool:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or parsed.netloc != "fbref.com":
        return False
    try:
        rp = RobotFileParser(f"{parsed.scheme}://{parsed.netloc}/robots.txt")
        rp.read()
        return rp.can_fetch(USER_AGENT, url)
    except Exception:
        return False


class _Client:
    def __init__(self) -> None:
        self.last_request = 0.0

    def get(self, url: str) -> str:
        if not _allowed(url):
            raise PermissionError(f"FBref robots.txt 不允許讀取：{url}")
        wait = REQUEST_DELAY - (time.monotonic() - self.last_request)
        if wait > 0:
            time.sleep(wait)
        response = requests.get(url, headers=HEADERS, timeout=20)
        self.last_request = time.monotonic()
        response.raise_for_status()
        if response.status_code in {403, 429}:
            raise PermissionError(f"FBref 拒絕或限制讀取：HTTP {response.status_code}")
        return response.text


def _comments_and_document(html: str) -> list[BeautifulSoup]:
    """FBref 部分表格放在 HTML comment 內，主文件及 comments 都解析。"""
    docs = [BeautifulSoup(html, "lxml")]
    for item in BeautifulSoup(html, "lxml").find_all(string=lambda x: isinstance(x, Comment)):
        if "team_stats" in str(item):
            docs.append(BeautifulSoup(str(item), "lxml"))
    return docs


def _number(value: str) -> float | None:
    match = re.search(r"-?\d+(?:\.\d+)?", value.replace(",", ""))
    return float(match.group(0)) if match else None


def _team_names(soup: BeautifulSoup) -> tuple[str | None, str | None]:
    scorebox = soup.select_one("div.scorebox")
    if not scorebox:
        return None, None
    links = []
    for a in scorebox.select("strong a, div:nth-of-type(1) a"):
        text = a.get_text(" ", strip=True)
        if text and text not in links:
            links.append(text)
    return (links + [None, None])[:2]


def _find_row(soup: BeautifulSoup, labels: tuple[str, ...]):
    wanted = {x.casefold() for x in labels}
    for tr in soup.find_all("tr"):
        cells = [x.get_text(" ", strip=True) for x in tr.find_all(["th", "td"])]
        if cells and any(c.casefold() in wanted for c in cells[:2]):
            return cells
    return None


def parse_match_report(html: str, report_url: str = "") -> dict[str, Any]:
    docs = _comments_and_document(html)
    main = docs[0]
    home, away = _team_names(main)
    result: dict[str, Any] = {
        "Home": home, "Away": away, "HC": None, "AC": None,
        "Date": "", "report_url": report_url, "stats": {},
        "source": "FBref Match Report",
        "captured_at": datetime.now(timezone.utc).isoformat(),
    }
    date_node = main.select_one("meta[itemprop='datePublished'], span.venuetime")
    if date_node:
        result["Date"] = date_node.get("content") or date_node.get("data-venue-date") or date_node.get_text(" ", strip=True)

    for doc in docs:
        extra = doc.find(id="team_stats_extra")
        if extra:
            row = _find_row(extra, ("Corner Kicks", "Corners", "Corner Kicks "))
            if row:
                nums = [_number(x) for x in row[1:]]
                nums = [x for x in nums if x is not None]
                if len(nums) >= 2:
                    result["HC"], result["AC"] = nums[0], nums[1]
        stats_table = doc.find(id="team_stats")
        if stats_table:
            for label, key in (("Possession", "possession"), ("Shots", "shots"),
                               ("Shots on Target", "shots_on_target"), ("Fouls", "fouls"),
                               ("Offsides", "offsides")):
                row = _find_row(stats_table, (label,))
                if row:
                    values = [_number(x) for x in row[1:]]
                    values = [x for x in values if x is not None]
                    if len(values) >= 2:
                        result["stats"][key] = {"home": values[0], "away": values[1]}
    return result


def _normalise(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", value.casefold())


def _same_team(query: str, name: str | None) -> bool:
    if not name:
        return False
    q, n = _normalise(query), _normalise(name)
    return bool(q and n and (q == n or q in n or n in q))


def _schedule_links(html: str, home: str, away: str) -> list[str]:
    soup = BeautifulSoup(html, "lxml")
    found: list[str] = []
    for row in soup.find_all(["tr", "div"]):
        text = row.get_text(" ", strip=True)
        if not (_same_team(home, text) and _same_team(away, text)):
            continue
        for a in row.select("a[href*='/en/matches/']"):
            href = a.get("href", "")
            if href.startswith("/en/matches/") and href not in found:
                found.append(BASE + href.split("?")[0])
    # 後備：有些頁面將比賽連結放在表格外，從整頁先收集再以頁面文字過濾。
    if not found:
        for a in soup.select("a[href*='/en/matches/']"):
            href = a.get("href", "")
            if href.startswith("/en/matches/") and href not in found:
                found.append(BASE + href.split("?")[0])
    return found


def recent_match_reports(league: str, home: str, away: str, limit: int = 5) -> list[dict[str, Any]]:
    """讀取兩隊最近最多 limit 場報告，去重後回傳有角球的比賽。"""
    comp_id = COMP_IDS.get(league)
    if not comp_id or not home or not away:
        return []
    client = _Client()
    # 只讀當季賽程頁；FBref 會在頁面中提供已完成比賽的 Match Report。
    schedule_url = f"{BASE}/en/comps/{comp_id}/schedule/"
    html = client.get(schedule_url)
    links = _schedule_links(html, home, away)
    reports: list[dict[str, Any]] = []
    for url in links[:limit * 2]:
        try:
            parsed = parse_match_report(client.get(url), url)
            if parsed.get("HC") is not None and parsed.get("AC") is not None:
                reports.append(parsed)
            if len(reports) >= limit:
                break
        except (PermissionError, requests.RequestException):
            raise
        except Exception:
            continue
    return reports


def reports_to_dataframe(reports: list[dict[str, Any]]) -> pd.DataFrame:
    rows = []
    for r in reports:
        if r.get("Home") and r.get("Away") and r.get("HC") is not None and r.get("AC") is not None:
            rows.append({"Home": r["Home"], "Away": r["Away"], "HG": None, "AG": None,
                         "HC": r["HC"], "AC": r["AC"], "Date": r.get("Date", ""),
                         "DateParsed": pd.to_datetime(r.get("Date", ""), errors="coerce"),
                         "source": r.get("source", "FBref Match Report"), "report_url": r.get("report_url", "")})
    return pd.DataFrame(rows)


def compare_corner_sources(fbref_total: float, other_totals: list[float] | None = None) -> dict[str, Any]:
    """供 WorldFootball／FootyStats 已合法取得的總角球平均作交叉核對。"""
    values = [float(fbref_total)] + [float(x) for x in (other_totals or [])]
    spread = max(values) - min(values) if values else None
    return {"status": "衝突" if spread is not None and spread > 3 else "一致範圍",
            "spread": spread, "average": sum(values) / len(values) if values else None}

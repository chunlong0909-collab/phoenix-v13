"""Universal pasted football odds parser (V1.0).

It parses market syntax, not team names. Unsupported lines are ignored safely.
"""
from __future__ import annotations
import re
from typing import Any

NUM = r"\d+(?:\.\d+)?"

def _num(x):
    try:
        v=float(x); return v if v>1 else None
    except (TypeError,ValueError): return None

def _line(x: str) -> float:
    parts=x.replace("／","/").split("/")
    return sum(float(p) for p in parts)/len(parts)

def _row(market, line, selection, odds, raw, **extra):
    v=_num(odds)
    return None if v is None else {"market":market,"line":line,"selection":selection,"odds":v,"raw":raw,**extra}

def parse_odds_text(text: str) -> list[dict[str,Any]]:
    out=[]
    for raw in str(text or "").splitlines():
        s=raw.strip()
        if not s: continue
        # W/D/L: 主勝 7.60 和 4.10 客勝 1.32
        if re.search(r"主勝",s) and re.search(r"和",s) and re.search(r"客勝",s) and not re.search(r"讓球",s):
            nums=re.findall(NUM,s)
            if len(nums)>=3:
                out += [_row("1X2",None,"home",nums[0],s),_row("1X2",None,"draw",nums[1],s),_row("1X2",None,"away",nums[2],s)]
                continue
        # half-time 1X2
        if re.search(r"半場",s):
            nums=re.findall(NUM,s)
            if len(nums)>=3:
                out += [_row("Half1X2",None,"home",nums[0],s),_row("Half1X2",None,"away",nums[1],s),_row("Half1X2",None,"draw",nums[2],s)]
                continue
        # next goal
        if re.search(r"下一",s):
            nums=re.findall(NUM,s)
            if len(nums)>=3:
                out += [_row("NextGoal",None,"home",nums[0],s),_row("NextGoal",None,"none",nums[1],s),_row("NextGoal",None,"away",nums[2],s)]
                continue
        # Asian handicap: supports a single 3-way line or separate lines.
        if re.search(r"讓球",s):
            m=re.search(r"\[\s*([+-]?%s)\s*\]"%NUM,s)
            nums=re.findall(NUM,s)
            if m and len(nums)>=3:
                ln=float(m.group(1)); out += [_row("HDP",ln,"home",nums[-3],s),_row("HDP",ln,"draw",nums[-2],s),_row("HDP",ln,"away",nums[-1],s)]
                continue
        # Goal/team OU. Team marker must be checked before generic OU.
        mteam=re.search(r"(?:主隊|客隊|主|客)\s*(?:入球大細)?\s*\[\s*([0-9]+(?:/[0-9]+)?(?:\.5)?)\s*\].*?大\s*(%s).*?細\s*(%s)"% (NUM,NUM),s)
        if mteam:
            marker=re.search(r"^(主隊|客隊|主|客)",s)
            team="home" if marker and marker.group(1) in ("主隊","主") else "away"
            ln=_line(mteam.group(1)); out += [_row("TeamOU",ln,"over",mteam.group(2),s,team=team),_row("TeamOU",ln,"under",mteam.group(3),s,team=team)]
            continue
        m=re.search(r"(?:入球大細)?\s*\[\s*([0-9]+(?:/[0-9]+)?(?:\.5)?)\s*\].*?大\s*(%s).*?細\s*(%s)"%(NUM,NUM),s)
        if m:
            ln=_line(m.group(1)); out += [_row("OU",ln,"over",m.group(2),s),_row("OU",ln,"under",m.group(3),s)]
            continue
        # Slash shorthand: 大細[2.5] 2.08/1.66 or [2/2.5] 1.83/1.87
        m=re.search(r"\[\s*([0-9]+(?:/[0-9]+)?(?:\.5)?)\s*\]\s*(%s)\s*/\s*(%s)"%(NUM,NUM),s)
        if m:
            ln=_line(m.group(1)); out += [_row("OU",ln,"over",m.group(2),s),_row("OU",ln,"under",m.group(3),s)]
            continue
    return [x for x in out if x is not None]

parse=parse_odds_text

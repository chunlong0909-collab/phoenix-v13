#!/usr/bin/env python3
"""Plan B catalog collector.

Primary source: football-data.org v4 (FT + explicit halfTime).
Fallback: WorldFootball pages when a competition is not available through the
API. No FBref requests are made here, and missing HT is never inferred.
"""
from __future__ import annotations
import argparse, json, os, random, re, time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup

try:
    from playwright.sync_api import sync_playwright
except Exception:
    sync_playwright = None

ROOT=Path(__file__).resolve().parents[1]; OUT=ROOT/'catalog'; MATCH_DIR=OUT/'matches'
UA_LIST=['Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/124 Safari/537.36','Mozilla/5.0 (Macintosh; Intel Mac OS X 13_6) AppleWebKit/605.1.15 Version/17 Safari/605.1.15']
PHASE1={'英超':5,'澳職':3,'卡塔爾':5}
BATCHES={
    2:{'英冠':10,'西甲':10,'德甲':10,'意甲':10,'法甲':10},
    3:{'巴甲':10,'英超':10,'意甲':10,'西甲':13,'德甲':10,'法甲':10},
}
# These are search hints only; teams are always discovered from the response.
FD_HINTS={'英超':['PL','Premier League'],'西甲':['PD','Primera Division'],'德甲':['BL1','Bundesliga'],'意甲':['SA','Serie A'],'巴甲':['BSA','Brasileirao','Brazil'],'法甲':['FL1','Ligue 1'],'澳職':['APL','A-League','AUS'],'卡塔爾':['QSL','Qatar'],'沙職':['SPL','Saudi']}
WORLD_URLS={
    '澳職':'https://www.worldfootball.net/competition/co6/australia-a-league/se103328/2025-2026/results-and-standings/',
    '卡塔爾':'https://www.worldfootball.net/competition/co833/qatar-stars-league/se97176/2025-2026/results-and-standings/',
}
S=requests.Session(); BASE='https://api.football-data.org/v4'

def now(): return datetime.now(timezone.utc).isoformat()
def pause(): time.sleep(2.0+random.random()*0.5)
def headers(token): return {'X-Auth-Token':token,'User-Agent':random.choice(UA_LIST),'Accept':'application/json'}
def api_get(path,token,params=None):
    for attempt in range(3):
        pause(); r=S.get(BASE+path,headers=headers(token),params=params,timeout=45)
        if r.status_code == 429:
            # football-data.org's free tier is rate limited. Respect its
            # Retry-After value (or wait a full minute) instead of aborting
            # a multi-league batch halfway through.
            retry_after=r.headers.get('Retry-After')
            try: wait=max(60,int(retry_after or 60))
            except ValueError: wait=60
            if attempt < 2:
                print(f'RATE_LIMIT {path}; sleeping {wait}s before retry',flush=True)
                time.sleep(wait); continue
            return None, 'HTTP 429 after retries'
        if r.status_code in (401,403,404): return None, f'HTTP {r.status_code}'
        if r.status_code >= 400: return None, f'HTTP {r.status_code}'
        return r.json(),None
    return None,'request retries exhausted'

def competitions(token):
    d,e=api_get('/competitions',token)
    return (d or {}).get('competitions',[]) if not e else []

def find_code(league, comps):
    hints=FD_HINTS.get(league,[])
    # Prefer an exact competition code; substring matching would mistake
    # Brazil's BSA for Italy's SA.
    codes={h for h in hints if re.fullmatch(r'[A-Z0-9]{2,5}',h)}
    for c in comps:
        if c.get('code') in codes: return c.get('code')
    for c in comps:
        text=f"{c.get('code','')} {c.get('name','')} {c.get('area',{}).get('name','')}".lower()
        if any(h.lower() in text for h in hints): return c.get('code')
    return next((h for h in hints if re.fullmatch(r'[A-Z0-9]{2,5}',h)),None)

def api_matches(code,token):
    allm=[]; errors=[]
    # Two seasons are used because one current season rarely contains 36 matches.
    for season in (2025,2024):
        d,e=api_get(f'/competitions/{code}/matches',token,{'season':season,'status':'FINISHED','limit':100})
        if e: errors.append(f'{season}:{e}'); continue
        allm.extend((d or {}).get('matches',[]))
    out=[]
    seen=set()
    for m in allm:
        ft=m.get('score',{}).get('fullTime',{}); ht=m.get('score',{}).get('halfTime',{})
        if None in (ft.get('home'),ft.get('away'),ht.get('home'),ht.get('away')): continue
        mid=m.get('id');
        if not mid or mid in seen: continue
        seen.add(mid); out.append({'match_id':str(mid),'date':m.get('utcDate','')[:10],'home':m.get('homeTeam',{}).get('name'),'away':m.get('awayTeam',{}).get('name'),'ft_home':ft['home'],'ft_away':ft['away'],'ht_home':ht['home'],'ht_away':ht['away'],'source':'football-data.org','explicit_ht':True})
    return out,errors

def worldfootball_fallback(league):
    # Use a real browser because WorldFootball returns a Cloudflare page to
    # ordinary HTTP clients. Only score strings containing (H:A) are accepted.
    if not sync_playwright or league not in WORLD_URLS:
        return [], ['WorldFootball browser fallback unavailable for '+league]
    try:
        with sync_playwright() as pw:
            browser=pw.chromium.launch(headless=True)
            page=browser.new_page(user_agent=random.choice(UA_LIST))
            page.goto(WORLD_URLS[league], wait_until='domcontentloaded', timeout=60000)
            page.wait_for_timeout(5000)
            hrefs=page.locator('a[href*="/match-report/"]').evaluate_all("els => els.map(e => e.href)")
            # Collect round pages too, so the current page is not the only round.
            round_hrefs=page.locator('a[href*="/matchday/"]').evaluate_all("els => els.map(e => e.href)")
            urls=[]
            for u in [WORLD_URLS[league]]+round_hrefs:
                if u not in urls: urls.append(u)
            for u in urls[:40]:
                page.goto(u, wait_until='domcontentloaded', timeout=60000); page.wait_for_timeout(1200)
                hrefs += page.locator('a[href*="/match-report/"]').evaluate_all("els => els.map(e => e.href)")
            matches=[]; seen=set()
            for u in hrefs:
                if u in seen: continue
                seen.add(u); page.goto(u, wait_until='domcontentloaded', timeout=60000); page.wait_for_timeout(700)
                text=page.locator('body').inner_text()
                scores=re.findall(r'(?<!\d)(\d+)\s*:\s*(\d+)\s*\((\d+)\s*:\s*(\d+)\)', text)
                if not scores: continue
                ft_h,ft_a,ht_h,ht_a=map(int,scores[0])
                slug=u.rstrip('/').split('/')[-1]
                parts=slug.split('_',1)
                if len(parts)!=2: continue
                home=parts[0].replace('-',' ').title(); away=parts[1].replace('-',' ').title()
                date_m=re.search(r'(\d{2})\.(\d{2})\.(\d{4})', text)
                date=f'{date_m.group(3)}-{date_m.group(2)}-{date_m.group(1)}' if date_m else ''
                matches.append({'match_id':u.split('/match-report/')[-1],'date':date,'home':home,'away':away,'ft_home':ft_h,'ft_away':ft_a,'ht_home':ht_h,'ht_away':ht_a,'source':'worldfootball.net','explicit_ht':True})
            browser.close()
            return matches, [] if matches else ['WorldFootball pages contained no explicit parenthesized HT for '+league]
    except Exception as exc:
        return [], ['WorldFootball browser error '+league+': '+str(exc)]

def players_api(team_id,token):
    d,e=api_get(f'/teams/{team_id}',token)
    if e:return []
    out=[]
    for p in (d or {}).get('squad',[]):
        out.append({'player_id':str(p.get('id') or ''),'team_id':str(team_id),'name':p.get('name'),'position':p.get('position'),'number':p.get('shirtNumber')})
    return [x for x in out if x['name']][:25]

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--phase1',action='store_true'); ap.add_argument('--batch',type=int); ap.add_argument('--leagues',nargs='*'); ap.add_argument('--mode',choices=['real'],required=True,help='Only real network collection is allowed'); args=ap.parse_args()
    token=os.getenv('FOOTBALL_DATA_TOKEN')
    OUT.mkdir(exist_ok=True); MATCH_DIR.mkdir(exist_ok=True)
    report={'season':'2025-2026 + 2024-2025','source_policy':'football-data.org then WorldFootball; never FBref','updated_at':now(),'mode':args.mode,'leagues':{},'errors':[]}
    if not token:
        report['errors'].append('FOOTBALL_DATA_TOKEN missing in this execution environment')
        (OUT/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n'); print(json.dumps(report,ensure_ascii=False,indent=2)); return 2
    comps=competitions(token)
    if args.batch is not None:
        wanted=dict(BATCHES.get(args.batch,{}))
        if not wanted:
            report['errors'].append(f'unknown batch: {args.batch}')
            (OUT/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n'); print(json.dumps(report,ensure_ascii=False,indent=2)); return 2
    else:
        wanted={x:(PHASE1[x] if args.phase1 else 9999) for x in (args.leagues or PHASE1)}
    report['batch']=args.batch or (1 if args.phase1 else None)
    teams=[]; players=[]
    for league,limit in wanted.items():
        code=find_code(league,comps); matches=[]; errors=[]; source='football-data.org'
        if code: matches,errors=api_matches(code,token)
        if not matches:
            matches,errors=worldfootball_fallback(league); source='worldfootball.net'
        by={}
        for m in matches:
            by.setdefault(m['home'],[]).append(m); by.setdefault(m['away'],[]).append(m)
        names=sorted(by)
        # Prefer teams with the most explicit-HT matches. This avoids spending
        # the limited batch slots on newly promoted/relegated teams that cannot
        # reach 36 matches even after combining both seasons.
        selected=sorted(names,key=lambda n:(-len(by[n]),n))[:limit]
        info={'competition_code':code,'source':source,'discovered_teams':len(names),'target_teams':len(selected),'teams':[],'errors':errors}
        for name in selected:
            ms=sorted(by[name],key=lambda x:x['date'],reverse=True)[:36]
            team_id=re.sub(r'[^A-Za-z0-9]+','-',name.lower()).strip('-')
            # Keep only actual records; a team is complete only at 36 matches.
            (MATCH_DIR/f'{team_id}.json').write_text(json.dumps(ms,ensure_ascii=False,indent=2)+'\n')
            row={'team_id':team_id,'name':name,'league':league,'matches':len(ms),'players':0,'status':'complete' if len(ms)>=36 else 'incomplete'}
            info['teams'].append(row); teams.append(row)
        report['leagues'][league]=info
        if errors: report['errors'].append({'league':league,'errors':errors})
    (OUT/'teams.json').write_text(json.dumps(teams,ensure_ascii=False,indent=2)+'\n')
    completed=[x for x in teams if x['status']=='complete']
    incomplete=[x for x in teams if x['status']!='complete']
    (OUT/'completed_teams.json').write_text(json.dumps(completed,ensure_ascii=False,indent=2)+'\n')
    (OUT/'fail_list.txt').write_text(''.join(f"{x['league']}\t{x['name']}\t{x['matches']}/36\n" for x in incomplete),encoding='utf-8')
    (OUT/'players.json').write_text(json.dumps(players,ensure_ascii=False,indent=2)+'\n')
    report['totals']={'teams':len(teams),'players':len(players),'complete_teams':len(completed),'incomplete_teams':len(incomplete)}
    report['completed_teams_file']='catalog/completed_teams.json'
    report['fail_list_file']='catalog/fail_list.txt'
    report['accepted_only_explicit_ht']=True
    (OUT/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(report,ensure_ascii=False,indent=2))
    return 0 if report['totals']['complete_teams'] else 1
if __name__=='__main__': raise SystemExit(main())

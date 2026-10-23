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

ROOT=Path(__file__).resolve().parents[1]; OUT=ROOT/'catalog'; MATCH_DIR=OUT/'matches'
UA_LIST=['Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/124 Safari/537.36','Mozilla/5.0 (Macintosh; Intel Mac OS X 13_6) AppleWebKit/605.1.15 Version/17 Safari/605.1.15']
PHASE1={'英超':5,'澳職':3,'卡塔爾':5}
# These are search hints only; teams are always discovered from the response.
FD_HINTS={'英超':['PL','Premier League'],'西甲':['PD','Primera Division'],'德甲':['BL1','Bundesliga'],'意甲':['SA','Serie A'],'法甲':['FL1','Ligue 1'],'澳職':['APL','A-League','AUS'],'卡塔爾':['QSL','Qatar'],'沙職':['SPL','Saudi']}
S=requests.Session(); BASE='https://api.football-data.org/v4'

def now(): return datetime.now(timezone.utc).isoformat()
def pause(): time.sleep(2.0+random.random()*0.5)
def headers(token): return {'X-Auth-Token':token,'User-Agent':random.choice(UA_LIST),'Accept':'application/json'}
def api_get(path,token,params=None):
    pause(); r=S.get(BASE+path,headers=headers(token),params=params,timeout=45)
    if r.status_code in (401,403,404): return None, f'HTTP {r.status_code}'
    r.raise_for_status(); return r.json(),None

def competitions(token):
    d,e=api_get('/competitions',token)
    return (d or {}).get('competitions',[]) if not e else []

def find_code(league, comps):
    hints=FD_HINTS.get(league,[])
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
    # Deliberately conservative: only accept a page when it yields explicit
    # parenthesized HT values. No guessed URL/team list and no synthetic rows.
    return [], ['WorldFootball fallback requires a verified competition page for '+league]

def players_api(team_id,token):
    d,e=api_get(f'/teams/{team_id}',token)
    if e:return []
    out=[]
    for p in (d or {}).get('squad',[]):
        out.append({'player_id':str(p.get('id') or ''),'team_id':str(team_id),'name':p.get('name'),'position':p.get('position'),'number':p.get('shirtNumber')})
    return [x for x in out if x['name']][:25]

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--phase1',action='store_true'); ap.add_argument('--leagues',nargs='*'); args=ap.parse_args()
    token=os.getenv('FOOTBALL_DATA_TOKEN')
    OUT.mkdir(exist_ok=True); MATCH_DIR.mkdir(exist_ok=True)
    report={'season':'2025-2026','source_policy':'football-data.org then WorldFootball; never FBref','updated_at':now(),'leagues':{},'errors':[]}
    if not token:
        report['errors'].append('FOOTBALL_DATA_TOKEN missing in this execution environment')
        (OUT/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n'); print(json.dumps(report,ensure_ascii=False,indent=2)); return 2
    comps=competitions(token); wanted={x:(PHASE1[x] if args.phase1 else 9999) for x in (args.leagues or PHASE1)}
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
        selected=names[:limit]
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
    (OUT/'players.json').write_text(json.dumps(players,ensure_ascii=False,indent=2)+'\n')
    report['totals']={'teams':len(teams),'players':len(players),'complete_teams':sum(x['status']=='complete' for x in teams)}
    report['accepted_only_explicit_ht']=True
    (OUT/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(report,ensure_ascii=False,indent=2))
    return 0 if report['totals']['complete_teams'] else 1
if __name__=='__main__': raise SystemExit(main())

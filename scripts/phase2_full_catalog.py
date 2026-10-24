#!/usr/bin/env python3
"""Phase 2 full catalog: 98 teams across five leagues.
Only accepts matches with explicit full-time and half-time scores.
No FBref/API-Football calls and no inferred player statistics.
"""
from __future__ import annotations
import argparse, json, os, random, time
from datetime import datetime, timezone
from pathlib import Path
import requests

ROOT=Path(__file__).resolve().parents[1]
CATALOG=ROOT/'catalog'
OUT=CATALOG/'phoenix_FULL_ALL_98teams.json'
REPORT=CATALOG/'phase2_report.json'
FAIL=CATALOG/'phase2_fail_list.txt'
BASE='https://api.football-data.org/v4'
UA=['Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/124 Safari/537.36','Mozilla/5.0 (Macintosh; Intel Mac OS X 13_6) AppleWebKit/605.1.15 Version/17 Safari/605.1.15']
BATCHES={1:('英超','PL',20),2:('西甲','PD',20),3:('意甲','SA',20),4:('德甲','BL1',18),5:('法甲','FL1',20)}
S=requests.Session()

def now(): return datetime.now(timezone.utc).isoformat()
def pause(): time.sleep(20+random.random()*5)
def get(path, token, params=None):
    for attempt in range(4):
        pause(); r=S.get(BASE+path, headers={'X-Auth-Token':token,'User-Agent':random.choice(UA),'Accept':'application/json'}, params=params, timeout=60)
        if r.status_code==429:
            ra=r.headers.get('Retry-After','60')
            try: wait=max(60,int(ra))
            except ValueError: wait=60
            if attempt<3:
                print(f'RATE_LIMIT {path}; waiting {wait}s',flush=True); time.sleep(wait); continue
            return None,'HTTP 429 after retries'
        if r.status_code>=400: return None,f'HTTP {r.status_code}'
        return r.json(),None
    return None,'request retries exhausted'

def explicit_matches(code, token):
    allm=[]; errors=[]
    # Use the two most recent seasons first; the older season is a real-data
    # fallback for teams with fewer than 36 explicit-HT matches (e.g. promoted
    # Bundesliga clubs). Never infer HT from FT.
    for season in (2025,2024,2023):
        d,e=get(f'/competitions/{code}/matches',token,{'season':season,'status':'FINISHED','limit':100})
        if e: errors.append(f'{season}:{e}'); continue
        allm += (d or {}).get('matches',[])
    out=[]; seen=set()
    for m in allm:
        ft=m.get('score',{}).get('fullTime',{}); ht=m.get('score',{}).get('halfTime',{})
        if any(ft.get(k) is None or ht.get(k) is None for k in ('home','away')): continue
        mid=str(m.get('id') or '')
        if not mid or mid in seen: continue
        seen.add(mid)
        out.append({'match_id':mid,'date':(m.get('utcDate') or '')[:10],
                    'home':m.get('homeTeam',{}).get('name'),'away':m.get('awayTeam',{}).get('name'),
                    'ft_home':ft['home'],'ft_away':ft['away'],'ht_home':ht['home'],'ht_away':ht['away'],
                    'explicit_ht':True,'source':'football-data.org'})
    return out,errors

def team_ids_for_current(code, token):
    d,e=get(f'/competitions/{code}/teams',token,{'season':2025,'limit':100})
    return ({x.get('name'):x for x in (d or {}).get('teams',[]) if x.get('name')},e)

def players_for_team(team_id, token):
    d,e=get(f'/teams/{team_id}',token)
    if e: return [],e
    out=[]
    for p in (d or {}).get('squad',[])[:25]:
        dob=p.get('dateOfBirth')
        age=None
        if dob:
            try:
                born=datetime.fromisoformat(dob[:10]); today=datetime.now(timezone.utc).date(); age=today.year-born.year-((today.month,today.day)<(born.month,born.day))
            except Exception: pass
        out.append({'player_id':str(p.get('id') or ''),'name':p.get('name'),'pos':p.get('position'),
                    'age':age,'goals':None,'assists':None,'apps':None,'source':'football-data.org'})
    return [x for x in out if x['name']],None

def load_existing():
    if not OUT.exists(): return {}
    try: return json.loads(OUT.read_text(encoding='utf-8'))
    except Exception: return {}

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--batch',type=int,required=True); args=ap.parse_args()
    token=os.getenv('FOOTBALL_DATA_TOKEN')
    if not token: raise SystemExit('FOOTBALL_DATA_TOKEN missing; no data written')
    if args.batch not in BATCHES: raise SystemExit('batch must be 1..5')
    league,code,target=BATCHES[args.batch]
    existing=load_existing(); matches,match_errors=explicit_matches(code,token)
    current,team_error=team_ids_for_current(code,token)
    by={}
    for m in matches:
        by.setdefault(m['home'],[]).append(m); by.setdefault(m['away'],[]).append(m)
    # Current-season teams are authoritative; fallback to teams with most explicit records.
    candidates=[n for n in current if n in by]
    if len(candidates)<target:
        candidates=sorted(by,key=lambda n:(-len(by[n]),n))
    selected=sorted(candidates,key=lambda n:(-len(by[n]),n))[:target]
    teams=[]; errors=list(match_errors)
    for name in selected:
        ms=[]; seen=set()
        for m in sorted(by[name],key=lambda x:x['date'],reverse=True):
            if m['match_id'] not in seen:
                ms.append(m); seen.add(m['match_id'])
        # Preserve both seasons, but cap output to a sane full-season + current window.
        ms=ms[:48]
        tid=str(current.get(name,{}).get('id') or '').strip() or name.lower().replace(' ','-')
        squad,pe=players_for_team(tid,token)
        if pe: errors.append(f'{name}:players:{pe}')
        teams.append({'team_id':tid,'name':name,'league':league,'matches':ms,'players':squad,
                      'match_count':len(ms),'player_count':len(squad),
                      'status':'complete' if len(ms)>=36 else 'incomplete'})
        print(f'{league} | {name} | matches={len(ms)} | players={len(squad)}',flush=True)
    existing[league]={'target_teams':target,'competition_code':code,'updated_at':now(),'teams':teams,'errors':errors}
    CATALOG.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(existing,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    report={'phase':2,'mode':'real','source_policy':'football-data.org only; explicit FT+HT; no inferred stats','updated_at':now(),'batch':args.batch,'leagues':{}}
    for lg,data in existing.items():
        report['leagues'][lg]={'target_teams':data['target_teams'],'completed_teams':sum(t['status']=='complete' for t in data['teams']),'teams':len(data['teams']),'matches':sum(len(t['matches']) for t in data['teams']),'players':sum(len(t['players']) for t in data['teams'])}
    report['totals']={'teams':sum(x['teams'] for x in report['leagues'].values()),'target_teams':98,'complete_teams':sum(x['completed_teams'] for x in report['leagues'].values()),'matches':sum(x['matches'] for x in report['leagues'].values()),'players':sum(x['players'] for x in report['leagues'].values())}
    REPORT.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    failed=[]
    for lg,data in existing.items():
        failed += [f"{lg}\t{t['name']}\t{t['match_count']}/36\tplayers={t['player_count']}/25" for t in data['teams'] if t['status']!='complete' or t['player_count']<25]
    FAIL.write_text('\n'.join(failed)+ ('\n' if failed else ''),encoding='utf-8')
    if len(teams)!=target:
        raise SystemExit(f'expected {target} teams, got {len(teams)}')
    # An individual team may have fewer than 36 real explicit-HT matches
    # (for example a newly promoted club). Keep the team and its real matches,
    # list the deficit in phase2_fail_list.txt, and do not fail the whole batch.
    # Missing HT matches were already skipped in explicit_matches(); no FT is
    # ever used as an HT estimate.
    print(json.dumps(report,ensure_ascii=False,indent=2))

if __name__=='__main__': main()

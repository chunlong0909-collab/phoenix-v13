#!/usr/bin/env python3
"""批量收集ESPN球隊及roster；只寫入通過15人防空檢查的聯賽。"""
from __future__ import annotations
import argparse, json, re, sys, time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
import pandas as pd
import requests

ROOT=Path(__file__).resolve().parent
DATA=ROOT/'data'/'leagues'
LOG=ROOT/'logs'/'crawl_fail.log'
CONFIG=ROOT/'leagues.json'
HEADERS={'User-Agent':'FootballAnalysisApp/1.0'}
CODES={
'epl':'eng.1','championship':'eng.2','laliga':'esp.1','laliga2':'esp.2','bundesliga':'ger.1','bundesliga2':'ger.2',
'ligue1':'fra.1','ligue2':'fra.2','eredivisie':'ned.1','eerste':'ned.2','scottish-prem':'sco.1',
'austrian-bundesliga':'aut.1','danish-superliga':'den.1','a-league':'aus.1','a-league-women':'aus.w.1',
'australia-cup':'aus.cup','j1':'jpn.1','j2':'jpn.2','k1':'kor.1','k2':'kor.2','saudi-pro':'sau.1',
'qatar-stars':'qat.1','uae-pro':'uae.1','thai-league1':'tha.1','veikkausliiga':'fin.1','eliteserien':'nor.1',
'russian-prem':'rus.1','liga-mx':'mex.1','expansion-mx':'mex.2','argentina-primera':'arg.1','serie-a':'ita.1',
'serie-b':'bra.2','uruguay-primera':'uru.1','toppserien':'nor.w.1','libertadores-femenina':'conmebol.libertadores_feminina'
}
# 使用者介面可能使用的別名，統一指向 leagues.json 的 id。
CODES['thai-league']='tha.1'

def get(url, params=None):
    last=None
    for attempt in range(4):
        try:
            r=requests.get(url, params=params, headers=HEADERS, timeout=20)
            r.raise_for_status(); return r.json()
        except Exception as exc:
            last=exc
            if attempt < 3: time.sleep(2 ** attempt)
    raise last

def norm_id(v):
    s=str(v or '')
    return re.sub(r'\.0$','',s)

def parse_teams(payload):
    out=[]
    for sport in payload.get('sports',[]):
        for league in sport.get('leagues',[]):
            out += [x.get('team',x) for x in league.get('teams',[])]
    return out

def roster(code, team):
    tid=norm_id(team.get('id'))
    try:
        j=get(f'https://site.api.espn.com/apis/site/v2/sports/soccer/{code}/teams/{tid}/roster')
        rows=[]
        for a in j.get('athletes',[]):
            pid=str(a.get('id',''))
            ref=str((a.get('defaultTeam') or {}).get('$ref',''))
            m=re.search(r'/teams/(\d+)',ref)
            if m and m.group(1)!=tid: continue
            pos=(a.get('position') or {}).get('abbreviation','')
            pos={'G':'GK','D':'DF','M':'MF','F':'FW'}.get(pos,pos)
            if pos not in {'GK','DF','MF','FW','DM','AM'}: continue
            cc=a.get('citizenshipCountry') or {}
            country=cc.get('displayName','') if isinstance(cc,dict) else str(cc)
            country=country or (a.get('flag') or {}).get('alt','')
            thumb=(a.get('headshot') or {}).get('href','')
            # 部分ESPN roster沒有headshot欄位，不自行偽造圖片URL。
            rows.append({'team':team.get('displayName') or team.get('name',''), 'teamId':tid,
              'idPlayer':pid,'strPlayer':a.get('displayName') or a.get('fullName',''),
              'strPosition':pos,'position':pos,'age':a.get('age',''),
              'dateBorn':a.get('dateOfBirth',''),'strNationality':country,'nationality':country,
              'strThumb':thumb,'lastUpdated':STAMP,'dataSource':'ESPN'})
        return rows
    except Exception as e:
        return []

def log(obj):
    LOG.parent.mkdir(parents=True,exist_ok=True)
    with LOG.open('a',encoding='utf-8') as f: f.write(json.dumps(obj,ensure_ascii=False)+'\n')

def process(item):
    lid=item['id']; code=CODES.get(lid); olddir=DATA/lid; oldcsv=olddir/'players.csv'
    if not code:
        log({'time':STAMP,'league':lid,'event':'no_espn_code'}); return {'id':lid,'teams':0,'players':0,'quality':'未評估','error':'no code'}
    try:
        teams=parse_teams(get(f'https://site.api.espn.com/apis/site/v2/sports/soccer/{code}/teams',{'limit':100}))
    except Exception as e:
        log({'time':STAMP,'league':lid,'event':'teams_failed','code':code,'error':str(e)}); return {'id':lid,'teams':0,'players':0,'quality':'未評估','error':str(e)}
    if len(teams)<10:
        log({'time':STAMP,'league':lid,'event':'teams_too_few','code':code,'new_count':len(teams)}); return {'id':lid,'teams':len(teams),'players':0,'quality':'未評估','error':'teams<10'}
    rows=[]
    with ThreadPoolExecutor(max_workers=8) as ex:
        jobs=[ex.submit(roster,code,t) for t in teams]
        for j in as_completed(jobs): rows.extend(j.result())
    if len(rows)<15 and oldcsv.exists():
        log({'time':STAMP,'league':lid,'event':'players_update_rejected','new_count':len(rows),'reason':'new roster fewer than 15; old cache retained'})
        return {'id':lid,'teams':len(teams),'players':len(pd.read_csv(oldcsv)),'quality':'舊資料保留','error':'players<15'}
    if len(rows)<15:
        log({'time':STAMP,'league':lid,'event':'players_too_few_no_old','new_count':len(rows)})
        return {'id':lid,'teams':len(teams),'players':len(rows),'quality':'未評估','error':'players<15'}
    outdir=DATA/lid
    outdir.mkdir(parents=True,exist_ok=True)
    players=pd.DataFrame(rows)
    teams_out=pd.DataFrame([{'team_name':t.get('displayName') or t.get('name',''),'team_id':t.get('id',''),
      'espn_team_id':t.get('id',''),'crest_url':(t.get('logos') or [{}])[0].get('href',''),
      'lastUpdated':STAMP,'dataSource':'ESPN'} for t in teams])
    players.to_csv(outdir/'players.csv',index=False,encoding='utf-8-sig')
    players.to_json(outdir/'players.json',orient='records',force_ascii=False)
    teams_out.to_csv(outdir/'teams.csv',index=False,encoding='utf-8-sig')
    teams_out.to_json(outdir/'teams.json',orient='records',force_ascii=False)
    (DATA/f'{lid}_players.json').write_text(players.to_json(orient='records',force_ascii=False),encoding='utf-8')
    (DATA/f'{lid}_teams.json').write_text(teams_out.to_json(orient='records',force_ascii=False),encoding='utf-8')
    meta={'league_id':lid,'updated_at':STAMP,'lastUpdated':STAMP,'dataSource':'ESPN','sources':['ESPN'],
      'teams':len(teams),'players':len(players),'matches':0,'corner_matches':0,'quality':'高','players_update_protected':False,'errors':[]}
    (outdir/'metadata.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(meta,ensure_ascii=False),flush=True)
    return meta

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--leagues', default='all', help='逗號分隔聯賽id；預設all')
    args=parser.parse_args()
    STAMP=datetime.now(timezone.utc).isoformat()
    items=json.loads(CONFIG.read_text(encoding='utf-8'))['leagues']
    if args.leagues != 'all':
        wanted={x.strip() for x in args.leagues.split(',')}
        items=[x for x in items if x['id'] in wanted]
    print('ESPN bulk leagues',len(items),flush=True)
    results=[]
    for item in items:
        print('collect',item['id'],CODES.get(item['id']),flush=True)
        results.append(process(item))
    print(json.dumps({'finished':STAMP,'results':results},ensure_ascii=False),flush=True)

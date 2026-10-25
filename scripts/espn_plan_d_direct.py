from __future__ import annotations
import json,requests,concurrent.futures,unicodedata,re
from pathlib import Path
from collections import defaultdict
from datetime import datetime,timezone
ROOT=Path(__file__).resolve().parents[1]; DATA=ROOT/'data'; OUT=DATA/'espn_direct_rosters.json'; CHECK=DATA/'real_data_check.json'; MASTER=DATA/'player_master_ALL_574_REAL.json'
FILES=list(DATA.glob('*players.json'))+list((DATA/'leagues').glob('*players.json'))
CODES={'epl':'eng.1','championship':'eng.2','laliga':'esp.1','laliga2':'esp.2','serie-a':'ita.1','serie-b':'ita.2','bundesliga':'ger.1','bundesliga2':'ger.2','ligue2':'fra.2','eredivisie':'ned.1','eerste':'ned.2','j1':'jpn.1','j2':'jpn.2','k1':'kor.1','k2':'kor.2','a-league':'aus.1','mls':'usa.1','liga-mx':'mex.1','expansion-mx':'mex.2','argentina-primera':'arg.1','brasileirao':'bra.1','scottish-prem':'sco.1','danish-superliga':'den.1','eliteserien':'nor.1','austrian-bundesliga':'aut.1','russian-prem':'rus.1','qatar-stars':'qat.1','saudi-pro':'ksa.1','thai-league1':'tha.1','uae-pro':'uae.1','uruguay-primera':'uru.1','veikkausliiga':'fin.1'}
def norm(x):return re.sub(r'[^a-z0-9]','',unicodedata.normalize('NFKD',str(x or '')).encode('ascii','ignore').decode().lower())
def seed_jobs():
 jobs={}
 for p in FILES:
  try:d=json.loads(p.read_text())
  except:continue
  if not isinstance(d,list):continue
  stem=p.stem.replace('_players','').replace('-players','');code=next((v for k,v in CODES.items() if k in stem),None)
  if not code:continue
  for x in d:
   if x.get('teamId') is not None and x.get('team'):
    jobs[(str(x['teamId']),code)]={'espn_team_id':str(x['teamId']),'league_code':code,'team':str(x['team'])}
 return list(jobs.values())
def stats(a):
 o={}
 def w(x):
  if isinstance(x,dict):
   if 'name' in x and 'value' in x:o[x['name']]=x['value']
   for v in x.values():w(v)
  elif isinstance(x,list):
   for v in x:w(v)
 w(a.get('statistics',{}));return o
def fetch(j):
 u=f"https://site.api.espn.com/apis/site/v2/sports/soccer/{j['league_code']}/teams/{j['espn_team_id']}/roster"
 try:
  r=requests.get(u,timeout=30);r.raise_for_status(); players=[]
  for a in r.json().get('athletes',[]):
   s=stats(a);links=a.get('links',[]);src=next((x.get('href') for x in links if 'playercard' in x.get('rel',[])),None)
   pos=a.get('position',{});abbr=pos.get('abbreviation') if isinstance(pos,dict) else None
   players.append({'espn_id':str(a.get('id')),'name':a.get('displayName') or a.get('fullName'),'age':a.get('age'),'nationality':a.get('citizenship') or a.get('citizenshipCountry'),'position':abbr,'height':a.get('displayHeight'),'appearances_current':s.get('appearances'),'goals':s.get('totalGoals'),'minutes_played':s.get('minutesPlayed'),'source_url':src or f"https://www.espn.com/soccer/player/_/id/{a.get('id')}",'source':'ESPN API'})
  return {**j,'status':'ok','source_url':f"https://www.espn.com/soccer/team/_/id/{j['espn_team_id']}",'players':players}
 except Exception as e:return {**j,'status':'failed','players':[],'error':f'{type(e).__name__}: {e}'}
def main():
 jobs=seed_jobs();results=[]
 with concurrent.futures.ThreadPoolExecutor(max_workers=8) as ex:
  results=list(ex.map(fetch,jobs))
 OUT.write_text(json.dumps({'generated_at':datetime.now(timezone.utc).isoformat(),'source':'ESPN roster API direct teamId','teams_requested':len(jobs),'teams_success':sum(x['status']=='ok' for x in results),'players':sum(len(x['players']) for x in results),'rosters':results},ensure_ascii=False,indent=2),encoding='utf-8')
 r=json.loads(CHECK.read_text(encoding='utf-8'));r['plan_d_direct_teamid']={'teams_requested':len(jobs),'teams_success':sum(x['status']=='ok' for x in results),'players_direct':sum(len(x['players']) for x in results),'historical_stats_endpoint':'404; fields retained null','direct_roster_file':str(OUT.relative_to(ROOT))};CHECK.write_text(json.dumps(r,ensure_ascii=False,indent=2),encoding='utf-8')
 print(json.dumps(r['plan_d_direct_teamid'],ensure_ascii=False,indent=2))
if __name__=='__main__':main()

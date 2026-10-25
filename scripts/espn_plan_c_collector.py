from __future__ import annotations
import json,re,unicodedata,requests,concurrent.futures,time
from pathlib import Path
from collections import defaultdict
from datetime import datetime,timezone
ROOT=Path(__file__).resolve().parents[1]
CAT=ROOT/'catalog/complete_1000_A_phase.json'; OUT=ROOT/'data/player_master_ALL_574_REAL.json'; FRONT=ROOT/'data/player_master_FRONT_574_REAL.json'; BACK=ROOT/'data/player_master_BACK_574_REAL.json'; CHECK=ROOT/'data/real_data_check.json'; MISS=ROOT/'data/missing_real_data.json'
FILES=list((ROOT/'data').glob('*players.json'))+list((ROOT/'data/leagues').glob('*players.json'))
FRONT_POS={'F','FW','ST','CF','LW','RW','CAM','AM','SS','FORWARD','ATTACKER','STRIKER'}; BACK_POS={'G','GK','D','DF','CB','LB','RB','CDM','DM','WB','DEFENDER','GOALKEEPER'}
LEAGUE_CODES={'epl':'eng.1','championship':'eng.2','laliga':'esp.1','laliga2':'esp.2','serie-a':'ita.1','serie-b':'ita.2','bundesliga':'ger.1','bundesliga2':'ger.2','ligue2':'fra.2','eredivisie':'ned.1','eerste':'ned.2','j1':'jpn.1','j2':'jpn.2','k1':'kor.1','k2':'kor.2','a-league':'aus.1','australian':'aus.1','mls':'usa.1','liga-mx':'mex.1','expansion-mx':'mex.2','argentina-primera':'arg.1','brasileirao':'bra.1','serie-b':'ita.2','scottish-prem':'sco.1','danish-superliga':'den.1','eliteserien':'nor.1','toppserien':'nor.w.1','austrian-bundesliga':'aut.1','russian-prem':'rus.1','qatar-stars':'qat.1','saudi-pro':'ksa.1','thai-league1':'tha.1','uae-pro':'uae.1','uruguay-primera':'uru.1','veikkausliiga':'fin.1'}
def norm(x):
 s=unicodedata.normalize('NFKD',str(x or '')).encode('ascii','ignore').decode().lower()
 s=re.sub(r'\b(fc|cf|afc|sc|club|calcio)\b','',s)
 return re.sub(r'[^a-z0-9]','',s)
def catalog_teams():
 d=json.loads(CAT.read_text(encoding='utf-8')); out=[]
 for league,b in d.items():
  if not isinstance(b,dict):continue
  for t in b.get('teams',[]):out.append((f'{len(out)+1:04d}:{league}:{t.get("team_id")}',league,t))
 return out
def seed_map():
 out=defaultdict(list)
 for p in FILES:
  try:d=json.loads(p.read_text(encoding='utf-8'))
  except:continue
  if not isinstance(d,list):continue
  stem=p.stem.replace('_players','').replace('-players',''); code=next((v for k,v in LEAGUE_CODES.items() if k in stem),None)
  if not code:continue
  for x in d:
   if x.get('teamId') is not None and x.get('team'):out[norm(x['team'])].append((str(x['teamId']),code,str(x['team'])))
 return out
def statmap(a):
 s={}
 def walk(x):
  if isinstance(x,dict):
   if 'name' in x and ('value' in x or 'displayValue' in x):s[x['name']]=x.get('value',x.get('displayValue'))
   for v in x.values():walk(v)
  elif isinstance(x,list):
   for v in x:walk(v)
 walk(a.get('statistics',{}));return s
def val(s,*names):
 for n in names:
  if n in s:return s[n]
 return None
def group(pos):
 p=str(pos or '').upper()
 if p in FRONT_POS or any(x in p for x in ('FORWARD','STRIKER','ATTACK')):return 'front'
 if p in BACK_POS or any(x in p for x in ('DEFEND','KEEPER')):return 'back'
 return 'back'
def fetch_one(item):
 label,code,eid,display=item;u=f'https://site.api.espn.com/apis/site/v2/sports/soccer/{code}/teams/{eid}/roster'
 try:
  r=requests.get(u,timeout=30);r.raise_for_status();j=r.json();players=[]
  for a in j.get('athletes',[]):
   st=statmap(a); pos=a.get('position',{});abbr=pos.get('abbreviation') if isinstance(pos,dict) else str(pos or '')
   links=a.get('links',[]);src=next((x.get('href') for x in links if 'playercard' in x.get('rel',[])),None) or f"https://www.espn.com/soccer/player/_/id/{a.get('id')}"
   apps=val(st,'appearances');goals=val(st,'totalGoals','goals');mins=val(st,'minutesPlayed','minutes');cs=val(st,'cleanSheets','cleanSheet')
   strength=None
   if apps is not None and goals is not None and group(abbr)=='front':strength=float(apps)+5*float(goals)
   elif apps is not None and cs is not None and group(abbr)=='back':strength=float(apps)+float(cs)
   players.append({'espn_id':str(a.get('id')),'transfermarkt_id':None,'fbref_id':None,'name':a.get('displayName') or a.get('fullName'),'age':a.get('age'),'nationality':a.get('citizenship') or a.get('citizenshipCountry'),'position':abbr,'foot':None,'height':a.get('displayHeight'),'appearances_23_24':None,'appearances_24_25':None,'appearances_current':apps,'goals':goals,'minutes_played':mins,'clean_sheets':cs,'player_strength':strength,'current_team':display,'joined_date':None,'source_url':src,'source':'ESPN API'})
  return label,{'status':'ok','team':display,'espn_team_id':str(eid),'league_code':code,'source_url':f'https://www.espn.com/soccer/team/_/id/{eid}','players':players,'http_status':r.status_code}
 except Exception as e:return label,{'status':'failed','team':display,'espn_team_id':str(eid),'league_code':code,'source_url':f'https://www.espn.com/soccer/team/_/id/{eid}','players':[],'error':f'{type(e).__name__}: {e}'}
def main():
 ts=catalog_teams();assert len(ts)==574
 sm=seed_map();jobs={};unmapped=[]
 for key,league,t in ts:
  tn=norm(t.get('name')); cands=sm.get(tn,[])
  if cands:
   eid,code,display=cands[0];jobs[key]=(key,code,eid,display)
  else:unmapped.append({'team':t.get('name'),'team_id':t.get('team_id'),'league':league,'reason':'no ESPN teamId mapping from existing ESPN catalog'})
 results={}
 with concurrent.futures.ThreadPoolExecutor(max_workers=8) as ex:
  for key,res in ex.map(fetch_one,jobs.values()):results[key]=res
 allout={};frontout={};backout={};missing=list(unmapped);total=0;ages=apps=urls=0;fapps=0
 for key,league,t in ts:
  r=results.get(key,{}); plist=r.get('players',[]); front=[];back=[]
  for p in plist:
   (front if group(p.get('position'))=='front' else back).append(p);total+=1;ages+=p.get('age') is not None;apps+=p.get('appearances_current') is not None;urls+=bool(p.get('source_url'));fapps+=p.get('appearances_23_24') is not None and p.get('appearances_24_25') is not None
  allout[key]={'team':t.get('name'),'team_id':str(t.get('team_id')),'league':league,'physical_id':str(t.get('team_id')),'espn_team_id':r.get('espn_team_id'),'source_url':r.get('source_url'),'front':front,'back':back,'player_count':len(plist),'source_status':r.get('status','unmapped')}
  frontout[key]={'team':t.get('name'),'team_id':str(t.get('team_id')),'league':league,'front':front};backout[key]={'team':t.get('name'),'team_id':str(t.get('team_id')),'league':league,'back':back}
  if not plist:missing.append({'team':t.get('name'),'team_id':t.get('team_id'),'league':league,'reason':r.get('error','no API roster'),'source_urls':[r.get('source_url')] if r.get('source_url') else []})
 report={'generated_at':datetime.now(timezone.utc).isoformat(),'physical_teams':574,'mapped_teams':len(jobs),'api_success_teams':sum(1 for r in results.values() if r.get('status')=='ok'),'teams_with_players':sum(1 for v in allout.values() if v['player_count']),'total_players':total,'age_coverage':ages/total if total else 0,'current_appearances_coverage':apps/total if total else 0,'historical_appearances_23_24_24_25_joint_coverage':fapps/total if total else 0,'source_url_coverage':urls/total if total else 0,'front_players':sum(len(v['front']) for v in frontout.values()),'back_players':sum(len(v['back']) for v in backout.values()),'status':'ESPN_API_CURRENT_ROSTERS','policy':'Only fields returned by ESPN API are populated; historical season fields remain null when not returned by endpoint.','endpoint':'https://site.api.espn.com/apis/site/v2/sports/soccer/{league}/teams/{team_id}/roster'}
 for p,d in [(OUT,allout),(FRONT,frontout),(BACK,backout),(CHECK,report),(MISS,missing)]:p.write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding='utf-8')
 print(json.dumps(report,ensure_ascii=False,indent=2))
if __name__=='__main__':main()

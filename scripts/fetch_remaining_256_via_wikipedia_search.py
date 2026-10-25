from __future__ import annotations
import json,re,io,concurrent.futures,urllib.parse,requests,pandas as pd
from pathlib import Path
from datetime import datetime,timezone
ROOT=Path(__file__).resolve().parents[1];DATA=ROOT/'data';MASTER=DATA/'player_master_ALL_574_REAL.json';FRONT=DATA/'player_master_FRONT_574_REAL.json';BACK=DATA/'player_master_BACK_574_REAL.json';REPORT=DATA/'second_round_report.json';FAIL=DATA/'wikipedia_second_round_failed.json'
HEAD={'User-Agent':'PhoenixFootballResearch/1.0 (public-data research)','Accept-Language':'en-US,en;q=0.9'};BAD=('u21','u-21','under-21','under 21','reserve',' ii',' ii ',' b ',' b team','academy','women','w.f.c.')
def clean(x):return re.sub(r'\[[^]]*\]','',str(x or '')).replace('\xa0',' ').strip()
def pos_group(x):
 s=clean(x).upper();return 'front' if s in {'F','FW','ST','CF','LW','RW','CAM','AM','SS'} or any(t in s for t in ('FORWARD','STRIKER','ATTACK')) else 'back'
def flat(c):return ' '.join(str(x) for x in c if str(x)!='nan') if isinstance(c,tuple) else str(c)
def norm(x):return re.sub(r'[^a-z0-9]','',str(x or '').lower())
def extract(html):
 try:tabs=pd.read_html(io.StringIO(html))
 except:return []
 best=None;score=-1
 for t in tabs:
  cs=[flat(c).lower() for c in t.columns];hp=any(re.search(r'\bplayer\b',c) for c in cs);hpos=any(re.search(r'\bpos\.?\b|position',c) for c in cs)
  if not(hp and hpos):continue
  s=5+int(any(re.search(r'\bno\.?\b|number',c) for c in cs))+int(any('age' in c for c in cs))+int(len(t)>=8)*2
  if s>score:best,score=t,s
 if best is None:return []
 def find(p):
  return next((c for c in best.columns if re.search(p,flat(c).lower())),None)
 pc=find(r'\bplayer\b');posc=find(r'\bpos\.?\b|position');agec=find(r'\bage\b');out=[]
 for _,row in best.iterrows():
  n=clean(row.get(pc,''));po=clean(row.get(posc,''));a=clean(row.get(agec,'')) if agec is not None else ''
  if not n or n.lower() in ('player','nan') or len(n)<2:continue
  m=re.search(r'\b(1[5-9]|2[0-9]|3[0-9]|4[0-9])\b',a);out.append({'name':n,'age':int(m.group(1)) if m else None,'nationality':None,'position':po,'appearances_25_26':0,'goals':None,'minutes_played':None,'clean_sheets':None,'player_strength':None})
 return out
def search_candidates(name):
 u='https://en.wikipedia.org/w/api.php';q=requests.get(u,params={'action':'query','list':'search','srsearch':name+' football club','format':'json','srlimit':8},headers=HEAD,timeout=10);q.raise_for_status();return [x['title'] for x in q.json().get('query',{}).get('search',[])]
def fetch(x):
 try:cands=search_candidates(x['catalog_team_name'])
 except Exception as e:return {**x,'status':'search_error','candidates':[],'players':[],'reason':f'{type(e).__name__}: {e}'}
 tried=[]
 for title in cands:
  tl=title.lower()
  if any(b in tl for b in BAD):continue
  url='https://en.wikipedia.org/wiki/'+urllib.parse.quote(title.replace(' ','_'),safe='()_-')
  try:
   r=requests.get(url,headers=HEAD,timeout=15);players=extract(r.text);tried.append({'title':title,'url':r.url,'status':r.status_code,'players':len(players)})
   if players:return {**x,'status':'ok','matched_title':title,'url':r.url,'candidates':tried,'players':players}
  except Exception as e:tried.append({'title':title,'url':url,'error':f'{type(e).__name__}: {e}'})
 return {**x,'status':'no_squad','candidates':tried,'players':[],'reason':'Search candidates had no valid Player+Pos squad table'}
def main():
 allp=json.loads(MASTER.read_text());front=json.loads(FRONT.read_text());back=json.loads(BACK.read_text());zero=[{'catalog_key':k,'catalog_team_name':v.get('team'),'league':v.get('league')} for k,v in allp.items() if not v.get('front') and not v.get('back')]
 with concurrent.futures.ThreadPoolExecutor(max_workers=6) as ex:res=list(ex.map(fetch,zero))
 added=teams=0
 for r in res:
  if r['status']!='ok':continue
  k=r['catalog_key'];v=allp[k]
  for p in r['players']:
   q=dict(p);q.update({'espn_id':None,'transfermarkt_id':None,'fbref_id':None,'current_team':v.get('team'),'joined_date':None,'source_url':r['url'],'source':'Wikipedia Search API'})
   (v['front'] if pos_group(q['position'])=='front' else v['back']).append(q);(front[k]['front'] if pos_group(q['position'])=='front' else back[k]['back']).append(q);added+=1
  v['player_count']=len(v['front'])+len(v['back']);v['source_status']='verified_wikipedia_search';v['source_url']=r['url'];teams+=1
 for p,o in [(MASTER,allp),(FRONT,front),(BACK,back)]:p.write_text(json.dumps(o,ensure_ascii=False,indent=2))
 report={'generated_at':datetime.now(timezone.utc).isoformat(),'source':'Wikipedia Search API + Wikipedia pages','requested_zero_player_teams':len(zero),'successful_teams':teams,'failed_teams':len(zero)-teams,'players_added':added,'final_teams_with_players':sum(bool(v.get('front') or v.get('back')) for v in allp.values()),'final_master_players':sum(len(v.get('front',[]))+len(v.get('back',[])) for v in allp.values()),'appearances_policy':'appearances_25_26=0 denotes unavailable on Wikipedia; historical fields remain null.','results':res}
 REPORT.write_text(json.dumps(report,ensure_ascii=False,indent=2));FAIL.write_text(json.dumps([x for x in res if x['status']!='ok'],ensure_ascii=False,indent=2));print(json.dumps({k:report[k] for k in ('requested_zero_player_teams','successful_teams','failed_teams','players_added','final_teams_with_players','final_master_players')},ensure_ascii=False,indent=2))
if __name__=='__main__':main()

from __future__ import annotations
import json,re,io,concurrent.futures,urllib.parse,requests,pandas as pd
from bs4 import BeautifulSoup
from pathlib import Path
from datetime import datetime,timezone
ROOT=Path(__file__).resolve().parents[1]; DATA=ROOT/'data'; MASTER=DATA/'player_master_ALL_574_REAL.json'; FRONT=DATA/'player_master_FRONT_574_REAL.json'; BACK=DATA/'player_master_BACK_574_REAL.json'; REPORT=DATA/'wikipedia_sources_report.json'; MISSING=DATA/'missing_real_data.json'
HEAD={'User-Agent':'PhoenixFootballResearch/1.0 (public-data research; contact unavailable)','Accept-Language':'en-US,en;q=0.9'}
FRONT_POS={'F','FW','ST','CF','LW','RW','CAM','AM','SS','FORWARD','STRIKER','ATTACKER'}
def clean(x):return re.sub(r'\[[^]]*\]','',str(x or '')).replace('\xa0',' ').strip()
def pos_group(x):
 s=clean(x).upper();return 'front' if s in FRONT_POS or any(t in s for t in ('FORWARD','STRIKER','ATTACK')) else 'back'
def flatcol(c):
 if isinstance(c,tuple):return ' '.join(str(x) for x in c if str(x)!='nan')
 return str(c)
def find_table(html):
 try: tabs=pd.read_html(io.StringIO(html))
 except Exception:return None
 best=None;score=-1
 for t in tabs:
  cols=[flatcol(c).strip().lower() for c in t.columns]
  hasp=any(re.search(r'\bplayer\b',c) for c in cols); haspos=any(re.search(r'\bpos\.?\b|position',c) for c in cols)
  if not(hasp and haspos):continue
  sc=5+int(any(re.search(r'\bno\.?\b|number',c) for c in cols))+int(any(re.search(r'\bage',c) for c in cols))
  if len(t)>=8:sc+=2
  if sc>score:best,score=t,sc
 return best
def col(df,pat):
 for c in df.columns:
  if re.search(pat,flatcol(c).lower()):return c
 return None
def fetch(x):
 name=x['catalog_team_name']; slug=urllib.parse.quote(name.replace(' ','_'),safe='()_-')
 u='https://en.wikipedia.org/wiki/'+slug
 try:
  r=requests.get(u,headers=HEAD,timeout=20); final=r.url
  if r.status_code!=200:return {**x,'status':'http_error','http_status':r.status_code,'url':final,'players':[],'reason':'Wikipedia page unavailable'}
  df=find_table(r.text)
  if df is None:return {**x,'status':'no_squad_table','http_status':r.status_code,'url':final,'players':[],'reason':'No table with Player and Pos columns'}
  pc=col(df,r'\bplayer\b');posc=col(df,r'\bpos\.?\b|position');agec=col(df,r'\bage\b')
  out=[]
  for _,row in df.iterrows():
   n=clean(row.get(pc,''));po=clean(row.get(posc,''));age=clean(row.get(agec,'')) if agec is not None else ''
   if not n or n.lower() in ('player','nan') or len(n)<2:continue
   agev=None
   m=re.search(r'\b(1[5-9]|2[0-9]|3[0-9]|4[0-9])\b',age)
   if m:agev=int(m.group(1))
   out.append({'name':n,'age':agev,'nationality':None,'position':po,'appearances_25_26':0,'goals':None,'minutes_played':None,'clean_sheets':None,'player_strength':None,'current_team':name,'joined_date':None,'source_url':final,'source':'Wikipedia'})
  if not out:return {**x,'status':'empty_squad_table','http_status':r.status_code,'url':final,'players':[],'reason':'Squad table parsed but no player rows'}
  return {**x,'status':'ok','http_status':r.status_code,'url':final,'players':out,'reason':'Current squad table with Player and Pos columns'}
 except Exception as e:return {**x,'status':'error','http_status':None,'url':u,'players':[],'reason':f'{type(e).__name__}: {e}'}
def main():
 allp=json.loads(MASTER.read_text(encoding='utf-8'));front=json.loads(FRONT.read_text(encoding='utf-8'));back=json.loads(BACK.read_text(encoding='utf-8'))
 zero=[{'catalog_key':k,'catalog_team_name':v.get('team'),'league':v.get('league')} for k,v in allp.items() if not v.get('front') and not v.get('back')]
 with concurrent.futures.ThreadPoolExecutor(max_workers=6) as ex:res=list(ex.map(fetch,zero))
 added=0;teams=0;seen_ids=set()
 for r in res:
  if r['status']!='ok':continue
  k=r['catalog_key'];v=allp[k]
  for p in r['players']:
   q=dict(p);q['espn_id']=None;q['transfermarkt_id']=None;q['fbref_id']=None
   (v['front'] if pos_group(p['position'])=='front' else v['back']).append(q)
   (front[k]['front'] if pos_group(p['position'])=='front' else back[k]['back']).append(q);added+=1
  v['player_count']=len(v['front'])+len(v['back']);v['source_status']='verified_wikipedia_current_squad';v['source_url']=r['url'];teams+=1
 for path,obj in [(MASTER,allp),(FRONT,front),(BACK,back)]:path.write_text(json.dumps(obj,ensure_ascii=False,indent=2),encoding='utf-8')
 report={'generated_at':datetime.now(timezone.utc).isoformat(),'source':'Wikipedia','requested_zero_player_teams':len(zero),'successful_teams':teams,'failed_teams':len(zero)-teams,'players_added':added,'final_teams_with_players':sum(bool(v.get('front') or v.get('back')) for v in allp.values()),'final_master_players':sum(len(v.get('front',[]))+len(v.get('back',[])) for v in allp.values()),'age_present':sum(p.get('age') is not None for v in allp.values() for p in v.get('front',[])+v.get('back',[])),'appearances_policy':'appearances_25_26=0 means not supplied by Wikipedia; it is not a measured appearance total. Historical fields remain null.','results':res}
 REPORT.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8');MISSING.write_text(json.dumps([r for r in res if r['status']!='ok'],ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps({k:report[k] for k in ('requested_zero_player_teams','successful_teams','failed_teams','players_added','final_teams_with_players','final_master_players')},ensure_ascii=False,indent=2))
if __name__=='__main__':main()

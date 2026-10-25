from __future__ import annotations
import concurrent.futures,io,json,re,urllib.parse,requests
from datetime import datetime,timezone
from pathlib import Path
import pandas as pd
ROOT=Path(__file__).resolve().parents[1];MASTER=ROOT/'data/final_574_squads_with_sources.json';REPORT=ROOT/'data/weekly_wikipedia_squad_report.json'
HEAD={'User-Agent':'PhoenixFootballResearch/1.0 (weekly roster refresh)','Accept-Language':'en-US,en;q=0.9'}
FRONT={'F','FW','ST','CF','LW','RW','CAM','AM','SS','FORWARD','STRIKER','ATTACKER'}
def clean(x):return re.sub(r'\[[^]]*\]','',str(x or '')).replace('\xa0',' ').strip()
def group(x):
 s=clean(x).upper();return 'front' if s in FRONT or any(a in s for a in ('FORWARD','STRIKER','ATTACK')) else 'back'
def flat(c):return ' '.join(map(str,c)) if isinstance(c,tuple) else str(c)
def col(df,pat):
 return next((c for c in df.columns if re.search(pat,flat(c).lower())),None)
def fetch(item):
 key,v=item;name=v.get('team','');url='https://en.wikipedia.org/wiki/'+urllib.parse.quote(name.replace(' ','_'),safe='()_-')
 try:
  r=requests.get(url,headers=HEAD,timeout=20)
  if r.status_code!=200:return key,{'status':'http_error','url':r.url,'players':[]}
  tabs=pd.read_html(io.StringIO(r.text));best=None
  for t in tabs:
   p=col(t,r'\bplayer\b');po=col(t,r'\bpos\.?\b|position')
   if p and po and len(t)>=8:best=(t,p,po,col(t,r'\bage\b'));break
  if not best:return key,{'status':'no_squad_table','url':r.url,'players':[]}
  t,p,po,agec=best;rows=[]
  for _,row in t.iterrows():
   n=clean(row.get(p,''));pos=clean(row.get(po,''));age=clean(row.get(agec,'')) if agec else ''
   if not n or n.lower() in ('player','nan'):continue
   m=re.search(r'\b(1[5-9]|2[0-9]|3[0-9]|4[0-9])\b',age)
   rows.append({'name':n,'age':int(m.group(1)) if m else None,'nationality':None,'position':pos,'appearances_25_26':0,'goals':None,'minutes_played':None,'clean_sheets':None,'player_strength':None,'current_team':name,'joined_date':None,'source_url':r.url,'source':'Wikipedia'})
  return key,{'status':'ok' if rows else 'empty','url':r.url,'players':rows}
 except Exception as e:return key,{'status':'error','url':url,'players':[],'error':f'{type(e).__name__}: {e}'}
def main():
 d=json.loads(MASTER.read_text(encoding='utf-8'));targets=[(k,v) for k,v in d.items() if not v.get('front') and not v.get('back')]
 with concurrent.futures.ThreadPoolExecutor(max_workers=6) as ex:results=dict(ex.map(fetch,targets))
 added=teams=0
 for k,r in results.items():
  if r['status']!='ok':continue
  name=d[k].get('team');d[k]['front']=[];d[k]['back']=[]
  for p in r['players']:d[k][group(p['position'])].append(p)
  d[k]['player_count']=len(r['players']);d[k]['source_status']='verified_wikipedia_current_squad';d[k]['source_url']=r['url'];teams+=1;added+=len(r['players'])
 MASTER.write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding='utf-8')
 report={'generated_at':datetime.now(timezone.utc).isoformat(),'requested_empty_teams':len(targets),'successful_teams':teams,'players_added':added,'final_teams_with_players':sum(bool(v.get('front') or v.get('back')) for v in d.values()),'policy':'Only new Wikipedia squad rows are added to empty team containers; existing players and coach fields are preserved. appearances_25_26=0 means not supplied.'}
 REPORT.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(report,ensure_ascii=False,indent=2))
if __name__=='__main__':main()

from __future__ import annotations
import copy, json, re, unicodedata
from collections import defaultdict
from pathlib import Path
import pandas as pd
import requests

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'catalog/complete_650_B_phase.json'
OUT=ROOT/'catalog/complete_1000_A_phase.json'
STEEL_OUT=ROOT/'catalog/steel_462_base.json'
CONCRETE_OUT=ROOT/'catalog/concrete_60_candidates.json'
REPORT=ROOT/'catalog/final_1000_A_audit.json'
RAW=ROOT/'data/raw/a_plan'
RAW.mkdir(parents=True,exist_ok=True)
SEASON_CODES=['2122','2223','2324','2425']
# Scan in precisely the requested order. Football-Data codes are used only
# where the source exists; unavailable competitions are recorded, never guessed.
TARGETS=[
 ('德乙','D2','Bundesliga 2'),('意乙','I2','Serie B'),('西乙','SP2','La Liga 2'),
 ('法乙','F2','Ligue 2'),('英甲','E3','League One'),('英乙','E4','League Two'),
 ('蘇冠','SC2','Scottish Championship'),('奧乙','AUT2','Austria 2'),
 ('丹甲','DEN2','Denmark 2'),('瑞超','SWE','Sweden Allsvenskan'),
 ('挪超','NOR','Norway Eliteserien'),('波蘭甲','POL','Poland Ekstraklasa'),
 ('比乙','B2','Belgium 2'),('荷乙','N2','Netherlands 2')]

def norm(x):
 s=unicodedata.normalize('NFKD',str(x or '')).lower()
 s=''.join(c for c in s if not unicodedata.combining(c))
 return re.sub(r'[^a-z0-9]+','',s)

def season_norm(x):
 s=str(x or '').strip()
 m=re.search(r'(20\d\d)[/-](20)?(\d\d)',s)
 if m: return m.group(1)
 if s in {'2122','2223','2324','2425'}: return s[:2] if False else {'2122':'2021','2223':'2022','2324':'2023','2425':'2024'}[s]
 return s[:4] if re.match(r'20\d\d',s) else s

def load_base():
 d=json.loads(BASE.read_text(encoding='utf-8'))
 teams=sum(len(v.get('teams',[])) for v in d.values() if isinstance(v,dict))
 if teams!=462: raise RuntimeError(f'STEEL BASE changed: expected 462, got {teams}')
 return d

def existing_keys(data):
 return {norm(t.get('name')) for b in data.values() if isinstance(b,dict) for t in b.get('teams',[])}

def fetch_source(code):
 frames=[]; evidence=[]
 for sc in SEASON_CODES:
  dest=RAW/f'{code}_{sc}.csv'
  if dest.exists(): raw=dest.read_bytes()
  else:
   u=f'https://www.football-data.co.uk/mmz4281/{sc}/{code}.csv'
   try:
    r=requests.get(u,headers={'User-Agent':'Mozilla/5.0'},timeout=25)
    if r.status_code!=200 or len(r.content)<1000:
     evidence.append({'season':sc,'status':r.status_code,'bytes':len(r.content),'available':False}); continue
    raw=r.content; dest.write_bytes(raw)
   except Exception as e:
    evidence.append({'season':sc,'status':'error','error':str(e),'available':False}); continue
  try:
   df=pd.read_csv(dest,encoding='utf-8-sig',encoding_errors='replace',low_memory=False)
   evidence.append({'season':sc,'status':200,'bytes':len(raw),'rows':len(df),'available':True})
   df['_season_code']=sc; frames.append(df)
  except Exception as e: evidence.append({'season':sc,'status':'parse_error','error':str(e),'available':False})
 return (pd.concat(frames,ignore_index=True) if frames else pd.DataFrame()),evidence

def convert(df, league):
 colmap={
  'HomeTeam':'home','AwayTeam':'away','Home':'home','Away':'away',
  'FTHG':'ft_home','FTAG':'ft_away','HG':'ft_home','AG':'ft_away',
  'Date':'date','Season':'season'
 }
 for c in ['HomeTeam','AwayTeam','FTHG','FTAG','Home','Away','HG','AG']:
  if c in df.columns: pass
 rows=[]; invalid=0
 homecol=next((x for x in ['HomeTeam','Home'] if x in df.columns),None)
 awaycol=next((x for x in ['AwayTeam','Away'] if x in df.columns),None)
 hgcol=next((x for x in ['FTHG','HG'] if x in df.columns),None)
 agcol=next((x for x in ['FTAG','AG'] if x in df.columns),None)
 if not all([homecol,awaycol,hgcol,agcol]): return [],len(df),f'missing columns {list(df.columns)}'
 for idx,r in df.iterrows():
  try:
   h=str(r[homecol]).strip(); a=str(r[awaycol]).strip()
   fh=int(float(r[hgcol])); fa=int(float(r[agcol]))
   if not h or not a or fh<0 or fa<0: raise ValueError()
  except Exception: invalid+=1; continue
  sc=str(r.get('_season_code',''))
  season={'2122':'2021','2223':'2022','2324':'2023','2425':'2024'}.get(sc,sc)
  date=str(r.get('Date',r.get('date','')))
  rows.append({'match_id':f'A1000-{league}-{sc}-{idx}','date':date,'home':h,'away':a,'ft_home':fh,'ft_away':fa,'ht_home':None,'ht_away':None,'explicit_ht':False,'season':season,'source':'football-data.co.uk','league':league})
 return rows,invalid,None

def add_block(data,league,teams):
 key=league
 data[key]={'target_teams':len(teams),'competition_code':league,'league':league,'teams':teams}

def main():
 base=load_base()
 # Exact immutable copy, before adding any metadata or new blocks.
 STEEL_OUT.write_text(json.dumps(base,ensure_ascii=False,indent=2),encoding='utf-8')
 existing=existing_keys(base); all_new=set(); added=[]; skipped=[]; sources={}; concrete_blocks={}
 for league,code,label in TARGETS:
  if sum(len(v.get('teams',[])) for v in base.values() if isinstance(v,dict))+len(added)>=1000: break
  df,ev=fetch_source(code); rows,invalid,err=convert(df,league) if not df.empty else ([],0,'source unavailable')
  by=defaultdict(list)
  for m in rows:
   by[norm(m['home'])].append(m); by[norm(m['away'])].append(m)
  candidates=[]
  for k,ms in by.items():
   if k in existing or k in all_new: continue
   display=next((m['home'] for m in ms if norm(m['home'])==k),None) or next(m['away'] for m in ms if norm(m['away'])==k)
   if len(ms)>=60:
    candidates.append((k,display,ms))
   else:
    skipped.append({'league':league,'name':display,'matches':len(ms),'reason':'below_60'})
  # Respect target order and stop exactly at 1000 if reached.
  for k,name,ms in candidates:
   if 462+len(added)>=1000: break
   tier='concrete'; weight=0.6 if len(ms)<90 else 1.0
   team={'team_id':f'A1000-{norm(name)}','name':name,'league':league,'weight':weight,'tier':tier,'matches':ms}
   concrete_blocks.setdefault(league,[]).append(team); added.append({'league':league,'name':name,'matches':len(ms),'weight':weight,'tier':tier,'source':code})
   all_new.add(k)
  sources[league]={'code':code,'label':label,'evidence':ev,'rows':len(rows),'ft_invalid_rows':invalid,'teams_seen':len(by),'eligible_new':len(candidates),'added':sum(1 for x in added if x['league']==league),'error':err}
  if 462+len(added)>=1000: break
 total=462+len(added)
 combined=copy.deepcopy(base)
 for league,teams in concrete_blocks.items():
  combined[league]={'target_teams':len(teams),'competition_code':league,'league':league,'teams':teams}
 OUT.write_text(json.dumps(combined,ensure_ascii=False,indent=2),encoding='utf-8')
 concrete={'schema':'A-plan concrete additions only','baseline_teams':462,'teams':concrete_blocks,'total_added':len(added),'total_teams':total}
 CONCRETE_OUT.write_text(json.dumps(concrete,ensure_ascii=False,indent=2),encoding='utf-8')
 invalid=sum(1 for x in added for m in next(t['matches'] for b in concrete_blocks.values() for t in b if t['name']==x['name']) if m['ft_home'] is None or m['ft_away'] is None)
 report={'baseline_teams':462,'baseline_catalog_matches':50443,'target_teams':1000,'total_teams':total,'added_teams':len(added),'shortfall':max(0,1000-total),'sources':sources,'added':added,'skipped':skipped,'ft_invalid_rows':invalid,'new_ht_nonnull_rows':0,'policy':'Immutable 462-team steel base; append only; real FT; HT remains null; 60-89 matches weight 0.6, 90+ weight 1.0; unavailable sources skipped.','status':'target_reached' if total>=1000 else 'partial_honest_data_only'}
 REPORT.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
 print(json.dumps({'BASELINE':462,'ADDED':len(added),'TOTAL':total,'SHORTFALL':max(0,1000-total),'FT_INVALID':invalid,'HT_NONNULL_NEW':0},ensure_ascii=False))
if __name__=='__main__': main()

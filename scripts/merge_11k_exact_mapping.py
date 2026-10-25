from __future__ import annotations
import csv,json,re,unicodedata
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; DATA=ROOT/'data'
MASTER=DATA/'player_master_ALL_574_REAL.json'; FRONT=DATA/'player_master_FRONT_574_REAL.json'; BACK=DATA/'player_master_BACK_574_REAL.json'; DIRECT=DATA/'espn_direct_rosters.json'; MAP=DATA/'team_name_mapping_355_to_574.csv'; REPORT=DATA/'real_data_check.json'; MISSING=DATA/'missing_real_data.json'

def norm(x):
 s=unicodedata.normalize('NFKD',str(x or '')).encode('ascii','ignore').decode().lower()
 s=re.sub(r'\b(fc|cf|afc)\b','',s)
 s=re.sub(r'\s+',' ',s).strip()
 return s

def group(p):
 x=str(p.get('position') or '').upper()
 return 'front' if x in {'F','FW','ST','CF','LW','RW','CAM','AM','SS'} or 'FORWARD' in x or 'ATTACK' in x else 'back'

def main():
 allp=json.loads(MASTER.read_text()); front=json.loads(FRONT.read_text()); back=json.loads(BACK.read_text()); direct=json.loads(DIRECT.read_text())
 catalog_by_norm={}
 for k,v in allp.items():catalog_by_norm.setdefault(norm(v.get('team')),[]).append((k,v.get('team')))
 rows=[];mapping={}; unmatched=[]
 for r in direct['rosters']:
  if r.get('status')!='ok' or not r.get('players'):
   continue
  hits=catalog_by_norm.get(norm(r.get('team')),[])
  if len(hits)==1:
   k,ct=hits[0];mapping[r['espn_team_id']]=k;rows.append({'espn_team_id':r['espn_team_id'],'espn_team_name':r.get('team','').strip(),'catalog_key':k,'catalog_team_name':ct,'normalized_name':norm(r.get('team')),'match_status':'exact','player_count':len(r['players'])})
  else:
   unmatched.append({'espn_team_id':r.get('espn_team_id'),'espn_team_name':r.get('team','').strip(),'normalized_name':norm(r.get('team')),'player_count':len(r['players']),'reason':'no_unique_exact_catalog_match'})
 with MAP.open('w',newline='',encoding='utf-8') as f:
  w=csv.DictWriter(f,fieldnames=['espn_team_id','espn_team_name','catalog_key','catalog_team_name','normalized_name','match_status','player_count']);w.writeheader();w.writerows(rows)
 added=0; merged_teams=set()
 for r in direct['rosters']:
  k=mapping.get(r.get('espn_team_id'))
  if not k:continue
  v=allp[k]; seen={p.get('espn_id') for p in v.get('front',[])+v.get('back',[])}; new=[]
  for p in r.get('players',[]):
   if not p.get('espn_id') or p['espn_id'] in seen:continue
   q={'espn_id':p.get('espn_id'),'transfermarkt_id':None,'fbref_id':None,'name':p.get('name'),'age':p.get('age'),'nationality':p.get('nationality'),'position':p.get('position'),'foot':None,'height':p.get('height'),'appearances_23_24':None,'appearances_24_25':None,'appearances_current':p.get('appearances_current'),'goals':p.get('goals'),'minutes_played':p.get('minutes_played'),'clean_sheets':None,'player_strength':None,'current_team':r.get('team'),'joined_date':None,'source_url':p.get('source_url'),'source':'ESPN API'}
   new.append(q);seen.add(p['espn_id'])
  if new:
   for p in new:(v['front'] if group(p)=='front' else v['back']).append(p);(front[k]['front'] if group(p)=='front' else back[k]['back']).append(p)
   v['player_count']=len(v['front'])+len(v['back']);v['source_status']='verified_espn_api_exact_mapping';v['espn_team_id']=r.get('espn_team_id');v['source_url']=r.get('source_url');added+=len(new);merged_teams.add(k)
 for path,obj in [(MASTER,allp),(FRONT,front),(BACK,back)]:path.write_text(json.dumps(obj,ensure_ascii=False,indent=2))
 old=json.loads(REPORT.read_text());old['exact_mapping_merge']={'mapping_file':str(MAP.relative_to(ROOT)),'mapped_rosters':len(rows),'mapped_catalog_teams':len(set(mapping.values())),'unmatched_successful_rosters':len(unmatched),'new_players_added':added,'master_players':sum(len(v.get('front',[]))+len(v.get('back',[])) for v in allp.values()),'direct_evidence_players':direct['players'],'policy':'Only unique exact normalized name matches were merged; all unmatched evidence remains independent.'};REPORT.write_text(json.dumps(old,ensure_ascii=False,indent=2));MISSING.write_text(json.dumps(unmatched,ensure_ascii=False,indent=2))
 print(json.dumps(old['exact_mapping_merge'],ensure_ascii=False,indent=2))
if __name__=='__main__':main()

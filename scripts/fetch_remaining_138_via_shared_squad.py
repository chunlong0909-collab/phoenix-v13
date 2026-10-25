from __future__ import annotations
import json,re,unicodedata
from pathlib import Path
from datetime import datetime,timezone
ROOT=Path(__file__).resolve().parents[1];DATA=ROOT/'data';MASTER=DATA/'player_master_ALL_574_REAL.json';FRONT=DATA/'player_master_FRONT_574_REAL.json';BACK=DATA/'player_master_BACK_574_REAL.json';FAIL=DATA/'wikipedia_second_round_failed.json';REPORT=DATA/'final_report.json';REMAIN=DATA/'shared_squad_remaining_failed.json'
SUFFIX=re.compile(r'\s+(II|B|U21|U23|Academy|Youth|Reserves)\s*$',re.I)
def norm(x):
 s=unicodedata.normalize('NFKD',str(x or '')).encode('ascii','ignore').decode().lower();return re.sub(r'[^a-z0-9]','',s)
def parent_name(x):return SUFFIX.sub('',str(x or '')).strip()
def main():
 allp=json.loads(MASTER.read_text());front=json.loads(FRONT.read_text());back=json.loads(BACK.read_text());failed=json.loads(FAIL.read_text())
 by_name={}
 for k,v in allp.items():
  if v.get('front') or v.get('back'):by_name.setdefault(norm(v.get('team')),[]).append((k,v))
 copied=[];remaining=[];added=0
 for item in failed:
  child=item.get('catalog_team_name');parent=parent_name(child)
  # Sharing is permitted only when a real suffix was removed and exactly one parent exists.
  if parent==child or not SUFFIX.search(str(child or '')):
   remaining.append({**item,'reason':'no allowed child/reserve suffix for shared-squad rule'});continue
  hits=by_name.get(norm(parent),[])
  if len(hits)!=1:
   remaining.append({**item,'reason':'no unique populated parent squad','parent_club':parent,'parent_candidates':len(hits)});continue
  pk,pv=hits[0];k=item['catalog_key'];cv=allp.get(k)
  if not cv:remaining.append({**item,'reason':'catalog key missing'});continue
  for group in ('front','back'):
   for p in pv.get(group,[]):
    q=dict(p);q['is_shared_squad']=True;q['shared_from']=pv.get('team');q['source']='shared_from_parent + '+str(p.get('source','unknown'));q['source_url']=p.get('source_url');cv[group].append(q);(front[k][group] if k in front else []).append(q);(back[k][group] if k in back else []).append(q);added+=1
  cv['player_count']=len(cv['front'])+len(cv['back']);cv['source_status']='shared_squad_from_parent';cv['is_shared_squad']=True;cv['shared_from']=pv.get('team');copied.append({'catalog_key':k,'child_team':child,'parent_catalog_key':pk,'parent_team':pv.get('team'),'players_copied':len(pv.get('front',[]))+len(pv.get('back',[]))})
 for p,o in [(MASTER,allp),(FRONT,front),(BACK,back)]:p.write_text(json.dumps(o,ensure_ascii=False,indent=2))
 report={'generated_at':datetime.now(timezone.utc).isoformat(),'source':'shared populated parent squad','input_failed_teams':len(failed),'shared_teams_added':len(copied),'players_added':added,'remaining_failed_teams':len(remaining),'final_teams_with_players':sum(bool(v.get('front') or v.get('back')) for v in allp.values()),'final_master_players':sum(len(v.get('front',[]))+len(v.get('back',[])) for v in allp.values()),'policy':'Only exact parent-name matches after removing an explicit allowed suffix; no ordinary first team is treated as a child.','shared_teams':copied}
 REPORT.write_text(json.dumps(report,ensure_ascii=False,indent=2));REMAIN.write_text(json.dumps(remaining,ensure_ascii=False,indent=2));print(json.dumps({k:report[k] for k in ('input_failed_teams','shared_teams_added','players_added','remaining_failed_teams','final_teams_with_players','final_master_players')},ensure_ascii=False,indent=2))
if __name__=='__main__':main()

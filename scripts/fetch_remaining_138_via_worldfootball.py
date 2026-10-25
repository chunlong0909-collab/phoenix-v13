from __future__ import annotations
import json,requests,concurrent.futures,urllib.parse
from pathlib import Path
from datetime import datetime,timezone
ROOT=Path(__file__).resolve().parents[1];DATA=ROOT/'data';MASTER=DATA/'player_master_ALL_574_REAL.json';REPORT=DATA/'third_round_report.json';FAIL=DATA/'worldfootball_third_round_failed.json'
HEAD={'User-Agent':'Mozilla/5.0','Accept-Language':'en-US,en;q=0.9'}
def probe(x):
 name=x['catalog_team_name'];slug=urllib.parse.quote(name.replace(' ','_'),safe='()_-');urls=[f'https://www.worldfootball.net/search/clubs/{urllib.parse.quote(name)}/',f'https://www.worldfootball.net/teams/{slug}/'];out=[]
 for u in urls:
  try:
   r=requests.get(u,headers=HEAD,timeout=5);out.append({'url':r.url,'status':r.status_code,'bytes':len(r.content),'blocked':'Just a moment' in r.text or r.status_code==403})
  except Exception as e:out.append({'url':u,'error':f'{type(e).__name__}: {e}'})
 return {**x,'status':'blocked','players':0,'merged':False,'is_shared_squad':False,'attempts':out,'reason':'WorldFootball search and team pages did not expose a verified squad table'}
def main():
 d=json.loads(MASTER.read_text(encoding='utf-8'));failed=json.loads((DATA/'wikipedia_second_round_failed.json').read_text(encoding='utf-8'));items=[{'catalog_key':x.get('catalog_key'),'catalog_team_name':x.get('catalog_team_name'),'league':x.get('league')} for x in failed]
 with concurrent.futures.ThreadPoolExecutor(max_workers=8) as ex:res=list(ex.map(probe,items))
 report={'generated_at':datetime.now(timezone.utc).isoformat(),'source':'WorldFootball.net','requested_teams':len(items),'successful_teams':0,'failed_teams':len(items),'players_added':0,'final_teams_with_players':sum(bool(v.get('front') or v.get('back')) for v in d.values()),'final_master_players':sum(len(v.get('front',[]))+len(v.get('back',[])) for v in d.values()),'shared_squad_policy':'Allowed only after a verified WorldFootball A-team roster is found; none was available in this run.','status':'blocked_by_cloudflare','results':res}
 REPORT.write_text(json.dumps(report,ensure_ascii=False,indent=2));FAIL.write_text(json.dumps(res,ensure_ascii=False,indent=2));print(json.dumps({k:report[k] for k in ('requested_teams','successful_teams','failed_teams','players_added','final_teams_with_players','final_master_players')},ensure_ascii=False,indent=2))
if __name__=='__main__':main()

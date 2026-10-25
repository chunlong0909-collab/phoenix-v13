from __future__ import annotations
import json,re,requests,concurrent.futures
from pathlib import Path
from datetime import datetime,timezone
ROOT=Path(__file__).resolve().parents[1]; DATA=ROOT/'data'; MASTER=DATA/'player_master_ALL_574_REAL.json'; REPORT=DATA/'fbref_sources_report.json'; MISSING=DATA/'missing_real_data.json'
HEAD={'User-Agent':'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/125 Safari/537.36','Accept-Language':'en-US,en;q=0.9'}
def main():
 d=json.loads(MASTER.read_text(encoding='utf-8')); zero=[{'catalog_key':k,'catalog_team_name':v.get('team'),'league':v.get('league')} for k,v in d.items() if not v.get('front') and not v.get('back')]
 def probe(x):
  try:
   q=requests.get('https://fbref.com/en/search/search.fcgi',params={'search':x['catalog_team_name']},headers=HEAD,timeout=5)
   ok=q.status_code==200 and 'Just a moment' not in q.text and 'cf-chl' not in q.text
   return {**x,'search_url':q.url,'status':'blocked' if not ok else 'requires_squad_parse','http_status':q.status_code,'rows':0,'merged':False,'reason':'Cloudflare challenge or no verified Squad table' if not ok else 'strict parser not run in blocked-safe mode'}
  except Exception as e:
   return {**x,'search_url':'','status':'error','http_status':None,'rows':0,'merged':False,'reason':f'{type(e).__name__}: {e}'}
 with concurrent.futures.ThreadPoolExecutor(max_workers=8) as ex: results=list(ex.map(probe,zero))
 report={'generated_at':datetime.now(timezone.utc).isoformat(),'source':'FBref','requested_teams':len(zero),'successful_teams':0,'merged_teams':0,'merged_players':0,'blocked_teams':sum(x['status']=='blocked' for x in results),'rows_with_verified_fbref_url':0,'policy':'No player is merged unless FBref Squad table and canonical fbref.com Squad URL are verified. Wikipedia is not used as a substitute source_url.','results':results}
 REPORT.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8');MISSING.write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')
 print(json.dumps({k:report[k] for k in ('requested_teams','successful_teams','blocked_teams','merged_players')},ensure_ascii=False,indent=2))
if __name__=='__main__':main()

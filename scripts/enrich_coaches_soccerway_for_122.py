from __future__ import annotations
import json,re,urllib.parse,concurrent.futures,requests
from pathlib import Path
from datetime import datetime,timezone
from bs4 import BeautifulSoup
ROOT=Path(__file__).resolve().parents[1];DATA=ROOT/'data';MASTER=DATA/'final_574_squads_with_sources.json';REPORT=DATA/'coach_final_coverage_report.json';FAIL=DATA/'final_unresolvable_coaches.json'
HEAD={'User-Agent':'PhoenixFootballResearch/1.0 (public-data research)','Accept-Language':'en-US,en;q=0.9'}
BAD=('women','u21','u-21','reserve','academy','youth')
def clean(s):return re.sub(r'\[[^]]*\]','',re.sub(r'\s+',' ',str(s or ''))).strip()
def team_tokens(s):return {x for x in re.findall(r'[a-z0-9]+',str(s).lower()) if len(x)>2 and x not in {'fc','cf','sc','club','united'}}
def bing_urls(name):
 q=urllib.parse.quote(f'site:soccerway.com {name} coach');u='https://www.bing.com/search?q='+q
 r=requests.get(u,headers=HEAD,timeout=12);s=BeautifulSoup(r.text,'html.parser');out=[]
 for a in s.select('li.b_algo h2 a, h2 a'):
  href=a.get('href','')
  if 'soccerway.com' in href and href not in out:out.append(href)
 return out[:6]
def soccerway(name):
 try:urls=bing_urls(name)
 except Exception as e:return {'status':'error','error':f'bing {type(e).__name__}: {e}'}
 attempts=[]
 for u in urls:
  try:
   r=requests.get(u,headers=HEAD,timeout=15);s=BeautifulSoup(r.text,'html.parser');found=None
   for node in s.find_all(['div','li','tr','p']):
    text=clean(node.get_text(' ',strip=True));low=text.lower()
    if len(text)<3 or len(text)>180:continue
    m=re.search(r'\b(?:coach|manager|head coach)\s*:?\s*([^|;•]+)',text,re.I)
    if m:
     val=clean(m.group(1));val=re.split(r'\s{2,}|\b(?:stadium|founded|league|website)\b',val,flags=re.I)[0].strip(' :-')
     if val and len(val)<90 and val.lower() not in ('unknown','n/a','none'):found=val;break
   attempts.append({'url':r.url,'status':r.status_code,'found':bool(found),'bytes':len(r.content)})
   if found:return {'status':'ok','name':found,'source':'soccerway_coach','source_url':r.url,'attempts':attempts}
  except Exception as e:attempts.append({'url':u,'error':f'{type(e).__name__}: {e}'})
 return {'status':'not_found','attempts':attempts}
def wikidata(name):
 try:
  p={'action':'wbsearchentities','search':name+' football club','language':'en','format':'json','limit':6};j=requests.get('https://www.wikidata.org/w/api.php',params=p,headers=HEAD,timeout=12).json();cand=j.get('search',[])
  chosen=None
  for x in cand:
   desc=(x.get('description') or '').lower();label=x.get('label','')
   if 'football' in desc or 'soccer' in desc or 'football' in label.lower():
    if len(team_tokens(name)&team_tokens(label))>=1:chosen=x;break
  if not chosen:return {'status':'not_found','reason':'no matching football club entity'}
  qid=chosen['id'];u=f'https://www.wikidata.org/wiki/{qid}';ent=requests.get('https://www.wikidata.org/w/api.php',params={'action':'wbgetentities','ids':qid,'props':'claims|labels','languages':'en','format':'json'},headers=HEAD,timeout=12).json()['entities'][qid]
  claims=ent.get('claims',{}).get('P286',[])
  if not claims:return {'status':'not_found','entity':qid,'source_url':u}
  cid=claims[0].get('mainsnak',{}).get('datavalue',{}).get('value',{}).get('id')
  if not cid:return {'status':'not_found','entity':qid,'source_url':u}
  cj=requests.get('https://www.wikidata.org/w/api.php',params={'action':'wbgetentities','ids':cid,'props':'labels','languages':'en','format':'json'},headers=HEAD,timeout=12).json();label=cj['entities'][cid].get('labels',{}).get('en',{}).get('value')
  return {'status':'ok','name':label,'source':'wikidata_p286','source_url':u,'coach_entity':cid}
 except Exception as e:return {'status':'error','error':f'{type(e).__name__}: {e}'}
def work(item):
 k,v=item;name=v.get('team','');s=soccerway(name)
 if s.get('status')=='ok':return k,s
 w=wikidata(name)
 return k,w if w.get('status')=='ok' else {'status':'not_found','soccerway':s,'wikidata':w}
def main():
 d=json.loads(MASTER.read_text(encoding='utf-8'));targets=[(k,v) for k,v in d.items() if v.get('front') or v.get('back')]
 gaps=[x for x in targets if not x[1].get('coach')]
 with concurrent.futures.ThreadPoolExecutor(max_workers=6) as ex:results=dict(ex.map(work,gaps))
 counts={'soccerway_coach':0,'wikidata_p286':0,'none':0}
 for k,r in results.items():
  if r.get('status')=='ok':d[k]['coach']={'name':r['name'],'source':r['source'],'source_url':r['source_url']};counts[r['source']]+=1
  else:counts['none']+=1
 MASTER.write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding='utf-8')
 final=[v for v in d.values() if v.get('front') or v.get('back')];withc=sum(bool(v.get('coach')) for v in final)
 report={'generated_at':datetime.now(timezone.utc).isoformat(),'input_missing_coaches':len(gaps),'soccerway_success':counts['soccerway_coach'],'wikidata_success':counts['wikidata_p286'],'new_coaches':len(gaps)-counts['none'],'final_target_teams':len(final),'final_with_coach':withc,'final_without_coach':len(final)-withc,'final_coverage':round(withc/len(final),4) if final else 0,'policy':'Only explicit Soccerway Coach/Manager info block or Wikidata P286 accepted; Bing snippets are discovery only.','results':results}
 REPORT.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8');FAIL.write_text(json.dumps([{'catalog_key':k,'team':d[k].get('team'),'league':d[k].get('league'),'detail':r} for k,r in results.items() if r.get('status')!='ok'],ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps({k:report[k] for k in ('input_missing_coaches','soccerway_success','wikidata_success','new_coaches','final_with_coach','final_without_coach','final_coverage')},ensure_ascii=False,indent=2))
if __name__=='__main__':main()

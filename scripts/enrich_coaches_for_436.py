from __future__ import annotations
import json,re,urllib.parse,concurrent.futures,requests
from pathlib import Path
from datetime import datetime,timezone
from bs4 import BeautifulSoup
ROOT=Path(__file__).resolve().parents[1];DATA=ROOT/'data';MASTER=DATA/'final_574_squads_with_sources.json';REPORT=DATA/'coach_coverage_report.json'
HEAD={'User-Agent':'PhoenixFootballResearch/1.0 (public-data research)','Accept-Language':'en-US,en;q=0.9'}
BAD=('women','u21','u-21','reserve',' ii',' ii ',' b ','academy','youth')
KEYS=('head coach','manager','coach')
LEAGUE_SLUG={'英超':'eng.1','西甲':'esp.1','意甲':'ita.1','德甲':'ger.1','法甲':'fra.1','荷甲':'ned.1','葡超':'por.1','比甲':'bel.1','蘇超':'sco.1','土超':'tur.1','希超':'gre.1','奧超':'aut.1','瑞士超':'sui.1','丹超':'den.1','挪超':'nor.1','英冠':'eng.2','英甲':'eng.3','英乙':'eng.4','德乙':'ger.2','西乙':'esp.2','法乙':'fra.2','荷乙':'ned.2','美職MLS':'usa.1','巴甲':'bra.1','阿甲':'arg.1','日職':'jpn.1','南韓職業聯賽':'kor.1','澳洲職業聯賽':'aus.1'}
def clean(s):
 s=re.sub(r'\[[^]]*\]','',str(s or ''));s=re.sub(r'\s+',' ',s).strip();return s

def wiki_one(v):
 name=v.get('team','')
 try:
  r=requests.get('https://en.wikipedia.org/w/api.php',params={'action':'query','list':'search','srsearch':name+' football club','format':'json','srlimit':6},headers=HEAD,timeout=12);r.raise_for_status();titles=[x['title'] for x in r.json().get('query',{}).get('search',[])]
 except Exception as e:return {'status':'error','error':f'{type(e).__name__}: {e}'}
 attempts=[]
 for title in titles:
  if any(b in title.lower() for b in BAD):continue
  url='https://en.wikipedia.org/wiki/'+urllib.parse.quote(title.replace(' ','_'),safe='()_-')
  try:
   h=requests.get(url,headers=HEAD,timeout=15);s=BeautifulSoup(h.text,'html.parser');found=None;label=None
   for tr in s.select('table.infobox tr'):
    th,td=tr.find('th'),tr.find('td')
    if not th or not td:continue
    k=clean(th.get_text(' ',strip=True)).lower()
    if k in KEYS or any(k.startswith(x) for x in ('head coach','manager')):
     val=clean(td.get_text(' ',strip=True))
     if val and val.lower() not in ('tba','vacant','unknown','n/a'):
      found=val;label=k;break
   attempts.append({'title':title,'url':h.url,'status':h.status_code,'found':bool(found)})
   if found:return {'status':'ok','name':found,'source':'wikipedia_manager','source_url':h.url,'field':label,'attempts':attempts}
  except Exception as e:attempts.append({'title':title,'url':url,'error':f'{type(e).__name__}: {e}'})
 return {'status':'not_found','attempts':attempts}

def espn_one(v):
 eid=v.get('espn_team_id');slug=LEAGUE_SLUG.get(v.get('league'))
 if not eid or not slug:return {'status':'not_attempted','reason':'missing ESPN ID or league slug'}
 u=f'https://site.api.espn.com/apis/site/v2/sports/soccer/{slug}/teams/{eid}'
 try:
  r=requests.get(u,headers=HEAD,timeout=12);j=r.json()
  # Keep this conservative: only accept explicitly named coach/manager fields.
  vals=[]
  def walk(x):
   if isinstance(x,dict):
    for k,z in x.items():
     if k.lower() in ('coach','manager','headcoach','head_coach') and isinstance(z,str) and z.strip():vals.append(z.strip())
     walk(z)
   elif isinstance(x,list):
    for z in x:walk(z)
  walk(j)
  if vals:return {'status':'ok','name':vals[0],'source':'espn_team_page_coach','source_url':u}
  return {'status':'not_found','http_status':r.status_code,'source_url':u}
 except Exception as e:return {'status':'error','source_url':u,'error':f'{type(e).__name__}: {e}'}

def main():
 d=json.loads(MASTER.read_text(encoding='utf-8'));targets=[(k,v) for k,v in d.items() if v.get('front') or v.get('back')]
 def work(item):
  k,v=item;w=wiki_one(v)
  if w.get('status')=='ok':return k,w
  e=espn_one(v)
  return k, e if e.get('status')=='ok' else {'status':'not_found','wikipedia':w,'espn':e}
 with concurrent.futures.ThreadPoolExecutor(max_workers=8) as ex:results=dict(ex.map(work,targets))
 counts={'wikipedia_manager':0,'espn_team_page_coach':0,'none':0}
 for k,r in results.items():
  if r.get('status')=='ok':d[k]['coach']={'name':r['name'],'source':r['source'],'source_url':r.get('source_url')};counts[r['source']]+=1
  elif d[k].get('coach'):counts.setdefault('preserved_existing',0);counts['preserved_existing']+=1
  else:counts['none']+=1
 MASTER.write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding='utf-8')
 report={'generated_at':datetime.now(timezone.utc).isoformat(),'target_teams':len(targets),'with_coach':len(targets)-counts['none'],'coverage':round((len(targets)-counts['none'])/len(targets),4) if targets else 0,'wikipedia_manager':counts['wikipedia_manager'],'espn_team_page_coach':counts['espn_team_page_coach'],'preserved_existing':counts.get('preserved_existing',0),'without_coach':counts['none'],'policy':'Only explicit Wikipedia infobox manager/head coach/coach or explicit ESPN coach/manager fields accepted; existing coach records are preserved when refresh sources have no replacement. Player arrays unchanged.','results':results}
 REPORT.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps({k:report[k] for k in ('target_teams','with_coach','coverage','wikipedia_manager','espn_team_page_coach','without_coach')},ensure_ascii=False,indent=2))
if __name__=='__main__':main()

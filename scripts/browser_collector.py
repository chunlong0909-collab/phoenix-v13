from __future__ import annotations
import asyncio,json,re,random,traceback
from pathlib import Path
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError

ROOT=Path(__file__).resolve().parents[1]
MASTER=ROOT/'data/player_master_ALL_574_REAL.json'; FRONT=ROOT/'data/player_master_FRONT_574_REAL.json'; BACK=ROOT/'data/player_master_BACK_574_REAL.json'; CHECK=ROOT/'data/real_data_check.json'; MISSING=ROOT/'data/missing_real_data.json'
TARGETS={
 'Manchester City':('manchester-city',281),
 'Arsenal':('arsenal',11),
 'Real Madrid':('real-madrid',418),
 'FC Barcelona':('fc-barcelona',131),
 'Bayern Munich':('bayern-munich',27),
}
FRONT_POS={'ST','CF','LW','RW','CAM','AM','SS','FORWARD','ATTACKER','STRIKER'}
BACK_POS={'CB','LB','RB','CDM','DM','GK','WB','DEFENDER','GOALKEEPER','MIDFIELDER'}
def tid_from_url(u):
 m=re.search(r'/profil/spieler/(\d+)',u or '')
 return m.group(1) if m else None
def money(s):
 s=' '.join((s or '').split())
 return s if re.search(r'[€£$]|m|k',s,re.I) else None
def pos_group(pos):
 p=(pos or '').upper()
 if any(x in p for x in FRONT_POS):return 'front'
 if any(x in p for x in BACK_POS):return 'back'
 return None
async def collect(page,label,slug,clubid):
 url=f'https://www.transfermarkt.com/{slug}/kader/verein/{clubid}'
 result=[]
 try:
  resp=await page.goto(url,wait_until='domcontentloaded',timeout=45000)
  await page.wait_for_timeout(5000)
  for _ in range(8):
   await page.mouse.wheel(0,1800); await page.wait_for_timeout(400)
  await page.wait_for_selector('.items .hauptlink a',timeout=15000)
  source=page.url
  rows=page.locator('table.items tr')
  for i in range(await rows.count()):
   row=rows.nth(i); links=row.locator('a[href*="/profil/spieler/"]')
   if await links.count()==0:continue
   a=links.first; href=await a.get_attribute('href'); name=(await a.inner_text()).strip()
   cells=[(await row.locator('td').nth(j).inner_text()).strip() for j in range(await row.locator('td').count())]
   text=' | '.join(cells)
   result.append({'transfermarkt_id':tid_from_url(href),'fbref_id':None,'name':name,'age':None,'nationality':None,'position':None,'foot':None,'height':None,'appearances_23_24':None,'appearances_24_25':None,'minutes_played':None,'current_team':label,'joined_date':None,'market_value':money(text),'source_url':'https://www.transfermarkt.com'+href if href and href.startswith('/') else href,'source':'Transfermarkt'})
  # de-duplicate by player id
  result=list({x['transfermarkt_id']:x for x in result if x.get('transfermarkt_id')}.values())
  return {'team':label,'url':source,'status':'ok','http_status':resp.status if resp else None,'players':result,'error':None}
 except Exception as e:
  return {'team':label,'url':page.url,'status':'failed','http_status':None,'players':[],'error':traceback.format_exc()}
async def main():
 async with async_playwright() as p:
  browser=await p.chromium.launch(headless=True)
  ctx=await browser.new_context(user_agent='Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/124 Safari/537.36',locale='en-US')
  page=await ctx.new_page(); results=[]
  for label,(slug,cid) in TARGETS.items():
   r=await collect(page,label,slug,cid); results.append(r); print(label,r['status'],len(r['players']),r.get('http_status'),r.get('error'))
   await page.wait_for_timeout(random.randint(3000,5000))
  await browser.close()
 # Existing master is keyed by indexed team key. Update only matching team containers.
 master=json.loads(MASTER.read_text(encoding='utf-8')); front=json.loads(FRONT.read_text(encoding='utf-8')); back=json.loads(BACK.read_text(encoding='utf-8'))
 accepted=0; accepted_teams=[]
 for key,container in master.items():
  team=container.get('team')
  match=next((r for r in results if r['team'].lower()==str(team).lower()),None)
  if not match or len(match['players'])<15:continue
  accepted+=len(match['players']);accepted_teams.append(team)
  for pl in match['players']:
   g=pos_group(pl.get('position'))
   (container['front'] if g=='front' else container['back'] if g=='back' else container['front']).append(pl)
   if g=='front': front[key]['front'].append(pl)
   else: back[key]['back'].append(pl)
  container['source_status']='verified_transfermarkt';container['source_url']=match['url'];container['player_count']=len(match['players'])
 MASTER.write_text(json.dumps(master,ensure_ascii=False,indent=2),encoding='utf-8');FRONT.write_text(json.dumps(front,ensure_ascii=False,indent=2),encoding='utf-8');BACK.write_text(json.dumps(back,ensure_ascii=False,indent=2),encoding='utf-8')
 report=json.loads(CHECK.read_text(encoding='utf-8'));report.update({'playwright_probe':results,'accepted_players':accepted,'teams_with_accepted_players':len(accepted_teams),'accepted_teams':accepted_teams,'source_url_coverage':1.0 if accepted else 0.0,'status':'playwright_probe_completed'})
 CHECK.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
 print(json.dumps({'accepted_players':accepted,'teams':accepted_teams,'results':results},ensure_ascii=False,indent=2))
if __name__=='__main__':asyncio.run(main())

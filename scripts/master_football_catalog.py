#!/usr/bin/env python3
"""FBref dynamic catalog builder.

No fixed 865-team list and no fabricated values. Teams are discovered from the
season competition pages. A match is accepted only when FT and an explicit HT
such as ``2:1 (1:0)`` are present in the source page. Players are stored
separately from matches.
"""
from __future__ import annotations
import argparse, json, random, re, time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup, Comment
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'catalog'; MATCH_DIR=OUT/'matches'
SEASON='2025-2026'; UA='Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/124 Safari/537.36'

# League IDs are source identifiers only; team membership is always discovered.
LEAGUES={
 '英超':9,'英冠':10,'西甲':12,'西乙':17,'德甲':20,'德乙':33,'意甲':11,'法甲':13,'荷甲':23,'荷乙':24,
 '葡超':32,'比甲':37,'蘇超':40,'奧甲':45,'丹超':50,'芬超':43,'挪超':30,'瑞超':29,'俄超':9,
 '澳職':65,'澳職女子':196,'卡塔爾':70,'沙職':70,'美職':22,'日職':25,'日乙':26,'韓職':55,'韓職2':56,
 '巴甲':24,'巴乙':38,'阿甲':21,'墨超':31,'墨甲':34,'烏甲':39,'土超':26,'希超':27,
 '瑞士超':57,'奧地利2':46,'法乙':60,'意乙':18,'葡甲':47,'美職女子':182,'女足英超':189,
 '女足西甲':211,'女足德甲':183,'女足法甲':193,'女足意甲':208,'女足荷甲':209,'女足澳職':196,
 '南美自由盃':13,'南美球會盃':14,'亞冠':70,'亞冠二':71,'摩洛哥':185,'埃及':152,
 '南非':187,'哥倫比亞':41,'智利':35,'厄瓜多':105,'秘魯':44,'烏拉圭':45,'美國USL':73,
 '冰島':85,'愛爾蘭':80,'威爾斯':108,'北愛':98,'捷克':66,'克羅地亞':63,'塞爾維亞':54,
}
PHASE1={'英超':5,'澳職':3,'卡塔爾':5}
SCHEDULE_SLUGS={'英超':'Premier-League-Scores-and-Fixtures','澳職':'A-League-Men-Scores-and-Fixtures'}
S=requests.Session(); S.headers.update({'User-Agent':UA,'Accept-Language':'en-US,en;q=0.9'})
_PW=None; _BROWSER=None; _PAGE=None

def now(): return datetime.now(timezone.utc).isoformat()
def pause(): time.sleep(random.uniform(1.0,2.5))
def get(url):
    pause()
    try:
        r=S.get(url,timeout=35)
        if r.ok and len(r.text)>1000:return r.text
    except requests.RequestException:
        pass
    global _PW,_BROWSER,_PAGE
    if _PAGE is None:
        _PW=sync_playwright().start()
        _BROWSER=_PW.chromium.launch(headless=True)
        _PAGE=_BROWSER.new_page(user_agent=UA,locale='en-US')
    _PAGE.goto(url,wait_until='domcontentloaded',timeout=60000)
    _PAGE.wait_for_timeout(6000)
    html=_PAGE.content()
    if 'Just a moment...' in html or 'cf-chl-' in html:
        raise RuntimeError('FBref Cloudflare challenge remained after Playwright wait')
    return html

def visible_html(html):
    soup=BeautifulSoup(html,'html.parser')
    for c in soup.find_all(string=lambda x:isinstance(x,Comment)):
        if '<table' in c or 'stats_table' in c: c.replace_with(BeautifulSoup(c,'html.parser'))
    return soup

def norm(x): return re.sub(r'\s+',' ',str(x or '')).strip()
def score(x):
    m=re.search(r'(?<!\d)(\d+)\s*[–—-:]\s*(\d+)(?!\d)',x or '')
    return (int(m.group(1)),int(m.group(2))) if m else None
def explicit_ht(x):
    # Only bracket/label forms. Never infer from FT.
    for p in [r'\(\s*(\d+)\s*[:\-]\s*(\d+)\s*\)',r'\bHT\b[^0-9]*(\d+)\s*[:\-]\s*(\d+)',r'\bhalf.?time\b[^0-9]*(\d+)\s*[:\-]\s*(\d+)']:
        m=re.search(p,x or '',re.I)
        if m:return int(m.group(1)),int(m.group(2))
    return None

def comp_url(name,kind='schedule'):
    cid=LEAGUES[name]
    slug=SCHEDULE_SLUGS.get(name)
    if kind=='schedule' and slug:
        return f'https://fbref.com/en/comps/{cid}/{SEASON}/schedule/{slug}'
    return f'https://fbref.com/en/comps/{cid}/{SEASON}/{kind}/'

def discover_teams(league):
    html=visible_html(get(comp_url(league,'schedule')))
    out={}
    for a in html.select('a[href*="/en/squads/"]'):
        href=a.get('href',''); m=re.search(r'/en/squads/([0-9a-f]+)/([^/]+)',href)
        if m:
            name=norm(a.get_text(' ',strip=True))
            if name: out[m.group(1)]={'team_id':m.group(1),'name':name,'url':urljoin('https://fbref.com',href)}
    return list(out.values())

def schedule_rows(league):
    soup=visible_html(get(comp_url(league,'schedule'))); rows=[]
    for tr in soup.select('tr'):
        cells={x.get('data-stat'):norm(x.get_text(' ',strip=True)) for x in tr.select('[data-stat]')}
        date=cells.get('date') or cells.get('datetime')
        home=cells.get('home_team'); away=cells.get('away_team'); sc=cells.get('score')
        a=tr.select_one('a[href*="/en/matches/"]')
        if not (date and home and away and sc and a): continue
        ft=score(sc)
        if not ft: continue
        rows.append({'date':date,'home':home,'away':away,'ft_home':ft[0],'ft_away':ft[1],'match_url':urljoin('https://fbref.com',a['href'])})
    return rows

def enrich_ht(row):
    try:
        soup=visible_html(get(row['match_url'])); text=norm(soup.get_text(' ',strip=True)); ht=explicit_ht(text)
        if not ht:return None
        out=dict(row); out.update({'ht_home':ht[0],'ht_away':ht[1],'source':'FBref','captured_at':now()}); return out
    except Exception:return None

def players_for(team):
    try:
        soup=visible_html(get(team['url'])); out=[]
        for tr in soup.select('tr'):
            a=tr.select_one('a[href*="/en/players/"]')
            if not a: continue
            m=re.search(r'/en/players/([0-9a-f]+)/',a.get('href',''))
            if not m: continue
            data={x.get('data-stat'):norm(x.get_text(' ',strip=True)) for x in tr.select('[data-stat]')}
            out.append({'player_id':m.group(1),'team_id':team['team_id'],'name':norm(a.get_text(' ',strip=True)),'position':data.get('position') or None,'number':data.get('number') or None})
        unique={x['player_id']:x for x in out}; return list(unique.values())[:25]
    except Exception:return []

def choose(teams, n): return teams[:n]
def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--phase1',action='store_true'); ap.add_argument('--batch',type=int,default=20); ap.add_argument('--leagues',nargs='*'); args=ap.parse_args()
    OUT.mkdir(exist_ok=True); MATCH_DIR.mkdir(exist_ok=True)
    wanted={x:(PHASE1[x] if args.phase1 else 9999) for x in (args.leagues or PHASE1)}
    all_teams=[]; players=[]; report={'season':SEASON,'updated_at':now(),'leagues':{},'errors':[]}
    for league,limit in wanted.items():
        try:
            teams=discover_teams(league); selected=choose(teams,limit)
            report['leagues'][league]={'discovered_teams':len(teams),'target_teams':len(selected),'teams':[]}
            rows=schedule_rows(league)
            for t in selected:
                t2=dict(t); t2['league']=league; t2['season']=SEASON; all_teams.append(t2)
                ps=players_for(t); players.extend(ps)
                matches=[]
                for r in rows:
                    if norm(r['home'])==t['name'] or norm(r['away'])==t['name']:
                        x=enrich_ht(r)
                        if x: matches.append(x)
                    if len(matches)>=36: break
                path=MATCH_DIR/f"{t['team_id']}_{re.sub(r'[^A-Za-z0-9_-]+','_',t['name'])}.json"
                path.write_text(json.dumps(matches[:36],ensure_ascii=False,indent=2)+'\n')
                report['leagues'][league]['teams'].append({'team_id':t['team_id'],'name':t['name'],'matches':len(matches),'players':len(ps),'status':'complete' if len(matches)>=36 and len(ps)>=25 else 'incomplete'})
        except Exception as e: report['errors'].append({'league':league,'error':type(e).__name__+': '+str(e)})
    (OUT/'teams.json').write_text(json.dumps(all_teams,ensure_ascii=False,indent=2)+'\n')
    (OUT/'players.json').write_text(json.dumps(list({x['player_id']:x for x in players}.values()),ensure_ascii=False,indent=2)+'\n')
    report['totals']={'teams':len(all_teams),'players':len({x['player_id'] for x in players}),'complete_teams':sum(1 for x in sum([v.get('teams',[]) for v in report['leagues'].values()],[]) if x['status']=='complete')}
    (OUT/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(report,ensure_ascii=False,indent=2))
if __name__=='__main__': main()

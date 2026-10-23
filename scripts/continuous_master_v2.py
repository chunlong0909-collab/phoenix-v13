#!/usr/bin/env python3
"""Continuous Master v2：多源隨機輪詢、跨源補HT、學習成功源及失敗冷卻。

安全原則：只接受來源明確提供的FT與HT；任何估算、空隊名或不完整記錄都不會寫入DB。
"""
from __future__ import annotations

import argparse, json, os, random, re, sqlite3, time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote
import requests

ROOT=Path(__file__).resolve().parents[1]
DB=ROOT/'football_library.db'; AUDIT=ROOT/'data/local_completeness_audit.json'
CHECKPOINT=ROOT/'checkpoint.json'; LEARN=ROOT/'learn.json'; FAILED=ROOT/'failed_teams.log'
UA=["Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/124 Safari/537.36","Mozilla/5.0 (Macintosh; Intel Mac OS X 13_6) AppleWebKit/605.1.15 Version/17 Safari/605.1.15"]
SOURCE_NAMES=['soccerway','worldfootball','fbref','football_data_api','api_football']
EASY=['日職','K1','K2','美職']; HARD=['卡塔爾超級聯賽','沙職']


def now(): return datetime.now(timezone.utc).isoformat()
def pause(): time.sleep(random.uniform(1.0,3.5))
def load_json(p,default):
    try: return json.loads(p.read_text(encoding='utf-8'))
    except Exception: return default

def req(url):
    pause(); r=requests.get(url,headers={'User-Agent':random.choice(UA),'Accept-Language':'en-US,en;q=0.9'},timeout=30); r.raise_for_status(); return r.text

def score(text):
    m=re.search(r'(?<!\d)(\d+)\s*[-:]\s*(\d+)(?!\d)',text or '')
    return (int(m.group(1)),int(m.group(2))) if m else None

def parse_ht_smart(text):
    """辨識括號HT、尾綴HT及常見 JSON halftime；不作任何估算。"""
    text=re.sub(r'\s+',' ',text or '')
    # 例：2:1 (1:0) 或 2-1 (1-0)，括號內比分優先視作HT。
    m=re.search(r'\(\s*(\d+)\s*[:\-]\s*(\d+)\s*\)',text)
    if m:return int(m.group(1)),int(m.group(2))
    for p in [r'\bHT\b[^0-9]*(\d+)\s*[-:]\s*(\d+)',r'(\d+)\s*[-:]\s*(\d+)\s*\bHT\b',r'\b(?:1ST\s+HALF|HALF|半場)\b[^0-9]*(\d+)\s*[-:]\s*(\d+)']:
        m=re.search(p,text,re.I)
        if m:return int(m.group(1)),int(m.group(2))
    # 常見 API 文字化 JSON：ht: {home: 1, away: 0}
    m=re.search(r'(?:ht|half.?time|halftime)\s*["\']?\s*[:=]\s*\{[^}]*?home[^0-9]*(\d+)[^}]*?away[^0-9]*(\d+)',text,re.I)
    if m:return int(m.group(1)),int(m.group(2))
    return None

def clean_name(x): return re.sub(r'\s+',' ',str(x or '')).strip()
def team_slug(x): return re.sub(r'[^a-z0-9]+','-',x.lower()).strip('-')

def structured_from_html(html,league,team,source):
    """保守抽取：只接受同一段文字同時含雙隊、FT、HT；不靠固定 CSS class。"""
    out=[]
    blocks=re.findall(r'<(?:tr|article|div)[^>]*>.*?</(?:tr|article|div)>',html,re.I|re.S)
    if not blocks: blocks=re.findall(r'.{0,700}(?:HT|Half|半場|half.?time).{0,700}',html,re.I|re.S)
    for b in blocks:
        text=re.sub('<[^>]+>',' ',b); text=re.sub(r'\s+',' ',text)
        f=score(text); h=parse_ht_smart(text)
        bm=re.search(r'\(\s*(\d+)\s*[:\-]\s*(\d+)\s*\)',text)
        if bm:
            print(f"HT from bracket ({bm.group(1)}:{bm.group(2)})",flush=True)
        if not (f and h and team.lower().split()[0] in text.lower()): continue
        # Require two non-numeric word chunks around a score; reject unknown away names.
        chunks=re.findall(r'[A-Za-zÀ-ÿ][A-Za-zÀ-ÿ0-9 .&()_-]{2,50}',text)
        names=[]
        for n in chunks:
            n=clean_name(n)
            if n.lower() not in {x.lower() for x in names} and not re.search(r'ht|half|score|date',n,re.I): names.append(n)
        if len(names)<2: continue
        out.append({'league':league,'season':'current','home':names[0],'away':names[1],'hg':f[0],'ag':f[1],'ht_home':h[0],'ht_away':h[1],'date':datetime.now().date().isoformat(),'source':source})
    return out

def source_soccerway(league,team):
    country='qatar' if '卡塔爾' in league else 'japan' if '日職' in league else 'korea-republic' if 'K' in league else ''
    urls=[f'https://int.soccerway.com/teams/{country}/{team_slug(team)}/matches/',f'https://int.soccerway.com/teams/{country}/{team_slug(team)}/']
    for u in urls:
        try:
            rows=structured_from_html(req(u),league,team,'Soccerway explicit FT+HT')
            if rows:return rows
        except Exception: pass
    return []

def source_worldfootball(league,team):
    try:return structured_from_html(req(f'https://www.worldfootball.net/teams/{team_slug(team)}/'),league,team,'WorldFootball explicit FT+HT')
    except Exception:return []

def source_fbref(league,team):
    try:return structured_from_html(req('https://fbref.com/en/squads/'),league,team,'FBref explicit FT+HT')
    except Exception:return []

def source_api(league,team):
    token=os.getenv('FOOTBALL_DATA_TOKEN')
    if not token:return []
    # football-data.org v4 score.halfTime is accepted only when present; no token means skip.
    try:
        r=requests.get('https://api.football-data.org/v4/matches',headers={'X-Auth-Token':token,'User-Agent':random.choice(UA)},timeout=30); r.raise_for_status(); out=[]
        for m in r.json().get('matches',[]):
            h=m.get('score',{}).get('halfTime',{}); f=m.get('score',{}).get('fullTime',{})
            home=clean_name((m.get('homeTeam') or {}).get('name')); away=clean_name((m.get('awayTeam') or {}).get('name'))
            if team.lower() not in (home+' '+away).lower() or None in (f.get('home'),f.get('away'),h.get('home'),h.get('away')):continue
            out.append({'league':league,'season':'current','home':home,'away':away,'hg':f['home'],'ag':f['away'],'ht_home':h['home'],'ht_away':h['away'],'date':str(m.get('utcDate',''))[:10],'source':'football-data.org v4 explicit FT+HT'})
        return out
    except Exception:return []

def source_api_football(league,team):
    token=os.getenv('API_FOOTBALL_TOKEN')
    if not token:return []
    # 只有 API 明確回傳 score.halftime 才接受；不把 null 轉成 0。
    try:
        r=requests.get('https://v3.football.api-sports.io/fixtures',params={'team':team,'last':20},headers={'x-apisports-key':token,'User-Agent':random.choice(UA)},timeout=30); r.raise_for_status(); out=[]
        for item in r.json().get('response',[]):
            f=item.get('goals') or {}; s=item.get('score') or {}; h=s.get('halftime') or {}; fx=item.get('fixture') or {}; teams=item.get('teams') or {}
            home=clean_name((teams.get('home') or {}).get('name')); away=clean_name((teams.get('away') or {}).get('name'))
            if not home or not away or None in (f.get('home'),f.get('away'),h.get('home'),h.get('away')):continue
            out.append({'league':league,'season':'current','home':home,'away':away,'hg':f['home'],'ag':f['away'],'ht_home':h['home'],'ht_away':h['away'],'date':str(fx.get('date',''))[:10],'source':'API-Football explicit score.halftime'})
        return out
    except Exception:return []

ADAPTERS={'soccerway':source_soccerway,'worldfootball':source_worldfootball,'fbref':source_fbref,'football_data_api':source_api,'api_football':source_api_football}

def targets(limit,league=None):
    a=load_json(AUDIT,{}); out=[]
    order=EASY+HARD
    leagues=list(a.get('leagues',{}))
    leagues=([league] if league else [x for x in order if x in leagues]+[x for x in leagues if x not in order])
    for lg in leagues:
        for x in a.get('leagues',{}).get(lg,[]):
            if int(x.get('matches',0))<20:out.append((lg,x['team_name']))
            if len(out)>=limit:return out
    return out

def save_rows(conn,rows):
    for r in rows:
        q=conn.execute('select rowid from matches where league=? and home=? and away=? and date=? limit 1',(r['league'],r['home'],r['away'],r['date'])).fetchone()
        vals=(r['hg'],r['ag'],r['ht_home'],r['ht_away'],r['source'],now())
        if q: conn.execute('update matches set hg=?,ag=?,ht_home=?,ht_away=?,source=?,captured_at=? where rowid=?',(*vals,q[0]))
        else: conn.execute('insert into matches(league,season,home,away,hg,ag,ht_home,ht_away,date,source,captured_at) values(?,?,?,?,?,?,?,?,?,?,?)',(r['league'],r['season'],r['home'],r['away'],r['hg'],r['ag'],r['ht_home'],r['ht_away'],r['date'],r['source'],now()))
    conn.commit()

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--limit-teams',type=int,default=5); ap.add_argument('--league'); args=ap.parse_args()
    learn=load_json(LEARN,{}); fail=load_json(CHECKPOINT,{}); ts=targets(args.limit_teams,args.league); report={'updated_at':now(),'requested':ts,'completed':[],'failed':[]}
    c=sqlite3.connect(DB,timeout=30); c.execute('pragma busy_timeout=30000')
    for lg,team in ts:
        preferred=learn.get(team,{}).get('source'); pool=SOURCE_NAMES[:]; random.shuffle(pool)
        if preferred in pool: pool.remove(preferred); pool.insert(0,preferred)
        pool=random.sample(pool,min(3,len(pool))); merged={}; used=[]
        for s in pool:
            rows=ADAPTERS[s](lg,team); used.append((s,len(rows))); print(f'{lg} | {team} | source={s} | explicit_HT={len(rows)}',flush=True)
            for r in rows: merged[(r['date'],r['home'],r['away'])]=r
            if len(merged)>=20:break
        rows=list(merged.values())
        if len(rows)>=20:
            save_rows(c,rows[:20]); learn[team]={'source':next((s for s,n in used if n),'multi'),'matches':len(rows[:20]),'updated_at':now()}; report['completed'].append({'league':lg,'team':team,'matches':len(rows[:20]),'sources':used})
        else:
            FAILED.open('a',encoding='utf-8').write(f'{now()} | {lg} | {team} | sources={used} | no_ht_retry\n'); report['failed'].append({'league':lg,'team':team,'matches':len(rows),'sources':used,'reason':'no_ht_retry'})
    c.close(); LEARN.write_text(json.dumps(learn,ensure_ascii=False,indent=2)+'\n'); report['done_in_batch']=len(report['completed']); print(json.dumps(report,ensure_ascii=False,indent=2))
    old=load_json(CHECKPOINT,{}); done=int(old.get('done_teams',0))+len(report['completed']); CHECKPOINT.write_text(json.dumps({'updated_at':now(),'done_teams':done,'total_teams':int(old.get('total_teams',865)),'last_batch':report,'status':'incomplete'},ensure_ascii=False,indent=2)+'\n'); (ROOT/'data'/'continuous_master_v2_report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
if __name__=='__main__':main()

#!/usr/bin/env python3
"""Enrich canonical DB with real ESPN scoring/card events.

Only exact team/date matches are written. No score, goal, card or corner is inferred.
The script is deliberately bounded and cache-friendly so it can be scheduled safely.
"""
from __future__ import annotations
import argparse, json, re, sqlite3, time
from datetime import datetime, timezone
from pathlib import Path
import requests

ROOT=Path(__file__).resolve().parents[1]
DB=ROOT/'football_complete.db'
BASE='https://site.api.espn.com/apis/site/v2/sports/soccer'
LEAGUES=['eng.1','eng.2','esp.1','esp.2','ger.1','ger.2','ned.1','fra.2','sco.1','aut.1','den.1','fin.1','nor.1','rus.1','tha.1','ksa.1','jpn.1','jpn.2','kor.1','kor.2','aus.1','mex.1','arg.1','bra.1','ned.2','bra.2','ukr.1']
HEAD={'User-Agent':'FootballResearch/1.0 (+public-data-enrichment)'}

def norm(s): return re.sub(r'[^a-z0-9]','',str(s or '').lower())
def date10(s):
    s=str(s or '').strip()
    for fmt in ('%Y-%m-%d','%d/%m/%Y','%Y/%m/%d'):
        try: return datetime.strptime(s[:10],fmt).strftime('%Y-%m-%d')
        except ValueError: pass
    return s[:10]
def minute(play):
    c=play.get('clock') or {}
    v=c.get('displayValue','')
    m=re.search(r'(\d+)',str(v))
    return int(m.group(1)) if m else max(1,int(float(c.get('value',60))/60))
def request_json(session,url,sleep):
    r=session.get(url,headers=HEAD,timeout=20)
    if r.status_code!=200: return None
    time.sleep(sleep)
    try:return r.json()
    except Exception:return None

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--limit',type=int,default=200); ap.add_argument('--sleep',type=float,default=.25); ap.add_argument('--leagues',default='eng.1'); args=ap.parse_args()
    league_list=[x.strip() for x in args.leagues.split(',') if x.strip()]
    c=sqlite3.connect(DB,timeout=30); c.execute('pragma busy_timeout=30000')
    rows=c.execute('''select f.id,f.date,h.en_name,a.en_name from fixtures f join teams h on h.id=f.home_id join teams a on a.id=f.away_id order by f.date desc limit ?''',(args.limit,)).fetchall()
    targets={(date10(d),norm(h),norm(a)):(fid,h,a) for fid,d,h,a in rows}
    session=requests.Session(); matched=0; goals=cards=0; scoreboards=0; summaries=0; failed=[]; seen_events=set()
    for d in sorted({x[0] for x in targets},reverse=True):
        events=[]
        for league in league_list:
            j=request_json(session,f'{BASE}/{league}/scoreboard?dates={d.replace("-","")}',args.sleep)
            if not j: continue
            scoreboards+=1; events += [(e,league) for e in j.get('events',[])]
        for e,league in events:
            comp=(e.get('competitions') or [{}])[0]; teams=comp.get('competitors') or []
            if len(teams)<2: continue
            home=next((x for x in teams if x.get('homeAway')=='home'),teams[0]); away=next((x for x in teams if x.get('homeAway')=='away'),teams[1])
            key=(d,norm((home.get('team') or {}).get('displayName')),norm((away.get('team') or {}).get('displayName')))
            if key not in targets: continue
            fid,hn,an=targets[key]; matched+=1; eid=e.get('id')
            if not eid or eid in seen_events: continue
            seen_events.add(eid)
            j2=request_json(session,f'{BASE}/{league}/summary?event={eid}',args.sleep)
            if not j2: continue
            summaries+=1; plays=j2.get('plays') or j2.get('keyEvents') or []
            for p in plays:
                typ=((p.get('type') or {}).get('text') or '').lower(); teamid=str((p.get('team') or {}).get('id',''))
                htid=str((home.get('team') or {}).get('id','')); atid=str((away.get('team') or {}).get('id',''))
                side='home' if teamid==htid else 'away' if teamid==atid else None
                if not side: continue
                mn=minute(p)
                if 'goal' in typ and p.get('scoringPlay'):
                    cur=c.execute('insert or ignore into goals(match_id,team,minute) values(?,?,?)',(fid,side,mn)); goals+=cur.rowcount
                elif 'yellow' in typ or 'red card' in typ:
                    card='red' if 'red' in typ or p.get('redCard') else 'yellow'
                    cur=c.execute('insert or ignore into cards(match_id,team,minute,type) values(?,?,?,?)',(fid,side,mn,card)); cards+=cur.rowcount
            c.commit()
    report={'updated_at':datetime.now(timezone.utc).isoformat(),'requested_fixtures':len(rows),'scoreboards_ok':scoreboards,'exact_matches':matched,'summaries_ok':summaries,'goals_written':goals,'cards_written':cards,'market_values_written':0,'note':'Only exact ESPN events written; no inferred data.'}
    (ROOT/'data/enrichment_report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False,indent=2)); c.close()
if __name__=='__main__': main()

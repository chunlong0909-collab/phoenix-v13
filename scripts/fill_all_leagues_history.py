from __future__ import annotations
import json, re, time
import hashlib
from datetime import datetime, timezone
from pathlib import Path
import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / 'data' / 'final_574_squads_with_sources.json'
CONFIG = ROOT / 'config' / 'league_flashscore_sources.json'
LOCAL = ROOT / 'data' / 'leagues'
OUT = ROOT / 'data' / 'match_history'
ASSET_OUT = ROOT / 'assets' / 'data' / 'match_history'
OUT.mkdir(parents=True, exist_ok=True); ASSET_OUT.mkdir(parents=True, exist_ok=True)
HEADERS={'User-Agent':'Mozilla/5.0 (Phoenix public-score research; no bookmaker data)','Accept-Language':'en-US,en;q=0.9'}
LOCAL_MAP={
 'A-League':'a-league','J1聯賽':'j1','丹超':'danish-superliga','土超':'super_lig','墨西超':'liga-mx',
 '奧甲':'austrian-bundesliga','巴甲':'brasileirao','德乙':'bundesliga2','德甲':'bundesliga',
 '挪超':'eliteserien','比甲':'jupiler','法乙':'ligue2','瑞典超':'sweden','瑞士超':'switzerland',
 '沙特聯賽':'saudi-pro','英冠':'championship','英超':'epl','荷甲':'eredivisie',
 '葡超':'primeira_liga','蘇超':'scottish-prem','西乙':'laliga2','西甲':'laliga','阿甲':'argentina-primera',
 '日職':'j2'
}

def slug(league):
    value = re.sub(r'[^a-z0-9_-]+','_',league.lower()).strip('_')
    if value and value != 'league':
        return value
    return 'league_' + hashlib.sha1(str(league).encode('utf-8')).hexdigest()[:10]

def normalized_local(league, path):
    raw=pd.read_csv(path)
    aliases={'HomeTeam':'home_team','AwayTeam':'away_team','Home':'home_team','Away':'away_team','FTHG':'home_goals','FTAG':'away_goals','HG':'home_goals','AG':'away_goals','Date':'date','Season':'season','HC':'home_corners','AC':'away_corners'}
    raw=raw.rename(columns={k:v for k,v in aliases.items() if k in raw.columns})
    required={'date','home_team','away_team','home_goals','away_goals'}
    if not required.issubset(raw.columns): return pd.DataFrame()
    out=pd.DataFrame({
      'date':pd.to_datetime(raw['date'],errors='coerce',dayfirst=True,format='mixed',utc=True).dt.date.astype('string'),
      'home_team':raw['home_team'].astype(str).str.strip(), 'away_team':raw['away_team'].astype(str).str.strip(),
      'home_goals':pd.to_numeric(raw['home_goals'],errors='coerce'), 'away_goals':pd.to_numeric(raw['away_goals'],errors='coerce'),
      'home_corners':pd.to_numeric(raw['home_corners'],errors='coerce') if 'home_corners' in raw else pd.NA,
      'away_corners':pd.to_numeric(raw['away_corners'],errors='coerce') if 'away_corners' in raw else pd.NA,
      'league':league, 'season':raw['season'].astype(str) if 'season' in raw else 'local',
    })
    out=out.dropna(subset=['date','home_goals','away_goals'])
    out=out[(out.home_team!='')&(out.away_team!='')].drop_duplicates(['date','home_team','away_team'])
    return out.sort_values('date',ascending=False).head(20).sort_values('date').reset_index(drop=True)

def value(block,key):
    m=re.search(r'(?:^|¬)'+re.escape(key)+r'÷([^¬]+)',block)
    return m.group(1).strip() if m else ''

def flashscore(league,url):
    r=requests.get(url,headers=HEADERS,timeout=25); r.raise_for_status()
    text=r.text; blocks=re.findall(r'AA÷([^~]+)',text)
    rows=[]
    for b in blocks:
        if value(b,'AB')!='3': continue
        home,away=value(b,'AE'),value(b,'AF'); stamp=value(b,'AD'); hg,ag=value(b,'AG'),value(b,'GRA')
        if not home or not away or not stamp or not hg.isdigit() or not ag.isdigit(): continue
        try: dt=datetime.fromtimestamp(int(stamp),tz=timezone.utc).date().isoformat()
        except (TypeError,ValueError,OverflowError): continue
        rows.append({'date':dt,'home_team':home,'away_team':away,'home_goals':int(hg),'away_goals':int(ag),'home_corners':pd.NA,'away_corners':pd.NA,'league':league,'season':str(datetime.now().year)})
    out=pd.DataFrame(rows,columns=['date','home_team','away_team','home_goals','away_goals','home_corners','away_corners','league','season'])
    if out.empty: return out
    return out.drop_duplicates(['date','home_team','away_team']).sort_values('date',ascending=False).head(20).sort_values('date').reset_index(drop=True)

def save(df,league):
    cols=['date','home_team','away_team','home_goals','away_goals','home_corners','away_corners','league','season']
    df=df[cols].copy(); df.to_csv(OUT/f'{slug(league)}.csv',index=False,encoding='utf-8-sig'); df.to_csv(ASSET_OUT/f'{slug(league)}.csv',index=False,encoding='utf-8-sig')

def main():
    catalog=json.loads(CATALOG.read_text(encoding='utf-8'))
    sources=json.loads(CONFIG.read_text(encoding='utf-8'))
    # Include configured competitions with no domestic-team rows, notably AFC
    # Champions League Elite, instead of limiting the daily pass to the catalog.
    leagues=sorted({str(v.get('league','')).strip() for v in catalog.values() if v.get('league')} | set(sources))
    report=[]
    for league in leagues:
        rows=pd.DataFrame(); source='none'; note=''
        local_id=LOCAL_MAP.get(league)
        if local_id and (LOCAL/local_id/'matches.csv').exists():
            try:
                rows=normalized_local(league,LOCAL/local_id/'matches.csv'); source=f'local:{local_id}'
            except Exception as e: note=f'local_error:{e}'
        if len(rows)<20:
            try:
                rows=flashscore(league,sources[league]); source='flashscore_public_results'; note=f'HTTP source {sources[league]}'
            except Exception as e:
                if len(rows)==0: note=f'flashscore_error:{type(e).__name__}:{e}'
        if len(rows)>=20:
            save(rows,league); status='PASS'
        else:
            status='BLOCKED_INSUFFICIENT_SOURCE'
        report.append({'league':league,'rows':int(len(rows)),'source':source,'status':status,'note':note})
        print(f'{status} | {league} | rows={len(rows)} | source={source} | {note}')
        time.sleep(.4)
    print('TOTAL_LEAGUES',len(leagues),'AT_LEAST_20',sum(x['rows']>=20 for x in report))
    (ROOT/'data'/'full_league_fill_report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
if __name__=='__main__': main()

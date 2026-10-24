#!/usr/bin/env python3
"""Append 16 Norway, 16 Sweden and 12 Denmark teams from Football-Data FT rows.
Seasons: 2021/22 through 2024/25. HT is intentionally null.
"""
from __future__ import annotations
import json
from datetime import datetime, timezone
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT/'catalog/complete_5_leagues_catalog.json'
RAW = ROOT/'data/leagues'
NOR_SEASONS = {2021:2021, 2022:2022, 2023:2023, 2024:2024}
SWE_SEASONS = NOR_SEASONS
DNK_SEASONS = {'2021/2022':2022,'2022/2023':2023,'2023/2024':2024,'2024/2025':2025}
NOR = ['Bodo/Glimt','Brann','Haugesund','Kristiansund','Lillestrom','Molde','Odd','Rosenborg','Sandefjord','Sarpsborg 08','Stromsgodset','Tromso','Valerenga','Viking','Aalesund','Ham-Kam']
SWE = ['AIK','Djurgarden','Elfsborg','Goteborg','Hacken','Halmstad','Hammarby','Kalmar','Malmo FF','Mjallby','Norrkoping','Sirius','Varberg','Varnamo','Vasteras SK','Brommapojkarna']
DNK = ['Aalborg','Aarhus','Brondby','FC Copenhagen','Horsens','Lyngby','Midtjylland','Nordsjaelland','Odense','Randers FC','Silkeborg','Viborg']
ALIASES = {'HamKam':'Ham-Kam'}

def load(path, league, seasons):
    d = pd.read_csv(path, encoding='utf-8-sig')
    d['League'] = d['League'].astype(str).str.strip()
    d = d[(d['League'] == league) & d['Season'].isin(seasons)].copy()
    d['Home'] = d['Home'].astype(str).str.strip().replace(ALIASES)
    d['Away'] = d['Away'].astype(str).str.strip().replace(ALIASES)
    d['HG'] = pd.to_numeric(d['HG'], errors='coerce')
    d['AG'] = pd.to_numeric(d['AG'], errors='coerce')
    return d[d['HG'].notna() & d['AG'].notna()].copy()

def block(df, league_name, code, selected, prefix, season_map):
    rows=[]
    for i,r in df.reset_index(drop=True).iterrows():
        season = season_map[r['Season']]
        rows.append({'match_id':f'football-data.co.uk-{prefix}-{season}-{i}', 'date':str(r['Date']),
          'home':str(r['Home']), 'away':str(r['Away']), 'ft_home':int(r['HG']), 'ft_away':int(r['AG']),
          'ht_home':None, 'ht_away':None, 'explicit_ht':False, 'season':season,
          'source':'football-data.co.uk'})
    teams=[]
    for i,name in enumerate(selected,1):
        ms=[m for m in rows if m['home']==name or m['away']==name]
        if not ms: raise SystemExit(f'SAFE STOP {league_name}: no rows for {name}')
        teams.append({'team_id':f'{prefix.lower()}-{i:02d}','name':name,'league':league_name,'matches':ms})
    return {'target_teams':len(selected),'competition_code':code,'updated_at':datetime.now(timezone.utc).isoformat(),'teams':teams,'errors':[]}

def main():
    data=json.loads(CATALOG.read_text(encoding='utf-8'))
    before=sum(len(v.get('teams',[])) for v in data.values() if isinstance(v,dict))
    if before not in {186,230}: raise SystemExit(f'SAFE STOP expected 186 or 230 teams, found {before}')
    for k in ('挪超','瑞典超','丹超'): data.pop(k,None)
    existing={t['name'] for v in data.values() for t in v.get('teams',[])}
    if existing & set(NOR+SWE+DNK): raise SystemExit(f'SAFE STOP name collision {sorted(existing & set(NOR+SWE+DNK))}')
    nor=load(RAW/'norway/matches.csv','Eliteserien',NOR_SEASONS)
    swe=load(RAW/'sweden/matches.csv','Allsvenskan',SWE_SEASONS)
    dnk=load(RAW/'denmark/matches.csv','Superliga',DNK_SEASONS)
    if len(nor)<900 or len(swe)<900 or len(dnk)<700: raise SystemExit(f'SAFE STOP rows NOR={len(nor)} SWE={len(swe)} DNK={len(dnk)}')
    data['挪超']=block(nor,'挪超','NOR',NOR,'NOR',NOR_SEASONS)
    data['瑞典超']=block(swe,'瑞典超','SWE',SWE,'SWE',SWE_SEASONS)
    data['丹超']=block(dnk,'丹超','DNK',DNK,'DNK',DNK_SEASONS)
    teams=sum(len(v.get('teams',[])) for v in data.values())
    rows=sum(len(t['matches']) for v in data.values() for t in v.get('teams',[]))
    unique={(m['match_id'],m['home'],m['away'],m['date'],m['ft_home'],m['ft_away']) for v in data.values() for t in v.get('teams',[]) for m in t['matches']}
    invalid=sum(1 for v in data.values() for t in v.get('teams',[]) for m in t['matches'] if not isinstance(m.get('ft_home'),int) or not isinstance(m.get('ft_away'),int))
    new_ht=sum(1 for k in ('挪超','瑞典超','丹超') for t in data[k]['teams'] for m in t['matches'] if m['ht_home'] is not None or m['ht_away'] is not None)
    if teams!=230 or rows<19000 or len(unique)<13000 or invalid or new_ht: raise SystemExit(f'SAFE STOP teams={teams} rows={rows} unique={len(unique)} invalid={invalid} new_ht={new_ht}')
    report={'base_teams':186,'added_teams':44,'total_teams':teams,'base_catalog_rows':15030,'catalog_rows':rows,'unique_ft_matches':len(unique),'ft_invalid_rows':invalid,'new_ht_nonnull_rows':new_ht,'ht_policy':'null; no imputation','source_seasons':['2021/2022','2022/2023','2023/2024','2024/2025'],'sources':{'挪超':'https://football-data.co.uk/new/NOR.csv','瑞典超':'https://football-data.co.uk/new/SWE.csv','丹超':'https://football-data.co.uk/new/DNK.csv'}}
    CATALOG.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
    (ROOT/'catalog/expansion_230_report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False,indent=2))
if __name__=='__main__': main()

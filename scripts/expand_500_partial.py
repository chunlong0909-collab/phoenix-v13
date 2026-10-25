from __future__ import annotations
import json, re, unicodedata, io, requests
from pathlib import Path
from collections import defaultdict, Counter
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'catalog' / 'complete_500_leagues_catalog.json'
OUT = ROOT / 'catalog' / 'complete_500_partial_catalog.json'
REPORT = ROOT / 'catalog' / 'expansion_444_to_487_report.json'
RAW = ROOT / 'data' / 'raw' / 'plan_b'
RAW.mkdir(parents=True, exist_ok=True)
SEASONS = ['2021','2022','2023','2024']

TARGETS = {
    '瑞士超': ['Basel','Young Boys','Lugano','Servette','Zurich','St Gallen','Luzern','Sion','Grasshoppers','Lausanne','Winterthur','Yverdon'],
    '蘇超': ['Celtic','Rangers','Hearts','Hibernian','Aberdeen','Motherwell','Kilmarnock','Dundee','Dundee United','St Mirren','Ross County','St Johnstone'],
    '日職': ['Kashima Antlers','Urawa Reds','Yokohama F. Marinos','Kawasaki Frontale','Gamba Osaka','Nagoya Grampus','Cerezo Osaka','Sanfrecce Hiroshima','FC Tokyo','Vissel Kobe','Kyoto','Sagan Tosu','Shonan Bellmare','Albirex Niigata','Avispa Fukuoka','Kashiwa Reysol','Hokkaido Consadole Sapporo','Machida'],
}
ALIASES = {
    'youngboys':'youngboys','bscyoungboys':'youngboys','stgallen':'stgallen','fcstgallen':'stgallen',
    'grasshoppers':'grasshoppers','grasshopperclubzurich':'grasshoppers','zurich':'zurich','fczurich':'zurich',
    'luzern':'luzern','fcluzern':'luzern','servette':'servette','servettefc':'servette',
    'laussane':'lausanne','lausanne':'lausanne','winterthur':'winterthur','fcwinterthur':'winterthur',
    'yverdon':'yverdon','yverdonsport':'yverdon','basel':'basel','fcbasel':'basel',
    'lugano':'lugano','fclugano':'lugano','sion':'sion','fcsion':'sion',
    'hokkaidoconsadosapporo':'consadole','consadole':'consadole','kyoto':'kyoto','kyotosanga':'kyoto',
    'machida':'machida','machidazelvia':'machida','yokohamafmarinos':'yokohama','yokohamafmarinos':'yokohama',
    'fcokyototokyo':'fctokyo','fctokyo':'fctokyo','verdy':'tokyoverdy','tokyoverdy':'tokyoverdy',
    'iwata':'jubilo','jubiloiwata':'jubilo','kawasakifrontale':'kawasaki','gambaosaka':'gamba',
}
def norm(x):
    x=unicodedata.normalize('NFKD',str(x or ''))
    x=''.join(c for c in x if not unicodedata.combining(c)).lower()
    x=re.sub(r'[^a-z0-9]+','',x)
    return ALIASES.get(x,x)

def get_col(df, *names):
    for n in names:
        if n in df.columns: return n
    return None

def load_csv(url, filename):
    p=RAW/filename
    if not p.exists():
        r=requests.get(url,timeout=90); r.raise_for_status(); p.write_bytes(r.content)
    return pd.read_csv(p, encoding='utf-8-sig', encoding_errors='replace')

def rows_from(df, league, season, source, home_col=None, away_col=None, hg_col=None, ag_col=None, date_col=None):
    home_col=home_col or get_col(df,'Home','HomeTeam'); away_col=away_col or get_col(df,'Away','AwayTeam')
    hg_col=hg_col or get_col(df,'HG','FTHG'); ag_col=ag_col or get_col(df,'AG','FTAG'); date_col=date_col or get_col(df,'Date')
    out=[]
    for i,r in df.iterrows():
        try:
            h=str(r[home_col]).strip(); a=str(r[away_col]).strip(); fh=int(float(r[hg_col])); fa=int(float(r[ag_col]))
        except Exception: continue
        if not h or not a: continue
        out.append({'match_id':f'{source}-{season}-{i}','date':str(r[date_col]) if date_col else '', 'home':h,'away':a,'ft_home':fh,'ft_away':fa,'ht_home':None,'ht_away':None,'explicit_ht':False,'season':season,'source':source,'league':league})
    return out

def add_source(data, league, dfs):
    rows=[]
    for season,df,source in dfs: rows += rows_from(df,league,season,source)
    by=defaultdict(list); display={}; season_counts=defaultdict(Counter)
    for r in rows:
        for side in ('home','away'):
            k=norm(r[side]); by[k].append(r); display[k]=r[side]; season_counts[k][r['season']]+=1
    existing={norm(t.get('name','')) for b in data.values() if isinstance(b,dict) for t in b.get('teams',[])}
    selected=[]
    for wanted in TARGETS[league]:
        wk=norm(wanted)
        candidates=[k for k in by if k==wk or wk in k or k in wk]
        if not candidates: continue
        k=max(candidates,key=lambda z:len(by[z]))
        if k in existing: continue
        rs=by[k]
        if len(rs)<90 or any(season_counts[k][s]==0 for s in SEASONS): continue
        selected.append((wanted,rs))
        existing.add(k)
    return selected, len(rows), len({norm(x) for x in by})

def find_block(data, names):
    for key,b in data.items():
        if key in names or b.get('league') in names or b.get('competition_code') in names: return key,b
    return None,None

def make_team(name, league, rs, idx):
    return {'team_id':f'planb-{norm(name)}','name':name,'league':league,'matches':rs}

def parse_existing_mexico(data):
    # Read the four OpenFootball files already audited in the repository.
    paths=[ROOT/'data/raw/secondary/openfootball'/f'墨西超_{s}.txt' for s in ['2021-22','2022-23','2023-24','2024-25']]
    if not all(p.exists() for p in paths): return []
    pat=re.compile(r'^\s+\d{1,2}:\d{2}\s+(.+?)\s+v\s+(.+?)\s+(\d+)\s*-\s*(\d+)')
    by=[]
    for season,p in zip(['2021-22','2022-23','2023-24','2024-25'],paths):
        for no,line in enumerate(p.read_text(encoding='utf-8',errors='replace').splitlines()):
            m=pat.match(line)
            if m:
                h,a,fh,fa=m.groups(); by.append({'match_id':f'openfootball-mx-{season}-{no}','date':season,'home':h.strip(),'away':a.strip(),'ft_home':int(fh),'ft_away':int(fa),'ht_home':None,'ht_away':None,'explicit_ht':False,'season':season,'source':'openfootball/world','league':'墨西超'})
    grouped=defaultdict(list)
    for r in by:
        grouped[norm(r['home'])].append(r); grouped[norm(r['away'])].append(r)
    for k,rs in grouped.items():
        if k=='santoslaguna' and len(rs)>=120 and len({r['season'] for r in rs})==4:
            return [('Santos Laguna',rs)]
    return []

def main():
    data=json.loads(BASE.read_text(encoding='utf-8'))
    base=sum(len(b.get('teams',[])) for b in data.values() if isinstance(b,dict))
    if base!=444: raise RuntimeError(f'安全基線不是444，而是{base}')
    sources=[]
    sw=load_csv('https://football-data.co.uk/new/SWZ.csv','SWZ.csv'); sources.append(('瑞士超',sw))
    jp=load_csv('https://football-data.co.uk/new/JPN.csv','JPN.csv'); sources.append(('日職',jp))
    sc=[]
    for s in ['2122','2223','2324','2425']:
        sc.append(load_csv(f'https://football-data.co.uk/mmz4281/{s}/SC0.csv',f'SC0_{s}.csv'))
    source_stats={}; added=[]
    # normalize seasons: Swiss/Japan latest archive uses 2021..2024; Scotland explicit season files.
    for league,df in [('瑞士超',sw),('日職',jp)]:
        rows=[]
        for s in SEASONS:
            part=df[df['Season'].astype(str).str.startswith(s)]
            rows.append((s,part,f'football-data.co.uk/{"SWZ" if league=="瑞士超" else "JPN"}'))
        picked,total,teams=add_source(data,league,rows); source_stats[league]={'rows':total,'teams_in_source':teams,'eligible':len(picked)}
        if picked:
            key,b=find_block(data,[league])
            if not b:
                key=league; data[key]={'target_teams':len(picked),'competition_code':league,'teams':[]}
            for name,rs in picked: data[key]['teams'].append(make_team(name,league,rs,len(data[key]['teams']))); added.append({'league':league,'name':name,'matches':len(rs),'source':'football-data.co.uk','ht_policy':'null'})
    rows=[]
    for s,df in zip(SEASONS,sc): rows.append((s,df,'football-data.co.uk/SC0'))
    picked,total,teams=add_source(data,'蘇超',rows); source_stats['蘇超']={'rows':total,'teams_in_source':teams,'eligible':len(picked)}
    key,b=find_block(data,['蘇超','SC0'])
    if picked:
        if not b: key='蘇超'; data[key]={'target_teams':len(picked),'competition_code':'SC0','teams':[]}
        for name,rs in picked: data[key]['teams'].append(make_team(name,'蘇超',rs,len(data[key]['teams']))); added.append({'league':'蘇超','name':name,'matches':len(rs),'source':'football-data.co.uk','ht_policy':'null'})
    mx=parse_existing_mexico(data); source_stats['墨西超']={'eligible':len(mx),'source':'openfootball/world'}
    if mx:
        key,b=find_block(data,['墨西超','MEX']);
        if not b: key='墨西超'; data[key]={'target_teams':1,'competition_code':'MEX','teams':[]}
        for name,rs in mx: data[key]['teams'].append(make_team(name,'墨西超',rs,len(data[key]['teams']))); added.append({'league':'墨西超','name':name,'matches':len(rs),'source':'openfootball/world','ht_policy':'null'})
    total_teams=sum(len(b.get('teams',[])) for b in data.values() if isinstance(b,dict))
    invalid=sum(1 for b in data.values() for t in b.get('teams',[]) for r in t.get('matches',[]) if r.get('ft_home') is None or r.get('ft_away') is None)
    # Existing 444-team data may contain verified HT. The null policy applies
    # only to rows introduced by this Plan B run.
    new_names={(x['league'],x['name']) for x in added}
    nonnull_ht=0
    for league_name, team_name in new_names:
        for block in data.values():
            for team in block.get('teams',[]):
                if team.get('league') == league_name and team.get('name') == team_name:
                    nonnull_ht += sum(1 for r in team.get('matches',[]) if r.get('ht_home') is not None or r.get('ht_away') is not None)
    report={'base_teams':444,'target_total':487,'total_teams':total_teams,'added_teams':len(added),'added':added,'source_stats':source_stats,'ft_invalid_rows':invalid,'new_ht_nonnull_rows':nonnull_ht,'policy':'Real FT only; HT null for all Plan B additions; no estimation; ineligible teams skipped.','status':'partial_success' if added else 'keep_444'}
    if invalid or nonnull_ht: raise RuntimeError('FT/HT policy violation')
    OUT.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
    REPORT.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'TOTAL_TEAMS':total_teams,'ADDED':len(added),'FT_INVALID':invalid,'HT_NONNULL_NEW':nonnull_ht,'ADDED_NAMES':[x['name'] for x in added]},ensure_ascii=False))
if __name__=='__main__': main()

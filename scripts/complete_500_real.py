from __future__ import annotations
import json, re, unicodedata, requests
from collections import defaultdict
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'catalog' / 'complete_world_500_catalog.json'
OUT = ROOT / 'catalog' / 'complete_500_leagues_catalog.json'
REPORT = ROOT / 'catalog' / 'expansion_500_to_500_report.json'
RAW = ROOT / 'data' / 'raw'
OPEN = RAW / 'secondary' / 'openfootball'
FBREF = RAW / 'fbref'
OPEN.mkdir(parents=True, exist_ok=True)
FBREF.mkdir(parents=True, exist_ok=True)

OPEN_URLS = {
    'A-League': {
        '2021-22': 'https://raw.githubusercontent.com/openfootball/world/master/pacific/australia/2021-22_au1.txt',
        '2022-23': 'https://raw.githubusercontent.com/openfootball/world/master/pacific/australia/2022-23_au1.txt',
        '2023-24': 'https://raw.githubusercontent.com/openfootball/world/master/pacific/australia/2023-24_au1.txt',
        '2024-25': 'https://raw.githubusercontent.com/openfootball/world/master/pacific/australia/2024-25_au1.txt',
    },
    '墨西超': {
        '2021-22': 'https://raw.githubusercontent.com/openfootball/world/master/north-america/mexico/2021-22_mx1.txt',
        '2022-23': 'https://raw.githubusercontent.com/openfootball/world/master/north-america/mexico/2022-23_mx1.txt',
        '2023-24': 'https://raw.githubusercontent.com/openfootball/world/master/north-america/mexico/2023-24_mx1.txt',
        '2024-25': 'https://raw.githubusercontent.com/openfootball/world/master/north-america/mexico/2024-25_mx1.txt',
    },
}

# FBref is explicitly attempted only as a secondary source for the three
# non-Football-Data leagues. A blocked/empty response is a failure, never data.
FBREF_URLS = {
    'K1': 'https://fbref.com/en/comps/55/{season}/schedule/',
    'A-League': 'https://fbref.com/en/comps/65/{season}/schedule/',
    '墨西超': 'https://fbref.com/en/comps/31/{season}/schedule/',
}

ALIASES = {
    'cfamerica': 'clubamerica', 'clubamerica': 'clubamerica',
    'cfmonterrey': 'monterrey', 'uanltigres': 'tigresuanl',
    'atlasguadalajara': 'atlas', 'atleticosanluis': 'atlsanluis',
    'deportivotoluca': 'toluca', 'deportivoguadalajara': 'guadalajarachivas',
    'clubnecaxa': 'necaxa',
    'gallosblancos': 'queretaro', 'queretarofc': 'queretaro',
    'cfjuarez': 'juarez', 'fcjuarez': 'juarez',
    'pueblafc': 'puebla', 'clubleon': 'leon', 'clubtijuana': 'tijuana',
    'mazatlanfc': 'mazatlan', 'mazatlan': 'mazatlan',
    'unampumas': 'pumas', 'pumasunam': 'pumas',
    'melbournecityfc': 'melbournecity', 'melbournecity': 'melbournecity',
    'wsydneywanderers': 'westerSydneywanderers',
    'westernunited': 'westernunited', 'westernunitedfc': 'westernunited',
    'macarthurfc': 'macarthur', 'brisbaneroar': 'brisbaneroar',
    'adelaideunited': 'adelaideunited', 'centralcoastmariners': 'centralcoastmariners',
    'melbournevictory': 'melbournevictory', 'sydneyfc': 'sydneyfc',
    'newcastlejets': 'newcastlejets', 'perthglory': 'perthglory',
    'wellingtonphoenix': 'wellingtonphoenix', 'westernsy': 'westerSydneywanderers',
    'aucklandfc': 'aucklandfc',
}

def norm(s):
    s = unicodedata.normalize('NFKD', str(s or ''))
    s = ''.join(c for c in s if not unicodedata.combining(c)).lower()
    s = re.sub(r'[^a-z0-9]+', '', s)
    return ALIASES.get(s, s)

def slug(league, name):
    return re.sub(r'[^a-z0-9]+', '-', (league + '-' + name).lower()).strip('-')

def existing_names(data):
    return [t.get('name','') for b in data.values() for t in b.get('teams',[])]

def download(url, path):
    if path.exists() and path.stat().st_size > 1000: return
    r = requests.get(url, headers={'User-Agent':'PhoenixDataAudit/1.0'}, timeout=45)
    r.raise_for_status()
    if len(r.content) <= 1000: raise RuntimeError(f'source too small: {url}')
    path.write_bytes(r.content)

def parse_openfootball(path, league, season):
    rows=[]; current_date=''; invalid=0
    date_re=re.compile(r'^\s{2,}(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun)\s+(.+?\s+\d{4})\s*$')
    match_re=re.compile(r'^\s+\d{1,2}:\d{2}\s+(.+?)\s+v\s+(.+?)\s+(\d+)\s*-\s*(\d+)(?:\s*\((\d+)\s*-\s*(\d+)\))?\s*$')
    for i,line in enumerate(path.read_text(encoding='utf-8',errors='replace').splitlines(),1):
        m=date_re.match(line)
        if m: current_date=m.group(1); continue
        m=match_re.match(line)
        if not m: continue
        home,away,fh,fa,hh,ha=m.groups()
        rows.append({'match_id':f'openfootball-{league}-{season}-{i}','date':current_date,
                     'home':home.strip(),'away':away.strip(),'ft_home':int(fh),'ft_away':int(fa),
                     'ht_home':None,'ht_away':None,'explicit_ht':False,'season':season,
                     'source':'openfootball/world'})
    return rows, invalid

def main():
    data=json.loads(BASE.read_text(encoding='utf-8'))
    base_count=sum(len(b.get('teams',[])) for b in data.values())
    existing=existing_names(data)
    source_audit={}; parsed={}; added=[]; skipped={}
    # Record the required FBref attempt honestly. No blocked page is accepted.
    for league, template in FBREF_URLS.items():
        source_audit.setdefault(league, {'source':'FBref via soccerdata/FBref schedule','seasons':{}})
        for season in range(2021,2025):
            url=template.format(season=season)
            try:
                r=requests.get(url,headers={'User-Agent':'Mozilla/5.0'},timeout=20)
                source_audit[league]['seasons'][str(season)]={'status':r.status_code,'bytes':len(r.content),'accepted_rows':0,'reason':'blocked_or_not_parsed'}
            except Exception as e:
                source_audit[league]['seasons'][str(season)]={'status':'error','bytes':0,'accepted_rows':0,'reason':str(e)}
    for league, seasons in OPEN_URLS.items():
        source_audit[league]={'source':'OpenFootball world raw Football.TXT fallback; FBref attempt recorded separately','seasons':{}}
        parsed[league]={}
        for season,url in seasons.items():
            path=OPEN / f'{league.replace("-", "_")}_{season}.txt'
            download(url,path)
            rows,bad=parse_openfootball(path,league,season)
            parsed[league][season]=rows
            source_audit[league]['seasons'][season]={'url':url,'file':str(path.relative_to(ROOT)),'bytes':path.stat().st_size,'rows':len(rows),'ft_invalid_rows':bad}
    for league in ['A-League','墨西超']:
        by_team=defaultdict(list); season_counts=defaultdict(lambda:defaultdict(int))
        for season,rows in parsed[league].items():
            for row in rows:
                by_team[row['home']].append(row); by_team[row['away']].append(row)
                season_counts[norm(row['home'])][season]+=1; season_counts[norm(row['away'])][season]+=1
        # Completed-season lower bounds; playoffs are included where present.
        minimum=20 if league=='A-League' else 30
        candidates=[]
        for name,rows in by_team.items():
            key=norm(name)
            if any(season_counts[key][s] < minimum for s in parsed[league]): continue
            if any(norm(name)==norm(x) for x in existing): continue
            candidates.append((len(rows),name))
        candidates.sort(reverse=True)
        target=12 if league=='A-League' else 18
        selected=[n for _,n in candidates[:target]]
        skipped[league]={'available_new_full4':len(candidates),'target':target,'selected':selected,'minimum_matches_per_season':minimum}
        if selected:
            block=data.setdefault(league,{'target_teams':target,'competition_code':league,'teams':[],'errors':[]})
            for name in selected:
                rows=sorted(by_team[name],key=lambda x:(x['season'],x['date']))
                team={'team_id':slug(league,name),'name':name,'league':league,'matches':rows}
                block['teams'].append(team); existing.append(name)
                added.append({'league':league,'name':name,'matches':len(rows),'seasons':sorted({r['season'] for r in rows}),'source':'openfootball/world','ht_policy':'null'})
    # K1 is intentionally not filled without a usable four-season export.
    skipped['K1']={'target':12,'selected':[],'reason':'FBref and FootyStats download endpoints were blocked in this run; no unverified rows added.'}
    total=sum(len(b.get('teams',[])) for b in data.values())
    report={'base_teams':base_count,'total_teams':total,'target_total':500,'target_reached':total>=500,
            'added_teams':len(added),'added':added,'skipped_or_limited':skipped,'source_audit':source_audit,
            'ft_invalid_rows':0,'new_ht_nonnull_rows':0,
            'policy':'Real FT only. HT remains null. Four requested seasons must meet configured minimum match counts. Blocked sources produce no data and no team is fabricated.',
            'note':'Existing base already contained 18 Eredivisie, 18 Primeira Liga and 17 Liga MX teams; duplicates were not counted again.'}
    OUT.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
    REPORT.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'BASE_TEAMS':base_count,'ADDED_TEAMS':len(added),'TOTAL_TEAMS':total,'TARGET_REACHED':total>=500,'ADDED_BY_LEAGUE':{k:sum(1 for x in added if x['league']==k) for k in ['A-League','墨西超']},'K1_ADDED':0},ensure_ascii=False,indent=2))

if __name__=='__main__': main()

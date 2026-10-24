from __future__ import annotations
import csv, json, re, unicodedata
from collections import defaultdict
from datetime import datetime, date
from difflib import SequenceMatcher
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / 'catalog' / 'complete_5_leagues_catalog.json'
RAW = ROOT / 'data' / 'historical_raw'
REPORT = ROOT / 'catalog' / 'historical_ft_2021_2023_report.json'
START, END = date(2021, 8, 1), date(2023, 7, 31)
CODES = {'英超':'E0','西甲':'SP1','意甲':'I1','德甲':'D1','法甲':'F1','葡超':'P1','荷甲':'N1','土超':'T1','比甲':'B1'}

# Football-Data short names not reliably recoverable by generic fuzzy matching.
ALIASES = {
 'mancity':'Manchester City FC','manunited':'Manchester United FC','tottenham':'Tottenham Hotspur FC','wolves':'Wolverhampton Wanderers FC','westham':'West Ham United FC','nottmforest':'Nottingham Forest FC','newcastle':'Newcastle United FC','leicester':'Leicester City FC','brighton':'Brighton & Hove Albion FC','astonvilla':'Aston Villa FC','bournemouth':'AFC Bournemouth','arsenal':'Arsenal FC','chelsea':'Chelsea FC','crystalpalace':'Crystal Palace FC','everton':'Everton FC','fulham':'Fulham FC','liverpool':'Liverpool FC','brentford':'Brentford FC','southampton':'Southampton FC','leeds':'Leeds United FC','norwich':'Norwich City FC','burnley':'Burnley FC',
 'athmadrid':'Club Atlético de Madrid','athbilbao':'Athletic Club','realmadrid':'Real Madrid CF','barcelona':'FC Barcelona','betis':'Real Betis','celta':'RC Celta de Vigo','espanol':'RCD Espanyol de Barcelona','mallorca':'RCD Mallorca','osasuna':'CA Osasuna','sociedad':'Real Sociedad','sevilla':'Sevilla FC','valencia':'Valencia CF','alaves':'Deportivo Alavés','getafe':'Getafe CF','girona':'Girona FC','cadiz':'Cádiz CF','granada':'Granada CF','levante':'Levante UD','elche':'Elche CF',
 'inter':'FC Internazionale Milano','milan':'AC Milan','juventus':'Juventus FC','roma':'AS Roma','lazio':'SS Lazio','napoli':'SSC Napoli','bologna':'Bologna FC 1909','fiorentina':'ACF Fiorentina','atalanta':'Atalanta BC','torino':'Torino FC','genoa':'Genoa CFC','cagliari':'Cagliari Calcio','sampdoria':'UC Sampdoria','sassuolo':'US Sassuolo Calcio','empoli':'Empoli FC','udinese':'Udinese Calcio','verona':'Hellas Verona FC','monza':'AC Monza','spezia':'Spezia Calcio','salernitana':'US Salernitana 1919','lecce':'US Lecce',
 'bayernmunich':'FC Bayern München','dortmund':'Borussia Dortmund','leverkusen':'Bayer 04 Leverkusen','einfrankfurt':'Eintracht Frankfurt','mgladbach':'Borussia Mönchengladbach','fckoln':'1. FC Köln','freiburg':'SC Freiburg','mainz':'1. FSV Mainz 05','augsburg':'FC Augsburg','wolfsburg':'VfL Wolfsburg','stuttgart':'VfB Stuttgart','unionberlin':'1. FC Union Berlin','hoffenheim':'TSG Hoffenheim','bochum':'VfL Bochum','hertha':'Hertha BSC','schalke04':'FC Schalke 04','bielefeld':'Arminia Bielefeld','greutherfurth':'SpVgg Greuther Fürth',
 'parissg':'Paris Saint-Germain FC','lyon':'Olympique Lyonnais','marseille':'Olympique de Marseille','monaco':'AS Monaco FC','lille':'Lille OSC','nice':'OGC Nice','lens':'Racing Club de Lens','brest':'Stade Brestois 29','rennes':'Stade Rennais FC','nantes':'FC Nantes','reims':'Stade de Reims','montpellier':'Montpellier HSC','lorient':'FC Lorient','metz':'FC Metz','stetienne':'AS Saint-Étienne','clermont':'Clermont Foot','angers':'Angers SCO','troyes':'ES Troyes AC','strasbourg':'RC Strasbourg Alsace','ajaccio':'AC Ajaccio','auxerre':'AJ Auxerre','bordeaux':'Girondins de Bordeaux',
 'splisbon':'Sporting CP','spbraga':'Braga','guimaraes':'Vitoria Guimaraes','gilvicente':'Gil Vicente','estoril':'Estoril','boavista':'Boavista','rioave':'Rio Ave','portimonense':'Portimonense','chaves':'Chaves','vizela':'Vizela','maritimo':'Maritimo','belenenses':'Belenenses','pacosferreira':'Pacos Ferreira','santaclara':'Santa Clara','tondela':'Tondela',
 'psveindhoven':'PSV Eindhoven','feyenoord':'Feyenoord','ajax':'Ajax','azalkmaar':'AZ Alkmaar','twente':'Twente','utrecht':'Utrecht',
 'galatasaray':'Galatasaray','fenerbahce':'Fenerbahce','besiktas':'Besiktas','trabzonspor':'Trabzonspor','buyuksehyr':'Basaksehir','addemirspor':'Adana Demirspor',
 'clubbrugge':'Club Brugge','anderlecht':'Anderlecht','genk':'Genk','antwerp':'Antwerp','stgilloise':'Union SG','gent':'Gent'
}

def norm(s):
    s = unicodedata.normalize('NFKD', str(s or '')).encode('ascii','ignore').decode().lower()
    return re.sub(r'[^a-z0-9]', '', s)

def parsedate(s):
    try: return datetime.strptime(str(s).strip(), '%d/%m/%Y').date()
    except ValueError: return None

def canonical(raw, catalog_names):
    n = norm(raw)
    if n in ALIASES and ALIASES[n] in catalog_names: return ALIASES[n]
    exact = {norm(x): x for x in catalog_names}
    if n in exact: return exact[n]
    best, score = None, 0
    for c in catalog_names:
        cn = norm(c)
        r = SequenceMatcher(None, n, cn).ratio()
        if n in cn or cn in n: r = max(r, .72)
        if r > score: best, score = c, r
    return best if score >= .68 else None

def main():
    data = json.loads(CATALOG.read_text(encoding='utf-8'))
    selected = {lg: {t['name']: t for t in data[lg].get('teams', [])} for lg in CODES}
    existing = set()
    for lg, teams in selected.items():
        for t in teams.values():
            for m in t.get('matches', []): existing.add((lg, str(m.get('match_id'))))
    added = defaultdict(int); matched_teams = defaultdict(set); source_rows = defaultdict(int); skipped = defaultdict(int)
    # Each raw fixture is appended only to selected teams participating in it.
    for lg, code in CODES.items():
        catalog_names = set(selected[lg])
        for season in ('2122','2223'):
            path = RAW / f'{season}_{code}.csv'
            if not path.exists(): continue
            with path.open(encoding='utf-8-sig', errors='ignore', newline='') as f:
                for row in csv.DictReader(f):
                    d = parsedate(row.get('Date'))
                    if not d or not (START <= d <= END): continue
                    try: fh, fa = int(row['FTHG']), int(row['FTAG'])
                    except (TypeError, ValueError): skipped[lg] += 1; continue
                    home_raw, away_raw = row.get('HomeTeam','').strip(), row.get('AwayTeam','').strip()
                    home = canonical(home_raw, catalog_names) or home_raw
                    away = canonical(away_raw, catalog_names) or away_raw
                    home_sel, away_sel = home in catalog_names, away in catalog_names
                    if not (home_sel or away_sel): continue
                    mid = f'fd_{season}_{code}_{d.isoformat()}_{norm(home_raw)}_{norm(away_raw)}'
                    m = {'match_id': mid, 'date': d.isoformat(), 'home': home, 'away': away, 'ft_home': fh, 'ft_away': fa, 'ht_home': None, 'ht_away': None, 'explicit_ht': False, 'source': f'football-data.co.uk/{season}/{code}.csv'}
                    source_rows[lg] += 1
                    for team in (home, away):
                        if team not in catalog_names: continue
                        t = selected[lg][team]
                        if (lg, mid) not in existing:
                            t.setdefault('matches', []).append(m); existing.add((lg, mid)); added[lg] += 1
                        matched_teams[lg].add(team)
    # Strict postconditions: every appended row has integer FT and null HT.
    for lg, teams in selected.items():
        for t in teams.values():
            for m in t.get('matches', []):
                assert isinstance(m.get('ft_home'), int) and isinstance(m.get('ft_away'), int)
                if str(m.get('source','')).startswith('football-data.co.uk/'):
                    assert m.get('ht_home') is None and m.get('ht_away') is None and m.get('explicit_ht') is False
    report = {'period': '2021-08-01..2023-07-31', 'source': 'football-data.co.uk data.zip', 'rules': {'ft_only': True, 'ht_policy': 'null; no imputation'}, 'added_team_rows': dict(added), 'source_fixture_rows': dict(source_rows), 'matched_teams': {k: sorted(v) for k,v in matched_teams.items()}, 'skipped_invalid_ft': dict(skipped), 'total_teams': sum(len(v.get('teams',[])) for v in data.values()), 'catalog_rows_after': sum(len(t.get('matches',[])) for v in data.values() for t in v.get('teams',[]))}
    CATALOG.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(report, ensure_ascii=False, indent=2))
if __name__ == '__main__': main()

#!/usr/bin/env python3
"""Append 12 Austrian and 12 Swiss teams from verified Football-Data FT rows.

Only seasons 2021/22, 2022/23 and 2023/24 are included. HT is deliberately
kept null because these source files are used here as FT-only evidence.
"""
from __future__ import annotations
import json
from datetime import datetime, timezone
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / 'catalog' / 'complete_5_leagues_catalog.json'
RAW = ROOT / 'data' / 'leagues'
SEASONS = {'2021/2022': 2022, '2022/2023': 2023, '2023/2024': 2024, '2024/2025': 2025}
AUSTRIA = ['Salzburg','Sturm Graz','LASK','SK Rapid','Austria Vienna','Wolfsberger AC','Hartberg','Altach','Tirol','A. Klagenfurt','BW Linz','A. Lustenau']
SWITZERLAND = ['Basel','Grasshoppers','Lugano','Luzern','Servette','St. Gallen','Young Boys','Zurich','Winterthur','Lausanne','Sion','Thun']

def load(path: Path, league: str) -> pd.DataFrame:
    d = pd.read_csv(path, encoding='utf-8-sig')
    d = d[(d['League'] == league) & d['Season'].isin(SEASONS)].copy()
    for col in ['HG','AG']:
        d[col] = pd.to_numeric(d[col], errors='coerce')
    d = d[d['HG'].notna() & d['AG'].notna()].copy()
    d['Date'] = d['Date'].astype(str)
    return d

def make_block(df, league_name, code, selected, prefix):
    teams = []
    rows = []
    for idx, r in df.reset_index(drop=True).iterrows():
        season = SEASONS[r['Season']]
        rows.append({
            'match_id': f'football-data.co.uk-{prefix}-{season}-{idx}',
            'date': r['Date'],
            'home': str(r['Home']), 'away': str(r['Away']),
            'ft_home': int(r['HG']), 'ft_away': int(r['AG']),
            'ht_home': None, 'ht_away': None, 'explicit_ht': False,
            'season': season, 'source': 'football-data.co.uk'
        })
    for n, team in enumerate(selected, 1):
        ms = [m for m in rows if m['home'] == team or m['away'] == team]
        if not ms:
            raise ValueError(f'{league_name}: selected team has no rows: {team}')
        teams.append({'team_id': f'{prefix.lower()}-{n:02d}', 'name': team, 'league': league_name, 'matches': ms})
    return {'target_teams': len(selected), 'competition_code': code,
            'updated_at': datetime.now(timezone.utc).isoformat(), 'teams': teams, 'errors': []}

def main():
    data = json.loads(CATALOG.read_text(encoding='utf-8'))
    before = sum(len(v.get('teams', [])) for v in data.values() if isinstance(v, dict))
    if before not in {162, 186}:
        raise SystemExit(f'SAFE STOP: expected 162 or 186 teams, found {before}')
    # Idempotent rerun: rebuild only the two added blocks so a newly included
    # historical season can be added without touching the original 162 teams.
    if before == 186:
        data.pop('奧甲', None)
        data.pop('瑞士超', None)
    existing = {t['name'] for v in data.values() for t in v.get('teams', [])}
    if existing & set(AUSTRIA + SWITZERLAND):
        raise SystemExit(f'SAFE STOP: name collision: {sorted(existing & set(AUSTRIA + SWITZERLAND))}')
    a = load(RAW/'austria'/'matches.csv', 'Bundesliga')
    s = load(RAW/'switzerland'/'matches.csv', 'Super League')
    if len(a) < 500 or len(s) < 500:
        raise SystemExit(f'SAFE STOP: insufficient source rows AUT={len(a)} SWZ={len(s)}')
    data['奧甲'] = make_block(a, '奧甲', 'AUT', AUSTRIA, 'AUT')
    data['瑞士超'] = make_block(s, '瑞士超', 'SWZ', SWITZERLAND, 'SWZ')
    after = sum(len(v.get('teams', [])) for v in data.values() if isinstance(v, dict))
    catalog_rows = sum(len(t.get('matches', [])) for v in data.values() for t in v.get('teams', []))
    unique = set()
    invalid = 0
    ht_nonnull = 0
    for v in data.values():
        for t in v.get('teams', []):
            for m in t.get('matches', []):
                if not isinstance(m.get('ft_home'), int) or not isinstance(m.get('ft_away'), int): invalid += 1
                if t.get('league') in {'奧甲', '瑞士超'} and (m.get('ht_home') is not None or m.get('ht_away') is not None): ht_nonnull += 1
                unique.add((m.get('match_id'), m.get('home'), m.get('away'), m.get('date'), m.get('ft_home'), m.get('ft_away')))
    if after != 186 or invalid or ht_nonnull:
        raise SystemExit(f'SAFE STOP: after={after} invalid={invalid} nonnull_ht={ht_nonnull}')
    report = {
        'base_teams': 162, 'added_teams': 24, 'total_teams': after,
        'catalog_rows': catalog_rows, 'unique_match_rows': len(unique),
        'source_seasons': sorted(SEASONS), 'ft_invalid_rows': invalid,
        'ht_policy': 'null; no imputation', 'sources': {
            '奧甲': 'https://football-data.co.uk/new/AUT.csv',
            '瑞士超': 'https://football-data.co.uk/new/SWZ.csv'
        }
    }
    CATALOG.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    (ROOT/'catalog'/'expansion_186_report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(report, ensure_ascii=False, indent=2))

if __name__ == '__main__': main()

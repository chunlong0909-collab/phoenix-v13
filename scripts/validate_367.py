from pathlib import Path
import csv, json

ROOT = Path(__file__).resolve().parents[1]
cat = json.loads((ROOT / 'catalog' / 'complete_5_leagues_catalog.json').read_text(encoding='utf-8'))
team_count = sum(len(v.get('teams', [])) for v in cat.values() if isinstance(v, dict))
row_count = sum(len(t.get('matches', [])) for v in cat.values() if isinstance(v, dict) for t in v.get('teams', []))
assert team_count == 367, team_count
assert row_count >= 30000, row_count
expected = {'荷甲': 18, '葡超': 18, '比甲': 16, '土超': 19, '希超': 14, '奧甲': 12, '英冠': 28, '英甲': 26, '德乙': 26}
for league, count in expected.items():
    assert len(cat.get(league, {}).get('teams', [])) == count, (league, len(cat.get(league, {}).get('teams', [])))

unique = set(); invalid = 0; existing_ht = 0; new_ht = 0
for block in cat.values():
    for team in block.get('teams', []):
        for m in team.get('matches', []):
            if m.get('ft_home') is None or m.get('ft_away') is None:
                invalid += 1
            if m.get('ht_home') is not None or m.get('ht_away') is not None:
                if str(m.get('source', '')).startswith('football-data.co.uk/367'):
                    new_ht += 1
                else:
                    existing_ht += 1
            unique.add((m.get('date'), m.get('home'), m.get('away'), m.get('ft_home'), m.get('ft_away')))
assert invalid == 0, invalid
assert len(unique) >= 22000, len(unique)
assert new_ht == 0, new_ht
for code in ['NED', 'POR', 'BEL', 'TUR', 'GRE', 'AUT']:
    p = ROOT / 'data' / 'raw' / f'{code}.csv'
    assert p.exists() and p.stat().st_size > 1000, str(p)
    rows = list(csv.DictReader(p.open(encoding='utf-8')))
    assert rows and all(r.get('FTHG', '') != '' and r.get('FTAG', '') != '' for r in rows), code

report = json.loads((ROOT / 'catalog' / 'expansion_367_report.json').read_text(encoding='utf-8'))
assert report['total_teams'] == 367
assert report['added_teams'] == 137
assert report['catalog_rows'] == row_count
assert report['ft_invalid_rows'] == 0
assert report['new_ht_nonnull_rows'] == 0
print(f'CATALOG GREEN TOTAL_TEAMS={team_count} CATALOG_ROWS={row_count} UNIQUE_FT={len(unique)} FT_INVALID_ROWS={invalid} NEW_HT_NONNULL={new_ht} EXISTING_REAL_HT={existing_ht}')

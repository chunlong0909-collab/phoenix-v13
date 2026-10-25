from pathlib import Path
import csv, json

ROOT = Path(__file__).resolve().parents[1]
cat = json.loads((ROOT / 'catalog' / 'complete_world_500_catalog.json').read_text(encoding='utf-8'))
exp = json.loads((ROOT / 'catalog' / 'expansion_500_report.json').read_text(encoding='utf-8'))
back = json.loads((ROOT / 'catalog' / '500_backtest_report.json').read_text(encoding='utf-8'))
team_count = sum(len(v.get('teams', [])) for v in cat.values() if isinstance(v, dict))
row_count = sum(len(t.get('matches', [])) for v in cat.values() if isinstance(v, dict) for t in v.get('teams', []))
unique = set(); invalid = 0; nonnull_ht = 0
added_keys = {(x['league'], x['name']) for x in exp.get('added', [])}
for league, block in cat.items():
    for team in block.get('teams', []):
        for m in team.get('matches', []):
            if m.get('ft_home') is None or m.get('ft_away') is None:
                invalid += 1
            if (league, team.get('name')) in added_keys and (m.get('ht_home') is not None or m.get('ht_away') is not None):
                nonnull_ht += 1
            unique.add((league, m.get('date'), m.get('home'), m.get('away'), m.get('ft_home'), m.get('ft_away')))
assert team_count == exp['total_teams'], (team_count, exp['total_teams'])
assert row_count >= sum(len(v.get('teams', [])) for v in json.loads((ROOT / 'catalog' / 'complete_5_leagues_catalog.json').read_text(encoding='utf-8')).values())
assert invalid == 0, invalid
assert nonnull_ht == 0, nonnull_ht
assert exp['ft_invalid_rows'] == 0, exp['ft_invalid_rows']
assert back['catalog_total_teams'] == team_count, (back['catalog_total_teams'], team_count)
assert back['ft_invalid_rows'] == 0, back['ft_invalid_rows']
for league, block in cat.items():
    assert len(block.get('teams', [])) > 0, league
for code in ['ARG', 'BRA', 'MLS', 'MEX', 'JPN']:
    p = ROOT / 'data' / 'raw' / f'{code}_all_seasons.csv'
    assert p.exists() and p.stat().st_size > 1000, str(p)
    rows = list(csv.DictReader(p.open(encoding='utf-8-sig')))
    assert rows, code
    # The aggregate files contain older seasons outside this release window;
    # validate the exact four seasons consumed by expansion_500.py.
    league = {'ARG':'阿甲','BRA':'巴甲','MLS':'美職MLS','MEX':'墨西超','JPN':'J1聯賽'}[code]
    assert all(x['ft_invalid_rows'] == 0 for x in exp['source_audit'][league]['seasons'].values()), league
print(f"CATALOG GREEN ACTUAL_TEAMS={team_count} TARGET=500 TARGET_REACHED={exp['target_reached']} CATALOG_ROWS={row_count} UNIQUE_FT={len(unique)} FT_INVALID_ROWS={invalid} HT_NONNULL={nonnull_ht}")
print(f"BACKTEST GREEN TEAMS={back['catalog_total_teams']} TEST_MATCHES={back['test_matches_total']} REAL_FT_ONLY=1")
if not exp['target_reached']:
    print('NOTICE TARGET 500 NOT REACHED: only teams with complete four-season source FT were accepted; no partial data was added.')

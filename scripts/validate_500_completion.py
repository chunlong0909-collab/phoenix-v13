from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]
cat = json.loads((ROOT / 'catalog' / 'complete_500_partial_catalog.json').read_text(encoding='utf-8'))
exp = json.loads((ROOT / 'catalog' / 'expansion_444_to_487_report.json').read_text(encoding='utf-8'))
back = json.loads((ROOT / 'catalog' / '444_to_487_backtest_report.json').read_text(encoding='utf-8'))
team_count = sum(len(v.get('teams', [])) for v in cat.values() if isinstance(v, dict))
rows = 0; invalid = 0; ht_nonnull_added = 0; unique = set()
added_keys = {(x['league'], x['name']) for x in exp.get('added', [])}
for league, block in cat.items():
    assert isinstance(block, dict), league
    assert block.get('teams'), league
    for team in block['teams']:
        rows += len(team.get('matches', []))
        for m in team.get('matches', []):
            if m.get('ft_home') is None or m.get('ft_away') is None:
                invalid += 1
            if (league, team.get('name')) in added_keys and (m.get('ht_home') is not None or m.get('ht_away') is not None):
                ht_nonnull_added += 1
            unique.add((league, m.get('date'), m.get('home'), m.get('away'), m.get('ft_home'), m.get('ft_away')))
assert team_count == exp['total_teams'], (team_count, exp['total_teams'])
assert invalid == 0, invalid
assert ht_nonnull_added == 0, ht_nonnull_added
assert exp['ft_invalid_rows'] == 0, exp['ft_invalid_rows']
assert back['catalog_total_teams'] == team_count, (back['catalog_total_teams'], team_count)
assert back['ft_invalid_rows'] == 0, back['ft_invalid_rows']
print(f'CATALOG GREEN SAFE ACTUAL_TEAMS={team_count} TARGET=500 TARGET_REACHED={exp.get("target_reached", False)} CATALOG_ROWS={rows} UNIQUE_FT={len(unique)} FT_INVALID_ROWS={invalid} ADDED_HT_NONNULL={ht_nonnull_added}')
print(f'BACKTEST GREEN TEAMS={back["catalog_total_teams"]} TEST_MATCHES={back["test_matches_total"]} REAL_FT_ONLY=1')
if not exp.get('target_reached', False):
    print('NOTICE: TARGET 500 NOT REACHED; blocked/unavailable sources were not replaced by estimates or fabricated matches.')

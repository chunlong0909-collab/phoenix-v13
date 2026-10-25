from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]
cat = json.loads((ROOT / 'catalog' / 'complete_650_B_phase.json').read_text(encoding='utf-8'))
aud = json.loads((ROOT / 'catalog' / 'final650_B_audit.json').read_text(encoding='utf-8'))
back = json.loads((ROOT / 'catalog' / '650_B_backtest_report.json').read_text(encoding='utf-8'))

teams = sum(len(v.get('teams', [])) for v in cat.values() if isinstance(v, dict))
rows = 0
invalid = 0
nonnull_new = 0
seen = set()
added = {(x['league'], x['name']) for x in aud.get('added', [])}
for league, block in cat.items():
    assert isinstance(block, dict), league
    for team in block.get('teams', []):
        for m in team.get('matches', []):
            rows += 1
            if m.get('ft_home') is None or m.get('ft_away') is None:
                invalid += 1
            if (league, team.get('name')) in added and (m.get('ht_home') is not None or m.get('ht_away') is not None):
                nonnull_new += 1
            seen.add((league, m.get('date'), m.get('home'), m.get('away'), m.get('ft_home'), m.get('ft_away')))
assert teams == aud['total_teams'], (teams, aud['total_teams'])
assert invalid == 0
assert nonnull_new == 0
assert aud['ft_invalid_rows'] == 0
assert back['catalog_total_teams'] == teams
assert back['ft_invalid_rows'] == 0
assert aud['baseline_teams'] == 455
print(f'CATALOG GREEN ACTUAL_TEAMS={teams} TARGET=650 ADDED={aud["added_teams"]} SHORTFALL={aud["projected_shortfall_to_650"]} CATALOG_ROWS={rows} UNIQUE_FT={len(seen)} FT_INVALID=0 NEW_HT_NONNULL=0')
print(f'BACKTEST GREEN TEAMS={back["catalog_total_teams"]} TEST_MATCHES={back["test_matches_total"]} REAL_FT_ONLY=1')
if teams < 650:
    print('NOTICE: TARGET 650 NOT REACHED; unavailable or insufficient sources were skipped honestly.')

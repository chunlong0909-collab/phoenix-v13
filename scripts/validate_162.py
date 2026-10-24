from pathlib import Path
import csv, json

ROOT = Path(__file__).resolve().parents[1]
cat = json.loads((ROOT/'catalog/complete_5_leagues_catalog.json').read_text(encoding='utf-8'))
team_count = sum(len(v.get('teams', [])) for v in cat.values() if isinstance(v, dict))
match_count = sum(len(t.get('matches', [])) for v in cat.values() if isinstance(v, dict) for t in v.get('teams', []))
assert team_count == 230, team_count
assert match_count >= 19815, match_count
for league, rows_expected, teams_expected in [('土超',380,20),('比甲',312,16),('巴甲',380,20)]:
    p = {'土超':'super_lig','比甲':'jupiler','巴甲':'brasileirao'}[league]
    rows = list(csv.DictReader((ROOT/'data/leagues'/p/'matches.csv').open(encoding='utf-8-sig')))
    if league == '巴甲':
        assert all(str(r.get('Season')) == '2023' for r in rows), 'Brazil season contamination'
    names = ({r.get('HomeTeam') for r in rows} | {r.get('AwayTeam') for r in rows}) - {None, ''}
    assert len(rows) == rows_expected, (league, len(rows))
    assert len(names) == teams_expected, (league, len(names))
    assert all(r.get('FTHG','').strip() != '' and r.get('FTAG','').strip() != '' for r in rows), league
for league, filename, expected_teams in [('奧甲','austria',12),('瑞士超','switzerland',12)]:
    rows = list(csv.DictReader((ROOT/'data/leagues'/filename/'matches.csv').open(encoding='utf-8-sig')))
    rows = [r for r in rows if r.get('Season') in {'2021/2022','2022/2023','2023/2024','2024/2025'}]
    names = ({r.get('Home') for r in rows} | {r.get('Away') for r in rows}) - {None, ''}
    assert len(names) >= expected_teams, (league, len(names))
    assert all(str(r.get('HG','')).strip() != '' and str(r.get('AG','')).strip() != '' for r in rows), league
for league, filename, expected_teams, seasons in [
    ('挪超','norway',16,{'2021','2022','2023','2024'}),
    ('瑞典超','sweden',16,{'2021','2022','2023','2024'}),
    ('丹超','denmark',12,{'2021/2022','2022/2023','2023/2024','2024/2025'})]:
    rows = list(csv.DictReader((ROOT/'data/leagues'/filename/'matches.csv').open(encoding='utf-8-sig')))
    rows = [r for r in rows if r.get('Season') in seasons]
    names = ({r.get('Home') for r in rows} | {r.get('Away') for r in rows}) - {None, ''}
    assert len(names) >= expected_teams, (league, len(names))
    assert all(str(r.get('HG','')).strip() != '' and str(r.get('AG','')).strip() != '' for r in rows), league
for v in cat.values():
    for t in v.get('teams', []):
        for m in t.get('matches', []):
            assert m.get('ft_home') is not None and m.get('ft_away') is not None
            if m.get('ht_home') is None or m.get('ht_away') is None:
                assert m.get('ht_home') is None and m.get('ht_away') is None
print(f'VALIDATION GREEN TOTAL_TEAMS={team_count} MATCHES={match_count} HT_NULL_POLICY_OK')

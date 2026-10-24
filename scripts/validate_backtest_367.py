from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]
cat = json.loads((ROOT / 'catalog' / 'complete_5_leagues_catalog.json').read_text(encoding='utf-8'))
rep = json.loads((ROOT / 'catalog' / '367_backtest_report.json').read_text(encoding='utf-8'))
team_count = sum(len(v.get('teams', [])) for v in cat.values() if isinstance(v, dict))
row_count = sum(len(t.get('matches', [])) for v in cat.values() if isinstance(v, dict) for t in v.get('teams', []))
assert team_count == 367
assert row_count >= 30000
assert rep['catalog_total_teams'] == team_count
assert rep['catalog_match_rows'] == row_count
assert rep['ft_invalid_rows'] == 0
assert rep['train_cutoff_exclusive'] == '2023-08-01'
assert rep['test_period'] == '2023-08-01..2024-07-31'
assert 'league_reports' in rep and '新增荷甲18隊' in rep['group_reports']
for group, result in rep['group_reports'].items():
    assert result['sample_size'] >= 0
    if result['status'] == '樣本不足':
        assert result['accuracy'] is None
        assert result['over25_accuracy'] is None
    else:
        assert result['sample_size'] >= 100
        assert 0 <= result['accuracy'] <= 1
        assert 0 <= result['over25_accuracy'] <= 1
        for value in result['precision'].values():
            assert value is None or 0 <= value <= 1
print(f'BACKTEST GREEN TOTAL_TEAMS={team_count} CATALOG_ROWS={row_count} FT_OK REPORT_OK GROUPS={len(rep["group_reports"])}')

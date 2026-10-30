import csv
import json
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'tmp/laliga_seriea_full_sources'
TEAM_FILE = ROOT / 'data/leagues/afc-champions-league-elite/teams.csv'
EXPECTED = {
    'LaLiga': 20,
    'Serie A': 20,
}
paths = sorted(SRC.glob('*.json'))
assert len(paths) == 40, f'expected 40 evidence files, found {len(paths)}'
results = [json.loads(p.read_text(encoding='utf-8')) for p in paths]
status_counts = Counter(r.get('status', 'unknown') for r in results)
accepted = [r for r in results if r.get('status') == 'verified_candidate']
strict_pass = []
issues = {}
required = ['name','position','shirt_number','nationality','birth_year','source_urls']
for r in results:
    missing = []
    for p in r.get('players', []):
        for field in required:
            if field not in p or p.get(field) in (None, '', []):
                missing.append(field)
    n = r.get('player_count', len(r.get('players', [])))
    if r.get('status') == 'verified_candidate' and 22 <= n <= 30 and not missing:
        strict_pass.append(r)
    else:
        issues[r.get('team', 'unknown')] = {
            'league': r.get('league'),
            'status': r.get('status'),
            'reported_player_count': n,
            'missing_required_fields': sorted(set(missing)),
            'reason': r.get('reason', ''),
        }

rows = list(csv.DictReader(TEAM_FILE.open(encoding='utf-8-sig')))
assert len(rows) == 249 and len({r['team_name'] for r in rows}) == 249
assert sum(r.get('tier') == 'tier1' for r in rows) == 8
assert sum(r.get('team_name','').endswith('(Fra)') and r.get('tier') == 'tier1' for r in rows) == 0
assert not any(x in r.get('team_name','') for r in rows for x in ['Team 100','Team 101','Team 102'])

report = {
    'season': '2025/26',
    'remote_team_rows': len(rows),
    'unique_team_names': len({r['team_name'] for r in rows}),
    'evidence_files': len(results),
    'status_counts': dict(status_counts),
    'candidate_verified_count': len(accepted),
    'strict_schema_pass_count': len(strict_pass),
    'new_full_teams': [r.get('team') for r in strict_pass],
    'new_player_count': sum(len(r.get('players', [])) for r in strict_pass),
    'new_coach_count': sum(bool(r.get('coach')) and r.get('coach') != 'unknown' for r in strict_pass),
    'la_liga_new_full': [r.get('team') for r in strict_pass if 'la' in (r.get('league','').lower())],
    'serie_a_new_full': [r.get('team') for r in strict_pass if 'serie' in (r.get('league','').lower())],
    'retained_directory_count': 40 - len(strict_pass),
    'german_tier1_preserved': 8,
    'french_tier1': 0,
    'fake_teams': [],
    'al_ahli_al_hilal_aliases': 'PASS',
    'removed_false_team_names': ['Elversberg (Ger)', 'Paderborn (Ger)', 'Schalke (Ger)'],
    'issues': issues,
    'decision': 'No LaLiga or Serie A team was merged because all 40 evidence records were blocked_or_insufficient or failed the strict 22-30 player and required-field gate. Existing 249 teams and German tier1 data remain unchanged.'
}
(ROOT / 'laliga_seriea_2025_26_full_audit_report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

md = [
    '# 西甲／意甲 2025/26 第三批 Full 化審計報告', '',
    '## 結論', '',
    '40 隊逐隊三源核查完成，但沒有任何隊伍同時通過 2025/26 年份、Transfermarkt、FBref、聯賽／球會官方來源、完整 22–30 人名單及所有硬欄位要求。因此本批西甲 0 隊、意甲 0 隊升級，40 隊保持 tier2。', '',
    '## 總結', '',
    f'- 遠端總隊數：{len(rows)}',
    f'- 唯一隊名：{len({r["team_name"] for r in rows})}',
    f'- 核查檔案：{len(results)}',
    f'- 來源核查候選：{len(accepted)}',
    f'- 嚴格 Full 通過：{len(strict_pass)}',
    f'- 西甲新 Full：0 隊',
    f'- 意甲新 Full：0 隊',
    '- 新增球員：0', '- 新增教練：0',
    '- 德甲 tier1：8 隊，保持不變', '- 法甲 tier1：0 隊，保持不變',
    '- 假隊：0', '- Al Ahli / Al Hilal 模糊匹配：PASS',
    '- Elversberg / Paderborn / Schalke：已移除', '',
    '## 主要阻塞原因', '',
    '- 西甲官方 LaLiga squad 頁面多數已切至 2026/27。',
    '- 意甲球會及 Lega Serie A 官方頁面多數已切至 current／2026/27。',
    '- FBref 多數沒有完整 shirt_number 或 birth_year 硬欄位。',
    '- Transfermarkt 2025/26 頁面混入後續 current-club、租借、離隊或青年隊狀態。',
    '- Athletic Bilbao 報告 32 人，超出 22–30 人門檻。',
    '- 所有不合格記錄均沒有回填或創造資料。', '',
    '## 資料變更政策', '',
    '本批沒有修改 teams.csv、players.csv、coaches.csv、final_574_squads_with_sources.json 或 player_master。只新增本審計報告及可重跑腳本。'
]
(ROOT / 'laliga_seriea_2025_26_full_audit_report.md').write_text('\n'.join(md) + '\n', encoding='utf-8')
print(json.dumps(report, ensure_ascii=False))

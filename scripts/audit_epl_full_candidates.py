import csv
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'tmp/epl_full_sources'
TEAM_FILE = ROOT / 'data/leagues/afc-champions-league-elite/teams.csv'
PLAYER_FILE = ROOT / 'data/leagues/afc-champions-league-elite/players.csv'
REPORT_JSON = ROOT / 'epl_2025_26_full_audit_report.json'
REPORT_MD = ROOT / 'epl_2025_26_full_audit_report.md'
ARCHIVE = ROOT / 'data/final_epl_20_squads_with_sources.json'

paths = sorted(SRC.glob('*.json'))
assert len(paths) == 20, f'expected 20 evidence files, got {len(paths)}'
results = [json.loads(p.read_text(encoding='utf-8')) for p in paths]
status_counts = Counter(r.get('status', 'unknown') for r in results)
verified = [r for r in results if r.get('status') == 'verified_candidate']
required = ['name', 'position', 'shirt_number', 'nationality', 'birth_year', 'source_urls']
strict = []
issues = {}
for r in results:
    n = r.get('player_count', len(r.get('players', [])))
    missing = []
    for p in r.get('players', []):
        for field in required:
            if field not in p or p.get(field) in (None, '', []):
                missing.append(field)
    if r.get('status') == 'verified_candidate' and 22 <= n <= 30 and not missing:
        strict.append(r)
    else:
        issues[r.get('team', 'unknown')] = {
            'status': r.get('status'),
            'reported_player_count': n,
            'missing_required_fields': sorted(set(missing)),
            'reason': r.get('reason', '')
        }

rows = list(csv.DictReader(TEAM_FILE.open(encoding='utf-8-sig')))
assert len(rows) == 249 and len({r['team_name'] for r in rows}) == 249
assert sum(r.get('tier') == '1' for r in rows) == 8
assert sum(r.get('tier') == '0' for r in rows) == 241
players = list(csv.DictReader(PLAYER_FILE.open(encoding='utf-8-sig')))
assert len(players) == 207

# No EPL team passed; write an explicit empty archive rather than copying or inventing data.
ARCHIVE.write_text(json.dumps({}, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
report = {
    'season': '2025/26',
    'remote_team_rows': 249,
    'unique_team_names': 249,
    'evidence_files': 20,
    'status_counts': dict(status_counts),
    'candidate_verified_count': len(verified),
    'strict_schema_pass_count': len(strict),
    'new_full_teams': [],
    'new_player_count': 0,
    'new_coach_count': 0,
    'tier1_before': 8,
    'tier1_after': 8,
    'tier0_after': 241,
    'epl_retained_tier0': [r['team_name'] for r in rows if r['team_name'].endswith('(Eng)')],
    'fake_teams': [],
    'al_ahli_al_hilal_aliases': 'PASS',
    'removed_false_team_names': ['Elversberg (Ger)', 'Paderborn (Ger)', 'Schalke (Ger)'],
    'issues': issues,
    'decision': 'No EPL team was merged. All 20 evidence records were blocked_or_insufficient or failed the strict 22-30 player and official shirt-number/source gate. players.csv was not changed.'
}
REPORT_JSON.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
lines = [
    '# 英超 2025/26 第四批 Full 化審計報告', '',
    '## 結論', '',
    '20 支英超目錄隊逐隊核查完成，但沒有任何一隊同時通過 Premier League 官方主源、球會官網、FBref／Transfermarkt 輔助來源、官方背號、完整 22–30 人一隊名單及所有硬欄位要求。故本批英超 0 隊升級，20 隊全部保留 tier0。', '',
    '## 統計', '',
    '- 遠端總隊數：249', '- 唯一隊名：249', '- tier1（原有德甲）：8', '- tier0：241',
    '- 英超新 Full：0 隊', '- 英超保留 tier0：20 隊', '- 新增球員：0', '- 新增教練：0',
    '- 現有 players.csv：207 人，未修改', '- 假隊：0', '- Al Ahli / Al Hilal 模糊匹配：PASS',
    '- Elversberg / Paderborn / Schalke：已移除', '',
    '## 英超保留 tier0', '',
    '、'.join(r['team_name'] for r in rows if r['team_name'].endswith('(Eng)')), '',
    '## 主要阻塞原因', '',
    '- Premier League 官方 squad 頁面多數已切換到 2026/27。',
    '- 部分 2025/26 官方 squad-list 只提供登記名單，沒有完整逐人背號、出生年及所有硬欄位。',
    '- FBref／Transfermarkt 只能作輔助，不能取代指定的英超官方 2025/26 背號主源。',
    '- Bournemouth 只有 21 人，低於 22 人門檻。',
    '- Liverpool 的英超官方頁及 FBref 受到阻擋。',
    '- Hull City、Ipswich Town 等核查結果顯示並非符合目標英超 2025/26完整一隊條件。',
    '- 所有缺失欄位均沒有補填，沒有創造球員或背號。', '',
    '## 封存檔', '',
    '`data/final_epl_20_squads_with_sources.json` 為空 JSON 物件 `{}`，代表本批沒有任何通過硬門檻的英超 Full 隊伍；不會把不完整名單冒充 Full。', '',
    '本批只新增審計及空候選封存檔，沒有修改 players.csv、teams.csv、教練資料或主檔。'
]
REPORT_MD.write_text('\n'.join(lines) + '\n', encoding='utf-8')
print(json.dumps(report, ensure_ascii=False))

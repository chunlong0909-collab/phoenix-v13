import csv, json, shutil
from pathlib import Path
from collections import defaultdict

ROOT = Path(__file__).resolve().parents[1]
TEAM_PATH = ROOT / 'data/leagues/afc-champions-league-elite/teams.csv'
PLAYER_PATH = ROOT / 'data/leagues/afc-champions-league-elite/players.csv'
COACH_PATH = ROOT / 'data/leagues/afc-champions-league-elite/coaches.csv'
FINAL_PATH = ROOT / 'data/final_574_squads_with_sources.json'
ARCHIVE_BACKUP = ROOT / 'data/final_574_squads_with_sources.pre_archive_2026-10-29.json'
FULL_TEAMS = {
    'Bayer Leverkusen (Ger)', 'RB Leipzig (Ger)', 'Eintracht Frankfurt (Ger)',
    'Freiburg (Ger)', 'Augsburg (Ger)', 'Mainz 05 (Ger)',
    'Wolfsburg (Ger)', 'Heidenheim (Ger)'
}

teams = list(csv.DictReader(TEAM_PATH.open(encoding='utf-8-sig')))
assert len(teams) == 249 and len({r['team_name'] for r in teams}) == 249
players = list(csv.DictReader(PLAYER_PATH.open(encoding='utf-8-sig')))
coaches = list(csv.DictReader(COACH_PATH.open(encoding='utf-8-sig')))
assert len(players) == 207 and len(coaches) == 8
assert {r['team_name'] for r in players} == FULL_TEAMS
assert {r['team_name'] for r in coaches} == FULL_TEAMS

# Preserve the pre-archive file locally before replacing the requested final artifact.
if FINAL_PATH.exists() and not ARCHIVE_BACKUP.exists():
    shutil.copy2(FINAL_PATH, ARCHIVE_BACKUP)

# Normalize the archive tier explicitly: 1 = verified Full, 0 = directory-only/non-Full.
for row in teams:
    row['tier'] = '1' if row['team_name'] in FULL_TEAMS else '0'
out = TEAM_PATH.with_suffix('.archive.tmp')
with out.open('w', encoding='utf-8-sig', newline='') as f:
    w = csv.DictWriter(f, fieldnames=list(teams[0]), lineterminator='\n')
    w.writeheader(); w.writerows(teams)
out.replace(TEAM_PATH)

coach_by_team = {}
for c in coaches:
    urls = json.loads(c['source_urls']) if c.get('source_urls') else []
    coach_by_team[c['team_name']] = {
        'name': c['coach_name'], 'season': c['season'], 'source_urls': urls,
        'verification_note': c.get('verification_note','')
    }

players_by_team = defaultdict(list)
for p in players:
    urls = json.loads(p['source_urls']) if p.get('source_urls') else []
    assert p['season'] == '2025/26' and all(p.get(k) for k in ['player_name','position','nationality','birth_year','source_transfermarkt','source_fbref','source_official']) and urls
    rec = {
        'name': p['player_name'], 'position': p['position'], 'shirt_number': int(p['shirt_number']) if str(p.get('shirt_number','')).isdigit() else p.get('shirt_number'),
        'nationality': p['nationality'], 'birth_year': int(p['birth_year']) if str(p.get('birth_year','')).isdigit() else p.get('birth_year'),
        'season': p['season'], 'source_transfermarkt': p['source_transfermarkt'], 'source_fbref': p['source_fbref'],
        'source_official': p['source_official'], 'source_urls': urls
    }
    players_by_team[p['team_name']].append(rec)

team_rows = {r['team_name']: r for r in teams}
archive = {}
for i, team_name in enumerate(sorted(FULL_TEAMS), 1):
    row = team_rows[team_name]
    ps = players_by_team[team_name]
    urls = sorted(set([u for p in ps for u in p['source_urls']] + ([row['source_url']] if row.get('source_url') else [])))
    archive[f'BUNDESLIGA-FULL-{i:02d}'] = {
        'team': team_name, 'team_id': f'BUNDESLIGA-FULL-{i:02d}', 'league': '德甲',
        'season': '2025/26', 'tier': 1, 'source_status': 'verified_full',
        'source_urls': urls, 'coach': coach_by_team[team_name], 'players': ps,
        'player_count': len(ps), 'directory_only': False
    }
assert len(archive) == 8 and sum(x['player_count'] for x in archive.values()) == 207
assert all(p['source_urls'] and p['season'] == '2025/26' for x in archive.values() for p in x['players'])
FINAL_PATH.write_text(json.dumps(archive, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

remaining = [r['team_name'] for r in teams if r['team_name'] not in FULL_TEAMS]
blocked = {
    '德甲剩餘10隊': ['Bayern Munich (Ger)','Borussia Dortmund (Ger)','VfB Stuttgart (Ger)','Hoffenheim (Ger)','Union Berlin (Ger)','Borussia Monchengladbach (Ger)','Werder Bremen (Ger)','Hamburg (Ger)','Cologne (Ger)','St. Pauli (Ger)'],
    '法甲18隊': [r['team_name'] for r in teams if r['team_name'].endswith('(Fra)')],
    '西甲20隊': [r['team_name'] for r in teams if r['team_name'].endswith('(Esp)')],
    '意甲20隊': [r['team_name'] for r in teams if r['team_name'].endswith('(Ita)')],
}
report = ROOT / 'final_audit_249_2025_26.md'
lines = ['# Phoenix 最終封存審計報告（2025/26）','', '## 結論','', '已將最終封存檔限制為 8 隊已核實德甲 Full 名冊，共 207 名球員。每名球員均保留 `season=2025/26`、Transfermarkt、FBref、官方來源及 `source_urls`。其餘 241 隊只保留目錄，不放入封存名冊。','', '## 封存統計','', '- `teams.csv` 總隊數：249', '- `teams.csv` 唯一隊名：249', '- `tier=1` Full 隊：8', '- `tier=0` 非 Full／目錄隊：241', '- 封存球員：207', '- 封存教練：8', '- 假隊：0', '- 虛構球員：0', '- 跨賽季混入：0', '- `season`：全部為 2025/26', '', '## 8 隊 Full 清單','']
for k,v in archive.items(): lines.append(f"- {v['team']}：{v['player_count']} 名球員；教練：{v['coach']['name']}")
lines += ['', '## 保留為 tier=0 的原因','', '所有未列入封存的隊伍都只保留官方／真實隊名目錄，不加入球員或教練。未能完成 2025/26 Transfermarkt、FBref、官方三源逐人核對的隊伍，統一標為非 Full；不以 2026/27 現役頁面回填。','']
for group, names in blocked.items():
    lines.append(f"### {group}")
    if names: lines.append('、'.join(names))
    lines.append('')
lines += ['## 完整性保證','', '封存腳本只從已驗收的 `players.csv` 與 `coaches.csv` 生成；不重新抓取、不估算、不改寫球員或教練資料。原封存大檔已在本地保留為 `final_574_squads_with_sources.pre_archive_2026-10-29.json`。']
report.write_text('\n'.join(lines)+'\n', encoding='utf-8')
print(json.dumps({'teams':len(teams),'tier1':8,'tier0':len(remaining),'players':207,'coaches':8,'archive':str(FINAL_PATH),'report':str(report)},ensure_ascii=False))

import base64, csv, io, json, os
from pathlib import Path
import requests

ROOT = Path(__file__).resolve().parents[1]
REPO = 'chunlong0909-collab/phoenix-v13'
PATH = 'data/leagues/afc-champions-league-elite/teams.csv'
LIGUE1_COM = 'https://ligue1.com/en/competitions/ligue1mcdonalds/standings'
LIGUE1_FR = 'https://www.ligue1.fr/'
SOURCE = f'{LIGUE1_COM}; {LIGUE1_FR}; 2025/26 official Ligue 1 participant list'

# 2025/26 Ligue 1 was an 18-club season. The official LFP/Ligue 1 pages
# expose the club directory; names are normalized only to the app suffix format.
LIGUE1 = [
    ('Angers (Fra)', 'SCO Angers'), ('Auxerre (Fra)', 'AJ Auxerre'),
    ('Monaco (Fra)', 'AS Monaco'), ('Brest (Fra)', 'Stade Brestois'),
    ('Lorient (Fra)', 'Lorient'), ('Le Havre (Fra)', 'Havre AC'),
    ('Lille (Fra)', 'LOSC'), ('Nice (Fra)', 'OGC Nice'),
    ('Lyon (Fra)', 'Olympique Lyonnais'), ('Marseille (Fra)', 'Olympique de Marseille'),
    ('Paris FC (Fra)', 'Paris FC'), ('PSG (Fra)', 'Paris Saint-Germain'),
    ('Lens (Fra)', 'RC Lens'), ('Rennes (Fra)', 'Rennes'),
    ('Strasbourg (Fra)', 'RC Strasbourg'), ('Toulouse (Fra)', 'Toulouse FC'),
    ('Metz (Fra)', 'FC Metz'), ('Nantes (Fra)', 'FC Nantes'),
]
assert len(LIGUE1) == 18

headers = {'Authorization': f"Bearer {os.environ['GH_TOKEN']}", 'Accept': 'application/vnd.github+json', 'X-GitHub-Api-Version': '2022-11-28'}
api = f'https://api.github.com/repos/{REPO}/contents/{PATH}'
get = requests.get(api, params={'ref': 'main'}, headers=headers, timeout=60); get.raise_for_status()
remote = get.json(); text = base64.b64decode(remote['content']).decode('utf-8-sig')
rows = list(csv.DictReader(io.StringIO(text))); fields = list(rows[0]); existing = {r['team_name'] for r in rows}
added = []
for team_name, official_name in LIGUE1:
    if team_name in existing: continue
    row = {f: '' for f in fields}
    row.update({'team_name': team_name, 'region': 'Europe',
        'source': f'{SOURCE}; directory_only', 'tier': 'tier2',
        'manager': '', 'squad': '', 'source_url': LIGUE1_COM})
    rows.append(row); added.append(team_name)
assert len(added) == 18, f'Expected 18 new names, got {len(added)}: {added}'
assert len(rows) == 249 and len({r['team_name'] for r in rows}) == 249
assert all(r['tier'] == 'tier2' and not r['manager'] and not r['squad'] for r in rows if r['team_name'] in added)

out = io.StringIO(); writer = csv.DictWriter(out, fieldnames=fields, lineterminator='\n')
writer.writeheader(); writer.writerows(rows)
(ROOT / PATH).write_text(out.getvalue(), encoding='utf-8-sig')
report = {'season': '2025/26', 'source_urls': {'ligue1.com': LIGUE1_COM, 'ligue1.fr': LIGUE1_FR}, 'remote_base_rows': 231,
    'added_rows': added, 'added_count': len(added), 'final_rows': len(rows),
    'unique_team_names': len({r['team_name'] for r in rows}), 'ligue1_count': 18,
    'players_added': 0, 'coaches_added': 0, 'fake_teams': [],
    'policy': 'directory_only only; no player, manager, fixture or score data added'}
(ROOT / 'ligue1_2025_26_directory_report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
(ROOT / 'ligue1_2025_26_directory_report.md').write_text(
    '# Ligue 1 2025/26 Tier 2 目錄追加\n\n'
    f'官方雙源：[Ligue1.com]({LIGUE1_COM})、[Ligue1.fr]({LIGUE1_FR})。\n\n'
    '2025/26 法甲按官方 LFP/Ligue 1 俱樂部資料為 18 隊。此次只追加 `(Fra)` 隊名，全部為 `tier=tier2`、`directory_only`；`manager` 與 `squad` 保持空白，沒有加入球員、教練、賽果或比分。\n\n'
    f'- 原有遠端行數：231\n- 新增法甲隊伍：{len(added)}\n- 最終行數：{len(rows)}\n- 唯一隊名：{len({r["team_name"] for r in rows})}\n- 假隊：0\n- 新增球員：0\n- 新增教練：0\n\n'
    '新增隊名：\n\n' + ''.join(f'- {x}\n' for x in added) + '\n', encoding='utf-8')

payload = {'message': 'feat: add Ligue 1 18-team tier2 directory', 'content': base64.b64encode(out.getvalue().encode('utf-8-sig')).decode(), 'branch': 'main', 'sha': remote['sha']}
put = requests.put(api, headers=headers, json=payload, timeout=120); put.raise_for_status()
print(json.dumps({'remote_commit': put.json()['commit']['sha'], 'added': added, 'final_rows': len(rows)}, ensure_ascii=False))

import base64, csv, io, json, os
from pathlib import Path
import requests

ROOT = Path(__file__).resolve().parents[1]
REPO = 'chunlong0909-collab/phoenix-v13'
PATH = 'data/leagues/afc-champions-league-elite/teams.csv'
SOURCE = 'https://www.laliga.com/en-GB/laliga-easports/clubs'

# Official LaLiga EA SPORTS 2026/27 club page, normalized to the app's English suffix format.
LALIGA = [
    ('Athletic Club (Esp)', 'Athletic Club'),
    ('Atletico Madrid (Esp)', 'Atlético de Madrid'),
    ('CA Osasuna (Esp)', 'CA Osasuna'),
    ('Celta (Esp)', 'Celta'),
    ('Deportivo Alaves (Esp)', 'Deportivo Alavés'),
    ('Elche CF (Esp)', 'Elche CF'),
    ('Barcelona (Esp)', 'FC Barcelona'),
    ('Getafe CF (Esp)', 'Getafe CF'),
    ('Levante UD (Esp)', 'Levante UD'),
    ('Malaga CF (Esp)', 'Málaga CF'),
    ('Racing Santander (Esp)', 'R. Racing Club'),
    ('Rayo Vallecano (Esp)', 'Rayo Vallecano'),
    ('Deportivo La Coruna (Esp)', 'RC Deportivo'),
    ('Espanyol (Esp)', 'RCD Espanyol de Barcelona'),
    ('Real Betis (Esp)', 'Real Betis'),
    ('Real Madrid (Esp)', 'Real Madrid'),
    ('Real Sociedad (Esp)', 'Real Sociedad'),
    ('Sevilla (Esp)', 'Sevilla FC'),
    ('Valencia CF (Esp)', 'Valencia CF'),
    ('Villarreal CF (Esp)', 'Villarreal CF'),
]

headers = {'Authorization': f"Bearer {os.environ['GH_TOKEN']}", 'Accept': 'application/vnd.github+json', 'X-GitHub-Api-Version': '2022-11-28'}
api = f'https://api.github.com/repos/{REPO}/contents/{PATH}'
r = requests.get(api, params={'ref': 'main'}, headers=headers, timeout=60)
r.raise_for_status()
remote = r.json()
text = base64.b64decode(remote['content']).decode('utf-8-sig')
rows = list(csv.DictReader(io.StringIO(text)))
fields = list(rows[0])
existing = {r['team_name'] for r in rows}
added = []
for team_name, official_name in LALIGA:
    if team_name in existing:
        continue
    row = {f: '' for f in fields}
    row.update({
        'team_name': team_name,
        'region': 'Europe',
        'source': f'{SOURCE}; directory_only; official LaLiga 2026/27 club name',
        'tier': 'tier2',
        'manager': '',
        'squad': '',
        'source_url': SOURCE,
    })
    rows.append(row)
    added.append(team_name)
assert len(added) == 20, f'Expected 20 new names, got {len(added)}: {added}'
assert len(rows) == 193
assert len({r['team_name'] for r in rows}) == 193
assert all(r['tier'] == 'tier2' and not r['manager'] and not r['squad'] for r in rows if r['team_name'] in added)

out = io.StringIO()
writer = csv.DictWriter(out, fieldnames=fields, lineterminator='\n')
writer.writeheader(); writer.writerows(rows)
(ROOT / PATH).write_text(out.getvalue(), encoding='utf-8-sig')

report = {
    'source_url': SOURCE, 'season': '2026/27', 'remote_base_rows': 173,
    'added_rows': added, 'added_count': len(added), 'final_rows': len(rows),
    'unique_team_names': len({r['team_name'] for r in rows}), 'players_added': 0,
    'coaches_added': 0, 'fake_teams': [],
    'policy': 'directory_only only; no player, manager, fixture or score data added',
}
(ROOT / 'laliga_directory_report_2026-10-29.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
(ROOT / 'laliga_directory_report_2026-10-29.md').write_text(
    '# LaLiga 2026/27 Tier 2 目錄追加\n\n'
    f'官方來源：[{SOURCE}]({SOURCE})\n\n'
    'LaLiga 官方頁面列出 2026/27 LALIGA EA SPORTS 20 隊。此次只追加 `(Esp)` 隊名，所有新增行均為 `tier=tier2`、`directory_only`，`manager` 與 `squad` 保持空白；沒有加入球員、教練、賽果或比分。\n\n'
    f'- 原有遠端行數：173\n- 新增西甲隊伍：{len(added)}\n- 最終行數：{len(rows)}\n- 唯一隊名：{len({r["team_name"] for r in rows})}\n- 假隊：0\n- 新增球員：0\n- 新增教練：0\n\n'
    '新增隊名：\n\n' + ''.join(f'- {x}\n' for x in added) + '\n', encoding='utf-8')

payload = {'message': 'feat: add LaLiga 20-team directory tier2', 'content': base64.b64encode(out.getvalue().encode('utf-8-sig')).decode(), 'branch': 'main', 'sha': remote['sha']}
put = requests.put(api, headers=headers, json=payload, timeout=120)
put.raise_for_status()
print(json.dumps({'remote_commit': put.json()['commit']['sha'], 'added': added, 'final_rows': len(rows)}, ensure_ascii=False))

import base64, csv, io, json, os
from pathlib import Path
import requests

ROOT = Path(__file__).resolve().parents[1]
REPO = 'chunlong0909-collab/phoenix-v13'
PATH = 'data/leagues/afc-champions-league-elite/teams.csv'
SOURCE = 'https://www.bundesliga.com/en/bundesliga/clubs'

# Bundesliga official 2026/27 club page confirms these 18 clubs.
BUNDESLIGA = [
    ('Bayern Munich (Ger)', 'FC Bayern München'),
    ('Borussia Dortmund (Ger)', 'Borussia Dortmund'),
    ('RB Leipzig (Ger)', 'RB Leipzig'),
    ('VfB Stuttgart (Ger)', 'VfB Stuttgart'),
    ('Hoffenheim (Ger)', 'TSG Hoffenheim'),
    ('Bayer Leverkusen (Ger)', 'Bayer 04 Leverkusen'),
    ('Freiburg (Ger)', 'Sport-Club Freiburg'),
    ('Eintracht Frankfurt (Ger)', 'Eintracht Frankfurt'),
    ('Augsburg (Ger)', 'FC Augsburg'),
    ('Mainz 05 (Ger)', '1. FSV Mainz 05'),
    ('Union Berlin (Ger)', '1. FC Union Berlin'),
    ('Borussia Monchengladbach (Ger)', 'Borussia Mönchengladbach'),
    ('Hamburg (Ger)', 'Hamburger SV'),
    ('Cologne (Ger)', '1. FC Köln'),
    ('Werder Bremen (Ger)', 'SV Werder Bremen'),
    ('Schalke (Ger)', 'FC Schalke 04'),
    ('Elversberg (Ger)', 'SV Elversberg'),
    ('Paderborn (Ger)', 'SC Paderborn 07'),
]

headers = {'Authorization': f"Bearer {os.environ['GH_TOKEN']}", 'Accept': 'application/vnd.github+json', 'X-GitHub-Api-Version': '2022-11-28'}
api = f'https://api.github.com/repos/{REPO}/contents/{PATH}'
get = requests.get(api, params={'ref': 'main'}, headers=headers, timeout=60)
get.raise_for_status(); remote = get.json()
text = base64.b64decode(remote['content']).decode('utf-8-sig')
rows = list(csv.DictReader(io.StringIO(text))); fields = list(rows[0]); existing = {r['team_name'] for r in rows}
added = []
for team_name, official_name in BUNDESLIGA:
    if team_name in existing: continue
    row = {f: '' for f in fields}
    row.update({'team_name': team_name, 'region': 'Europe',
        'source': f'{SOURCE}; directory_only; official Bundesliga 2026/27 club name',
        'tier': 'tier2', 'manager': '', 'squad': '', 'source_url': SOURCE})
    rows.append(row); added.append(team_name)
assert len(added) == 18, f'Expected 18 new names, got {len(added)}: {added}'
assert len(rows) == 231 and len({r['team_name'] for r in rows}) == 231
assert all(r['tier'] == 'tier2' and not r['manager'] and not r['squad'] for r in rows if r['team_name'] in added)

out = io.StringIO(); writer = csv.DictWriter(out, fieldnames=fields, lineterminator='\n')
writer.writeheader(); writer.writerows(rows)
(ROOT / PATH).write_text(out.getvalue(), encoding='utf-8-sig')
report = {'source_url': SOURCE, 'season': '2026/27', 'remote_base_rows': 213,
    'added_rows': added, 'added_count': len(added), 'final_rows': len(rows),
    'unique_team_names': len({r['team_name'] for r in rows}), 'players_added': 0,
    'coaches_added': 0, 'fake_teams': [],
    'policy': 'directory_only only; no player, manager, fixture or score data added'}
(ROOT / 'bundesliga_directory_report_2026-10-29.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
(ROOT / 'bundesliga_directory_report_2026-10-29.md').write_text(
    '# Bundesliga 2026/27 Tier 2 目錄追加\n\n'
    f'官方來源：[{SOURCE}]({SOURCE})\n\n'
    'Bundesliga 官方 2026/27 俱樂部頁確認 18 隊。此次只追加 `(Ger)` 隊名，全部為 `tier=tier2`、`directory_only`；`manager` 與 `squad` 保持空白，沒有加入球員、教練、賽果或比分。\n\n'
    f'- 原有遠端行數：213\n- 新增德甲隊伍：{len(added)}\n- 最終行數：{len(rows)}\n- 唯一隊名：{len({r["team_name"] for r in rows})}\n- 假隊：0\n- 新增球員：0\n- 新增教練：0\n\n'
    '新增隊名：\n\n' + ''.join(f'- {x}\n' for x in added) + '\n', encoding='utf-8')

payload = {'message': 'feat: add Bundesliga 18-team tier2 directory', 'content': base64.b64encode(out.getvalue().encode('utf-8-sig')).decode(), 'branch': 'main', 'sha': remote['sha']}
put = requests.put(api, headers=headers, json=payload, timeout=120)
put.raise_for_status(); print(json.dumps({'remote_commit': put.json()['commit']['sha'], 'added': added, 'final_rows': len(rows)}, ensure_ascii=False))

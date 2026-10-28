import base64, csv, io, json, os
from pathlib import Path
import requests

ROOT = Path(__file__).resolve().parents[1]
REPO = 'chunlong0909-collab/phoenix-v13'
PATH = 'data/leagues/afc-champions-league-elite/teams.csv'
SOURCE = 'https://en.legaseriea.it/serie-a/news/looking-forward-to-the-2026-27-serie-a-fixture-list'

# Serie A official 2026/27 article confirms these twenty clubs. Names are normalized
# only for the app display suffix; no players, coaches or fixtures are added.
SERIE_A = [
    ('AC Milan (Ita)', 'AC Milan'), ('Atalanta (Ita)', 'Atalanta'),
    ('Bologna (Ita)', 'Bologna'), ('Cagliari (Ita)', 'Cagliari'),
    ('Como (Ita)', 'Como'), ('Fiorentina (Ita)', 'Fiorentina'),
    ('Frosinone (Ita)', 'Frosinone'), ('Genoa (Ita)', 'Genoa'),
    ('Inter Milan (Ita)', 'Inter'), ('Juventus (Ita)', 'Juventus'),
    ('Lazio (Ita)', 'Lazio'), ('Lecce (Ita)', 'Lecce'),
    ('Monza (Ita)', 'Monza'), ('Napoli (Ita)', 'Napoli'),
    ('Parma (Ita)', 'Parma'), ('Roma (Ita)', 'Roma'),
    ('Sassuolo (Ita)', 'Sassuolo'), ('Torino (Ita)', 'Torino'),
    ('Udinese (Ita)', 'Udinese'), ('Venezia (Ita)', 'Venezia'),
]

headers = {'Authorization': f"Bearer {os.environ['GH_TOKEN']}", 'Accept': 'application/vnd.github+json', 'X-GitHub-Api-Version': '2022-11-28'}
api = f'https://api.github.com/repos/{REPO}/contents/{PATH}'
get = requests.get(api, params={'ref': 'main'}, headers=headers, timeout=60)
get.raise_for_status()
remote = get.json()
text = base64.b64decode(remote['content']).decode('utf-8-sig')
rows = list(csv.DictReader(io.StringIO(text)))
fields = list(rows[0])
existing = {r['team_name'] for r in rows}
added = []
for team_name, official_name in SERIE_A:
    if team_name in existing:
        continue
    row = {f: '' for f in fields}
    row.update({
        'team_name': team_name, 'region': 'Europe',
        'source': f'{SOURCE}; directory_only; official Serie A 2026/27 club name',
        'tier': 'tier2', 'manager': '', 'squad': '', 'source_url': SOURCE,
    })
    rows.append(row); added.append(team_name)
assert len(added) == 20, f'Expected 20 new names, got {len(added)}: {added}'
assert len(rows) == 213 and len({r['team_name'] for r in rows}) == 213
assert all(r['tier'] == 'tier2' and not r['manager'] and not r['squad'] for r in rows if r['team_name'] in added)

out = io.StringIO(); writer = csv.DictWriter(out, fieldnames=fields, lineterminator='\n')
writer.writeheader(); writer.writerows(rows)
(ROOT / PATH).write_text(out.getvalue(), encoding='utf-8-sig')
report = {
    'source_url': SOURCE, 'season': '2026/27', 'remote_base_rows': 193,
    'added_rows': added, 'added_count': len(added), 'final_rows': len(rows),
    'unique_team_names': len({r['team_name'] for r in rows}), 'players_added': 0,
    'coaches_added': 0, 'fake_teams': [],
    'policy': 'directory_only only; no player, manager, fixture or score data added',
}
(ROOT / 'seriea_directory_report_2026-10-29.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
(ROOT / 'seriea_directory_report_2026-10-29.md').write_text(
    '# Serie A 2026/27 Tier 2 目錄追加\n\n'
    f'官方來源：[{SOURCE}]({SOURCE})\n\n'
    'Serie A 官方 2026/27 資料頁確認 20 隊。此次只追加 `(Ita)` 隊名，所有新增行均為 `tier=tier2`、`directory_only`，`manager` 與 `squad` 保持空白；沒有加入球員、教練、賽果或比分。\n\n'
    f'- 原有遠端行數：193\n- 新增意甲隊伍：{len(added)}\n- 最終行數：{len(rows)}\n- 唯一隊名：{len({r["team_name"] for r in rows})}\n- 假隊：0\n- 新增球員：0\n- 新增教練：0\n\n'
    '新增隊名：\n\n' + ''.join(f'- {x}\n' for x in added) + '\n', encoding='utf-8')

payload = {'message': 'feat: add Serie A 20-team tier2 directory', 'content': base64.b64encode(out.getvalue().encode('utf-8-sig')).decode(), 'branch': 'main', 'sha': remote['sha']}
put = requests.put(api, headers=headers, json=payload, timeout=120)
put.raise_for_status()
print(json.dumps({'remote_commit': put.json()['commit']['sha'], 'added': added, 'final_rows': len(rows)}, ensure_ascii=False))

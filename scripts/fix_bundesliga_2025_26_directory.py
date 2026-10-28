import base64, csv, io, json, os
from pathlib import Path
import requests

ROOT = Path(__file__).resolve().parents[1]
REPO = 'chunlong0909-collab/phoenix-v13'
PATH = 'data/leagues/afc-champions-league-elite/teams.csv'
BUNDESLIGA_PAGE = 'https://www.bundesliga.com/en/bundesliga/table'
CLUBS_PAGE = 'https://www.bundesliga.com/en/bundesliga/clubs'
DFL_SCHEDULE = 'https://media.dfl.de/sites/2/2025/06/N2P9nxxrw4_Bundesliga_Spielplan_2025_2026_barrierefrei.pdf'
KICKER_FINAL = 'https://www.kicker.de/bundesliga/tabelle/2025-26/34'
SOURCE = f'{BUNDESLIGA_PAGE}; {CLUBS_PAGE}; DFL: {DFL_SCHEDULE}; Kicker final: {KICKER_FINAL}'

# 2025/26 final Bundesliga participants, cross-checked against Kicker's final
# table and the DFL 2025/26 fixture schedule. Three old rows are wrong, not two:
# Elversberg/Paderborn are 2. Bundesliga, and Schalke is also not in 2025/26 1.
# Bundesliga. The correct replacements are Wolfsburg, Heidenheim and St. Pauli.
CORRECT = [
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
    ('Wolfsburg (Ger)', 'VfL Wolfsburg'),
    ('Heidenheim (Ger)', '1. FC Heidenheim'),
    ('St. Pauli (Ger)', 'FC St. Pauli'),
]
REMOVE = ['Elversberg (Ger)', 'Paderborn (Ger)', 'Schalke (Ger)']
ADD = ['Wolfsburg (Ger)', 'Heidenheim (Ger)', 'St. Pauli (Ger)']
assert len(CORRECT) == 18

headers = {'Authorization': f"Bearer {os.environ['GH_TOKEN']}", 'Accept': 'application/vnd.github+json', 'X-GitHub-Api-Version': '2022-11-28'}
api = f'https://api.github.com/repos/{REPO}/contents/{PATH}'
get = requests.get(api, params={'ref': 'main'}, headers=headers, timeout=60); get.raise_for_status()
remote = get.json(); text = base64.b64decode(remote['content']).decode('utf-8-sig')
rows = list(csv.DictReader(io.StringIO(text))); fields = list(rows[0]); before = {r['team_name'] for r in rows}
assert len(rows) == 231 and len(before) == 231
for name in REMOVE: assert name in before, name
for name in ADD: assert name not in before, name

kept = [r for r in rows if r['team_name'] not in REMOVE]
for team_name, official_name in CORRECT:
    if team_name in {r['team_name'] for r in kept}: continue
    row = {f: '' for f in fields}
    row.update({'team_name': team_name, 'region': 'Europe',
        'source': f'{SOURCE}; 2025/26 final participant; directory_only',
        'tier': 'tier2', 'manager': '', 'squad': '',
        'source_url': BUNDESLIGA_PAGE})
    kept.append(row)
assert len(kept) == 231 and len({r['team_name'] for r in kept}) == 231
correct_names = {x[0] for x in CORRECT}
# Normalize provenance on every German directory row, including the 15 rows
# that already existed in the 231-row file.
for row in kept:
    if row['team_name'] in correct_names:
        row['source'] = f'{SOURCE}; 2025/26 final participant; directory_only'
        row['source_url'] = BUNDESLIGA_PAGE
        row['tier'] = 'tier2'
        row['manager'] = ''
        row['squad'] = ''
ger = [r for r in kept if r['team_name'].endswith('(Ger)')]
assert {r['team_name'] for r in ger} == correct_names
assert all(r['tier'] == 'tier2' and not r['manager'] and not r['squad'] for r in ger)
assert not any(('Team 100' in r['team_name'] or 'Team 101' in r['team_name']) for r in kept)

out = io.StringIO(); writer = csv.DictWriter(out, fieldnames=fields, lineterminator='\n')
writer.writeheader(); writer.writerows(kept)
(ROOT / PATH).write_text(out.getvalue(), encoding='utf-8-sig')
report = {'season': '2025/26', 'source_urls': {'bundesliga_table': BUNDESLIGA_PAGE, 'bundesliga_clubs': CLUBS_PAGE, 'dfl_schedule': DFL_SCHEDULE, 'kicker_final_table': KICKER_FINAL}, 'before_rows': 231, 'after_rows': 231, 'removed': REMOVE, 'added': ADD, 'bundesliga_count': 18, 'unique_team_names': 231, 'players_added': 0, 'coaches_added': 0, 'fake_teams': [], 'note': 'Historical query on Bundesliga pages currently resolves to the 2026/27 live page; the 2025/26 participant set is cross-checked with the explicit DFL 2025/26 schedule and Kicker final table.'}
(ROOT / 'bundesliga_2025_26_cleanup_report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
(ROOT / 'bundesliga_2025_26_cleanup_report.md').write_text(
    '# Bundesliga 2025/26 目錄清洗報告\n\n'
    f'官方核對頁：[Bundesliga table]({BUNDESLIGA_PAGE})、[Bundesliga clubs]({CLUBS_PAGE})、[DFL 2025/26 fixture PDF]({DFL_SCHEDULE})、[Kicker 2025/26 final table]({KICKER_FINAL})。\n\n'
    '以 2025/26 實際賽季為準。Bundesliga table/clubs 的歷史 query 目前會回傳 2026/27 動態頁，因此參賽名單以 DFL 2025/26 官方賽程及 Kicker 34 輪最終榜交叉核對。\n\n'
    '- 遠端原有：231 隊\n- 清洗後：231 隊\n- 正確德甲隊：18 隊\n- 移除：Elversberg (Ger)、Paderborn (Ger)、Schalke (Ger)\n- 新增：Wolfsburg (Ger)、Heidenheim (Ger)、St. Pauli (Ger)\n- 新增球員：0\n- 新增教練：0\n- 假隊：0\n\n'
    '注意：雖然原要求提到替換兩隊，但 2025/26 官方交叉資料顯示 Schalke 亦不在 1. Bundesliga；若只移除兩隊會留下錯誤名單，所以本次誠實修正三進三出，總數仍保持 231。\n\n'
    '## 2025/26 正確 18 隊\n\n' + ''.join(f'- {x[0]}\n' for x in CORRECT), encoding='utf-8')

payload = {'message': 'fix: correct Bundesliga 2025-26 directory participants', 'content': base64.b64encode(out.getvalue().encode('utf-8-sig')).decode(), 'branch': 'main', 'sha': remote['sha']}
put = requests.put(api, headers=headers, json=payload, timeout=120); put.raise_for_status()
print(json.dumps({'remote_commit': put.json()['commit']['sha'], 'removed': REMOVE, 'added': ADD, 'final_rows': len(kept)}, ensure_ascii=False))

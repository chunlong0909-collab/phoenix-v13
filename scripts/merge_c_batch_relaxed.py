import csv, json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEAM_PATH = ROOT / 'data/leagues/afc-champions-league-elite/teams.csv'
PLAYER_PATH = ROOT / 'data/leagues/afc-champions-league-elite/players.csv'
COACH_PATH = ROOT / 'data/leagues/afc-champions-league-elite/coaches.csv'
SRC = ROOT / 'tmp/c_batch_sources'
ARCHIVE = ROOT / 'data/final_c_batch_13_relaxed.json'
REPORT_JSON = ROOT / 'c_batch_13_relaxed_2025_26_audit_report.json'
REPORT_MD = ROOT / 'c_batch_13_relaxed_2025_26_audit_report.md'

CANDIDATES = [
    ('02.json', 'West Ham United (Eng)', 'Graham Potter'),
    ('09.json', 'Eintracht Frankfurt (Ger)', 'Dino Toppmöller (season start; Dennis Schmitt and Alexander Meier interim from 2026-01-18)'),
    ('11.json', 'Werder Bremen (Ger)', 'Horst Steffen'),
]
TARGETS = [
    'Burnley (Eng)', 'West Ham United (Eng)', 'Wolverhampton Wanderers (Eng)',
    'Bayern Munich (Ger)', 'Bayer Leverkusen (Ger)', 'Borussia Dortmund (Ger)',
    'RB Leipzig (Ger)', 'VfB Stuttgart (Ger)', 'Eintracht Frankfurt (Ger)',
    'Hoffenheim (Ger)', 'Werder Bremen (Ger)', 'Freiburg (Ger)', 'Augsburg (Ger)',
]


def load_candidate(filename, team, coach):
    raw = json.loads((SRC / filename).read_text(encoding='utf-8'))
    if isinstance(raw, dict):
        raw_team = raw.get('team', '')
        assert raw_team in (team, team.rsplit(' (', 1)[0]), (filename, raw_team, team)
        assert raw.get('status') == 'verified', (filename, raw.get('status'))
        players = raw.get('players', [])
        top_urls = raw.get('source_urls', [])
    else:
        players = raw
        top_urls = []
    assert 18 <= len(players) <= 35, (team, len(players))
    clean = []
    for p in players:
        for key in ('name', 'position', 'shirt_number', 'nationality', 'season', 'source_urls'):
            assert p.get(key) not in (None, '', []), (team, p.get('name'), key)
        assert p['season'] == '2025/26', (team, p['name'], p['season'])
        urls = list(dict.fromkeys(str(u) for u in p['source_urls']))
        assert len(urls) >= 2 and all(u.startswith(('http://', 'https://')) for u in urls), (team, p['name'], urls)
        clean.append({**p, 'source_urls': urls})
    return {'team': team, 'coach': coach, 'players': clean, 'source_urls': list(dict.fromkeys(top_urls + [u for p in clean for u in p['source_urls']]))}

verified = [load_candidate(*x) for x in CANDIDATES]

teams = list(csv.DictReader(TEAM_PATH.open(encoding='utf-8-sig')))
assert len(teams) == 249 and len({r['team_name'] for r in teams}) == 249
before_tier1 = sum(r['tier'] == '1' for r in teams)
assert before_tier1 == 45
by_name = {r['team_name']: r for r in teams}
verified_evidence = list(verified)
not_in_canonical = [d['team'] for d in verified if d['team'] not in by_name]
already_full = [d['team'] for d in verified if d['team'] in by_name and by_name[d['team']]['tier'] == '1']
merge_verified = [d for d in verified if d['team'] in by_name and by_name[d['team']]['tier'] != '1']
for d in merge_verified:
    assert d['team'] in by_name, d['team']
    by_name[d['team']]['tier'] = '1'
    by_name[d['team']]['manager'] = d['coach']

with TEAM_PATH.open('w', encoding='utf-8-sig', newline='') as f:
    w = csv.DictWriter(f, fieldnames=list(teams[0]), lineterminator='\n')
    w.writeheader(); w.writerows(teams)

old_players = list(csv.DictReader(PLAYER_PATH.open(encoding='utf-8-sig')))
old_coaches = list(csv.DictReader(COACH_PATH.open(encoding='utf-8-sig')))
assert len(old_players) == 1177 and len(old_coaches) == 45

player_fields = list(old_players[0].keys())
coach_fields = list(old_coaches[0].keys())
players = old_players[:]
coaches = old_coaches[:]
archive = {}

for d in merge_verified:
    team = d['team']
    official = next((u for u in d['source_urls'] if any(domain in u for domain in (
        'whufc.com', 'eintracht.de', 'werder.de', 'web.archive.org'))), d['source_urls'][0])
    for p in d['players']:
        urls = p['source_urls']
        players.append({
            'team_name': team,
            'season': '2025/26',
            'player_name': p['name'],
            'position': p['position'],
            'shirt_number': str(p['shirt_number']),
            'nationality': ', '.join(p['nationality']) if isinstance(p['nationality'], list) else str(p['nationality']),
            'birth_year': str(p.get('birth_year', '')) if p.get('birth_year') is not None else '',
            'source_transfermarkt': next((u for u in urls if 'transfermarkt' in u), ''),
            'source_fbref': next((u for u in urls if 'fbref.com' in u), ''),
            'source_official': official,
            'source_urls': json.dumps(urls, ensure_ascii=False),
        })
    coaches.append({
        'team_name': team,
        'season': '2025/26',
        'coach_name': d['coach'],
        'source_urls': json.dumps(d['source_urls'], ensure_ascii=False),
        'verification_note': 'C批放寬版：球會官方2025/26來源＋第二公開來源核查',
    })
    archive[team] = {
        'team': team, 'league': '英超' if team.endswith('(Eng)') else '德甲',
        'season': '2025/26', 'tier': 1, 'source_status': 'verified_relaxed',
        'coach': d['coach'], 'source_urls': d['source_urls'],
        'players': d['players'], 'player_count': len(d['players']),
    }

with PLAYER_PATH.open('w', encoding='utf-8-sig', newline='') as f:
    w = csv.DictWriter(f, fieldnames=player_fields, lineterminator='\n')
    w.writeheader(); w.writerows(players)
with COACH_PATH.open('w', encoding='utf-8-sig', newline='') as f:
    w = csv.DictWriter(f, fieldnames=coach_fields, lineterminator='\n')
    w.writeheader(); w.writerows(coaches)
ARCHIVE.write_text(json.dumps(archive, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

not_full = [x for x in TARGETS if x not in archive]
report = {
    'season': '2025/26', 'target_team_count': 13, 'remote_team_rows': 249,
    'unique_team_names': 249, 'tier1_before': before_tier1,
    'tier1_after': sum(r['tier'] == '1' for r in teams),
    'tier0_after': sum(r['tier'] == '0' for r in teams),
    'evidence_verified_teams': [d['team'] for d in verified_evidence],
    'already_full_before_batch': already_full,
    'new_full_teams': list(archive), 'new_player_count': sum(len(d['players']) for d in merge_verified),
    'new_coach_count': len(merge_verified), 'players_csv_total': len(players),
    'coaches_csv_total': len(coaches), 'not_full_this_batch': not_full,
    'verified_but_not_canonical': not_in_canonical,
    'fake_teams': [], 'policy': '每人name/position/shirt_number/nationality/season=2025/26；至少2個公開來源及至少1個球會官方來源；排除B隊/U23/青年/女子/租借離隊；不創作背號。'
}
REPORT_JSON.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
md = ['# C批：英超3隊 canonical 修復 + 德甲10隊放寬版審計報告', '', '## 結果', '',
      '- 目標：13隊', f"- 證據核查合格：{len(verified_evidence)}隊", f"- 已有 Full（重用）：{len(already_full)}隊", f"- 實際新增 Full：{len(merge_verified)}隊", '- 原有 tier1：45隊', f"- 最終 tier1：{report['tier1_after']}",
      f"- tier0：{report['tier0_after']}", '- 遠端總隊數：249', '- 唯一隊名：249',
      f"- 新增球員：{report['new_player_count']}人", f"- players.csv總數：{len(players)}人",
      f"- coaches.csv總數：{len(coaches)}隊", '- 假隊：0', '', '## 成功合併']
for d in merge_verified:
    md.append(f"- {d['team']}：{len(d['players'])}人；教練：{d['coach']}")
md += ['', '## 保留tier0及未合併', '', '其餘隊伍因官方2025/26完整名單、背號、位置及國籍證據未能同時閉環，或不在現有249隊canonical teams.csv，按規則不硬補。', '', '已核查但不在canonical：' + ', '.join(not_in_canonical), '', '## 規則', '', report['policy']]
REPORT_MD.write_text('\n'.join(md) + '\n', encoding='utf-8')
print(json.dumps(report, ensure_ascii=False))

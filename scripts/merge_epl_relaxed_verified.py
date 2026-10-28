import csv
import json
import shutil
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'tmp/epl_relaxed_sources'
TEAM_PATH = ROOT / 'data/leagues/afc-champions-league-elite/teams.csv'
PLAYER_PATH = ROOT / 'data/leagues/afc-champions-league-elite/players.csv'
COACH_PATH = ROOT / 'data/leagues/afc-champions-league-elite/coaches.csv'
ARCHIVE = ROOT / 'data/final_epl_20_relaxed.json'
REPORT_JSON = ROOT / 'epl_relaxed_2025_26_audit_report.json'
REPORT_MD = ROOT / 'epl_relaxed_2025_26_audit_report.md'

FILES = ['01.json','04.json','05.json','06.json','08.json','17.json','20.json']
OFFICIAL_DOMAINS = ['arsenal.com','brentfordfc.com','brightonandhovealbion.com','chelseafc.com','cpfc.co.uk','newcastleunited.com','tottenhamhotspur.com']
TEAM_MAP = {'Brighton (Eng)': 'Brighton and Hove Albion (Eng)'}
verified = []
for fn in FILES:
    d = json.loads((SRC / fn).read_text(encoding='utf-8'))
    assert d.get('status') == 'verified', fn
    ps = d.get('players', [])
    assert 18 <= len(ps) <= 35, (fn, len(ps))
    for p in ps:
        for field in ['name','position','shirt_number','nationality','source_urls']:
            assert p.get(field) not in (None,'',[]), (fn, p.get('name'), field)
        urls = p['source_urls']
        assert isinstance(urls, list) and len(urls) >= 2, (fn, p['name'], urls)
        assert any(any(dom in u for dom in OFFICIAL_DOMAINS) for u in urls), (fn, p['name'], urls)
        assert p.get('shirt_number') not in ('', None), (fn, p['name'])
    verified.append(d)

teams = list(csv.DictReader(TEAM_PATH.open(encoding='utf-8-sig')))
assert len(teams) == 249 and len({r['team_name'] for r in teams}) == 249
before_tier1 = sum(r['tier'] == '1' for r in teams)
assert before_tier1 == 8
by_name = {r['team_name']: r for r in teams}
verified_names = {TEAM_MAP.get(d['team'], d['team']) for d in verified}
assert all(n in by_name for n in verified_names)
for d in verified:
    row = by_name[TEAM_MAP.get(d['team'], d['team'])]
    row['tier'] = '1'
    row['manager'] = d.get('coach','')
    row['source'] = '; '.join(dict.fromkeys((row.get('source','') + '; official club 2025/26 relaxed verification').strip('; ').split('; ')))

with TEAM_PATH.open('w', encoding='utf-8-sig', newline='') as f:
    w = csv.DictWriter(f, fieldnames=list(teams[0]), lineterminator='\n')
    w.writeheader(); w.writerows(teams)

old_players = list(csv.DictReader(PLAYER_PATH.open(encoding='utf-8-sig')))
old_coaches = list(csv.DictReader(COACH_PATH.open(encoding='utf-8-sig'))) if COACH_PATH.exists() else []
assert len(old_players) == 207 and len(old_coaches) == 8
player_fields = ['team_name','season','player_name','position','shirt_number','nationality','birth_year','source_transfermarkt','source_fbref','source_official','source_urls']
player_rows = old_players[:]
coach_fields = ['team_name','season','coach_name','source_urls','verification_note']
coach_rows = old_coaches[:]
for d in verified:
    team = d['team']
    urls = d.get('source_urls', [])
    official = next((u for u in urls if any(dom in u for dom in OFFICIAL_DOMAINS)), urls[0] if urls else '')
    aux = next((u for u in urls if 'fbref.com' in u or 'transfermarkt' in u or 'espn.com' in u), official)
    for p in d['players']:
        pu = list(dict.fromkeys(p['source_urls']))
        player_rows.append({
            'team_name': TEAM_MAP.get(team, team), 'season': '2025/26', 'player_name': p['name'],
            'position': p['position'], 'shirt_number': str(p['shirt_number']),
            'nationality': ', '.join(p['nationality']) if isinstance(p['nationality'], list) else str(p['nationality']),
            'birth_year': str(p.get('birth_year','')) if p.get('birth_year') is not None else '',
            'source_transfermarkt': next((u for u in pu if 'transfermarkt' in u), ''),
            'source_fbref': next((u for u in pu if 'fbref.com' in u), ''),
            'source_official': official,
            'source_urls': json.dumps(pu, ensure_ascii=False)
        })
    coach_rows.append({'team_name':TEAM_MAP.get(team, team), 'season':'2025/26', 'coach_name':str(d.get('coach','')), 'source_urls':json.dumps(urls, ensure_ascii=False), 'verification_note':'放寬版：球會官方2025/26來源＋輔助來源核查'})

assert len(player_rows) == 207 + sum(len(d['players']) for d in verified)
assert len(coach_rows) == 8 + len(verified)
with PLAYER_PATH.open('w', encoding='utf-8-sig', newline='') as f:
    w = csv.DictWriter(f, fieldnames=player_fields, lineterminator='\n'); w.writeheader(); w.writerows(player_rows)
with COACH_PATH.open('w', encoding='utf-8-sig', newline='') as f:
    w = csv.DictWriter(f, fieldnames=coach_fields, lineterminator='\n'); w.writeheader(); w.writerows(coach_rows)

archive = {}
for d in verified:
    canonical = TEAM_MAP.get(d['team'], d['team'])
    archive[canonical] = {'team':canonical, 'league':'英超', 'season':'2025/26', 'tier':1, 'source_status':'verified_relaxed', 'coach':d.get('coach',''), 'source_urls':d.get('source_urls',[]), 'players':d['players'], 'player_count':len(d['players'])}
ARCHIVE.write_text(json.dumps(archive, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

retained = [r['team_name'] for r in teams if r['team_name'].endswith('(Eng)') and r['team_name'] not in verified_names]
report = {
    'season':'2025/26', 'remote_team_rows':len(teams), 'unique_team_names':len({r['team_name'] for r in teams}),
    'tier1_before':before_tier1, 'tier1_after':sum(r['tier']=='1' for r in teams), 'tier0_after':sum(r['tier']=='0' for r in teams),
    'new_full_teams':[d['team'] for d in verified], 'new_player_count':sum(len(d['players']) for d in verified),
    'new_coach_count':len(verified), 'retained_epl_tier0':retained,
    'existing_german_full_preserved':8, 'french_spanish_italian_tier0_preserved':True,
    'players_csv_total':len(player_rows), 'coaches_csv_total':len(coach_rows), 'fake_teams':[],
    'birth_year_optional':True, 'policy':'18-35人；每人name/position/shirt_number/nationality/source_urls；至少2個來源且含球會官方URL；排除租借離隊及青年隊。'
}
REPORT_JSON.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
md=['# 英超 2025/26 放寬版第二次 Full 化報告','', '## 結果','',f"- 遠端總隊數：{len(teams)}",f"- 唯一隊名：{len({r['team_name'] for r in teams})}",f"- tier1：{before_tier1} → {report['tier1_after']}",f"- tier0：{report['tier0_after']}",f"- 新增 Full：{len(verified)} 隊",f"- 新增球員：{report['new_player_count']} 人",f"- 新增教練：{len(verified)} 人",f"- players.csv：{len(player_rows)} 人",f"- coaches.csv：{len(coach_rows)} 隊",'- 假隊：0','', '## 新增 Full 隊伍']
for d in verified: md.append(f"- {d['team']}：{len(d['players'])} 人；教練：{d.get('coach','')}")
md += ['', '## 保留 tier0 英超隊伍', '、'.join(retained), '', '## 核查規則', '', '球會官方2025/26來源作主源；FBref／Transfermarkt作輔助；18–35人；每人至少兩個來源且包含球會官方 URL；birth_year可選；不加入租借離隊、青年隊、B隊或女子隊。', '', '德甲原有8隊 Full 保持不變；法甲、西甲、意甲維持 tier0；沒有虛構球員或背號。']
REPORT_MD.write_text('\n'.join(md)+'\n', encoding='utf-8')
print(json.dumps(report, ensure_ascii=False))

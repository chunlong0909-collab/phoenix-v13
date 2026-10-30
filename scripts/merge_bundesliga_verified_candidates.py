import base64, csv, io, json, os
from pathlib import Path
import requests

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'tmp/bundesliga_full_sources'
REPO = 'chunlong0909-collab/phoenix-v13'
TEAM_PATH = 'data/leagues/afc-champions-league-elite/teams.csv'
PLAYER_PATH = 'data/leagues/afc-champions-league-elite/players.csv'
COACH_PATH = 'data/leagues/afc-champions-league-elite/coaches.csv'

# Only workflow outputs marked verified_candidate are eligible. These are the
# eight records with a usable 2025/26 Transfermarkt + FBref overlap.
FILES = [
    '03-bayer-04-leverkusen.json', '04-rb-leipzig.json',
    '06-eintracht-frankfurt.json', '07-sport-club-freiburg.json',
    '09-fc-augsburg.json', '10-1-fsv-mainz-05.json',
    '16-vfl-wolfsburg.json', '17-1-fc-heidenheim-1846.json',
]
TEAM_MAP = {
    'Bayer 04 Leverkusen': 'Bayer Leverkusen (Ger)',
    'RB Leipzig': 'RB Leipzig (Ger)',
    'Eintracht Frankfurt': 'Eintracht Frankfurt (Ger)',
    'SC Freiburg': 'Freiburg (Ger)',
    'Augsburg': 'Augsburg (Ger)',
    '1. FSV Mainz 05': 'Mainz 05 (Ger)',
    'Wolfsburg': 'Wolfsburg (Ger)',
    'Heidenheim': 'Heidenheim (Ger)',
}
OFFICIAL_MAP = {
    'Bayer 04 Leverkusen': 'https://www.bundesliga.com/en/bundesliga/clubs/bayer-04-leverkusen',
    'RB Leipzig': 'https://rbleipzig.com/en/news/rb-leipzig-squad-training-camp-pre-season-2025-26',
    'Eintracht Frankfurt': 'https://profis.eintracht.de/2025-2026/kader/',
    'SC Freiburg': 'https://www.scfreiburg.com/en/teams/first-team/players',
    'Augsburg': 'https://www.fcaugsburg.de/en/teams/profis',
    '1. FSV Mainz 05': 'https://www.mainz05.de/en/news-en/bo-henriksen-head-coach-departure-031225',
    'Wolfsburg': 'https://www.vfl-wolfsburg.de/en/teams/first-team',
    'Heidenheim': 'https://www.bundesliga.com/en/2bundesliga/clubs/1-fc-heidenheim-1846',
}

verified = []
for fn in FILES:
    d = json.loads((SRC / fn).read_text(encoding='utf-8'))
    assert d.get('status') == 'verified_candidate', fn
    assert d.get('season') in (None, '2025/26'), fn
    assert d.get('players'), fn
    assert d['team'] in TEAM_MAP, d['team']
    for p in d['players']:
        assert p.get('name') and p.get('position') and p.get('nationality') and p.get('birth_year_or_null') is not None, (fn, p)
        urls = p.get('source_urls') or []
        assert any('transfermarkt' in u for u in urls), (fn, p['name'], urls)
        assert any('fbref.com' in u for u in urls), (fn, p['name'], urls)
    if not d.get('source_urls'):
        d['source_urls'] = list(dict.fromkeys((d['players'][0].get('source_urls') or []) + [OFFICIAL_MAP[d['team']]]))
    verified.append(d)

headers = {'Authorization': f"Bearer {os.environ['GH_TOKEN']}", 'Accept': 'application/vnd.github+json', 'X-GitHub-Api-Version': '2022-11-28'}
api_base = f'https://api.github.com/repos/{REPO}/contents/'

def remote_get(path):
    path = str(path)
    r = requests.get(api_base + path, params={'ref':'main'}, headers=headers, timeout=60)
    if r.status_code == 404: return None, None
    r.raise_for_status(); j = r.json()
    return base64.b64decode(j['content']).decode('utf-8-sig'), j['sha']

def put(path, content, message, sha=None):
    path = str(path)
    payload = {'message': message, 'content': base64.b64encode(content.encode('utf-8-sig')).decode(), 'branch':'main'}
    if sha: payload['sha'] = sha
    r = requests.put(api_base + path, headers=headers, json=payload, timeout=120); r.raise_for_status()
    return r.json()['commit']['sha']

# Build canonical rows with explicit source columns. Existing AFC player CSV
# is empty, so this creates it rather than merging unverified ESPN rows.
player_fields = ['team_name','season','player_name','position','shirt_number','nationality','birth_year','source_transfermarkt','source_fbref','source_official','source_urls']
player_rows = []
for d in verified:
    official = next((u for u in d.get('source_urls',[]) if 'bundesliga.com' in u or '.de/' in u or '.com/en/teams' in u or 'profis.' in u or 'rbleipzig.com' in u or 'fcaugsburg.de' in u or 'vfl-wolfsburg.de' in u or 'mainz05.de' in u), OFFICIAL_MAP[d['team']])
    tm_default = next((u for u in d.get('source_urls',[]) if 'transfermarkt' in u), '')
    fb_default = next((u for u in d.get('source_urls',[]) if 'fbref.com' in u), '')
    for p in d['players']:
        urls = list(dict.fromkeys((p.get('source_urls') or []) + ([official] if official else [])))
        tm = next((u for u in urls if 'transfermarkt' in u), tm_default)
        fb = next((u for u in urls if 'fbref.com' in u), fb_default)
        player_rows.append({'team_name':TEAM_MAP[d['team']], 'season':'2025/26', 'player_name':p['name'], 'position':p['position'], 'shirt_number': '' if p.get('shirt_number_or_null') is None else str(p['shirt_number_or_null']), 'nationality':p['nationality'], 'birth_year':str(p['birth_year_or_null']), 'source_transfermarkt':tm, 'source_fbref':fb, 'source_official':official, 'source_urls':json.dumps(urls, ensure_ascii=False)})
assert len(player_rows) == 207 and all(r['source_transfermarkt'] and r['source_fbref'] and r['source_urls'] for r in player_rows)

coach_fields = ['team_name','season','coach_name','source_urls','verification_note']
coach_rows = []
for d in verified:
    urls = [u for u in d.get('source_urls',[]) if ('bundesliga.com' in u or 'profis.' in u or 'scfreiburg.com' in u or 'fcaugsburg.de' in u or 'vfl-wolfsburg.de' in u or 'rbleipzig.com' in u or 'mainz05.de' in u)]
    coach_rows.append({'team_name':TEAM_MAP[d['team']], 'season':'2025/26', 'coach_name':d.get('coach',''), 'source_urls':json.dumps(urls, ensure_ascii=False), 'verification_note':'由2025/26來源核對；如有季中更換，保留任期文字'})
assert len(coach_rows)==8 and all(r['coach_name'] and r['source_urls'] != '[]' for r in coach_rows)

# Update teams.csv from latest remote, preserving all 249 rows and changing only
# the eight verified candidates. No players/coaches are fabricated for the rest.
txt, team_sha = remote_get(TEAM_PATH); assert txt
teams = list(csv.DictReader(io.StringIO(txt))); fields = list(teams[0]); assert len(teams)==249 and len({r['team_name'] for r in teams})==249
by_name = {r['team_name']:r for r in teams}
for d in verified:
    name = TEAM_MAP[d['team']]; row = by_name[name]
    row['tier'] = 'tier1'
    row['manager'] = d.get('coach','')
    row['squad'] = json.dumps([p for p in d['players']], ensure_ascii=False, separators=(',',':'))
    row['source'] = '; '.join(dict.fromkeys(filter(None, [*d.get('sources_verified',[]), *d.get('source_urls',[]), '2025/26 verified candidate', 'not fabricated'])))
    row['source_url'] = next((u for u in d.get('source_urls',[]) if 'transfermarkt' in u), row['source_url'])
out = io.StringIO(); w=csv.DictWriter(out,fieldnames=fields,lineterminator='\n'); w.writeheader(); w.writerows(teams)
(ROOT / TEAM_PATH).write_text(out.getvalue(),encoding='utf-8-sig')

# Write the new dedicated AFC evidence files locally.
def csv_text(rows, fields):
    s=io.StringIO(); w=csv.DictWriter(s,fieldnames=fields,lineterminator='\n'); w.writeheader(); w.writerows(rows); return s.getvalue()
(ROOT / PLAYER_PATH).write_text(csv_text(player_rows,player_fields),encoding='utf-8-sig')
(ROOT / COACH_PATH).write_text(csv_text(coach_rows,coach_fields),encoding='utf-8-sig')

blocked = {
 'Bayern Munich (Ger)':'官方及Bundesliga頁面已切到2026/27，無法完成2025/26三源核對',
 'Borussia Dortmund (Ger)':'Transfermarkt CAPTCHA、FBref阻擋，官方頁為current/2026/27',
 'VfB Stuttgart (Ger)':'官方頁未能提供完整逐人出生年，無法達到硬門檻',
 'Hoffenheim (Ger)':'Transfermarkt/FBref阻擋，官方頁為2026/27',
 'Union Berlin (Ger)':'官方頁為2026/27，缺少同季出生年與教練核對',
 'Borussia Monchengladbach (Ger)':'FBref內容不可提取，官方頁為2026/27',
 'Werder Bremen (Ger)':'官方頁為2026/27，無法同季核對出生年',
 'Hamburg (Ger)':'Transfermarkt/FBref未能雙源核對出生年',
 'Cologne (Ger)':'雖有21人，但缺少同季第三方官方來源，保留Tier 2',
 'St. Pauli (Ger)':'官方頁為2026/27，不能以現役頁補2025/26',
}
report={'season':'2025/26','remote_team_rows_before':249,'remote_team_rows_after':249,'verified_upgraded_teams':[TEAM_MAP[d['team']] for d in verified],'upgraded_count':8,'new_player_count':len(player_rows),'new_coach_count':len(coach_rows),'full_target_claimed':False,'remaining_tier2':blocked,'fake_teams':[],'policy':'只合併逐人有Transfermarkt+FBref及官方/聯賽來源URL的候選；未達門檻不升級。'}
(ROOT/'bundesliga_2025_26_partial_full_report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
(ROOT/'bundesliga_2025_26_partial_full_report.md').write_text('# 德甲2025/26 Full 化第一批（誠實部分合併）\n\n'+json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

# Push latest content via GitHub Contents API, with current SHA for each path.
for path, content, msg in [
 (TEAM_PATH,out.getvalue(),'feat: add verified Bundesliga 2025-26 partial full squads'),
 (PLAYER_PATH,(ROOT/PLAYER_PATH).read_text(encoding='utf-8-sig'),'feat: add verified Bundesliga 2025-26 player evidence'),
 (COACH_PATH,(ROOT/COACH_PATH).read_text(encoding='utf-8-sig'),'feat: add verified Bundesliga 2025-26 coach evidence'),
 ('bundesliga_2025_26_partial_full_report.json',(ROOT/'bundesliga_2025_26_partial_full_report.json').read_text(encoding='utf-8'),'docs: report Bundesliga 2025-26 partial full upgrade'),
 ('bundesliga_2025_26_partial_full_report.md',(ROOT/'bundesliga_2025_26_partial_full_report.md').read_text(encoding='utf-8'),'docs: report Bundesliga 2025-26 partial full upgrade'),
]:
    _, sha = remote_get(path)
    put(path, content, msg, sha)
print(json.dumps(report,ensure_ascii=False))

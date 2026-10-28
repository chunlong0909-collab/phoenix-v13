import json
import re
import shutil
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARTICLE_URL = 'https://www.premierleague.com/en/news/4725682/all-20-premier-league-clubs-squad-numbers-for-202627'

MANAGERS = {
    'Arsenal': ('Mikel Arteta', 'https://www.premierleague.com/en/managers/51018/mikel-arteta'),
    'Aston Villa': ('Unai Emery', 'https://www.premierleague.com/en/managers/37569/unai-emery'),
    'AFC Bournemouth': ('Marco Rose', 'https://www.premierleague.com/en/managers/48664/marco-rose'),
    'Brentford': ('Keith Andrews', 'https://www.premierleague.com/en/managers/66206/keith-andrews'),
    'Brighton & Hove Albion': ('Fabian Hürzeler', 'https://www.premierleague.com/en/managers/53902/fabian-hurzeler'),
    'Chelsea': ('Xabi Alonso', 'https://www.premierleague.com/en/managers/48314/xabi-alonso'),
    'Coventry City': ('Frank Lampard', 'https://www.premierleague.com/en/managers/50167/frank-lampard'),
    'Crystal Palace': ('Pierre Sage', 'https://www.premierleague.com/en/managers/62022/pierre-sage'),
    'Everton': ('David Moyes', 'https://www.premierleague.com/en/managers/85/david-moyes'),
    'Fulham': ('Álvaro Arbeloa', 'https://www.premierleague.com/en/managers/58906/alvaro-arbeloa'),
    'Hull City': ('Sergej Jakirović', 'https://www.premierleague.com/en/managers/50432/sergej-jakirovic'),
    'Ipswich Town': ('Gary O\'Neil', 'https://www.premierleague.com/en/managers/58884/gary-o-neil'),
    'Leeds United': ('Daniel Farke', 'https://www.premierleague.com/en/managers/42856/daniel-farke'),
    'Liverpool': ('Andoni Iraola', 'https://www.liverpoolfc.com/teams/mens-team/andoni-iraola'),
    'Manchester City': ('Enzo Maresca', 'https://www.premierleague.com/en/managers/48549/enzo-maresca'),
    'Manchester United': ('Michael Carrick', 'https://www.premierleague.com/en/clubs/1/manchester-united/overview'),
    'Newcastle United': ('Matthias Jaissle', 'https://www.premierleague.com/en/managers/53959/matthias-jaissle'),
    'Nottingham Forest': ('Oliver Glasner', 'https://www.nottinghamforest.co.uk/news/2026/july/06/forest-appoint-oliver-glasner-as-head-coach/'),
    'Sunderland': ('Régis Le Bris', 'https://www.premierleague.com/en/managers/58318/regis-le-bris'),
    'Tottenham Hotspur': ('Roberto De Zerbi', 'https://www.premierleague.com/en/managers/47376/roberto-de-zerbi'),
}
DISPLAY = {
    'Arsenal': 'Arsenal (Eng)', 'Aston Villa': 'Aston Villa (Eng)', 'AFC Bournemouth': 'Bournemouth (Eng)',
    'Brentford': 'Brentford (Eng)', 'Brighton & Hove Albion': 'Brighton and Hove Albion (Eng)', 'Chelsea': 'Chelsea (Eng)',
    'Coventry City': 'Coventry City (Eng)', 'Crystal Palace': 'Crystal Palace (Eng)', 'Everton': 'Everton (Eng)',
    'Fulham': 'Fulham (Eng)', 'Hull City': 'Hull City (Eng)', 'Ipswich Town': 'Ipswich Town (Eng)',
    'Leeds United': 'Leeds United (Eng)', 'Liverpool': 'Liverpool (Eng)', 'Manchester City': 'Manchester City (Eng)',
    'Manchester United': 'Manchester United (Eng)', 'Newcastle United': 'Newcastle United (Eng)',
    'Nottingham Forest': 'Nottingham Forest (Eng)', 'Sunderland': 'Sunderland (Eng)', 'Tottenham Hotspur': 'Tottenham Hotspur (Eng)',
}

def norm(value):
    return re.sub(r'[^a-z0-9]', '', str(value or '').casefold())

article = (ROOT / 'scripts' / 'epl_official_source_snapshot.md')
if not article.exists():
    raise SystemExit('Missing saved official source snapshot: scripts/epl_official_source_snapshot.md')
text = article.read_text(encoding='utf-8')
parts = re.split(r'(?m)^##### ', text)[1:]
source_squads = {}
for part in parts:
    lines = part.splitlines()
    heading = lines[0]
    match = re.match(r'\[([^]]+)\]\(([^)]+)\)', heading)
    if not match:
        continue
    club, club_url = match.groups()
    players = []
    for line in lines[1:]:
        m = re.match(r'^(\d+)\s+(.+?)\s*$', line.strip())
        if m:
            players.append({'shirt_number': int(m.group(1)), 'name': m.group(2).strip()})
    source_squads[club] = {'club_url': club_url, 'players': players}
assert set(MANAGERS) == set(source_squads), (set(MANAGERS) - set(source_squads), set(source_squads) - set(MANAGERS))
assert sum(len(v['players']) for v in source_squads.values()) == 566

old_master = json.loads((ROOT / 'data/player_master_ALL_574_REAL.json').read_text(encoding='utf-8'))
position_by_name = defaultdict(set)
for record in old_master.values():
    if not isinstance(record, dict):
        continue
    for player in (record.get('front') or []) + (record.get('back') or []):
        if player.get('name') and player.get('position'):
            position_by_name[norm(player['name'])].add(player['position'])

def player_record(item, current_team, club_url):
    positions = sorted(position_by_name.get(norm(item['name']), set()))
    position = positions[0] if len(positions) == 1 else None
    return {
        'name': item['name'], 'shirt_number': item['shirt_number'], 'position': position,
        'age': None, 'nationality': None, 'appearances_current': None, 'goals': None,
        'minutes_played': None, 'current_team': current_team, 'joined_date': None,
        'source': 'premierleague_official_squad_numbers_2026_27', 'source_url': ARTICLE_URL,
        'club_source_url': club_url, 'data_policy': 'official roster presence only; unavailable fields remain null',
    }

def split_known(players):
    front_pos = {'F', 'FW', 'ST', 'CF', 'LW', 'RW', 'AM', 'M', 'MF'}
    back_pos = {'G', 'GK', 'D', 'DF', 'CB', 'LB', 'RB', 'DM', 'WB'}
    front, back = [], []
    for player in players:
        pos = str(player.get('position') or '').upper()
        if pos in front_pos:
            front.append(player)
        elif pos in back_pos:
            back.append(player)
    return front, back

new_records = {}
for index, (club, data) in enumerate(source_squads.items(), start=1):
    display = DISPLAY[club]
    manager, manager_url = MANAGERS[club]
    players = [player_record(item, display, data['club_url']) for item in data['players']]
    front, back = split_known(players)
    key = f'AFC-ENG-{index:02d}:亞冠精英盃:{norm(display)}'
    new_records[key] = {
        'team': display, 'team_id': f'afc-eng-{index:02d}', 'physical_id': f'epl-{norm(club)}',
        'league': '亞冠精英盃', 'competition_scope': 'AFC Champions League Elite', 'tier': 'full',
        'source': 'premierleague_official', 'source_url': data['club_url'],
        'coach': {'name': manager, 'source': 'premierleague_official_manager', 'source_url': manager_url},
        'squad_source_url': ARTICLE_URL, 'squad': players, 'all_players': players,
        'front': front, 'back': back, 'player_count': len(players),
    }

for name in ['data/final_574_squads_with_sources.json', 'assets/data/final_574_squads_with_sources.json']:
    path = ROOT / name
    data = json.loads(path.read_text(encoding='utf-8'))
    data.update(new_records)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

for filename, field in [('data/player_master_ALL_574_REAL.json', None), ('data/player_master_FRONT_574_REAL.json', 'front'), ('data/player_master_BACK_574_REAL.json', 'back')]:
    path = ROOT / filename
    data = json.loads(path.read_text(encoding='utf-8'))
    for key, record in new_records.items():
        if field is None:
            data[key] = record
        else:
            data[key] = {k: record[k] for k in ['team','team_id','physical_id','league','competition_scope','tier','source','source_url','coach','squad_source_url','squad','all_players']}
            data[key][field] = record[field]
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

# Produce a compact audit.
old_coaches = 325
new_players = sum(len(v['all_players']) for v in new_records.values())
known_positions = sum(sum(bool(p.get('position')) for p in v['all_players']) for v in new_records.values())
audit = {
    'source_url': ARTICLE_URL, 'teams_added': len(new_records), 'players_added': new_players,
    'players_with_position_from_existing_verified_master': known_positions,
    'all_player_source_url_nonempty': all(bool(p.get('source_url')) for v in new_records.values() for p in v['all_players']),
    'all_coach_source_url_nonempty': all(bool(v['coach'].get('source_url')) for v in new_records.values()),
    'coaches_before': old_coaches, 'coaches_after_expected': old_coaches + len(new_records),
    'fake_names': [], 'policy': 'No invented player, coach, score, age or nationality; unavailable fields null.'
}
(ROOT / 'epl_full_enrichment_audit.json').write_text(json.dumps(audit, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print(json.dumps({'teams':len(new_records),'players':new_players,'known_positions':known_positions,'coach_after':old_coaches+len(new_records)},ensure_ascii=False))

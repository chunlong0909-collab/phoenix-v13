#!/usr/bin/env python3
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

p=ROOT/'leagues.json'; d=json.loads(p.read_text())
if not any(x.get('id')=='afc-champions-league-elite' for x in d['leagues']):
 d['leagues'].append({'id':'afc-champions-league-elite','name_zh':'亞冠精英盃','name_en':'AFC Champions League Elite','provider':'official/flashscore','openfootball_paths':[],'sportsdb_names':['AFC Champions League Elite'],'official_fixtures_url':'https://www.the-afc.com/en/club/afc_champions_league_elite/fixtures__standings.html','flashscore_results_url':'https://www.flashscore.com/football/asia/afc-champions-league/'})
p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')

p=ROOT/'config/league_flashscore_sources.json'; s=json.loads(p.read_text())
url='https://www.flashscore.com/football/asia/afc-champions-league/'
s['亞冠精英盃']=url; s['AFC Champions League Elite']=url
p.write_text(json.dumps(s,ensure_ascii=False,indent=2)+'\n')

for fn in ['data/final_574_squads_with_sources.json','assets/data/final_574_squads_with_sources.json']:
 p=ROOT/fn; teams=json.loads(p.read_text())
 key='0575:亞冠精英盃:daejeon-hana-citizen'
 if key not in teams:
  teams[key]={'team':'Daejeon Hana Citizen','team_id':'daejeon-hana-citizen','league':'亞冠精英盃','physical_id':'daejeon-hana-citizen','espn_team_id':None,'source_url':'https://en.wikipedia.org/wiki/Daejeon_Hana_Citizen','front':[],'back':[],'coach':None,'stadium':'城市中心fallback（非球場）','city':'Daejeon','lat':36.34913,'lon':127.38493,'stadium_source':'Open-Meteo Geocoding','coordinates_source':'city_center','coordinates_source_url':'https://geocoding-api.open-meteo.com/v1/search?name=Daejeon&count=5&language=en&format=json','data_note':'AFC supplemental team record; no player roster fabricated.'}
 for v in teams.values():
  if v.get('team')=='Vissel Kobe':
   v.update({'stadium':'城市中心fallback（非球場）','city':'Kobe','lat':34.6913,'lon':135.183,'stadium_source':'Open-Meteo Geocoding','coordinates_source':'city_center','coordinates_source_url':'https://geocoding-api.open-meteo.com/v1/search?name=Kobe&count=5&language=en&format=json'})
 p.write_text(json.dumps(teams,ensure_ascii=False,indent=2)+'\n')

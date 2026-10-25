"""Source-aware player, coach and Open-Meteo weather helpers."""
from __future__ import annotations
import json
from datetime import date,datetime,timedelta,timezone
from pathlib import Path
import requests

FRONT_POS={"F","FW","ST","CF","LW","RW","CAM","AM","SS"}; BACK_POS={"G","GK","D","DF","CB","LB","RB","CDM","DM","WB"}
POSITION_WEIGHT={"G":.75,"GK":.75,"D":.90,"DF":.90,"CB":.95,"LB":.90,"RB":.90,"WB":.90,"CDM":1.,"DM":1.,"M":1.,"MF":1.,"CM":1.,"CAM":1.05,"AM":1.05,"F":1.10,"FW":1.10,"ST":1.10,"CF":1.10,"LW":1.05,"RW":1.05,"SS":1.05}
coach_style={"進攻型":{"factor":1.08,"keywords":("pep","guardiola","klopp","arteta","ancelotti")},"防守型":{"factor":.92,"keywords":("mourinho","simeone","conte")},"中性":{"factor":1.,"keywords":()}}

def position_weight(position): return POSITION_WEIGHT.get(str(position or '').upper(),1.)
def player_strength(player):
 pos=position_weight(player.get('position'));goals=player.get('goals');apps=player.get('appearances_current',player.get('appearances_25_26'))
 try:goals=max(float(goals),0.) if goals is not None else 0.
 except(TypeError,ValueError):goals=0.
 try:apps=float(apps) if apps is not None else None
 except(TypeError,ValueError):apps=None
 raw=50.*pos if apps is None or apps==0 else (35.+min(apps,38.)/38.*35.+min(goals,20.)/20.*30.)*pos
 return round(max(0.,min(100.,raw)),2)
def team_strength(team):
 ps=team.get('front',[])+team.get('back',[]);ss=[player_strength(p) for p in ps]
 return {'team':team.get('team'),'players':len(ps),'mean_strength':round(sum(ss)/len(ss),2) if ss else None,'source_aware':True}
def classify_coach(coach):
 name=str((coach or {}).get('name') or '').strip();low=name.casefold()
 for style,c in coach_style.items():
  for key in c['keywords']:
   if key in low:return {'name':name,'style':style,'factor':c['factor'],'matched_keyword':key}
 return {'name':name or None,'style':'中性','factor':1.,'matched_keyword':None}
def apply_coach_factors(lambda_home,lambda_away,home_team=None,away_team=None,prediction_log=None):
 h=classify_coach((home_team or {}).get('coach'));a=classify_coach((away_team or {}).get('coach'));rh=float(lambda_home)*h['factor'];ra=float(lambda_away)*a['factor']
 out={'lambda_home':round(rh,6),'lambda_away':round(ra,6),'home_coach_factor':h['factor'],'away_coach_factor':a['factor'],'home_coach_style':h['style'],'away_coach_style':a['style'],'coach_factor':{'home':h,'away':a}}
 if prediction_log is not None:prediction_log.append({'timestamp':datetime.now(timezone.utc).isoformat(),'event':'coach_factor','home':h,'away':a,'lambda_home_before':float(lambda_home),'lambda_away_before':float(lambda_away),'lambda_home_after':out['lambda_home'],'lambda_away_after':out['lambda_away']})
 return out

def _weather_point(forecast,target):
 if 'rain_mm' in forecast or 'temp_c' in forecast:return forecast.get('rain_mm'),forecast.get('temp_c')
 d=forecast.get('daily',{});rs=d.get('precipitation_sum',[]);ts=d.get('temperature_2m_max',[]);ds=d.get('time',[]);i=ds.index(target) if target in ds else 0
 return (rs[i] if i<len(rs) else None),(ts[i] if i<len(ts) else None)
def _factor_from_forecast(forecast,target):
 rain,temp=_weather_point(forecast,target);rain=float(rain) if rain is not None else None;temp=float(temp) if temp is not None else None;total=1.;over=1.;reasons=[]
 if rain is not None and rain>15:total*=.85;over*=.85;reasons.append('rain>15mm')
 elif rain is not None and rain>5:total*=.90;over*=.90;reasons.append('rain>5mm')
 if temp is not None and temp<5:total*=.95;reasons.append('temp<5C')
 return {'status':'ok','date':target,'rain_mm':rain,'temp_c':temp,'total_factor':round(total,6),'over25_factor':round(over,6),'reasons':reasons}
def get_weather_factor(lat,lon,match_date=None):
 """Get Open-Meteo factor for match_date or tomorrow when omitted."""
 target=(match_date.isoformat() if hasattr(match_date,'isoformat') else str(match_date)) if match_date is not None else (date.today()+timedelta(days=1)).isoformat()
 neutral={'status':'no_coordinates','date':target,'total_factor':1.,'over25_factor':1.,'rain_mm':None,'temp_c':None}
 if lat is None or lon is None:return neutral
 params={'latitude':lat,'longitude':lon,'daily':'precipitation_sum,temperature_2m_max','timezone':'auto'}
 if match_date is None:params['forecast_days']=2
 else:params['start_date']=target;params['end_date']=target
 try:
  r=requests.get('https://api.open-meteo.com/v1/forecast',params=params,timeout=12);r.raise_for_status();return _factor_from_forecast(r.json(),target)
 except requests.RequestException as e:return {'status':'api_error','date':target,'error':str(e),'total_factor':1.,'over25_factor':1.,'rain_mm':None,'temp_c':None}
def apply_weather_factor(total_goals,over25_probability,team=None,match_date=None,prediction_log=None,forecast=None):
 team=team or {};w=_factor_from_forecast(forecast,((match_date.isoformat() if hasattr(match_date,'isoformat') else str(match_date)) if match_date is not None else (date.today()+timedelta(days=1)).isoformat())) if forecast is not None else get_weather_factor(team.get('lat'),team.get('lon'),match_date)
 out={'total_goals':round(float(total_goals)*w['total_factor'],6),'over25_probability':round(float(over25_probability)*w['over25_factor'],6),'weather_factor':w}
 if prediction_log is not None:prediction_log.append({'timestamp':datetime.now(timezone.utc).isoformat(),'event':'weather_factor','weather_factor':w,'total_goals_before':float(total_goals),'over25_before':float(over25_probability),'total_goals_after':out['total_goals'],'over25_after':out['over25_probability']})
 return out
def calculate_value_and_yinpan(model_prob,bookmaker_odds,market_name=""):
 """計算手動十進制賠率的隱含機率、EV及陰盤差距；不連接任何莊家。"""
 try: prob=float(model_prob);odds=float(bookmaker_odds)
 except (TypeError,ValueError): return None
 if not 0<=prob<=1 or odds<=1:return None
 implied=1.0/odds;value=(prob*odds)-1.0;diff=abs(prob-implied)
 if diff>.25 or value>.25:status="⚠️ 疑似陰盤/陷阱 - 差距過大，查正選/傷病"
 elif value>.05:status="✅ VALUE值得買"
 elif value<-.05:status="❌ NO VALUE唔值"
 else:status="➖ FAIR合理"
 return {'market':market_name,'model_prob':prob,'implied':implied,'value':value,'diff':diff,'status':status}

def _manual_odds_analysis(over25_probability,home_odds=None,draw_odds=None,away_odds=None,
                          over_odds=None,under_odds=None,corner_over_odds=None,
                          corner_under_odds=None,corner_line=9.5,over_line=2.5,
                          corner_total=None,home_probability=None,draw_probability=None,
                          away_probability=None):
 rows={}
 entries=(("主勝",home_probability,home_odds),("和局",draw_probability,draw_odds),
          ("客勝",away_probability,away_odds),(f"大{over_line}",over25_probability,over_odds),
          (f"細{over_line}",1-float(over25_probability),under_odds))
 for name,prob,odds in entries:
  if prob is not None and odds not in (None,0):rows[name]=calculate_value_and_yinpan(prob,odds,name)
 if corner_total is not None:
  cp=1.0 if float(corner_total)>float(corner_line) else .6
  for name,prob,odds in ((f"角球大{corner_line}",cp,corner_over_odds),(f"角球細{corner_line}",1-cp,corner_under_odds)):
   if odds not in (None,0):rows[name]=calculate_value_and_yinpan(prob,odds,name)
 return rows

def predict_match(total_goals,over25_probability,lat=None,lon=None,match_date=None,prediction_log=None,
                  home_odds=None,draw_odds=None,away_odds=None,over_odds=None,under_odds=None,
                  corner_over_odds=None,corner_under_odds=None,corner_line=9.5,over_line=2.5,
                  corner_total=None,home_probability=None,draw_probability=None,away_probability=None):
 """Apply weather and optionally analyse manually entered odds."""
 out=apply_weather_factor(total_goals,over25_probability,{'lat':lat,'lon':lon},match_date,prediction_log)
 out['odds_analysis']=_manual_odds_analysis(out['over25_probability'],home_odds,draw_odds,away_odds,over_odds,under_odds,corner_over_odds,corner_under_odds,corner_line,over_line,corner_total,home_probability,draw_probability,away_probability)
 if prediction_log is not None and out['odds_analysis']:
  prediction_log.append({'timestamp':datetime.now(timezone.utc).isoformat(),'event':'manual_odds_value_yinpan','markets':out['odds_analysis']})
 return out
def load_squads(path):return json.loads(Path(path).read_text(encoding='utf-8'))
if __name__=='__main__':print(f"Loaded {len(load_squads(Path(__file__).parent/'data'/'final_574_squads_with_sources.json'))} team containers")

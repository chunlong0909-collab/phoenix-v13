#!/usr/bin/env python3
"""v2 stadium backfill: preserve v1 successes, resolve remaining teams by city/country.

來源層級：
1. v1 已核實資料原樣保留；
2. Open-Meteo Geocoding / Nominatim 的球隊城市位置，標 city_center；
3. 聯賽國家中心坐標，標 country_center，絕不冒充球場。
"""
from __future__ import annotations
import json, re, sqlite3, time
from datetime import datetime, timezone
from pathlib import Path
import requests

ROOT=Path(__file__).resolve().parents[1]
DATA_JSON=ROOT/'data/final_574_squads_with_sources.json'
ASSET_JSON=ROOT/'assets/data/final_574_squads_with_sources.json'
REPORT=ROOT/'data/stadium_backfill_report.json'
DB=ROOT/'football_library.db'
UA='PhoenixFootballResearch/2.0 (transparent city/country coordinate fallback)'
CITY_HINTS={'Manchester City FC':('Manchester',53.48095,-2.23743),'Real Madrid CF':('Madrid',40.4165,-3.70256),'Vissel Kobe':('Kobe',34.6913,135.183),'Daejeon Hana Citizen':('Daejeon',36.34913,127.38493)}
# Approximate geographic centres are explicitly marked country_center, never stadium_exact.
COUNTRY_CENTER={
 'England':(52.3555,-1.1743),'Spain':(40.4637,-3.7492),'Italy':(41.8719,12.5674),'Germany':(51.1657,10.4515),'France':(46.2276,2.2137),
 'Japan':(36.2048,138.2529),'Portugal':(39.3999,-8.2245),'Netherlands':(52.1326,5.2913),'Turkey':(38.9637,35.2433),'Belgium':(50.5039,4.4699),
 'Brazil':(-14.2350,-51.9253),'Austria':(47.5162,14.5501),'Switzerland':(46.8182,8.2275),'Norway':(60.4720,8.4689),'Sweden':(60.1282,18.6435),
 'Denmark':(56.2639,9.5018),'Scotland':(56.4907,-4.2026),'Greece':(39.0742,21.8243),'Argentina':(-38.4161,-63.6167),'United States':(39.8283,-98.5795),
 'Mexico':(23.6345,-102.5528),'Australia':(-25.2744,133.7751),'South Korea':(35.9078,127.7669),'China':(35.8617,104.1954)
}
LEAGUE_COUNTRY={'英超':'England','英冠':'England','英甲':'England','西甲':'Spain','西乙':'Spain','意甲':'Italy','意乙':'Italy','德甲':'Germany','德乙':'Germany','法甲':'France','法乙':'France','J1聯賽':'Japan','日職':'Japan','葡超':'Portugal','荷甲':'Netherlands','土超':'Turkey','比甲':'Belgium','巴甲':'Brazil','奧甲':'Austria','瑞士超':'Switzerland','挪超':'Norway','瑞典超':'Sweden','丹超':'Denmark','蘇冠':'Scotland','蘇超':'Scotland','希超':'Greece','阿甲':'Argentina','美職MLS':'United States','墨西超':'Mexico','A-League':'Australia'}

def valid(x,y):
 try:return -90<=float(x)<=90 and -180<=float(y)<=180
 except:return False

def base_name(team):
 s=re.sub(r'\b(FC|CF|AFC|AC|BC|SC|UD|RC|RCD|AS|SS|US|SV|VfB|VfL|TSG|CA|CD|SD)\b','',team,flags=re.I)
 return re.sub(r'\s+',' ',s).strip()

def req(url,params):
 try:
  r=requests.get(url,params=params,headers={'User-Agent':UA,'Accept-Language':'en'},timeout=3)
  if r.status_code==429: return {}
  r.raise_for_status(); return r.json()
 except (requests.RequestException,ValueError):
  pass
 return {}

def city_geocode(team,league):
    country=LEAGUE_COUNTRY.get(league,''); q=base_name(team)
    if team in CITY_HINTS:
        city,lat,lon=CITY_HINTS[team]
        return {'lat':lat,'lon':lon,'city':city,'stadium_name':'城市中心fallback（非球場）','source':'city_center','provider':'Open-Meteo Geocoding (verified hint)'}
    # Open-Meteo is tried first because it returns a city object directly.
    for query in [q]:
        d=req('https://geocoding-api.open-meteo.com/v1/search',{'name':query,'count':5,'language':'en','format':'json'})
        for x in d.get('results',[]) if isinstance(d,dict) else []:
            if country and str(x.get('country','')).casefold()!=country.casefold(): continue
            if valid(x.get('latitude'),x.get('longitude')):
                return {'lat':float(x['latitude']),'lon':float(x['longitude']),'city':x.get('name'),'stadium_name':'城市中心fallback（非球場）','source':'city_center','provider':'Open-Meteo Geocoding'}
    # Deliberately do not wait on a second slow provider here; country_center below
    # is deterministic and transparent when Open-Meteo cannot identify the city.
    return None

def main():
 D=json.loads(DATA_JSON.read_text(encoding='utf-8'))
 old=json.loads(REPORT.read_text(encoding='utf-8')) if REPORT.exists() else {'entries':[]}
 old_by={(e.get('team'),e.get('league')):e for e in old.get('entries',[])}
 entries=[]; counts={'stadium_exact':0,'city_center':0,'country_center':0}
 unresolved=[e for e in old.get('entries',[]) if e.get('status')!='ok']
 unresolved_keys={(e.get('team'),e.get('league')) for e in unresolved}
 for key,item in D.items():
  team=str(item.get('team') or key); league=str(item.get('league') or '')
  previous=old_by.get((team,league))
  if (team,league) not in unresolved_keys and previous and previous.get('status')=='ok' and valid(previous.get('lat'),previous.get('lon')):
   src='stadium_exact' if previous.get('source') in {'user_verified','OpenStreetMap Nominatim'} and 'fallback' not in str(previous.get('stadium','')) else 'city_center'
   item['lat']=previous['lat']; item['lon']=previous['lon']; item['city']=previous.get('city'); item['stadium']=previous.get('stadium'); item['coordinates_source']=src; item['stadium_source']=previous.get('source')
   counts[src]+=1
   entries.append({**previous,'status':'ok','source':src}); continue
  country=LEAGUE_COUNTRY.get(league)
  found=city_geocode(team,league) if country else None
  if found:
   item.update({'lat':found['lat'],'lon':found['lon'],'city':found['city'],'stadium':found['stadium_name'],'coordinates_source':found['source'],'stadium_source':found['provider']})
   counts['city_center']+=1; entries.append({'team':team,'league':league,'status':'ok','stadium':found['stadium_name'],'city':found['city'],'lat':found['lat'],'lon':found['lon'],'source':'city_center','provider':found['provider']})
  elif country in COUNTRY_CENTER:
   lat,lon=COUNTRY_CENTER[country]; item.update({'lat':lat,'lon':lon,'city':country,'stadium':'國家中心fallback（非球場）','coordinates_source':'country_center','stadium_source':'country_center'})
   counts['country_center']+=1; entries.append({'team':team,'league':league,'status':'ok','stadium':'國家中心fallback（非球場）','city':country,'lat':lat,'lon':lon,'source':'country_center'})
  else:
   entries.append({'team':team,'league':league,'status':'unresolved','reason':'no country mapping'})
  print(f"{len(entries)}/{len(D)} {team}: {entries[-1]['source'] if entries[-1]['status']=='ok' else 'unresolved'}",flush=True)
 out=json.dumps(D,ensure_ascii=False,indent=2)+'\n'; DATA_JSON.write_text(out,encoding='utf-8'); ASSET_JSON.write_text(out,encoding='utf-8')
 now=datetime.now(timezone.utc).isoformat(); summary={'generated_at':now,'version':'v2','teams_seen':len(D),'processed':len(entries),'coordinates_ok':sum(valid(e.get('lat'),e.get('lon')) for e in entries),'unresolved':sum(e.get('status')!='ok' for e in entries),'stadium_exact':counts['stadium_exact'],'city_center':counts['city_center'],'country_center':counts['country_center'],'fallback_city_center':counts['city_center'],'entries':entries}
 REPORT.write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 conn=sqlite3.connect(DB); conn.execute('CREATE TABLE IF NOT EXISTS stadiums (team_key TEXT PRIMARY KEY, team_name TEXT NOT NULL, league TEXT, stadium_name TEXT, city TEXT, lat REAL, lon REAL, source TEXT, updated_at TEXT)')
 for key,item in D.items():
  conn.execute('INSERT INTO stadiums(team_key,team_name,league,stadium_name,city,lat,lon,source,updated_at) VALUES(?,?,?,?,?,?,?,?,?) ON CONFLICT(team_key) DO UPDATE SET stadium_name=excluded.stadium_name,city=excluded.city,lat=excluded.lat,lon=excluded.lon,source=excluded.source,updated_at=excluded.updated_at',(key,item.get('team'),item.get('league'),item.get('stadium'),item.get('city'),item.get('lat'),item.get('lon'),item.get('coordinates_source'),now))
 conn.commit(); conn.close(); print(json.dumps({k:summary[k] for k in ['teams_seen','processed','coordinates_ok','unresolved','stadium_exact','city_center','country_center']},ensure_ascii=False))
if __name__=='__main__': main()

from __future__ import annotations
import json, re, requests
from pathlib import Path
from datetime import datetime, timezone

ROOT=Path(__file__).resolve().parents[1]
CAT=ROOT/'catalog/complete_1000_A_phase.json'
OUT=ROOT/'data/player_master_ALL_574_REAL.json'
FRONT=ROOT/'data/player_master_FRONT_574_REAL.json'
BACK=ROOT/'data/player_master_BACK_574_REAL.json'
CHECK=ROOT/'data/real_data_check.json'
MISSING=ROOT/'data/missing_real_data.json'

FRONT_POS={'ST','CF','LW','RW','CAM','AM','SS','FORWARD','ATTACKER','STRIKER'}
BACK_POS={'CB','LB','RB','CDM','DM','GK','WB','DEFENDER','GOALKEEPER','MIDFIELDER'}

def teams():
 d=json.loads(CAT.read_text(encoding='utf-8'))
 return [(league,t) for league,b in d.items() if isinstance(b,dict) for t in b.get('teams',[])]

def empty_player(team):
 return {'transfermarkt_id':None,'fbref_id':None,'name':None,'age':None,'nationality':None,'position':None,'foot':None,'height':None,'appearances_23_24':None,'appearances_24_25':None,'minutes_played':None,'current_team':team,'joined_date':None,'source_url':None}

def main():
 ts=teams()
 if len(ts)!=574: raise SystemExit(f'expected 574 teams, got {len(ts)}')
 all_out={}; front_out={}; back_out={}; missing=[]
 for league,t in ts:
  tid=str(t.get('team_id')); name=t.get('name'); key=f'{league}:{tid}'
  # No unverified ESPN/catalog rows are promoted into REAL output.
  all_out[key]={'team':name,'team_id':tid,'league':league,'physical_id':tid,'front':[],'back':[],'source_status':'not_verified'}
  front_out[key]={'team':name,'team_id':tid,'league':league,'front':[]}
  back_out[key]={'team':name,'team_id':tid,'league':league,'back':[]}
  missing.append({'team':name,'team_id':tid,'league':league,'missing':'player roster not accepted','reason':'Transfermarkt player table blocked/dynamic and FBref returned Cloudflare 403','source_urls':[]})
 report={'generated_at':datetime.now(timezone.utc).isoformat(),'physical_teams':len(ts),'accepted_players':0,'teams_with_accepted_players':0,'age_coverage':0.0,'appearances_23_24_coverage':0.0,'appearances_24_25_coverage':0.0,'minutes_coverage':0.0,'source_url_coverage':0.0,'front_players':0,'back_players':0,'position_unknown':0,'source_policy':'Only player rows with verifiable Transfermarkt or FBref player page URLs and source fields may enter REAL outputs; no ESPN fallback is promoted.','probes':{'transfermarkt':'HTTP 200 but roster table/player rows not exposed in static HTML during probe; requires browser/session or allowed source export','fbref':'HTTP 403 Cloudflare during probe'},'status':'blocked_sources_no_real_player_rows_written','note':'All missing fields remain null. This is an honest empty result, not a claim that the 574 rosters are complete.'}
 for p,d in [(OUT,all_out),(FRONT,front_out),(BACK,back_out),(CHECK,report),(MISSING,missing)]: p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding='utf-8')
 print(json.dumps(report,ensure_ascii=False,indent=2))
if __name__=='__main__':main()

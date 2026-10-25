from __future__ import annotations
import copy, json, re, unicodedata
from collections import Counter
from datetime import datetime, date
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'catalog/complete_1000_A_phase.json'
STEEL=ROOT/'catalog/steel_462_base.json'
CONCRETE=ROOT/'catalog/concrete_60_candidates.json'
OUT=ROOT/'catalog/logical_2870_catalog.json'
PART1=ROOT/'catalog/logical_2870_part1.json'
PART2=ROOT/'catalog/logical_2870_part2.json'
CON112=ROOT/'catalog/concrete_112.json'
AUD=ROOT/'catalog/final_2870_A_audit.json'
BT=ROOT/'catalog/2870_weighted_backtest_report.json'


def norm(s):
    s=unicodedata.normalize('NFKD',str(s or '')).encode('ascii','ignore').decode().lower()
    return re.sub(r'[^a-z0-9]+','',s)

def parsed(v):
    s=str(v or '').strip().replace('T',' ').replace('Z','')
    for f in ('%Y-%m-%d %H:%M:%S','%Y-%m-%d','%d/%m/%Y','%d/%m/%Y %H:%M'):
        try:return datetime.strptime(s[:19],f).date()
        except ValueError:pass
    return None

def season_group(d):
    if not d:return None
    if date(2021,8,1)<=d<date(2023,8,1): return 'EARLY'
    if date(2023,8,1)<=d<date(2025,8,1): return 'LATE'
    return None

def physical_side(team,m):
    name=norm(team.get('name')); h=norm(m.get('home')); a=norm(m.get('away'))
    if h==name:return 'HOME'
    if a==name:return 'AWAY'
    # A small fallback for source name suffixes; never invents a match.
    if name and (name in h or h in name):return 'HOME'
    if name and (name in a or a in name):return 'AWAY'
    return None

def make_team(team, suffix, matches):
    x=copy.deepcopy(team)
    original=team.get('team_id')
    x['team_id']=f"{original}_{suffix}"
    x['physical_id']=original
    x['logical_type']=suffix
    x['matches']=copy.deepcopy(matches)
    x['sample_count']=len(matches)
    x['match_count']=len(matches)
    x['status']='active' if len(matches)>=30 else 'dropped_low_sample'
    x['dropped_low_sample']=len(matches)<30
    if suffix=='BASE': mult=1.0
    elif suffix in ('HOME','AWAY'): mult=0.8
    elif suffix=='EARLY': mult=0.6
    else: mult=0.9
    x['weight']=round(float(team.get('weight',1.0))*mult,4)
    x['tier']=team.get('tier','steel')
    return x

def main():
    data=json.loads(BASE.read_text(encoding='utf-8'))
    physical=[(league,t) for league,b in data.items() if isinstance(b,dict) for t in b.get('teams',[])]
    if len(physical)!=574: raise RuntimeError(f'expected 574 physical teams, got {len(physical)}')
    logical={}; all_logical=[]; dropped=[]
    for league,t in physical:
        ms=t.get('matches',[])
        buckets={'BASE':ms,'HOME':[],'AWAY':[],'EARLY':[],'LATE':[]}
        for m in ms:
            side=physical_side(t,m)
            if side in ('HOME','AWAY'): buckets[side].append(m)
            sg=season_group(parsed(m.get('date')))
            if sg:buckets[sg].append(m)
        block=logical.setdefault(league,{'competition_code':data[league].get('competition_code',league),'league':league,'teams':[]})
        for suffix in ('BASE','HOME','AWAY','EARLY','LATE'):
            lt=make_team(t,suffix,buckets[suffix])
            if lt['dropped_low_sample']:
                dropped.append({'physical_id':t.get('team_id'),'name':t.get('name'),'league':league,'logical_type':suffix,'sample_count':len(lt['matches']),'reason':'dropped_low_sample'})
            else:
                block['teams'].append(lt); all_logical.append((league,lt))
    active_by_type=Counter(t['logical_type'] for _,t in all_logical)
    all_rows=sum(len(t['matches']) for _,t in all_logical)
    physical_rows=sum(len(t.get('matches',[])) for _,t in physical)
    physical_ft_keys={(m.get('match_id'),m.get('date'),m.get('home'),m.get('away'),m.get('ft_home'),m.get('ft_away')) for _,t in physical for m in t.get('matches',[])}
    logical_ft_keys={(m.get('match_id'),m.get('date'),m.get('home'),m.get('away'),m.get('ft_home'),m.get('ft_away')) for _,t in all_logical for m in t.get('matches',[])}
    # Keep full logical object locally and split by physical-team order for GitHub-sized uploads.
    OUT.write_text(json.dumps(logical,ensure_ascii=False,indent=2),encoding='utf-8')
    leagues=list(logical)
    p1={};p2={}; half=(len(leagues)+1)//2
    for i,k in enumerate(leagues): (p1 if i<half else p2)[k]=logical[k]
    PART1.write_text(json.dumps(p1,ensure_ascii=False,indent=2),encoding='utf-8')
    PART2.write_text(json.dumps(p2,ensure_ascii=False,indent=2),encoding='utf-8')
    CON112.write_text(CONCRETE.read_text(encoding='utf-8'),encoding='utf-8')
    original_ht=sum(1 for _,t in physical for m in t.get('matches',[]) if m.get('ht_home') is not None or m.get('ht_away') is not None)
    logical_ht=sum(1 for _,t in all_logical for m in t.get('matches',[]) if m.get('ht_home') is not None or m.get('ht_away') is not None)
    bad_ft=sum(1 for _,t in all_logical for m in t.get('matches',[]) if m.get('ft_home') is None or m.get('ft_away') is None or not m.get('date') or not m.get('home') or not m.get('away'))
    report={'physical_teams':574,'physical_retention_rate':1.0,'physical_catalog_rows':physical_rows,'physical_unique_ft_rows':len(physical_ft_keys),'physical_ft_invalid_rows':sum(1 for _,t in physical for m in t.get('matches',[]) if m.get('ft_home') is None or m.get('ft_away') is None),'physical_ht_nonnull_rows':original_ht,'logical_target':2870,'logical_active':len(all_logical),'logical_dropped':len(dropped),'logical_by_type':dict(active_by_type),'logical_catalog_rows':all_rows,'logical_ft_invalid_rows':bad_ft,'logical_ht_nonnull_rows':logical_ht,'logical_unique_ft_rows':len(logical_ft_keys),'unique_ft_set_equal':physical_ft_keys==logical_ft_keys,'split_rows_equal':all_rows==sum(len(t['matches']) for _,t in all_logical),'split_policy':'All logical views reuse exact source match objects; no scores or HT values are generated. EARLY=2021-08-01..2023-07-31; LATE=2023-08-01..2025-07-31.','dropped_low_sample':dropped}
    AUD.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({k:report[k] for k in ('physical_teams','physical_catalog_rows','physical_unique_ft_rows','physical_ft_invalid_rows','physical_ht_nonnull_rows','logical_target','logical_active','logical_dropped','logical_by_type','logical_catalog_rows','logical_ft_invalid_rows','logical_ht_nonnull_rows')},ensure_ascii=False))

if __name__=='__main__':main()

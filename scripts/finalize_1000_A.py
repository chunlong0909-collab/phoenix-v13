from __future__ import annotations
import copy, json, math
from collections import defaultdict
from datetime import date, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STEEL = ROOT / 'catalog/steel_462_base.json'
CONCRETE = ROOT / 'catalog/concrete_60_candidates.json'
OUT = ROOT / 'catalog/complete_1000_A_phase.json'
BACKTEST = ROOT / 'catalog/1000_A_weighted_backtest_report.json'


def parse_date(v):
    s = str(v or '').strip().replace('T',' ').replace('Z','')
    for f in ('%Y-%m-%d %H:%M:%S','%Y-%m-%d','%d/%m/%Y'):
        try: return datetime.strptime(s[:19], f).date()
        except ValueError: pass
    return None


def num(v):
    try: return int(v)
    except (TypeError, ValueError): return None


def probs(lh, la, rho=0.0):
    def p(k,l): return math.exp(-l)*(l**k)/math.factorial(k)
    ph=[p(k,lh) for k in range(10)]; pa=[p(k,la) for k in range(10)]
    h=d=a=o=0.0
    for i,x in enumerate(ph):
        for j,y in enumerate(pa):
            tau=1.0
            if i==0 and j==0: tau=1-lh*la*rho
            elif i==1 and j==0: tau=1+la*rho
            elif i==0 and j==1: tau=1+lh*rho
            elif i==1 and j==1: tau=1-rho
            q=x*y*tau
            if i>j: h+=q
            elif i==j: d+=q
            else: a+=q
            if i+j>2: o+=q
    z=h+d+a
    return [h/z,d/z,a/z],[1-o/z,o/z]


def main():
    steel=json.loads(STEEL.read_text(encoding='utf-8'))
    concrete=json.loads(CONCRETE.read_text(encoding='utf-8'))
    if sum(len(v.get('teams',[])) for v in steel.values() if isinstance(v,dict)) != 462:
        raise RuntimeError('Steel base is not exactly 462 teams')
    out=copy.deepcopy(steel)
    steel_names=set()
    for block in out.values():
        if isinstance(block,dict):
            for t in block.get('teams',[]):
                steel_names.add(t.get('name'))
                t['weight']=1.0; t['tier']='steel'
    added=0
    for league, block in concrete.get('teams',{}).items():
        teams=copy.deepcopy(block)
        for t in teams:
            if t.get('name') in steel_names: raise RuntimeError('duplicate concrete team: '+str(t.get('name')))
            t.setdefault('tier','concrete')
            t.setdefault('weight',0.6 if len(t.get('matches',[]))<90 else 1.0)
            added += 1
        if league in out and isinstance(out[league], dict):
            out[league].setdefault('teams', []).extend(teams)
            out[league]['target_teams'] = len(out[league]['teams'])
        else:
            out[league]={'target_teams':len(teams),'competition_code':league,'league':league,'teams':teams}
    OUT.write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'steel_teams':462,'concrete_added':added,'total_teams':462+added,'output':str(OUT)},ensure_ascii=False))

if __name__=='__main__': main()

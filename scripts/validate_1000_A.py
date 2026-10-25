from __future__ import annotations
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
STEEL=ROOT/'catalog/steel_462_base.json'; CON=ROOT/'catalog/concrete_60_candidates.json'; CAT=ROOT/'catalog/complete_1000_A_phase.json'; AUD=ROOT/'catalog/final_1000_A_audit.json'; BT=ROOT/'catalog/1000_A_weighted_backtest_report.json'
def teams(d):return [t for b in d.values() if isinstance(b,dict) for t in b.get('teams',[])]
def main():
 s=json.loads(STEEL.read_text()); c=json.loads(CON.read_text()); d=json.loads(CAT.read_text()); a=json.loads(AUD.read_text()); bt=json.loads(BT.read_text())
 st=teams(s); ct=[t for b in c.get('teams',{}).values() for t in b]; all_t=teams(d)
 assert len(st)==462, len(st); assert len(all_t)==len(st)+len(ct)==574, len(all_t)
 old_names={t['name'] for t in st}; assert not old_names & {t['name'] for t in ct}
 bad_ft=[]; bad_ht=[]
 for t in all_t:
  for m in t.get('matches',[]):
   if m.get('ft_home') is None or m.get('ft_away') is None or not m.get('date') or not m.get('home') or not m.get('away'): bad_ft.append((t['name'],m))
   if t.get('tier')=='concrete' and (m.get('ht_home') is not None or m.get('ht_away') is not None): bad_ht.append((t['name'],m))
 assert not bad_ft, len(bad_ft); assert not bad_ht, len(bad_ht)
 combined_by_name={t.get('name'):t for t in all_t}
 assert all(combined_by_name.get(t.get('name'),{}).get('tier')=='steel' and combined_by_name.get(t.get('name'),{}).get('weight')==1.0 for t in st)
 assert all(t.get('tier')=='concrete' and t.get('weight') in (0.6,1.0) for t in ct)
 assert a['baseline_teams']==462 and a['total_teams']==574 and a['ft_invalid_rows']==0 and a['new_ht_nonnull_rows']==0
 print(json.dumps({'CATALOG_GREEN':True,'STEEL_TEAMS':len(st),'CONCRETE_TEAMS':len(ct),'TOTAL_TEAMS':len(all_t),'FT_INVALID':len(bad_ft),'CONCRETE_HT_NONNULL':len(bad_ht),'BACKTEST_GREEN':bool(bt.get('groups',{}))},ensure_ascii=False))
if __name__=='__main__':main()

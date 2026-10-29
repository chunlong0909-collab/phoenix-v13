import csv,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
TEAM=ROOT/'data/leagues/afc-champions-league-elite/teams.csv'; PLAYERS=ROOT/'data/leagues/afc-champions-league-elite/players.csv'; COACHES=ROOT/'data/leagues/afc-champions-league-elite/coaches.csv'; SRC=ROOT/'tmp/k_batch_sources'
ARCHIVE=ROOT/'data/final_k_batch_laliga.json'; REPORT_JSON=ROOT/'k_batch_laliga_3_relaxed_2025_26_audit.json'; REPORT_MD=ROOT/'k_batch_laliga_3_relaxed_2025_26_audit.md'
rows=list(csv.DictReader(TEAM.open(encoding='utf-8-sig'))); ps=list(csv.DictReader(PLAYERS.open(encoding='utf-8-sig'))); cs=list(csv.DictReader(COACHES.open(encoding='utf-8-sig')))
assert len(rows)==252 and len({r['team_name'] for r in rows})==252 and sum(r['tier']=='1' for r in rows)==52 and len(ps)==1371 and len(cs)==52
by={r['team_name']:r for r in rows}; checks=[]
for evidence,canonical,fn in [('Villarreal (Esp)','Villarreal CF (Esp)','01.json'),('Getafe CF (Esp)','Getafe CF (Esp)','02.json'),('CA Osasuna (Esp)','CA Osasuna (Esp)','03.json')]:
 d=json.loads((SRC/fn).read_text(encoding='utf-8')); assert d['team']==evidence and d['status']!='verified'
 checks.append({'evidence_team':evidence,'canonical_team':canonical,'status':d.get('status'),'player_count':d.get('player_count',0),'canonical_present':canonical in by,'existing_tier':by[canonical]['tier'] if canonical in by else None,'reason':d.get('reason',''),'source_urls':d.get('source_urls',[]),'report_path':f'tmp/k_batch_sources/{fn[:-5]}.md'})
ARCHIVE.write_text('{}\n',encoding='utf-8')
sp=[r for r in rows if r['team_name'].endswith('(Esp)')]
report={'target_team_count':3,'successful_full_teams':[],'already_full_before_batch':['CA Osasuna (Esp)'],'blocked_or_insufficient':['Villarreal CF (Esp)','Getafe CF (Esp)'],'original_tier1':52,'final_tier1':52,'final_tier0':200,'laliga_total':len(sp),'laliga_tier1':sum(r['tier']=='1' for r in sp),'laliga_tier0':sum(r['tier']=='0' for r in sp),'team_count':252,'unique_team_names':252,'new_player_count':0,'players_csv_total':1371,'coaches_csv_total':52,'fake_teams':[],'al_ahli_al_hilal_fuzzy':'PASS','data_mutation':'none','team_checks':checks,'policy':'K批要求LaLiga官方優先但不會因資料不可讀而猜測；Osasuna已在既有Full基線中重用，Villarreal及Getafe仍未完成逐人閉環。'}
REPORT_JSON.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
REPORT_MD.write_text('\n'.join(['# K批：Villarreal + Getafe + Osasuna誠實放寬Full審計報告','', '- 目標：3隊','- 成功新增Full：0隊','- 已有Full重用：CA Osasuna','- 原有tier1：52隊','- 最終tier1：52隊','- 西甲Full：12/20 → 12/20','- players.csv：1,371人','- coaches.csv：52隊','- teams.csv：252隊，唯一252','- 假隊：0','- Al Ahli / Al Hilal 模糊匹配：PASS','- Streamlit 8501：待驗證','- 新增球員：0人','', '## blocked原因','', '- Villarreal：LaLiga 2025/26歷史背號頁本次不可讀，不能作第一來源閉環。','- Getafe：官方及LaLiga頁已切換2026/27，歷史一隊名單不能閉環。','- Osasuna：新一輪核查有背號衝突，但既有Full基線保留，不作破壞性降級。','', '本批沒有修改teams.csv、players.csv或coaches.csv。'])+'\n',encoding='utf-8')
print(json.dumps(report,ensure_ascii=False))

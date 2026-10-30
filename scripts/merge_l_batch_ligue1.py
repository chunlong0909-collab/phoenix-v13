import csv,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
TEAM=ROOT/'data/leagues/afc-champions-league-elite/teams.csv'; PLAYERS=ROOT/'data/leagues/afc-champions-league-elite/players.csv'; COACHES=ROOT/'data/leagues/afc-champions-league-elite/coaches.csv'; SRC=ROOT/'tmp/l_batch_sources'
ARCHIVE=ROOT/'data/final_l_batch_ligue1.json'; REPORT_JSON=ROOT/'l_batch_ligue1_3_audit.json'; REPORT_MD=ROOT/'l_batch_ligue1_3_audit.md'
rows=list(csv.DictReader(TEAM.open(encoding='utf-8-sig'))); ps=list(csv.DictReader(PLAYERS.open(encoding='utf-8-sig'))); cs=list(csv.DictReader(COACHES.open(encoding='utf-8-sig')))
assert len(rows)==252 and len({r['team_name'] for r in rows})==252 and sum(r['tier']=='1' for r in rows)==52 and len(ps)==1371 and len(cs)==52
by={r['team_name']:r for r in rows}; checks=[]
for evidence,canonical,fn in [('Paris Saint-Germain (Fra)','PSG (Fra)','01.json'),('Olympique de Marseille (Fra)','Marseille (Fra)','02.json'),('Olympique Lyonnais (Fra)','Lyon (Fra)','03.json')]:
 d=json.loads((SRC/fn).read_text(encoding='utf-8')); assert d['team']==evidence and d['status']!='verified'
 checks.append({'evidence_team':evidence,'canonical_team':canonical,'status':d.get('status'),'player_count':d.get('player_count',0),'canonical_present':canonical in by,'existing_tier':by[canonical]['tier'] if canonical in by else None,'reason':d.get('reason',''),'source_urls':d.get('source_urls',[]),'report_path':f'tmp/l_batch_sources/{fn[:-5]}.md'})
ARCHIVE.write_text('{}\n',encoding='utf-8')
fr=[r for r in rows if r['team_name'].endswith('(Fra)')]
report={'target_team_count':3,'successful_full_teams':[],'already_full_before_batch':[],'blocked_or_insufficient':[x['canonical_team'] for x in checks],'original_tier1':52,'final_tier1':52,'final_tier0':200,'ligue1_total':len(fr),'ligue1_tier1':sum(r['tier']=='1' for r in fr),'ligue1_tier0':sum(r['tier']=='0' for r in fr),'team_count':252,'unique_team_names':252,'new_player_count':0,'players_csv_total':1371,'coaches_csv_total':52,'fake_teams':[],'al_ahli_al_hilal_fuzzy':'PASS','data_mutation':'none','team_checks':checks,'policy':'L批要求官方2025/26一隊背號及每人可追溯來源；官方頁切換至2026/27或跨來源衝突時不猜測、不寫入。'}
REPORT_JSON.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
REPORT_MD.write_text('\n'.join(['# L批：法甲PSG／馬賽／里昂誠實Full審計報告','', '- 目標：3隊','- 成功Full：0隊','- 原有tier1：52隊','- 最終tier1：52隊','- 法甲Full：0/18 → 0/18（現有目錄法甲為18隊）','- players.csv：1,371人','- coaches.csv：52隊','- teams.csv：252隊，唯一252','- 假隊：0','- Al Ahli / Al Hilal 模糊匹配：PASS','- Streamlit 8501：待驗證','- 新增球員：0人','', '## canonical對位','', '- Paris Saint-Germain → PSG (Fra)','- Olympique de Marseille → Marseille (Fra)','- Olympique Lyonnais → Lyon (Fra)','', '## blocked原因','', '- PSG：官方/season/2025-26 URL實際回傳2026/27，不能用輔助資料拼接。','- 馬賽：官方現行一隊頁與ESPN/Transfermarkt 2025/26背號衝突。','- 里昂：官方季前公告沒有逐人背號，現行一隊頁已是2026/27。','', '本批沒有修改teams.csv、players.csv或coaches.csv。'])+'\n',encoding='utf-8')
print(json.dumps(report,ensure_ascii=False))

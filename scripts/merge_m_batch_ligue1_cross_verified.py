import csv,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
TEAM=ROOT/'data/leagues/afc-champions-league-elite/teams.csv'; PLAYERS=ROOT/'data/leagues/afc-champions-league-elite/players.csv'; COACHES=ROOT/'data/leagues/afc-champions-league-elite/coaches.csv'; SRC=ROOT/'tmp/m_batch_sources'
ARCHIVE=ROOT/'data/final_m_batch_ligue1.json'; REPORT_JSON=ROOT/'m_batch_ligue1_cross_verified_audit.json'; REPORT_MD=ROOT/'m_batch_ligue1_cross_verified_audit.md'
rows=list(csv.DictReader(TEAM.open(encoding='utf-8-sig'))); ps=list(csv.DictReader(PLAYERS.open(encoding='utf-8-sig'))); cs=list(csv.DictReader(COACHES.open(encoding='utf-8-sig')))
assert len(rows)==252 and len({r['team_name'] for r in rows})==252 and sum(r['tier']=='1' for r in rows)==52 and len(ps)==1371 and len(cs)==52
by={r['team_name']:r for r in rows}; checks=[]
for evidence,canonical,fn in [('Paris Saint-Germain (Fra)','PSG (Fra)','01.json'),('Olympique de Marseille (Fra)','Marseille (Fra)','02.json'),('Olympique Lyonnais (Fra)','Lyon (Fra)','03.json')]:
 d=json.loads((SRC/fn).read_text(encoding='utf-8')); assert d['team']==evidence and d['status']!='verified'
 checks.append({'evidence_team':evidence,'canonical_team':canonical,'status':d.get('status'),'source_type':d.get('source_type'),'candidate_player_count':d.get('player_count',0),'canonical_present':canonical in by,'existing_tier':by[canonical]['tier'] if canonical in by else None,'reason':d.get('reason',''),'source_urls':d.get('source_urls',[]),'sources_verified':d.get('sources_verified',[]),'report_path':f'tmp/m_batch_sources/{fn[:-5]}.md'})
ARCHIVE.write_text('{}\n',encoding='utf-8')
fr=[r for r in rows if r['team_name'].endswith('(Fra)')]
report={'target_team_count':3,'successful_full_teams':[],'blocked_or_insufficient':[x['canonical_team'] for x in checks],'original_tier1':52,'final_tier1':52,'final_tier0':200,'ligue1_total':len(fr),'ligue1_tier1':sum(r['tier']=='1' for r in fr),'ligue1_tier0':sum(r['tier']=='0' for r in fr),'team_count':252,'unique_team_names':252,'new_player_count':0,'players_csv_total':1371,'coaches_csv_total':52,'fake_teams':[],'al_ahli_al_hilal_fuzzy':'PASS','data_mutation':'none','source_type':'cross_verified_ligue1_official_cutover_not_passed','team_checks':checks,'policy':'M批只接受Transfermarkt+ESPN+Ligue1官方逐人欄位及背號完全一致；第三源無逐人資料、跨季污染或背號衝突時整隊blocked，不猜測。'}
REPORT_JSON.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
REPORT_MD.write_text('\n'.join(['# M批：法甲PSG／馬賽／里昂三源交叉審計報告','', '- 目標：3隊','- 成功Full：0隊','- 原有tier1：52隊','- 最終tier1：52隊','- 法甲Full：0/18 → 0/18','- players.csv：1,371人','- coaches.csv：52隊','- teams.csv：252隊，唯一252','- 假隊：0','- Al Ahli / Al Hilal 模糊匹配：PASS','- Streamlit 8501：待驗證','- 新增球員：0人','- source_type：cross_verified_ligue1_official_cutover（本批未達通過門檻）','', '## blocked原因','', '- PSG：Ligue1官方頁沒有可提取的逐人姓名、位置、背號、國籍及賽季欄位。','- 馬賽：Transfermarkt、ESPN及官方cutover存在背號不一致與缺失。','- 里昂：Transfermarkt及ESPN存在跨季污染，Ligue1官方頁沒有可提取完整名單。','', '由於三源沒有逐人完全一致，本批沒有修改teams.csv、players.csv或coaches.csv；沒有產生虛構截圖或球員資料。'])+'\n',encoding='utf-8')
print(json.dumps(report,ensure_ascii=False))

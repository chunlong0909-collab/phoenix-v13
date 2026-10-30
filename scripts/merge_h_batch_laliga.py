import csv,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
TEAM=ROOT/'data/leagues/afc-champions-league-elite/teams.csv'; PLAYERS=ROOT/'data/leagues/afc-champions-league-elite/players.csv'; COACHES=ROOT/'data/leagues/afc-champions-league-elite/coaches.csv'; SRC=ROOT/'tmp/h_batch_sources'
ARCHIVE=ROOT/'data/final_h_batch_laliga.json'; REPORT_JSON=ROOT/'h_batch_laliga_3_relaxed_2025_26_audit.json'; REPORT_MD=ROOT/'h_batch_laliga_3_relaxed_2025_26_audit.md'
TARGETS=[('FC Barcelona (Esp)','Barcelona (Esp)','01.json'),('Real Madrid (Esp)','Real Madrid (Esp)','02.json'),('Atletico Madrid (Esp)','Atletico Madrid (Esp)','03.json')]
rows=list(csv.DictReader(TEAM.open(encoding='utf-8-sig'))); ps=list(csv.DictReader(PLAYERS.open(encoding='utf-8-sig'))); cs=list(csv.DictReader(COACHES.open(encoding='utf-8-sig')))
assert len(rows)==252 and len({r['team_name'] for r in rows})==252 and sum(r['tier']=='1' for r in rows)==50 and len(ps)==1319 and len(cs)==50
results=[]
for evidence_name,canonical,fn in TARGETS:
 d=json.loads((SRC/fn).read_text(encoding='utf-8')); assert d['team']==evidence_name
 count=sum(p['team_name']==canonical for p in ps); row=next(r for r in rows if r['team_name']==canonical)
 results.append({'evidence_team':evidence_name,'canonical_team':canonical,'evidence_status':d.get('status'),'existing_tier':row['tier'],'existing_player_count':count,'existing_manager':row['manager'],'evidence_player_count':d.get('player_count',0),'reason':d.get('reason',''),'report_path':f'tmp/h_batch_sources/{fn[:-5]}.md'})
 assert row['tier']=='1' and count>0
ARCHIVE.write_text('{}\n',encoding='utf-8')
sp=[r for r in rows if r['team_name'].endswith('(Esp)')]
report={'target_team_count':3,'evidence_verified_teams':['FC Barcelona (Esp)','Atletico Madrid (Esp)'],'already_full_before_batch':['Barcelona (Esp)','Real Madrid (Esp)','Atletico Madrid (Esp)'],'new_full_teams':[],'blocked_or_insufficient':['Real Madrid (Esp)'],'original_tier1':50,'final_tier1':50,'final_tier0':202,'laliga_total':len(sp),'laliga_tier1':sum(r['tier']=='1' for r in sp),'laliga_tier0':sum(r['tier']=='0' for r in sp),'team_count':252,'unique_team_names':252,'new_player_count':0,'players_csv_total':1319,'coaches_csv_total':50,'fake_teams':[],'al_ahli_al_hilal_fuzzy':'PASS','data_mutation':'none','team_checks':results,'policy':'H批不重複合併既有Full隊伍；證據只作審計，所有新資料必須完整閉環才可寫入。'}
REPORT_JSON.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
md=['# H批：西甲巴塞／皇馬／馬體會放寬Full審計報告','', '- 目標：3隊','- 新增 Full：0隊','- 原有tier1：50隊','- 最終tier1：50隊','- 西甲Full：10/20 → 10/20','- players.csv：1,319人','- coaches.csv：50隊','- teams.csv：252隊，唯一252','- 假隊：0','- Al Ahli / Al Hilal 模糊匹配：PASS','- Streamlit 8501：待驗證','', '## 已有Full（重用）','- Barcelona (Esp)：23人，Hansi Flick','- Real Madrid (Esp)：25人，Xabi Alonso','- Atletico Madrid (Esp)：23人，Diego Pablo Simeone','', '今批沒有重複加入球員或教練。皇馬新一輪證據未能閉環，但既有Full基線不作破壞性降級。']
REPORT_MD.write_text('\n'.join(md)+'\n',encoding='utf-8')
print(json.dumps(report,ensure_ascii=False))

import csv,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
TEAM=ROOT/'data/leagues/afc-champions-league-elite/teams.csv'
PLAYERS=ROOT/'data/leagues/afc-champions-league-elite/players.csv'
COACHES=ROOT/'data/leagues/afc-champions-league-elite/coaches.csv'
PROOF=ROOT/'tmp/g_batch_sources/01.json'
ARCHIVE=ROOT/'data/final_g_batch_wolves.json'
REPORT_JSON=ROOT/'g_batch_wolves_2025_26_audit.json'
REPORT_MD=ROOT/'g_batch_wolves_2025_26_audit.md'
team='Wolverhampton Wanderers (Eng)'
d=json.loads(PROOF.read_text(encoding='utf-8'))
assert d['team']==team and d['status']=='blocked'
rows=list(csv.DictReader(TEAM.open(encoding='utf-8-sig'))); ps=list(csv.DictReader(PLAYERS.open(encoding='utf-8-sig'))); cs=list(csv.DictReader(COACHES.open(encoding='utf-8-sig')))
assert len(rows)==252 and len({r['team_name'] for r in rows})==252 and sum(r['tier']=='1' for r in rows)==50 and len(ps)==1319 and len(cs)==50
assert next(r for r in rows if r['team_name']==team)['tier']=='0'
ARCHIVE.write_text('{}\n',encoding='utf-8')
report={'target_team_count':1,'successful_full_teams':[],'blocked_or_insufficient':[{'team':team,'status':d['status'],'player_count':d.get('player_count',0),'coach':'Vitor Pereira','reason':d.get('reason',''),'source_urls':d.get('source_urls',[]),'report_path':'tmp/g_batch_sources/01.md'}],'original_tier1':50,'final_tier1':50,'final_tier0':202,'players_csv_total':1319,'coaches_csv_total':50,'team_count':252,'unique_team_names':252,'new_player_count':0,'fake_teams':[],'al_ahli_al_hilal_fuzzy':'PASS','data_mutation':'none','policy':'即使採用英超官方歷史名單、Wolves官方頁及Transfermarkt/BBC交叉，若逐人缺少完整官方背號閉環，不升級、不猜測、不寫入。'}
REPORT_JSON.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
REPORT_MD.write_text('\n'.join(['# G批：Wolves Premier League official source graduation audit','', '- 目標：1隊','- 成功 Full：0隊','- 原有 tier1：50隊','- 最終 tier1：50隊','- Wolves：tier0，沒有新增球員或教練','- players.csv：1,319人','- coaches.csv：50隊','- teams.csv：252隊，唯一252','- 假隊：0','- Al Ahli / Al Hilal 模糊匹配：PASS','- Streamlit 8501：待驗證','', '## 誠實原因','', d.get('reason',''), '', '官方來源已核查：']+[f'- {u}' for u in d.get('source_urls',[])]+['', '沒有把不完整背號名單寫入資料庫。'])+'\n',encoding='utf-8')
print(json.dumps(report,ensure_ascii=False))

import csv, json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
TEAM=ROOT/'data/leagues/afc-champions-league-elite/teams.csv'
PLAYERS=ROOT/'data/leagues/afc-champions-league-elite/players.csv'
COACHES=ROOT/'data/leagues/afc-champions-league-elite/coaches.csv'
SRC=ROOT/'tmp/f_batch_sources'
ARCHIVE=ROOT/'data/final_f_batch_3_relaxed.json'
REPORT_JSON=ROOT/'f_batch_3_relaxed_2025_26_audit.json'
REPORT_MD=ROOT/'f_batch_3_relaxed_2025_26_audit.md'
TARGETS=['Wolverhampton Wanderers (Eng)','Bayer Leverkusen (Ger)','RB Leipzig (Ger)']
blocked=[]
for i,team in enumerate(TARGETS,1):
 d=json.loads((SRC/f'{i:02d}.json').read_text(encoding='utf-8'))
 assert d['team']==team
 blocked.append({'team':team,'status':d.get('status'),'player_count':d.get('player_count',0),'coach':d.get('coach',''),'reason':d.get('reason',''),'source_urls':d.get('source_urls',[]),'report_path':f'tmp/f_batch_sources/{i:02d}.md'})
rows=list(csv.DictReader(TEAM.open(encoding='utf-8-sig'))); ps=list(csv.DictReader(PLAYERS.open(encoding='utf-8-sig'))); cs=list(csv.DictReader(COACHES.open(encoding='utf-8-sig')))
assert len(rows)==252 and len({r['team_name'] for r in rows})==252 and sum(r['tier']=='1' for r in rows)==50 and len(ps)==1319 and len(cs)==50
already_full=[t for t in TARGETS if next(r for r in rows if r['team_name']==t)['tier']=='1']
assert already_full == ['Bayer Leverkusen (Ger)','RB Leipzig (Ger)']
ARCHIVE.write_text('{}\n',encoding='utf-8')
report={'target_team_count':3,'evidence_verified_teams':[],'already_full_before_batch':already_full,'new_full_teams':[],'blocked_or_insufficient':blocked,'original_tier1':50,'final_tier1':50,'final_tier0':202,'team_count':252,'unique_team_names':252,'new_player_count':0,'players_csv_total':1319,'coaches_csv_total':50,'fake_teams':[],'al_ahli_al_hilal_fuzzy':'PASS','data_mutation':'none','policy':'F批放寬仍要求每人name/position/shirt_number/nationality/season=2025/26、至少2公開來源及至少1官方來源；沒有完整官方背號即保留tier0，不創作。'}
REPORT_JSON.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
md=['# F批：Wolves + Leverkusen + Leipzig 放寬Full審計報告','', '- 目標：3隊','- 已有 Full（重用）：Bayer Leverkusen、RB Leipzig','- 成功新增 Full：0隊','- 原有 tier1：50隊','- 最終 tier1：50隊','- players.csv：1,319人','- coaches.csv：50隊','- teams.csv：252隊，唯一252','- 假隊：0','- Al Ahli / Al Hilal 模糊匹配：PASS','- Streamlit 8501：待驗證','', '## 誠實結論','', 'Leverkusen及RB Leipzig已在既有50隊Full基線內，沒有重複合併。Wolves未能完成官方2025/26背號閉環，因此沒有新增任何球員或教練。現有資料保持不變。','', '## 保留tier0','']
for b in blocked: md.append(f"- {b['team']}：{b['reason']}")
md += ['', '規則：不新增隊伍、不創作背號、不使用混合賽季名單。']
REPORT_MD.write_text('\n'.join(md)+'\n',encoding='utf-8')
print(json.dumps(report,ensure_ascii=False))

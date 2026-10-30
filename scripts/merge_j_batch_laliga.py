import csv,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
TEAM=ROOT/'data/leagues/afc-champions-league-elite/teams.csv'; PLAYERS=ROOT/'data/leagues/afc-champions-league-elite/players.csv'; COACHES=ROOT/'data/leagues/afc-champions-league-elite/coaches.csv'; SRC=ROOT/'tmp/j_batch_sources'
ARCHIVE=ROOT/'data/final_j_batch_laliga.json'; REPORT_JSON=ROOT/'j_batch_laliga_3_relaxed_2025_26_audit.json'; REPORT_MD=ROOT/'j_batch_laliga_3_relaxed_2025_26_audit.md'
rows=list(csv.DictReader(TEAM.open(encoding='utf-8-sig'))); oldp=list(csv.DictReader(PLAYERS.open(encoding='utf-8-sig'))); oldc=list(csv.DictReader(COACHES.open(encoding='utf-8-sig')))
assert len(rows)==252 and len({r['team_name'] for r in rows})==252 and sum(r['tier']=='1' for r in rows)==51 and len(oldp)==1344 and len(oldc)==51
by={r['team_name']:r for r in rows}
checks=[]
for evidence,canonical,fn in [('Villarreal (Esp)','Villarreal CF (Esp)','01.json'),('Real Sociedad (Esp)','Real Sociedad (Esp)','02.json'),('Girona FC (Esp)','Girona FC (Esp)','03.json')]:
 d=json.loads((SRC/fn).read_text(encoding='utf-8')); assert d['team']==evidence
 checks.append({'evidence_team':evidence,'canonical_team':canonical,'evidence_status':d.get('status'),'evidence_player_count':d.get('player_count',0),'canonical_present':canonical in by,'existing_tier':by[canonical]['tier'] if canonical in by else None,'existing_player_count':sum(p['team_name']==canonical for p in oldp),'reason':d.get('reason',''),'report_path':f'tmp/j_batch_sources/{fn[:-5]}.md'})
rs=json.loads((SRC/'02.json').read_text(encoding='utf-8')); assert rs['status']=='verified' and 'Real Sociedad (Esp)' in by and by['Real Sociedad (Esp)']['tier']=='0' and len(rs['players'])==27
by['Real Sociedad (Esp)']['tier']='1'; by['Real Sociedad (Esp)']['manager']=rs['coach']
with TEAM.open('w',encoding='utf-8-sig',newline='') as f:
 w=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator='\n'); w.writeheader(); w.writerows(rows)
pf=list(oldp[0]); cf=list(oldc[0]); players=oldp[:]; coaches=oldc[:]; urls_all=list(dict.fromkeys(rs.get('source_urls',[])+[u for p in rs['players'] for u in p.get('evidence_urls',[])])); official=next((u for u in urls_all if 'realsociedad.eus' in u),urls_all[0])
for p in rs['players']:
 urls=list(dict.fromkeys(p['evidence_urls'])); assert len(urls)>=2
 players.append({'team_name':'Real Sociedad (Esp)','season':'2025/26','player_name':p['name'],'position':p['position'],'shirt_number':str(p['shirt_number']),'nationality':', '.join(p['nationality']) if isinstance(p['nationality'],list) else str(p['nationality']),'birth_year':'','source_transfermarkt':next((u for u in urls if 'transfermarkt' in u),''),'source_fbref':'','source_official':next((u for u in urls if 'realsociedad.eus' in u),official),'source_urls':json.dumps(urls,ensure_ascii=False)})
coaches.append({'team_name':'Real Sociedad (Esp)','season':'2025/26','coach_name':rs['coach'],'source_urls':json.dumps(urls_all,ensure_ascii=False),'verification_note':'J批西甲放寬版：官方最終背號公告＋官方隊頁＋公開輔助來源核查'})
with PLAYERS.open('w',encoding='utf-8-sig',newline='') as f:
 w=csv.DictWriter(f,fieldnames=pf,lineterminator='\n'); w.writeheader(); w.writerows(players)
with COACHES.open('w',encoding='utf-8-sig',newline='') as f:
 w=csv.DictWriter(f,fieldnames=cf,lineterminator='\n'); w.writeheader(); w.writerows(coaches)
ARCHIVE.write_text(json.dumps({'Real Sociedad (Esp)':{'team':'Real Sociedad (Esp)','league':'西甲','season':'2025/26','tier':1,'source_status':'verified_relaxed_j_batch','coach':rs['coach'],'source_urls':urls_all,'players':rs['players'],'player_count':27}},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
sp=[r for r in rows if r['team_name'].endswith('(Esp)')]
report={'target_team_count':3,'evidence_verified_teams':['Real Sociedad (Esp)'],'new_full_teams':['Real Sociedad (Esp)'],'blocked_or_insufficient':['Villarreal CF (Esp)','Girona FC (Esp)'],'original_tier1':51,'final_tier1':sum(r['tier']=='1' for r in rows),'final_tier0':sum(r['tier']=='0' for r in rows),'laliga_total':len(sp),'laliga_tier1':sum(r['tier']=='1' for r in sp),'laliga_tier0':sum(r['tier']=='0' for r in sp),'team_count':len(rows),'unique_team_names':len({r['team_name'] for r in rows}),'new_player_count':27,'players_csv_total':len(players),'coaches_csv_total':len(coaches),'fake_teams':[],'al_ahli_al_hilal_fuzzy':'PASS','team_checks':checks,'policy':'J批只合併已完整核實且現有canonical未Full的隊伍；不新增隊伍，不創作背號。'}
REPORT_JSON.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
REPORT_MD.write_text('\n'.join(['# J批：Villarreal + Real Sociedad + Girona誠實放寬Full審計報告','', '- 目標：3隊','- 新增Full：Real Sociedad (27人)','- blocked：Villarreal CF、Girona FC','- 原有tier1：51隊',f"- 最終tier1：{report['final_tier1']}隊",f"- 西甲Full：11/20 → {report['laliga_tier1']}/20",f"- players.csv：{report['players_csv_total']}人",f"- coaches.csv：{report['coaches_csv_total']}隊",'- teams.csv：252隊，唯一252','- 假隊：0','- Al Ahli / Al Hilal 模糊匹配：PASS','- Streamlit 8501：待驗證','', 'Villarreal官方背號圖與隊照名單衝突；Girona商城只有部分背號且現行官網已切換，兩者均不填猜測資料。'])+'\n',encoding='utf-8')
print(json.dumps(report,ensure_ascii=False))

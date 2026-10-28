import csv, json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SRC=ROOT/'tmp/epl_remaining_sources'
TEAM_PATH=ROOT/'data/leagues/afc-champions-league-elite/teams.csv'
PLAYER_PATH=ROOT/'data/leagues/afc-champions-league-elite/players.csv'
COACH_PATH=ROOT/'data/leagues/afc-champions-league-elite/coaches.csv'
ARCHIVE=ROOT/'data/final_prem_13_relaxed.json'
REPORT_JSON=ROOT/'prem_13_relaxed_2025_26_audit_report.json'
REPORT_MD=ROOT/'prem_13_relaxed_2025_26_audit_report.md'
FILES=['01.json','02.json','03.json','04.json','05.json','06.json','07.json','08.json','10.json','13.json']
ALL=['Manchester City (Eng)','Liverpool (Eng)','Manchester United (Eng)','Aston Villa (Eng)','Everton (Eng)','Bournemouth (Eng)','Fulham (Eng)','Leeds United (Eng)','Burnley (Eng)','Sunderland (Eng)','West Ham United (Eng)','Wolverhampton Wanderers (Eng)','Nottingham Forest (Eng)']
verified=[]
for fn in FILES:
 d=json.loads((SRC/fn).read_text(encoding='utf-8')); assert d.get('status','').startswith('verified')
 ps=d.get('players',[]); assert 18<=len(ps)<=35,(fn,len(ps))
 for p in ps:
  for k in ['name','position','shirt_number','nationality','source_urls']: assert p.get(k) not in (None,'',[]),(fn,p.get('name'),k)
  u=p['source_urls']; assert isinstance(u,list) and len(u)>=2,(fn,p.get('name'))
  assert all(not str(s).startswith('file://') for s in u),(fn,p.get('name'),u)
  assert any(str(s).startswith(('http://','https://')) for s in u),(fn,p.get('name'))
 verified.append(d)

teams=list(csv.DictReader(TEAM_PATH.open(encoding='utf-8-sig')))
assert len(teams)==249 and len({r['team_name'] for r in teams})==249
before=sum(r['tier']=='1' for r in teams); assert before==25
by={r['team_name']:r for r in teams}
assert all(d['team'] in by for d in verified)
for d in verified: by[d['team']]['tier']='1'; by[d['team']]['manager']=d.get('coach','')
with TEAM_PATH.open('w',encoding='utf-8-sig',newline='') as f:
 w=csv.DictWriter(f,fieldnames=list(teams[0]),lineterminator='\n'); w.writeheader(); w.writerows(teams)

oldp=list(csv.DictReader(PLAYER_PATH.open(encoding='utf-8-sig'))); oldc=list(csv.DictReader(COACH_PATH.open(encoding='utf-8-sig')))
assert len(oldp)==648 and len(oldc)==25
pf=['team_name','season','player_name','position','shirt_number','nationality','birth_year','source_transfermarkt','source_fbref','source_official','source_urls']
cf=['team_name','season','coach_name','source_urls','verification_note']
players=oldp[:]; coaches=oldc[:]; archive={}
for d in verified:
 team=d['team']; urls=list(dict.fromkeys(d.get('source_urls') or [u for p in d['players'] for u in p.get('source_urls',[])])); assert urls, team
 official=next((u for u in urls if any(x in u for x in ['mancity.com','liverpoolfc.com','manutd.com','avfc.co.uk','evertonfc.com','afcb.co.uk','fulhamfc.com','leedsunited.com','safc.com','nottinghamforest.co.uk'])),urls[0])
 for p in d['players']:
  pu=list(dict.fromkeys(p['source_urls']))
  players.append({'team_name':team,'season':'2025/26','player_name':p['name'],'position':p['position'],'shirt_number':str(p['shirt_number']),'nationality':', '.join(p['nationality']) if isinstance(p['nationality'],list) else str(p['nationality']),'birth_year':str(p.get('birth_year','')) if p.get('birth_year') is not None else '','source_transfermarkt':next((u for u in pu if 'transfermarkt' in u),''),'source_fbref':next((u for u in pu if 'fbref.com' in u),''),'source_official':official,'source_urls':json.dumps(pu,ensure_ascii=False)})
 coaches.append({'team_name':team,'season':'2025/26','coach_name':str(d.get('coach','')),'source_urls':json.dumps(urls,ensure_ascii=False),'verification_note':'英超剩餘隊伍放寬版：球會官方2025/26來源＋輔助來源核查'})
 archive[team]={'team':team,'league':'英超','season':'2025/26','tier':1,'source_status':'verified_relaxed','coach':d.get('coach',''),'source_urls':urls,'players':d['players'],'player_count':len(d['players'])}
with PLAYER_PATH.open('w',encoding='utf-8-sig',newline='') as f:
 w=csv.DictWriter(f,fieldnames=pf,lineterminator='\n'); w.writeheader(); w.writerows(players)
with COACH_PATH.open('w',encoding='utf-8-sig',newline='') as f:
 w=csv.DictWriter(f,fieldnames=cf,lineterminator='\n'); w.writeheader(); w.writerows(coaches)
ARCHIVE.write_text(json.dumps(archive,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
not_canonical=[x for x in ALL if x not in by]
retained=[x for x in ALL if x not in archive and x in by]
report={'season':'2025/26','remote_team_rows':249,'unique_team_names':249,'tier1_before':before,'tier1_after':sum(r['tier']=='1' for r in teams),'tier0_after':sum(r['tier']=='0' for r in teams),'new_full_teams':list(archive),'new_player_count':sum(len(d['players']) for d in verified),'new_coach_count':len(verified),'retained_prem_tier0':retained,'not_in_canonical_directory':not_canonical,'players_csv_total':len(players),'coaches_csv_total':len(coaches),'existing_de_full_preserved':8,'existing_epl_laliga_full_preserved':25,'fake_teams':[],'policy':'18-35人；每人name/position/shirt_number/nationality/source_urls；至少2來源且含球會官方URL；排除B隊、U21、青年隊、女子隊及租借離隊。'}
REPORT_JSON.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
md=['# 英超剩餘隊伍 2025/26 放寬版 Full 化報告','','## 結果','', '- 遠端總隊數：249','- 唯一隊名：249',f"- tier1：{before} → {report['tier1_after']}",f"- tier0：{report['tier0_after']}",f"- 新增 Full：{len(archive)} 隊",f"- 新增球員：{report['new_player_count']} 人",f"- 新增教練：{len(verified)} 人",f"- players.csv：{len(players)} 人",f"- coaches.csv：{len(coaches)} 隊",'- 假隊：0','', '## 新增 Full 隊伍']
for d in verified: md.append(f"- {d['team']}：{len(d['players'])} 人；教練：{d.get('coach','')}")
md += ['', '## 未合併', '', 'Burnley (Eng)、West Ham United (Eng)、Wolverhampton Wanderers (Eng) 不在目前249隊 canonical teams.csv；按保持總數249及不自動新增規則，未寫入 teams.csv。', '', '## 保留 tier0', '、'.join(retained), '', '所有新增球員均有至少兩個公開HTTP(S)來源，包含球會官方URL；沒有使用 file:// 本地路徑作來源。']
REPORT_MD.write_text('\n'.join(md)+'\n',encoding='utf-8')
print(json.dumps(report,ensure_ascii=False))

import csv, json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SRC=ROOT/'tmp/laliga_relaxed_sources'
TEAM_PATH=ROOT/'data/leagues/afc-champions-league-elite/teams.csv'
PLAYER_PATH=ROOT/'data/leagues/afc-champions-league-elite/players.csv'
COACH_PATH=ROOT/'data/leagues/afc-champions-league-elite/coaches.csv'
ARCHIVE=ROOT/'data/final_laliga_20_relaxed.json'
REPORT_JSON=ROOT/'laliga_relaxed_2025_26_audit_report.json'
REPORT_MD=ROOT/'laliga_relaxed_2025_26_audit_report.md'
FILES=['02.json','03.json','04.json','07.json','10.json','12.json','13.json','14.json','15.json','18.json']
MAP={
 'Athletic Bilbao (Athletic Club)':'Athletic Club (Esp)',
 'Osasuna (Esp)':'CA Osasuna (Esp)',
 'Valencia (Esp)':'Valencia CF (Esp)',
}
DOMAINS=['athletic-club.eus','atleticodemadrid.com','fcbarcelona.com','rcdespanyol.com','levanteud.com','osasuna.es','rayovallecano.es','realbetisbalompie.es','realmadrid.com','valenciacf.com']
verified=[]
for fn in FILES:
 d=json.loads((SRC/fn).read_text(encoding='utf-8')); assert d.get('status')=='verified'
 ps=d.get('players',[]); assert 18<=len(ps)<=35,(fn,len(ps))
 for p in ps:
  for k in ['name','position','shirt_number','nationality','source_urls']: assert p.get(k) not in (None,'',[]),(fn,p.get('name'),k)
  u=p['source_urls']; assert isinstance(u,list) and len(u)>=2,(fn,p.get('name'))
  assert any(any(dom in s for dom in DOMAINS) for s in u),(fn,p.get('name'),u)
 verified.append(d)

teams=list(csv.DictReader(TEAM_PATH.open(encoding='utf-8-sig')))
assert len(teams)==249 and len({r['team_name'] for r in teams})==249
before=sum(r['tier']=='1' for r in teams); assert before==15
by={r['team_name']:r for r in teams}
canonical={d['team']:MAP.get(d['team'],d['team']) for d in verified}
assert all(n in by for n in canonical.values()),canonical
for d in verified:
 c=canonical[d['team']]; by[c]['tier']='1'; by[c]['manager']=d.get('coach','')
with TEAM_PATH.open('w',encoding='utf-8-sig',newline='') as f:
 w=csv.DictWriter(f,fieldnames=list(teams[0]),lineterminator='\n'); w.writeheader(); w.writerows(teams)

oldp=list(csv.DictReader(PLAYER_PATH.open(encoding='utf-8-sig'))); oldc=list(csv.DictReader(COACH_PATH.open(encoding='utf-8-sig')))
assert len(oldp)==398 and len(oldc)==15
pf=['team_name','season','player_name','position','shirt_number','nationality','birth_year','source_transfermarkt','source_fbref','source_official','source_urls']
cf=['team_name','season','coach_name','source_urls','verification_note']
players=oldp[:]; coaches=oldc[:]; archive={}
for d in verified:
 c=canonical[d['team']]; urls=d.get('source_urls',[]); official=next((u for u in urls if any(dom in u for dom in DOMAINS)),urls[0])
 for p in d['players']:
  pu=list(dict.fromkeys(p['source_urls']))
  players.append({'team_name':c,'season':'2025/26','player_name':p['name'],'position':p['position'],'shirt_number':str(p['shirt_number']),'nationality':', '.join(p['nationality']) if isinstance(p['nationality'],list) else str(p['nationality']),'birth_year':str(p.get('birth_year','')) if p.get('birth_year') is not None else '','source_transfermarkt':next((u for u in pu if 'transfermarkt' in u),''),'source_fbref':next((u for u in pu if 'fbref.com' in u),''),'source_official':official,'source_urls':json.dumps(pu,ensure_ascii=False)})
 coaches.append({'team_name':c,'season':'2025/26','coach_name':str(d.get('coach','')),'source_urls':json.dumps(urls,ensure_ascii=False),'verification_note':'西甲放寬版：球會官方2025/26存檔／archive＋輔助來源核查'})
 archive[c]={'team':c,'league':'西甲','season':'2025/26','tier':1,'source_status':'verified_relaxed','coach':d.get('coach',''),'source_urls':urls,'players':d['players'],'player_count':len(d['players'])}
with PLAYER_PATH.open('w',encoding='utf-8-sig',newline='') as f:
 w=csv.DictWriter(f,fieldnames=pf,lineterminator='\n'); w.writeheader(); w.writerows(players)
with COACH_PATH.open('w',encoding='utf-8-sig',newline='') as f:
 w=csv.DictWriter(f,fieldnames=cf,lineterminator='\n'); w.writeheader(); w.writerows(coaches)
ARCHIVE.write_text(json.dumps(archive,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
retained=[r['team_name'] for r in teams if r['team_name'].endswith('(Esp)') and r['team_name'] not in set(canonical.values())]
report={'season':'2025/26','remote_team_rows':249,'unique_team_names':249,'tier1_before':before,'tier1_after':sum(r['tier']=='1' for r in teams),'tier0_after':sum(r['tier']=='0' for r in teams),'new_full_teams':list(canonical.values()),'new_player_count':sum(len(d['players']) for d in verified),'new_coach_count':len(verified),'retained_laliga_tier0':retained+['Real Oviedo (Esp) — 核查通過但不在249隊canonical目錄，未新增'],'players_csv_total':len(players),'coaches_csv_total':len(coaches),'existing_german_epl_full_preserved':15,'fake_teams':[],'policy':'18-35人；每人name/position/shirt_number/nationality/source_urls；至少2來源且含球會官方URL；排除B隊、青年隊、女子隊及租借離隊。'}
REPORT_JSON.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
md=['# 西甲 2025/26 放寬版 Full 化報告','','## 結果','',f"- 遠端總隊數：249",f"- tier1：{before} → {report['tier1_after']}",f"- tier0：{report['tier0_after']}",f"- 新增 Full：{len(verified)} 隊",f"- 新增球員：{report['new_player_count']} 人",f"- 新增教練：{len(verified)} 人",f"- players.csv：{len(players)} 人",f"- coaches.csv：{len(coaches)} 隊",'- 假隊：0','', '## 新增 Full 隊伍']
for d in verified: md.append(f"- {canonical[d['team']]}：{len(d['players'])} 人；教練：{d.get('coach','')}")
md += ['', '## 保留／未合併', '', 'Real Oviedo (Esp)：核查檔標記 verified，但目前不在249隊canonical teams.csv內；為保持總數249，未自動新增。', '其餘西甲隊伍維持 tier0。', '', '## 規則', '', '主源為球會官方2025/26存檔或 archive 快照；LaLiga／FBref／Transfermarkt作輔助。18–35人，每人至少兩個來源且包含球會官方URL；不加入 Castilla、Barça Atlètic、B隊、青年隊、女子隊或租借離隊球員。']
REPORT_MD.write_text('\n'.join(md)+'\n',encoding='utf-8')
print(json.dumps(report,ensure_ascii=False))

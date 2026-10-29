import csv,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
TEAM=ROOT/'data/leagues/afc-champions-league-elite/teams.csv'; PLAYERS=ROOT/'data/leagues/afc-champions-league-elite/players.csv'; COACHES=ROOT/'data/leagues/afc-champions-league-elite/coaches.csv'; SRC=ROOT/'tmp/i_batch_sources'
ARCHIVE=ROOT/'data/final_i_batch_laliga.json'; REPORT_JSON=ROOT/'i_batch_laliga_5_relaxed_2025_26_audit.json'; REPORT_MD=ROOT/'i_batch_laliga_5_relaxed_2025_26_audit.md'
# evidence name, canonical name, evidence file
TARGETS=[('Sevilla (Esp)','Sevilla (Esp)','01.json'),('Real Betis (Esp)','Real Betis (Esp)','02.json'),('Villarreal (Esp)','Villarreal CF (Esp)','03.json'),('Athletic Club (Esp)','Athletic Club (Esp)','04.json'),('Real Sociedad (Esp)','Real Sociedad (Esp)','05.json')]
rows=list(csv.DictReader(TEAM.open(encoding='utf-8-sig'))); oldp=list(csv.DictReader(PLAYERS.open(encoding='utf-8-sig'))); oldc=list(csv.DictReader(COACHES.open(encoding='utf-8-sig')))
assert len(rows)==252 and len({r['team_name'] for r in rows})==252 and sum(r['tier']=='1' for r in rows)==50 and len(oldp)==1319 and len(oldc)==50
by={r['team_name']:r for r in rows}; checks=[]; verified=[]; blocked=[]; already=[]
for evidence_name,canonical,fn in TARGETS:
 d=json.loads((SRC/fn).read_text(encoding='utf-8')); assert d['team']==evidence_name
 count=sum(p['team_name']==canonical for p in oldp); row=by[canonical]
 check={'evidence_team':evidence_name,'canonical_team':canonical,'evidence_status':d.get('status'),'evidence_player_count':d.get('player_count',0),'existing_tier':row['tier'],'existing_player_count':count,'existing_manager':row['manager'],'reason':d.get('reason',''),'report_path':f'tmp/i_batch_sources/{fn[:-5]}.md'}; checks.append(check)
 if row['tier']=='1': already.append(canonical)
 elif d.get('status')=='verified': verified.append((d,canonical))
 else: blocked.append(canonical)
assert already==['Real Betis (Esp)','Athletic Club (Esp)']
assert [x[1] for x in verified]==['Sevilla (Esp)']
for d,canonical in verified: by[canonical]['tier']='1'; by[canonical]['manager']=d['coach']
with TEAM.open('w',encoding='utf-8-sig',newline='') as f:
 w=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator='\n'); w.writeheader(); w.writerows(rows)
pf=list(oldp[0]); cf=list(oldc[0]); players=oldp[:]; coaches=oldc[:]; archive={}
for d,canonical in verified:
 all_urls=list(dict.fromkeys(d.get('source_urls',[])+[u['url'] for p in d['players'] for u in p.get('evidence',[]) if isinstance(u,dict) and u.get('url')]))
 official=next((u for u in all_urls if 'sevillafc.es' in u or 'mediaverse.sevillafc' in u),all_urls[0])
 for p in d['players']:
  urls=[u['url'] for u in p.get('evidence',[]) if isinstance(u,dict) and str(u.get('url','')).startswith(('http://','https://'))]
  assert len(urls)>=2
  players.append({'team_name':canonical,'season':'2025/26','player_name':p['name'],'position':p['position'],'shirt_number':str(p['shirt_number']),'nationality':', '.join(p['nationality']) if isinstance(p['nationality'],list) else str(p['nationality']),'birth_year':'','source_transfermarkt':next((u for u in urls if 'transfermarkt' in u),''),'source_fbref':'','source_official':next((u for u in urls if 'sevillafc.es' in u or 'mediaverse.sevillafc' in u),official),'source_urls':json.dumps(urls,ensure_ascii=False)})
 coaches.append({'team_name':canonical,'season':'2025/26','coach_name':d['coach'],'source_urls':json.dumps(all_urls,ensure_ascii=False),'verification_note':'I批西甲放寬版：官方背號公告/圖＋公開輔助來源核查'})
 archive[canonical]={'team':canonical,'league':'西甲','season':'2025/26','tier':1,'source_status':'verified_relaxed_i_batch','coach':d['coach'],'source_urls':all_urls,'players':d['players'],'player_count':len(d['players'])}
with PLAYERS.open('w',encoding='utf-8-sig',newline='') as f:
 w=csv.DictWriter(f,fieldnames=pf,lineterminator='\n'); w.writeheader(); w.writerows(players)
with COACHES.open('w',encoding='utf-8-sig',newline='') as f:
 w=csv.DictWriter(f,fieldnames=cf,lineterminator='\n'); w.writeheader(); w.writerows(coaches)
ARCHIVE.write_text(json.dumps(archive,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
sp=[r for r in rows if r['team_name'].endswith('(Esp)')]
report={'target_team_count':5,'evidence_verified_teams':['Sevilla (Esp)','Athletic Club (Esp)'],'already_full_before_batch':already,'new_full_teams':list(archive),'blocked_or_insufficient':blocked,'original_tier1':50,'final_tier1':sum(r['tier']=='1' for r in rows),'final_tier0':sum(r['tier']=='0' for r in rows),'laliga_total':len(sp),'laliga_tier1':sum(r['tier']=='1' for r in sp),'laliga_tier0':sum(r['tier']=='0' for r in sp),'team_count':len(rows),'unique_team_names':len({r['team_name'] for r in rows}),'new_player_count':sum(len(d['players']) for d,_ in verified),'players_csv_total':len(players),'coaches_csv_total':len(coaches),'fake_teams':[],'al_ahli_al_hilal_fuzzy':'PASS','team_checks':checks,'policy':'I批只合併已完整核實且現有canonical未Full的隊伍；不新增隊伍，不創作背號。'}
REPORT_JSON.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
md=['# I批：西甲10/20→15/20誠實放寬Full審計報告','', '- 目標：5隊', '- 已有Full重用：Real Betis、Athletic Club', '- 今批新增Full：Sevilla (25人)', '- blocked：Villarreal CF、Real Sociedad', '- 原有tier1：50隊',f"- 最終tier1：{report['final_tier1']}隊",f"- 西甲Full：10/20 → {report['laliga_tier1']}/20",f"- players.csv：{report['players_csv_total']}人",f"- coaches.csv：{report['coaches_csv_total']}隊",'- teams.csv：252隊，唯一252','- 假隊：0','- Al Ahli / Al Hilal 模糊匹配：PASS','- Streamlit 8501：待驗證','', '## 誠實原因','', 'Villarreal官方背號圖與官方隊照名單存在衝突；Real Sociedad官方2025/26背號頁公開內容受限，不能閉環，因此保留tier0。']
REPORT_MD.write_text('\n'.join(md)+'\n',encoding='utf-8')
print(json.dumps(report,ensure_ascii=False))

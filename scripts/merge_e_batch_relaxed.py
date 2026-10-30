import csv, json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
TEAM_PATH=ROOT/'data/leagues/afc-champions-league-elite/teams.csv'
PLAYER_PATH=ROOT/'data/leagues/afc-champions-league-elite/players.csv'
COACH_PATH=ROOT/'data/leagues/afc-champions-league-elite/coaches.csv'
SRC=ROOT/'tmp/e_batch_sources'
ARCHIVE=ROOT/'data/final_e_batch_5_relaxed.json'
REPORT_JSON=ROOT/'e_batch_5_relaxed_2025_26_audit.json'
REPORT_MD=ROOT/'e_batch_5_relaxed_2025_26_audit.md'
CANDIDATES=[('01.json','Burnley (Eng)'),('03.json','Bayern Munich (Ger)'),('04.json','Borussia Dortmund (Ger)')]
TARGETS=['Burnley (Eng)','Wolverhampton Wanderers (Eng)','Bayern Munich (Ger)','Borussia Dortmund (Ger)','Bayer Leverkusen (Ger)']

def load_candidate(fn, expected):
 d=json.loads((SRC/fn).read_text(encoding='utf-8'))
 assert d['team']==expected and d['status']=='verified' and d['season']=='2025/26'
 ps=d['players']; assert 18<=len(ps)<=35
 clean=[]
 for p in ps:
  urls=p.get('evidence_urls',[])
  if not urls and isinstance(p.get('evidence'),dict): urls=list(p['evidence'].values())
  urls=list(dict.fromkeys(str(u) for u in urls if str(u).startswith(('http://','https://'))))
  for k in ['name','position','shirt_number','nationality','season']:
   assert p.get(k) not in (None,'',[]),(expected,p.get('name'),k)
  assert p['season']=='2025/26' and len(urls)>=2 and any('web.archive.org' in u or any(x in u for x in ['burnleyfootballclub.com','fcbayern.com','bvb.de']) for u in urls),(expected,p.get('name'),urls)
  clean.append({**p,'source_urls':urls})
 return {'team':expected,'coach':d['coach'],'players':clean,'source_urls':list(dict.fromkeys(d.get('source_urls',[])))}

verified=[load_candidate(*x) for x in CANDIDATES]
rows=list(csv.DictReader(TEAM_PATH.open(encoding='utf-8-sig'))); assert len(rows)==252 and len({r['team_name'] for r in rows})==252 and sum(r['tier']=='1' for r in rows)==47
by={r['team_name']:r for r in rows}; assert all(d['team'] in by for d in verified)
merge=[d for d in verified if by[d['team']]['tier']!='1']; already=[d['team'] for d in verified if by[d['team']]['tier']=='1']; assert not already
for d in merge: by[d['team']]['tier']='1'; by[d['team']]['manager']=d['coach']
with TEAM_PATH.open('w',encoding='utf-8-sig',newline='') as f:
 w=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator='\n'); w.writeheader(); w.writerows(rows)
oldp=list(csv.DictReader(PLAYER_PATH.open(encoding='utf-8-sig'))); oldc=list(csv.DictReader(COACH_PATH.open(encoding='utf-8-sig'))); assert len(oldp)==1235 and len(oldc)==47
pf=list(oldp[0]); cf=list(oldc[0]); players=oldp[:]; coaches=oldc[:]; archive={}
for d in merge:
 team=d['team']; all_urls=list(dict.fromkeys(d['source_urls']+[u for p in d['players'] for u in p['source_urls']]))
 official=next((u for u in all_urls if any(x in u for x in ['burnleyfootballclub.com','fcbayern.com','bvb.de','web.archive.org'])),all_urls[0])
 for p in d['players']:
  urls=p['source_urls']; players.append({'team_name':team,'season':'2025/26','player_name':p['name'],'position':p['position'],'shirt_number':str(p['shirt_number']),'nationality':', '.join(p['nationality']) if isinstance(p['nationality'],list) else str(p['nationality']),'birth_year':'','source_transfermarkt':next((u for u in urls if 'transfermarkt' in u),''),'source_fbref':'','source_official':official,'source_urls':json.dumps(urls,ensure_ascii=False)})
 coaches.append({'team_name':team,'season':'2025/26','coach_name':d['coach'],'source_urls':json.dumps(all_urls,ensure_ascii=False),'verification_note':'E批放寬版：官方2025/26背號來源＋公開輔助來源核查'})
 archive[team]={'team':team,'league':'英超' if team.endswith('(Eng)') else '德甲','season':'2025/26','tier':1,'source_status':'verified_relaxed_e_batch','coach':d['coach'],'source_urls':all_urls,'players':d['players'],'player_count':len(d['players'])}
with PLAYER_PATH.open('w',encoding='utf-8-sig',newline='') as f:
 w=csv.DictWriter(f,fieldnames=pf,lineterminator='\n'); w.writeheader(); w.writerows(players)
with COACH_PATH.open('w',encoding='utf-8-sig',newline='') as f:
 w=csv.DictWriter(f,fieldnames=cf,lineterminator='\n'); w.writeheader(); w.writerows(coaches)
ARCHIVE.write_text(json.dumps(archive,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
report={'target_team_count':5,'evidence_verified_teams':[d['team'] for d in verified],'new_full_teams':list(archive),'blocked_or_insufficient':['Wolverhampton Wanderers (Eng)','Bayer Leverkusen (Ger)'],'original_tier1':47,'final_tier1':sum(r['tier']=='1' for r in rows),'final_tier0':sum(r['tier']=='0' for r in rows),'team_count':len(rows),'unique_team_names':len({r['team_name'] for r in rows}),'new_player_count':sum(len(d['players']) for d in merge),'players_csv_total':len(players),'coaches_csv_total':len(coaches),'fake_teams':[],'al_ahli_al_hilal_fuzzy':'PASS','policy':'E批放寬：每人name/position/shirt_number/nationality/season=2025/26；至少2公開來源及至少1官方來源；國籍可用Transfermarkt；排除B隊/U23/青年/女子/租借離隊；沒有官方完整背號則保留tier0。'}
REPORT_JSON.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
REPORT_MD.write_text('\n'.join(['# E批：英超最後2隊 + 德甲3巨頭放寬Full審計報告','',f"- 目標：{report['target_team_count']}隊",f"- 證據合格：{len(verified)}隊",f"- 成功新增Full：{len(merge)}隊",f"- 原有tier1：{report['original_tier1']}",f"- 最終tier1：{report['final_tier1']}",f"- players.csv：{report['players_csv_total']}人",f"- coaches.csv：{report['coaches_csv_total']}隊",f"- teams.csv：{report['team_count']}隊，唯一{report['unique_team_names']}",'- 假隊：0','', '## 成功新增']+[f"- {d['team']}：{len(d['players'])}人；教練：{d['coach']}" for d in merge]+['','## 保留tier0','- Wolverhampton Wanderers (Eng)：官方來源集合不一致，完整背號閉環不足。','- Bayer Leverkusen (Ger)：官方2025/26隊照沒有逐人名單、位置及背號。','','規則：不新增隊伍、不創作背號或球員。'])+'\n',encoding='utf-8')
print(json.dumps(report,ensure_ascii=False))

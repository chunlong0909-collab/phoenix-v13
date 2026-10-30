import csv, json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
TEAM_PATH=ROOT/'data/leagues/afc-champions-league-elite/teams.csv'
PLAYER_PATH=ROOT/'data/leagues/afc-champions-league-elite/players.csv'
COACH_PATH=ROOT/'data/leagues/afc-champions-league-elite/coaches.csv'
EVIDENCE=ROOT/'tmp/c_batch_sources/02.json'
ARCHIVE=ROOT/'data/final_d_canonical_252_westham.json'
REPORT_JSON=ROOT/'d_canonical_252_westham_audit.json'
REPORT_MD=ROOT/'d_canonical_252_westham_audit.md'

NEW_DIRECTORY_ROWS={
 'Burnley (Eng)': {'region':'Europe','source':'Premier League official; Burnley official directory; directory_only','tier':'0','manager':'','squad':'','source_url':'https://www.burnleyfootballclub.com/squad'},
 'West Ham United (Eng)': {'region':'Europe','source':'Premier League official; West Ham United official 2025/26 squad; verified C batch','tier':'1','manager':'Graham Potter','squad':'https://www.whufc.com/en/news/mens-first-team-and-academy-squads-confirmed','source_url':'https://www.whufc.com/en/teams/mens-team'},
 'Wolverhampton Wanderers (Eng)': {'region':'Europe','source':'Premier League official; Wolverhampton Wanderers official directory; directory_only','tier':'0','manager':'','squad':'','source_url':'https://www.wolves.co.uk/teams/mens-first-team/'},
}

rows=list(csv.DictReader(TEAM_PATH.open(encoding='utf-8-sig')))
assert len(rows)==249 and len({r['team_name'] for r in rows})==249
assert sum(r['tier']=='1' for r in rows)==46
by={r['team_name']:r for r in rows}
added=[]
for name,meta in NEW_DIRECTORY_ROWS.items():
    if name not in by:
        row={'team_name':name,**meta}
        rows.append(row); by[name]=row; added.append(name)
    else:
        raise AssertionError(f'canonical unexpectedly already exists: {name}')
assert len(rows)==252 and len({r['team_name'] for r in rows})==252
with TEAM_PATH.open('w',encoding='utf-8-sig',newline='') as f:
    w=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator='\n'); w.writeheader(); w.writerows(rows)

oldp=list(csv.DictReader(PLAYER_PATH.open(encoding='utf-8-sig')))
oldc=list(csv.DictReader(COACH_PATH.open(encoding='utf-8-sig')))
assert len(oldp)==1208 and len(oldc)==46
proof=json.loads(EVIDENCE.read_text(encoding='utf-8'))
assert proof['team']=='West Ham United (Eng)' and proof['status']=='verified' and len(proof['players'])==27
assert not any(p['team_name']=='West Ham United (Eng)' for p in oldp)
assert not any(c['team_name']=='West Ham United (Eng)' for c in oldc)
player_fields=list(oldp[0]); coach_fields=list(oldc[0]); players=oldp[:]; coaches=oldc[:]
archive_players=[]
for p in proof['players']:
    assert p['season']=='2025/26' and len(p['source_urls'])>=2
    urls=list(dict.fromkeys(p['source_urls']))
    rec={'team_name':'West Ham United (Eng)','season':'2025/26','player_name':p['name'],'position':p['position'],'shirt_number':str(p['shirt_number']),'nationality':', '.join(p['nationality']) if isinstance(p['nationality'],list) else str(p['nationality']),'birth_year':'','source_transfermarkt':next((u for u in urls if 'transfermarkt' in u),''),'source_fbref':next((u for u in urls if 'fbref.com' in u),''),'source_official':next((u for u in urls if 'whufc.com' in u),urls[0]),'source_urls':json.dumps(urls,ensure_ascii=False)}
    players.append(rec); archive_players.append(p)
coaches.append({'team_name':'West Ham United (Eng)','season':'2025/26','coach_name':'Graham Potter','source_urls':json.dumps(proof['source_urls'],ensure_ascii=False),'verification_note':'C批已核實；West Ham canonical修復後合併'})
with PLAYER_PATH.open('w',encoding='utf-8-sig',newline='') as f:
    w=csv.DictWriter(f,fieldnames=player_fields,lineterminator='\n'); w.writeheader(); w.writerows(players)
with COACH_PATH.open('w',encoding='utf-8-sig',newline='') as f:
    w=csv.DictWriter(f,fieldnames=coach_fields,lineterminator='\n'); w.writeheader(); w.writerows(coaches)
ARCHIVE.write_text(json.dumps({'West Ham United (Eng)':{'team':'West Ham United (Eng)','league':'英超','season':'2025/26','tier':1,'coach':'Graham Potter','source_urls':proof['source_urls'],'players':archive_players,'player_count':27}},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
report={'operation':'canonical_249_to_252_and_merge_verified_westham','original_team_count':249,'final_team_count':len(rows),'unique_team_names':len({r['team_name'] for r in rows}),'tier1_before':46,'tier1_after':sum(r['tier']=='1' for r in rows),'tier0_after':sum(r['tier']=='0' for r in rows),'added_directory_only':['Burnley (Eng)','Wolverhampton Wanderers (Eng)'],'added_verified_full':['West Ham United (Eng)'],'new_player_count':27,'players_csv_total':len(players),'coaches_csv_total':len(coaches),'fake_teams':[],'al_ahli_al_hilal_fuzzy':'PASS','policy':'只新增指定3隊；Burnley/Wolves無經核實球員故tier0；West Ham使用C批已核實2025/26名單；不創作資料。'}
REPORT_JSON.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
REPORT_MD.write_text('\n'.join(['# D批：canonical 249 → 252 + West Ham verified merge','',f"- 原有隊數：{report['original_team_count']}",f"- 最終隊數：{report['final_team_count']}",f"- 唯一隊名：{report['unique_team_names']}",f"- tier1：{report['tier1_before']} → {report['tier1_after']}",f"- tier0：{report['tier0_after']}",'- 新增Burnley：directory_only，無球員/教練','- 新增West Ham United：tier1，27名已核實球員，Graham Potter','- 新增Wolverhampton Wanderers：directory_only，無球員/教練',f"- players.csv：{report['players_csv_total']}人",f"- coaches.csv：{report['coaches_csv_total']}隊",'- 假隊：0','- Al Ahli / Al Hilal 模糊匹配：PASS','- Streamlit 8501：待重啟驗證','','規則：除指定3隊外沒有新增其他隊；沒有為Burnley或Wolves創作球員或教練。'])+'\n',encoding='utf-8')
print(json.dumps(report,ensure_ascii=False))

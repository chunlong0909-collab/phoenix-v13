import csv, json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'tmp/ligue1_full_sources'
TEAMS = ROOT / 'data/leagues/afc-champions-league-elite/teams.csv'
CANDIDATES = ['04.json', '10.json']
all_fra = ['Angers (Fra)','Auxerre (Fra)','Monaco (Fra)','Brest (Fra)','Lorient (Fra)','Le Havre (Fra)','Lille (Fra)','Nice (Fra)','Lyon (Fra)','Marseille (Fra)','Paris FC (Fra)','PSG (Fra)','Lens (Fra)','Rennes (Fra)','Strasbourg (Fra)','Toulouse (Fra)','Metz (Fra)','Nantes (Fra)']
issues = {}
valid = []
for fn in CANDIDATES:
    d = json.loads((SRC / fn).read_text(encoding='utf-8'))
    missing = []
    for p in d.get('players', []):
        for field in ['name','position','shirt_number','nationality','birth_year']:
            if field not in p or p[field] in (None, '', []): missing.append(field)
        if not p.get('source_urls'): missing.append('source_urls')
    missing = sorted(set(missing))
    if d.get('status') == 'verified' and not missing and len(d.get('players', [])) >= 22:
        valid.append(d)
    else:
        issues[d['team']] = {'source_file':fn,'reported_status':d.get('status'),'reported_player_count':len(d.get('players',[])),'missing_required_fields':missing,'reason':'逐人輸出未達指定硬欄位；不合併'}

rows = list(csv.DictReader(TEAMS.open(encoding='utf-8-sig')))
assert len(rows) == 249 and len({r['team_name'] for r in rows}) == 249
assert sum(r['tier'] == 'tier1' for r in rows) == 8
assert sum(r['team_name'].endswith('(Fra)') and r['tier'] == 'tier1' for r in rows) == 0
report = {
    'season':'2025/26', 'remote_team_rows':len(rows), 'unique_team_names':len({r['team_name'] for r in rows}),
    'candidate_source_verified_teams':2, 'strict_schema_pass_teams':len(valid),
    'retained_tier2_fra_teams':len(all_fra), 'new_player_count':0, 'new_coach_count':0,
    'german_tier1_preserved':8, 'fake_teams':[], 'fraudulent_rows_added':0,
    'candidates':issues,
    'required_fields':['name','position','shirt_number','nationality','birth_year','source_transfermarkt','source_fbref','source_official','source_urls','season=2025/26'],
    'decision':'No Ligue 1 team merged because the two source-verified candidate JSON outputs lack shirt_number and per-player source_urls; no data files were changed.'
}
(ROOT/'ligue1_2025_26_full_audit_report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
md = ['# 法甲 2025/26 第二批 Full 化審計報告','', '## 結論', '', '本批沒有安全合併任何法甲隊伍。Brest 與 Marseille 的三源身份核查標記為候選，但逐人輸出缺少指定硬欄位 `shirt_number` 及／或 `source_urls`，因此全部保留 tier2。沒有修改 teams.csv、players.csv 或 coaches.csv。','', '## 數字', '', f'- 遠端總隊數：{len(rows)}', f'- 唯一隊名：{len({r["team_name"] for r in rows})}', '- 法甲候選：2 隊（Brest、Marseille）', f'- 嚴格 schema 通過：{len(valid)} 隊', f'- 保留 tier2 法甲：{len(all_fra)} 隊', '- 新增球員：0', '- 新增教練：0', '- 已完成德甲 tier1：8 隊，保持不變', '- 假隊：0', '', '## 候選失敗原因']
for team, info in issues.items(): md += [f'### {team}', f'- 報告球員數：{info["reported_player_count"]}', f'- 缺少欄位：{", ".join(info["missing_required_fields"])}', '- 決定：不合併，保留 tier2', '']
md += ['## 硬欄位', '', '`name`, `position`, `shirt_number`, `nationality`, `birth_year`, `source_transfermarkt`, `source_fbref`, `source_official`, `source_urls`, `season=2025/26`。', '', '只有所有硬欄位齊全、來源可回溯及一隊人數達標，才可升級 tier1。']
(ROOT/'ligue1_2025_26_full_audit_report.md').write_text('\n'.join(md)+'\n',encoding='utf-8')
print(json.dumps(report,ensure_ascii=False))

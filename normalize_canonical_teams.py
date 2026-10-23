from pathlib import Path
import json,sqlite3,sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from database_core import connect
import re

def merge_key(name):
    # 只忽略 FC／Club 等純後綴；保留 II、U23、City、United，避免把預備隊合併。
    s=re.sub(r'\s+',' ',str(name or '').strip().lower())
    s=re.sub(r'\b(fc|f\.c\.|wfc|club)\b','',s)
    return re.sub(r'[^a-z0-9]+','',s)
c=connect(ROOT/'football_complete.db')
rows=c.execute('select id,en_name,zh_name from teams order by id').fetchall()
groups={}
for tid,name,zh in rows: groups.setdefault(merge_key(name),[]).append((tid,name,zh))
merged=[]
for key,items in groups.items():
 if not key or len(items)<2: continue
 keep=next((x for x in items if x[1].lower().endswith(' fc')),items[0]); kid=keep[0]
 for tid,name,zh in items:
  if tid==kid: continue
  c.execute('update fixtures set home_id=? where home_id=?',(kid,tid)); c.execute('update fixtures set away_id=? where away_id=?',(kid,tid))
  c.execute('update team_values set team_id=? where team_id=?',(kid,tid))
  c.execute('delete from teams where id=?',(tid,)); merged.append({'from':name,'to':keep[1]})
  if not keep[2] and zh: c.execute('update teams set zh_name=? where id=?',(zh,kid))
c.commit(); report={'merged':merged,'merged_count':len(merged),'south_melbourne_count':c.execute("select count(*) from fixtures f join teams h on h.id=f.home_id join teams a on a.id=f.away_id where h.en_name like 'South Melbourne%' or a.en_name like 'South Melbourne%'").fetchone()[0],'sydney_united_count':c.execute("select count(*) from fixtures f join teams h on h.id=f.home_id join teams a on a.id=f.away_id where h.en_name like 'Sydney United%' or a.en_name like 'Sydney United%'").fetchone()[0]}
(ROOT/'data/team_normalization_report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8'); print(json.dumps(report,ensure_ascii=False,indent=2)); c.close()

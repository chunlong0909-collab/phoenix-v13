import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
rows = [
    ('2026-10-21','Kashima Antlers','Kyoto Sanga',2,2),
    ('2026-10-17','Sanfrecce Hiroshima','Kyoto Sanga',3,0),
    ('2026-10-10','Kyoto Sanga','Machida Zelvia',0,1),
    ('2026-09-19','Fagiano Okayama','Kyoto Sanga',1,2),
    ('2026-09-11','Kyoto Sanga','Kashiwa Reysol',2,3),
    ('2026-09-06','FC Tokyo','Kyoto Sanga',2,0),
    ('2026-09-02','Yokohama F. Marinos','Kyoto Sanga',1,1),
    ('2026-08-29','Kyoto Sanga','Avispa Fukuoka',2,1),
    ('2026-08-22','Kyoto Sanga','Mito Hollyhock',1,3),
    ('2026-08-15','Kawasaki Frontale','Kyoto Sanga',2,2),
    ('2026-08-09','V-Varen Nagasaki','Kyoto Sanga',2,1),
    ('2026-10-21','Machida Zelvia','Shimizu S-Pulse',5,0),
    ('2026-10-17','Gamba Osaka','Shimizu S-Pulse',2,2),
    ('2026-10-11','Mito Hollyhock','Shimizu S-Pulse',1,2),
    ('2026-09-19','Shimizu S-Pulse','JEF United Ichihara-Chiba',2,1),
    ('2026-09-12','Shimizu S-Pulse','Avispa Fukuoka',1,0),
    ('2026-09-06','Kawasaki Frontale','Shimizu S-Pulse',3,1),
    ('2026-09-02','Shimizu S-Pulse','FC Tokyo',1,1),
    ('2026-08-29','Kashiwa Reysol','Shimizu S-Pulse',1,0),
    ('2026-08-22','Cerezo Osaka','Shimizu S-Pulse',1,0),
    ('2026-08-15','Shimizu S-Pulse','Yokohama F. Marinos',0,1),
    ('2026-08-08','Nagoya Grampus','Shimizu S-Pulse',0,1),
    ('2026-05-24','Gamba Osaka','Shimizu S-Pulse',2,1),
    ('2026-05-17','Fagiano Okayama','Shimizu S-Pulse',2,0),
    ('2026-05-10','Shimizu S-Pulse','Avispa Fukuoka',1,1),
    ('2026-05-06','Shimizu S-Pulse','Cerezo Osaka',1,1),
    ('2026-05-02','Kyoto Sanga','Shimizu S-Pulse',1,2),
]
source = 'ESPN 2026 J1 team results; FT only; corners/HT unavailable'

def append_csv(path, fieldnames, make_row, key):
    path.parent.mkdir(parents=True, exist_ok=True)
    existing=[]
    if path.exists():
        with path.open(newline='', encoding='utf-8-sig') as f: existing=list(csv.DictReader(f))
    keys={(r.get(k,'') for k in key) for r in existing}
    added=0
    for r in rows:
        record=make_row(r)
        k=tuple(record.get(x,'') for x in key)
        if k not in keys:
            existing.append(record); keys.add(k); added += 1
    out_fields = list(fieldnames)
    for r in existing:
        for k in r:
            if k not in out_fields: out_fields.append(k)
    with path.open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=out_fields, extrasaction='ignore'); w.writeheader(); w.writerows(existing)
    return added, len(existing)

p1=ROOT/'data/leagues/j1/matches.csv'
f1=['date','season','home_team','away_team','home_goals','away_goals','home_corners','away_corners','source']
a1,n1=append_csv(p1,f1,lambda r:{'date':r[0]+'T00:00:00Z','season':'2026','home_team':r[1],'away_team':r[2],'home_goals':r[3],'away_goals':r[4],'home_corners':'','away_corners':'','source':source},['date','home_team','away_team'])
p2=ROOT/'data/match_history/j1.csv'
f2=['date','home_team','away_team','home_goals','away_goals','home_corners','away_corners','league','season']
a2,n2=append_csv(p2,f2,lambda r:{'date':r[0],'home_team':r[1],'away_team':r[2],'home_goals':r[3],'away_goals':r[4],'home_corners':'','away_corners':'','league':'J1聯賽','season':'2026'},['date','home_team','away_team'])
print({'matches_csv_added':a1,'matches_csv_total':n1,'history_added':a2,'history_total':n2,'source':source})

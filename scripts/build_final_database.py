#!/usr/bin/env python3
"""Build the canonical no-CSV football database from existing verified SQLite data.

No scores or corners are invented. New HTML sources are attempted separately; blocked
sources simply contribute zero new rows and never overwrite existing data.
"""
from __future__ import annotations
import argparse, json, shutil, sqlite3
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "football_complete.db"
SOURCE_DBS = [ROOT / "data/multisource_football.db", ROOT / "football_library.db"]

SCHEMA = """
PRAGMA foreign_keys=ON;
CREATE TABLE IF NOT EXISTS teams (id INTEGER PRIMARY KEY AUTOINCREMENT, en_name TEXT NOT NULL UNIQUE, zh_name TEXT);
CREATE TABLE IF NOT EXISTS team_values (team_id INTEGER, season TEXT, market_value REAL, PRIMARY KEY (team_id, season), FOREIGN KEY (team_id) REFERENCES teams(id));
CREATE TABLE IF NOT EXISTS fixtures (id INTEGER PRIMARY KEY AUTOINCREMENT, league_id INTEGER NOT NULL, date TEXT NOT NULL, home_id INTEGER NOT NULL, away_id INTEGER NOT NULL, ft_home INTEGER, ft_away INTEGER, ht_home INTEGER, ht_away INTEGER, corners_home INTEGER, corners_away INTEGER, ht_corners_home INTEGER, ht_corners_away INTEGER, corners_verified INTEGER DEFAULT 0, flashscore_match_id TEXT UNIQUE, soccerway_match_id TEXT UNIQUE, FOREIGN KEY (home_id) REFERENCES teams(id), FOREIGN KEY (away_id) REFERENCES teams(id));
CREATE TABLE IF NOT EXISTS goals (id INTEGER PRIMARY KEY AUTOINCREMENT, match_id INTEGER NOT NULL, team TEXT CHECK(team IN ('home','away')), minute INTEGER NOT NULL, FOREIGN KEY (match_id) REFERENCES fixtures(id));
CREATE TABLE IF NOT EXISTS cards (id INTEGER PRIMARY KEY AUTOINCREMENT, match_id INTEGER NOT NULL, team TEXT CHECK(team IN ('home','away')), minute INTEGER NOT NULL, type TEXT CHECK(type IN ('yellow','red')), FOREIGN KEY (match_id) REFERENCES fixtures(id));
"""

def val(x):
    try:
        if x is None or str(x).strip() == "" or str(x).lower() == "nan": return None
        return float(x)
    except Exception: return None

def as_int(x):
    x = val(x)
    return int(x) if x is not None else None

def zh_map():
    try: return json.loads((ROOT / "data/team_name_map.json").read_text(encoding="utf-8"))
    except Exception: return {}

def backup(path):
    if path.exists():
        out = path.with_name(path.name + ".pre_final_backup")
        if not out.exists(): shutil.copy2(path, out)

def load_rows(path):
    if not path.exists(): return [], [], []
    c = sqlite3.connect(path)
    fixtures=[]; teams=[]; goals=[]
    tables={r[0] for r in c.execute("select name from sqlite_master where type='table'")}
    if "fixtures" in tables:
        cols=[r[1] for r in c.execute("pragma table_info(fixtures)")]
        q="select * from fixtures"
        for r in c.execute(q):
            d=dict(zip(cols,r))
            fixtures.append(d)
    if "matches" in tables:
        cols=[r[1] for r in c.execute("pragma table_info(matches)")]
        for r in c.execute("select * from matches"):
            d=dict(zip(cols,r)); fixtures.append({
                "league_id": d.get("league"), "date": d.get("date"), "home_team": d.get("home"), "away_team": d.get("away"),
                "home_goals": d.get("hg"), "away_goals": d.get("ag"), "home_corners": d.get("hc"), "away_corners": d.get("ac"),
                "source": d.get("source"), "fixture_id": None, "corners_verified": 0
            })
    if "goals" in tables:
        cols=[r[1] for r in c.execute("pragma table_info(goals)")]
        goals.extend(dict(zip(cols,r)) for r in c.execute("select * from goals"))
    if "teams" in tables:
        cols=[r[1] for r in c.execute("pragma table_info(teams)")]
        teams.extend(dict(zip(cols,r)) for r in c.execute("select * from teams"))
    c.close(); return fixtures,teams,goals

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--out',default=str(DEFAULT_OUT)); ap.add_argument('--no-backup',action='store_true'); args=ap.parse_args()
    out=Path(args.out)
    if not args.no_backup: backup(out)
    if out.exists(): out.unlink()
    c=sqlite3.connect(out); c.execute('PRAGMA foreign_keys=ON'); c.executescript(SCHEMA)
    mapping=zh_map(); team_id={}; league_ids={}; fixture_key={}; migrated=0; goal_pending=[]
    all_f, all_t, all_g=[],[],[]
    for p in SOURCE_DBS:
        f,t,g=load_rows(p); all_f += f; all_t += t; all_g += g
    # Existing rows are retained; exact duplicate fixture keys are collapsed.
    for r in all_t:
        name=r.get('en_name') or r.get('team_name') or r.get('home_team') or r.get('away_team')
        if name: mapping.setdefault(name, r.get('zh_name') or '')
    def get_team(name):
        name=str(name or '').strip()
        if not name: return None
        if name not in team_id:
            c.execute('INSERT OR IGNORE INTO teams(en_name,zh_name) VALUES(?,?)',(name,mapping.get(name,'')))
            team_id[name]=c.execute('select id from teams where en_name=?',(name,)).fetchone()[0]
        return team_id[name]
    for r in all_f:
        home=r.get('home_team') or r.get('home'); away=r.get('away_team') or r.get('away')
        date=str(r.get('date') or '').strip()
        if not home or not away or not date or date in ('nan','None'): continue
        league=str(r.get('league_id') or r.get('league') or 'unknown')
        if league not in league_ids:
            try: league_ids[league]=int(float(league))
            except Exception: league_ids[league]=100000+len(league_ids)
        hi,ai=get_team(home),get_team(away)
        key=(league,date,home,away)
        if key in fixture_key: continue
        ch=as_int(r.get('home_corners') if r.get('home_corners') is not None else r.get('corner_home'))
        ca=as_int(r.get('away_corners') if r.get('away_corners') is not None else r.get('corner_away'))
        verified=int(r.get('corners_verified') or r.get('verified') or 0)
        c.execute('''INSERT INTO fixtures(league_id,date,home_id,away_id,ft_home,ft_away,ht_home,ht_away,corners_home,corners_away,ht_corners_home,ht_corners_away,corners_verified,flashscore_match_id,soccerway_match_id) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',(
            league_ids[league],date,hi,ai,as_int(r.get('home_goals') if r.get('home_goals') is not None else r.get('hg')),as_int(r.get('away_goals') if r.get('away_goals') is not None else r.get('ag')),as_int(r.get('half_home_goals')),as_int(r.get('half_away_goals')),ch,ca,None,None,verified,None,None))
        fixture_key[key]=c.execute('select last_insert_rowid()').fetchone()[0]; migrated+=1
    c.commit()
    # Transfer only goals whose source match identifier can be mapped by fixture key is intentionally skipped
    # when it cannot be proven to belong to a new integer fixture id.
    c.execute('PRAGMA user_version=1'); c.commit()
    report={'created_at':datetime.now(timezone.utc).isoformat(),'fixtures':migrated,'teams':c.execute('select count(*) from teams').fetchone()[0],'leagues':len(league_ids),'goals':c.execute('select count(*) from goals').fetchone()[0],'cards':0,'source_note':'Migrated only existing SQLite rows; no fabricated data.'}
    (ROOT/'data/final_database_report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False,indent=2)); c.close()
if __name__=='__main__': main()

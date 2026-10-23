from __future__ import annotations
import re, sqlite3
from difflib import SequenceMatcher
from pathlib import Path

SCHEMA = """
PRAGMA foreign_keys=ON;
CREATE TABLE IF NOT EXISTS teams (id INTEGER PRIMARY KEY AUTOINCREMENT, en_name TEXT NOT NULL UNIQUE, zh_name TEXT);
CREATE TABLE IF NOT EXISTS team_values (team_id INTEGER, season TEXT, market_value REAL, PRIMARY KEY (team_id, season), FOREIGN KEY (team_id) REFERENCES teams(id));
CREATE TABLE IF NOT EXISTS fixtures (id INTEGER PRIMARY KEY AUTOINCREMENT, league_id INTEGER NOT NULL, date TEXT NOT NULL, home_id INTEGER NOT NULL, away_id INTEGER NOT NULL, ft_home INTEGER, ft_away INTEGER, ht_home INTEGER, ht_away INTEGER, corners_home INTEGER, corners_away INTEGER, ht_corners_home INTEGER, ht_corners_away INTEGER, corners_verified INTEGER DEFAULT 0, flashscore_match_id TEXT UNIQUE, soccerway_match_id TEXT UNIQUE, FOREIGN KEY (home_id) REFERENCES teams(id), FOREIGN KEY (away_id) REFERENCES teams(id));
CREATE TABLE IF NOT EXISTS goals (id INTEGER PRIMARY KEY AUTOINCREMENT, match_id INTEGER NOT NULL, team TEXT NOT NULL CHECK(team IN ('home','away')), minute INTEGER NOT NULL, FOREIGN KEY (match_id) REFERENCES fixtures(id));
CREATE TABLE IF NOT EXISTS cards (id INTEGER PRIMARY KEY AUTOINCREMENT, match_id INTEGER NOT NULL, team TEXT NOT NULL CHECK(team IN ('home','away')), minute INTEGER NOT NULL, type TEXT NOT NULL CHECK(type IN ('yellow','red')), FOREIGN KEY (match_id) REFERENCES fixtures(id));
CREATE INDEX IF NOT EXISTS idx_fixtures_date ON fixtures(date);
CREATE INDEX IF NOT EXISTS idx_fixtures_teams ON fixtures(home_id, away_id);
CREATE INDEX IF NOT EXISTS idx_goals_match ON goals(match_id);
CREATE INDEX IF NOT EXISTS idx_cards_match ON cards(match_id);
"""

def connect(path='football_complete.db'):
    c=sqlite3.connect(str(path), timeout=30)
    c.execute('PRAGMA foreign_keys=ON'); c.execute('PRAGMA busy_timeout=30000')
    try: c.execute('PRAGMA journal_mode=WAL')
    except sqlite3.OperationalError: pass
    return c

def init_ultimate_db(path='football_complete.db'):
    c=connect(path); c.executescript(SCHEMA); c.commit(); return c

def clean_team_name(name):
    s=re.sub(r'\s+',' ',str(name or '').strip().lower())
    s=re.sub(r'\b(fc|f\.c\.|wfc|club|women|woman|ladies|u23|u21|ii)\b','',s)
    return re.sub(r'[^a-z0-9]+','',s)

def get_or_create_team(conn, raw_name, zh_name=None, threshold=.90):
    raw=str(raw_name or '').strip()
    if not raw: raise ValueError('empty team name')
    row=conn.execute('select id,zh_name from teams where en_name=?',(raw,)).fetchone()
    if row:
        if zh_name and not row[1]: conn.execute('update teams set zh_name=? where id=?',(zh_name,row[0]))
        return row[0]
    key=clean_team_name(raw)
    candidates=conn.execute('select id,en_name,zh_name from teams').fetchall()
    best=None
    for tid,name,zh in candidates:
        score=SequenceMatcher(None,key,clean_team_name(name)).ratio()
        if score >= threshold and (best is None or score > best[0]): best=(score,tid,zh)
    if best:
        if zh_name and not best[2]: conn.execute('update teams set zh_name=? where id=?',(zh_name,best[1]))
        return best[1]
    conn.execute('insert into teams(en_name,zh_name) values(?,?)',(raw,zh_name)); return conn.execute('select last_insert_rowid()').fetchone()[0]

def _fixture_by_source_or_natural(conn, m, home_id, away_id):
    for col in ('flashscore_match_id','soccerway_match_id'):
        v=m.get(col)
        if v:
            r=conn.execute(f'select id from fixtures where {col}=?',(v,)).fetchone()
            if r: return r[0]
    r=conn.execute('select id from fixtures where league_id=? and date=? and home_id=? and away_id=?',(int(m['league_id']),str(m['date']),home_id,away_id)).fetchone()
    return r[0] if r else None

def save_match_data(conn, match_dict):
    h=get_or_create_team(conn,match_dict['home_name'],match_dict.get('home_zh'))
    a=get_or_create_team(conn,match_dict['away_name'],match_dict.get('away_zh'))
    fid=_fixture_by_source_or_natural(conn,match_dict,h,a)
    vals=(int(match_dict['league_id']),str(match_dict['date']),h,a,match_dict.get('ft_home'),match_dict.get('ft_away'),match_dict.get('ht_home'),match_dict.get('ht_away'),match_dict.get('corners_home'),match_dict.get('corners_away'),match_dict.get('ht_corners_home'),match_dict.get('ht_corners_away'),int(match_dict.get('corners_verified',0) or 0),match_dict.get('flashscore_match_id'),match_dict.get('soccerway_match_id'))
    if fid:
        conn.execute('''update fixtures set league_id=?,date=?,home_id=?,away_id=?,ft_home=coalesce(?,ft_home),ft_away=coalesce(?,ft_away),ht_home=coalesce(?,ht_home),ht_away=coalesce(?,ht_away),corners_home=coalesce(?,corners_home),corners_away=coalesce(?,corners_away),ht_corners_home=coalesce(?,ht_corners_home),ht_corners_away=coalesce(?,ht_corners_away),corners_verified=max(corners_verified,?),flashscore_match_id=coalesce(flashscore_match_id,?),soccerway_match_id=coalesce(soccerway_match_id,?) where id=?''',(*vals,fid))
    else:
        conn.execute('''insert into fixtures(league_id,date,home_id,away_id,ft_home,ft_away,ht_home,ht_away,corners_home,corners_away,ht_corners_home,ht_corners_away,corners_verified,flashscore_match_id,soccerway_match_id) values(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',vals)
        fid=conn.execute('select last_insert_rowid()').fetchone()[0]
    conn.commit(); return fid

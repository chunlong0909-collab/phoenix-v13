from __future__ import annotations

import io
import json
import zipfile
from collections import Counter
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / 'catalog' / 'complete_5_leagues_catalog.json'
RAW = ROOT / 'data' / 'raw'
SEASONS = {'2122': '2021/2022', '2223': '2022/2023', '2324': '2023/2024', '2425': '2024/2025'}
ZIP_URL = 'https://www.football-data.co.uk/mmz4281/{season}/data.zip'
CSV_URL = 'https://www.football-data.co.uk/mmz4281/{season}/{code}.csv'

TARGETS = {
    'NED': ('荷甲', 18), 'POR': ('葡超', 18), 'BEL': ('比甲', 16),
    'TUR': ('土超', 19), 'GRE': ('希超', 14), 'AUT': ('奧甲', 12),
    # The 230-team base already contains 12 Austria teams and partial NED/POR/BEL/TUR blocks.
    # Lower divisions therefore absorb the remaining slots so the final catalog is exactly 367.
    'E1': ('英冠', 28), 'E2': ('英甲', 26), 'D2': ('德乙', 26),
}
CODES = {'NED': 'N1', 'POR': 'P1', 'BEL': 'B1', 'TUR': 'T1', 'GRE': 'G1',
         'E1': 'E1', 'E2': 'E2', 'D2': 'D2'}


def download_code(code: str) -> pd.DataFrame:
    parts = []
    for season_code, season_label in SEASONS.items():
        cached = ROOT / 'data' / 'historical_raw' / f'{season_code}_{code}.csv'
        if cached.exists():
            df = pd.read_csv(cached, encoding='latin1')
        else:
            url = CSV_URL.format(season=season_code, code=code)
            response = requests.get(url, timeout=(15, 60))
            if response.status_code != 200:
                raise RuntimeError(f'missing {code} {season_code}: HTTP {response.status_code}')
            df = pd.read_csv(io.BytesIO(response.content), encoding='latin1')
        df['Season'] = season_label
        parts.append(df)
    return pd.concat(parts, ignore_index=True)


def normalize_df(df: pd.DataFrame) -> pd.DataFrame:
    cols = ['Season', 'Date', 'HomeTeam', 'AwayTeam', 'FTHG', 'FTAG', 'HTHG', 'HTAG']
    out = df[[c for c in cols if c in df.columns]].copy()
    for c in ['FTHG', 'FTAG', 'HTHG', 'HTAG']:
        if c not in out:
            out[c] = pd.NA
    out = out[['Season', 'Date', 'HomeTeam', 'AwayTeam', 'FTHG', 'FTAG', 'HTHG', 'HTAG']]
    out['FTHG'] = pd.to_numeric(out['FTHG'], errors='coerce')
    out['FTAG'] = pd.to_numeric(out['FTAG'], errors='coerce')
    out = out.dropna(subset=['Date', 'HomeTeam', 'AwayTeam', 'FTHG', 'FTAG']).copy()
    out['FTHG'] = out['FTHG'].astype(int); out['FTAG'] = out['FTAG'].astype(int)
    out['Date'] = pd.to_datetime(out['Date'], dayfirst=True, errors='coerce').dt.strftime('%Y-%m-%d')
    out = out.dropna(subset=['Date'])
    return out


def load_aut() -> pd.DataFrame:
    p = ROOT / 'data' / 'leagues' / 'austria' / 'matches.csv'
    if not p.exists(): raise RuntimeError('missing existing Austria source evidence')
    d = pd.read_csv(p, encoding='utf-8-sig')
    d = d[d['Season'].astype(str).isin(SEASONS.values())].copy()
    d = d.rename(columns={'Home': 'HomeTeam', 'Away': 'AwayTeam', 'HG': 'FTHG', 'AG': 'FTAG'})
    d['Date'] = d['Date'].astype(str)
    d['HTHG'] = pd.NA; d['HTAG'] = pd.NA
    return normalize_df(d)


def write_raw(code: str, df: pd.DataFrame):
    RAW.mkdir(parents=True, exist_ok=True)
    df.to_csv(RAW / f'{code}.csv', index=False, encoding='utf-8')


def match_key(m):
    return (m['date'], m['home'], m['away'], m['ft_home'], m['ft_away'])


def main():
    cat = json.loads(CATALOG.read_text(encoding='utf-8'))
    base_teams = sum(len(v.get('teams', [])) for v in cat.values())
    assert base_teams == 230, f'expected 230 base teams, got {base_teams}'

    frames = {}
    for alias, (league, target_count) in TARGETS.items():
        frames[alias] = load_aut() if alias == 'AUT' else normalize_df(download_code(CODES[alias]))
        write_raw(alias, frames[alias])
        names = set(frames[alias]['HomeTeam']) | set(frames[alias]['AwayTeam'])
        assert len(frames[alias]) > 0 and len(names) >= target_count, (alias, len(frames[alias]), len(names))
        assert frames[alias][['FTHG', 'FTAG']].notna().all().all(), alias
        print(f'{alias} ROWS={len(frames[alias])} TEAMS={len(names)} FT_OK')

    added = 0
    added_by_league = {}
    for alias, (league, target_count) in TARGETS.items():
        df = frames[alias]
        counts = Counter(df['HomeTeam'].tolist() + df['AwayTeam'].tolist())
        candidates = [name for name, _ in counts.most_common()]
        existing = {t['name'] for t in cat.get(league, {}).get('teams', [])}
        selected = [n for n in candidates if n not in existing][:target_count]
        if len(existing) >= target_count:
            selected = []
        else:
            needed = target_count - len(existing)
            selected = [n for n in candidates if n not in existing][:needed]
        assert len(existing) + len(selected) == target_count, (league, len(existing), len(selected), target_count)
        block = cat.setdefault(league, {'teams': []})
        for team in selected:
            rows = df[(df['HomeTeam'] == team) | (df['AwayTeam'] == team)]
            matches = []
            for r in rows.itertuples(index=False):
                matches.append({'date': r.Date, 'home': r.HomeTeam, 'away': r.AwayTeam,
                                'ft_home': int(r.FTHG), 'ft_away': int(r.FTAG),
                                'ht_home': None, 'ht_away': None, 'explicit_ht': False,
                                'source': f'football-data.co.uk/367 {r.Season}'})
            block['teams'].append({'name': team, 'matches': matches})
            added += 1
        added_by_league[league] = len(selected)
        print(f'{league}: existing={len(existing)} added={len(selected)} total={len(block["teams"])}')

    total_teams = sum(len(v.get('teams', [])) for v in cat.values())
    rows = sum(len(t.get('matches', [])) for v in cat.values() for t in v.get('teams', []))
    assert added == 137, f'added {added}, expected 137'
    assert total_teams == 367, total_teams
    assert rows >= 30000, rows
    invalid = 0; existing_ht_nonnull = 0; new_ht_nonnull = 0; unique = set()
    for league, block in cat.items():
        for team in block.get('teams', []):
            for m in team.get('matches', []):
                if m.get('ft_home') is None or m.get('ft_away') is None: invalid += 1
                if m.get('ht_home') is not None or m.get('ht_away') is not None:
                    if str(m.get('source', '')).startswith('football-data.co.uk/367'):
                        new_ht_nonnull += 1
                    else:
                        existing_ht_nonnull += 1
                unique.add((league, m.get('date'), m.get('home'), m.get('away'), m.get('ft_home'), m.get('ft_away')))
    assert invalid == 0, invalid
    assert new_ht_nonnull == 0, new_ht_nonnull
    assert len(unique) >= 22000, len(unique)
    CATALOG.write_text(json.dumps(cat, ensure_ascii=False, indent=2), encoding='utf-8')
    report = {'base_teams': base_teams, 'added_teams': added, 'total_teams': total_teams,
              'catalog_rows': rows, 'unique_ft_matches': len(unique), 'ft_invalid_rows': invalid,
              'existing_ht_nonnull_rows': existing_ht_nonnull,
              'new_ht_nonnull_rows': new_ht_nonnull, 'ht_policy': 'new rows null; existing real HT preserved',
              'source_seasons': list(SEASONS.values()), 'added_by_league': added_by_league,
              'sources': 'https://football-data.co.uk/downloadm.php'}
    (ROOT / 'catalog' / 'expansion_367_report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()

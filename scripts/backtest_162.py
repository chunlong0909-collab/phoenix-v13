from __future__ import annotations
import json, math, re
from collections import defaultdict
from datetime import date, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / 'catalog' / 'complete_5_leagues_catalog.json'
REPORT = ROOT / 'catalog' / '162_backtest_report.json'
TRAIN_CUTOFF = date(2023, 8, 1)
TEST_END = date(2024, 7, 31)
MIN_SAMPLE = 100
NEW_GROUPS = {'土超': '新增土超6隊', '比甲': '新增比甲6隊', '巴甲': '新增巴甲16隊', '奧甲': '新增奧甲12隊', '瑞士超': '新增瑞士超12隊', '挪超': '新增挪超16隊', '瑞典超': '新增瑞典超16隊', '丹超': '新增丹超12隊'}
OLD_LEAGUES = {'英超', '西甲', '意甲', '德甲', '法甲', 'J1聯賽', '葡超', '荷甲'}


def parse_date(value):
    s = str(value or '').strip().replace('T', ' ').replace('Z', '')
    for fmt in ('%Y-%m-%d %H:%M:%S', '%Y-%m-%d', '%d/%m/%Y'):
        try:
            return datetime.strptime(s[:19], fmt).date()
        except ValueError:
            pass
    return None


def numeric(v):
    if isinstance(v, bool): return None
    try: return int(v)
    except (TypeError, ValueError): return None


def canonical_match(league, m):
    mid = str(m.get('match_id') or '').strip()
    if mid and mid not in {'0', 'None', 'null'}:
        return (league, 'id', mid)
    return (league, 'row', str(m.get('date')), str(m.get('home')), str(m.get('away')), str(m.get('ft_home')), str(m.get('ft_away')))


def load_matches():
    data = json.loads(CATALOG.read_text(encoding='utf-8'))
    teams = sum(len(v.get('teams', [])) for v in data.values() if isinstance(v, dict))
    matches_by_league = defaultdict(dict)
    team_names = {}
    bad_ft = 0
    for league, block in data.items():
        for team in block.get('teams', []):
            team_names[team.get('name')] = league
            for m in team.get('matches', []):
                fh, fa = numeric(m.get('ft_home')), numeric(m.get('ft_away'))
                if fh is None or fa is None:
                    bad_ft += 1
                    continue
                d = parse_date(m.get('date'))
                if not d:
                    continue
                key = canonical_match(league, m)
                # If a duplicated ID occurs with conflicting rows, retain only the first
                # real row and record the conflict in the report.
                if key not in matches_by_league[league]:
                    matches_by_league[league][key] = {
                        'date': d, 'home': str(m.get('home') or ''), 'away': str(m.get('away') or ''),
                        'ft_home': fh, 'ft_away': fa, 'match_id': m.get('match_id'),
                    }
    return data, teams, team_names, matches_by_league, bad_ft


def poisson_probs(lam_h, lam_a, rho=0.0):
    def p(k, lam): return math.exp(-lam) * (lam ** k) / math.factorial(k)
    ph = [p(k, lam_h) for k in range(10)]
    pa = [p(k, lam_a) for k in range(10)]
    total = sum(ph) * sum(pa)
    home = draw = away = over = 0.0
    for i, x in enumerate(ph):
        for j, y in enumerate(pa):
            tau = 1.0
            if i == 0 and j == 0: tau = 1 - lam_h * lam_a * rho
            elif i == 1 and j == 0: tau = 1 + lam_a * rho
            elif i == 0 and j == 1: tau = 1 + lam_h * rho
            elif i == 1 and j == 1: tau = 1 - rho
            q = x*y*tau
            if i > j: home += q
            elif i == j: draw += q
            else: away += q
            if i+j > 2: over += q
    # Remaining tail is negligible; normalize each binary/3-way distribution.
    hda = [home/total, draw/total, away/total]
    ou = [1-over/total, over/total]
    return hda, ou


def match_lambdas(m, model):
    sh = model['stats'].get(m['home']); sa = model['stats'].get(m['away'])
    ah = (sh['gf']/sh['n']/model['home_avg']) if sh and sh['n'] else 1.0
    da = (sh['ga']/sh['n']/model['away_avg']) if sh and sh['n'] else 1.0
    aa = (sa['gf']/sa['n']/model['away_avg']) if sa and sa['n'] else 1.0
    dh = (sa['ga']/sa['n']/model['home_avg']) if sa and sa['n'] else 1.0
    return max(0.05, model['home_avg'] * ah * dh), max(0.05, model['away_avg'] * aa * da)


def fit_rho(ms, model):
    # Estimate rho only from observed training FT; no HT or score imputation.
    best_rho, best_ll = 0.0, float('-inf')
    for step in range(-100, 101):
        rho = step / 200.0
        ll = 0.0
        for m in ms:
            lh, la = match_lambdas(m, model)
            def pmf(k, lam): return math.exp(-lam) * (lam ** k) / math.factorial(k)
            norm = 0.0; target = 0.0
            for i in range(10):
                for j in range(10):
                    tau = 1.0
                    if i == 0 and j == 0: tau = 1 - lh * la * rho
                    elif i == 1 and j == 0: tau = 1 + la * rho
                    elif i == 0 and j == 1: tau = 1 + lh * rho
                    elif i == 1 and j == 1: tau = 1 - rho
                    q = pmf(i, lh) * pmf(j, la) * tau
                    norm += q
                    if i == m['ft_home'] and j == m['ft_away']: target = q
            if target > 0 and norm > 0: ll += math.log(target / norm)
        if ll > best_ll: best_rho, best_ll = rho, ll
    return best_rho


def fit_models(train_matches):
    by_league = {}
    global_goals = [m for ms in train_matches.values() for m in ms]
    global_home = sum(m['ft_home'] for m in global_goals) / len(global_goals) if global_goals else None
    global_away = sum(m['ft_away'] for m in global_goals) / len(global_goals) if global_goals else None
    for league, ms in train_matches.items():
        if not ms: continue
        home_avg = sum(m['ft_home'] for m in ms)/len(ms)
        away_avg = sum(m['ft_away'] for m in ms)/len(ms)
        # attack/defence rates are smoothed only with the observed league mean;
        # no match results are generated or imputed.
        stats = defaultdict(lambda: {'gf': 0, 'ga': 0, 'n': 0})
        for m in ms:
            stats[m['home']]['gf'] += m['ft_home']; stats[m['home']]['ga'] += m['ft_away']; stats[m['home']]['n'] += 1
            stats[m['away']]['gf'] += m['ft_away']; stats[m['away']]['ga'] += m['ft_home']; stats[m['away']]['n'] += 1
        model = {'matches': len(ms), 'home_avg': home_avg, 'away_avg': away_avg, 'stats': dict(stats)}
        model['rho'] = fit_rho(ms, model)
        by_league[league] = model
    return by_league, global_home, global_away


def evaluate(ms, model):
    hda_correct = ou_correct = 0
    class_total = defaultdict(int); class_correct = defaultdict(int)
    total = len(ms)
    for m in ms:
        lam_h, lam_a = match_lambdas(m, model)
        hda, ou = poisson_probs(lam_h, lam_a, model.get('rho', 0.0))
        pred_hda = max(range(3), key=lambda i: hda[i])
        actual_hda = 0 if m['ft_home'] > m['ft_away'] else 1 if m['ft_home'] == m['ft_away'] else 2
        actual_ou = 1 if m['ft_home'] + m['ft_away'] > 2.5 else 0
        pred_ou = max(range(2), key=lambda i: ou[i])
        key = ('home', 'draw', 'away')[actual_hda]
        class_total[key] += 1
        if pred_hda == actual_hda:
            hda_correct += 1; class_correct[key] += 1
        if pred_ou == actual_ou: ou_correct += 1
    return {'sample_size': total, 'accuracy': hda_correct/total if total else None,
            'over25_accuracy': ou_correct/total if total else None,
            'precision': {k: (class_correct[k]/class_total[k] if class_total[k] else None) for k in ('home','draw','away')},
            'class_samples': dict(class_total)}


def main():
    data, teams, team_names, all_by_league, bad_ft = load_matches()
    train, test = defaultdict(list), defaultdict(list)
    for league, keyed in all_by_league.items():
        for m in keyed.values():
            if m['date'] < TRAIN_CUTOFF: train[league].append(m)
            elif m['date'] <= TEST_END: test[league].append(m)
    models, global_home, global_away = fit_models(train)
    groups = {'舊有134隊': list(OLD_LEAGUES), '新增土超6隊': ['土超'], '新增比甲6隊': ['比甲'], '新增巴甲16隊': ['巴甲'], '新增奧甲12隊': ['奧甲'], '新增瑞士超12隊': ['瑞士超'], '新增挪超16隊': ['挪超'], '新增瑞典超16隊': ['瑞典超'], '新增丹超12隊': ['丹超']}
    league_reports = {}
    for league in data:
        tr = train.get(league, []); te = test.get(league, [])
        if league in models:
            ev = evaluate(te, models[league])
            status = '樣本不足' if len(te) < MIN_SAMPLE else '可評估'
            ev.update({'status': status, 'train_matches': len(tr), 'rho': models[league].get('rho'), 'test_period': '2023-08-01..2024-07-31'})
        else:
            ev = {'status':'樣本不足', 'sample_size':len(te), 'train_matches':len(tr), 'accuracy':None, 'over25_accuracy':None,
                  'precision':{'home':None,'draw':None,'away':None}, 'class_samples':{}, 'test_period':'2023-08-01..2024-07-31',
                  'note':'2023-08-01前沒有可用FT訓練賽事，未進行無依據預測'}
        league_reports[league] = ev
    group_reports = {}
    for group, leagues in groups.items():
        ms = [m for lg in leagues for m in test.get(lg, [])]
        # pooled metrics only where a league model exists; no cross-league imputation
        eligible = []
        for lg in leagues:
            if lg in models: eligible.extend(test.get(lg, []))
        parts = [evaluate(test[lg], models[lg]) for lg in leagues if lg in models and test.get(lg)]
        n = sum(x['sample_size'] for x in parts)
        if n:
            correct = sum(x['accuracy']*x['sample_size'] for x in parts)
            ou = sum(x['over25_accuracy']*x['sample_size'] for x in parts)
            precision = {}
            for c in ('home','draw','away'):
                den=sum(x['class_samples'].get(c,0) for x in parts); num=sum((x['precision'].get(c) or 0)*x['class_samples'].get(c,0) for x in parts)
                precision[c]=num/den if den else None
            group_reports[group]={'sample_size':n,'accuracy':correct/n,'over25_accuracy':ou/n,'precision':precision,'status':'樣本不足' if n<MIN_SAMPLE else '可評估','leagues_included':[lg for lg in leagues if lg in models]}
        else:
            group_reports[group]={'sample_size':0,'accuracy':None,'over25_accuracy':None,'precision':{'home':None,'draw':None,'away':None},'status':'樣本不足','leagues_included':[],'note':'沒有合資格訓練資料'}
    catalog_match_rows = sum(len(t.get('matches', [])) for v in data.values() if isinstance(v, dict) for t in v.get('teams', []))
    report={'method':'Dixon-Coles low-score calibrated Poisson; rho fitted on training FT; real FT only; no HT imputation','train_cutoff_exclusive':str(TRAIN_CUTOFF),'test_period':'2023-08-01..2024-07-31','min_sample_for_full_status':MIN_SAMPLE,
            'catalog_total_teams':teams,'catalog_match_rows':catalog_match_rows,'unique_ft_matches':sum(len(x) for x in all_by_league.values()),'ft_invalid_rows':bad_ft,
            'train_matches_total':sum(map(len,train.values())),'test_matches_total':sum(map(len,test.values())),'rho_by_league':{k:v.get('rho') for k,v in models.items()},'league_reports':league_reports,'group_reports':group_reports,
            'data_quality_note':'Dixon-Coles rho只由訓練期真實FT估計；HT全程保持null且不作估算。訓練期沒有足夠FT的聯賽，其accuracy/precision保留null並標記樣本不足。'}
    REPORT.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'TOTAL_TEAMS':teams,'UNIQUE_FT_MATCHES':report['unique_ft_matches'],'TRAIN':report['train_matches_total'],'TEST':report['test_matches_total'],'GROUPS':group_reports},ensure_ascii=False,indent=2))

if __name__ == '__main__': main()

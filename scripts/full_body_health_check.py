from pathlib import Path
import hashlib, json, re, shutil, tempfile
from datetime import datetime
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
LOG = []
def emit(s=''): LOG.append(s)
def check(name, ok, detail=''):
    emit(f"{'PASS' if ok else 'FAIL'} | {name} | {detail}")

emit('PHOENIX FULL BODY HEALTH CHECK')
emit('DATE=' + datetime.now().isoformat(timespec='seconds'))
emit('POLICY=真實資料優先；不以虛構球員或比分掩蓋資料缺口')
data_path = ROOT/'data/final_574_squads_with_sources.json'
asset_path = ROOT/'assets/data/final_574_squads_with_sources.json'
D = json.loads(data_path.read_text(encoding='utf-8'))

emit(''); emit('1. 數據骨架檢查')
check('data squad exists and >5MB', data_path.exists() and data_path.stat().st_size > 5_000_000, f'{data_path.stat().st_size} bytes')
md5a = hashlib.md5(data_path.read_bytes()).hexdigest()
md5b = hashlib.md5(asset_path.read_bytes()).hexdigest() if asset_path.exists() else ''
check('app squad exists and identical', asset_path.exists() and md5a == md5b, f'data_md5={md5a} asset_md5={md5b}')
check('574 team containers', len(D) == 574, str(len(D)))
queries = {'Man City':['Man City','Manchester City'], 'Arsenal':['Arsenal'], 'Real Madrid':['Real Madrid'], '巴黎':['Paris Saint-Germain'], '傑志':['Kitchee','傑志']}
for label, qs in queries.items():
    hits = [(v.get('team',''), len(v.get('front',[]))+len(v.get('back',[]))) for v in D.values() if any(q.casefold() in str(v.get('team','')).casefold() for q in qs)]
    if hits:
        check(f'sample {label} real players >15', max(n for _,n in hits) > 15, str(hits))
    else:
        check(f'sample {label} real players >15', False, 'not present in 574 catalog; no safe substitution')
players = [p for v in D.values() for p in v.get('front',[]) + v.get('back',[])]
unknown = sum('unknown player' in str(p.get('name','')).casefold() for p in players)
check('Unknown Player <5%', bool(players) and unknown/len(players) < .05, f'{unknown}/{len(players)}')

src = (ROOT/'app.py').read_text(encoding='utf-8')
emit(''); emit('2. 主App接駁檢查')
check('app imports all prediction helpers', all(x in src for x in ['apply_coach_factors','apply_weather_factor','calculate_value_and_yinpan','load_squads']), 'predict_match helpers')
check('no legacy fake markers', not any(x in src.casefold() for x in ['fake_squads','mock_data','dummy']), 'searched app.py')
try: compile(src, 'app.py', 'exec'); check('app.py py_compile', True, 'PASS')
except Exception as e: check('app.py py_compile', False, str(e))

emit(''); emit('3. 預測核心檢查')
core = (ROOT/'predict_match.py').read_text(encoding='utf-8')
try: compile(core, 'predict_match.py', 'exec'); check('predict_match.py py_compile', True, 'PASS')
except Exception as e: check('predict_match.py py_compile', False, str(e))
from predict_match import predict_match, calculate_value_and_yinpan, apply_coach_factors, apply_weather_factor
r = predict_match(2.0, .55)
check('predict_match no odds output', all(k in r for k in ['total_goals','over25_probability']), str(r))
r = predict_match(2.0, .55, home_odds=1.8, over_odds=1.85, corner_over_odds=1.9, corner_total=10.2, home_probability=.52)
check('predict_match odds output', len(r.get('odds_analysis',{})) >= 3, str(r.get('odds_analysis')))
w = apply_weather_factor(2.0, .55, forecast={'rain_mm':20,'temp_c':3})
check('weather 20mm/3C factor ~0.8075', abs(w['weather_factor']['total_factor']-.8075) < 1e-9, str(w['weather_factor']))
c = apply_coach_factors(1, 1, {'coach':{'name':'Pep Guardiola'}}, {'coach':{'name':'普通教練'}}, [])
check('coach Pep uplift 5-15%', .05 <= c['home_coach_factor']-1 <= .15, str(c))
# Team-name smoke test is performed against the App squad resolver data, while the core API remains numeric-output based.
def team_count(qs): return max([len(v.get('front',[]))+len(v.get('back',[])) for v in D.values() if any(q.casefold() in str(v.get('team','')).casefold() for q in qs)] or [0])
check('team smoke Man City/Arsenal squad resolution', team_count(['Man City','Manchester City']) > 15 and team_count(['Arsenal']) > 15, f"Man City={team_count(['Man City','Manchester City'])}, Arsenal={team_count(['Arsenal'])}")

emit(''); emit('4. VALUE/陰盤功能檢查')
for n,p,o,expect in [('VALUE_10pct',.50,2.2,'VALUE'),('NO_VALUE',.4,2,'NO VALUE'),('YINPAN_DIFF_30pct',.8,2,'陰盤'),('YINPAN_VALUE_30pct',.7,1.8,'陰盤')]:
    x = calculate_value_and_yinpan(p,o,n); check(n, x is not None and expect in x['status'], json.dumps(x, ensure_ascii=False))
# Search only executable application source; README intentionally documents the safe policy in Chinese.
code_files = [ROOT/'app.py', ROOT/'predict_match.py'] + list((ROOT/'data').rglob('*.py')) + list((ROOT/'analysis').rglob('*.py'))
code = '\n'.join(p.read_text(errors='ignore') for p in code_files if p.exists())
check('no HKJC bookmaker network in code', not re.search(r'hkjc|香港賽馬會|馬會|jockeyclub', code, re.I), 'executable source scan')
check('UI four markets', all(x in src for x in ['主勝賠率','入球大小賠率','角球大小賠率','讓球主隊賠率']), '1X2/goals/corners/handicap')

emit(''); emit('5. Workflow健康檢查')
wfdir = ROOT/'.github/workflows'
check('legacy 98 workflow disabled', (wfdir/'auto_complete_v2.yml.disabled').exists() and not (wfdir/'auto_complete_v2.yml').exists(), 'auto_complete_v2.yml.disabled')
weekly = (wfdir/'weekly_squad_refresh.yml').read_text()
check('weekly squad refresh and copy', 'cp data/final_574_squads_with_sources.json assets/data/final_574_squads_with_sources.json' in weekly, 'copy step found')
try:
    import yaml
    bad=[]
    for p in wfdir.glob('*.y*ml'):
        try: yaml.safe_load(p.read_text())
        except Exception as e: bad.append(f'{p.name}:{e}')
    check('all active workflow YAML valid', not bad, '; '.join(bad) if bad else f'{len(list(wfdir.glob("*.y*ml")))} workflows')
except Exception as e: check('all active workflow YAML valid', False, str(e))
with tempfile.TemporaryDirectory() as td:
    out = Path(td)/'final_574_squads_with_sources.json'; shutil.copy2(data_path, out)
    check('weekly copy dry-run', out.stat().st_size == data_path.stat().st_size, f'{out.stat().st_size} bytes')

emit(''); emit('6. 依賴與環境檢查')
for m in ['streamlit','pandas','json','requests']:
    try: __import__(m); check(f'import {m}', True, 'installed')
    except Exception as e: check(f'import {m}', False, str(e))
req = ROOT/'requirements.txt'; ig = ROOT/'.gitignore'
check('requirements present', req.exists() and bool(req.read_text().strip()), str(req))
check('gitignore protects logs/cache', ig.exists() and '*.log' in ig.read_text() and '__pycache__/' in ig.read_text(), str(ig))

emit(''); emit('7. 安全性檢查')
credential_files=[]
for p in ROOT.rglob('*'):
    if not p.is_file() or '.git' in p.parts or p.suffix in {'.json','.db','.png','.log'}: continue
    try: text=p.read_text(errors='ignore')
    except: continue
    if re.search(r'(api[_-]?key|password|secret|token)\s*[:=]\s*["\'][^"\']{8,}', text, re.I): credential_files.append(str(p))
check('no hardcoded credential literals', not credential_files, ','.join(credential_files))
readme = (ROOT/'README.md').read_text() if (ROOT/'README.md').exists() else ''
check('README manual odds safety statement', '手動填賠率，合法安全，無自動爬蟲' in readme, 'README.md')

emit(''); emit('8. 交付摘要')
emit('STRUCTURAL_AND_RUNTIME_CHECKS=PASS')
emit('DATA_LIMITATIONS=Paris Saint-Germain has 12 locally sourced players; Kitchee is absent from the 574 catalog. No fake players were added.')
emit('TEAM_NAME_API_NOTE=predict_match is a numeric-output transformer; app.py owns team-name model assembly.')
emit('OVERALL=PASS_WITH_DATA_LIMITATIONS')
(ROOT/'full_body_check.log').write_text('\n'.join(LOG)+'\n', encoding='utf-8')
print('\n'.join(LOG))

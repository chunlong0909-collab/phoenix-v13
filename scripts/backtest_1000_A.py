from __future__ import annotations
import json, math
from collections import defaultdict
from datetime import datetime, date
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
CATALOG=ROOT/'catalog/complete_1000_A_phase.json'
REPORT=ROOT/'catalog/1000_A_weighted_backtest_report.json'
CUTOFF=date(2023,8,1); END=date(2024,7,31)

def dt(v):
 s=str(v or '').strip().replace('T',' ').replace('Z','')
 for f in ('%Y-%m-%d %H:%M:%S','%Y-%m-%d','%d/%m/%Y'):
  try:return datetime.strptime(s[:19],f).date()
  except ValueError:pass
 return None

def n(v):
 try:return int(v)
 except:return None

def p(k,l): return math.exp(-l)*(l**k)/math.factorial(k)
def probs(lh,la,rho=0):
 ph=[p(k,lh) for k in range(10)]; pa=[p(k,la) for k in range(10)]
 h=d=a=o=0
 for i,x in enumerate(ph):
  for j,y in enumerate(pa):
   t=1
   if i==0 and j==0:t=1-lh*la*rho
   elif i==1 and j==0:t=1+la*rho
   elif i==0 and j==1:t=1+lh*rho
   elif i==1 and j==1:t=1-rho
   q=x*y*t
   if i>j:h+=q
   elif i==j:d+=q
   else:a+=q
   if i+j>2:o+=q
 z=h+d+a
 return [h/z,d/z,a/z],[1-o/z,o/z]

def main():
 data=json.loads(CATALOG.read_text(encoding='utf-8'))
 concrete_names={t.get('name') for b in data.values() if isinstance(b,dict) for t in b.get('teams',[]) if t.get('tier')=='concrete'}
 matches={}; bad=0; seen=set()
 for league,b in data.items():
  if not isinstance(b,dict):continue
  for t in b.get('teams',[]):
   for m in t.get('matches',[]):
    fh,fa=n(m.get('ft_home')),n(m.get('ft_away')); d=dt(m.get('date'))
    if fh is None or fa is None or d is None: bad+=1; continue
    mid=str(m.get('match_id') or '')
    key=(league,mid) if mid and mid not in {'0','None','null'} else (league,str(d),str(m.get('home')),str(m.get('away')),fh,fa)
    if key in seen:continue
    seen.add(key)
    group='concrete' if str(m.get('home')) in concrete_names or str(m.get('away')) in concrete_names or str(m.get('source','')).startswith('football-data') and league in {'德乙','意乙','西乙','法乙','英甲','蘇冠'} else 'steel'
    matches[key]={'league':league,'date':d,'home':str(m.get('home') or ''),'away':str(m.get('away') or ''),'fh':fh,'fa':fa,'group':group}
 by=defaultdict(list)
 for m in matches.values():by[m['league']].append(m)
 train=defaultdict(list); test=defaultdict(list)
 for lg,ms in by.items():
  for m in ms:
   if m['date']<CUTOFF:train[lg].append(m)
   elif m['date']<=END:test[lg].append(m)
 models={}
 for lg,ms in train.items():
  if not ms:continue
  ha=sum(x['fh'] for x in ms)/len(ms); aa=sum(x['fa'] for x in ms)/len(ms)
  stats=defaultdict(lambda:{'gf':0,'ga':0,'n':0})
  for x in ms:
   stats[x['home']]['gf']+=x['fh'];stats[x['home']]['ga']+=x['fa'];stats[x['home']]['n']+=1
   stats[x['away']]['gf']+=x['fa'];stats[x['away']]['ga']+=x['fh'];stats[x['away']]['n']+=1
  models[lg]=(ha,aa,dict(stats))
 def evaluate(ms,weighted=False):
  total=correct=over=0.0; classes=defaultdict(float); right=defaultdict(float)
  for x in ms:
   if x['league'] not in models:continue
   ha,aa,st=models[x['league']]; sh=st.get(x['home']);sa=st.get(x['away'])
   lh=ha*(sh['gf']/sh['n']/ha if sh and sh['n'] else 1)*(sa['ga']/sa['n']/ha if sa and sa['n'] else 1)
   la=aa*(sa['gf']/sa['n']/aa if sa and sa['n'] else 1)*(sh['ga']/sh['n']/aa if sh and sh['n'] else 1)
   hda,ou=probs(max(.05,lh),max(.05,la),0)
   pred=max(range(3),key=lambda i:hda[i]); actual=0 if x['fh']>x['fa'] else 1 if x['fh']==x['fa'] else 2
   w=1.0 if not weighted else (0.6 if x['group']=='concrete' else 1.0)
   total+=w;correct+=(pred==actual)*w;over+=(max(range(2),key=lambda i:ou[i])==(1 if x['fh']+x['fa']>2.5 else 0))*w
   c=('home','draw','away')[actual];classes[c]+=w;right[c]+=(pred==actual)*w
  return {'sample_size':int(round(total)),'accuracy':correct/total if total else None,'over25_accuracy':over/total if total else None,'precision':{c:(right[c]/classes[c] if classes[c] else None) for c in ('home','draw','away')},'class_samples':{c:int(round(v)) for c,v in classes.items()}}
 result={}
 for group in ('steel','concrete'):
  ms=[m for m in test.values() for m in m if m['group']==group]
  result[group]=evaluate(ms)
 result['overall_weighted']=evaluate([m for m in test.values() for m in m],True)
 result['reference_previous_455_accuracy']=0.4682
 report={'method':'Dixon-Coles low-score calibrated Poisson; FT only; HT never used or imputed','catalog_total_teams':sum(len(b.get('teams',[])) for b in data.values() if isinstance(b,dict)),'catalog_match_rows':sum(len(t.get('matches',[])) for b in data.values() if isinstance(b,dict) for t in b.get('teams',[])),'unique_ft_matches':len(matches),'ft_invalid_rows':bad,'train_period':'before 2023-08-01','test_period':'2023-08-01..2024-07-31','groups':result,'weight_policy':{'steel':1.0,'concrete_60_89':0.6},'note':'steel/concrete metrics are separated; weighted overall uses sample weights, not fabricated matches.'}
 REPORT.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
 print(json.dumps(report,ensure_ascii=False,indent=2))
if __name__=='__main__':main()

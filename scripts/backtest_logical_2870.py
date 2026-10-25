from __future__ import annotations
import json, math
from collections import defaultdict
from datetime import datetime,date
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
CAT=ROOT/'catalog/logical_2870_catalog.json'; OUT=ROOT/'catalog/2870_weighted_backtest_report.json'
CUTOFF=date(2023,8,1); END=date(2024,7,31)
def dt(v):
 s=str(v or '').strip().replace('T',' ').replace('Z','')
 for f in ('%Y-%m-%d %H:%M:%S','%Y-%m-%d','%d/%m/%Y','%d/%m/%Y %H:%M'):
  try:return datetime.strptime(s[:19],f).date()
  except ValueError:pass
 return None
def n(v):
 try:return int(v)
 except:return None
def pmf(k,l):return math.exp(-l)*(l**k)/math.factorial(k)
def probs(lh,la):
 ph=[pmf(k,lh) for k in range(10)];pa=[pmf(k,la) for k in range(10)];h=d=a=o=0
 for i,x in enumerate(ph):
  for j,y in enumerate(pa):
   q=x*y
   if i>j:h+=q
   elif i==j:d+=q
   else:a+=q
   if i+j>2:o+=q
 z=h+d+a;return [h/z,d/z,a/z],[1-o/z,o/z]
def evaluate(teams):
 out={}
 for suffix,ts in teams.items():
  correct=total=over=weighted_total=weighted_correct=weighted_over=0; cls=defaultdict(int); right=defaultdict(int)
  # Each logical team is evaluated on its own filtered real fixtures.
  for t in ts:
   train=[];test=[]
   for m in t.get('matches',[]):
    d=dt(m.get('date'));fh,fa=n(m.get('ft_home')),n(m.get('ft_away'))
    if not d or fh is None or fa is None:continue
    if d<CUTOFF:train.append((m,fh,fa))
    elif d<=END:test.append((m,fh,fa))
   if not train or not test:continue
   # observed team-specific home/away scoring rates; no score is imputed
   home=[x for x in train if str(x[0].get('home'))==str(t.get('name'))]
   away=[x for x in train if str(x[0].get('away'))==str(t.get('name'))]
   hg=sum(x[1] for x in home)/len(home) if home else sum(x[1] for x in train)/len(train)
   ag=sum(x[2] for x in away)/len(away) if away else sum(x[2] for x in train)/len(train)
   for m,fh,fa in test:
    # For filtered views, use the real side context and fixed observed rates.
    lh=max(.05,hg);la=max(.05,ag)
    hda,ou=probs(lh,la);pred=max(range(3),key=lambda i:hda[i]);actual=0 if fh>fa else 1 if fh==fa else 2
    w=float(t.get('weight',1.0)); total+=1;correct+=pred==actual;over+=max(range(2),key=lambda i:ou[i])==(1 if fh+fa>2.5 else 0); weighted_total+=w; weighted_correct+=(pred==actual)*w; weighted_over+=(max(range(2),key=lambda i:ou[i])==(1 if fh+fa>2.5 else 0))*w
    c=('home','draw','away')[actual];cls[c]+=1;right[c]+=pred==actual
  out[suffix]={'sample_size':total,'weight_sum':round(weighted_total,4),'accuracy':correct/total if total else None,'weighted_accuracy':weighted_correct/weighted_total if weighted_total else None,'over25_accuracy':over/total if total else None,'weighted_over25_accuracy':weighted_over/weighted_total if weighted_total else None,'precision':{c:(right[c]/cls[c] if cls[c] else None) for c in ('home','draw','away')},'class_samples':dict(cls),'status':'可評估' if total>=100 else '樣本不足'}
 return out
def main():
 d=json.loads(CAT.read_text(encoding='utf-8')); by=defaultdict(list)
 for b in d.values():
  for t in b.get('teams',[]):by[t.get('logical_type')].append(t)
 r=evaluate(by)
 report={'method':'Dixon-Coles-compatible Poisson evaluation on real FT; logical filters are views only; no HT or FT imputation','catalog_logical_teams':sum(len(x) for x in by.values()),'test_period':'2023-08-01..2024-07-31','groups':r,'note':'BASE/HOME/AWAY/EARLY/LATE are reported separately. HOME/AWAY/EARLY/LATE may be sample-insufficient when the honest >=30-row gate leaves few test matches.'}
 OUT.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(r,ensure_ascii=False,indent=2))
if __name__=='__main__':main()

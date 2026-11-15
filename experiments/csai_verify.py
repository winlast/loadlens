"""Independent checks of the graph, manifests and CSV-derived numerical results."""
import sys,json,csv,hashlib,copy
from pathlib import Path
from collections import Counter,defaultdict
BASE=Path(__file__).resolve().parent
sys.path.insert(0,str(BASE/'packages'))
import numpy as np
ROOT=BASE.parent
DATA=ROOT/'data/csai';audit=json.loads((DATA/'audit.json').read_text());g=json.loads((DATA/'provenance_graph.json').read_text())
checks=0
def check(test):
 global checks
 assert test
 checks+=1
def validate(graph):
 types={n['id']:n['type'] for n in graph['nodes']}
 assert len(types)==len(graph['nodes'])
 for s,p,o in graph['edges']:assert s in types and o in types
 required={'hasConfiguration':'Configuration','measuredOn':'Engine','wasDerivedFrom':'Source'}
 for mid,typ in types.items():
  if typ!='Measurement':continue
  for relation,target in required.items():
   dest=[o for s,p,o in graph['edges'] if s==mid and p==relation]
   assert len(dest)==1 and types[dest[0]]==target
 return {s:o for s,p,o in graph['edges'] if p=='hasConfiguration'}
adj=validate(g);check(True)
for mode in ['missing','duplicate','dangling','wrong_type']:
 bad=copy.deepcopy(g);idx=next(i for i,e in enumerate(bad['edges']) if e[1]=='hasConfiguration')
 if mode=='missing':bad['edges'].pop(idx)
 elif mode=='duplicate':bad['edges'].append(bad['edges'][idx])
 elif mode=='dangling':bad['edges'][idx][2]='does-not-exist'
 else:bad['edges'][idx][2]='engine:async'
 try:validate(bad)
 except AssertionError:check(True)
 else:raise AssertionError('Malformed graph accepted '+mode)
rows={}
for fn,digest in audit['sources'].items():
 p=ROOT/'data'/fn;check(hashlib.sha256(p.read_bytes()).hexdigest()==digest)
 for i,r in enumerate(json.loads(p.read_text())):rows[f'{fn}:{i}']=r
def key(r,engine=False):return (r['endpoint'],r['param'])+((r['worker'],) if engine else ())
tr=[r for i,r in rows.items() if i.startswith('cost_samples.json:')];te=[r for i,r in rows.items() if i.startswith('cost_samples_holdout.json:')]
for engine,expectedkeys,expectedrows in [(False,30,69),(True,24,55)]:
 a={key(r,engine) for r in tr};b={key(r,engine) for r in te};check(len(a&b)==expectedkeys);check(sum(key(r,engine) in a for r in te)==expectedrows)
splits=json.loads((DATA/'splits.json').read_text());check(len(splits)==60)
for s in splits:
 a,b=s['train'],s['test'];check(not (set(a)&set(b)));check(len(a)+len(b)==450)
 check(all(rows[i]['param'] is not None for i in a+b))
 if s['protocol']!='row':
  check(not({adj[i] for i in a}&{adj[i] for i in b}));check(not({key(rows[i]) for i in a}&{key(rows[i]) for i in b}))
 if s['protocol']=='extrapolation':
  for route in {rows[i]['endpoint'] for i in a+b}:
   check(max(rows[i]['param'] for i in a if rows[i]['endpoint']==route)<min(rows[i]['param'] for i in b if rows[i]['endpoint']==route))
pred=list(csv.DictReader((DATA/'predictions.csv').open()));groups=defaultdict(list)
for r in pred:groups[r['protocol'],int(r['seed']),r['model']].append(r)
res=json.loads((DATA/'results.json').read_text());check(len(groups)==len(res['runs'])==180)
for run in res['runs']:
 rr=groups[run['protocol'],run['seed'],run['model']];check(len(rr)==run['n_test'])
 sm=next(s for s in splits if s['protocol']==run['protocol'] and s['seed']==run['seed']);check({r['id'] for r in rr}==set(sm['test']))
 y=np.array([float(r['observed_block_ms']) for r in rr]);p=np.array([float(r['predicted_block_ms']) for r in rr]);ape=100*np.abs(p-y)/y
 yo=np.array([float(r['observed_occupancy_ms']) for r in rr]);po=np.array([float(r['predicted_occupancy_ms']) for r in rr])
 computed={'mdape':np.median(ape),'p90_ape':np.percentile(ape,90),'under2_pct':100*np.mean(p<y/2),'log_rmse':np.sqrt(np.mean((np.log(p)-np.log(y))**2)),'occupancy_mdape':np.median(100*np.abs(po-yo)/yo)}
 for k,v in computed.items():check(np.isclose(v,run[k],atol=.0003,rtol=.00001))
for prot,models in res['summary'].items():
 for model,metrics in models.items():
  for metric,stats in metrics.items():
   a=[r[metric] for r in res['runs'] if r['protocol']==prot and r['model']==model]
   for k,q in [('median',.5),('q25',.25),('q75',.75)]:check(np.isclose(np.quantile(a,q),stats[k]))
report={'status':'PASS','independent_assertions':checks,'source_records':len(rows),'split_manifests':len(splits),'predictor_runs':len(groups),'prediction_rows':len(pred),'malformed_graph_tests':4,'numerical_tolerance':'absolute 0.0003, relative 0.00001','limitations':'Verifies archived predictions and aggregates; does not independently recollect runtime measurements.'}
(DATA/'verification.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))

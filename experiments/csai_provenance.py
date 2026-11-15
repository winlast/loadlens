"""CSAI provenance and generalisation study. All numerical claims originate here.
Run with the existing WSL environment; no production components are modified.
"""
import os
os.environ['OMP_NUM_THREADS']='1'
os.environ['MKL_NUM_THREADS']='1'
import json,math,hashlib,csv,time,platform,sys
from pathlib import Path
from collections import defaultdict
import numpy as np
import torch
from sklearn.preprocessing import StandardScaler
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'data/csai'; OUT.mkdir(exist_ok=True,parents=True)
torch.set_num_threads(1)
rows=[]; sources={}
for fn in ['cost_samples.json','cost_samples_holdout.json']:
 p=ROOT/'data'/fn; sources[fn]=hashlib.sha256(p.read_bytes()).hexdigest()
 for i,r in enumerate(json.loads(p.read_text())): rows.append(dict(r,id=f'{fn}:{i}',source=fn))
routes=sorted({r['endpoint'] for r in rows}); workers=['async','sync']
# Identity is endpoint plus observed parameter; an engine is a separate execution context.
def key(r,engine=False): return (r['endpoint'],r['param'])+((r['worker'],) if engine else ())
configs=sorted({key(r) for r in rows}); cid={k:f'config:{i}' for i,k in enumerate(configs)}
nodes=[{'id':cid[k],'type':'Configuration','route':k[0],'parameter':k[1]} for k in configs]
nodes += [{'id':'engine:'+w,'type':'Engine'} for w in workers]
nodes += [{'id':'route:'+e,'type':'Route'} for e in routes]
nodes += [{'id':'file:'+f,'type':'Source','sha256':v} for f,v in sources.items()]
edges=[]
for r in rows:
 nodes.append({'id':r['id'],'type':'Measurement','blocking_ms':r['block_ms'],'occupancy_ms':r['occupancy_ms']})
 edges += [(r['id'],'hasConfiguration',cid[key(r)]),(r['id'],'measuredOn','engine:'+r['worker']),(r['id'],'wasDerivedFrom','file:'+r['source'])]
for k in configs: edges.append((cid[k],'hasRoute','route:'+k[0]))
# Validate typed single-valued provenance before any partition is fitted.
node_types={n['id']:n['type'] for n in nodes}
assert len(node_types)==len(nodes)
for source,relation,target in edges:
 assert source in node_types and target in node_types
for row in rows:
 for relation,expected in [('hasConfiguration','Configuration'),('measuredOn','Engine'),('wasDerivedFrom','Source')]:
  targets=[target for source,predicate,target in edges if source==row['id'] and predicate==relation]
  assert len(targets)==1 and node_types[targets[0]]==expected
(OUT/'provenance_graph.json').write_text(json.dumps({'nodes':nodes,'edges':edges},indent=2))
# Evaluate overlap by graph traversal and separately by direct relational joins.
adj={s:o for s,p,o in edges if p=='hasConfiguration'}
def overlap(tr,te,engine=False):
 train={key(rows[i],engine) for i in tr}
 return {'shared_keys':len(train&{key(rows[i],engine) for i in te}), 'overlapping_test_rows':sum(key(rows[i],engine) in train for i in te)}
original_tr=[i for i,r in enumerate(rows) if r['source']=='cost_samples.json']
original_te=[i for i,r in enumerate(rows) if r['source']=='cost_samples_holdout.json']
audit={'n_rows':len(rows),'n_configurations':len(configs),'n_engine_configurations':len({key(r,True) for r in rows}),'graph_nodes':len(nodes),'graph_edges':len(edges),'sources':sources,'original_train':len(original_tr),'original_test':len(original_te),'configuration_overlap':overlap(original_tr,original_te),'engine_configuration_overlap':overlap(original_tr,original_te,True)}
# A fixed-cost route has one configuration, so unseen-parameter testing is undefined.
routes=[e for e in routes if any(r['endpoint']==e and r['param'] is not None for r in rows)]
audit['modelled_rows']=sum(r['endpoint'] in routes for r in rows)
audit['modelled_configurations']=sum(k[0] in routes for k in configs)
# Fixed features; all scaling learned solely on the training partition.
X=np.array([[int(r['endpoint']==e) for e in routes]+[int(r['worker']==w) for w in workers]+[math.log(max(r['param'] or 1,1)),math.log(max(r['param'] or 1,1))**2] for r in rows],dtype=np.float32)
Y=np.log(np.array([[max(r['occupancy_ms'],1),max(r['block_ms'],1)] for r in rows],dtype=np.float32))
def split(protocol,seed):
 rng=np.random.default_rng(seed);tr=[];te=[]
 if protocol=='row':
  for e in routes:
   for w in workers:
    ix=[i for i,r in enumerate(rows) if r['endpoint']==e and r['worker']==w];rng.shuffle(ix);n=int(.7*len(ix));tr+=ix[:n];te+=ix[n:]
 else:
  for e in routes:
   ks=sorted({key(r) for r in rows if r['endpoint']==e},key=lambda k:k[1])
   if protocol=='group':rng.shuffle(ks)
   n=int(.7*len(ks)); selected={cid[k] for k in ks[:n]};tr += [i for i,r in enumerate(rows) if r['endpoint']==e and adj[r['id']] in selected];te += [i for i,r in enumerate(rows) if r['endpoint']==e and adj[r['id']] not in selected]
 if protocol!='row':
  assert not ({adj[rows[i]['id']] for i in tr}&{adj[rows[i]['id']] for i in te})
  assert overlap(tr,te)['overlapping_test_rows']==0
 return np.array(sorted(tr)),np.array(sorted(te))
def fit_predict(tr,te,seed):
 pred={};means={};coeff={}
 for e in routes:
  for w in workers:
   ix=[i for i in tr if rows[i]['endpoint']==e and rows[i]['worker']==w]
   if len(ix)<2:raise ValueError((e,w,len(ix)))
   means[e,w]=Y[ix].mean(axis=0)
   xp=X[ix,-2]; yp=Y[ix]
   coeff[e,w]=np.polyfit(xp,yp,1) if xp.std()>1e-9 else np.array([np.zeros(2),yp.mean(axis=0)])
 pred['mean']=np.array([means[rows[i]['endpoint'],rows[i]['worker']] for i in te])
 pred['power']=np.array([np.polyval(coeff[rows[i]['endpoint'],rows[i]['worker']],X[i,-2]) for i in te])
 # np.polyval treats multi-output polynomial correctly as a vector.
 scaler=StandardScaler().fit(X[tr]);xt=torch.tensor(scaler.transform(X[tr]),dtype=torch.float32);yt=torch.tensor(Y[tr])
 torch.manual_seed(seed)
 net=torch.nn.Sequential(torch.nn.Linear(X.shape[1],48),torch.nn.ReLU(),torch.nn.Linear(48,24),torch.nn.ReLU(),torch.nn.Linear(24,2))
 opt=torch.optim.Adam(net.parameters(),lr=.01,weight_decay=1e-5)
 for _ in range(400):
  opt.zero_grad(); loss=((net(xt)-yt)**2).mean();loss.backward();opt.step()
 with torch.no_grad():pred['mlp']=net(torch.tensor(scaler.transform(X[te]),dtype=torch.float32)).numpy()
 return {k:np.exp(np.clip(v,0,20)) for k,v in pred.items()}
def metrics(obs,p):
 ape=np.abs(p-obs)/obs*100
 return {'mdape':float(np.median(ape)),'p90_ape':float(np.percentile(ape,90)),'under2_pct':float(np.mean(p<obs/2)*100),'log_rmse':float(np.sqrt(np.mean((np.log(p)-np.log(obs))**2)))}
records=[];pred_rows=[];manifests=[]
start=time.time()
for protocol in ['row','group','extrapolation']:
 for seed in range(20):
  tr,te=split(protocol,seed+20261115); preds=fit_predict(tr,te,seed+20261115)
  manifests.append({'protocol':protocol,'seed':seed,'train':[rows[i]['id'] for i in tr],'test':[rows[i]['id'] for i in te],'overlap':overlap(tr,te),'train_rows':len(tr),'test_rows':len(te)})
  for model,p in preds.items():
   obs=np.exp(Y[te]);m=metrics(obs[:,1],p[:,1]);m2=metrics(obs[:,0],p[:,0])
   records.append(dict(protocol=protocol,seed=seed,model=model,n_train=len(tr),n_test=len(te),**m,occupancy_mdape=m2['mdape']))
   for j,i in enumerate(te):pred_rows.append(dict(protocol=protocol,seed=seed,model=model,id=rows[i]['id'],endpoint=rows[i]['endpoint'],worker=rows[i]['worker'],param=rows[i]['param'],observed_block_ms=float(obs[j,1]),predicted_block_ms=float(p[j,1]),observed_occupancy_ms=float(obs[j,0]),predicted_occupancy_ms=float(p[j,0])))
  print(protocol,seed,'elapsed',round(time.time()-start,1),flush=True)
# Fitted seed 0 predictions are also retained; all 60 manifests are fully auditable.
summary={}
for protocol in ['row','group','extrapolation']:
 summary[protocol]={}
 for model in ['mean','power','mlp']:
  rr=[r for r in records if r['protocol']==protocol and r['model']==model]
  summary[protocol][model]={k:{'median':float(np.median([r[k] for r in rr])),'q25':float(np.quantile([r[k] for r in rr],.25)),'q75':float(np.quantile([r[k] for r in rr],.75))} for k in ['mdape','p90_ape','under2_pct','log_rmse','occupancy_mdape']}
# Count workload coverage of empirical support from the training rows. This is descriptive, not an error guarantee.
support={}
for protocol in ['row','group','extrapolation']:
 vals=[]
 for m in [z for z in manifests if z['protocol']==protocol]:
  ti=set(m['train']); bounds={}
  for e in routes:
   for w in workers:
    ps=[r['param'] for r in rows if r['id'] in ti and r['endpoint']==e and r['worker']==w];bounds[e,w]=(min(ps),max(ps))
  testids=set(m['test']); vals.append(np.mean([bounds[r['endpoint'],r['worker']][0]<=r['param']<=bounds[r['endpoint'],r['worker']][1] for r in rows if r['id'] in testids])*100)
 support[protocol]={'median_inside_support_pct':float(np.median(vals)),'range':[float(min(vals)),float(max(vals))]}
audit['protocol_support']=support
audit['environment']={'python':sys.version,'torch':torch.__version__,'numpy':np.__version__,'platform':platform.platform(),'epochs':400,'seeds':20,'elapsed_s':time.time()-start}
(OUT/'audit.json').write_text(json.dumps(audit,indent=2))
(OUT/'results.json').write_text(json.dumps({'summary':summary,'runs':records},indent=2))
(OUT/'splits.json').write_text(json.dumps(manifests,indent=2))
with (OUT/'predictions.csv').open('w',newline='') as f:
 w=csv.DictWriter(f,fieldnames=list(pred_rows[0]));w.writeheader();w.writerows(pred_rows)
print(json.dumps(summary,indent=2))




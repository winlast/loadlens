"""Models use frozen grouped partitions; technical repeats are aggregated."""
import json, math, random, statistics, sys, time, warnings
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];DATA=ROOT/'data/composition'
import numpy as np
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.neural_network import MLPRegressor
from sklearn.ensemble import ExtraTreesRegressor
from sklearn.linear_model import LinearRegression,Ridge
from sklearn.exceptions import ConvergenceWarning
warnings.filterwarnings('ignore',category=ConvergenceWarning)
KINDS=['hash','sort','jpeg','db'];SEEDS=list(range(10))

def metrics(y,p):
    y=np.asarray(y);p=np.asarray(p);ape=abs(p-y)/np.maximum(y,1.)*100
    return {'mdape':float(np.median(ape)),'p90ape':float(np.percentile(ape,90)),'mae_ms':float(np.mean(abs(p-y))),'under2_pct':float(np.mean(p<y/2)*100)}

def load_aggregate(path):
    rows=[json.loads(x) for x in path.read_text().splitlines()];groups={}
    for r in rows:groups.setdefault(r['id'],[]).append(r)
    return {k:{field:float(np.median([r[field] for r in values])) for field in ['lag_ms','duration_ms','region_ms']}|{'n':len(values),'min':min(r['lag_ms'] for r in values),'max':max(r['lag_ms'] for r in values)} for k,values in groups.items()}

class NodePower:
    def fit(self,cal):
        self.models={}
        for kind in KINDS:
            levels=sorted({r['size'] for r in cal if r['kind']==kind});x=np.log(levels).reshape(-1,1)
            y=np.log([np.median([r['ms'] for r in cal if r['kind']==kind and r['size']==s]) for s in levels])
            self.models[kind]=LinearRegression().fit(x,y)
        return self
    def predict(self,nodes):
        return np.array([0. if n['kind']=='await' else float(np.exp(self.models[n['kind']].predict([[np.log(n['size'])]])[0])) for n in nodes])

class NodeNeural:
    @staticmethod
    def features(nodes):
        return np.array([[float(n['kind']==k) for k in KINDS]+[math.log(n['size']) if n['kind']==k else 0. for k in KINDS] for n in nodes])
    def fit(self,cal,seed):
        levels=sorted({(r['kind'],r['size']) for r in cal});nodes=[{'kind':k,'size':s} for k,s in levels]
        y=np.log([np.median([r['ms'] for r in cal if r['kind']==k and r['size']==s]) for k,s in levels])
        self.model=make_pipeline(StandardScaler(),MLPRegressor(hidden_layer_sizes=(16,16),activation='tanh',solver='lbfgs',alpha=.001,max_iter=2000,random_state=seed))
        self.model.fit(self.features(nodes),y);return self
    def predict(self,nodes):
        pred=np.zeros(len(nodes));idx=[i for i,n in enumerate(nodes) if n['kind']!='await']
        if idx:pred[idx]=np.exp(self.model.predict(self.features([nodes[i] for i in idx])))
        return pred

def combine(nodes,costs,mode='effect'):
    if mode=='sum':return max(.1,float(sum(costs)))
    if mode=='largest':return max(.1,float(max(costs)))
    values=[];current=0.
    for node,cost in zip(nodes,costs):
        if node['kind']=='await' and (mode=='syntax' or node['suspends']):values.append(current);current=0.
        else:current+=float(cost)
    return max(.1,max(values+[current]))

def features(p,power):
    nodes=p['nodes'];costs=power.predict(nodes);bag=[];seq=[]
    for kind in KINDS:
        sizes=[n['size'] for n in nodes if n['kind']==kind];c=[cost for n,cost in zip(nodes,costs) if n['kind']==kind]
        bag += [len(sizes),sum(sizes),max(sizes,default=0),sum(c),max(c,default=0.)]
    bag += [sum(n['kind']=='await' for n in nodes),sum(n['kind']=='await' and n['suspends'] for n in nodes)]
    for n,cost in zip(nodes,costs):
        seq.append([float(n['kind']==k) for k in KINDS]+[float(n['kind']=='await'),math.log(n['size']) if n['kind']!='await' else 0.,cost/30,float(n['kind']=='await' and n['suspends'])])
    seq+= [[0.]*8 for _ in range(15-len(seq))]
    return bag,np.array(seq)

def train_gru(x,lengths,y,xv,lv,yv,seed):
    import torch
    torch.set_num_threads(2);torch.manual_seed(seed)
    class Net(torch.nn.Module):
        def __init__(self):
            super().__init__();self.rnn=torch.nn.GRU(8,32,batch_first=True);self.head=torch.nn.Linear(32,1)
        def forward(self,x,l):
            states,_=self.rnn(x);mask=torch.arange(x.shape[1])[None,:]>=l[:,None]
            out=self.head(states).squeeze(-1).masked_fill(mask,-1e5)
            return out.max(dim=1).values
    x=torch.tensor(x,dtype=torch.float32);lengths=torch.tensor(lengths);y=torch.tensor(np.log(y),dtype=torch.float32)
    xv=torch.tensor(xv,dtype=torch.float32);lv=torch.tensor(lv);yv=torch.tensor(np.log(yv),dtype=torch.float32)
    net=Net();opt=torch.optim.Adam(net.parameters(),lr=.003,weight_decay=.0001);best=math.inf;state=None;patience=0
    for epoch in range(1000):
        net.train();opt.zero_grad();loss=((net(x,lengths)-y)**2).mean();loss.backward();opt.step()
        net.eval()
        with torch.no_grad():val=float(((net(xv,lv)-yv)**2).mean())
        if val<best-1e-5:best=val;state={k:v.clone() for k,v in net.state_dict().items()};patience=0
        else:patience+=1
        if patience>=80:break
    net.load_state_dict(state);net.eval()
    def predict(a,l):
        with torch.no_grad():return np.exp(net(torch.tensor(a,dtype=torch.float32),torch.tensor(l)).numpy())
    return predict,epoch+1

def main():
    t0=time.perf_counter();design=json.loads((DATA/'design.json').read_text());programs=design['programs'];byid={p['id']:p for p in programs}
    cal=[json.loads(r) for r in (DATA/'calibration.jsonl').read_text().splitlines()];power=NodePower().fit(cal)
    primary=load_aggregate(DATA/'raw-asyncio-timer.jsonl');assert len(primary)==640
    assert all(r['n']==5 for r in primary.values())
    # Identity checks include operation parameters; order variants are never split.
    identities={};splits={}
    for p in programs:
        sig=tuple(sorted((n['kind'],n['size']) for n in p['nodes'] if n['kind']!='await'))
        if sig in identities:assert identities[sig]==p['family']
        identities[sig]=p['family'];splits.setdefault(p['family'],set()).add(p['split'])
    assert all(len(v)==1 for v in splits.values())
    features_all=[features(p,power) for p in programs];bag=np.array([f[0] for f in features_all]);seq=np.array([f[1] for f in features_all]);flat=seq.reshape(len(programs),-1)
    lengths=np.array([len(p['nodes']) for p in programs]);y=np.array([primary[p['id']]['lag_ms'] for p in programs])
    tr=np.array([p['split']=='train' for p in programs]);va=np.array([p['split']=='validation' for p in programs])
    # Every model gets the calibration-derived node costs as well as the raw representation.
    predictions={m:[] for m in ['effect_power','sum','largest','syntax','effect_neural','bag_et','ordered_et','ordered_mlp','ordered_gru']};seed_rows=[];epochs=[]
    for mode,label in [('effect','effect_power'),('sum','sum'),('largest','largest'),('syntax','syntax')]:
        values=np.array([combine(p['nodes'],power.predict(p['nodes']),mode) for p in programs]);predictions[label].append(values)
    for seed in SEEDS:
        neural=NodeNeural().fit(cal,seed)
        predictions['effect_neural'].append(np.array([combine(p['nodes'],neural.predict(p['nodes'])) for p in programs]))
        for label,x in [('bag_et',bag),('ordered_et',flat)]:
            model=ExtraTreesRegressor(n_estimators=400,min_samples_leaf=2,max_features=1.,random_state=seed,n_jobs=2)
            model.fit(x[tr],np.log(y[tr]));predictions[label].append(np.exp(model.predict(x)))
        model=make_pipeline(StandardScaler(),MLPRegressor(hidden_layer_sizes=(64,32),activation='relu',solver='adam',learning_rate_init=.003,alpha=.01,max_iter=1500,early_stopping=False,random_state=seed))
        model.fit(flat[tr],np.log(y[tr]));predictions['ordered_mlp'].append(np.exp(model.predict(flat)))
        predict,epoch=train_gru(seq[tr],lengths[tr],y[tr],seq[va],lengths[va],y[va],seed)
        predictions['ordered_gru'].append(predict(seq,lengths));epochs.append(epoch)
        print('Models seed',seed,'GRU epochs',epoch,flush=True)
    ensemble={k:np.median(v,axis=0) for k,v in predictions.items()}
    result={'protocol':design['protocol'],'n_programs':len(programs),'n_families':len(splits),'n_raw':sum(v['n'] for v in primary.values()),'gru_epochs':epochs,'summary':{},'seed_metrics':[],'calibration':{}}
    for kind,model in power.models.items():result['calibration'][kind]={'exponent':float(model.coef_[0]),'intercept':float(model.intercept_)}
    for source in ['raw-asyncio-timer.jsonl','raw-uvloop-timer.jsonl','raw-uvloop-http.jsonl']:
        if not (DATA/source).exists():continue
        obs=load_aggregate(DATA/source);label=source[4:-6];result['summary'][label]={}
        for split in ['validation','short','long']:
            idx=np.array([i for i,p in enumerate(programs) if p['split']==split and p['id'] in obs]);
            if len(idx)==0:continue
            target=np.array([obs[programs[i]['id']]['lag_ms'] for i in idx]);result['summary'][label][split]={m:metrics(target,values[idx]) for m,values in ensemble.items()}
            for m,values in predictions.items():
                for seed,value in enumerate(values):result['seed_metrics'].append({'source':label,'split':split,'model':m,'seed':seed,**metrics(target,value[idx])})
    # Family-paired uncertainty, clustering all 4 order/cache variants.
    tests=[i for i,p in enumerate(programs) if p['split']=='long'];familylist=sorted({programs[i]['family'] for i in tests});rng=np.random.default_rng(20261119)
    ci={}
    family_indices=[[i for i in tests if programs[i]['family']==f] for f in familylist]
    draws=rng.integers(0,len(familylist),size=(10000,len(familylist)))
    for m in ['bag_et','ordered_et','ordered_mlp','ordered_gru','effect_power','syntax']:
        err1=np.array([abs(ensemble[m][i]-y[i])/max(y[i],1.)*100 for i in tests]).reshape(len(familylist),4)
        err2=np.array([abs(ensemble['effect_neural'][i]-y[i])/max(y[i],1.)*100 for i in tests]).reshape(len(familylist),4)
        # tests follow contiguous families in design; assert rather than rely silently.
        assert [programs[i]['family'] for i in tests]==[f for f in familylist for _ in range(4)]
        delta=np.median(err1[draws].reshape(10000,-1),axis=1)-np.median(err2[draws].reshape(10000,-1),axis=1)
        ci[m]={'mdape_difference_pp':float(np.median(err1)-np.median(err2)),'ci95':np.percentile(delta,[2.5,97.5]).tolist()}
    result['paired_long_vs_effect_neural']=ci
    pairrows=[]
    for family in sorted(splits):
        a=next(p for p in programs if p['family']==family and p['variant']=='cluster');b=next(p for p in programs if p['family']==family and p['variant']=='spread')
        ya=primary[a['id']]['lag_ms'];yb=primary[b['id']]['lag_ms'];
        assert features(a,power)[0]==features(b,power)[0]
        pairrows.append({'family':family,'split':a['split'],'cluster':ya,'spread':yb,'ratio':ya/yb,'unordered_min_mean_abs_error_ms':abs(ya-yb)/2})
    result['pairs']={s:{'n':len(rr),'median_ratio':float(np.median([r['ratio'] for r in rr])),'median_unordered_lower_bound_ms':float(np.median([r['unordered_min_mean_abs_error_ms'] for r in rr]))} for s in ['short','long'] if (rr:=[r for r in pairrows if r['split']==s])}
    import csv
    with (DATA/'predictions.csv').open('w',newline='') as out:
        writer=csv.DictWriter(out,fieldnames=['id','family','split','variant','n_cpu','observed_lag_ms','duration_ms','region_ms']+list(ensemble));writer.writeheader()
        for i,p in enumerate(programs):writer.writerow({k:p[k] for k in ['id','family','split','variant','n_cpu']}|{'observed_lag_ms':y[i],'duration_ms':primary[p['id']]['duration_ms'],'region_ms':primary[p['id']]['region_ms']}|{m:float(v[i]) for m,v in ensemble.items()})
    (DATA/'paired_counterfactuals.json').write_text(json.dumps(pairrows,indent=2));result['analysis_seconds']=time.perf_counter()-t0
    (DATA/'results.json').write_text(json.dumps(result,indent=2));print(json.dumps(result['summary'],indent=2),flush=True)
if __name__=='__main__':main()

"""Independent arithmetic and consistency checks, no model refitting."""
import csv,json,math,statistics,hashlib
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[2];D=ROOT/'data/composition'
def check(cond,msg):
    global assertions
    assertions+=1
    if not cond:raise AssertionError(msg)
def metric(y,p):
    ape=[abs(b-a)/max(a,1)*100 for a,b in zip(y,p)]
    return dict(mdape=float(np.median(ape)),p90ape=float(np.percentile(ape,90)),mae_ms=float(np.mean([abs(b-a) for a,b in zip(y,p)])),under2_pct=sum(b<a/2 for a,b in zip(y,p))/len(y)*100)
assertions=0
design=json.loads((D/'design.json').read_text());plans={p['id']:p for p in design['programs']};res=json.loads((D/'results.json').read_text());rows=list(csv.DictReader((D/'predictions.csv').open()));pred={r['id']:r for r in rows}
observed={};counts={}
for source,expected in [('asyncio-timer',3200),('uvloop-timer',1600),('uvloop-http',1600)]:
    raw=[json.loads(x) for x in (D/f'raw-{source}.jsonl').read_text().splitlines()];check(len(raw)==expected,'raw count');groups={};seen=set()
    for r in raw:
        p=plans[r['id']];key=(r['id'],r['rep']);check(key not in seen,'duplicate repeat');seen.add(key)
        check(r['family']==p['family'] and r['split']==p['split'],'identity');check(len(r['node_ms'])==len(p['nodes']),'trace length')
        check(math.isclose(r['lag_ms'],max(r['callback_lags_ms']),rel_tol=1e-12),'callback max')
        region=0;regions=[]
        for node,ms in zip(p['nodes'],r['node_ms']):
            check(ms>=0,'positive time')
            if node['kind']=='await' and node['suspends']:regions.append(region);region=0
            else:region+=ms
        regions.append(region);check(abs(max(regions)-r['region_ms'])<1e-10,'trace composition');groups.setdefault(r['id'],[]).append(r)
    check(all(len(g)==5 for g in groups.values()),'5 repeats');observed[source]={k:float(np.median([r['lag_ms'] for r in v])) for k,v in groups.items()}
    for split,models in res['summary'][source].items():
        ids=[r['id'] for r in rows if r['split']==split];y=[observed[source][i] for i in ids]
        for model,values in models.items():
            got=metric(y,[float(pred[i][model]) for i in ids])
            for field,value in values.items():check(abs(got[field]-value)<1e-9,'metric '+model+field)
for r in rows:check(abs(float(r['observed_lag_ms'])-observed['asyncio-timer'][r['id']])<1e-10,'median target')
families={}
for p in plans.values():families.setdefault(p['family'],[]).append(p)
identities={};pairs=[]
for fid,ps in families.items():
    check(len(ps)==4,'variants');check(len({p['split'] for p in ps})==1,'group separation')
    signatures=[tuple(sorted((n['kind'],n['size']) for n in p['nodes'] if n['kind']!='await')) for p in ps]
    check(len(set(signatures))==1,'matched operations');check(signatures[0] not in identities,'family uniqueness');identities[signatures[0]]=fid
    a=next(p for p in ps if p['variant']=='cluster');b=next(p for p in ps if p['variant']=='spread');ra=pred[a['id']];rb=pred[b['id']]
    check(float(ra['bag_et'])==float(rb['bag_et']),'unordered counterfactual equality')
    ya=float(ra['observed_lag_ms']);yb=float(rb['observed_lag_ms'])
    pairs.append({'family':fid,'split':a['split'],'ratio':ya/yb,'duration_ratio':float(ra['duration_ms'])/float(rb['duration_ms']),'min_mae_ms':abs(ya-yb)/2,'minimax_ape_pct':abs(ya-yb)/(ya+yb)*100,'opposite_budget':(ya>20)!=(yb>20)})
extra={'assertions':0,'counterfactual':{},'lengths':{},'variants':{},'classification':{},'replay':{},'seed_ranges':{}}
for split in ['short','long']:
    rr=[r for r in pairs if r['split']==split];extra['counterfactual'][split]={field:float(np.median([r[field] for r in rr])) for field in ['ratio','duration_ratio','min_mae_ms','minimax_ape_pct']};extra['counterfactual'][split]['n_opposite_budget']=sum(r['opposite_budget'] for r in rr)
for n in [4,6,8]:
    rr=[r for r in rows if int(r['n_cpu'])==n];y=[float(r['observed_lag_ms']) for r in rr];extra['lengths'][str(n)]={m:metric(y,[float(r[m]) for r in rr]) for m in ['effect_neural','effect_power','ordered_gru','bag_et','syntax']}
for variant in ['cluster','spread','mixed','cached']:
    rr=[r for r in rows if r['split']=='long' and r['variant']==variant];y=[float(r['observed_lag_ms']) for r in rr];extra['variants'][variant]={m:metric(y,[float(r[m]) for r in rr]) for m in ['effect_neural','effect_power','ordered_gru','largest','syntax','sum']}
rr=[r for r in rows if r['split'] in ['short','long']];y=np.array([float(r['observed_lag_ms']) for r in rr])
for m in ['effect_neural','effect_power','ordered_gru','largest','syntax','sum']:
    yp=np.array([float(r[m]) for r in rr]);extra['classification'][m]={'offload_pct':float(np.mean(yp>20)*100),'false_negative_count':int(np.sum((yp<=20)&(y>20))),'true_positive_denominator':int(np.sum(y>20)),'false_positive_count':int(np.sum((yp>20)&(y<=20)))}
for model in ['effect_neural','ordered_gru','ordered_mlp','bag_et']:
    vals=[r['mdape'] for r in res['seed_metrics'] if r['model']==model and r['source']=='asyncio-timer' and r['split']=='long'];extra['seed_ranges'][model]={'min':min(vals),'median':float(np.median(vals)),'max':max(vals)}
replay=[json.loads(x) for x in (D/'http_replay.jsonl').read_text().splitlines()];check(len(replay)==960,'replay count');groups={}
for r in replay:
    check(abs(max(r['probe_rtt_ms'])-r['max_probe_rtt_ms'])<1e-10,'probe maximum')
    m=r['policy'];offload=m=='all_offload' or (m!='inline' and float(pred[r['id']][m])>20);check(r['offload']==offload,'frozen policy');groups.setdefault((r['id'],m),[]).append(r)
check(all(len(v)==3 for v in groups.values()),'replay repeats')
for policy in ['inline','all_offload','effect_neural','largest','ordered_gru']:
    gs=[g for (i,m),g in groups.items() if m==policy];maxima=[float(np.median([r['max_probe_rtt_ms'] for r in g])) for g in gs];heavy=[float(np.median([r['heavy_rtt_ms'] for r in g])) for g in gs]
    extra['replay'][policy]={'programs':len(gs),'offload_pct':sum(g[0]['offload'] for g in gs)/len(gs)*100,'median_max_probe_ms':float(np.median(maxima)),'p90_max_probe_ms':float(np.percentile(maxima,90)),'median_heavy_ms':float(np.median(heavy)),'p90_heavy_ms':float(np.percentile(heavy,90)),'programs_max_probe_gt20':sum(v>20 for v in maxima)}
# Family-paired replay comparison; three repeats remain inside each program.
familyids=sorted({i.rsplit('-',1)[0] for i,m in groups if m=='inline'});rng=np.random.default_rng(20261121);draws=rng.integers(0,len(familyids),(10000,len(familyids)))
def matrix(policy):
    return np.array([[np.median([r['max_probe_rtt_ms'] for r in groups[(p['id'],policy)]]) for p in plans.values() if p['family']==fid] for fid in familyids])
base=matrix('inline');active=matrix('effect_neural');delta=np.median(base[draws].reshape(10000,-1),axis=1)-np.median(active[draws].reshape(10000,-1),axis=1)
extra['replay_ci']={'median_reduction_ms':float(np.median(base)-np.median(active)),'ci95_ms':np.percentile(delta,[2.5,97.5]).tolist()}
rr=[r for r in rows if r['split']=='long'];ff=sorted({r['family'] for r in rr});rng=np.random.default_rng(20261119);draws=rng.integers(0,len(ff),(10000,len(ff)));extra['simultaneous_comparisons']={}
for m in ['bag_et','ordered_et','ordered_mlp','ordered_gru','effect_power','syntax']:
    e1=np.array([abs(float(r[m])-float(r['observed_lag_ms']))/max(float(r['observed_lag_ms']),1)*100 for r in rr]).reshape(len(ff),4)
    e2=np.array([abs(float(r['effect_neural'])-float(r['observed_lag_ms']))/max(float(r['observed_lag_ms']),1)*100 for r in rr]).reshape(len(ff),4)
    delta=np.median(e1[draws].reshape(10000,-1),axis=1)-np.median(e2[draws].reshape(10000,-1),axis=1)
    extra['simultaneous_comparisons'][m]={'difference_pp':float(np.median(e1)-np.median(e2)),'bonferroni_ci':np.percentile(delta,[100*.05/12,100*(1-.05/12)]).tolist()}
extra['assertions']=assertions;extra['primary_lag_range_ms']=[min(observed['asyncio-timer'].values()),max(observed['asyncio-timer'].values())]
(D/'verification.json').write_text(json.dumps(extra,indent=2));print(json.dumps({k:extra[k] for k in ['assertions','counterfactual','replay','replay_ci','seed_ranges']},indent=2));print('paired primary CI',json.dumps(res['paired_long_vs_effect_neural'],indent=2))

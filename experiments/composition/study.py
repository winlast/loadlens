"""Controlled composition benchmark. Run in research worktree, not main."""
import argparse, asyncio, hashlib, json, math, os, platform, random, statistics, sys, time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from core.workload import cpu_hash,cpu_sort,cpu_image,db_read,ensure_database
FUNCS={'hash':cpu_hash,'sort':cpu_sort,'jpeg':cpu_image,'db':db_read}
KINDS=list(FUNCS)
RANGES={'hash':(20000,160000),'sort':(10000,100000),'jpeg':(128,640),'db':(1000,20000)}
DATA=ROOT/'data/composition'

def make_design():
    rng=random.Random(20261116);families=[];seen=set()
    regimes=[('train',64,[2,3]),('validation',16,[2,3]),('short',32,[2,3]),('long',48,[4,6,8])]
    for split,count,lengths in regimes:
        for i in range(count):
            n=lengths[i%len(lengths)]
            while True:
                ops=[{'kind':rng.choice(KINDS)} for _ in range(n)]
                for op in ops:
                    lo,hi=RANGES[op['kind']];op['size']=round(math.exp(rng.uniform(math.log(lo),math.log(hi))))
                    if op['kind']=='jpeg':op['size']=max(128,round(op['size']/8)*8)
                sig=tuple(sorted((o['kind'],o['size']) for o in ops))
                if sig not in seen:seen.add(sig);break
            fid=f'{split}-{i:03d}';waits=[{'kind':'await','size':3,'suspends':True} for _ in range(n-1)]
            programs=[]
            programs.append({'variant':'cluster','nodes':ops+waits})
            spread=[]
            for j,op in enumerate(ops):
                spread.append(op)
                if j<n-1:spread.append(waits[j])
            programs.append({'variant':'spread','nodes':spread})
            for variant,all_hits in [('mixed',False),('cached',True)]:
                nodes=[];ai=0
                for node in spread:
                    node=dict(node)
                    if node['kind']=='await':
                        node['suspends']=False if all_hits else ai%2==1;ai+=1
                    nodes.append(node)
                programs.append({'variant':variant,'nodes':nodes})
            for program in programs:program.update(id=f'{fid}-{program["variant"]}',family=fid,split=split,n_cpu=n)
            families.extend(programs)
    levels={k:sorted(set(round(math.exp(math.log(lo)+j/11*math.log(hi/lo))) for j in range(12))) for k,(lo,hi) in RANGES.items()}
    design={'seed':20261116,'calibration_levels':levels,'repeats':5,'period_ms':1,'programs':families,
            'protocol':'Frozen before full measurements; pilot excluded. Short train/validation; grouped short/long tests. 4 variants/family.'}
    DATA.mkdir(exist_ok=True);(DATA/'design.json').write_text(json.dumps(design,indent=2))
    print('Design:',len(families),'programs',flush=True)
    return design

async def cached():return b'cached'

async def run_program(program,client=None):
    """Record external-to-task periodic callback lag and diagnostic node wall time."""
    loop=asyncio.get_running_loop();delays=[];running=True
    def tick(expected):
        now=loop.time();delays.append(max(0.,(now-expected)*1000))
        if running:loop.call_later(.001,tick,now+.001)
    loop.call_later(.001,tick,loop.time()+.001)
    await asyncio.sleep(.003);delays.clear();trace=[];t0=time.perf_counter()
    for node in program['nodes']:
        a=time.perf_counter();kind=node['kind']
        if kind=='await':
            if not node['suspends']:await cached()
            elif client is None:await asyncio.sleep(node['size']/1000)
            else:await client.get('/wait',params={'ms':node['size']})
        else:FUNCS[kind](node['size'])
        trace.append((time.perf_counter()-a)*1000)
    duration=(time.perf_counter()-t0)*1000
    await asyncio.sleep(.004);running=False
    regions=[];region=0.
    for node,ms in zip(program['nodes'],trace):
        if node['kind']=='await' and node['suspends']:regions.append(region);region=0.
        else:region+=ms
    regions.append(region)
    return {'duration_ms':duration,'lag_ms':max(delays,default=0.),'region_ms':max(regions),'node_ms':trace,'callback_lags_ms':delays}

def environment():
    import importlib.metadata as md
    packages={}
    for name in ['numpy','scipy','scikit-learn','torch','uvloop','httpx','Pillow','fastapi','uvicorn']:
        try:packages[name]=md.version(name)
        except md.PackageNotFoundError:pass
    return {'python':sys.version,'platform':platform.platform(),'packages':packages,'cpu':Path('/proc/cpuinfo').read_text().split('model name')[1].splitlines()[0],
            'affinity':sorted(os.sched_getaffinity(0)),'time_utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())}

async def collect(args):
    ensure_database();DATA.mkdir(exist_ok=True)
    design=json.loads((DATA/'design.json').read_text())
    env=environment();env.update(loop=args.loop,transport=args.transport)
    (DATA/f'environment-{args.loop}-{args.transport}.json').write_text(json.dumps(env,indent=2))
    calibration=DATA/'calibration.jsonl'
    if args.loop=='asyncio' and args.transport=='timer' and not calibration.exists():
        order=[(kind,size,rep) for rep in range(5) for kind,sizes in design['calibration_levels'].items() for size in sizes]
        random.Random(20261117).shuffle(order)
        for kind in KINDS:FUNCS[kind](RANGES[kind][0])
        with calibration.open('w') as out:
            for kind,size,rep in order:
                a=time.perf_counter();FUNCS[kind](size);ms=(time.perf_counter()-a)*1000
                out.write(json.dumps({'kind':kind,'size':size,'rep':rep,'ms':ms})+'\n');out.flush()
    programs=[p for p in design['programs'] if args.split=='all' or p['split'] in args.split.split(',')]
    order=[(p,rep) for rep in range(design['repeats']) for p in programs];random.Random(20261118).shuffle(order)
    output=DATA/f'raw-{args.loop}-{args.transport}.jsonl'
    done=set()
    if output.exists():
        done={(r['id'],r['rep']) for r in map(json.loads,output.read_text().splitlines())}
    client=None
    if args.transport=='http':
        import httpx
        client=httpx.AsyncClient(base_url='http://127.0.0.1:18391',timeout=10,trust_env=False)
        await client.get('/wait',params={'ms':1})
    with output.open('a') as out:
        for i,(program,rep) in enumerate(order):
            if (program['id'],rep) in done:continue
            row=await run_program(program,client);row.update(id=program['id'],family=program['family'],split=program['split'],variant=program['variant'],n_cpu=program['n_cpu'],rep=rep,order=i)
            out.write(json.dumps(row)+'\n');out.flush()
            if i%100==0:print(args.loop,args.transport,i,'/',len(order),flush=True)
    if client:await client.aclose()
    print('Complete',output,flush=True)

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('action',choices=['design','collect']);ap.add_argument('--loop',default='asyncio',choices=['asyncio','uvloop']);ap.add_argument('--transport',default='timer',choices=['timer','http']);ap.add_argument('--split',default='all');args=ap.parse_args()
    if args.action=='design':make_design()
    elif args.loop=='uvloop':
        import uvloop
        uvloop.run(collect(args))
    else:asyncio.run(collect(args))

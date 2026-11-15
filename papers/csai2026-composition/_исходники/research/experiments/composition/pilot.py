import asyncio, json, statistics, time, sys, platform
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from core.workload import cpu_hash, cpu_sort, cpu_image, db_read, ensure_database

FUNCS={'hash':cpu_hash,'sort':cpu_sort,'jpeg':cpu_image,'db':db_read}

async def execute(nodes):
    loop=asyncio.get_running_loop(); delays=[]; running=True
    def tick(expected):
        now=loop.time(); delays.append(max(0.,(now-expected)*1000))
        if running: loop.call_later(.001,tick,now+.001)
    loop.call_later(.001,tick,loop.time()+.001)
    await asyncio.sleep(.003)
    delays.clear(); trace=[]; start=time.perf_counter()
    for kind,size in nodes:
        a=time.perf_counter()
        if kind=='wait': await asyncio.sleep(size/1000)
        elif kind=='hit': await cached()
        else: FUNCS[kind](size)
        trace.append({'kind':kind,'size':size,'ms':(time.perf_counter()-a)*1000})
    duration=(time.perf_counter()-start)*1000
    await asyncio.sleep(.004); running=False
    return {'nodes':nodes,'duration_ms':duration,'max_lag_ms':max(delays,default=0),'trace':trace,'delays_ms':delays}
async def cached(): return b'cached'
async def main():
    ensure_database()
    grid={'hash':[20000,40000,80000,120000], 'sort':[10000,20000,40000,80000], 'jpeg':[128,256,384,512], 'db':[1000,4000,10000,20000]}
    result={'env':{'python':sys.version,'platform':platform.platform()},'calibration':[],'plans':[]}
    for kind,sizes in grid.items():
        for size in sizes:
            vals=[]
            for rep in range(3):
                a=time.perf_counter();FUNCS[kind](size);vals.append((time.perf_counter()-a)*1000)
            result['calibration'].append({'kind':kind,'size':size,'times_ms':vals})
            print(kind,size,round(statistics.median(vals),3),flush=True)
    cpu=[('hash',80000),('sort',40000),('jpeg',384),('db',10000)]
    programs={'cluster':cpu+[('wait',3)]*3,'spread':sum(([op,('wait',3)] for op in cpu[:-1]),[])+cpu[-1:], 'cached':sum(([op,('hit',0)] for op in cpu[:-1]),[])+cpu[-1:]}
    for rep in range(5):
        for name,plan in programs.items():
            row=await execute(plan);row.update(name=name,rep=rep);result['plans'].append(row)
            print(name,round(row['duration_ms'],2),round(row['max_lag_ms'],2),flush=True)
    target=ROOT/'data/composition/pilot.json';target.parent.mkdir(exist_ok=True);target.write_text(json.dumps(result,indent=2))
if __name__=='__main__': asyncio.run(main())

import asyncio,csv,json,random,time
from pathlib import Path
import httpx,numpy as np
ROOT=Path(__file__).resolve().parents[2];DATA=ROOT/'data/composition'
async def main():
    predictions={r['id']:r for r in csv.DictReader((DATA/'predictions.csv').open())}
    design=json.loads((DATA/'design.json').read_text())
    programs=[p for p in design['programs'] if p['split'] in ['short','long'] and int(p['family'].split('-')[1])<8]
    policies=['inline','all_offload','effect_neural','largest','ordered_gru']
    order=[(p,policy,rep) for rep in range(3) for policy in policies for p in programs];random.Random(20261120).shuffle(order)
    path=DATA/'http_replay.jsonl';done=set()
    if path.exists():done={(r['id'],r['policy'],r['rep']) for r in map(json.loads,path.read_text().splitlines())}
    async with httpx.AsyncClient(base_url='http://127.0.0.1:18392',trust_env=False,timeout=20) as heavy, httpx.AsyncClient(base_url='http://127.0.0.1:18392',trust_env=False,timeout=20) as probe:
        idle=[]
        for _ in range(100):
            a=time.perf_counter();await probe.get('/ping');idle.append((time.perf_counter()-a)*1000);await asyncio.sleep(.001)
        (DATA/'http_replay_idle.json').write_text(json.dumps({'rtt_ms':idle,'median_ms':float(np.median(idle))},indent=2))
        with path.open('a') as out:
            for i,(p,policy,rep) in enumerate(order):
                if (p['id'],policy,rep) in done:continue
                pred=predictions[p['id']];offload=policy=='all_offload' or (policy!='inline' and float(pred[policy])>20)
                running=True;latencies=[]
                async def probes():
                    while running:
                        a=time.perf_counter();await probe.get('/ping');latencies.append((time.perf_counter()-a)*1000);await asyncio.sleep(.001)
                task=asyncio.create_task(probes());await asyncio.sleep(.004)
                a=time.perf_counter();response=await heavy.post('/run',json={'id':p['id'],'offload':offload});response.raise_for_status();rtt=(time.perf_counter()-a)*1000
                await asyncio.sleep(.004);running=False;await task
                row={'id':p['id'],'family':p['family'],'split':p['split'],'variant':p['variant'],'policy':policy,'offload':offload,'rep':rep,'order':i,'heavy_rtt_ms':rtt,'server_ms':response.json()['ms'],'probe_rtt_ms':latencies,'max_probe_rtt_ms':max(latencies)}
                out.write(json.dumps(row)+'\n');out.flush()
                if i%100==0:print('HTTP replay',i,'/',len(order),flush=True)
    print('HTTP replay complete',flush=True)
if __name__=='__main__':asyncio.run(main())

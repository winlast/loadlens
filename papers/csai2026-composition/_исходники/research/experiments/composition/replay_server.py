import asyncio,json,sys,time,multiprocessing
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from experiments.composition.study import FUNCS,ensure_database,cached
from fastapi import FastAPI
import uvicorn
PROGRAMS={p['id']:p for p in json.loads((ROOT/'data/composition/design.json').read_text())['programs']}
app=FastAPI();pool=None

def sync_execute(nodes):
    result=0
    for n in nodes:
        if n['kind']=='await':
            if n['suspends']:time.sleep(n['size']/1000)
        else:result=FUNCS[n['kind']](n['size'])
    return str(result)[:8]

async def async_execute(nodes):
    for n in nodes:
        if n['kind']=='await':
            if n['suspends']:await asyncio.sleep(n['size']/1000)
            else:await cached()
        else:FUNCS[n['kind']](n['size'])

@app.on_event('startup')
async def start():
    global pool
    ensure_database();pool=ProcessPoolExecutor(max_workers=2,mp_context=multiprocessing.get_context('spawn'))
    loop=asyncio.get_running_loop();await asyncio.gather(*(loop.run_in_executor(pool,sync_execute,[]) for _ in range(2)))

@app.on_event('shutdown')
async def close():
    pool.shutdown()

@app.get('/ping')
async def ping():return {'ok':True}

@app.post('/run')
async def run(body:dict):
    nodes=PROGRAMS[body['id']]['nodes'];a=time.perf_counter()
    if body['offload']:await asyncio.get_running_loop().run_in_executor(pool,sync_execute,nodes)
    else:await async_execute(nodes)
    return {'ms':(time.perf_counter()-a)*1000}

if __name__=='__main__':uvicorn.run(app,host='127.0.0.1',port=18392,loop='uvloop',access_log=False)

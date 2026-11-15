from pathlib import Path
import sys,json,zipfile,hashlib,subprocess,collections,ast
BASE=Path(__file__).resolve().parent
OUT=BASE.parent.parent if BASE.parent.name=='_исходники' else BASE.parents[1]/'outputs/CSAI2026_Composition'
archive=OUT/'CSAI2026_Composition_Anonymous_Research.zip'
report={}
with zipfile.ZipFile(archive) as z:
    names=z.namelist();manifest=json.loads(z.read('SHA256SUMS.json'))
    assert all(hashlib.sha256(z.read(name)).hexdigest()==digest for name,digest in manifest.items())
    assert set(names)==set(manifest)|{'SHA256SUMS.json'}
    for suffix in ['docx','pdf']:assert z.read('paper/CSAI2026_Composition_Anonymous.'+suffix)==(OUT/('CSAI2026_Composition_Anonymous.'+suffix)).read_bytes()
    py=[n for n in names if n.endswith('.py')]
    for name in py:ast.parse(z.read(name).decode('utf8'),filename=name)
    groups=collections.Counter('measurements/results' if n.startswith('data/composition/') else 'operation library' if n.startswith('core/') else 'experiment code/protocols' if n.startswith('experiments/') else 'paper' if n.startswith('paper/') else 'database' if n=='data/workload.db' else 'instructions/dependencies/manifest' for n in names)
    report={'file_count':len(names),'python_files':len(py),'zip_bytes':archive.stat().st_size,'uncompressed_bytes':sum(i.file_size for i in z.infolist()),'groups':dict(groups),'all_manifest_hashes_valid':True,'paper_matches_deliverables':True,'paths':names}
    expected={'raw-asyncio-timer.jsonl':3200,'raw-uvloop-timer.jsonl':1600,'raw-uvloop-http.jsonl':1600,'http_replay.jsonl':960,'calibration.jsonl':240}
    for name,n in expected.items():assert len(z.read('data/composition/'+name).splitlines())==n
    report['record_counts']=expected
repo='/home/winlast/projects/loadlens-csai'
for branch in ['main','research']:
    proc=subprocess.run(['wsl','-e','git','-c','core.quotepath=false','-C',repo,'ls-tree','-r','--name-only',branch],capture_output=True,text=True,encoding='utf8',check=True)
    files=proc.stdout.splitlines();report[branch+'_tracked_files']=len(files);report[branch+'_top_level_counts']=dict(collections.Counter(p.split('/')[0] if '/' in p else '(root)' for p in files))
(OUT/'_исходники/qa/archive_audit.json').write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding='utf8')
print(json.dumps({k:v for k,v in report.items() if k!='paths'},indent=2,ensure_ascii=False))

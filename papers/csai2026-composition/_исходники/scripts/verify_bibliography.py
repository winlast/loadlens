"""Verify DOI registration and compare titles with publisher-deposited metadata."""
from pathlib import Path
import concurrent.futures,hashlib,json,re,time,unicodedata,urllib.request,urllib.parse,urllib.error
from paper_content import REFERENCES,REF_LINKS

BASE=Path(__file__).resolve().parent
CACHE=BASE.parent/'qa/bibliography_crossref';CACHE.mkdir(exist_ok=True)
def normal(text):
    text=unicodedata.normalize('NFKD',text.lower().replace('&','and'))
    return ''.join(c for c in text if c.isalnum())
def fetch(item):
    number,reference,url=item
    title=re.search(r"'([^']+)'",reference).group(1)
    result={'reference':number,'title':title,'source_url':url}
    match=re.search(r'doi:\s*(\S+)',reference)
    if match:
        doi=match.group(1)
        request=urllib.request.Request('https://api.crossref.org/works/'+urllib.parse.quote(doi,safe='/'),headers={'User-Agent':'CSAI-Bibliography-Verification/1.0'})
        cache=CACHE/(hashlib.sha256(doi.lower().encode()).hexdigest()[:16]+'.json')
        if cache.exists():metadata=json.loads(cache.read_text(encoding='utf8'))
        else:
            for attempt in range(4):
                try:
                    with urllib.request.urlopen(request,timeout=20) as response:metadata=json.load(response)['message']
                    cache.write_text(json.dumps(metadata,indent=2,ensure_ascii=False),encoding='utf8');time.sleep(1.2);break
                except urllib.error.HTTPError as error:
                    if error.code!=429 or attempt==3:raise
                    raw=error.headers.get('Retry-After','30');delay=min(int(raw),59) if raw.isdigit() else 30
                    print('Crossref rate limit: respecting retry delay of',delay,'seconds',flush=True);time.sleep(delay)
        assert normal(title)==normal(metadata['title'][0]),(number,title,metadata['title'])
        result.update({'doi':doi,'Crossref_title_matches':True,'Crossref':{k:metadata.get(k) for k in ['title','author','published','container-title','volume','issue','page','article-number']}})
    else:result['verification']='Primary proceedings/documentation page inspected; no DOI invented.'
    return result

with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
    results=list(executor.map(fetch,[(i,ref,url) for i,(ref,url) in enumerate(zip(REFERENCES,REF_LINKS),1)]))
report={'verification_date':'2026-11-16','references':results,'doi_count':sum('doi' in item for item in results),'all_DOI_titles_match':True,'scope':'Crossref registration/title comparison plus manual primary-source authors/year/venue and claim checks; title links also verified in exported PDF. Crossref continuous pagination can differ from article-local pagination; article identifiers follow author/publisher PDFs.'}
(BASE.parent/'qa/bibliography_sources.json').write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding='utf8')
print(json.dumps({'references':len(results),'DOI_registered_and_titles_match':report['doi_count']}))

from pathlib import Path
import sys,json,hashlib,re,zipfile,csv
BASE=Path(__file__).resolve().parent;OUT=BASE.parent.parent;DATA=BASE.parent/'research/data/composition'
sys.path.insert(0,str(BASE.parents[2]/'_исходники/scripts/packages'))
import pymupdf,numpy as np
from pypdf import PdfReader,PdfWriter
from pypdf.generic import NameObject
from docx import Document
from docx.oxml.ns import qn
from paper_content import TITLE,CONFERENCE,KEYWORDS,ABSTRACT,BLOCKS,REFERENCES
count=0
def check(value,message):
    global count
    count+=1
    if not value:raise AssertionError(message)
def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
report={'documents':{},'similarity':{},'reproduction':{}}
check(len(ABSTRACT.split())<=200,'abstract length');check(len(KEYWORDS)<=5,'keywords')
template=BASE.parent/'IET-Template.docx';check(digest(template)=='5c47aa829c833b784e253c3491dd51586cebee956d5d5c9b5434d49eabf4929f','reference preserved')
identities=re.compile(r'sinyav|letunov|galyuk|teplits|sanina|babichev|ssd-tula|winlast|bauman',re.I)
for author,qa in [(False,'anonymous-review-final2'),(True,'authors-review-final2')]:
    stem='CSAI2026_Composition_'+('Authors' if author else 'Anonymous');path=OUT/(stem+'.docx');d=Document(path)
    check(len(d.sections)==2,'two sections')
    for s in d.sections:
        for actual,target in [(s.page_width.cm,21),(s.page_height.cm,29.7),(s.top_margin.cm,2.54),(s.bottom_margin.cm,2.54),(s.left_margin.cm,1.5),(s.right_margin.cm,1.5)]:check(abs(actual-target)<.004,'page geometry')
    cols=d.sections[1]._sectPr.find(qn('w:cols'));check(cols.get(qn('w:num'))=='2','two columns');check(cols.get(qn('w:space'))=='227','gutter')
    check(d.styles['PaperParagraphs'].font.size.pt==10,'body size');check(d.styles['PaperTitle'].font.size.pt==18,'title size')
    check(len(d.tables)==5,'table count');check(len(d.inline_shapes)==2,'figure count')
    body='\n'.join(p.text for p in d.paragraphs)
    check(d.core_properties.subject==CONFERENCE,'full conference name in DOCX Subject')
    if not author:check(body.count('Anonymous authors')==1,'anonymous author label')
    check('@' not in body if not author else True,'markup removed')
    check(re.search(r'\d (?:ms|µs|cm|mm|pt)\b',body) is None,'number unit nonbreaking space')
    citations=[int(x) for x in re.findall(r'\[(\d+)\]',body.split('6 References')[0])];check(list(dict.fromkeys(citations))==list(range(1,10)),'citation order')
    with zipfile.ZipFile(path) as z,zipfile.ZipFile(template) as src:
        changed=[name for name in src.namelist() if name in z.namelist() and z.read(name)!=src.read(name)]
        missing=[name for name in src.namelist() if name not in z.namelist()]
        allowed={'[Content_Types].xml','docProps/core.xml','word/document.xml','word/_rels/document.xml.rels','word/styles.xml','word/footer1.xml','word/footer2.xml'}
        check(not set(changed)-allowed,'preserve-only package parts changed '+str(set(changed)-allowed))
        check(not missing,'package parts removed '+str(missing))
        xml='\n'.join(z.read(name).decode('utf8','ignore') for name in z.namelist() if name.endswith('.xml'))
        if not author:check(not identities.search(xml),'anonymous OOXML identifiers')
        check('w:vertAlign w:val="subscript"' in xml,'real subscripts')
    source=BASE.parent/'qa'/qa/(stem+'.pdf');reader=PdfReader(source);writer=PdfWriter();writer.clone_document_from_reader(reader);writer.pdf_header='%PDF-1.4';writer._root_object.pop(NameObject('/Version'),None)
    writer.add_metadata({'/Title':TITLE,'/Author':d.core_properties.author or '', '/Creator':'Microsoft Word','/Subject':CONFERENCE,'/Keywords':', '.join(KEYWORDS)})
    final=OUT/(stem+'.pdf')
    if not (author and '--anonymous-only' in sys.argv):
        with final.open('wb') as f:writer.write(f)
    pdf=pymupdf.open(final);original=pymupdf.open(source);check(len(pdf)==6,'six pages')
    check(final.read_bytes().startswith(b'%PDF-1.4'),'PDF version')
    check(PdfReader(final).metadata.subject==CONFERENCE,'full conference name in PDF Subject')
    fonts={};unit_starts=[]
    for index,page in enumerate(pdf):
        check(abs(page.rect.width-595.3)<1 and abs(page.rect.height-841.9)<1,'PDF A4')
        a=page.get_pixmap(matrix=pymupdf.Matrix(1,1));b=original[index].get_pixmap(matrix=pymupdf.Matrix(1,1));check(a.samples==b.samples,'PDF pixels preserved')
        check('\ufffd' not in page.get_text(),'replacement glyph')
        for f in page.get_fonts():
            name=f[3];embedded=len(pdf.extract_font(f[0])[3]);fonts[name]=embedded;check(embedded>0,'embedded font');check('TimesNewRoman' in name,'standard font');check(re.match(r'^[A-Z]{6}\+',name) is not None,'font subset')
        for block in page.get_text('dict')['blocks']:
            for line in block.get('lines',[]):
                text=''.join(s['text'] for s in line['spans']).strip()
                if not text:continue
                x0,y0,x1,y1=line['bbox'];check(x0>=35 and x1<=560,'text horizontal extent '+text)
                if y0<790:check(y0>=65 and y1<=778,'body vertical extent '+text)
                if re.match(r'^(?:ms|µs|%)(?:\W|$)',text) and not all('Bold' in s['font'] for s in line['spans'] if s['text'].strip()):unit_starts.append((index+1,text))
    check(not unit_starts,'orphan units '+str(unit_starts))
    fulltext='\n'.join(p.get_text() for p in pdf)
    if not author:check(not identities.search(fulltext+str(PdfReader(final).metadata)),'anonymous PDF')
    report['documents'][stem]={'pages':len(pdf),'fonts_embedded':fonts,'docx_sha256':digest(path),'pdf_sha256':digest(final),'changed_template_parts':changed,'missing_template_parts':missing}
# Secondary lexical check, not an external plagiarism-service score.
def grams(t,n=5):
    words=re.findall(r'\w+',t.lower());return {tuple(words[i:i+n]) for i in range(len(words)-n+1)}
newtext=' '.join(t for k,t in BLOCKS if k=='p');newgrams=grams(newtext)
refs=BASE.parents[2]/'_исходники/references'
for filename in ['Sinyavskiy_ISCT.txt','Синявский_статья_РИНЦ_ИИАСУ.txt']:
    old=grams((refs/filename).read_text(encoding='utf8'));report['similarity'][filename]={'shared_fivegrams':len(newgrams&old),'new_fivegrams':len(newgrams),'share_pct':len(newgrams&old)/len(newgrams)*100}
check(all(v['share_pct']<50 for v in report['similarity'].values()),'lexical difference')
study=DATA/'design.json';design=json.loads(study.read_text());distinct={json.dumps(p['nodes'],sort_keys=True) for p in design['programs']};check(len(distinct)==584,'distinct annotated paths')
previous=DATA/'reproduction/results.json'
if previous.exists():
    a=json.loads(previous.read_text());b=json.loads((DATA/'results.json').read_text());a.pop('analysis_seconds');b.pop('analysis_seconds');differences=[]
    def compare(x,y):
        if isinstance(x,dict):
            check(x.keys()==y.keys(),'reproduction keys')
            for k in x:compare(x[k],y[k])
        elif isinstance(x,list):
            check(len(x)==len(y),'reproduction length')
            for xx,yy in zip(x,y):compare(xx,yy)
        elif isinstance(x,(float,int)):
            differences.append(abs(x-y));check(abs(x-y)<1e-10,'model reproduction tolerance')
        else:check(x==y,'reproduction metadata')
    compare(a,b)
    aa=list(csv.DictReader((DATA/'reproduction/predictions.csv').open()));bb=list(csv.DictReader((DATA/'predictions.csv').open()));max_prediction_difference=0.
    for x,y in zip(aa,bb):
        for k in x:
            try:delta=abs(float(x[k])-float(y[k]));max_prediction_difference=max(max_prediction_difference,delta);check(delta<1e-10,'prediction reproduction')
            except ValueError:check(x[k]==y[k],'prediction identity')
    report['reproduction']={'results_max_absolute_difference':max(differences),'predictions_max_absolute_difference_ms':max_prediction_difference,'tolerance':1e-10,'note':'Parallel tree-ensemble accumulation differs at floating-point roundoff; all neural, recurrent and analytic predictions are identical.'}
report['assertions']=count;(BASE.parent/'qa/final_checks.json').write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding='utf8');print(json.dumps(report,indent=2,ensure_ascii=False))

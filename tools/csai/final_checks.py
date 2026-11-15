from pathlib import Path
import sys,json,re,hashlib,zipfile
BASE=Path(__file__).resolve().parent
sys.path.insert(0,str(BASE/'packages'))
import pymupdf
from pypdf import PdfReader,PdfWriter
from pypdf.generic import NameObject
from docx import Document
from docx.oxml.ns import qn
from paper_content import TITLE,KEYWORDS,ABSTRACT
OUT=BASE.parent/'outputs'
reports={}
for kind in ['Anonymous','Authors']:
 stem='CSAI2026_SuperPuper_'+kind
 source=BASE/('qa-anonymous-final' if kind=='Anonymous' else 'qa-authors-final')/(stem+'.pdf')
 reader=PdfReader(source);writer=PdfWriter();writer.clone_document_from_reader(reader);writer.pdf_header='%PDF-1.4'
 writer._root_object.pop(NameObject('/Version'),None)
 writer.add_metadata({'/Title':TITLE,'/Author':'' if kind=='Anonymous' else 'Stanislav Sinyavskiy; Artemiy Letunovskiy; Stanislava Galyuk; Kirill Teplitskiy; Anastasia Sanina; Alexander Babichev','/Subject':'The 10th International Conference on Computer Science and Artificial Intelligence (CSAI 2026)','/Keywords':', '.join(KEYWORDS)})
 target=OUT/(stem+'.pdf')
 with target.open('wb') as f:writer.write(f)
 final=pymupdf.open(target);orig=pymupdf.open(source);assert len(final)==len(orig)==6
 fonts=set();sizes=[];lines=[];imagehashes=[]
 for i,(p,o) in enumerate(zip(final,orig)):
  assert p.rect.width==o.rect.width and p.rect.height==o.rect.height
  pix=p.get_pixmap(matrix=pymupdf.Matrix(1,1));opix=o.get_pixmap(matrix=pymupdf.Matrix(1,1));assert pix.samples==opix.samples
  imagehashes.append(hashlib.sha256(pix.samples).hexdigest())
  for font in p.get_fonts():
   assert 'Times' in font[3],font
   assert '+' in font[3],font
   assert len(final.extract_font(font[0])[3])>0,font
   fonts.add(font[3])
  for b in p.get_text('dict')['blocks']:
   for l in b.get('lines',[]):
    text=''.join(s['text'] for s in l['spans']);lines.append(text)
    assert not re.match(r'^\s*(ms|µs|%)\b',text),('unit at line start',i+1,text)
    for s in l['spans']:
     assert 'Times' in s['font'],s
     # Word reports 10pt as9.96 in some PDF spans.
     assert s['size']>=9.9 or (kind=='Authors' and i==0 and s['bbox'][1]<210 and s['text'].strip() in ['1','1*']),(i+1,s)
  footer=[w for w in p.get_text('words') if w[1]>770 and w[4]==str(i+1)]
  assert footer,('missing footer page number',i+1)
 text='\n'.join(p.get_text() for p in final)
 if kind=='Anonymous':assert not re.search(r'Sinyav|Letun|Galyuk|Teplit|Sanina|Babichev|ssd-tula|winlast|github|Bauman',text,re.I)
 d=Document(OUT/(stem+'.docx'))
 assert len(d.sections)==2
 for s in d.sections:
  assert abs(s.page_width.cm-21)<.01 and abs(s.page_height.cm-29.7)<.01
  assert abs(s.left_margin.cm-1.5)<.01 and abs(s.right_margin.cm-1.5)<.01
 assert d.sections[1]._sectPr.find(qn('w:cols')).get(qn('w:num'))=='2'
 assert d.sections[1]._sectPr.find(qn('w:cols')).get(qn('w:space'))=='227'
 assert len(d.tables)==4 and len(d.inline_shapes)==2
 paras=[p.text for p in d.paragraphs]
 assert next(i for i,x in enumerate(paras) if x.startswith('Keywords:'))<paras.index('Abstract')
 assert len(ABSTRACT.split())<=200 and len(KEYWORDS)<=5
 main='\n'.join(paras[:paras.index('6 References')])
 refs=[int(n) for n in re.findall(r'\[(\d+)\]',main)]
 assert list(dict.fromkeys(refs))==list(range(1,10)),refs
 for i in range(1,5):assert f'Table {i}' in main
 for i in range(1,3):assert f'Fig. {i}' in main
 assert not re.search(r'\d (ms|µs|%)\b','\n'.join(paras))
 for p in d.paragraphs:
  if p.style.name=='PaperHeading' and re.match(r'\d+\.\d+ ',p.text):assert all(r.italic and r.font.size.pt==10 for r in p.runs)
 if kind=='Anonymous':assert not d.core_properties.author and not d.core_properties.last_modified_by
 reports[kind]={'pages':6,'tables':4,'figures':2,'abstract_words':len(ABSTRACT.split()),'keywords':len(KEYWORDS),'body_font_min_pt':10,'pdf_header':target.read_bytes()[:8].decode(),'fonts_embedded_subset':sorted(fonts),'pdf_matches_word_render_pixels':True,'footer_numbers':True,'number_unit_linebreaks':'none found','anonymous_identity_check':kind=='Anonymous','sha256':hashlib.sha256(target.read_bytes()).hexdigest(),'page_pixel_sha256':imagehashes}
(BASE/'format_verification.json').write_text(json.dumps(reports,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps(reports,ensure_ascii=False,indent=2))



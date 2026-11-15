from pathlib import Path
import sys,json,re
BASE=Path(__file__).resolve().parent
OUT=BASE.parent.parent if BASE.parent.name=='_исходники' else BASE.parents[1]/'outputs/CSAI2026_Composition'
sys.path.insert(0,str(OUT.parent/'_исходники/scripts/packages'))
import pymupdf
from docx import Document
from docx.oxml.ns import qn
from pypdf import PdfReader
def font_value(p,r,attribute):
    value=getattr(r.font,attribute)
    style=p.style
    while value is None and style is not None:
        value=getattr(style.font,attribute);style=style.base_style
    return value
report={}
for stem in ['CSAI2026_Composition_Anonymous','CSAI2026_Composition_Authors']:
    d=Document(OUT/(stem+'.docx'));ptext=[p.text for p in d.paragraphs];headings=[];captions=[]
    assert ptext[0]==ptext[0].upper()
    assert next(i for i,t in enumerate(ptext) if t.startswith('Keywords:'))<ptext.index('Abstract')
    for paragraph_index,p in enumerate(d.paragraphs):
        if re.match(r'^\d+(?:\.\d+)? ',p.text):
            level=2 if re.match(r'^\d+\.\d+ ',p.text) else 1
            assert p._p.pPr is None or p._p.pPr.find(qn('w:numPr')) is None
            for r in p.runs:
                assert font_value(p,r,'size').pt==(10 if level==2 else 12)
                assert bool(font_value(p,r,'italic'))==(level==2)
                assert bool(font_value(p,r,'bold'))==(level==1)
            headings.append(p.text)
        if p._p.xpath('.//w:drawing'):
            caption=d.paragraphs[paragraph_index+1]
            assert caption.text.startswith('Fig. ') and caption.text.endswith('.')
            assert all(font_value(caption,r,'size').pt==10 for r in caption.runs)
            captions.append(caption.text)
    assert len(captions)==2
    assert all(c.text.strip() for table in d.tables for row in table.rows for c in row.cells)
    assert not any(c._tc.tcPr is not None and (c._tc.tcPr.find(qn('w:vMerge')) is not None or c._tc.tcPr.find(qn('w:gridSpan')) is not None) for t in d.tables for row in t.rows for c in row.cells)
    for name in ['PaperParagraphs','PaperTitle','PaperAuthor','PaperAffiliations','PaperHeading']:
        assert d.styles[name].element.get_or_add_rPr().find(qn('w:lang')).get(qn('w:val'))=='en-GB'
    body='\n'.join(p.text for p in d.paragraphs if p.text not in captions and not (p._p.getnext() is not None and p._p.getnext().tag==qn('w:tbl')))
    for n in range(1,6):assert re.search(r'\bTable '+str(n)+r'\b',body)
    for n in range(1,3):assert re.search(r'\bFig\. '+str(n)+r'\b',body)
    for n in range(1,4):assert body.count('('+str(n)+')')>=2
    assert re.search(r'\b(?:Eq\.|Equation|Equations|Expression)\s+\(',body) is None
    ref_index=ptext.index('6 References')
    for p in d.paragraphs[ref_index+1:]:assert not any(bool(font_value(p,r,'italic')) for r in p.runs)
    pdf=pymupdf.open(OUT/(stem+'.pdf'));reader=PdfReader(OUT/(stem+'.pdf'));assert not reader.is_encrypted
    image_dpi=[]
    for page in pdf:
        for xref,_,width,height,*_ in page.get_images(full=True):
            for rect in page.get_image_rects(xref):
                dpi=min(width*72/rect.width,height*72/rect.height);assert dpi>0;image_dpi.append(dpi)
    last=pdf[-1];blocks=last.get_text('blocks');ys=[b[3] for b in blocks if b[1]<790];assert max(ys)>700
    report[stem]={'numbered_headings':headings,'caption_sentences':captions,'empty_or_merged_table_cells':False,'all_tables_figures_equations_referenced':True,'UK_English_styles':True,'references_Roman':True,'encrypted':False,'minimum_figure_dpi':min(image_dpi),'last_page_text_bottom_pt':max(ys),'pages':len(pdf)}
(OUT/'_исходники/qa/teacher_checklist.json').write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding='utf8')
print(json.dumps({k:{n:v for n,v in x.items() if n not in ['numbered_headings','caption_sentences']} for k,x in report.items()},indent=2))

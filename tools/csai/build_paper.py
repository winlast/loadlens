from pathlib import Path
import sys, json, re, csv, copy, hashlib
BASE=Path(__file__).resolve().parent
sys.path.insert(0,str(BASE/'packages'))
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.patches import FancyBboxPatch
from docx import Document
from docx.shared import Pt,Cm,RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK, WD_TAB_ALIGNMENT
from docx.enum.section import WD_SECTION_START
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from paper_content import TITLE,KEYWORDS,ABSTRACT,BLOCKS,REFERENCES

OUT=BASE.parents[1]/'docs/CSAI2026';OUT.mkdir(exist_ok=True,parents=True)
DATA=BASE.parents[1]/'data/csai'
RES=json.loads((DATA/'results.json').read_text())
AUD=json.loads((DATA/'audit.json').read_text())
PRED=list(csv.DictReader((DATA/'predictions.csv').open()))
FIG=BASE/'figures';FIG.mkdir(exist_ok=True)
for fn in ['times.ttf','timesbd.ttf','timesi.ttf','timesbi.ttf']:
 font_manager.fontManager.addfont('C:/Windows/Fonts/'+fn)
plt.rcParams.update({'font.family':'Times New Roman','font.size':10,'axes.labelsize':10,'xtick.labelsize':10,'ytick.labelsize':10,'svg.fonttype':'none'})

def figures():
 fig,ax=plt.subplots(figsize=(3.46,2.6));ax.set(xlim=(0,10),ylim=(0,10));ax.axis('off')
 def box(x,y,w,h,t,face='white'):
  ax.add_patch(FancyBboxPatch((x,y),w,h,boxstyle='round,pad=0.12',edgecolor='black',facecolor=face,linewidth=.8));ax.text(x+w/2,y+h/2,t,ha='center',va='center',fontsize=10)
 box(.4,8.1,3.6,1.1,'Training record', '#eeeeee');box(6,8.1,3.6,1.1,'Test record','#eeeeee')
 box(3.1,5.05,3.8,1.35,'Configuration\nroute + parameter')
 box(.4,1.85,3.6,1.3,'Engine\nexecution context');box(6,1.85,3.6,1.3,'Source file\nSHA-256 digest')
 for xx in [2.2,7.8]:
  ax.annotate('',xy=(5,6.55),xytext=(xx,8),arrowprops={'arrowstyle':'->','lw':1.1})
 ax.text(5,7.7,'hasConfiguration',ha='center',fontsize=10)
 ax.text(5,4.15,'Shared node = overlap',ha='center',fontsize=10)
 for a,b in [((2.2,8),(2.2,3.3)),((7.8,8),(7.8,3.3))]:ax.annotate('',xy=b,xytext=a,arrowprops={'arrowstyle':'->','linestyle':'--','lw':.8})
 ax.text(2.1,.6,'measuredOn',ha='center');ax.text(7.8,.6,'wasDerivedFrom',ha='center')
 fig.tight_layout(pad=.1)
 for suffix in ['png','svg']:fig.savefig(FIG/f'graph.{suffix}',dpi=350,bbox_inches='tight',pad_inches=.03)
 plt.close(fig)
 fig,ax=plt.subplots(figsize=(3.46,2.6))
 protocols=['row','group','extrapolation'];positions=[];arrays=[]
 for k,p in enumerate(protocols):
  for j,m in enumerate(['power','mlp']):
   positions.append(k*3+j);arrays.append([r['mdape'] for r in RES['runs'] if r['protocol']==p and r['model']==m])
 bp=ax.boxplot(arrays,positions=positions,widths=.65,patch_artist=True,showfliers=True,medianprops={'color':'black'})
 for i,b in enumerate(bp['boxes']):b.set(facecolor='white' if i%2==0 else '#cccccc',hatch='///' if i%2==0 else '',edgecolor='black')
 ax.set_xticks([.5,3.5,6.5],['Row-wise','Grouped','Upper range']);ax.set_ylabel('Blocking MdAPE, %');ax.set_ylim(0,60);ax.grid(axis='y',alpha=.25)
 from matplotlib.patches import Patch
 ax.legend(handles=[Patch(facecolor='white',hatch='///',label='Power law',edgecolor='black'),Patch(facecolor='#cccccc',label='Perceptron',edgecolor='black')],loc='upper left',fontsize=10,frameon=False)
 fig.tight_layout(pad=.4)
 for suffix in ['png','svg']:fig.savefig(FIG/f'errors.{suffix}',dpi=350,bbox_inches='tight',pad_inches=.03)
 plt.close(fig)

def val(p,m,k='mdape'):return RES['summary'][p][m][k]['median']
def tables(which):
 if which=='overlap':return ('Table 1 Original test overlap at two identity resolutions',['Identity','Shared keys','Test records'],[['Route + parameter','30','69 / 156'],['Route + parameter + engine','24','55 / 156']],[3.9,2.0,2.9])
 if which=='accuracy':
  rr=[]
  for p,plabel in [('row','Row-wise'),('group','Grouped'),('extrapolation','Upper')]:
   for m,mlabel in [('mean','Mean'),('power','Power law'),('mlp','Perceptron')]:
    q=RES['summary'][p][m]['mdape'];s=f"{q['median']:.2f}"
    if q['q25']!=q['q75']:s+=f" [{q['q25']:.2f}, {q['q75']:.2f}]"
    rr.append([plabel,mlabel,s])
  return ('Table 2 Blocking MdAPE in percent as median [interquartile range]',['Regime','Predictor','MdAPE, %'],rr,[2.1,2.1,4.6])
 if which=='routes':
  rr=[]
  for e,label in [('/api/user/profile','Profile'),('/api/feed','Feed'),('/api/search','Search'),('/api/image/thumbnail','Thumbnail'),('/api/report/generate','Report')]:
   vals=[]
   for m in ['power','mlp']:
    v=[]
    for seed in range(20):
     a=[r for r in PRED if r['endpoint']==e and r['protocol']=='extrapolation' and r['model']==m and int(r['seed'])==seed]
     v.append(np.median([abs(float(r['predicted_block_ms'])-float(r['observed_block_ms']))/float(r['observed_block_ms'])*100 for r in a]))
    vals.append(f'{np.median(v):.2f}')
   rr.append([label]+vals)
  return ('Table 3 Upper-range blocking MdAPE by operation',['Operation','Power law, %','Perceptron, %'],rr,[3.0,2.9,2.9])
 if which=='direction':return ('Table 4 Upper-range absolute error and severe underestimation',['Predictor','P90 APE, %','Under half, %'],[[label,f"{val('extrapolation',m,'p90_ape'):.2f}",f"{val('extrapolation',m,'under2_pct'):.2f}"] for m,label in [('mean','Mean'),('power','Power law'),('mlp','Perceptron')]],[3.0,2.9,2.9])

def nonbreak(t):
 t=re.sub(r'(?<=\d)\s?%', '\u00a0%',t)
 return re.sub(r'(\d) (ms|s|µs|cm|mm|pt)\b',lambda m:m[1]+'\u00a0'+m[2],t).replace('route–parameter','route-parameter').replace('route–engine','route-engine').replace('measurement–configuration','measurement-configuration')

def run(p,t,**kwargs):
 r=p.add_run(t)
 for k,v in kwargs.items():setattr(r.font,k,v)
 return r

def build(authors=False):
 d=Document(BASE/'IET-Template.docx')
 # Keep the original styles and footer; replace only documented content slots.
 sec=copy.deepcopy(d.sections[1]._sectPr)
 for e in list(d._element.body):d._element.body.remove(e)
 d._element.body.append(sec)
 for name in ['PaperTitle','PaperAuthor','PaperAffiliations','PaperParagraphs','PaperHeading']:
  st=d.styles[name];st.font.name='Times New Roman';st.font.color.rgb=RGBColor(0,0,0)
 normal=d.styles['PaperParagraphs'];normal.font.size=Pt(10);normal.paragraph_format.space_after=Pt(4);normal.paragraph_format.line_spacing=1
 normal.paragraph_format.widow_control=True
 for s in d.sections:
  s.page_width=Cm(21);s.page_height=Cm(29.7);s.top_margin=Cm(2.54);s.bottom_margin=Cm(2.54);s.left_margin=Cm(1.5);s.right_margin=Cm(1.5);s.gutter=Cm(0)
  cols=s._sectPr.find(qn('w:cols'));cols.set(qn('w:num'),'1');cols.set(qn('w:space'),'227')
  for c in list(cols):cols.remove(c)
 p=d.add_paragraph(TITLE.upper(),'PaperTitle');p.paragraph_format.space_after=Pt(12);p.paragraph_format.keep_with_next=True
 if authors:
  p=d.add_paragraph(style='PaperAuthor');p.paragraph_format.space_after=Pt(6)
  names=['Stanislav Sinyavskiy','Artemiy Letunovskiy','Stanislava Galyuk','Kirill Teplitskiy','Anastasia Sanina','Alexander Babichev']
  for i,n in enumerate(names):
   run(p,(', ' if i else '')+n);run(p,'1*' if i==0 else '1',superscript=True)
  p=d.add_paragraph(style='PaperAffiliations');p.paragraph_format.space_after=Pt(4);run(p,'1',superscript=True);run(p,'Department of Information Processing and Control Systems, Bauman Moscow State Technical University, Moscow, Russia')
  p=d.add_paragraph('*ssd-tula@mail.ru','PaperAffiliations');p.paragraph_format.space_after=Pt(10)
 else:
  # Anonymous placeholders preserve the author-block height without disclosing identity.
  p=d.add_paragraph('Anonymous authors','PaperAuthor');p.paragraph_format.space_after=Pt(6)
  p=d.add_paragraph('Affiliations withheld for double-blind review','PaperAffiliations');p.paragraph_format.space_after=Pt(4)
  p=d.add_paragraph('Correspondence withheld for double-blind review','PaperAffiliations');p.paragraph_format.space_after=Pt(10)
 p=d.add_paragraph(style='PaperParagraphs');run(p,'Keywords: ',bold=True);run(p,', '.join(KEYWORDS))
 p=d.add_paragraph('Abstract','PaperHeading');p.paragraph_format.space_before=Pt(4);p.paragraph_format.space_after=Pt(6)
 d.add_paragraph(nonbreak(ABSTRACT),'PaperParagraphs')
 s=d.add_section(WD_SECTION_START.CONTINUOUS)
 cols=s._sectPr.find(qn('w:cols'));cols.set(qn('w:num'),'2');cols.set(qn('w:space'),'227');cols.set(qn('w:equalWidth'),'1')
 for c in list(cols):cols.remove(c)
 for typ,txt in BLOCKS:
  if typ in ['p','h1','h2']:
   txt=txt.replace('Let the italic symbols c and s denote','Let c and s denote')
   p=d.add_paragraph(nonbreak(txt),'PaperParagraphs' if typ=='p' else 'PaperHeading')
   if typ=='h1':p.paragraph_format.space_before=Pt(8);p.paragraph_format.space_after=Pt(6)
   if typ=='h2':
    p.paragraph_format.space_before=Pt(6);p.paragraph_format.space_after=Pt(6)
    for r in p.runs:r.font.size=Pt(10);r.font.bold=False;r.font.italic=True
   if txt.startswith('Let c and s'):
    p.clear();parts=re.split(r'\b([cs])\b',nonbreak(txt))
    for q in parts:run(p,q,italic=q in ['c','s'])
  elif typ=='equation':
   p=d.add_paragraph(style='PaperParagraphs');p.paragraph_format.tab_stops.add_tab_stop(Cm(8.75),WD_TAB_ALIGNMENT.RIGHT)
   if '(1)' in txt:
    run(p,'C',italic=True);run(p,'(train) ∩ ');run(p,'C',italic=True);run(p,'(test) = {}\t(1)')
   else:
    run(p,'APE = 100 × |');run(p,'ŷ',italic=True);run(p,' − ');run(p,'y',italic=True);run(p,'| / ');run(p,'y',italic=True);run(p,'\t(2)')
    q=d.add_paragraph(style='PaperParagraphs');run(q,'Here ');run(q,'y',italic=True);run(q,' is the observed floored target and ');run(q,'ŷ',italic=True);run(q,' is its prediction.')
  elif typ=='figure':
   fname,caption=txt
   p=d.add_paragraph(style='PaperParagraphs');p.alignment=WD_ALIGN_PARAGRAPH.CENTER;p.paragraph_format.space_after=Pt(3);p.paragraph_format.keep_with_next=True;p.add_run().add_picture(str(FIG/fname),width=Cm(8.7))
   p=d.add_paragraph(nonbreak(caption),'PaperParagraphs');p.paragraph_format.space_after=Pt(8)
  elif typ=='table':
   caption,head,rows,widths=tables(txt);p=d.add_paragraph(caption,'PaperParagraphs');p.paragraph_format.keep_with_next=True
   t=d.add_table(rows=1,cols=len(head));t.autofit=False
   for c,w in zip(t.columns,widths):c.width=Cm(w)
   for row in [head]+rows:
    cells=t.rows[0].cells if row is head else t.add_row().cells
    for j,(c,text) in enumerate(zip(cells,row)):
     c.width=Cm(widths[j]);p=c.paragraphs[0];p.style=d.styles['PaperParagraphs'];p.paragraph_format.space_after=Pt(1.5);p.paragraph_format.space_before=Pt(1.5);p.alignment=WD_ALIGN_PARAGRAPH.LEFT if j==0 else WD_ALIGN_PARAGRAPH.CENTER;run(p,text,bold=row is head)
    trPr=cells[0]._tc.getparent().get_or_add_trPr();el=OxmlElement('w:cantSplit');trPr.append(el)
   pr=t._tbl.tblPr
   borders=OxmlElement('w:tblBorders')
   for edge in ['top','left','bottom','right','insideH','insideV']:
    e=OxmlElement('w:'+edge);e.set(qn('w:val'),'single' if edge in ['top','bottom'] else 'nil');e.set(qn('w:sz'),'4');e.set(qn('w:color'),'000000');borders.append(e)
   pr.append(borders)
   for c in t.rows[0].cells:
    tcPr=c._tc.get_or_add_tcPr();b=OxmlElement('w:tcBorders');e=OxmlElement('w:bottom');e.set(qn('w:val'),'single');e.set(qn('w:sz'),'4');b.append(e);tcPr.append(b)
   d.add_paragraph(style='PaperParagraphs').paragraph_format.space_after=Pt(2)
 for i,ref in enumerate(REFERENCES,1):
  p=d.add_paragraph(f'[{i}] '+ref,'PaperParagraphs');p.paragraph_format.left_indent=Cm(.55);p.paragraph_format.first_line_indent=Cm(-.55);p.paragraph_format.space_after=Pt(5)
 # Restore the template PAGE field explicitly: the removed first section owned its relationship.
 footer=d.sections[0].footer
 p=footer.paragraphs[0];p.clear();p.style=d.styles['PaperParagraphs'];p.paragraph_format.space_after=Pt(0);p.alignment=WD_ALIGN_PARAGRAPH.CENTER
 fld=OxmlElement('w:fldSimple');fld.set(qn('w:instr'),'PAGE'); fr=OxmlElement('w:r'); rp=OxmlElement('w:rPr');rf=OxmlElement('w:rFonts');rf.set(qn('w:ascii'),'Times New Roman');rf.set(qn('w:hAnsi'),'Times New Roman');rp.append(rf);sz=OxmlElement('w:sz');sz.set(qn('w:val'),'20');rp.append(sz);fr.append(rp);ft=OxmlElement('w:t');ft.text='1';fr.append(ft);fld.append(fr);p._p.append(fld)
 # Explicitly standardise footer and keep all identifying metadata out of review copy.
 for s in d.sections:
  for p in s.footer.paragraphs:
   p.alignment=WD_ALIGN_PARAGRAPH.CENTER
   for r in p.runs:r.font.name='Times New Roman';r.font.size=Pt(10)
 cp=d.core_properties;cp.title=TITLE;cp.author='; '.join(names) if authors else '';cp.last_modified_by='';cp.subject='The 10th International Conference on Computer Science and Artificial Intelligence (CSAI 2026)';cp.keywords=', '.join(KEYWORDS);cp.comments='';cp.revision=1
 # Avoid inherited author identity in template custom properties and comments.
 for rel in list(d.part.rels.values()):
  if 'comments' in rel.reltype:d.part.drop_rel(rel.rId)
 path=OUT/('CSAI2026_SuperPuper_Authors.docx' if authors else 'CSAI2026_Anonymous.docx');d.save(path)
 return path

if __name__=='__main__':
 figures()
 for a in [False,True]:print(build(a))
 print('Abstract words',len(ABSTRACT.split()))
 print('Main text words',sum(len(str(t).split()) for _,t in BLOCKS))





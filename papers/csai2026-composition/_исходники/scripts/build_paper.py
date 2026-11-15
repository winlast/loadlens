from pathlib import Path
import sys,copy,re,json,zipfile
BASE=Path(__file__).resolve().parent;OUT=BASE.parent.parent;FIG=BASE.parent/'figures'
sys.path.insert(0,str(BASE.parents[2]/'_исходники/scripts/packages'))
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.patches import FancyBboxPatch
from docx import Document
from docx.shared import Pt,Cm,RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH,WD_TAB_ALIGNMENT
from docx.enum.section import WD_SECTION_START
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from paper_content import TITLE,KEYWORDS,ABSTRACT,BLOCKS,REFERENCES,RESULTS,CHECKS

def figures():
    FIG.mkdir(exist_ok=True)
    for fn in ['times.ttf','timesbd.ttf','timesi.ttf','timesbi.ttf']:font_manager.fontManager.addfont('C:/Windows/Fonts/'+fn)
    plt.rcParams.update({'font.family':'Times New Roman','font.size':10,'axes.labelsize':10,'xtick.labelsize':10,'ytick.labelsize':10,'svg.fonttype':'none'})
    fig,ax=plt.subplots(figsize=(8.7/2.54,6.3/2.54));ax.set(xlim=(0,10),ylim=(0,9));ax.axis('off')
    def box(x,y,label,face='white'):
        ax.add_patch(FancyBboxPatch((x-.95,y-.42),1.9,.84,boxstyle='round,pad=.07',facecolor=face,edgecolor='black',linewidth=.8));ax.text(x,y,label,ha='center',va='center',fontsize=10)
    for y,heading,labels,spans in [(7.3,'A  Clustered',['hash','sort','wait'],[(.6,6.0)]),(4.4,'B  Separated',['hash','wait','sort'],[(.6,2.9),(7.1,9.4)]),(1.5,'C  Cache hit',['hash','cache','sort'],[(.6,9.4)])]:
        ax.text(.25,y+1.0,heading,ha='left',va='center',fontsize=10)
        for x,label in zip([1.8,5.,8.2],labels):box(x,y,label,'#eeeeee' if label in ['wait','cache'] else 'white')
        for x1,x2 in [(2.85,3.95),(6.05,7.15)]:ax.annotate('',xy=(x2,y),xytext=(x1,y),arrowprops={'arrowstyle':'->','lw':.8})
        for a,b in spans:ax.plot([a,a,b,b],[y-.7,y-.9,y-.9,y-.7],color='black',lw=.8)
    fig.subplots_adjust(left=.02,right=.98,top=.98,bottom=.02)
    for ext in ['png','svg']:fig.savefig(FIG/f'effects.{ext}',dpi=350)
    path=FIG/'effects.svg';path.write_text('\n'.join(line.rstrip() for line in path.read_text().splitlines())+'\n')
    plt.close(fig)
    fig,ax=plt.subplots(figsize=(8.7/2.54,6.4/2.54))
    for m,label,style,marker,color in [('effect_neural','Effect neural','-','o','black'),('effect_power','Effect power','--','^','#777777'),('ordered_gru','Ordered GRU','-.','s','black'),('bag_et','Unordered trees',':','D','#555555')]:
        ax.plot([4,6,8],[CHECKS['lengths'][str(n)][m]['mdape'] for n in [4,6,8]],label=label,linestyle=style,marker=marker,color=color,markersize=4,linewidth=1.1)
    ax.set(xlabel='Computation nodes in unseen program',ylabel='MdAPE, %',xticks=[4,6,8],ylim=(0,70));ax.grid(axis='y',alpha=.25);ax.legend(fontsize=10,frameon=False,loc='upper left')
    fig.subplots_adjust(left=.17,bottom=.2,right=.97,top=.97)
    for ext in ['png','svg']:fig.savefig(FIG/f'length.{ext}',dpi=350)
    path=FIG/'length.svg';path.write_text('\n'.join(line.rstrip() for line in path.read_text().splitlines())+'\n')
    plt.close(fig)

def tables(which):
    primary=RESULTS['summary']['asyncio-timer']
    if which=='design':return ('Table 1 Fixed family partitions and program variant counts',['Partition','Work nodes','Families','Variants'],[['Training','2, 3','64','256'],['Validation','2, 3','16','64'],['Short test','2, 3','32','128'],['Long test','4, 6, 8','48','192']],[2.6,2.1,1.9,2.2])
    if which=='accuracy':
        rows=[]
        for m,label in [('sum','Sum'),('largest','Largest'),('syntax','Syntax'),('bag_et','Unordered trees'),('ordered_et','Ordered trees'),('ordered_mlp','Ordered perceptron'),('ordered_gru','Ordered GRU'),('effect_power','Effect power'),('effect_neural','Effect neural')]:
            rows.append([label,f"{primary['short'][m]['mdape']:.1f}",f"{primary['long'][m]['mdape']:.1f}",f"{primary['long'][m]['p90ape']:.1f}"])
        return ('Table 2 Primary test relative errors in percent',['Predictor','Short\nMdAPE','Long\nMdAPE','Long\nP90 APE'],rows,[3.4,1.8,1.8,1.8])
    if which=='ablation':
        rows=[[label]+[f"{CHECKS['variants'][v][m]['mdape']:.1f}" for m in ['effect_power','syntax','largest']] for v,label in [('cluster','Cluster'),('spread','Spread'),('mixed','Mixed'),('cached','Cached')]]
        return ('Table 3 Long-test MdAPE in percent by effect variant',['Variant','Effect\npower','Syntax','Largest'],rows,[2.5,2.1,2.1,2.1])
    if which=='transfer':
        rows=[]
        for m,label in [('effect_power','Effect power'),('effect_neural','Effect neural'),('ordered_gru','Ordered GRU')]:
            rows.append([label]+[f"{RESULTS['summary'][condition][split][m]['mdape']:.1f}" for condition in ['uvloop-timer','uvloop-http'] for split in ['short','long']])
        return ('Table 4 Frozen-prediction transfer MdAPE in percent',['Predictor','Timer\nshort','Timer\nlong','HTTP\nshort','HTTP\nlong'],rows,[2.8,1.5,1.5,1.5,1.5])
    if which=='replay':
        rows=[]
        for m,label in [('inline','Inline'),('all_offload','All offloaded'),('largest','Largest'),('ordered_gru','Ordered GRU'),('effect_neural','Effect neural')]:
            q=CHECKS['replay'][m];rows.append([label,f"{q['offload_pct']:.2f}",f"{q['p90_max_probe_ms']:.2f}",f"{q['median_heavy_ms']:.2f}"])
        return ('Table 5 HTTP replay interference and offloading',['Policy','Offload\n%','Probe P90,\nms','Heavy median,\nms'],rows,[2.8,1.9,2.05,2.05])
    raise ValueError(which)

def nonbreak(t):
    t=re.sub(r'(?<=\d)\s?%', '\u00a0%',t)
    return re.sub(r'(\d) (ms|s|µs|cm|mm|pt|pixels)\b',lambda m:m[1]+'\u00a0'+m[2],t)

def run(p,t,**kwargs):
    r=p.add_run(t)
    for k,v in kwargs.items():setattr(r.font,k,v)
    return r

def inline(p,text):
    for token in re.split(r'(@[^@]+@|max_R|∑_i)',nonbreak(text)):
        if token.startswith('@') and token.endswith('@'):
            value=token[1:-1]
            if '_' in value:
                a,b=value.split('_',1);run(p,a,italic=True);run(p,b,italic=True,subscript=True)
            else:run(p,value,italic=True)
        elif token in ['max_R','∑_i']:
            a,b=token.split('_');run(p,a);run(p,b,italic=True,subscript=True)
        else:run(p,token)

def add_table(d,which):
    caption,head,rows,widths=tables(which);p=d.add_paragraph(caption,'PaperParagraphs');p.paragraph_format.keep_with_next=True
    t=d.add_table(rows=1,cols=len(head));t.autofit=False
    for col,w in zip(t.columns,widths):col.width=Cm(w)
    for index,row in enumerate([head]+rows):
        cells=t.rows[0].cells if index==0 else t.add_row().cells
        for j,(cell,text) in enumerate(zip(cells,row)):
            cell.width=Cm(widths[j]);p=cell.paragraphs[0];p.style=d.styles['PaperParagraphs'];p.paragraph_format.space_before=Pt(2);p.paragraph_format.space_after=Pt(2);p.alignment=WD_ALIGN_PARAGRAPH.LEFT if j==0 else WD_ALIGN_PARAGRAPH.CENTER
            run(p,nonbreak(text),bold=index==0)
            p.paragraph_format.keep_with_next=index<len(rows)
        tr=cells[0]._tc.getparent().get_or_add_trPr();tr.append(OxmlElement('w:cantSplit'))
        if index==0:tr.append(OxmlElement('w:tblHeader'))
    borders=OxmlElement('w:tblBorders')
    for edge in ['top','left','bottom','right','insideH','insideV']:
        el=OxmlElement('w:'+edge);el.set(qn('w:val'),'single' if edge in ['top','bottom'] else 'nil');el.set(qn('w:sz'),'4');el.set(qn('w:color'),'000000');borders.append(el)
    t._tbl.tblPr.append(borders)
    for cell in t.rows[0].cells:
        border=OxmlElement('w:tcBorders');el=OxmlElement('w:bottom');el.set(qn('w:val'),'single');el.set(qn('w:sz'),'4');border.append(el);cell._tc.get_or_add_tcPr().append(border)
    d.add_paragraph(style='PaperParagraphs').paragraph_format.space_after=Pt(2)

def build(authors=False):
    d=Document(BASE.parent/'IET-Template.docx');sec=copy.deepcopy(d.sections[1]._sectPr)
    for el in list(d._element.body):d._element.body.remove(el)
    d._element.body.append(sec)
    for name in ['PaperTitle','PaperAuthor','PaperAffiliations','PaperParagraphs','PaperHeading']:
        st=d.styles[name];st.font.name='Times New Roman';st.font.color.rgb=RGBColor(0,0,0)
    normal=d.styles['PaperParagraphs'];normal.font.size=Pt(10);normal.paragraph_format.space_after=Pt(3);normal.paragraph_format.line_spacing=1;normal.paragraph_format.widow_control=True
    d.styles['PaperTitle'].font.size=Pt(18);d.styles['PaperTitle'].font.bold=True
    d.styles['PaperHeading'].font.size=Pt(12);d.styles['PaperHeading'].font.bold=True
    for s in d.sections:
        s.page_width=Cm(21);s.page_height=Cm(29.7);s.top_margin=Cm(2.54);s.bottom_margin=Cm(2.54);s.left_margin=Cm(1.5);s.right_margin=Cm(1.5);s.gutter=Cm(0)
        cols=s._sectPr.find(qn('w:cols'));cols.set(qn('w:num'),'1');cols.set(qn('w:space'),'227')
        for col in list(cols):cols.remove(col)
    p=d.add_paragraph(TITLE.upper(),'PaperTitle');p.paragraph_format.space_after=Pt(12);p.paragraph_format.keep_with_next=True
    names=['Stanislav Sinyavskiy','Artemiy Letunovskiy','Stanislava Galyuk','Kirill Teplitskiy','Anastasia Sanina','Alexander Babichev']
    if authors:
        p=d.add_paragraph(style='PaperAuthor');p.paragraph_format.space_after=Pt(6)
        for i,n in enumerate(names):run(p,(', ' if i else '')+n);run(p,'1*' if i==0 else '1',superscript=True)
        p=d.add_paragraph(style='PaperAffiliations');p.paragraph_format.space_after=Pt(4);run(p,'1',superscript=True);run(p,'Department of Information Processing and Control Systems, Bauman Moscow State Technical University, Moscow, Russia')
        p=d.add_paragraph('*ssd-tula@mail.ru','PaperAffiliations');p.paragraph_format.space_after=Pt(10)
    p=d.add_paragraph(style='PaperParagraphs');run(p,'Keywords: ',bold=True);run(p,', '.join(KEYWORDS))
    p=d.add_paragraph('Abstract','PaperHeading');p.paragraph_format.space_before=Pt(4);p.paragraph_format.space_after=Pt(6)
    inline(d.add_paragraph(style='PaperParagraphs'),ABSTRACT)
    s=d.add_section(WD_SECTION_START.CONTINUOUS);cols=s._sectPr.find(qn('w:cols'));cols.set(qn('w:num'),'2');cols.set(qn('w:space'),'227');cols.set(qn('w:equalWidth'),'1')
    for col in list(cols):cols.remove(col)
    for typ,text in BLOCKS:
        if typ in ['p','h1','h2']:
            p=d.add_paragraph(style='PaperParagraphs' if typ=='p' else 'PaperHeading');inline(p,text)
            if typ=='h1':p.paragraph_format.space_before=Pt(8);p.paragraph_format.space_after=Pt(6)
            if typ=='h2':
                p.paragraph_format.space_before=Pt(6);p.paragraph_format.space_after=Pt(6)
                for r in p.runs:r.font.size=Pt(10);r.font.bold=False;r.font.italic=True
        elif typ=='equation':
            expression,number=text;p=d.add_paragraph(style='PaperParagraphs');p.paragraph_format.tab_stops.add_tab_stop(Cm(8.7),WD_TAB_ALIGNMENT.RIGHT);inline(p,expression);run(p,'\t('+number+')')
        elif typ=='figure':
            filename,caption=text;p=d.add_paragraph(style='PaperParagraphs');p.alignment=WD_ALIGN_PARAGRAPH.CENTER;p.paragraph_format.space_after=Pt(3);p.paragraph_format.keep_with_next=True;p.add_run().add_picture(str(FIG/filename),width=Cm(8.7));p=d.add_paragraph(nonbreak(caption),'PaperParagraphs');p.paragraph_format.space_after=Pt(8)
        elif typ=='table':add_table(d,text)
    for i,ref in enumerate(REFERENCES,1):
        p=d.add_paragraph(f'[{i}] '+ref,'PaperParagraphs');p.paragraph_format.left_indent=Cm(.55);p.paragraph_format.first_line_indent=Cm(-.55);p.paragraph_format.space_after=Pt(5)
    p=d.sections[0].footer.paragraphs[0];p.clear();p.style=d.styles['PaperParagraphs'];p.paragraph_format.space_after=Pt(0);p.alignment=WD_ALIGN_PARAGRAPH.CENTER
    fld=OxmlElement('w:fldSimple');fld.set(qn('w:instr'),'PAGE');r=OxmlElement('w:r');pr=OxmlElement('w:rPr');font=OxmlElement('w:rFonts');font.set(qn('w:ascii'),'Times New Roman');font.set(qn('w:hAnsi'),'Times New Roman');pr.append(font);sz=OxmlElement('w:sz');sz.set(qn('w:val'),'20');pr.append(sz);r.append(pr);t=OxmlElement('w:t');t.text='1';r.append(t);fld.append(r);p._p.append(fld)
    cp=d.core_properties;cp.title=TITLE;cp.author='; '.join(names) if authors else '';cp.last_modified_by='';cp.subject='CSAI 2026';cp.keywords=', '.join(KEYWORDS);cp.comments='';cp.revision=1
    for rel in list(d.part.rels.values()):
        if 'comments' in rel.reltype:d.part.drop_rel(rel.rId)
    path=OUT/('CSAI2026_Composition_Authors.docx' if authors else 'CSAI2026_Composition_Anonymous.docx');d.save(path)
    # python-docx changes namespace serialisation in these unedited parts.
    # Their expanded-name trees were checked equal; retain reference bytes.
    unchanged={'word/settings.xml','_rels/.rels','word/numbering.xml'}
    with zipfile.ZipFile(path) as z:parts={info.filename:(info,z.read(info.filename)) for info in z.infolist()}
    with zipfile.ZipFile(BASE.parent/'IET-Template.docx') as ref:
        for name in unchanged:parts[name]=(parts[name][0],ref.read(name))
    with zipfile.ZipFile(path,'w') as z:
        for info,data in parts.values():z.writestr(info,data)
    return path

if __name__=='__main__':
    figures()
    for authors in [False,True]:print(build(authors))
    print('Abstract words',len(ABSTRACT.split()),'Body words',sum(len(str(t).split()) for _,t in BLOCKS))

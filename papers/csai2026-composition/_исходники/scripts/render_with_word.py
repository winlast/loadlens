"""Use the packaged render_docx pipeline with native Word and PyMuPDF backends.
The installed Windows runtime does not include LibreOffice or Poppler. This
adapter retains packaged DPI calculation, page naming and rasterisation flow.
"""
from pathlib import Path
import sys,importlib.util,subprocess
BASE=Path(__file__).resolve().parent
sys.path.insert(0,str(BASE/'packages'))
sys.path.insert(0,str(BASE.parents[2]/'_исходники/scripts/packages'))
import pymupdf
SKILL=Path(r'C:/Users/User/.codex/plugins/cache/openai-primary-runtime/documents/26.1112.11217/skills/documents')
spec=importlib.util.spec_from_file_location('packaged_render',SKILL/'render_docx.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
def convert(doc_path,user_profile,convert_tmp_dir,stem,verbose=False):
 pdf=Path(convert_tmp_dir)/(stem+'.pdf')
 r=subprocess.run(['powershell','-NoProfile','-ExecutionPolicy','Bypass','-File',str(BASE/'word_export.ps1'),'-Docx',str(Path(doc_path).resolve()),'-Pdf',str(pdf)],capture_output=True,text=True,encoding='utf8',errors='replace',timeout=90)
 if r.returncode:raise RuntimeError(r.stdout+r.stderr)
 print(r.stdout.strip())
 return str(pdf),'Native Microsoft Word ExportAsFixedFormat'
def raster(pdf_path,dpi,output_folder,**kwargs):
 doc=pymupdf.open(pdf_path);paths=[]
 for i,p in enumerate(doc):
  path=Path(output_folder)/f'page0001-{i+1:02d}.png';p.get_pixmap(matrix=pymupdf.Matrix(dpi/72,dpi/72),alpha=False).save(path);paths.append(str(path))
 return paths
module.convert_to_pdf=convert
module.convert_from_path=raster
if __name__=='__main__':module.main()

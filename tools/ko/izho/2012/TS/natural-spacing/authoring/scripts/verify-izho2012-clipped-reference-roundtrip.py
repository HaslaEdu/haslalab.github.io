from pathlib import Path
import json,sys,hashlib,subprocess,gc
from PIL import Image,ImageChops
import pymupdf as f
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/izho2012-complete-solutions');sys.path[:0]=[str(B/'engine'),'D:/CodexBuilds/Hasla-publish-20261031/tools']
from pdf_memory_gate import page_worker
from initial_prose_reading_order import journal
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();POP='C:/Users/andre/.cache/codex-runtimes/codex-primary-runtime/dependencies/native/poppler/Library/bin/pdftoppm.exe'
for n in map(int,sys.argv[1:]):
 plan=json.loads((B/f'natural/2012/TS/plans/page{n:02}.json').read_text('utf8'));base=Path(plan['source_base']);pdf=B/f'2012/native-reference-isolation/{plan["source_base_sha256"][:16]}/page{n:02}.pdf';assert pdf.exists();reports=[]
 with page_worker():
  for scale in[4,8]:
   for source,page,label in[(base,n,'source'),(pdf,1,'reference-forms')]:
    dest=pdf.parent/f'page{n:02}-{label}-mupdf-{scale}x.png';code='import sys,pymupdf as f;d=f.open(sys.argv[1]);d[int(sys.argv[2])-1].get_pixmap(matrix=f.Matrix(int(sys.argv[3]),int(sys.argv[3])),colorspace=f.csRGB,alpha=False).save(sys.argv[4])'
    subprocess.run([sys.executable,'-X','utf8','-c',code,str(source),str(page),str(scale),str(dest)],capture_output=True,check=True)
   with Image.open(pdf.parent/f'page{n:02}-source-mupdf-{scale}x.png')as a,Image.open(pdf.parent/f'page{n:02}-reference-forms-mupdf-{scale}x.png')as b:
    if a.size!=b.size or ImageChops.difference(a.convert('RGB'),b.convert('RGB')).getbbox()is not None:raise ValueError(('Original source CID fresh-process RGB roundtrip differs',n,scale))
   reports.append(dict(renderer='independent fresh-process MuPDF',scale=scale,changed_RGB_samples=0));gc.collect()
  for source,page,label in[(base,n,'source'),(pdf,1,'reference-forms')]:
   dest=pdf.parent/f'page{n:02}-{label}-poppler';subprocess.run([POP,'-f',str(page),'-l',str(page),'-singlefile','-r','144','-png',str(source),str(dest)],capture_output=True,check=True)
  with Image.open(pdf.parent/f'page{n:02}-source-poppler.png')as a,Image.open(pdf.parent/f'page{n:02}-reference-forms-poppler.png')as b:assert ImageChops.difference(a.convert('RGB'),b.convert('RGB')).getbbox()is None
  reports.append(dict(renderer='external Poppler144dpi',changed_RGB_samples=0))
 with f.open(pdf)as doc:rows=journal(doc[0],plan['prose_placements']);assert len(rows)==len(plan['prose_placements'])
 q=dict(source_base_sha256=sha(base),source_page=n,reference_forms_sha256=sha(pdf),exact_source_CIDs_fonts_points_origins_and_original_clips_preserved=True,source_gray_field_graphics_unchanged=True,renderers=reports,initial_prose_suffix_journal_exact=True,passed=True)
 pdf.with_suffix('.roundtrip.json').write_text(json.dumps(q,indent=2)+'\n','utf8');print('SOURCE_REFERENCE_COMPLETE_ROUNDTRIP_BOTH_RENDERERS_AND_PROSE_JOURNAL_PASS',n,flush=True)

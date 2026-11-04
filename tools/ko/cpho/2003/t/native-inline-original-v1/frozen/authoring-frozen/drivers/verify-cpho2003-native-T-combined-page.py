from pathlib import Path
from collections import Counter
import sys,json,hashlib,subprocess,os
B=Path('C:/Users/andre/CodexWork/HaslaLab/translation-builds/cpho2003-original-native');M=B/'T/master-v1';F=M/'authoring-frozen';sys.path.insert(0,str(F/'engine'));lang=sys.argv[1];n=int(sys.argv[2]);assert lang in ['ko','en']and n in [1,2,3]
from pdf_memory_gate import page_worker
from pdf_native_inline_reposition import _traces
from cpho_natural_full_qa import native_font_programs
from izho_early_fixed_style import native_image_programs
from izho_natural_spacing_qa import semantic
import pymupdf as f,pikepdf
from PIL import Image
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();proof=F/f'natural/2003/{lang}/page{n:02}.pdf';edition=M/f'CPhO_2003_T_{lang.upper()}.pdf';visual=json.loads((F/'authoring/full144-visual-review-complete.json').read_text('utf8'));v=next(p for p in visual['pages']if p['language']==lang and p['source_page']==n);assert v['proof_sha256']==sha(proof)
env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',PYTHONIOENCODING='utf8',OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1')
probe="import sys,json,hashlib,pymupdf as f;d=f.open(sys.argv[1]);p=d[int(sys.argv[2])-1].get_pixmap(matrix=f.Matrix(4,4),colorspace=f.csRGB,alpha=False);print(json.dumps(dict(width=p.width,height=p.height,rgb_sha256=hashlib.sha256(p.samples).hexdigest())))"
def fresh(path,page):return json.loads(subprocess.run([sys.executable,'-X','utf8','-c',probe,str(path),str(page)],env=env,capture_output=True,text=True,check=True).stdout)
def streams(page):
 c=page.Contents;return[s.read_bytes()for s in(c if isinstance(c,pikepdf.Array)else[c])]
with page_worker():
 with pikepdf.open(proof)as a,pikepdf.open(edition)as b:
  assert len(a.pages)==1 and len(b.pages)==3;assert streams(a.pages[0])==streams(b.pages[n-1])
  for key in ['/MediaBox','/CropBox','/Rotate','/Group']:assert semantic(a.pages[0].get(key))==semantic(b.pages[n-1].get(key))
 with f.open(proof)as a,f.open(edition)as b:assert _traces(a[0])==_traces(b[n-1])
 assert Counter(native_font_programs(proof,1))==Counter(native_font_programs(edition,n));assert Counter(native_image_programs(proof,1))==Counter(native_image_programs(edition,n));first=fresh(proof,1);second=fresh(edition,n);assert first==second
 folder=M/f'verification/poppler144/{lang}';folder.mkdir(parents=True,exist_ok=True);stem=folder/f'page{n:02}';png=stem.with_suffix('.png');assert not png.exists();pop=Path('C:/Users/andre/.cache/codex-runtimes/codex-primary-runtime/dependencies/native/poppler/Library/bin/pdftoppm.exe');subprocess.run([str(pop),'-f',str(n),'-l',str(n),'-r','144','-png','-singlefile',str(edition),str(stem)],check=True,capture_output=True)
 reviewed=F/'reviewed-proofs144'/lang/Path(v['png']).name
 with Image.open(reviewed)as a,Image.open(png)as b:
  a=a.convert('RGB');b=b.convert('RGB');assert a.size==b.size and a.tobytes()==b.tobytes();rgb=hashlib.sha256(b.tobytes()).hexdigest()
report=dict(passed=True,language=lang,source_page=n,edition_page=n,edition_sha256=sha(edition),reviewed_proof_sha256=sha(proof),native_page_content_stream_bytes_identical=True,all_native_glyph_traces_and_font_programs_identical=True,all_image_programs_identical=True,fresh_separate_process_MuPDF4x_RGB_difference_pixels=0,MuPDF4x=first,Poppler144_RGB_difference_pixels=0,Poppler144_RGB_sha256=rgb,combined_poppler_png=str(png),combined_poppler_png_sha256=sha(png),reviewed_proof_poppler_png_sha256=v['png_sha256'])
path=M/f'verification/{lang}-page{n:02}.json';assert not path.exists();path.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n','utf8')
modules=[]
for name,module in sorted(sys.modules.items()):
 p=getattr(module,'__file__',None)
 if p and Path(p).is_file()and Path(p).resolve().is_relative_to((F/'engine').resolve()):modules.append(dict(module=name,path=str(Path(p).resolve()),sha256=sha(Path(p)),bytes=Path(p).stat().st_size))
(M/f'verification/{lang}-page{n:02}-loaded-modules.json').write_text(json.dumps(modules,ensure_ascii=False,indent=2)+'\n','utf8');print('CPHO2003_T_NATIVE_APPEND_BOTH_RENDERERS_ZERO_DIFF',lang,n,flush=True)

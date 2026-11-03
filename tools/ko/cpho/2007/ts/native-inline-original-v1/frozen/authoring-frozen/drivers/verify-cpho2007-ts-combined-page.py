from pathlib import Path
from collections import Counter
import sys,json,hashlib,subprocess,os
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/cpho2007/TS');lang=sys.argv[1];n=int(sys.argv[2]);idx=n-4;M=B/'master-v1';F=M/'authoring-frozen';sys.path.insert(0,str(F/'engine'));proof=F/f'natural/2007/{lang}/page{n:02}.pdf';edition=M/f'CPhO_2007_TS_{lang.upper()}.pdf';sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
from pdf_memory_gate import page_worker
import pikepdf,pymupdf as f
from PIL import Image
from pdf_native_inline_reposition import _traces
from cpho_natural_full_qa import native_font_programs
from izho_early_fixed_style import native_image_programs
from izho_natural_spacing_qa import semantic
visual=json.loads((B/'authoring/full144-visual-review-complete.json').read_text('utf8'));v=next(r for r in visual['pages']if r['language']==lang and r['source_page']==n);assert v['proof_sha256']==sha(proof)
env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',PYTHONIOENCODING='utf8',OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1')
probe="import sys,json,hashlib,pymupdf as f;d=f.open(sys.argv[1]);p=d[int(sys.argv[2])-1].get_pixmap(matrix=f.Matrix(4,4),colorspace=f.csRGB,alpha=False);print(json.dumps(dict(width=p.width,height=p.height,rgb_sha256=hashlib.sha256(p.samples).hexdigest())))"
def fresh(path,page):return json.loads(subprocess.run([sys.executable,'-X','utf8','-c',probe,str(path),str(page)],env=env,capture_output=True,text=True,check=True).stdout)
def streams(page):
 c=page.Contents;return[s.read_bytes()for s in(c if isinstance(c,pikepdf.Array)else[c])]
with page_worker():
 with pikepdf.open(proof)as a,pikepdf.open(edition)as b:
  assert len(a.pages)==1 and len(b.pages)==16;pa=a.pages[0];pb=b.pages[idx-1];assert streams(pa)==streams(pb)
  for k in['/MediaBox','/CropBox','/Rotate','/Group']:assert semantic(pa.get(k))==semantic(pb.get(k)),k
 with f.open(proof)as a,f.open(edition)as b:assert _traces(a[0])==_traces(b[idx-1])
 assert Counter(native_font_programs(proof,1))==Counter(native_font_programs(edition,idx));assert Counter(native_image_programs(proof,1))==Counter(native_image_programs(edition,idx))
 first=fresh(proof,1);second=fresh(edition,idx);assert first==second,'Fresh MuPDF4x RGB differs after native append'
 pop=Path('C:/Users/andre/.cache/codex-runtimes/codex-primary-runtime/dependencies/native/poppler/Library/bin/pdftoppm.exe');folder=M/f'verification/poppler144/{lang}';folder.mkdir(parents=True,exist_ok=True);stem=folder/f'page{n:02}';png=stem.with_suffix('.png');assert not png.exists()
 subprocess.run([str(pop),'-f',str(idx),'-l',str(idx),'-r','144','-png','-singlefile',str(edition),str(stem)],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
 reviewed=F/'reviewed-proofs144'/lang/Path(v['png']).name
 with Image.open(reviewed)as a,Image.open(png)as b:
  a=a.convert('RGB');b=b.convert('RGB');assert a.size==b.size and a.tobytes()==b.tobytes(),'Poppler144 RGB differs from reviewed individual proof';rgb=hashlib.sha256(b.tobytes()).hexdigest()
report=dict(passed=True,language=lang,source_page=n,edition_page=idx,edition_sha256=sha(edition),reviewed_proof_sha256=sha(proof),native_page_content_stream_bytes_identical=True,all_native_glyph_traces_and_font_programs_identical=True,all_image_programs_identical=True,fresh_separate_process_MuPDF4x_RGB_difference_pixels=0,MuPDF4x=first,Poppler144_RGB_difference_pixels=0,Poppler144_RGB_sha256=rgb,combined_poppler_png=str(png),combined_poppler_png_sha256=sha(png),reviewed_proof_poppler_png_sha256=v['png_sha256'])
path=M/f'verification/{lang}-page{n:02}.json';path.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n','utf8')
modules=[]
for name,module in sorted(sys.modules.items()):
 file=getattr(module,'__file__',None)
 if file and Path(file).is_file()and(Path(file).resolve().is_relative_to((F/'engine').resolve())):modules.append(dict(module=name,path=str(Path(file).resolve()),sha256=sha(file),bytes=Path(file).stat().st_size))
(M/f'verification/{lang}-page{n:02}-loaded-modules.json').write_text(json.dumps(modules,ensure_ascii=False,indent=2)+'\n','utf8');print('COMBINED_CPHO2007_TS_PAGE_ZERO_DIFF',lang,n,0,0,flush=True)

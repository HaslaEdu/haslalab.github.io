from pathlib import Path
import sys,json,hashlib,shutil,subprocess,os
R=Path('D:/CodexBuilds');B=Path('C:/Users/andre/CodexWork/HaslaLab/translation-builds/cpho2003-original-native');sys.path.insert(0,str(R));from haslalab_runtime_paths import map_repository_path
inventory=R/'Hasla-original-style-20261031/cpho-all-source-coverage-20261102.json';item=next(v for v in json.loads(inventory.read_text('utf8'))['years']if v['year']==2003);source=map_repository_path(item['sources'][0]['path']);sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();assert sha(source)=='52f8a891d6129becf4d21ccb60f46997cedf9aa50123ffd147294cedcb121b63'
for name in['inputs','source-renders-144','authoring','evidence','engine']:(B/name).mkdir(parents=True,exist_ok=True)
target=B/'inputs/CPhO_2003_Chinese_original.pdf'
if target.exists():assert sha(target)==sha(source)
else:shutil.copy2(source,target)
gate=R/'Hasla-original-style-20261031/cpho2007/TS/master-v1/authoring-frozen/engine/pdf_memory_gate.py';copy=B/'engine/pdf_memory_gate.py'
if not copy.exists():shutil.copy2(gate,copy)
assert sha(copy)==sha(gate);sys.path.insert(0,str(B/'engine'));from pdf_memory_gate import page_worker
import pymupdf as f
pop=Path('C:/Users/andre/.cache/codex-runtimes/codex-primary-runtime/dependencies/native/poppler/Library/bin/pdftoppm.exe');assert pop.exists();pages=[]
with f.open(target)as doc:
 assert len(doc)==10
 for n in range(1,11):
  with page_worker():
   page=doc[n-1];text=page.get_text(sort=True);tr=page.get_texttrace();images=page.get_image_info();fonts=page.get_fonts(full=True);drawings=page.get_drawings();plain=B/f'authoring/original-page{n:02}-reading.txt';plain.write_text(text,'utf8')
   png=B/f'source-renders-144/page{n:02}.png'
   if not png.exists():subprocess.run([str(pop),'-f',str(n),'-l',str(n),'-r','144','-png','-singlefile',str(target),str(png.with_suffix(''))],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
   pages.append(dict(source_page=n,page_rect=list(page.rect),text_characters=len(text),physical_trace_characters=sum(len(t['chars'])for t in tr),fonts=fonts,images=images,native_drawing_paths=len(drawings),font_points=sorted({round(t['size'],7)for t in tr}),text_preview=text[:900],png=str(png),png_sha256=sha(png)))
   print('CPHO2003_ORIGINAL_PAGE_READ_RENDER_READY',n,'text',len(text),'traces',sum(len(t['chars'])for t in tr),'fonts',len(fonts),'images',len(images),'paths',len(drawings),flush=True)
(B/'inputs/source-provenance.json').write_text(json.dumps(dict(source_original_path=str(source),historical_inventory_source=item['sources'],source_copy=str(target),source_sha256=sha(target),source_bytes=target.stat().st_size,source_inventory_sha256=sha(inventory),global_gate_sha256=sha(copy),global_gate_lock='D:/CodexBuilds/Hasla-original-style-20261031/pdf-render-memory.lock',all10_pages=pages),ensure_ascii=False,indent=2)+'\n','utf8')
print('ALL10_ORIGINAL_CPHO2003_SOURCE_PAGES_READY',sha(target),flush=True)

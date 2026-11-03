from pathlib import Path
import hashlib,json,sys,shutil,os,subprocess
R=Path('D:/CodexBuilds');D=R/'Hasla-original-style-20261031';B=D/'cpho2007/TS';S=D/'cpho-natural-spacing-v2/2007/authoring-snapshot';P=Path('C:/Users/andre/CodexWork/HaslaLab/haslalab-translation-publish');SOURCE=Path('C:/Users/andre/CodexWork/HaslaLab/haslalab/tmp/source-audit/CPhO_2007_TS.pdf')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();assert sha(SOURCE)=='2e30b56ab9274363686cbf5bc1ef7532dcf579e0703de2c01098b003ab70cdd9'
for sub in ['inputs','engine','source-renders','authoring','native-baseline','natural','proofs','evidence']:(B/sub).mkdir(parents=True,exist_ok=True)
for src,dst in[(SOURCE,B/'inputs/CPhO_2007_Chinese_original.pdf'),(S/'tmp/original-style-repair/2007/slots.json',B/'inputs/original-all20-source-slots.json')]:
 if dst.exists():assert sha(dst)==sha(src)
 else:shutil.copy2(src,dst)
slots=json.loads((B/'inputs/original-all20-source-slots.json').read_text('utf8'));assert slots['source_sha256']==sha(SOURCE)and len(slots['pages'])==20
report=[]
for page in slots['pages']:
 if page['source_page']<5:continue
 n=page['source_page'];(B/f'authoring/page{n:02}-original-source-slots.json').write_text(json.dumps(page,ensure_ascii=False,indent=2)+'\n','utf8')
 lines=[f"PAGE {n}"]
 for row in page['rows']:
  lines.append(f"ROW {row['row']} y={row['baseline']:.5f} | {row['source']}")
  for slot in page['slots']:
   if slot['row']==row['row']:lines.append(f"{slot['id']} | {slot['size']:.5f} | {slot['source_font']} | x={slot['origin'][0]:.4f}..{slot['right']:.4f} | {slot['source']}")
 (B/f'authoring/page{n:02}-source-reading.txt').write_text('\n'.join(lines)+'\n','utf8');report.append(dict(page=n,rows=len(page['rows']),prose_slots=len(page['slots'])))
engine_records=[]
for src in sorted((S/'tools').glob('*.py')):
 dst=B/'engine'/src.name
 if dst.exists():assert sha(src)==sha(dst),(src,dst)
 else:shutil.copy2(src,dst)
 engine_records.append(dict(file=src.name,sha256=sha(dst),copied_from=str(src)))
modern=D/'izho2013-complete-solutions/engine'
for name in ['pdf_native_inline_reposition.py','pdf_text_motion_ink.py','initial_prose_reading_order.py','haslalab_runtime_paths.py']:
 src=modern/name;dst=B/'engine'/name
 if dst.exists()and sha(dst)!=sha(src):
  history=B/'engine/history'/sha(dst)[:16];history.mkdir(parents=True,exist_ok=True);shutil.copy2(dst,history/dst.name)
 shutil.copy2(src,dst)
assert sha(B/'engine/pdf_native_inline_reposition.py')=='ab04f78a8de1845269742c3e95828c635ee5b3d5bd957d226577390bfe25279f'
(B/'inputs/source-and-engine-provenance.json').write_text(json.dumps(dict(source=str(SOURCE),source_sha256=sha(SOURCE),source_physical_pages=list(range(5,21)),original_blank_last_page20_is_preserved=True,extraction_is_frozen_original_all20_slots=True,original_source_selection_notes='This is a native digital PDF, not a scanned page compositor. Chinese prose selection is explicit in the frozen original source-slot extraction; all mathematical CIDs/fonts/points/figures/vectors remain native.',page_inventory=report,initial_engine_records=engine_records,shared_native_guard_sha256=sha(B/'engine/pdf_native_inline_reposition.py')),ensure_ascii=False,indent=2)+'\n','utf8')
print('CPHO2007_TS_SOURCE_SLOTS_READY',report,flush=True)
env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',PYTHONIOENCODING='utf8',OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1')
poppler=Path('C:/Users/andre/.cache/codex-runtimes/codex-primary-runtime/dependencies/native/poppler/Library/bin/pdftoppm.exe')
for n in range(5,21):
 target=B/f'source-renders/page{n:02}.png'
 if target.exists():continue
 code=f"import sys,subprocess;sys.path.insert(0,{str(B/'engine')!r});from pdf_memory_gate import page_worker\nwith page_worker():subprocess.run([{str(poppler)!r},'-f',{str(n)!r},'-l',{str(n)!r},'-r','144','-singlefile','-png',{str(B/'inputs/CPhO_2007_Chinese_original.pdf')!r},{str(target.with_suffix(''))!r}],check=True,capture_output=True,creationflags=0x08000000)"
 subprocess.run([sys.executable,'-u','-X','utf8','-c',code],env=env,check=True,cwd=P);assert target.exists();print('CPHO2007_TS_SOURCE144DPI_READY',n,flush=True)
print('ALL16_CPHO2007_TS_ORIGINAL_PAGES_READY_FOR_FULL_VISUAL_READING',flush=True)

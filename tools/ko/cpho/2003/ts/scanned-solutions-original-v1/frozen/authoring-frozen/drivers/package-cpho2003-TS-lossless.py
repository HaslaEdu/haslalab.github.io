"""Lossless PDF packaging only; every decoded native program remains identical."""
from pathlib import Path
from collections import Counter
import sys,json,hashlib,os,shutil
B=Path('C:/Users/andre/CodexWork/HaslaLab/translation-builds/cpho2003-original-native');T=B/'TS';M=T/'master-v1';F=M/'authoring-frozen'
sys.path[:0]=[str(F/'engine-ts'),str(F/'engine-base'),'D:/CodexBuilds']
from pdf_memory_gate import page_worker
from cpho_natural_full_qa import native_font_programs
from izho_early_fixed_style import native_image_programs
from izho_natural_spacing_qa import semantic
from pdf_native_inline_reposition import _traces
import pikepdf,pymupdf as f
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def streams(page):
 c=page.Contents;return[s.read_bytes()for s in(c if isinstance(c,pikepdf.Array)else[c])]
assert not(M/'READY.json').exists()
out=T/'packaging-candidates';out.mkdir(exist_ok=True)
editions=json.loads((M/'edition-candidates.json').read_text('utf8'));records=[]
for e in editions:
 with page_worker():
  old=Path(e['path']);target=out/old.name;assert sha(old)==e['sha256']and not target.exists()
  with pikepdf.open(old)as p:p.save(target,compress_streams=True,object_stream_mode=pikepdf.ObjectStreamMode.generate,recompress_flate=False)
  with pikepdf.open(old)as a,pikepdf.open(target)as b:
   assert len(a.pages)==len(b.pages)==7
   for aa,bb in zip(a.pages,b.pages):
    assert streams(aa)==streams(bb)
    for key in ['/MediaBox','/CropBox','/Rotate','/Group']:assert semantic(aa.get(key))==semantic(bb.get(key))
  with f.open(old)as a,f.open(target)as b:
   for aa,bb in zip(a,b):assert _traces(aa)==_traces(bb)
  for n in range(1,8):
   assert Counter(native_font_programs(old,n))==Counter(native_font_programs(target,n))
   assert Counter(native_image_programs(old,n))==Counter(native_image_programs(target,n))
  assert target.stat().st_size<25*1024**2
  records.append(dict(language=e['language'],original_sha256=sha(old),original_bytes=old.stat().st_size,packaged_sha256=sha(target),packaged_bytes=target.stat().st_size,all7_decoded_page_programs_font_names_ToUnicode_glyph_traces_encoded_image_programs_and_page_groups_identical=True))
  print('LOSSLESS_NATIVE_PROGRAM_PACKAGING',e['language'],old.stat().st_size,target.stat().st_size,sha(target),flush=True)
# Preserve the uncompressed editions and their completed assembly checks.
h=M/'packaging-history/uncompressed';assert not h.exists();h.mkdir(parents=True)
for e in editions:
 old=Path(e['path']);dest=h/old.name;assert old.resolve().is_relative_to(M.resolve())and dest.resolve().is_relative_to(M.resolve());old.replace(dest)
old=M/'edition-candidates.json';dest=h/old.name;assert old.resolve().is_relative_to(M.resolve())and dest.resolve().is_relative_to(M.resolve());old.replace(dest)
old=M/'verification';dest=h/'verification';assert old.resolve().is_relative_to(M.resolve())and dest.resolve().is_relative_to(M.resolve());old.replace(dest)
for e,r in zip(editions,records):
 target=M/Path(e['path']).name;os.link(out/target.name,target);e.update(sha256=r['packaged_sha256'],bytes=r['packaged_bytes'],method=e['method']+' Lossless stream/object-table packaging; all decoded native page/font/glyph programs and exact encoded images unchanged.')
(M/'edition-candidates.json').write_text(json.dumps(editions,ensure_ascii=False,indent=2)+'\n','utf8')
(M/'lossless-packaging.json').write_text(json.dumps(dict(passed=True,source_original_sha256='52f8a891d6129becf4d21ccb60f46997cedf9aa50123ffd147294cedcb121b63',no_refonting_retypesetting_reflow_resampling_or_point_fitting=True,original_uncompressed_editions_and_all_prior_positive_checks_preserved=True,all14_fresh_both_renderer_checks_required_before_READY=True,editions=records),indent=2)+'\n','utf8')
driver=Path(__file__);dest=F/'drivers'/driver.name;assert not dest.exists();shutil.copy2(driver,dest);assert sha(driver)==sha(dest)

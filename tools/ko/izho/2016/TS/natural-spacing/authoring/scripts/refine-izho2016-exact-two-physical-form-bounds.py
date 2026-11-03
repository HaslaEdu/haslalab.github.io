from pathlib import Path
import json,hashlib,sys,pymupdf as f
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/izho2016-complete-solutions');sys.path[:0]=[str(B/'engine'),'D:/CodexBuilds/Hasla-publish-20261031/tools']
from pdf_memory_gate import page_worker
from pdf_native_inline_reposition import _traces,inspect_inline_groups
from pdf_original_text_ops import glyph_key
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
for n in map(int,sys.argv[1:]):
 assert n in[2,5];path=B/f'natural/2016/TS/plans/page{n:02}.json';p=json.loads(path.read_text('utf8'));history=path.parent/'history'/sha(path);history.mkdir(parents=True,exist_ok=True);(history/path.name).write_bytes(path.read_bytes())
 y,rect=(704.02,[191,692,208,707])if n==2 else(268.25,[195,247,310,283])
 with page_worker():
  with f.open(p['original_english_source'])as doc:gs=[g for g in _traces(doc[n-1])if g['c'].strip()and f.Rect(rect).contains(f.Point(g['origin']))]
  inv=inspect_inline_groups(p['source_base'],n)
 wanted={glyph_key(g)for g in gs};matches=[v for v in inv['forms']if {glyph_key(g)for g in v['glyphs']if g['c'].strip()}==wanted];assert len(matches)==1,(n,rect,len(matches));v=matches[0]
 atoms=[a for a in p['explicit_native_math_atoms']if abs(a['baseline']-y)<.01];assert len(atoms)==1;a=atoms[0];a.update(rect=rect,source_native_glyphs=gs,source_form_path=v['path'],source_form_bbox=v['native_page_bbox'])
 p.setdefault('reviewed_complete_original_mathematical_form_bindings',[]).append(dict(rect=rect,path=v['path'],original_form_bbox=v['native_page_bbox'],original_form_program_sha256=v['original_raw_sha256'],complete_native_glyph_set=True,reason='Original full source144dpi and native Form inventory reviewed: exact physical expression bounds include its leading2 on page5 and exclude the next display superscript2 on page2. All original CID/points/Y and internal rule programs retained; one whole native Form invocation moves.'))
 path.write_text(json.dumps(p,ensure_ascii=False,indent=2)+'\n','utf8');print('IZHO2016_EXACT_PHYSICAL_FORM_BOUNDS_REVIEWED',n,v['path'],len(gs),flush=True)

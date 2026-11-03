from pathlib import Path
import json,hashlib,sys,pymupdf as f
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/izho2016-complete-solutions');E=B/'engine';sys.path[:0]=[str(E),'D:/CodexBuilds/Hasla-publish-20261031/tools'];SOURCE='19f23f790b5dd43bf2303f4b597da862c5d17a0267320fee3cca7f5f015a1df8';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
from pdf_native_inline_reposition import _traces,inspect_inline_groups
from pdf_original_text_ops import glyph_key
from pdf_memory_gate import page_worker
engine=E/'izho_natural_spacing_rebuild.py';text=engine.read_text('utf8')
if 'source_complete_clip_operator_indices'not in text:
 history=E/'history'/sha(engine);history.mkdir(parents=True,exist_ok=True);(history/engine.name).write_bytes(engine.read_bytes())
 for needle,var in[("                if len(complete_source_clip)!=1:raise ValueError('An original glyph origin outside its reviewed rectangle needs the exact complete original clipped CID group')",'complete_source_clip'),("                if len(matches)!=1:raise ValueError('Reviewed native fraction must identify one complete original clip containing all its original rules')",'matches')]:
  indent=needle[:len(needle)-len(needle.lstrip())];insert=indent+"if rule.get('source_complete_clip_operator_indices')is not None:\n"+indent+"    if d['original_english_source_sha256']!="+repr(SOURCE)+":raise ValueError('Unexpected source-specific complete clip program')\n"+indent+"    "+var+"=[c for c in "+var+" if c['operator_indices']==rule['source_complete_clip_operator_indices']]\n";assert needle in text;text=text.replace(needle,insert+needle)
 engine.write_text(text,'utf8')
for n in map(int,sys.argv[1:]):
 path=B/f'natural/2016/TS/plans/page{n:02}.json';p=json.loads(path.read_text('utf8'));assert p['original_english_source_sha256']==SOURCE;history=path.parent/'history'/sha(path);history.mkdir(parents=True,exist_ok=True);(history/path.name).write_bytes(path.read_bytes())
 with page_worker():
  with f.open(p['original_english_source'])as doc:original=_traces(doc[n-1])
  inv=inspect_inline_groups(p['source_base'],n)
 if n==4:
  rect=[186,724,350,760];a=next(a for a in p['explicit_native_math_atoms']if abs(a['baseline']-741.7)<.02);gs=[g for g in original if g['c'].strip()and f.Rect(rect).contains(f.Point(g['origin']))];wanted={glyph_key(g)for g in gs};forms=[v for v in inv['forms']if{glyph_key(g)for g in v['glyphs']if g['c'].strip()}==wanted];assert len(forms)==1;v=forms[0]
  a.update(rect=rect,source_native_glyphs=gs,source_form_path=v['path'],source_form_bbox=v['native_page_bbox']);p.setdefault('reviewed_complete_original_mathematical_form_bindings',[]).append(dict(rect=rect,path=v['path'],original_form_bbox=v['native_page_bbox'],original_form_program_sha256=v['original_raw_sha256'],complete_native_glyph_set=True,reason='Full original formula10 includes leading sigma0 cos(theta), not only the r/fraction suffix. Entire original Form and all scripts/rules move by one dx.'))
 elif n==7:
  clips=[c for c in inv['clip_groups']if c.get('known_rectangular_clips')and len(c['clip_rects'])==1 and 670<c['clip_rects'][0][1]<672 and 684<c['clip_rects'][0][3]<686];assert clips;v=min(clips,key=lambda c:c['operator_indices'][0]);gs=[g for g in v['glyphs']if g['c'].strip()];wanted={glyph_key(g)for g in gs};assert len(gs)>10
  a=next(a for a in p['explicit_native_math_atoms']if abs(a['baseline']-682.18)<.02);a.update(rect=v['clip_rects'][0],source_native_glyphs=gs,use_complete_original_clip=True,source_complete_clip_operator_indices=v['operator_indices']);a.pop('source_form_path',None);a.pop('source_form_bbox',None);a['reason']='Original2016 page7 rubric equation3: complete original outer Word row clip, original native reference(3) plus q=CU0=0.50muCl, all source CIDs/scripts and any original paths share one dx. Korean label remains outside the original clip. Exact outer source clip indices resolve duplicated tight row ancestors without any guard or numeric tolerance change.'
  p['reviewed_complete_original_mathematical_form_bindings']=[b for b in p.get('reviewed_complete_original_mathematical_form_bindings',[])if b.get('rect')!=[180,670,288,695]]
 elif n==8:
  a=next(a for a in p['explicit_native_math_atoms']if abs(a['baseline']-352.37)<.02);rect=[305,346,387,365];a.update(rect=rect,source_native_glyphs=[g for g in original if g['c'].strip()and f.Rect(rect).contains(f.Point(g['origin']))]);assert len(a['source_native_glyphs'])>5
 else:raise ValueError(n)
 path.write_text(json.dumps(p,ensure_ascii=False,indent=2)+'\n','utf8');print('IZHO2016_SOURCE_EXACT_FORM_OR_CLIP_BOUND',n,flush=True)
assert sha(E/'pdf_native_inline_reposition.py')=='ab04f78a8de1845269742c3e95828c635ee5b3d5bd957d226577390bfe25279f'

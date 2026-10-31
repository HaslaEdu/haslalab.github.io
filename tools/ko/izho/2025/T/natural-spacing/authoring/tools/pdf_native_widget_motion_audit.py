"""Read-only relative-dx audit of complete original tight mathematical clips."""
from pathlib import Path
import json
from collections import defaultdict
import pymupdf as fitz
from pdf_native_inline_reposition import inspect_inline_groups,_traces
from pdf_original_text_ops import glyph_key

def audit_plan(path):
    path=Path(path);p=json.loads(path.read_text(encoding='utf8'));q=json.loads((path.parents[1]/f"page{p['page']:02}.qa.json").read_text(encoding='utf8'))
    with fitz.open(p['original_english_source'])as doc:
        physical={(glyph_key(g),g['trace_gid'])for g in _traces(doc[p['source_page']-1])if g['c'].strip()and g['trace_gid']>=0}
    offsets=defaultdict(list)
    for s in q['native_shifts']:
        for g in s['glyphs']:offsets[glyph_key(g)].append(s['dx'])
    groups=[]
    for item in inspect_inline_groups(p['source_base'],p['page'])['clip_groups']:
        clips=item.get('clip_rects',[])
        if not item.get('known_rectangular_clips')or not any(fitz.Rect(r).width<160 and fitz.Rect(r).height<50 for r in clips):continue
        gs=[g for g in item['glyphs']if g['c'].strip()and g['trace_gid']>=0 and(glyph_key(g),g['trace_gid'])in physical]
        if len(gs)<2:continue
        dx=[offsets.get(glyph_key(g),[0.])[0]for g in gs];spread=max(dx)-min(dx)
        groups.append(dict(source_clip_rects=clips,glyphs=[{k:g[k]for k in('c','font','size','origin','trace_gid')}for g in gs],dx=dx,relative_dx_spread_pt=spread,passed=spread<=.001))
    return dict(year=p['year'],kind=p['kind'],page=p['page'],original_source_sha256=p['original_english_source_sha256'],recorded_proof_sha256=q['output_sha256'],groups=groups,nonrigid_candidate_groups=sum(not g['passed']for g in groups),read_only=True)

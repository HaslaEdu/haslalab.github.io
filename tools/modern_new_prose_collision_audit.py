"""Independent read-only new Batang prose/native text and graphics collision audit."""
from pathlib import Path
import json,hashlib
import pymupdf as fitz
from pdf_native_inline_reposition import _traces
from pdf_original_text_ops import glyph_key
from pdf_new_prose_native_text_overlap import audit as text_overlap
from pdf_new_hangul_graphics_overlap import audit as graphics_overlap

def audit_plan(plan_path,proof_path=None,composition_path=None):
    plan_path=Path(plan_path);plan=json.loads(plan_path.read_text(encoding='utf8'))
    folder=plan_path.parents[1];n=plan['page'];proof=Path(proof_path)if proof_path else folder/f'page{n:02}.pdf'
    comp=Path(composition_path)if composition_path else proof.with_suffix('.qa.json');q=json.loads(comp.read_text(encoding='utf8'))
    with fitz.open(plan['original_english_source'])as original,fitz.open(plan['source_base'])as old,fitz.open(proof)as final:
        keys={(glyph_key(g),g['trace_gid'],g['render_mode'])for g in _traces(original[plan['source_page']-1])if g['c'].strip()and g['trace_gid']>=0 and g['render_mode']!=3}
        native=[g for g in _traces(old[n-1])if(glyph_key(g),g['trace_gid'],g['render_mode'])in keys and g['trace_gid']>=0 and g['c'].strip()]
        prose=[g for g in _traces(final[0])if g['font']=='Batang'and g['c'].strip()and g['trace_gid']>=0]
    text=text_overlap(proof,native_glyphs=native,shifts=q['native_shifts'],prose_glyphs=prose)
    graph=graphics_overlap(proof,new_glyphs=prose)
    result=dict(year=plan['year'],kind=plan['kind'],page=n,original_source_sha256=plan['original_english_source_sha256'],input_sha256=plan['source_base_sha256'],final_sha256=hashlib.sha256(proof.read_bytes()).hexdigest(),
        native_text_overlap=text,native_graphics_overlap=graph,passed=text['passed']and graph['passed'],read_only=True)
    proof.with_suffix('.prose-collision.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8')
    return result

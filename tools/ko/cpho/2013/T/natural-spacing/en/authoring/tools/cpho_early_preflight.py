"""Read-only collect every fixed-size line overflow before PDF rendering."""
import json
from pathlib import Path
from io import BytesIO
from fontTools.ttLib import TTFont
import pymupdf as fitz
import pdf_korean_natural_composer as composer
from izho_natural_spacing import baseline_lines,boundary_gap,inject_atomic_tokens
from izho_native_atomic_tokens import atomic_tokens
from pdf_original_text_ops import glyph_key
from cpho_natural_atoms import explicit_atoms,explicit_form_atoms

def check(spec):
    font=TTFont(composer.BATANG,fontNumber=0,recalcTimestamp=False);b=BytesIO();font.save(b);metric=fitz.Font(fontbuffer=b.getvalue())
    explicit=explicit_atoms(spec)+explicit_form_atoms(spec);out=[]
    predicate=None
    if spec['language']=='en':
        from cpho_natural_spacing import native_records
        original={glyph_key(g)for g in native_records(spec['year'],spec['page'],spec['input'],spec['input_page'])}
        predicate=lambda rs:any(g['c'].strip()and glyph_key(g)not in original for g in rs)
    with fitz.open(spec['input'])as doc:
        page=doc[spec['input_page']-1];ps=spec['prose_placements']
        for r in spec['regions']:
            rect=r['rect'];lines=baseline_lines(page,allowed_line_rects=[rect],excluded_figure_rects=spec['excluded_figure_rects'],prose_placements=ps,prose_trace_predicate=predicate)
            atoms=atomic_tokens(spec['input'],spec['input_page'],rect,[dict(baseline=l['baseline'],size=max(t['size']for t in l['tokens']))for l in lines],spec['excluded_figure_rects'])
            chosen=[a for a in explicit if rect[0]-1<=a['x0']and a['x1']<=rect[2]+1 and rect[1]<=a['y']<=rect[3]]
            keys={glyph_key(g)for a in chosen for g in a['glyphs']};atoms=[a for a in atoms if not any(glyph_key(g)in keys for g in a['glyphs'])]+chosen
            lines=inject_atomic_tokens(lines,atoms)
            for l in lines:
                ts=l['tokens'];start=cursor=ts[0]['x0']
                for i,t in enumerate(ts):
                    if i:cursor+=boundary_gap(ts[i-1],t)
                    cursor+=sum(u['width']for u in composer._units(t,ps,metric))
                c=[x['center']for x in spec['centered_lines']if abs(x['baseline']-l['baseline'])<.02]
                rights=[x['right']for x in spec.get('right_aligned_lines',[])if abs(x['baseline']-l['baseline'])<.02]
                adjust=c[0]-(start+cursor)/2 if c else rights[0]-cursor if rights else 0
                if cursor+adjust>rect[2]+.1 or start+adjust<rect[0]-.1:
                    out.append(dict(baseline=l['baseline'],over=cursor+adjust-rect[2],left=start+adjust,rect=rect,tokens=[t['text']for t in ts],placement_ids=[ps[t['placement']]['id']for t in ts if'placement'in t]))
    return out
if __name__=='__main__':
    import sys
    import cpho_early_natural as a
    a.install();s=json.loads(Path(sys.argv[1]).read_text('utf8'));print(json.dumps(check(s),ensure_ascii=False,indent=2))

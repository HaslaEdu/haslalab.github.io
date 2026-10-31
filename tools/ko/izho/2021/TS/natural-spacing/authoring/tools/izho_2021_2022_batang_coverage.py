"""Read-only coverage of eligible regular-serif Korean body replacement."""
import argparse,json
from pathlib import Path
import pymupdf as fitz
from izho_2021_2022_natural_spacing import OUT,sha
from pdf_korean_natural_composer import records,normalize_placements,_replace
from pdf_original_text_ops import glyph_key

def audit(year,kind,page_number):
    path=OUT/str(year)/kind/f'batang-page{page_number}.qa.json'
    qa=json.loads(path.read_text('utf8'))
    spec=json.loads(path.with_name(f'batang-page{page_number}.plan.json').read_text('utf8'))
    source=Path(qa['source'])
    oldqa=json.loads(source.with_suffix('.qa.json').read_text('utf8'))
    erased={glyph_key(g)for g in qa['composition']['erased_hangul_glyphs']}
    excluded=[fitz.Rect(r)for r in spec['excluded_figure_rects']]
    eligible=[];missing=[];ambiguous=[]
    with fitz.open(source)as doc:
        placements=normalize_placements(doc[0],oldqa['placements'])
        for row in records(doc[0]):
            if row['origin'][1]<=60 or not('NotoSerif'in row['font']and 'Regular'in row['font']):continue
            if not(len(row['c'])==1 and 0xac00<=ord(row['c'])<=0xd7a3):continue
            if any(r.intersects(fitz.Rect(row['bbox']))for r in excluded):continue
            candidates=[p for p in placements if p.get('point')and p.get('width')is not None
                and abs(p['point'][1]-row['origin'][1])<.025
                and p['point'][0]-.04<=row['origin'][0]<p['point'][0]+p['width']+.04]
            decisions={_replace(row,p)for p in candidates}if candidates else{_replace(row,None)}
            if len(decisions)>1:
                ambiguous.append(dict(c=row['c'],origin=row['origin'],candidates=candidates));continue
            if decisions!={True}:continue
            eligible.append(row)
            if glyph_key(row)not in erased:
                missing.append({k:row[k]for k in('c','font','size','origin','bbox')})
    return dict(source=str(source),source_sha256=sha(source),proof_sha256=qa['output_sha256'],
        eligible_regular_body_hangul=len(eligible),covered_regular_body_hangul=len(eligible)-len(missing),
        missing_eligible_body_hangul=missing,ambiguous_style_classifications=ambiguous,
        figures_excluded=spec['excluded_figure_rects'],
        method='All actual source regular-serif Hangul body glyphs outside reviewed figure bounds, with original placement italic-role exclusions, must occur exactly in the erasure journal.',
        passed=not missing and not ambiguous)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('year',type=int);p.add_argument('kind');p.add_argument('page',type=int);a=p.parse_args()
    q=audit(a.year,a.kind,a.page)
    target=OUT/str(a.year)/a.kind/f'batang-page{a.page}.coverage.json'
    target.write_text(json.dumps(q,ensure_ascii=False,indent=2),'utf8')
    print(json.dumps(q,ensure_ascii=False,indent=2))
    if not q['passed']:raise SystemExit(1)

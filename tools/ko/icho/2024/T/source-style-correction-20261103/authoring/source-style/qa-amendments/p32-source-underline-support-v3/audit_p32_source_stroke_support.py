"""P32-only external QA: exact original underline support, unchanged .5pt pad."""
from pathlib import Path
import hashlib
import json
import math
import sys
sys.dont_write_bytecode = True
A = Path(__file__).resolve().parent
O = A.parents[1]
R = O / 'revisions/final62-v3'
F = O / 'final/2024-v3'
sys.path.insert(0, str(R / 'working/authoring'))
import natural_plan_compose_icho2024_style as c
import verify_pixel_and_KK_icho2024 as old_pixel
import pymupdf as fitz
import pikepdf
import numpy as np

SOURCE = '959174ab5ddc8be71c251c8fe95a12c810ba730edbcbbef3b771197e32929a4a'
GOOD = '295d4bcd98d367c2cc0a140ba5d824fdf3345407500b03a127e04d1d2b159219'
LAYOUT = '1b5cdf8f40e8774344d024a5ccdbde997137be37a0f18027000619cfc2971eea'
MAP = 'ad5990b8ceb44b2dabbfc7a53ce8c344907d4b5b243f58e4e7cd88fba0dfde8a'
PROGRAM = '8756e7deb5c4dd9e6d470d9fc562f58398996bc4a34371ebcd759b4da9be9477'
SOURCE_CONTENT = 'df64f3e667006792f7486b2818d2fdd62d64ea99881d8b45a50797c9fd444643'


def sha(p):
    with Path(p).open('rb') as h:
        return hashlib.file_digest(h, 'sha256').hexdigest()


def read(p):
    return json.loads(Path(p).read_text('utf8'))


def contents(page):
    streams = list(page.Contents) if isinstance(page.Contents, pikepdf.Array) else [page.Contents]
    return b'\n'.join(s.read_bytes() for s in streams)


def visible(page):
    return [dict(c=chr(cp),gid=gid,font=t['font'],size=t['size'],origin=list(origin),bbox=list(box),
        paint=t['type'],direction=list(t['dir']),color=list(t['color']),opacity=t['opacity'])
        for t in page.get_texttrace() if t['type'] != 3 for cp,gid,origin,box in t['chars'] if chr(cp).strip()]


def draw_match(drawing, expected):
    return list(drawing['rect']) == expected['rect'] and drawing['width'] == expected['width'] \
        and drawing['type'] == expected['type'] and list(drawing['color']) == expected['color'] \
        and drawing['fill'] is None and tuple(drawing['lineCap']) == tuple(expected['lineCap']) \
        and drawing['lineJoin'] == expected['lineJoin']


def audit(candidate, layout=None):
    candidate = Path(candidate).resolve()
    lp = Path(layout).resolve() if layout else candidate.with_suffix('.layout.json')
    assert candidate.name == 'page32.pdf'
    assert candidate == (F/'page32.pdf').resolve() or candidate.is_relative_to(A)
    q = read(lp)
    assert q['page'] == 32 and q['source_sha256'] == SOURCE
    assert sha(candidate) == q['output_sha256']
    good = F/'page32.pdf'; original_layout = F/'page32.layout.json'
    assert sha(good) == GOOD and sha(original_layout) == LAYOUT
    certified_q = read(original_layout)
    assert {k:v for k,v in q.items() if k != 'output_sha256'} == {k:v for k,v in certified_q.items() if k != 'output_sha256'}, 'Certified layout changed beyond output_sha256'
    assert q['composer_sha256'] == '1218ee97ff057bb171c0185f103e913976162bada32dc3b9ec48266050e88982'
    mapping = O/'semantic-underline-mapping-68-v2.json'
    assert sha(mapping) == MAP
    m = read(mapping)
    reviewed = next(v for v in m['rows'] if v['inventory_index'] == 34)
    assert reviewed['page'] == 32 and reviewed['source_English'] == 'Some hints' and reviewed['target_literal'] == '몇 가지 단서'
    spec = next(v for v in q['prose_vector_decorations'] if v.get('semantic_mapping_index') == 34)
    assert spec['source_program'] == reviewed['source_prose_decoration_program']
    program = spec['source_program']; fragment = program['source_construction_and_paint_fragment_latin1'].encode('latin1')
    assert hashlib.sha256(fragment).hexdigest() == PROGRAM
    assert program['source_operator_indices'] == [392,393,394] and program['source_operator_names'] == ['m','l','S']
    assert spec['source_rect'] == [56.693,664.5410146484376,108.963,664.5410146484376]
    expected_drawing = program['source_drawing']
    assert expected_drawing['width'] == .398499995470047 and expected_drawing['color'] == [0,0,0]
    assert expected_drawing['lineCap'] == [0,0,0] and expected_drawing['lineJoin'] == 0
    source_path = O/'frozen/source/IChO_2024_T_EN.pdf'
    assert sha(source_path) == SOURCE
    with pikepdf.open(source_path) as source, pikepdf.open(candidate) as target:
        raw = contents(source.pages[31])
        assert hashlib.sha256(raw).hexdigest() == SOURCE_CONTENT and raw.count(fragment) == 1
        ops = pikepdf.parse_content_stream(source.pages[31])
        assert [str(ops[i].operator) for i in [392,393,394]] == ['m','l','S']
        assert contents(target.pages[0]).count(fragment) == 1, 'Original source underline construction bytes missing or replaced'
    oldq = read(O/'frozen/publication/page32.qa.json')
    assert not any(abs(v['source_baseline']-663.0490112304688)<.001 for v in oldq['prose_vector_decorations'])
    approved = read(R/'approved-translation-manifest.json')
    edits = {k for k,v in approved['edits'].items() if v['page'] == 32}
    changed_y = {p['baseline'] for z in [q,oldq] for p in z['placements'] if p.get('original_source_slot_id',p['id']) in edits}
    baselines = sorted({r['source_guard']['source_prose_baseline'] for r in m['rows'] if r['page'] == 32}
        | {r['baseline'] for r in m['new_Korean_italic_placements'] if r['page'] == 32} | changed_y)
    assert baselines == [486.906982421875,663.0490112304688]
    rects = []
    for y in baselines:
        lines = [v for z in [q,oldq] for v in z['line_reports'] if abs(v['baseline']-y)<.001]
        x0=min(v['left'] for v in lines);x1=max(v['right'] for v in lines)
        y0=min(v['source_bounds'][1] for v in lines);y1=max(v['source_bounds'][3] for v in lines)
        for z in [q,oldq]:
            for dec in z['prose_vector_decorations']:
                if abs(dec['source_baseline']-y)<.001:
                    rr=dec.get('target_rect',[v+(dec['dx'] if i%2==0 else 0) for i,v in enumerate(dec['source_rect'])])
                    x0=min(x0,rr[0]);x1=max(x1,rr[2]);y0=min(y0,rr[1]-.3);y1=max(y1,rr[3]+.3)
        rects.append([x0-.5,y0-.5,x1+.5,y1+.5])
    # Butt-cap horizontal stroke: no longitudinal expansion. Only the real
    # half-width in y, and exactly the frozen .5pt anti-alias support in x/y.
    sr = spec['source_rect']; half = expected_drawing['width']/2
    source_support = [sr[0]-.5,sr[1]-half-.5,sr[2]+.5,sr[3]+half+.5]
    samples = []
    with fitz.open(source_path) as source, fitz.open(O/'frozen/reference-proofs/page32.pdf') as old, fitz.open(candidate) as new, fitz.open(good) as certified:
        sp, op, npg, gp = source[31],old[0],new[0],certified[0]
        assert any(draw_match(d,expected_drawing) for d in sp.get_drawings())
        assert any(draw_match(d,expected_drawing) for d in op.get_drawings()), 'P0 does not contain the reviewed original source stroke'
        # Every current visible source/native/KO glyph is independently compared
        # to the immutable proof that already passed full-font GID/curve/native QA.
        actual, certified_glyphs = visible(npg),visible(gp)
        assert actual == certified_glyphs, 'Actual visible glyph geometry differs from audited immutable p32 proof'
        assert c.original_helpers.font_programs(source,sp) <= c.original_helpers.font_programs(new,npg)
        assert c.original_helpers.font_programs(certified,gp) == c.original_helpers.font_programs(new,npg)
        assert c.original_helpers.encoded_images(source,sp) == c.original_helpers.encoded_images(new,npg)
        assert c.original_helpers.native_images(sp) == c.original_helpers.native_images(npg)
        actual_paths = c.motion.inspect_inline_groups(candidate.read_bytes(),1)['vector_paths']
        u = actual_paths[spec['source_path_index']]['rect']
        assert max(abs(u[i]-spec['target_rect'][i]) for i in [0,2]) <= .001
        assert abs(u[1]-sr[1]) <= 1e-7 and abs(u[3]-sr[3]) <= 1e-7
        assert actual_paths[spec['source_path_index']]['paint_operator'] == 'S'
        for fraction in [.1,.25,.5,.75,.9]:
            columns=[]
            for pg,r in [(sp,sr),(npg,u)]:
                x=r[0]+fraction*(r[2]-r[0]);y=r[1]
                pm=pg.get_pixmap(matrix=fitz.Matrix(32,32),clip=fitz.Rect(x-.125,y-.35,x+.125,y+.35),colorspace=fitz.csGRAY,alpha=False)
                arr=np.frombuffer(pm.samples,np.uint8).reshape(pm.height,pm.width)
                columns.append([pm.y,arr[:,arr.shape[1]//2].tolist()])
            same=columns[0]==columns[1] and any(v<220 for v in columns[0][1])
            samples.append(dict(fraction=fraction,source=columns[0],candidate=columns[1],byte_identical=same))
        assert any(v['byte_identical'] for v in samples), 'Actual original vertical stroke paint/width changed'
        c._correction_qa_metrics = c.FontMetrics({role:Path(p) for role,p in q['new_font_paths'].items()})
        kk = old_pixel.interrow_ink(c,q,new)
        arrays=[]
        for pg in [op,npg,sp]:
            pm=pg.get_pixmap(matrix=fitz.Matrix(2,2),alpha=False)
            arrays.append(np.frombuffer(pm.samples,np.uint8).reshape(pm.height,pm.width,3).copy())
        a,b,source_rgb=arrays;original_mask=np.zeros(a.shape[:2],bool)
        def add(mask,r):
            x0=max(0,math.floor(r[0]*2));x1=min(mask.shape[1],math.ceil(r[2]*2));y0=max(0,math.floor(r[1]*2));y1=min(mask.shape[0],math.ceil(r[3]*2));mask[y0:y1,x0:x1]=True
        for r in rects:add(original_mask,r)
        mask=original_mask.copy();add(mask,source_support)
        changed=np.any(a!=b,axis=2);outside=changed&~mask
        assert not outside.any(), ('Actual pixels outside exact source/target stroke support union',int(outside.sum()))
        admitted=np.argwhere(changed&~original_mask)
        assert admitted.tolist() == [[1328,215],[1328,216],[1328,217],[1329,215],[1329,216],[1329,217]]
        assert all(np.array_equal(a[y,x],source_rgb[y,x]) and b[y,x].tolist()==[255,255,255] for y,x in admitted)
        def outside_glyphs(page):
            return [v for v in visible(page) if not any(abs(v['origin'][1]-y)<.001 for y in baselines)
                and not any((fitz.Rect(r)&fitz.Rect(v['bbox'])).get_area()>0 for r in rects+[source_support])]
        assert outside_glyphs(op)==outside_glyphs(npg)
    return dict(page=32,passed=True,status='PASS',proof_sha256=sha(candidate),layout_sha256=sha(lp),
        reference_proof_sha256=sha(O/'frozen/reference-proofs/page32.pdf'),protected_source_sha256=SOURCE,
        source_bound_changed_row_baselines=baselines,source_bound_row_rects=rects,
        original_source_stroke_support_rect=source_support,anti_alias_support_pad_pt=.5,pixel_scale=2,
        changed_pixels_total=int(changed.sum()),changed_pixels_outside_named_source_rows=0,
        unchanged_frozen_mask_original_outside_pixels=6,admitted_original_underline_tail_pixel_yx=admitted.tolist(),
        all_admitted_pixels_exact_original_source_and_P0_stroke_erasure=True,
        visible_glyph_geometry_outside_rows_exactly_equal=True,all_actual_glyphs_equal_to_full_font_curve_audited_immutable_proof=True,
        source_font_programs_images_and_image_placements_preserved=True,source_operator_indices=[392,393,394],
        source_stroke_program_sha256=PROGRAM,source_mapping_index=34,source_semantic_mapping_sha256=MAP,
        actual32x_vertical_stroke_samples=samples,kk=kk,glyph_tolerance_pt=.001,native_vector_tolerance_pt=1e-7,
        certified_full_font_curve_proof_sha256=GOOD,certified_original_layout_sha256=LAYOUT,
        correction_scope='Only missing original Some hints stroke support; no row/glyph/figure expansion or pad relaxation.',
        program_sha256=sha(__file__),frozen_pixel_auditor_sha256=sha(old_pixel.__file__))


if __name__ == '__main__':
    result=audit(F/'page32.pdf')
    out=A/'actual-p32-external-pixel-KK-audit.json';assert not out.exists()
    out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n','utf8')
    print('P32-EXTERNAL-EXACT-STROKE-SUPPORT-PASS',out,sha(out),flush=True)

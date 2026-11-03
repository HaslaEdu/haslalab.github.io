"""Independent actual-PDF orbital audit, including real d/space counts."""
from pathlib import Path
from io import BytesIO
import hashlib
import json
import re
import sys
import pikepdf
import pymupdf as fitz
from fontTools.ttLib import TTFont
from fontTools.cffLib import CFFFontSet

O = Path(__file__).resolve().parent
SOURCE = O / 'frozen/source/IChO_2024_T_EN.pdf'
SOURCE_SHA = '959174ab5ddc8be71c251c8fe95a12c810ba730edbcbbef3b771197e32929a4a'
PROFILE = O / 'readonly-hold-review-20261103/p57-native-d-existing-interface-design.json'
PROFILE_SHA = 'f3efb347598737eb8505f8f529e044e15ee4307a8bdf5caaced7e88f2b09ff3d'
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
read = lambda p: json.loads(Path(p).read_text('utf8'))
family = lambda n: re.sub(r'^[A-Z]{6}\+', '', str(n).lstrip('/'))
face = lambda n: re.sub('[^a-z0-9]', '', family(n).lower())


def glyphs(page):
    result = []
    for t in page.get_texttrace():
        if t['type'] == 3 or t['opacity'] <= 0:
            continue
        for cp, gid, origin, box in t['chars']:
            result.append(dict(c=chr(cp), gid=gid, font=t['font'], size=t['size'],
                origin=list(origin), bbox=list(box), paint=t['type'], opacity=t['opacity'],
                color=list(t['color']) if isinstance(t['color'], tuple) else t['color'],
                direction=list(t['dir'])))
    return result


def font_records(path, page_index):
    rows = []
    with pikepdf.Pdf.open(path) as pdf:
        fonts = pdf.pages[page_index].Resources.Font
        for name, font in fonts.items():
            ff = font.DescendantFonts[0] if font.Subtype == pikepdf.Name.Type0 else font
            desc = ff.get('/FontDescriptor')
            if desc is None:
                continue
            streams = [(key, desc[key]) for key in ['/FontFile', '/FontFile2', '/FontFile3'] if key in desc]
            if len(streams) != 1:
                continue
            kind, stream = streams[0]
            data = stream.read_bytes()
            assert data, ('Empty embedded font program', path, name)
            subtype = str(stream.get('/Subtype', ''))
            if kind == '/FontFile2' or subtype == '/OpenType':
                tt = TTFont(BytesIO(data))
                internal = [tt['name'].getDebugName(6)]
                tt.close()
            elif subtype in ['/CIDFontType0C', '/Type1C']:
                cf = CFFFontSet()
                cf.decompile(BytesIO(data), None)
                internal = [v.decode('ascii') if isinstance(v, bytes) else str(v) for v in cf.fontNames]
            else:
                internal = ['UNPARSED:' + subtype]
            encoding = str(font.get('/Encoding', ''))
            base_name = str(font.get('/BaseFont', ''))
            base_family = family(base_name)
            # The literal PDF Encoding suffix is not part of the face name.
            suffix = '-' + encoding.lstrip('/')
            if encoding == '/Identity-H' and base_family.endswith(suffix):
                base_family = base_family[:-len(suffix)]
            rows.append(dict(resource=str(name), object_reference=list(font.objgen),
                BaseFont=base_name, descriptor_FontName=str(desc.get('/FontName', '')),
                base_family=base_family, descriptor_family=family(desc.get('/FontName', '')),
                Encoding=encoding, subtype=str(font.Subtype), fontfile_kind=kind,
                fontfile_subtype=subtype, internal_PostScript_names=internal,
                embedded_program_sha256=hashlib.sha256(data).hexdigest(), embedded_program_bytes=len(data)))
    return rows


def bound_programs(source_rows, target_rows, expected_family):
    # Select the original resource using exact source descriptor and face
    # identity, then require that same resource/program in the actual output.
    source = [r for r in source_rows if r['base_family'] == expected_family and r['descriptor_family'] == expected_family]
    assert len(source) == 1, ('Ambiguous original font resource', expected_family, source)
    before = source[0]
    after = [r for r in target_rows if r['resource'] == before['resource']]
    assert len(after) == 1, ('Original font resource missing', before)
    after = after[0]
    for field in ['BaseFont', 'descriptor_FontName', 'Encoding', 'subtype', 'fontfile_kind',
                  'fontfile_subtype', 'internal_PostScript_names', 'embedded_program_sha256', 'embedded_program_bytes']:
        assert before[field] == after[field], ('Original embedded font resource changed', field, before, after)
    for alternative in target_rows:
        if alternative['base_family'] == expected_family or alternative['descriptor_family'] == expected_family:
            assert alternative['embedded_program_sha256'] == before['embedded_program_sha256'], ('Substitute font program under original face name', alternative)
    return dict(trace_family=expected_family, source=before, actual=after)


def spaces_between(all_glyphs, d, first_subscript, expected_six):
    x0, x1 = d['origin'][0] - .001, first_subscript['origin'][0] + .001
    y0 = min(g['bbox'][1] for g in expected_six) - .001
    y1 = max(g['bbox'][3] for g in expected_six) + .001
    return [g for g in all_glyphs if g['c'].isspace() and x0 <= g['origin'][0] <= x1 and y0 <= g['origin'][1] <= y1]


def audit(pdf_path, layout_path=None):
    path = Path(pdf_path)
    lp = Path(layout_path) if layout_path else path.with_suffix('.layout.json')
    q = read(lp)
    assert q['page'] == 57, 'Wrong page'
    assert q['source_sha256'] == SOURCE_SHA and Path(q['source']).resolve() == SOURCE.resolve(), 'Wrong original source binding'
    assert sha(SOURCE) == SOURCE_SHA and q['output_sha256'] == sha(path), 'Actual PDF/source hash mismatch'
    assert sha(PROFILE) == PROFILE_SHA
    ref = read(PROFILE)
    d = dict(ref['actual_original_d_glyph'], paint=0)
    expected = [d] + ref['original_adjacent_native_subscript_group']['glyphs']
    key = lambda g: (g['c'], g['gid'], g['font'], g['size'], tuple(g['origin']))
    groups = [s for s in q['native_shifts'] if key(d) in {key(g) for g in s['glyphs']}]
    assert len(groups) == 1 and len(groups[0]['glyphs']) == 6
    group = groups[0]
    assert {key(g) for g in group['glyphs']} == {key(g) for g in expected}, 'Incomplete six-glyph atom'
    dx = group['dx']
    assert not any(key(g) == key(d) for g in q['selected_glyphs']), 'Original d still selected as language'
    original_resources = font_records(SOURCE, 56)
    actual_resources = font_records(path, 0)
    bindings = [bound_programs(original_resources, actual_resources, name) for name in ['NotoSans', 'LatinModernMath-Regular']]
    actual_rows = []
    with fitz.open(SOURCE) as before, fitz.open(path) as after:
        source_glyphs, actual = glyphs(before[56]), glyphs(after[0])
        for g in expected:
            originals = [v for v in source_glyphs if key(v) == key(g)]
            assert len(originals) == 1 and originals[0]['opacity'] == 1
            source = originals[0]
            pos = [g['origin'][0] + dx, g['origin'][1]]
            matches = [v for v in actual if v['c'] == g['c'] and v['gid'] == g['gid'] and v['font'] == g['font']
                and v['size'] == g['size'] and v['paint'] == g['paint'] and v['opacity'] == 1
                and max(abs(v['origin'][j] - pos[j]) for j in [0, 1]) <= .001]
            assert len(matches) == 1, ('Actual native font/GID/point/common-dx mismatch', g, pos, matches)
            found = matches[0]
            assert found['origin'][1] == source['origin'][1] and found['color'] == source['color'] and found['direction'] == source['direction']
            target_box = [g['bbox'][j] + (dx if j % 2 == 0 else 0) for j in range(4)]
            assert max(abs(x-y) for x,y in zip(target_box, found['bbox'])) <= .001
            actual_rows.append(dict(source=source, actual=found, actual_dx=found['origin'][0]-g['origin'][0]))
        ko_faces = {face(r['BaseFont']) for r in actual_resources if r['resource'].startswith('/KO_Natural_')}
        assert ko_faces, 'New Korean font resources missing'
        newly_typed_d = [g for g in actual if g['c'] == 'd' and face(g['font']) in ko_faces
            and abs(g['origin'][1]-d['origin'][1]) <= .001]
        assert not newly_typed_d, ('Actual new-Korean d at orbital row', newly_typed_d)
        original_six = [r['source'] for r in actual_rows]
        actual_six = [r['actual'] for r in actual_rows]
        original_spaces = spaces_between(source_glyphs, original_six[0], original_six[1], original_six)
        actual_spaces = spaces_between(actual, actual_six[0], actual_six[1], actual_six)
        assert not original_spaces, ('Source itself has an ordinary space before subscript', original_spaces)
        assert not actual_spaces, ('Actual ordinary-space glyph inside d-to-subscript interval', actual_spaces)
    spread = max(r['actual_dx'] for r in actual_rows)-min(r['actual_dx'] for r in actual_rows)
    assert spread <= .001
    return dict(status='PASS', page=57, proof_sha256=sha(path), layout_sha256=sha(lp), source_sha256=SOURCE_SHA,
        source_profile_sha256=PROFILE_SHA, actual_original_native_glyphs=6, actual_common_dx_spread_pt=spread,
        source_and_actual_embedded_font_resources=bindings, glyphs=actual_rows,
        actual_visible_new_Korean_d_count_at_orbital_row=len(newly_typed_d),
        measured_source_ordinary_space_glyphs_between_d_and_subscript=len(original_spaces),
        measured_actual_ordinary_space_glyphs_between_d_and_subscript=len(actual_spaces),
        source_ordinary_spaces=original_spaces, actual_ordinary_spaces=actual_spaces,
        actual_new_Korean_d_glyphs=newly_typed_d, source_d_to_first_subscript_dx=original_six[1]['origin'][0]-original_six[0]['origin'][0],
        actual_d_to_first_subscript_dx=actual_six[1]['origin'][0]-actual_six[0]['origin'][0],
        glyph_tolerance_pt=.001, native_vector_tolerance_pt=1e-7, program_sha256=sha(__file__))


if __name__ == '__main__':
    path = Path(sys.argv[1])
    result = audit(path)
    out = path.with_suffix('.actual-native-atom-v2.json')
    assert not out.exists()
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n', 'utf8')
    print('ACTUAL-NATIVE-ATOM-V2-PASS', out, sha(out), flush=True)

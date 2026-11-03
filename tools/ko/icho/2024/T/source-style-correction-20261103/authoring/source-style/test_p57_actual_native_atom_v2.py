"""Four actual-PDF corruptions, including a d or space from a different slot."""
from pathlib import Path
from io import BytesIO
import hashlib
import json
import sys
sys.dont_write_bytecode = True
import pikepdf
from fontTools.ttLib import TTFont
import audit_p57_actual_native_atom_v2 as audit

O = Path(__file__).resolve().parent
R = O / 'revisions/native-d-p7-v7'
F = O / 'experiments/v7'
sys.path.insert(0, str(R / 'working/style-engine'))
import latex_native_motion as motion

sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
good = F / 'page57.pdf'
q = json.loads(good.with_suffix('.layout.json').read_text('utf8'))
positive = audit.audit(good)
actual_six = [r['actual'] for r in positive['glyphs']]
original_d = actual_six[0]
space = 2.2316224138535006
shifted, shift_audit = motion.reposition_inline(good, 1,
    shifts=[dict(glyphs=[{k:g[k] for k in ['c','gid','font','size','origin','bbox','paint']} for g in actual_six[1:]], dx=space)], validate=True)
assert shift_audit['passed']


def append_ko_character(character, x, y):
    # The source-matched full font GID is the encoded CID in these retained-GID
    # new Korean font resources. Use the already embedded font, not a new one.
    ff = TTFont(q['new_font_paths']['sans'])
    gid = ff.getGlyphID(ff.getBestCmap()[ord(character)])
    ff.close()
    with pikepdf.Pdf.open(good) as pdf:
        page = pdf.pages[0]
        assert pikepdf.Name('/KO_Natural_sans') in page.Resources.Font
        gs = page.Resources.get('/ExtGState', pikepdf.Dictionary())
        gs[pikepdf.Name('/P57_NEG_OPAQUE')] = pikepdf.Dictionary(Type=pikepdf.Name.ExtGState,
            ca=1, CA=1, BM=pikepdf.Name.Normal)
        page.Resources.ExtGState = gs
        old = list(page.Contents) if isinstance(page.Contents, pikepdf.Array) else [page.Contents]
        # Restore the default page graphics state after all unchanged original
        # streams, then add the isolated counterexample glyph in page space.
        height = float(page.MediaBox[3]) - float(page.MediaBox[1])
        text = f'q /P57_NEG_OPAQUE gs 0 0 0 rg BT /KO_Natural_sans {original_d["size"]:.12f} Tf 0 Tr 1 0 0 1 {x:.12f} {height-y:.12f} Tm <{gid:04X}> Tj ET Q'
        page.Contents = pikepdf.Array([pdf.make_stream(b'q\n'), *old, pdf.make_stream(b'\nQ\n'), pdf.make_stream(text.encode('ascii'))])
        result = BytesIO()
        pdf.save(result, compress_streams=False)
        return result.getvalue()


results = []


def rejected(name, data, expected_error, other_slot=None):
    folder = F / 'actual-native-atom-v2-negatives' / name
    folder.mkdir(parents=True, exist_ok=False)
    path = folder / 'page57.pdf'
    path.write_bytes(data)
    fake = json.loads(json.dumps(q))
    fake['output_sha256'] = sha(path)
    if other_slot:
        # Deliberately keep the orbital source slot absent and claim the extra
        # glyph comes from an unrelated slot. The new check must read the PDF.
        fake['placements'].append(dict(id='p57:b11:l3:s5-5#unrelated-negative',
            text=other_slot, font_role='sans', size=original_d['size'], baseline=original_d['origin'][1]))
    lp = path.with_suffix('.layout.json')
    lp.write_text(json.dumps(fake, ensure_ascii=False, indent=2)+'\n', 'utf8')
    try:
        audit.audit(path)
    except AssertionError as exc:
        assert expected_error in str(exc), (name, str(exc))
        results.append(dict(name=name, rejected=True, actual_PDF_corruption=True,
            false_six_glyph_report_and_fresh_output_hash_were_supplied=True,
            proof_sha256=sha(path), layout_sha256=sha(lp), expected_actual_check=expected_error,
            concrete_mismatch=str(exc)[:7000], unrelated_slot_label=other_slot))
    else:
        raise AssertionError(name+' incorrectly accepted')


rejected('ordinary-space-width-separates-five-subscripts', shifted, 'Actual native font/GID/point/common-dx mismatch')
rejected('retained-old-proof-redraws-CJK-d', (O/'frozen/reference-proofs/page57.pdf').read_bytes(), 'Actual native font/GID/point/common-dx mismatch')
rejected('another-slot-adds-visible-Korean-font-d', append_ko_character('d', 520, original_d['origin'][1]),
    'Actual new-Korean d at orbital row', other_slot='d')
space_x = (original_d['bbox'][2]+actual_six[1]['origin'][0])/2
rejected('another-slot-adds-ordinary-space-glyph', append_ko_character(' ', space_x, original_d['origin'][1]),
    'Actual ordinary-space glyph inside d-to-subscript interval', other_slot=' ')
assert len(results) == 4
out = F/'p57-actual-native-atom-v2-negative-regressions.json'
assert not out.exists()
out.write_text(json.dumps(dict(status='PASS', actual_PDF_corruptions=4, all_rejected=True,
    positive_proof_sha256=sha(good), positive_layout_sha256=sha(good.with_suffix('.layout.json')),
    source_original_d_and_five_subscript_geometry_checked=True,
    actual_new_Korean_d_and_ordinary_space_counts_checked_from_PDF=True,
    program_sha256=sha(__file__), auditor_program_sha256=sha(audit.__file__), cases=results),
    ensure_ascii=False, indent=2)+'\n', 'utf8')
print('P57-ACTUAL-NATIVE-ATOM-V2-FOUR-NEGATIVES-PASS', out, sha(out), flush=True)

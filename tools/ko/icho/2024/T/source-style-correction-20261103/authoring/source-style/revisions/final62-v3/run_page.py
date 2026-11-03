"""One final page under the shared PDF memory gate and frozen inputs."""
from pathlib import Path
import hashlib
import json
import sys
import subprocess
sys.dont_write_bytecode = True
R = Path(__file__).resolve().parent
O = R.parents[1]
W = R / 'working'
F = O / 'final/2024-v3'
sys.path.insert(0, str(W / 'authoring'))
import natural_plan_compose_icho2024_style as c
import verify_semantic_bindings_icho2024 as semantic
import verify_prose_underline_and_style_icho2024 as style
import verify_native_vectors_icho2024_style as native
import verify_pixel_and_KK_icho2024 as pixel
import verify_inline_atom_appearance_icho2024 as atom
import icho2024_style_experiment_guard as guard
from PIL import Image
import pymupdf as fitz


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


n = int(sys.argv[1])
assert n in range(1, 63)
guard.PROOFS = F
target = F / f'page{n:02}.pdf'
assert not target.exists()
over = W / f'overrides/page{n:02}.overrides.json'
c.build(W / f'plans/page{n:02}.plan.json', target, json.loads(over.read_text('utf8')), over)
s = semantic.run(n, F)
a = style.run(n)
v = native.verify(target)
p = pixel.run(n, F)
if n == 39:
    atom.run(F)
if n == 57:
    subprocess.run([sys.executable, '-X', 'utf8', str(O / 'audit_p57_actual_native_atom_v2.py'), str(target)], cwd=R, check=True)
references = json.loads((R / 'selected-prototype-references.json').read_text('utf8'))
if str(n) in references:
    previous_folder = references[str(n)]
    previous = O / previous_folder / f'page{n:02}.pdf'
    before = Image.open(previous.with_suffix('.png')).convert('RGB')
    after = Image.open(target.with_suffix('.png')).convert('RGB')
    assert before.size == after.size and before.tobytes() == after.tobytes(), (n, 'Prototype pixel mismatch')
    with fitz.open(previous) as d1, fitz.open(target) as d2:
        assert c._glyphs(d1[0]) == c._glyphs(d2[0]), (n, 'Prototype glyph mismatch')
    eq = dict(page=n, passed=True, proof_sha256=sha(target),
        previous_selected_proof=str(previous), previous_selected_proof_sha256=sha(previous),
        previous_PNG_sha256=sha(previous.with_suffix('.png')), final_PNG_sha256=sha(target.with_suffix('.png')),
        actual_1_5x_RGB_pixels_identical=True, all_visible_actual_glyph_geometry_identical=True,
        no_font_size_baseline_word_space_or_scientific_symbol_change=True,
        program_sha256=sha(__file__))
    target.with_suffix('.prototype-equivalence.json').write_text(json.dumps(eq, indent=2) + '\n', 'utf8')
print(json.dumps(dict(page=n, passed=True, glyphs=a['all_authored_glyphs_verified'],
    underlines=len(a['underline_rows']), italic=s['new_Korean_italic_placements'],
    KK_pairs=p['kk']['tested_close_row_pairs'], outside_pixels=p['changed_pixels_outside_named_source_rows'])), flush=True)

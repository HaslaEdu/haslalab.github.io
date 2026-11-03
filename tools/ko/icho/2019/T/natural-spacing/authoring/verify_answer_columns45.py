"""Read the actual source/output PDF glyphs for both original answer columns."""
from pathlib import Path
import hashlib, json, sys
import fitz

B = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(B))
import icho2019_write_guard as g

sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
proof = g.PROOFS / 'page45.pdf'
g.assert_output(proof, 45)
assert sha(g.SOURCE) == g.SOURCE_SHA
ys = [735.219970703125, 759.0960083007812]

def boxes(page):
    result = []
    for span in page.get_texttrace():
        if 'Wingdings' not in span['font']:
            continue
        for char in span['chars']:
            if min(abs(char[2][1] - y) for y in ys) < .0001:
                result.append(dict(code=char[0], gid=char[1], origin=list(char[2]), bbox=list(char[3]), font=span['font'], size=span['size'], color=span['color'], opacity=span['opacity'], render_type=span['type']))
    return sorted(result, key=lambda r: (r['origin'][1], r['origin'][0]))

with fitz.open(g.SOURCE) as original, fitz.open(proof) as target:
    source_boxes = boxes(original[44])
    actual_boxes = boxes(target[0])
assert len(source_boxes) == len(actual_boxes) == 4
for source, actual in zip(source_boxes, actual_boxes):
    for key in ['code', 'gid', 'font', 'size', 'color', 'opacity', 'render_type']:
        assert actual[key] == source[key], (key, source, actual)
    for key in ['origin', 'bbox']:
        assert max(abs(a - b) for a, b in zip(source[key], actual[key])) <= 1e-6, (key, source, actual)

layout_path = g.PROOFS / 'page45.layout.json'
layout = json.loads(layout_path.read_text('utf8'))
assert layout['output_sha256'] == sha(proof)
labels = [p for p in layout['placements'] if p['id'] in [f'p45:b{b}:l{l}:s{s}' for b in [10, 11] for l, s in [(2, '1-1'), (4, '1-2')]]]
assert len(labels) == 4
assert all(p['text'] in ['소수성', '친수성'] and abs(p['point'][0] - p['old_x']) < .001 for p in labels)
assert not [s for s in layout['native_shifts'] if any(min(abs(glyph['origin'][1] - y) for y in ys) < .0001 for glyph in s['glyphs'])]
report = dict(passed=True, page=45, source_sha256=g.SOURCE_SHA, proof_sha256=sha(proof), layout_sha256=sha(layout_path), source_checkbox_glyphs=source_boxes, actual_output_checkbox_glyphs=actual_boxes, source_column_labels=[dict(id=p['id'], text=p['text'], original_x=p['old_x'], target_point=p['point']) for p in labels], scope='Both source answer-choice columns retain all four original checkbox codes/GIDs/fonts/sizes/colors/opacity/render modes and exact original glyph coordinates. Each translated label begins at its own original source prose anchor. No other page is changed.', audit_code_sha256=sha(__file__))
out = g.PROOFS / 'page45.answer-columns-audit.json'
out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', 'utf8')
print(json.dumps(dict(passed=True, page=45, sha256=sha(out))))

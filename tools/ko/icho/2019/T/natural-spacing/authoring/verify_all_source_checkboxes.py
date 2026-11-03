"""Independently compare every actual source Wingdings GID133 checkbox on 60 pages."""
from pathlib import Path
import hashlib, json, sys
import fitz

B = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(B))
import icho2019_write_guard as g

sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
assert sha(g.SOURCE) == g.SOURCE_SHA

def checkboxes(page):
    rows = []
    for span in page.get_texttrace():
        if 'Wingdings' not in span['font']:
            continue
        for char in span['chars']:
            if char[1] == 133:
                rows.append(dict(code=char[0], gid=char[1], origin=list(char[2]), bbox=list(char[3]), font=span['font'], size=span['size'], color=span['color'], opacity=span['opacity'], render_type=span['type']))
    return sorted(rows, key=lambda r: (r['origin'][1], r['origin'][0]))

pages = []
with fitz.open(g.SOURCE) as original:
    for n in range(1, 61):
        proof = g.PROOFS / f'page{n:02}.pdf'
        g.assert_output(proof, n)
        with fitz.open(proof) as target:
            source_rows = checkboxes(original[n - 1])
            actual_rows = checkboxes(target[0])
        assert len(source_rows) == len(actual_rows), (n, 'checkbox count changed')
        max_error = 0.
        for source, actual in zip(source_rows, actual_rows):
            for key in ['code', 'gid', 'font', 'size', 'color', 'opacity', 'render_type']:
                assert source[key] == actual[key], (n, key, source, actual)
            for key in ['origin', 'bbox']:
                error = max(abs(a - b) for a, b in zip(source[key], actual[key]))
                max_error = max(max_error, error)
                assert error <= 1e-6, (n, key, source, actual)
        pages.append(dict(page=n, passed=True, checkbox_count=len(source_rows), max_actual_coordinate_error_pt=max_error, proof_sha256=sha(proof), source_checkbox_glyphs=source_rows, actual_checkbox_glyphs=actual_rows))
assert all(row['checkbox_count'] for row in pages if row['page'] in [13, 45, 46, 51])
report = dict(passed=True, source_sha256=g.SOURCE_SHA, pages_verified=60, checkbox_count=sum(row['checkbox_count'] for row in pages), max_actual_coordinate_error_pt=max(row['max_actual_coordinate_error_pt'] for row in pages), pages=pages, audit_code_sha256=sha(__file__), scope='Actual original PDF vs actual final single-page PDF text traces. Every original Wingdings GID133 checkbox retains its Unicode/code, GID, font, point size, original x/y and bbox within 1e-6pt, color, opacity and render type. No native movement declaration or target-layout metadata is accepted in place of actual coordinates. No source/target PDF is modified.')
out = B / 'final-r2-code-review/all-source-checkbox-coordinate-audit.json'
out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', 'utf8')
print(json.dumps(dict(passed=True, pages=60, checkboxes=report['checkbox_count'], max_error_pt=report['max_actual_coordinate_error_pt'], sha256=sha(out))))

"""Record a real source/target image read only after final-page artifact checks."""
from pathlib import Path
import argparse
import hashlib
import json
import sys
sys.dont_write_bytecode = True
import qa3_common as g
O = g.O
F = O / 'final/2024-v3'
R = O / 'revisions/final62-v3'


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def read(p):
    return json.loads(Path(p).read_text('utf8'))


parser = argparse.ArgumentParser()
parser.add_argument('page', type=int)
parser.add_argument('--observation', required=True)
parser.add_argument('--evidence', action='append', default=[])
args = parser.parse_args()
n = args.page
assert n in g.complete_pages()
path = F / 'manual-review-checkpoints.json'
out = read(path)
assert n not in [v['page'] for v in out['reviewed']]
render = read(F / f'page{n:02}.render.json')
q = read(F / f'page{n:02}.layout.json')
assert sha(F / f'page{n:02}.pdf') == render['proof_sha256'] == q['output_sha256']
assert sha(F / f'page{n:02}.layout.json') == render['layout_sha256']
assert sha(F / f'page{n:02}.png') == render['image_sha256']
assert sha(F / f'page{n:02}-source.png') == render['source_image_sha256']
assert render['source_sha256'] == '959174ab5ddc8be71c251c8fe95a12c810ba730edbcbbef3b771197e32929a4a'
for suffix in ['semantic-style-audit', 'underline-style-audit', 'pixel-KK-audit']:
    report = read(F / f'page{n:02}.{suffix}.json')
    assert report['passed'] and report['proof_sha256'] == render['proof_sha256']
out['reviewed'].append(dict(page=n, status='PASS', reviewer='/root/ortvay_current',
    review_mode='ACTUAL_ORIGINAL_RESOLUTION_FINAL_SOURCE_AND_CANDIDATE_PNGS_READ',
    actual_original_resolution_source_and_candidate_images_read=True, current_file_reopened_for_this_rebinding=True,
    proof_sha256=render['proof_sha256'], layout_sha256=render['layout_sha256'], composer_sha256=render['composer_sha256'],
    source_sha256=render['source_sha256'], image_sha256=render['image_sha256'], source_image_sha256=render['source_image_sha256'],
    code_input_freeze_sha256=sha(R / 'FINAL-CODE-INPUT-FREEZE.json'),
    qa_amendment_code_input_freeze_sha256=sha(g.C / 'CODE-INPUT-FREEZE.json'),
    observation=args.observation, additional_actual_read_evidence=[dict(path=str(Path(v)), sha256=sha(v)) for v in args.evidence],
    review_recording_program_path=str(Path(__file__).resolve()), review_recording_program_sha256=sha(__file__)))
out['reviewed'].sort(key=lambda v: v['page'])
path.write_text(json.dumps(out, ensure_ascii=False, indent=2) + '\n', 'utf8')
print('ACTUAL-PNG-READ-PASS', n, 'reviewed', len(out['reviewed']), flush=True)

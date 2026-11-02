"""Freeze one-page authored-space repair without changing historical READY editions."""
from pathlib import Path
import sys,json,hashlib,shutil
ROOT=Path.cwd()
BASE=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(BASE/'engine'),str(ROOT/'tools')]
from pdf_memory_gate import page_worker
import izho_natural_spacing_ready as ready
ready.BUILD=BASE
original_render=ready.fresh_render
def serial_render(*args,**kwargs):
    with page_worker():return original_render(*args,**kwargs)
ready.fresh_render=serial_render
folder=BASE/'2020/T'
review=json.loads((folder/'visual-review.json').read_text('utf8'))
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
for item in review['pages']:
    if item['page']==2:
        item.update(reviewed=True,proof_sha256=sha(folder/'page02.pdf'),notes='Full page visually reviewed after exact authored internal-space restoration: 다음 가정과 uses 3pt word space. Original epsilon whole 2D fraction/period, all display equations and star-shadow diagram retained. Natural paragraph/title alignment; no overlap or missing math.')
(folder/'visual-review.json').write_text(json.dumps(review,ensure_ascii=False,indent=2),'utf8')
manifest=ready.ready(2020,'T')
audits=[json.loads((folder/f'page{i:02d}.audit.json').read_text('utf8'))for i in range(1,6)]
for audit in audits:
    assert audit['independent_new_hangul_native_graphics_overlap']['passed']
    assert audit['independent_source_grading_columns']['passed']
    assert audit['independent_new_prose_original_math_overprint']['passed']
manifest['independent_new_hangul_native_graphics_overlap_pixels']=sum(q['independent_new_hangul_native_graphics_overlap']['new_hangul_dark_pixels_over_native_foreground']for q in audits)
manifest['independent_stationary_original_grading_glyphs_checked']=sum(q['independent_source_grading_columns']['original_grading_glyphs_checked']for q in audits)
manifest['independent_new_hangul_over_original_math_text_pixels']=sum(q['independent_new_prose_original_math_overprint']['new_hangul_pixels_over_original_mathematical_text']for q in audits)
snapshot=Path(manifest['authoring_snapshot'])/'tools'
sources={p.name:p for p in (BASE/'engine').glob('*.py')}
for module in tuple(sys.modules.values()):
    filename=getattr(module,'__file__',None)
    if filename:
        p=Path(filename)
        if p.suffix=='.py'and p.parent==ROOT/'tools'and p.name not in sources:sources[p.name]=p
for name,source in sources.items():
    target=snapshot/name;shutil.copyfile(source,target);manifest['authoring_files'][str(Path('tools')/name)]=sha(target)
shutil.copyfile(Path(__file__),snapshot/Path(__file__).name)
manifest['authoring_files'][str(Path('tools')/Path(__file__).name)]=sha(snapshot/Path(__file__).name)
manifest['single_page_revision']=json.loads((BASE/'revision-provenance.json').read_text('utf8'))
manifest['single_page_revision']['unchanged_pages']=[dict(page=i,proof_sha256=sha(folder/f'page{i:02d}.pdf'),original_authoring_snapshot=str(BASE.parent/'2020-T-authoring'))for i in[1,3,4,5]]
manifest['single_page_revision']['repaired_page']=dict(page=2,proof_sha256=sha(folder/'page02.pdf'),before='다음가정과',after='다음 가정과',restored_word_space_pt=3.0)
manifest['authoring_capture_note']='Page 2 rebuilt with frozen partial-authored-substring spacing engine; unchanged pages 1/3/4/5 retain exact historical proof bytes and original historical snapshots. Current tools snapshot freezes all imported project dependencies for this one-page revision and assembly.'
output=Path(manifest['output']);output.with_suffix('.ready.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),'utf8')
print('REVISED READY',manifest['sha256'],manifest['pages'],flush=True)

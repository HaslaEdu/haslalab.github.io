"""Recover migrated source paths at read time; preserve old manifests."""
from pathlib import Path
import sys,json,hashlib,shutil
R=Path('D:/CodexBuilds');B=R/'Hasla-original-style-20261031/izho2012-complete-solutions'
sys.path[:0]=[str(R),'C:/Users/andre/.codex/tmp/Hasla-original-style-20261102/izho2011-complete-solutions/engine']
from haslalab_runtime_paths import map_repository_path
from izho_initial_fixed_style import runs_of
from pdf_memory_gate import page_worker
import pymupdf as fitz
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
inventory=R/'Hasla-original-style-20261031/izho-missing-scope-20261102.json';original=inventory.read_bytes();entry=next(x for x in json.loads(original)['editions']if x['year']==2012 and x['kind']=='TS')
source=map_repository_path(entry['source']);legacy=map_repository_path(entry['template'])
assert sha(source)==entry['source_sha256_expected'];assert sha(legacy)==entry['template_sha256']
for source_path,dest in [(source,B/'2012/source/IZhO_2012_TS.pdf'),(legacy,B/'legacy-semantics/translation.json')]:
 dest.parent.mkdir(parents=True,exist_ok=True)
 if dest.exists():assert sha(dest)==sha(source_path)
 else:shutil.copy2(source_path,dest)
inspection=B/'2012/inspection';inspection.mkdir(parents=True,exist_ok=True)
with fitz.open(source)as doc:
 assert len(doc)==11
 for index,page in enumerate(doc,1):
  runs={','.join(map(str,k)):{key:v[key]for key in ['text','font','size','flags','color','origin','bbox']}for k,v in runs_of(page).items()}
  (inspection/f'page{index:02}-runs.json').write_text(json.dumps(runs,ensure_ascii=False,indent=2)+'\n','utf8')
  print('IZHO2012_SOURCE_PAGE',index,len(runs),'NATIVE_RUNS',flush=True)
 with page_worker():doc[0].get_pixmap(matrix=fitz.Matrix(2,2),alpha=False).save(inspection/'page01-source.png')
assert inventory.read_bytes()==original
(B/'source-policy.json').write_text(json.dumps(dict(source=str(B/'2012/source/IZhO_2012_TS.pdf'),source_sha256=sha(source),source_url=entry['official_url'],source_language='English',pages=11,legacy_KO_prose_records=218,legacy_prose_is_semantic_reference_only=True,source_math_fonts_and_layout_must_stay_native=True,unmodified_historical_inventory_sha256=hashlib.sha256(original).hexdigest(),historical_repo_paths_mapped_only_at_read_time=True,publication_ready=False),ensure_ascii=False,indent=2)+'\n','utf8')
print('IZHO2012_SOURCE_INSPECTION_PREPARED',B,flush=True)

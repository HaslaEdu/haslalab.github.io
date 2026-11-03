from pathlib import Path
import hashlib,json,sys,shutil,os
os.environ.update(PYTHONDONTWRITEBYTECODE='1',OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1')
D=Path('D:/CodexBuilds/Hasla-original-style-20261031/izho2019-complete-solutions');B=Path('C:/Users/andre/CodexWork/HaslaLab/translation-builds/izho2019-complete-solutions');sys.path[:0]=['D:/CodexBuilds/Hasla-original-style-20261031/izho2012-complete-solutions/engine','D:/CodexBuilds/Hasla-publish-20261031/tools']
from pdf_memory_gate import page_worker
import pymupdf as f
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();source_sha='5e83000f5d2abe161186a6f81e5b9cd306a0758d2969744edbfb68fcad413da8';policy=json.loads((D/'source-policy.json').read_text('utf8'));assert sha(D/'2019/source/IZhO_2019_TS.pdf')==policy['source_sha256']==source_sha
files=sorted(p for p in D.rglob('*')if p.is_file());pins={str(p.relative_to(D)):sha(p)for p in files}
for src in files:
 dst=B/src.relative_to(D);dst.parent.mkdir(parents=True,exist_ok=True)
 if dst.exists():assert dst.read_bytes()==src.read_bytes()
 else:shutil.copy2(src,dst)
out=B/'2019/inspection'
for n in range(1,13):
 dst=out/f'page{n:02}-source.png'
 if not dst.exists():
  with page_worker(),f.open(B/'2019/source/IZhO_2019_TS.pdf')as doc:assert len(doc)==12;doc[n-1].get_pixmap(matrix=f.Matrix(2,2),alpha=False).save(dst)
 print('IZHO2019_TS_C_SOURCE144_READY',n,flush=True)
assert pins=={str(p.relative_to(D)):sha(p)for p in files}
(B/'source-migration-read-only-policy.json').write_text(json.dumps(dict(original_read_only_D_root=str(D),new_derived_C_root=str(B),source_sha256=source_sha,pages=12,legacy_prose_records=392,legacy_semantics_only=True,original_D_file_pins=pins,original_D_files_unmodified=True,global_pdf_memory_gate='D:/CodexBuilds/Hasla-original-style-20261031/pdf-render-memory.lock',new_generated_files_in_D19=False,original_source_url=policy['source_url']),ensure_ascii=False,indent=2)+'\n','utf8')
print('IZHO2019_TS_C_SOURCE_READY_D_INPUTS_UNMODIFIED',source_sha,flush=True)

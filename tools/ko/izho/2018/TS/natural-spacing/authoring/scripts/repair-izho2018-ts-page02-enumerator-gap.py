from pathlib import Path
import sys,json,os
os.environ.update(PYTHONDONTWRITEBYTECODE='1',OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1')
B=Path('C:/Users/andre/CodexWork/HaslaLab/translation-builds/izho2018-complete-solutions');sys.path[:0]=[str(B/'engine'),'D:/CodexBuilds/Hasla-publish-20261031/tools'];p=B/'natural/2018/TS/plans/page02.json';d=json.loads(p.read_text('utf8'));r=next(r for r in d['reviewed_source_prose_native_reference_glyphs']if r['source_at']==[6,0,0]and r['source_text']=='А2.3');d['section_number_prefixes'].extend(r['source_glyphs']);d['reviewed_original_subsection_enumerator_spacing']=dict(native_source_identifier='А2.3',source_at=[6,0,0],reason='One normal quarter-em space separates the exact original subsection identifier and Korean demonstrative 이 계. Original native glyphs/fonts/points/paint/Y and all mathematics unchanged.');p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n','utf8')
from izho_natural_spacing_rebuild import page_build
page_build(p)

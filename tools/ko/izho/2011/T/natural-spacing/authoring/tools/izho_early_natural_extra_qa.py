"""Supplement the shared IZhO QA with independent graphics/cell collisions."""
import argparse,json
from pathlib import Path
from izho_natural_spacing import BUILD,ROOT
from izho_natural_spacing_qa import sha
from pdf_new_hangul_graphics_overlap import audit as collision_audit
from pdf_grading_columns_stationary import audit as grading_audit
from pdf_memory_gate import page_worker

def audit(year,page):
    folder=BUILD/str(year)/'T';proof=folder/f'page{page:02d}.pdf';path=proof.with_suffix('.audit.json')
    result=json.loads(path.read_text('utf8'));plan=json.loads((folder/f'plans/page{page:02d}.json').read_text('utf8'))
    if result['output_sha256']!=sha(proof):raise ValueError('Shared audited proof changed')
    original=folder/f'page{page:02d}.old-source.pdf'
    collision=collision_audit(proof)
    grading=grading_audit(original,proof,plan['prose_placements'])
    result['independent_new_hangul_native_graphics_overlap']=collision
    result['independent_source_grading_columns']=grading
    result['supplementary_qa_authoring_sha256']={str(Path('tools')/name):sha(ROOT/'tools'/name)for name in[
        'izho_early_natural_extra_qa.py','pdf_new_hangul_graphics_overlap.py','pdf_grading_columns_stationary.py']}
    result['passed']=result['passed']and collision['passed']and grading['passed']
    path.write_text(json.dumps(result,ensure_ascii=False,indent=2),'utf8')
    if not result['passed']:raise ValueError(('Extra independent graphics/grade-column QA failed',year,page,collision,grading))
    print(year,page,'extra QA PASS',flush=True);return result

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('year',type=int);p.add_argument('page',type=int);a=p.parse_args()
    with page_worker():audit(a.year,a.page)

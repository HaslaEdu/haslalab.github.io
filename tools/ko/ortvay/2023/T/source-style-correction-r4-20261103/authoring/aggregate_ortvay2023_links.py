"""Bind both freshly checked O2023 URL pages without altering their evidence."""
import argparse
import hashlib
import json
from pathlib import Path

sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
read=lambda p:json.loads(Path(p).read_text(encoding='utf-8-sig'))
p=argparse.ArgumentParser();p.add_argument('--page1',type=Path,required=True)
p.add_argument('--page6',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
a=p.parse_args();assert not a.output.exists()
documents=[read(a.page1),read(a.page6)]
assert [d['page']for d in documents]==[1,6]
common=['source_sha256','program_sha256','test_program_sha256','core_program_sha256','helper_sha256','assembler_sha256']
for key in common:assert documents[0][key]==documents[1][key],key
pages=[];inputs={}
for document in documents:
    assert document['status']=='PASS'and document['year']==2023 and document['changed_pixels']==0
    for key in ['all_visible_glyph_geometry_identical','all_nonrect_annotation_settings_identical_after_save',
                'annotation_P_same_page_semantics_verified','all_annotation_rectangles_checked_after_save']:
        assert document[key]is True
    assert len(document['negative_regression_details'])>=9
    assert all(row['rejected']for row in document['negative_regression_details'])
    for path,digest in document['inputs_rehashed_after_run'].items():
        assert sha(path)==digest,('Changed regression input',path)
        assert path not in inputs or inputs[path]==digest
        inputs[path]=digest
    assert sha(document['output_pdf'])==document['output_sha256']
    pages.append(dict(page=document['page'],proof_sha256=document['proof_sha256'],layout_sha256=document['layout_sha256'],
        output_sha256=document['output_sha256'],changed_pixels=0,all_visible_glyph_geometry_identical=True,
        all_nonrect_annotation_settings_identical_after_save=True,links=document['links'],
        negative_regressions=document['negative_regressions'],negative_regression_details=document['negative_regression_details']))
assert documents[0]['ready_manifest']['sha256']==documents[1]['ready_manifest']['sha256']
report={key:documents[0][key]for key in common}
report.update(schema='ortvay2023-r4-two-page-link-regression-v1',status='PASS',passed=True,year=2023,
    pages=pages,links=[v for d in pages for v in d['links']],changed_pixels=0,
    all_visible_glyph_geometry_identical=True,all_nonrect_annotation_settings_identical_after_save=True,
    annotation_P_same_page_semantics_verified=True,all_annotation_rectangles_checked_after_save=True,
    negative_regressions=[dict(page=d['page'],check=v)for d in pages for v in d['negative_regressions']],
    negative_regression_details=[dict(page=d['page'],**v)for d in pages for v in d['negative_regression_details']],
    page_regressions=[dict(path=str(path.resolve()),sha256=sha(path))for path in[a.page1,a.page6]],
    ready_manifest=documents[0]['ready_manifest'],inputs_rehashed_after_run=inputs,
    aggregation_program_path=str(Path(__file__).resolve()),aggregation_program_sha256=sha(__file__))
assert len(report['links'])==3 and len(report['negative_regressions'])>=18
a.output.parent.mkdir(parents=True,exist_ok=True)
a.output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(dict(status='PASS',links=3,negative_cases=len(report['negative_regressions']),path=str(a.output),sha256=sha(a.output))))

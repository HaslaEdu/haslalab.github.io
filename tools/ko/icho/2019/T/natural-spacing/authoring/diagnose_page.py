from pathlib import Path
import json,sys,traceback,time,hashlib
sys.stdout.reconfigure(encoding='utf-8')
import natural_plan_compose_icho2019 as composer
import verify_native_vectors_icho2019 as auditor
BASE=Path(__file__).resolve().parent
page=int(sys.argv[1]);plan=BASE.parent/'2019'/f'page{page:02}.ko.json';proof_root=Path(sys.argv[2])if len(sys.argv)>2 else composer.year_guard.PROOFS;out=proof_root/f'page{page:02}.pdf';composer.year_guard.assert_output(out,page)
report=dict(page=page,plan=str(plan),plan_sha256=hashlib.sha256(plan.read_bytes()).hexdigest(),composer=str(Path(composer.__file__).resolve()),frozen_helpers={m.__name__:str(Path(m.__file__).resolve())for m in[composer.motion,composer.ops,composer.ink,composer.original_helpers]},rasterization=False,source_font_substitution=False)
t=time.monotonic()
try:
 override=BASE/f'page{page:02}.overrides.json'
 layout=composer.build(plan,out,json.loads(override.read_text('utf8'))if override.exists()else None,override if override.exists()else None)
 vectors=auditor.verify(out)
 import verify_prose_underline_and_style as prose_style_auditor
 prose_style_audit=prose_style_auditor.run(page)
 import verify_graphic_label_geometry as graphic_auditor
 graphic_audit=graphic_auditor.run(page)
 import verify_source_caption_centers as caption_auditor
 caption_audit=caption_auditor.run(page)
 import audit_rows_and_render as row_auditor
 row_audit=row_auditor.run(page)
 import verify_template_geometry as template_auditor
 template_audit=template_auditor.run(page)
 report.update(passed=True,output=str(out),output_sha256=layout['output_sha256'],native_geometry=layout['final_native_geometry'],korean_geometry=layout['new_korean_glyph_and_geometry_audit'],vector_geometry=vectors)
 report['actual_new_korean_inter_row_ink_audit']=row_audit
 report['actual_prose_underline_coverage_and_style_audit']=prose_style_audit
 if graphic_audit:report['actual_outlined_vector_label_geometry_audit']=graphic_audit
 if caption_audit:report['actual_source_caption_center_audit']=caption_audit
 if template_audit:report['actual_template_geometry_audit']=template_audit
except Exception as exc:
 report.update(passed=False,error_type=type(exc).__name__,error=str(exc),traceback=traceback.format_exc())
report['elapsed_seconds']=time.monotonic()-t
(BASE/f'page{page:02}.diagnostic.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n','utf8')
print(json.dumps({k:v for k,v in report.items()if k not in{'traceback','native_geometry','korean_geometry'}},ensure_ascii=False),flush=True)
if not report['passed']:print(report['traceback'],flush=True);raise SystemExit(1)

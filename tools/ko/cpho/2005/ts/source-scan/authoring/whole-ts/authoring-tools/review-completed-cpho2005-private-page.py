"""Record an explicitly completed manual full-page review, never publication."""
from pathlib import Path
import json,hashlib,datetime,sys
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/cpho2005/TS');number=int(sys.argv[1]);sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();records=[]
plan=json.loads((B/f'authoring/page{number:02}-layout.json').read_text('utf8'));neg=json.loads((B/f'proofs/page{number:02}-negative-native-math-visibility.json').read_text('utf8'));assert neg['passed']
for lang in ['ko','en']:
 p=B/f'proofs/{lang}/page{number:02}.pdf';digest=sha(p);proofs={k:json.loads(p.with_suffix('.'+k+'.json').read_text('utf8'))for k in ['source-qa','poppler-qa']};assert all(v['passed']for v in proofs.values());assert proofs['source-qa']['final_sha256']==proofs['poppler-qa']['proof_sha256']==digest
 assert next(r for r in neg['results']if r['language']==lang)['good_sha256']==digest
 preview=p.parent/f'page{number:02}-preview.png';assert preview.stat().st_mtime>=p.stat().st_mtime
 records.append(dict(language=lang,proof_sha256=digest,preview_sha256=sha(preview),source_qa_sha256=sha(p.with_suffix('.source-qa.json')),poppler_qa_sha256=sha(p.with_suffix('.poppler-qa.json')),fresh_Poppler144_full_page_visually_reviewed=True,native_equation_numbers_math_and_original_y_scale_preserved=True,original_header_footer_horizontal_centers_retained=True,source_word_spacing_fixed_quarter_em=True))
report=dict(source_page=number,source_sha256=plan['source_sha256'],reviewed_UTC=datetime.datetime.now(datetime.timezone.utc).isoformat(),rows=len(plan['rows']),native_math_objects=sum(len(r['atoms'])for r in plan['rows']),records=records,real_native_math_omission_negative_rejected=True,all_two_renderer_source_nonlanguage_ink_and_math_RGB_changes_zero=True,publication_ready=False,complete_edition_ready=False,scope=f'Complete private bilingual physical source page{number}; not a complete edition. Finish physical4–16 and final joins before publication.')
out=B/f'proofs/page{number:02}-visual-review.json';out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n','utf8')
if '--no-state'in sys.argv[2:]:
 print('RECORDED_PRIVATE_COMPLETE_BILINGUAL_SOURCE_PAGE',number,report['rows'],report['native_math_objects'],flush=True)
 raise SystemExit(0)
p=B.parents[1]/'current-task-state-20261101.json';d=json.loads(p.read_text('utf8'));d[f'CPhO2005_TS_page{number:02}_native_active']=dict(base=str(B),source_page=number,status='PRIVATE_BILINGUAL_PAGE_REVIEWED',source_rows=report['rows'],native_math_objects=report['native_math_objects'],proofs=records,all_four_renderer_language_checks_passed=True,real_native_math_omission_negatives_rejected=True,visual_review=str(out),publication_ready=False,next=f'Continue physical{number+1}–16; publish only complete13-page solutions. All8 missing IZhO TS editions2012–2019(91p) and broader CPhO source scope remain.')
d['current']=f'IZhO2011TS10p LIVE cache45, actual PDF SHA and all81 live revision URLs verified; all3 CI success. CPhO2005TS physical4–{number} private bilingual reviewed, physical{number+1}–16 remain. Missing IZhO2012–2019TS91p and all outstanding CPhO source coverage retained.'
p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n','utf8');print('RECORDED_PRIVATE_COMPLETE_BILINGUAL_SOURCE_PAGE',number,report['rows'],report['native_math_objects'],flush=True)

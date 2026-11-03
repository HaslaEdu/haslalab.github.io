from pathlib import Path
import json,hashlib
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/cpho2005/TS')
p=B.parents[1]/'current-task-state-20261101.json'
j=json.loads(p.read_text('utf8'))
pages={}
for n,rows,atoms in [(4,22,41),(5,33,58),(6,30,37),(7,19,45)]:
 proofs={}
 for lang in ['ko','en']:
  pdf=B/f'proofs/{lang}/page{n:02}.pdf'
  q=json.loads(pdf.with_suffix('.source-qa.json').read_text('utf8'))
  r=json.loads(pdf.with_suffix('.poppler-qa.json').read_text('utf8'))
  h=hashlib.sha256(pdf.read_bytes()).hexdigest()
  assert q['passed'] and r['passed'] and q['final_sha256']==r['proof_sha256']==h
  proofs[lang]=dict(path=str(pdf),sha256=h,MuPDF4x_source_qa=str(pdf.with_suffix('.source-qa.json')),Poppler144_source_qa=str(pdf.with_suffix('.poppler-qa.json')),both_pass=True)
 pages[str(n)]=dict(rows=rows,native_bitmap_math_atoms=atoms,proofs=proofs,actual_native_math_RGB_errors_both_renderers=0,all_source_font_programs_images_linear_ctms_pagegroup_preserved=True,missing_prose_collisions_protected_ink_loss_outside_declared_changes=0,negative_actual_native_math_omission_report=str(B/f'proofs/page{n:02}-negative-native-math-visibility.json'),publication_ready=False)
j['active_cpho_2005_ts']['completed_private_source_pages']=pages
j['active_cpho_2005_ts'].pop('first_page_physical4',None)
j['active_cpho_2005_ts']['next']='Physical04–07(4/13) both languages strict MuPDF4x+Poppler144 complete. Page7 caption center612.0pt/native1 and original fN/fP/fQ list geometry retained using source1.125/.5pt gaps; sourceprintfamily/points/weights independently measured. Physical08–16 authoring/QA and whole13-page KO+EN publication remain. Also working on newly authorized missing IZhO2018T6p native typography; p1 strict natural checks passed, p2–6 remain. No partial-edition publication.'
j['current']['CPhO2005']='All13physical04–16 semantic drafts complete186fields. First4/13pages(physical4–7) native bilingual proof complete104reviewed rows181nativebitmapmathatoms, exact0 in MuPDF4x+Poppler144 allcurrentSHA/negative actualomissionchecked. Private only; physical08–16 native authoring/QA/whole13pKO+ENpublication remain.'
j['current']['next']=j['active_cpho_2005_ts']['next']
j['remaining'][0]=j['current']['CPhO2005']
j['lastCommentary']='Showed current Poppler-rendered source vs Korean p05 comparison; all missing IZhO problems and solutions explicitly authorized, all original scope continues.'
j['IZhO2018_T_semantic_progress']=json.loads((B.parents[1]/'izho-missing-editions/2018/T/semantic-progress.json').read_text('utf8'))
j['IZhO2018_T_native_active']=dict(base='D:/CodexBuilds/Hasla-original-style-20261031/izho2018-theory-original',source_all6_original_pages_inventoried=True,source_math_cross_sectional_areas_confirmed=['S_0','S'],page1_private_natural_all4_checks_pass=True,page1_log='D:/CodexBuilds/Hasla-original-style-20261031/izho2018-theory-original/natural/2018/T/page01-build.log',remaining='p2–6 explicit native source prose/math authoring, full6p visual/font/math/heading QA/freeze/publication',publication_ready=False)
j['current']['IZhO_missing']='User explicitly requested all missing problems and solutions.11editions115p:2018/2019T and2011–2019TS. Newly authored all62 formerly blank2018T Korean prose fields, private semantic-only draft74records nowallfilled. Source math extraction2-3/2-4 misses secondarea variable: must recover actual native source before output. Remaining2017TS148blank+2018TS144blank; all11editions need original-style native reconstruction/proof/QA/publication even if older KO already filled. Full inventory pinned.'
j['environment_current_free_bytes']={drive:__import__('shutil').disk_usage(drive+':/').free for drive in ['C','D']}
p.write_text(json.dumps(j,ensure_ascii=False,indent=2)+'\n','utf8')
print('CURRENT_STATE_VERIFIED_AND_UPDATED',list(pages))

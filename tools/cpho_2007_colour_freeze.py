"""Freeze the separately audited strict 2007 colour repair, without natural proofs."""
from pathlib import Path
import hashlib,json,shutil

ROOT=Path(__file__).resolve().parents[1]
BASE=Path('D:/CodexBuilds/Hasla-original-style-20261031/english-face-repair/2007')
AUTHOR=ROOT/'tools/ko/cpho/2007/original'


def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    inventory_path=ROOT/'tools/cpho_2007_original_inventory.json'
    inv=json.loads(inventory_path.read_text('utf8'));files=[]
    for lang in ['ko','en']:
        p=BASE/f'editions/CPhO_2007_T_{lang.upper()}.pdf'
        audit=BASE/f'qa/{p.stem}/audit.json';a=json.loads(audit.read_text('utf8'))
        assert a['passed'] and a['sha256']==sha(p)
        assert all(not r['translation_style_violations'] and r['translation_size_max_delta_pt']==0
                   and r['translation_baseline_max_delta_pt']==0 for r in a['pages'])
        q=AUTHOR/f'qa-{lang}-same-face.json';shutil.copyfile(audit,q)
        poppler=AUTHOR/f'qa-{lang}-same-face-poppler.json';b=json.loads(poppler.read_text('utf8'))
        assert b['passed'] and b['sha256']==sha(p)
        files.append(dict(path=str(p),file=p.name,language=lang,pages=4,bytes=p.stat().st_size,sha256=sha(p),
                          qa=q.relative_to(ROOT).as_posix(),additional_qa=poppler.relative_to(ROOT).as_posix()))
    inv['files']=files
    selection=('Interim strict baseline: body uses installed original SimSun; heading/date/section labels retain '
               'the previously declared Arial400 fallback. The subsequently acquired official SimHei full face '
               'is queued for the separate natural-spacing edition, and is not claimed in these frozen PDFs.')
    inv['translation_fonts']['en']=selection
    inv['english_same_face_repair'].update(sha256=files[1]['sha256'],korean_pdf_unchanged=False,
        korean_change_reason='Explicitly authorized repair of figure-reference prose colours to the original source palette; 4-page colour/font/size/baseline checks all zero.')
    inv['strict_colour_repair']=dict(status='READY',natural_spacing_applied=False,batang_applied=False,
        full_simhei_applied=False,original_native_math_and_figures_preserved=True,
        source_palette_style_size_baseline_violations=0,
        previous_korean_sha256='6d45fbd4ab984933febe512157a0d9dea839714169f4d01064f1bf5333c69aa2',
        previous_english_sha256='468832f5e9fcce91dfcb313f74accdeba169530f14c59ca62109b7e58eaf374e')
    policy_path=AUTHOR/'english-face-policy.json';policy=json.loads(policy_path.read_text('utf8'))
    policy['selection']=selection;policy['strict_colour_repair']=inv['strict_colour_repair']
    policy['korean_artifact_unchanged']=False
    policy_path.write_text(json.dumps(policy,ensure_ascii=False,indent=2)+'\n','utf8')
    extras=['tools/cpho_2007_colour_freeze.py','tools/ko/cpho/2007/original/qa-ko-same-face.json',
            'tools/ko/cpho/2007/original/qa-ko-same-face-poppler.json']
    inv['authoring_files']=list(dict.fromkeys(inv['authoring_files']+extras))
    inventory_path.write_text(json.dumps(inv,ensure_ascii=False,indent=2)+'\n','utf8')
    common_path=ROOT/'tools/cpho_original_en_face_inventory.json';common=json.loads(common_path.read_text('utf8'))
    common['scope']='Strict English family corrections for 2006/2007/2022, plus the explicitly authorized 2007 Korean/English source-colour repair. Natural-spacing/Batang/official-SimHei drafts are excluded.'
    for f in common['files']:
        if f['year']!=2007:continue
        f.update(path=files[1]['path'],sha256=files[1]['sha256'],bytes=files[1]['bytes'],
                 korean_colour_corrected=files[0],strict_colour_repair=inv['strict_colour_repair'])
        f.pop('korean_unchanged',None)
    common['authoring_files']=list(dict.fromkeys(common['authoring_files']+extras))
    common['authoring_file_sha256']={p:sha(ROOT/p) for p in common['authoring_files']}
    common_path.write_text(json.dumps(common,ensure_ascii=False,indent=2)+'\n','utf8')
    frozen=dict(status='READY_STRICT_COLOUR_REPAIR',year=2007,source_sha256=inv['source_sha256'],
                files=files,natural_spacing_applied=False,batang_applied=False,full_simhei_applied=False,
                source_colour_size_baseline_violations=0,independent_mupdf_and_poppler_pages_passed=8,
                authoring_files=inv['authoring_files'],
                authoring_file_sha256={p:sha(ROOT/p) for p in inv['authoring_files']},
                individual_inventory='tools/cpho_2007_original_inventory.json',
                common_inventory='tools/cpho_original_en_face_inventory.json')
    out=ROOT/'tools/cpho_2007_colour_inventory.json';out.write_text(json.dumps(frozen,ensure_ascii=False,indent=2)+'\n','utf8')
    print(json.dumps(dict(inventory=str(out),files=files),ensure_ascii=False))


if __name__=='__main__':main()

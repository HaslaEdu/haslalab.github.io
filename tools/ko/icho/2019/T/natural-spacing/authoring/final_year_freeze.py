"""Pin IChO2019 inputs before the one-code final proof run; verify all 60 pages."""
from pathlib import Path
import argparse,datetime,hashlib,json,sys
import icho2019_write_guard as g
B=Path(__file__).resolve().parent
F=B/'final-code-freeze.json'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(path,data):path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n','utf8')
def freeze():
    assert not F.exists(),'An existing final freeze must be explicitly reviewed, not overwritten.'
    g.assert_protected_2024();assert sha(g.SOURCE)==g.SOURCE_SHA
    paths=list(B.glob('*.py'))+list((B/'engine').glob('*.py'))
    paths += [g.PLANS/f'page{n:02}.ko.json'for n in range(1,61)]
    paths += [B/f'page{n:02}.overrides.json'for n in range(1,61)]
    paths += [B/'bootstrap-provenance.json',B/'source-emphasis-meaning-review.json',B/'graphic-source-font-role-inference.json',g.SOURCE]
    paths += list((B/'source-review').glob('*.json'))
    fd=Path('D:/CodexBuilds/Hasla-publish-20261031/tools/ko/fonts')
    paths += [fd/f'Noto{family}CJKkr-{weight}.otf'for family in ['Serif','Sans']for weight in ['Regular','Bold']]
    paths += [Path('D:/CodexBuilds/Hasla-publish-20261031/tools/pdf_memory_gate.py')]
    paths=sorted(set(p.resolve()for p in paths));assert all(p.is_file()for p in paths)
    result=dict(year=2019,pages=60,source=str(g.SOURCE),source_sha256=g.SOURCE_SHA,created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        files=[dict(path=str(p),sha256=sha(p),bytes=p.stat().st_size)for p in paths],
        policy='Same exact production code, original source, 60 plans/overrides, Korean full-font programs and source-bound semantic/scope reviews for all final pages. Source outlined/raster labels have separately documented inferred face/size; no invented source font metadata. Native Latin/math remains source fonts/GIDs/programs, original point sizes and baseline tolerances. No assembly or publication by this child.')
    write(F,result);print(json.dumps(dict(frozen=str(F),sha256=sha(F),files=len(paths))))
def verify_inputs():
    q=json.loads(F.read_text('utf8'));assert q['year']==2019 and q['source_sha256']==g.SOURCE_SHA
    errors=[e['path']for e in q['files']if not Path(e['path']).is_file()or sha(e['path'])!=e['sha256']]
    assert not errors,dict(changed_frozen_inputs=errors)
    g.assert_protected_2024();return q
def verify_pages():
    freeze=verify_inputs();start=datetime.datetime.fromisoformat(freeze['created_utc']).timestamp();rows=[];failures=[]
    for n in range(1,61):
        try:
            p=g.PROOFS/f'page{n:02}.pdf';g.assert_output(p,n)
            paths={s:g.PROOFS/f'page{n:02}{s}'for s in ['.pdf','.layout.json','.effective-plan.json','.png','.render.json','.inter-row-audit.json','.underline-style-audit.json']}
            assert all(v.is_file()for v in paths.values()),'Missing final artifact'
            diag=B/f'page{n:02}.diagnostic.json';assert diag.stat().st_mtime>=start,'Pre-freeze diagnostic'
            d=json.loads(diag.read_text('utf8'));q=json.loads(paths['.layout.json'].read_text('utf8'));r=json.loads(paths['.render.json'].read_text('utf8'))
            assert d['passed'] and q['page']==n and q['source_sha256']==g.SOURCE_SHA
            assert sha(p)==q['output_sha256']==d['output_sha256']==r['proof_sha256']
            assert r['png_sha256']==sha(paths['.png']) and r['layout_sha256']==sha(paths['.layout.json'])
            assert q['composer_sha256']==sha(B/'natural_plan_compose_icho2019.py') and q['native_motion_engine_sha256']==sha(B/'engine/latex_native_motion.py')
            assert q['plan_sha256']==sha(g.PLANS/f'page{n:02}.ko.json') and q['overrides_sha256']==sha(B/f'page{n:02}.overrides.json')
            assert q['effective_plan_sha256']==sha(paths['.effective-plan.json'])
            assert all(sha(path)==q['new_font_file_sha256'][role]for role,path in q['new_font_paths'].items())
            for suffix in ['.inter-row-audit.json','.underline-style-audit.json']:
                a=json.loads(paths[suffix].read_text('utf8'));assert a['passed'] and a['proof_sha256']==sha(p)
            for suffix in ['.graphic-label-geometry.json','.caption-center-audit.json','.template-geometry.json']:
                optional=g.PROOFS/f'page{n:02}{suffix}'
                if optional.exists():
                    a=json.loads(optional.read_text('utf8'));assert a['passed'] and a['proof_sha256']==sha(p),(suffix,'stale auxiliary audit');paths[suffix]=optional
            assert q['actual_prose_underline_protected_native_ink_contact_pixels']==0
            rows.append(dict(page=n,passed=True,artifacts=[dict(path=str(v),sha256=sha(v),bytes=v.stat().st_size)for v in paths.values()]+[dict(path=str(diag),sha256=sha(diag),bytes=diag.stat().st_size)]))
        except Exception as exc:failures.append(dict(page=n,error=str(exc)))
    result=dict(year=2019,source_sha256=g.SOURCE_SHA,freeze_path=str(F),freeze_sha256=sha(F),passed=len(rows)==60 and not failures,verified_pages=len(rows),rows=rows,failures=failures,visual_review_required_separately=True)
    write(B/'final-60-page-proof-verification.json',result);print(json.dumps(dict(passed=result['passed'],verified_pages=len(rows),failures=failures),ensure_ascii=False));return result['passed']
if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('operation',choices=['freeze','inputs','pages']);op=a.parse_args().operation
    if op=='freeze':freeze()
    elif op=='inputs':verify_inputs();print('Frozen 2019 inputs unchanged.')
    else:sys.exit(0 if verify_pages()else 1)

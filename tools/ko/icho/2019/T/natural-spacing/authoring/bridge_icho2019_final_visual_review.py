"""Normalize the pinned human review schema; do not create new human approvals."""
from pathlib import Path
import hashlib,json

BASE=Path(__file__).resolve().parents[1]
ENG=BASE/'historical/icho/composer-2019'
PROOFS=BASE/'proofs/icho/2019-final'
OUT=BASE/'staged/icho/review-2019-r2/visual-review-normalized.json'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
read=lambda p:json.loads(Path(p).read_text('utf8'))

def main():
    ready_path=ENG/'READY-for-root-assembly-r2.json'
    assert sha(ready_path)=='e7ac28136d66573a9674322876b08458ef0165dcf0e3aab2a682cf48665b6737'
    ready=read(ready_path)
    assert ready['status']=='READY_FOR_ROOT_ASSEMBLY' and ready['pages']==60
    assert [p['page'] for p in ready['page_artifacts']]==list(range(1,61))
    for pin in [ready['source']]+ready['evidence']+[a for p in ready['page_artifacts'] for a in p['artifacts']]:
        assert sha(pin['path'])==pin['sha256'],pin['path']
        assert Path(pin['path']).stat().st_size==pin['bytes']
    original=ENG/'final-r2-visual-review.json'
    assert sha(original)=='e9bfa61f777c3d072cb02f9de3e502831d696dcf7391857af21ee465588063e7'
    visual=read(original)
    assert visual['passed'] is True and visual['source_sha256']==ready['source']['sha256']
    assert visual['reviewed_pages']==60 and not visual['remaining_pages']
    assert [r['page'] for r in visual['pages']]==list(range(1,61))
    rows=[]
    for r in visual['pages']:
        n=r['page'];stem=PROOFS/f'page{n:02}'
        q=read(stem.with_suffix('.layout.json'))
        assert r['passed'] is True
        for field,path in [('pdf',stem.with_suffix('.pdf')),('png',stem.with_suffix('.png')),
                ('layout',stem.with_suffix('.layout.json')),('render',stem.with_suffix('.render.json')),
                ('diagnostic',ENG/f'page{n:02}.diagnostic.json')]:
            assert sha(path)==r[field+'_sha256'],(n,field)
        human_path=Path(r['human_review_path'])
        human_sha=r.get('human_review_sha256')
        if human_sha is None:
            human_sha=next(p['sha256'] for p in ready['evidence'] if Path(p['path']).resolve()==human_path.resolve())
            matches=[p for p in read(human_path)['pages'] if p['page']==n]
            assert len(matches)==1 and matches[0]['passed'] is True
            assert all(matches[0][k]==r[k] for k in ('pdf_sha256','png_sha256','layout_sha256'))
        assert sha(human_path)==human_sha
        assert q['output_sha256']==r['pdf_sha256'] and q['source_sha256']==visual['source_sha256']
        assert sha(q['effective_plan_path'])==q['effective_plan_sha256']
        assert sha(q['composer_path'])==q['composer_sha256']
        rows.append(dict(r,reviewed=True,human_review_sha256=human_sha,proof_sha256=r['pdf_sha256'],
            effective_plan_sha256=q['effective_plan_sha256'],composer_sha256=q['composer_sha256']))
    result=dict(schema='normalized-pinned-human-visual-review-v1',source_sha256=visual['source_sha256'],
        original_review=dict(path=str(original),sha256=sha(original)),
        ready=dict(path=str(ready_path),sha256=sha(ready_path)),
        normalizer=dict(path=str(Path(__file__).resolve()),sha256=sha(__file__)),
        scope='Schema bridge from exact final human review and PNG bindings. Reviewer identities and read/rebind methods are preserved. Root normalization does not claim a new independent reading of all pages.',
        pages=rows)
    OUT.parent.mkdir(parents=True,exist_ok=True)
    encoded=(json.dumps(result,ensure_ascii=False,indent=2)+'\n').encode('utf8')
    if OUT.exists():assert OUT.read_bytes()==encoded,'Do not overwrite a different normalized review'
    else:OUT.write_bytes(encoded)
    print(json.dumps(dict(status='PASS',pages=len(rows),path=str(OUT),sha256=sha(OUT))))

if __name__=='__main__':main()

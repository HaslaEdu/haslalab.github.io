"""Assemble reviewed original-style proofs without rebuilding their operators."""
from pathlib import Path
import argparse,hashlib,json,os
from collections import Counter
import pikepdf,pymupdf as fitz,numpy as np
import cpho_2013_original_build as b
import cpho_2013_original_qa as q
from pdf_white_raster_original_style import image_snapshot
from pdf_original_style_audit import glyphs
from pdf_hangul_visibility import audit as hangul

OUTPUT=Path(os.environ.get('HASLA_CPHO2013_OUTPUT',
    'D:/CodexBuilds/Hasla-original-style-20261031/cpho2013'if Path('D:/CodexBuilds').exists()else str(b.BASE)))

def recorded_path(path):
    path=Path(path)
    return str(path.relative_to(b.ROOT)).replace('\\','/')if path.is_relative_to(b.ROOT)else str(path).replace('\\','/')

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def render(page):
    p=page.get_pixmap(matrix=fitz.Matrix(4,4),colorspace=fitz.csRGB,alpha=False)
    return np.frombuffer(p.samples,np.uint8).reshape(p.height,p.width,3)

def ready(kind,language):
    pages=[1,2,3]if kind=='T'else list(range(4,15))
    reviewed=json.loads((b.AUTHOR/f'visual-review-{kind}.json').read_text('utf8'))
    poppler=json.loads((b.AUTHOR/f'qa-poppler-{kind}.json').read_text('utf8'))
    if not poppler['passed']:raise ValueError('Independent second-renderer checks failed')
    proofs=[];source_audits=[]
    for number in pages:
        proof=b.BASE/language/f'page{number:02}.pdf';qa=json.loads(proof.with_suffix('.qa.json').read_text('utf8'))
        if not qa['passed']or qa['sha256']!=sha(proof)or qa['authoring_sha256']!=b.authoring_hashes(number,language):
            raise ValueError('Proof or source audit is stale')
        record=next((r for r in reviewed['pages']if r['source_page']==number and r['language']==language),None)
        if not record or record.get('reviewed')is not True or record['proof_sha256']!=sha(proof):raise ValueError('Current proof lacks visual review')
        second=next(r for r in poppler['pages']if r['source_page']==number and r['language']==language)
        if not second['passed']or second['proof_sha256']!=sha(proof):raise ValueError('Poppler audit predates proof')
        proofs.append(proof);source_audits.append(qa)
    staging=OUTPUT/'joined-temp';staging.mkdir(parents=True,exist_ok=True)
    name=f'CPhO_2013_{kind}_{language.upper()}.pdf';joined=staging/name
    with pikepdf.new()as target:
        for path in proofs:
            with pikepdf.open(path)as one:target.pages.append(one.pages[0])
        target.save(joined,compress_streams=False)
    identity=[]
    with fitz.open(joined)as full,pikepdf.open(joined)as full_raw:
        if len(full)!=len(pages):raise ValueError('Joined page count differs')
        for index,path in enumerate(proofs):
            with fitz.open(path)as one,pikepdf.open(path)as one_raw:
                pix=int(np.any(render(one[0])!=render(full[index]),axis=2).sum())
                metadata=Counter(q.exact(g)for g in glyphs(one[0]))==Counter(q.exact(g)for g in glyphs(full[index]))
                images=image_snapshot(one,one[0])==image_snapshot(full,full[index])
                fonts=q.original_font_programs(one,one[0])==q.original_font_programs(full,full[index])
                group=str(one_raw.pages[0].obj.get('/Group'))==str(full_raw.pages[index].obj.get('/Group'))
                ascii=q.new_ascii_widths(joined,index)
                row=dict(source_page=pages[index],joined_page=index+1,reviewed_proof_sha256=sha(path),
                    joined_vs_reviewed_proof_changed_pixels_4x=pix,glyph_metadata_identical=metadata,
                    original_image_and_smask_programs_identical=images,original_font_programs_identical=fonts,
                    page_group_identical=group,new_ascii_widths=ascii)
                row['passed']=pix==0 and all([metadata,images,fonts,group])and not ascii['nonpositive_or_missing_widths']
                identity.append(row)
    visibility=hangul(joined)if language=='ko'else None
    passed=all(r['passed']for r in identity)and not(visibility and visibility['flagged_components'])
    if not passed:raise ValueError('Final assembly changed reviewed output')
    canonical=OUTPUT/'editions'/name;canonical.parent.mkdir(parents=True,exist_ok=True)
    if canonical.exists():
        versions=canonical.parent/'versions';versions.mkdir(exist_ok=True)
        backup=versions/(canonical.stem+'-'+sha(canonical)[:16]+'.pdf')
        if not backup.resolve().is_relative_to(canonical.parent.resolve()):raise ValueError('Version path outside canonical scope')
        if backup.exists():raise ValueError('A version backup already exists; review before replacement')
        canonical.rename(backup)
    os.replace(joined,canonical)
    report=dict(status='READY',kind=kind,language=language,source_sha256=b.source.SOURCE_SHA,
        source_pages=pages,file=name,path=recorded_path(canonical),pages=len(pages),
        bytes=canonical.stat().st_size,sha256=sha(canonical),all_source_proof_audits_passed=True,
        source_audits=source_audits,joined_vs_reviewed_proofs=identity,hangul_visibility=visibility,
        poppler_audit=f'tools/ko/cpho/2013/original/qa-poppler-{kind}.json',
        visual_review=f'tools/ko/cpho/2013/original/visual-review-{kind}.json',added_editorial_notes=0,
        note='Original wrong footer totals and source equation-image order are retained; see provenance.json.')
    (b.AUTHOR/f'qa-{kind}-{language}.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),'utf8')
    print(name,report['bytes'],report['sha256'],flush=True)
    return report

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--kind',choices=['T','TS'],required=True);p.add_argument('--lang',choices=['ko','en']);a=p.parse_args()
    results=[ready(a.kind,l)for l in([a.lang]if a.lang else['ko','en'])]
    inventory=dict(year=2013,status='READY',scope='problems'if a.kind=='T'else'solutions',
        source='tmp/original-style-sources/CPhO_2013_Chinese_original.pdf',source_sha256=b.source.SOURCE_SHA,
        source_pages=results[0]['source_pages'],files=[{k:r[k]for k in['file','path','language','pages','bytes','sha256']}|dict(qa=f"tools/ko/cpho/2013/original/qa-{a.kind}-{r['language']}.json")for r in results],
        source_provenance='tools/ko/cpho/2013/original/provenance.json',
        source_page_split={'T':[1,2,3],'TS':list(range(4,15))},
        translation_scope_notes='Native prose at exact source size/baseline/stroke; bitmap prose and labels use separately recorded measured typography and original image programs. No equation retypesetting.')
    (b.ROOT/f'tools/cpho_2013_original_{a.kind}_inventory.json').write_text(json.dumps(inventory,ensure_ascii=False,indent=2),'utf8')

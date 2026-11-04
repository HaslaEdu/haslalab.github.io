"""Actual original-only and new-glyph-only controls; coincident black ink fails."""
from pathlib import Path
import hashlib,json,shutil
import pikepdf,pymupdf as f,numpy as np
from pdf_original_text_ops import glyph_key
from pdf_moved_native_ink import audit_moved_native_ink
B=Path(__file__).resolve().parents[1];S=B/'source/CPhO_2008_original_combined_ZH.pdf'
SHA='4e076fb9234683d028792190bcec56f12de72890da6c0e44ddf0e9146013459d'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
read=lambda p:json.loads(Path(p).read_text('utf8'))
def chunks(page):return list(page.Contents)if isinstance(page.Contents,pikepdf.Array)else[page.Contents]
def pixels(path):
    with f.open(path)as doc:
        pix=doc[0].get_pixmap(matrix=f.Matrix(4,4),colorspace=f.csRGB,alpha=False)
        return np.frombuffer(pix.samples,np.uint8).reshape(pix.height,pix.width,3).copy()
def archive_existing(path):
    if not path.exists():return
    history=B/'history/previous-kept-ink-audits';history.mkdir(exist_ok=True)
    dest=history/(path.stem+'-'+sha(path)+path.suffix)
    if not dest.exists():shutil.copy2(path,dest)
    assert sha(path)==sha(dest)
def audit(n,lang,final_override=None,write_report=True):
    target=Path(final_override)if final_override else B/f'proofs/{lang}/page{n:02}.pdf'
    assert sha(S)==SHA;c=read(B/f'proofs/{lang}/page{n:02}.composition.json')
    plan=Path(c['actual_immutable_producing_plan']);assert sha(plan)==c['plan_sha256'];q=read(plan)
    inv=read(B/f'inspection/page{n:02}-original-native-programs.json')
    folder=B/'evidence/kept-original-and-new-glyph-controls';folder.mkdir(exist_ok=True)
    base=f'page{n:02}-{lang}-{sha(target)[:16]}'
    kept=folder/(base+'-actual-kept-original.pdf');new=folder/(base+'-actual-new-glyphs.pdf')
    allowed={'/C08Translated'+face for face in c['fonts']}
    if n==4:allowed.add('/C08BitmapLabelSerifBold')
    errors=[]
    with pikepdf.open(S)as src,pikepdf.open(target)as doc,pikepdf.open(B/f'proofs/{lang}/page{n:02}.native-control.pdf')as initial:
        expected_fonts={str(alias)for alias in src.pages[n-1].Resources.Font}|allowed
        actual_fonts={str(alias)for alias in doc.pages[0].Resources.Font}
        if expected_fonts!=actual_fonts:errors.append(dict(error='Actual final font-resource closure differs',expected=sorted(expected_fonts),actual=sorted(actual_fonts)))
        selected=[];retained=[]
        for index,stream in enumerate(chunks(doc.pages[0])):
            raw=stream.read_bytes()
            is_new=any(alias.encode()in raw for alias in allowed)
            (selected if is_new else retained).append(index)
        prior=chunks(initial.pages[0]);current=chunks(doc.pages[0]);initial_programs=[hashlib.sha256(s.read_bytes()).hexdigest()for s in prior]
        kept_programs=[hashlib.sha256(current[i].read_bytes()).hexdigest()for i in retained]
        # MuPDF encloses the unchanged imported source stream in two literal
        # save/restore streams before appending the first translated glyph.
        source_count=len(initial_programs)
        wrapper_exact=(current[retained[0]].read_bytes()==b'q\n' and current[retained[source_count+1]].read_bytes()==b'\nQ\n')
        if not wrapper_exact or kept_programs[1:source_count+1]!=initial_programs:errors.append('The actual original native content and literal save/restore prefix differ from the initial source-native control')
        if len(kept_programs)!=source_count+2+(2 if n==4 else 0):errors.append('Unexpected nonlanguage content added outside the literal save/restore wrapper and two reviewed original bitmap word covers')
        for output,indices in [(kept,retained),(new,selected)]:
            archive_existing(output)
            with pikepdf.Pdf.new()as out:
                out.pages.append(doc.pages[0]);page=out.pages[0];all_chunks=chunks(page);page.Contents=pikepdf.Array([all_chunks[i]for i in indices]);out.save(output,compress_streams=False)
    erased={glyph_key(g)for row in q['rows']for g in row['erase_glyphs']}
    native=[g for g in inv['actual_original_glyphs']if glyph_key(g)not in erased and g['c'].strip()]
    original_ink=audit_moved_native_ink(S,n,kept,shifts=c['native_shifts'],erased_glyphs=c['erased_original_language_glyphs'],protected_glyphs=native)
    aa=pixels(kept);bb=pixels(new);overlap=np.any(aa!=255,2)&np.any(bb!=255,2)
    yy,xx=np.where(overlap);examples=[dict(point=[float(x/4),float(y/4)],kept_original_RGB=aa[y,x].tolist(),new_glyph_RGB=bb[y,x].tolist())for y,x in zip(yy[:60],xx[:60])]
    r=dict(original_source_sha256=SHA,source_page=n,language=lang,proof_sha256=sha(target),actual_producing_plan_sha256=sha(plan),
        source_and_known_new_font_resource_closure=sorted(expected_fonts),errors=errors,initial_original_native_program_sha256s=initial_programs,
        actual_kept_original_control_path=str(kept),actual_kept_original_control_sha256=sha(kept),actual_new_glyphs_only_control_path=str(new),actual_new_glyphs_only_control_sha256=sha(new),
        actual_original_native_ink_without_any_new_language_glyph=original_ink,kept_original_vs_new_glyph_any_nonwhite_RGB_overlap_pixels=int(overlap.sum()),overlap_examples=examples,
        passed=not errors and original_ink['passed']and not overlap.any())
    if write_report:
        report=target.with_suffix('.kept-ink-collision.json');archive_existing(report)
        report.write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n','utf8')
    print('C08_KEPT_ORIGINAL_VS_NEW_GLYPH_INK',n,lang,r['passed'],'overlap',r['kept_original_vs_new_glyph_any_nonwhite_RGB_overlap_pixels'],'errors',len(errors),flush=True)
    return r

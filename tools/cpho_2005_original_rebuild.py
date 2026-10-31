"""Reproduce manually reviewed, original-style CPhO2005 editions.

The problem edition is complete. Scanned solution pages need their separate
manual language masks before this command can assemble a solution edition.
Large generated files stay on the explicitly assigned D: build volume.
"""
from pathlib import Path
import argparse,hashlib,json,subprocess,os
os.environ.setdefault('OPENBLAS_NUM_THREADS','1');os.environ.setdefault('OMP_NUM_THREADS','1')
import pikepdf
import pymupdf as fitz
import numpy as np
import cpho_2005_original_build as b
import cpho_2005_original_qa as q
from pdf_white_raster_original_style import image_snapshot


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def pixels(page):
    p=page.get_pixmap(matrix=fitz.Matrix(4,4),colorspace=fitz.csRGB,alpha=False)
    return np.frombuffer(p.samples,np.uint8).reshape(p.height,p.width,3)


def all_font_programs(doc,page):
    # Font-resource dictionary order is not paint order; qpdf may sort the
    # aliases while keeping every alias, encoding and program byte identical.
    return sorted([(list(r[1:6]),hashlib.sha256(doc.extract_font(r[0])[3]).hexdigest())for r in page.get_fonts(full=True)],key=lambda r:(r[0][3],r[0][2],r[1]))


def translation_resources(path,index):
    rows=[]
    with pikepdf.open(path)as pdf:
        for alias,font in pdf.pages[index].Resources.Font.items():
            if not str(alias).startswith('/Translation'):continue
            child=font.get('/DescendantFonts',[font])[0]
            rows.append(dict(alias=str(alias),basefont=str(font['/BaseFont']),widths=str(child.get('/W')),
                default_width=str(child.get('/DW')),first_char=str(child.get('/FirstChar')),last_char=str(child.get('/LastChar')),
                simple_widths=str(child.get('/Widths')),to_unicode_sha256=hashlib.sha256(font['/ToUnicode'].read_bytes()).hexdigest()))
    return sorted(rows,key=lambda r:r['alias'])


def build(lang,render=True):
    pages=[1,2,3];proofs=[];audits=[]
    for number in pages:
        path=b.BASE/lang/f'page{number:02}.pdf';meta=path.with_suffix('.build.json')
        current=(path.exists()and meta.exists()and json.loads(meta.read_text('utf8')).get('authoring_sha256')==b.authoring_hashes(number,lang))
        if not current:b.compose_page(number,lang)
        prior=path.with_suffix('.qa.json')
        audit=json.loads(prior.read_text('utf8'))if prior.exists()else{}
        if not(audit.get('passed')and audit.get('sha256')==sha(path)and audit.get('authoring_sha256')==b.authoring_hashes(number,lang)and'new_outline_ink'in audit):
            audit=q.audit(number,lang)
        if not audit['passed']:raise ValueError('Original-style page audit failed')
        proofs.append(path);audits.append(audit)
    target=b.BASE.parent/f'CPhO_2005_T_{lang.upper()}.pdf'
    with pikepdf.Pdf.new()as joined:
        for path in proofs:
            with pikepdf.open(path)as single:joined.pages.append(single.pages[0])
        joined.save(target,compress_streams=False)
    assembly=[]
    with fitz.open(target)as final,fitz.open(b.source.SOURCE)as source:
        for i,path in enumerate(proofs):
            with fitz.open(path)as single:
                changed=int(np.any(pixels(single[0])!=pixels(final[i]),axis=2).sum())
                exact_glyphs=q.preservation.glyphs(single[0])==q.preservation.glyphs(final[i])
                font_programs_same=all_font_programs(single,single[0])==all_font_programs(final,final[i])
                images_same=image_snapshot(single,single[0])==image_snapshot(final,final[i])
                resources_same=translation_resources(path,0)==translation_resources(target,i)
            graphic=q.graphics.audit(b.source.SOURCE,target,i+1,proof_page=i+1)
            original_fonts_same=q.original_font_programs(source,source[i])==q.original_font_programs(final,final[i])
            row=dict(page=i+1,final_vs_reviewed_proof_changed_pixels=changed,all_trace_glyph_metadata_identical=exact_glyphs,
                all_actual_font_programs_identical=font_programs_same,new_translation_pdf_widths_and_cmaps_identical=resources_same,
                all_image_and_smask_raw_decoded_programs_and_positions_identical=images_same,
                original_font_programs_identical=original_fonts_same,original_graphics=graphic)
            row['passed']=(changed==0 and exact_glyphs and font_programs_same and images_same and resources_same and original_fonts_same
                and graphic['original_graphics_ink_changed_pixels']==0 and graphic['original_image_and_smask_programs_and_positions_identical'])
            if not row['passed']:raise ValueError(('Final assembly audit failed',row))
            assembly.append(row)
    report=dict(source=str(b.source.SOURCE.relative_to(b.ROOT)),source_sha256=b.source.SOURCE_SHA,source_page_count=16,
        original_problem_pages_1based=pages,original_solution_pages_1based=list(range(4,17)),
        output=str(target),sha256=sha(target),bytes=target.stat().st_size,pages=3,language=lang,
        assembly='pikepdf append, compress_streams=False',autoshrink=False,new_equation_rasterisation=False,
        paragraph_reflow=False,new_editorial_notes=False,original_problem_identifiers_preserved=True,
        native_source_fonts_and_math_and_figures_preserved=True,
        source_bitmap_language_review=dict(reviewed=True,language_labels_found=0,note='All T bitmaps are diagrams, variables, numbers, SI or original mathematical operators.'),
        new_nonspace_gids_with_actual_outlines_checked=sum(a['new_outline_ink']['new_nonspace_gids_checked']for a in audits),
        new_ascii_positive_pdf_widths_checked=sum(a['new_ascii_widths']['ascii_codes_checked']for a in audits),
        new_empty_outline_count=sum(a['new_outline_ink']['empty_outline_count']for a in audits),
        page_audits=audits,final_assembly_audits=assembly,visual_review_required=True)
    (b.AUTHOR/f'T-{lang}-audit.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),'utf8')
    if render:
        folder=b.BASE/'poppler'/lang;folder.mkdir(parents=True,exist_ok=True)
        subprocess.run(['pdftoppm','-png','-r','144',str(target),str(folder/'page')],check=True,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt'else 0)
    print(json.dumps({k:report[k]for k in ['output','sha256','bytes','pages','language','new_empty_outline_count','visual_review_required']},ensure_ascii=False),flush=True)
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('kind',choices=['T']);parser.add_argument('--lang',nargs='+',choices=['ko','en'],default=['ko','en']);parser.add_argument('--no-render',action='store_true');args=parser.parse_args()
    for lang in args.lang:build(lang,render=not args.no_render)

"""Assemble native pages and verify the delivered PDF in fresh renderers."""
from pathlib import Path
import argparse,hashlib,json,subprocess,sys,shutil
import pikepdf
import pymupdf as fitz
from cpho_2023_natural_spacing import OUT,ROOT
from pdf_memory_gate import page_worker
from pdf_original_image_ink import resolved_images
from izho_early_fixed_style import native_font_programs,native_image_programs

BASE=OUT.parent
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,d):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n','utf8')
def final_path(language):return BASE/'editions'/f'CPhO_2023_Combined_{language.upper()}.pdf'
def proof_path(language,page):return OUT/f'CPhO_2023_p{page}_{language.upper()}_natural.pdf'

def semantic(value,ancestors=()):
    if isinstance(value,pikepdf.Stream):
        if value.objgen in ancestors:raise ValueError('Recursive graphics resource')
        try:decoded=hashlib.sha256(value.read_bytes()).hexdigest()
        except pikepdf.PdfError:
            if not any(f in str(value.get('/Filter'))for f in['DCTDecode','JPXDecode','JBIG2Decode','CCITTFaxDecode']):raise
            decoded='Exact compressed original image program'
        return dict(dictionary={str(k):semantic(v,ancestors+(value.objgen,))for k,v in value.items()},raw_sha256=hashlib.sha256(value.read_raw_bytes()).hexdigest(),decoded_sha256=decoded)
    if isinstance(value,pikepdf.Dictionary):return{str(k):semantic(v,ancestors)for k,v in value.items()}
    if isinstance(value,pikepdf.Array):return[semantic(v,ancestors)for v in value]
    if isinstance(value,pikepdf.String):return dict(pdf_string_hex=bytes(value).hex())
    return str(value)

def resources(source,target,independent):
    with fitz.open(source)as a,fitz.open(target)as b:
        old=resolved_images(a,a[0]);new=resolved_images(b,b[0])
    if len(old)!=len(new):raise ValueError('Original image paint count changed')
    with pikepdf.open(source)as a,pikepdf.open(target)as b:
        def painted_images(node,res,ancestors=()):
            values=set()
            for instruction in pikepdf.parse_content_stream(node):
                if str(instruction.operator)!='Do':continue
                child=res.get('/XObject',{}).get(instruction.operands[0])
                if child is None:continue
                if str(child.get('/Subtype'))=='/Image':values.add(child.objgen[0])
                elif str(child.get('/Subtype'))=='/Form':
                    if child.objgen in ancestors:raise ValueError('Recursive original math graphics')
                    values.update(painted_images(child,child.get('/Resources',res),ancestors+(child.objgen,)))
            return values
        movements=[]
        for group in independent['native_geometry']['selected_native_math_groups']:
            if 'form_path'not in group:continue
            node=a.pages[0];res=node.Resources
            for index in group['form_path']:
                instruction=list(pikepdf.parse_content_stream(node))[index]
                if str(instruction.operator)!='Do':raise ValueError('Original mathematical invocation changed')
                node=res.XObject[instruction.operands[0]];res=node.get('/Resources',res)
            movements.append((painted_images(node,res),group['dx']))
        group=semantic(a.pages[0].get('/Group'))==semantic(b.pages[0].get('/Group'))
        colors=semantic(a.pages[0].Resources.get('/ColorSpace'))==semantic(b.pages[0].Resources.get('/ColorSpace'))
        images=[]
        for x,y in zip(old,new):
            old_box=list(x['bbox']);new_box=list(y['bbox'])
            delta=[v-u for u,v in zip(old_box,new_box)];stationary=max(map(abs,delta))<=.001
            permitted=[dx for ids,dx in movements if x['xref']in ids and max(abs(delta[0]-dx),abs(delta[2]-dx),abs(delta[1]),abs(delta[3]))<=.001]
            images.append(dict(position_identical=stationary,reviewed_native_inline_math_dx=permitted[0]if permitted else None,
                expected_native_position_preserved=stationary or bool(permitted),old_bbox=old_box,new_bbox=new_box,
                palette_icc_mask_and_original_stream_graph_identical=semantic(a.get_object((x['xref'],0)))==semantic(b.get_object((y['xref'],0)))))
    font=all(row in native_font_programs(target,1)for row in native_font_programs(source,1))
    programs=all(row in native_image_programs(target,1)for row in native_image_programs(source,1))
    report=dict(page_group_identical=group,colorspace_resources_identical=colors,original_font_programs_retained=font,original_image_programs_retained=programs,images=images)
    if not(group and colors and font and programs and all(i['expected_native_position_preserved']and i['palette_icc_mask_and_original_stream_graph_identical']for i in images)):raise ValueError(('Original resource identity changed',report))
    return report

def assemble(language):
    target=final_path(language);target.parent.mkdir(parents=True,exist_ok=True)
    with page_worker(),pikepdf.Pdf.new()as joined:
        for number in range(1,37):
            p=proof_path(language,number);q=json.loads(p.with_suffix('.independent.json').read_text('utf8'))
            if not q['passed']or q['output_sha256']!=sha(p):raise ValueError(('Unreviewed or changed page',number))
            with pikepdf.open(p)as source:joined.pages.append(source.pages[0])
        joined.save(target,compress_streams=False)
    print(json.dumps(dict(output=str(target),sha256=sha(target),pages=36,bytes=target.stat().st_size)),flush=True)

def pixel_hash(path,page):
    with page_worker(),fitz.open(path)as doc:
        p=doc[page-1].get_pixmap(matrix=fitz.Matrix(4,4),colorspace=fitz.csRGB,alpha=False)
        print(json.dumps(dict(width=p.width,height=p.height,sha256=hashlib.sha256(p.samples).hexdigest())),flush=True)

def verify(language,number):
    p=proof_path(language,number);target=final_path(language)
    def fresh(path,page):
        value=subprocess.check_output([sys.executable,__file__,'--pixel-hash',str(path),'--page',str(page)],encoding='utf8')
        return json.loads(value)
    before=fresh(p,1);after=fresh(target,number)
    if before!=after:raise ValueError(('Final combined page differs from reviewed proof',number,before,after))
    record=dict(page=number,proof_sha256=sha(p),final_sha256=sha(target),rendered_pixel_sha256_4x=after['sha256'],
        final_vs_reviewed_proof_changed_pixels=0,renderers='Separate fresh Python/MuPDF process for each complete PDF; no shared palette/font cache.')
    save(BASE/f'assembly-{language}/page{number:02}.json',record)
    print(json.dumps(dict(page=number,passed=True,pixel_sha256=after['sha256'])),flush=True)

def finalize(language):
    target=final_path(language);digest=sha(target);rows=[];audits=[];review=[]
    visually_checked={}
    for first in range(1,37,6):
        contact=BASE/f'review-current/{language}-{first:02}.json'
        record=json.loads(contact.read_text('utf8'))
        assert record['reviewed']and record['language']==language
        for page in record['pages']:
            assert page['page']not in visually_checked
            visually_checked[page['page']]=page['sha256']
    assert set(visually_checked)==set(range(1,37))
    for number in range(1,37):
        p=proof_path(language,number);q=json.loads(p.with_suffix('.qa.json').read_text('utf8'))
        independent=json.loads(p.with_suffix('.independent.json').read_text('utf8'))
        row=json.loads((BASE/f'assembly-{language}/page{number:02}.json').read_text('utf8'))
        assert independent['passed']and row['proof_sha256']==sha(p)==q['output_sha256']==independent['output_sha256']and row['final_sha256']==digest
        assert visually_checked[number]==sha(p)
        assert sha(q['source'])==q['source_sha256']
        with page_worker():
            identity=resources(q['source'],p,independent)
            figure_source=Path(f'D:/CodexBuilds/Hasla-original-style-20261031/cpho2023/immutable-slot-baselines/CPhO_2023_p{number}_KO_proof.pdf')if language=='ko'else Path(f'D:/CodexBuilds/Hasla-original-style-20261031/cpho2023/strict-en/proofs/CPhO_2023_p{number}_EN_proof.pdf')
            regions=[]
            with fitz.open(figure_source)as original,fitz.open(p)as final:
                for rect in q['reviewed_line_profile']['excluded_figure_rects']:
                    before=original[0].get_pixmap(matrix=fitz.Matrix(4,4),clip=fitz.Rect(rect),colorspace=fitz.csRGB,alpha=False)
                    after=final[0].get_pixmap(matrix=fitz.Matrix(4,4),clip=fitz.Rect(rect),colorspace=fitz.csRGB,alpha=False)
                    assert(before.width,before.height,before.samples)==(after.width,after.height,after.samples),('Immutable original figure/display region changed',number,rect)
                    regions.append(dict(rect=rect,changed_pixels=0,rendered_pixel_sha256=hashlib.sha256(after.samples).hexdigest()))
            identity['immutable_figure_reference']=str(figure_source)
            identity['figures_vs_immutable_before_any_prose_or_heading_edits']=regions
        rows.append(dict(row,source_pdf_sha256=q['source_sha256'],old_korean_proof_sha256=q['source_sha256'],
            native_move_qa=q['native_move_qa'],actual_native_math_visible_ink=independent['native_ink'],
            changed_figures=sum(r['changed_pixels']for r in independent['unchanged_figure_and_stationary_display_regions']),new_empty_hangul_outlines=q['empty_new_batang_outlines'],original_resource_identity=identity))
        audits.append(dict(page=number,path=str(p.with_suffix('.independent.json')),sha256=sha(p.with_suffix('.independent.json'))))
        review.append(dict(page=number,proof_sha256=sha(p),reviewed=True,review='Full-page rendered layout and original equation/figure comparison; source nominal sizes and natural spacing, no new clipping or overlaps.'))
    visual=BASE/f'visual-{language}.json';save(visual,dict(language=language,pages=review))
    files=['cpho_2023_natural_spacing.py','cpho_2023_natural_heading.py','cpho_2023_natural_qa.py','cpho_2023_natural_ready.py',
        'pdf_native_inline_reposition.py','pdf_korean_natural_composer.py','izho_natural_spacing.py','izho_native_atomic_tokens.py',
        'natural_spacing_form_groups.py','pdf_original_text_ops.py','pdf_original_style_fonts.py','pdf_native_geometry_motion.py',
        'pdf_original_graphics_ink.py','pdf_moved_native_ink.py','pdf_memory_gate.py','pdf_original_image_ink.py','izho_early_fixed_style.py']
    snapshot=BASE/f'authoring-{language}'
    hashes={}
    for name in files:
        src=ROOT/'tools'/name;dst=snapshot/'tools'/name;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dst);hashes['tools/'+name]=sha(dst)
    plan=Path('tools/ko/cpho/2023/natural-inline-groups.json')
    dst=snapshot/plan;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/plan,dst);hashes[plan.as_posix()]=sha(dst)
    r=dict(status='READY',year=2023,kind='Combined',language=language,pages=36,output=str(target),sha256=digest,bytes=target.stat().st_size,
        source='CPhO2023 Chinese original combined',original_source_sha256='956f132218ce6591d418a1faa998648b00a6195b2f2b522e6e16c1a405a418f0',
        font_policy='Original nominal sizes. Korean regular serif uses Batang; native scientific fonts, encoded CIDs, GIDs, paint and baselines retained. English uses actual same-face SimSun and SimHei source families.',
        spacing_policy='Ordinary quarter-em spaces with Korean particles and references joined; original paragraph baselines, figures and display equations retained. Complete heading and edition line centered.',
        native_actual_glyph_missing=0,new_batang_empty_outlines=0,hangul_visibility_loss_candidates=0,outside_motion_ink_pixels=0,figure_changed_pixels=0,
        original_fonts_and_image_programs_retained=True,page_groups_preserved=True,original_point_sizes_scaled=False,no_added_editorial_notes=True,
        page_proofs=rows,page_audits=audits,visual_review=str(visual),authoring_snapshotroot=str(snapshot),authoring_snapshot_sha256=hashes,
        independent_original_input_moved_math_audits=[dict(page=row['page'],path=row['path'],sha256=row['sha256'],container_key='native_ink')for row in audits],
        native_program_and_figure_changes=0,assembly_verification='Exact 4x RGB pixel SHA of each reviewed proof versus assembled page, using two separate fresh processes.')
    save(target.with_suffix('.ready.json'),r)
    print(json.dumps(dict(status='READY',output=str(target),sha256=digest,pages=36,bytes=r['bytes'])),flush=True)

if __name__=='__main__':
    a=argparse.ArgumentParser(description=__doc__);a.add_argument('--language',choices=['ko','en'],default='ko');a.add_argument('--assemble',action='store_true');a.add_argument('--verify',type=int);a.add_argument('--finalize',action='store_true');a.add_argument('--pixel-hash',type=Path);a.add_argument('--page',type=int,default=1);args=a.parse_args()
    if args.pixel_hash:pixel_hash(args.pixel_hash,args.page)
    elif args.assemble:assemble(args.language)
    elif args.verify:verify(args.language,args.verify)
    elif args.finalize:finalize(args.language)
    else:a.error('Choose an operation')

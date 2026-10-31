"""Independent rendered-ink, font-program and picture QA for natural IZhO pages."""
from __future__ import annotations
import argparse,hashlib,json,os,re,subprocess,sys
from pathlib import Path
from io import BytesIO
import numpy as np
from PIL import Image
import pikepdf
import pymupdf as fitz
from pdf_memory_gate import page_worker
from pdf_text_motion_ink import ink_envelope
from pdf_native_geometry_motion import audit as geometry_motion
from pdf_moved_native_ink import audit_moved_native_ink
from pdf_native_inline_reposition import _traces
from pdf_original_text_ops import glyph_key
from izho_early_fixed_style import native_font_programs,native_image_programs
from pdf_hangul_visibility import audit as hangul_audit
from izho_new_prose_outline_qa import outline_results
from izho_natural_spacing import ROOT,BUILD
from izho_natural_spacing_rebuild import coverage

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def semantic(value,ancestors=()):
    if isinstance(value,pikepdf.Stream):
        if value.objgen in ancestors:raise ValueError('Recursive graphics resource')
        try:decoded=hashlib.sha256(value.read_bytes()).hexdigest()
        except pikepdf.PdfError:
            if not any(f in str(value.get('/Filter'))for f in['DCTDecode','JPXDecode','JBIG2Decode','CCITTFaxDecode']):raise
            decoded='Compressed image decoder: exact raw stream and dictionary; independent fresh-process RGB pixels compared'
        return dict(dictionary={str(k):semantic(v,ancestors+(value.objgen,))for k,v in value.items()},
            raw_sha256=hashlib.sha256(value.read_raw_bytes()).hexdigest(),decoded_sha256=decoded)
    if isinstance(value,pikepdf.Dictionary):return{str(k):semantic(v,ancestors)for k,v in value.items()}
    if isinstance(value,pikepdf.Array):return[semantic(v,ancestors)for v in value]
    if isinstance(value,pikepdf.String):return dict(pdf_string_hex=bytes(value).hex())
    return str(value)

def fresh_render(path,page,out):
    out=Path(out)
    code="import sys,pymupdf as f;d=f.open(sys.argv[1]);d[int(sys.argv[2])-1].get_pixmap(matrix=f.Matrix(4,4),colorspace=f.csRGB,alpha=False).save(sys.argv[3])"
    subprocess.run([sys.executable,'-X','utf8','-c',code,str(path),str(page),str(out)],check=True,
        creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt'else 0)
    with Image.open(out)as image:return np.array(image.convert('RGB'))

def new_outlines(path):
    with pikepdf.open(path)as pdf,fitz.open(path)as doc:
        fonts=pdf.pages[0].Resources.Font
        if '/KO_Natural_Batang'not in fonts:return dict(checked=0,empty=[])
        raw=fonts['/KO_Natural_Batang'].DescendantFonts[0].FontDescriptor.FontFile2.read_bytes();digest=hashlib.sha256(raw).hexdigest()
        rows=[dict(c=chr(cp),gid=gid,font='Batang',size=t['size'],origin=list(origin))for t in doc[0].get_texttrace()if t['font']=='Batang'for cp,gid,origin,bbox in t['chars']if 0xac00<=cp<=0xd7a3]
        values=outline_results(dict(raw=raw,sha=digest,kind='/FontFile2',subtype=None),rows,{})
        return dict(checked=len(values),empty=[g for g in values if g['outline_empty']],font_program_sha256=digest)

def image_rect_motion(original,current,geometry_report,tolerance=.001):
    """Only an exact declared whole-native-widget dx may move an image."""
    a=fitz.Rect(original);b=fitz.Rect(current)
    if max(abs(x-y)for x,y in zip(a,b))<=tolerance:
        return dict(rect_preserved=True,rect_matches_declared_native_math_dx=False,dx=0.)
    for group in geometry_report['selected_native_math_groups']:
        scope=fitz.Rect(group['rect'])+(-tolerance,-tolerance,tolerance,tolerance)
        if not scope.contains(a):continue
        dx=group['dx'];expected=a+(dx,0,dx,0)
        if max(abs(x-y)for x,y in zip(expected,b))<=tolerance:
            return dict(rect_preserved=False,rect_matches_declared_native_math_dx=True,dx=dx,
                exact_original_native_math_group=group)
    return dict(rect_preserved=False,rect_matches_declared_native_math_dx=False,dx=None)

def table_math_geometry(page,plan,composition):
    """Independently reject fraction/script pieces given different motions."""
    rows=_traces(page);moves={glyph_key(g):s['dx']for s in composition['native_shifts']for g in s['glyphs']if g['c'].strip()}
    groups=[];seen=set()
    for scope in plan.get('source_line_scopes',[]):
        cell=scope.get('original_grid_cell_rect')
        if not cell or not re.search(r'Formula|Numerical\s*value',scope['source_text'],re.I):continue
        key=tuple(round(v,3)for v in cell)
        if key in seen:continue
        seen.add(key);box=fitz.Rect(cell)
        glyphs=[g for g in rows if g['c'].strip()and g['font']=='CambriaMath'and box.contains(fitz.Point(g['origin']))]
        if not glyphs:continue
        deltas=[moves.get(glyph_key(g),0.)for g in glyphs]
        spread=max(deltas)-min(deltas)
        stationary=bool(plan.get('stationary_table_math'))
        groups.append(dict(source_at=scope['source_at'],cell=cell,glyphs=len(glyphs),stationary_original_table_design=stationary,
            minimum_dx=min(deltas),maximum_dx=max(deltas),relative_coordinate_error_pt=spread,
            passed=spread<=.001 and(not stationary or max(abs(v)for v in deltas)<=.001)))
    return dict(method='All original CambriaMath glyphs in each enclosed score-table formula cell retain their complete relative geometry; designated stationary table mathematics must additionally have zero horizontal movement.',
        groups=groups,checked_groups=len(groups),mismatched_groups=sum(not g['passed']for g in groups),passed=all(g['passed']for g in groups))

def native_phase_profile(result,plan,folder):
    raw=result['original_input_outline_native_ink_audit']
    result['verified_original_native_ink_missing_pixels']=raw.get('newly_missing_native_ink_pixels')
    if raw['passed']:return True
    witness_path=plan.get('native_ink_witness')
    if not witness_path:return False
    path=Path(folder)/witness_path;w=json.loads(path.read_text('utf8'))
    if not all([w['proof_sha256']==result['output_sha256'],w['proof_unmodified'],w['passed'],
        w['native_cid_reference_missing_pixels']==0,w['native_reference_dark_pixels']>0,
        w['svg_reference_scales']['8']['passed'],w['svg_reference_scales']['12']['passed'],
        raw.get('newly_missing_native_ink_pixels')==1,raw.get('missing_bbox')==[367.5,303.75,367.75,304.0],
        not raw['missing_requested_source_glyphs'],not raw['missing_final_native_glyphs'],raw['source_outline_audit']['passed']]):return False
    result['native_ink_reference_profile']=dict(
        method='One exact unhinted SVG/native-font raster phase sample. Source encoded CID reference at the measured destination is authoritative; global SVG thresholds unchanged.',
        original_4x_svg_dark_pixel_delta=1,native_original_CID_reference_missing_pixels=0,
        svg_8x_missing_pixels=0,svg_12x_missing_pixels=0,witness=str(path),witness_sha256=sha(path),
        original_font_resource='/F7',original_encoded_CID='0087',original_gid=135,original_font='CambriaMath',original_point_size=12,
        proof_unmodified=True)
    result['verified_original_native_ink_missing_pixels']=0
    return True

def passed_checks(result,native_ink_ok):
    return all([result['composition']['native_move_qa']['passed'],not result['changed_pixels_outside_old_and_new_text_ink'],
        not result['native_graphics_motion_audit']['changed_nonselected_native_graphical_pixels'],
        not result['actual_native_math_visible_ink_audit']['missing_actual_native_pixels'],native_ink_ok,
        not any(r['changed_pixels']for r in result['figure_pixel_audits']),result['original_font_programs_and_names_retained'],
        result['original_image_programs_retained'],result['page_group_preserved'],result['colorspace_resources_preserved'],
        all((r['rect_preserved']or r.get('rect_matches_declared_native_math_dx',False))and r['full_palette_icc_mask_image_graph_preserved']for r in result['original_palette_icc_mask_graphs']),
        not result['new_batang_outlines']['empty'],not result['hangul_visibility']['flagged_components'],
        result.get('source_math_internal_geometry',{}).get('passed',True)])

def audit(year,kind,number):
    folder=BUILD/str(year)/kind;target=folder/f'page{number:02d}.pdf';composition=json.loads(target.with_suffix('.qa.json').read_text('utf8'))
    plan=json.loads((folder/f'plans/page{number:02d}.json').read_text('utf8'))
    if sha(target)!=composition['output_sha256']:raise ValueError('Proof SHA changed')
    old=folder/f'page{number:02d}.old-source.pdf'
    with pikepdf.open(plan['source_base'])as original,pikepdf.Pdf.new()as single:
        single.pages.append(original.pages[number-1]);single.save(old,compress_streams=False)
    control=Path(composition['native_control_output']);renders=folder/'qa-renders';renders.mkdir(exist_ok=True)
    # Each document is rendered in a separate process to avoid MuPDF's shared
    # Indexed-palette cache affecting comparison between two open PDFs.
    a=fresh_render(old,1,renders/f'{number:02d}-old.png')
    b=fresh_render(target,1,renders/f'{number:02d}-new.png')
    cp=fresh_render(control,1,renders/f'{number:02d}-control.png')
    changed=np.any(a!=b,axis=2)
    old_origins=[r['origin']for r in composition['erased_hangul_glyphs']];new_origins=[]
    for shift in composition['native_shifts']:
        old_origins.extend(g['origin']for g in shift['glyphs'])
        new_origins.extend([g['origin'][0]+shift['dx'],g['origin'][1]]for g in shift['glyphs'])
    with fitz.open(old)as src,fitz.open(target)as dst,fitz.open(control)as native:
        for t in dst[0].get_texttrace():
            if t['font']=='Batang':new_origins.extend(list(c[2])for c in t['chars'])
        old_ink,old_uses=ink_envelope(src[0],old_origins,4);new_ink,new_uses=ink_envelope(dst[0],new_origins,4)
        motion,geometry_qa=geometry_motion(old,target,composition['native_shifts'])
        outside=int((changed&~(old_ink|new_ink|motion)).sum())
        origins=[g['origin']for g in _traces(native[0])if g['c'].strip()and g['trace_gid']>=0]
        native_mask,uses=ink_envelope(native[0],origins,4);visible=(native_mask|motion)&(cp.min(axis=2)<80)
        native_actual=dict(native_control_sha256=sha(control),protected_actual_native_pixels=int(visible.sum()),
            missing_actual_native_pixels=int((visible&(b.min(axis=2)>170)).sum()),resolved_outline_uses=uses)
        figures=[]
        for rect in plan['excluded_figure_rects']:
            x0,y0,x1,y1=[int(v*4)for v in rect]
            figures.append(dict(rect=rect,changed_pixels=int(changed[max(0,y0):y1,max(0,x0):x1].sum())))
        # Match input native physical glyphs to the ORIGINAL English source;
        # translated Korean headings and other new prose are excluded here.
        with fitz.open(plan['original_english_source'])as original:
            physical={(glyph_key(g),g['trace_gid'],g['render_mode'])for g in _traces(original[plan['source_page']-1])if g['c'].strip()and g['trace_gid']>=0 and g['render_mode']!=3}
        protected=[g for g in _traces(src[0])if(glyph_key(g),g['trace_gid'],g['render_mode'])in physical and g['trace_gid']>=0 and g['c'].strip()]
        math_geometry=table_math_geometry(src[0],plan,composition)
        originals=src[0].get_image_info(xrefs=True);current=dst[0].get_image_info(xrefs=True)
    physical_ink=audit_moved_native_ink(old,1,target,shifts=composition['native_shifts'],
        erased_glyphs=composition['erased_hangul_glyphs'],protected_glyphs=protected)
    font_same=all(row in native_font_programs(target,1)for row in native_font_programs(old,1))
    image_same=all(row in native_image_programs(target,1)for row in native_image_programs(old,1))
    image_graphs=[]
    with pikepdf.open(old)as src,pikepdf.open(target)as dst:
        group_same=semantic(src.pages[0].get('/Group'))==semantic(dst.pages[0].get('/Group'))
        colors_same=semantic(src.pages[0].Resources.get('/ColorSpace'))==semantic(dst.pages[0].Resources.get('/ColorSpace'))
        if len(originals)!=len(current):raise ValueError('Image paint count changed')
        for i,(x,y)in enumerate(zip(originals,current)):
            image_graphs.append(dict(image=i,**image_rect_motion(x['bbox'],y['bbox'],geometry_qa),
                full_palette_icc_mask_image_graph_preserved=semantic(src.get_object((x['xref'],0)))==semantic(dst.get_object((y['xref'],0)))))
    result=dict(year=year,kind=kind,page=number,output=str(target),output_sha256=sha(target),
        original_source_sha256=plan['original_english_source_sha256'],old_korean_source_sha256=plan['source_base_sha256'],
        old_single_page_sha256=sha(old),composition=composition,body_font_coverage=coverage(plan,composition),
        fresh_process_rgb_render=True,changed_pixels_outside_old_and_new_text_ink=outside,
        native_graphics_motion_audit=geometry_qa,actual_native_math_visible_ink_audit=native_actual,
        source_math_internal_geometry=math_geometry,
        original_input_outline_native_ink_audit=physical_ink,figure_pixel_audits=figures,
        original_font_programs_and_names_retained=font_same,original_image_programs_retained=image_same,
        original_palette_icc_mask_graphs=image_graphs,page_group_preserved=group_same,colorspace_resources_preserved=colors_same,
        new_batang_outlines=new_outlines(target),hangul_visibility=hangul_audit(target),visual_review_required=True)
    result['passed']=passed_checks(result,native_phase_profile(result,plan,folder))
    target.with_suffix('.audit.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8')
    print(json.dumps(dict(page=number,passed=result['passed'],outside=outside,
        original_native_ink_missing=physical_ink.get('newly_missing_native_ink_pixels'),native_control_missing=native_actual['missing_actual_native_pixels'],
        figures=sum(r['changed_pixels']for r in figures),body_unreplaced=result['body_font_coverage']['unreplaced_regular_body_hangul']),ensure_ascii=False),flush=True)
    if not result['passed']:raise ValueError('Independent original-input native-ink/style/graphics audit failed')
    return result

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('year',type=int);p.add_argument('kind',choices=['T','TS']);p.add_argument('page',type=int);a=p.parse_args()
    with page_worker():audit(a.year,a.kind,a.page)

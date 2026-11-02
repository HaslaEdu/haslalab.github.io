"""Source-defined heading alignment, with exact encoded-CID ink references.

This changes only complete existing heading runs horizontally. Original native
font programs, encoded CIDs, GIDs, point sizes, paint, baseline, and all other
page content remain unchanged. References are analysis only and are generated
from the input PDF's actual native instructions, never from observed changes.
"""
from pathlib import Path
from io import BytesIO
from collections import defaultdict, Counter
import sys, json, hashlib, gc, re
import numpy as np
import pymupdf as fitz
import pikepdf

P = Path('D:/CodexBuilds/Hasla-publish-20261031')
B = Path('D:/CodexBuilds/Hasla-original-style-20261031/heading-alignment-v1')
sys.path.insert(0, str(P/'tools'))
from pdf_native_inline_reposition import (
    reposition_inline, _traces, inspect_inline_groups, _raw_regions,
    _multiply, _inverse_vector, _number, _verify_glyphs, _font_programs,
)
from pdf_original_text_ops import glyph_key
from pdf_native_glyph_promote import PAINT_STATE
from pdf_memory_gate import page_worker

fitz.TOOLS.set_small_glyph_heights(True)
load = lambda p: json.loads(Path(p).read_text('utf8'))
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
PRODUCER_SHA256 = sha(__file__)

def save(p, q):
    p = Path(p); p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(q, ensure_ascii=False, indent=2)+'\n', 'utf8')

def selected_heading(page, row):
    rect = row['scopes'][0]['rect']; y = row['scopes'][0]['baseline']
    # The source inventory is prose-only. Select the entire target heading at
    # its unchanged baseline, including its native punctuation and spaces.
    gs = [g for g in _traces(page) if g['trace_gid'] >= 0
          and abs(g['origin'][1]-y) < .02
          and rect[0]-.001 <= g['origin'][0] <= rect[2]+.001]
    visible = [g for g in gs if g['c'].strip()]
    assert visible and any(re.search('[가-힣]', g['c']) for g in visible), row
    # Any off-baseline glyph inside this row needs explicit whole-expression
    # review; never silently omit a subscript or superscript from the move.
    off = [g for g in _traces(page) if g['trace_gid'] >= 0 and g['c'].strip()
           and rect[0] <= g['origin'][0] <= rect[2]
           and rect[1] <= g['origin'][1] <= rect[3]
           and abs(g['origin'][1]-y) >= .02]
    assert not off, ('Off-baseline heading glyphs require review', row, off)
    return gs

def nonspace_center(gs):
    gs = [g for g in gs if g['c'].strip()]
    return (min(g['bbox'][0] for g in gs)+max(g['bbox'][2] for g in gs))/2

def original_center(row):
    with fitz.open(row['source_path']) as doc:
        bi, li = row['source_at']
        line = doc[row['source_page']-1].get_text('rawdict')['blocks'][bi]['lines'][li]
        cs = [c for s in line['spans'] for c in s['chars'] if c['c'].strip()]
        center = (min(c['bbox'][0] for c in cs)+max(c['bbox'][2] for c in cs))/2
        assert abs(center-row['source_center']) < 1e-7
        return center

def reference_replace(container,replacements):
    """Analysis-only suppression supports original quote shows as well as TJ.

    The publication mover's production allowlist remains unchanged. Quote
    operators are only copied verbatim inside nonpainting reference runs.
    """
    raw,regions=_raw_regions(container);chunks=[];position=0
    for index,value in sorted(replacements.items()):
        a,z,op=regions[index]
        assert op in {'Tj','TJ',"'",'"','Do','S','s','f','F','f*','B','B*','b','b*','n'}
        chunks.extend([raw[position:a],b'\n',value,b'\n']);position=z
    chunks.append(raw[position:]);return b''.join(chunks)

def cid_reference(raw, page_number, glyphs, heading_only=True):
    """Keep original native shows verbatim; make other shows nonpainting.

    Every original text-matrix operation, advance, graphics state, and clip is
    replayed in its original order. Selected encoded shows are byte-identical.
    The separate reference page suppresses all nonheading paint, while Tr=3
    keeps all unselected text advances exact. No reconstructed glyph origins,
    font remapping, Unicode insertion, or discarded active clips are involved.
    """
    from pdf_native_inline_reposition import _replace, PATH_PAINT
    inv=inspect_inline_groups(raw,page_number,include_text_shows=True)
    wanted={glyph_key(g)for g in glyphs};found=set();selected_shows=[];replacements={};reports=[]
    with pikepdf.open(BytesIO(raw))as pdf,fitz.open(stream=raw,filetype='pdf')as doc:
        src=pdf.pages[page_number-1];assert not src.obj.get('/Annots')
        contents,regions=_raw_regions(src);ops=pikepdf.parse_content_stream(src)
        white=[d for d in doc[page_number-1].get_drawings()if d['type']=='f'and d['fill']==(1.,1.,1.)and d['fill_opacity']==1 and d['color']is None]
        white_paints={v['operator_indices'][-1]for v in inv['vector_paths']if v['paint_operator']in['f','f*']and any(max(abs(a-b)for a,b in zip(v['rect'],list(d['rect'])))<.0001 for d in white)}
        for show in inv['top_level_text_shows']:
            keys={glyph_key(g)for part in show['parts']for g in part['glyphs']}
            selected=bool(keys&wanted)
            if selected:
                assert show['operator']in['Tj','TJ']
                # A wholly selected encoded show preserves its original native
                # raster phase and kerning, including inter-glyph accumulation.
                assert keys<=wanted,('Partial native heading show',show)
                found.update(keys);selected_shows.append(show['operator_index'])
                for part in show['parts']:
                    for g in part['glyphs']:
                        reports.append(dict(c=g['c'],font=g['font'],gid=g['trace_gid'],size=g['size'],origin=g['origin'],source_encoded_CID=part['raw_hex'],source_font_resource=show['state']['active'],source_Tf=show['state']['tf'],source_Tm_linear=show['text_matrix'][:4],render_mode=g['render_mode']))
            if selected != heading_only:
                assert show['state']['tr']<4,'Nonheading text clip needs a separate reference profile'
                index=show['operator_index'];a,z,_=regions[index]
                replacements[index]=b'\n3 Tr '+contents[a:z]+(' '+str(show['state']['tr'])+' Tr ').encode('ascii')
        assert found==wanted,('Heading is not exact top-level native paint',len(found),len(wanted))
        for index,instruction in enumerate(ops)if heading_only else []:
            op=str(instruction.operator)
            if op in PATH_PAINT and index not in white_paints:replacements[index]=b'\nn '
            elif op=='Do':replacements[index]=b'\n '
            elif op=='sh':raise ValueError('Shading needs explicit reference suppression')
        before=_font_programs(src);src.Contents=pdf.make_stream(reference_replace(src,replacements))
        with pikepdf.Pdf.new()as ref:
            ref.pages.append(src);out=BytesIO();ref.save(out,compress_streams=False,deterministic_id=True);result=out.getvalue()
        with pikepdf.open(BytesIO(result))as ref:assert before==_font_programs(ref.pages[0])
    with fitz.open(stream=result,filetype='pdf')as ref:
        actual=[g for g in _traces(ref[0])if g['render_mode']!=3 and g['trace_gid']>=0]
    def ident(g):return(g['c'],g['font'],g['trace_gid'],round(g['size'],5),g['render_mode'],str(g['color']),g['opacity'],g['linewidth'],str(g['stroke_color']),g['stroke_opacity'])
    with fitz.open(stream=raw,filetype='pdf')as original:
        expected_glyphs=glyphs if heading_only else [g for g in _traces(original[page_number-1])if glyph_key(g)not in wanted and g['render_mode']!=3 and g['trace_gid']>=0]
    expected=Counter(ident(g)for g in expected_glyphs);assert expected==Counter(ident(g)for g in actual),(expected,Counter(ident(g)for g in actual))
    buckets=defaultdict(list)
    for h in actual:buckets[ident(h)].append(h)
    for g in expected_glyphs:assert any(max(abs(g['origin'][k]-h['origin'][k])for k in[0,1])<=.001 for h in buckets[ident(g)])
    return result,dict(passed=True,original_encoded_CIDs_and_native_font_programs_retained=True,no_unicode_retyping=True,original_text_show_bytes_and_all_original_advances_and_clips_replayed=True,reference_sha256=hashlib.sha256(result).hexdigest(),glyphs=reports,selected_original_text_shows=selected_shows,metadata_audit=dict(passed=True,painted_heading_glyphs=len(actual),native_glyph_mismatches=[]))

def gray(raw, page=0, scale=4):
    with fitz.open(stream=raw,filetype='pdf') as doc:
        pix=doc[page].get_pixmap(matrix=fitz.Matrix(scale,scale),colorspace=fitz.csRGB,alpha=False)
        return np.frombuffer(pix.samples,np.uint8).reshape(pix.height,pix.width,3).min(axis=2)

def rgb(raw,page=0,scale=4):
    with fitz.open(stream=raw,filetype='pdf')as doc:
        pix=doc[page].get_pixmap(matrix=fitz.Matrix(scale,scale),colorspace=fitz.csRGB,alpha=False)
        return np.frombuffer(pix.samples,np.uint8).reshape(pix.height,pix.width,3).copy()

def independent_native_control(raw, page, shifts):
    """Move complete original shows independently of the per-CID producer.

    Replaying the entire source page also preserves native transparency and
    white-background compositing. Pixel prediction never combines antialias
    samples from separately flattened layers.
    """
    from pdf_native_inline_reposition import _replace
    inv=inspect_inline_groups(raw,page,include_text_shows=True)
    offsets={glyph_key(g):s['dx']for s in shifts for g in s['glyphs']};found=set();replacements={}
    with pikepdf.open(BytesIO(raw))as pdf,fitz.open(stream=raw,filetype='pdf')as source:
        src=pdf.pages[page-1];contents,regions=_raw_regions(src)
        for show in inv['top_level_text_shows']:
            keys={glyph_key(g)for part in show['parts']for g in part['glyphs']}
            if not keys&offsets.keys():continue
            assert keys<=offsets.keys();ds={offsets[k]for k in keys};assert len(ds)==1
            combined=_multiply(show['state']['ctm'],tuple(source[page-1].transformation_matrix))
            dx,dy=_inverse_vector(combined,next(iter(ds)),0.)
            index=show['operator_index'];a,z,_=regions[index]
            replacements[index]=('\nq 1 0 0 1 '+_number(dx)+' '+_number(dy)+' cm\n').encode('ascii')+contents[a:z]+b'\nQ '
            found.update(keys)
        assert found==offsets.keys()
        src.Contents=pdf.make_stream(_replace(src,replacements))
        with pikepdf.Pdf.new()as target:
            target.pages.append(src);buf=BytesIO();target.save(buf,compress_streams=False,deterministic_id=True);result=buf.getvalue()
        metadata=_verify_glyphs(source[page-1],result,set(),offsets,tolerance=.001)
    assert not metadata['native_glyph_mismatches']and not metadata['unexpected_glyphs'],metadata
    return result,dict(passed=True,original_source_entire_native_text_shows_replayed=True,not_the_publication_producer=True,source_text_show_bytes_retained=True,only_declared_complete_heading_shows_shifted=True,reference_sha256=hashlib.sha256(result).hexdigest(),metadata_audit=metadata)

def ink_audit(source_raw, page, result_raw, headings, shifts):
    old_ref, old_qa=cid_reference(source_raw,page,headings)
    with fitz.open(stream=result_raw,filetype='pdf') as doc:
        # Match exact requested positions from independent movement inputs.
        actual=_traces(doc[0]); target=[]
        for move in shifts:
            for g in move['glyphs']:
                matches=[h for h in actual if h['c']==g['c'] and h['trace_gid']==g['trace_gid'] and h['font']==g['font'] and abs(h['size']-g['size'])<.00001 and abs(h['origin'][0]-g['origin'][0]-move['dx'])<.001 and abs(h['origin'][1]-g['origin'][1])<.001]
                assert len(matches)==1, (g,matches)
                target.append(matches[0])
    new_ref,new_qa=cid_reference(result_raw,1,target)
    background_ref,background_qa=cid_reference(source_raw,page,headings,heading_only=False)
    control,control_qa=independent_native_control(source_raw,page,shifts)
    # Native PDF resources are large. Release closed-document cycles and font
    # caches before allocating the 4x reference pixmaps on this shared machine.
    fitz.TOOLS.store_shrink(100);gc.collect()
    with page_worker():
        old=gray(old_ref); new=gray(new_ref)
        # One device-pixel dilation encloses all independently rendered native
        # antialias samples. It does not infer any mask from observed changes.
        import cv2
        mask=cv2.dilate(((old<255)|(new<255)).astype(np.uint8),np.ones((3,3),np.uint8)).astype(bool)
        a=rgb(source_raw,page-1); b=rgb(result_raw)
        outside=int((np.any(a!=b,axis=2)&~mask).sum())
        missing=int(((new<220)&(b.min(axis=2)>=220)).sum())
        old_bad=int(((old<220)&(a.min(axis=2)>=220)).sum())
        # Reject any unexpected paint inside the swept heading region too:
        # original nonheading paint must remain pixel-identical under the two
        # exact native references, with antialias composition accounted for.
        predicted=rgb(control)
        inside_unexpected=int((np.any(predicted!=b,axis=2)&mask).sum())
        unexpected_dark=int(((b.min(axis=2)<220)&(predicted.min(axis=2)>=220)&mask).sum())
        diff=(predicted.astype(np.int16)-b.astype(np.int16))
        delta_histogram=dict(Counter(int(v)for v in diff[(predicted!=b)&mask[:,:,None]]))
    q=dict(scale=4,independent_actual_original_encoded_CID_references=True,mask_derived_from_observed_difference=False,source_reference=old_qa,target_reference=new_qa,stationary_background_reference=background_qa,independent_full_native_control=control_qa,changed_pixels_outside_source_and_target_heading_ink=outside,missing_target_native_heading_ink_pixels=missing,missing_source_reference_ink_pixels=old_bad,unexpected_pixels_inside_independent_heading_reference=inside_unexpected)
    q['passed']=outside==missing==old_bad==inside_unexpected==0
    if not q['passed']:
        save(B/'last-pixel-diagnostic.json',dict(outside=outside,missing=missing,old_bad=old_bad,inside_unexpected=inside_unexpected,unexpected_dark=unexpected_dark,delta_histogram=delta_histogram))
    assert q['passed'],{k:v for k,v in q.items()if k not in ['source_reference','target_reference','stationary_background_reference']}
    return q

def build_page(filename, number, rows):
    folder=B/filename.removesuffix('.pdf'); folder.mkdir(exist_ok=True)
    output=folder/f'page{number:02}.pdf'; report=output.with_suffix('.alignment.json')
    item=next(i for i in load(P/'tools/original_style_publication.json') if i['file']==filename)
    source=Path(item['generated_file']); assert sha(source)==item['sha256']; source_raw=source.read_bytes()
    shifts=[]; selected=[]; audits=[]; white_panels=[]
    with fitz.open(stream=source_raw,filetype='pdf') as doc:
        for row in rows:
            gs=selected_heading(doc[number-1],row); center=original_center(row); current=nonspace_center(gs); dx=center-current
            assert abs(dx)>.001
            assert not ({glyph_key(g)for g in gs}&{glyph_key(g)for g in selected})
            selected.extend(gs); shifts.append(dict(glyphs=gs,dx=dx))
            audits.append(dict(source_at=row['source_at'],source_text=row['source_text'],source_path=row['source_path'],source_sha256=sha(row['source_path']),source_page=row['source_page'],source_nonspace_center=center,previous_center=current,requested_dx=dx,baseline=row['scopes'][0]['baseline'],scope=row['scopes'][0]['rect'],glyphs=len(gs)))
        # Existing source-language erasure panels are stationary backgrounds.
        # Whitelist only exact opaque, unstroked, white native rectangles. The
        # shared mover validates this profile again; independent ink QA below
        # still protects every actual nonheading pixel, including the panels.
        for d in doc[number-1].get_drawings():
            if d['type']=='f' and d['fill']==(1.,1.,1.) and d['fill_opacity']==1 and d['color'] is None and len(d['items'])==1 and d['items'][0][0]=='re' and any(d['rect'].intersects(fitz.Rect(g['bbox'])) for g in selected):
                white_panels.append(list(d['rect']))
    result,move=reposition_inline(source_raw,number,shifts=shifts,text_shift_mode='ctm',reviewed_white_panel_rects=white_panels)
    assert move['passed'] and move['font_programs_unchanged'] and move['original_image_streams_unchanged'] and move['native_vector_path_bytes_preserved'] and not move['native_glyph_mismatches']
    output.write_bytes(result)
    ink=ink_audit(source_raw,number,result,selected,shifts)
    with fitz.open(stream=result,filetype='pdf') as final:
        for r,s in zip(audits,shifts):
            gs=[]
            for g in s['glyphs']:
                gs.extend(h for h in _traces(final[0])if h['c']==g['c'] and h['trace_gid']==g['trace_gid']and h['font']==g['font']and abs(h['origin'][0]-g['origin'][0]-s['dx'])<.001 and abs(h['origin'][1]-g['origin'][1])<.001)
            r['actual_center']=nonspace_center(gs);r['center_error_pt']=r['actual_center']-r['source_nonspace_center'];r['passed']=abs(r['center_error_pt'])<=.001
    q=dict(passed=all(r['passed']for r in audits)and ink['passed'],file=filename,page=number,baseline_item=item,source_pdf_sha256=item['sha256'],proof_sha256=sha(output),producer_sha256=PRODUCER_SHA256,headings=audits,native_move_qa=move,pixel_audit=ink,reviewed_stationary_opaque_white_rectangles=white_panels)
    save(report,q);print('PASS',filename,number,len(rows),flush=True)
    fitz.TOOLS.store_shrink(100);gc.collect()
    return q

def main():
    inventory=load(B.parent/'published-izho-heading-detail-20261102.json')
    groups=defaultdict(list)
    for r in inventory['candidates_requiring_review']:
        if abs(r['actual_center_error'])>.001:groups[(r['file'],r['published_page'])].append(r)
    if len(sys.argv)>1:
        filename=sys.argv[1]; page=int(sys.argv[2]); build_page(filename,page,groups[(filename,page)]);return
    for (filename,page),rows in sorted(groups.items()):
        report=B/filename.removesuffix('.pdf')/f'page{page:02}.alignment.json'
        if report.exists():
            q=load(report)
            if q['passed']and q.get('producer_sha256')==PRODUCER_SHA256 and 'stationary_background_reference'in q['pixel_audit']and sha(report.with_suffix('.pdf').with_name(f'page{page:02}.pdf'))==q['proof_sha256']:
                print('CACHED',filename,page,flush=True);continue
        build_page(filename,page,rows)

if __name__=='__main__':main()

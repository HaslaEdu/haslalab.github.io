"""Rebuild reviewed IZhO legacy-font editions without replacing native fonts.

Reuses the shared fixed-style engine's original PDF /Widths, encodings, font
aliases and SVG glyph audit. Plans explicitly select translated prose only.
"""
from __future__ import annotations
import argparse,hashlib,json
from pathlib import Path
import numpy as np
import pikepdf
import pymupdf as fitz
import izho_early_fixed_style as legacy
from pdf_original_style_fonts import FONTS
from pdf_original_style_audit import glyphs,key
from pdf_original_text_ops import suppress_prose
from izho_native_ascii_audit import audit as ascii_audit
from izho_bitmap_labels import apply as bitmap_labels

ROOT=legacy.ROOT

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def hashes(plan):
    paths=[plan,Path(__file__).resolve(),ROOT/'tools/izho_early_fixed_style.py',ROOT/'tools/pdf_original_text_ops.py',
           ROOT/'tools/pdf_original_style_audit.py',ROOT/'tools/pdf_original_style_fonts.py',
           ROOT/'tools/izho_native_ascii_audit.py',*FONTS.values()]
    if json.loads(plan.read_text('utf8')).get('raster_language_overlays'):paths.append(ROOT/'tools/izho_bitmap_labels.py')
    if any(row.get('protect_features')for row in json.loads(plan.read_text('utf8')).get('raster_language_overlays',[])):
        paths.append(ROOT/'tools/izho_bitmap_features.py')
    return {str(p.relative_to(ROOT)):sha(p)for p in paths}

def check(plan):
    data=json.loads(plan.read_text('utf8'));source=legacy.ensure_reviewed_source(data,plan)
    fitz.TOOLS.set_small_glyph_heights(data.get('small_glyph_heights',True))
    doc=fitz.open(source);page=doc[data['page']];runs=legacy.runs_of(page)
    catalog=legacy.font_catalog(source,data['page']+1,{t['font']for t in page.get_texttrace()})
    metrics={role:fitz.Font(fontfile=str(path))for role,path in FONTS.items()}
    errors=[]
    for spec in data['slots']:
        anchor,chars,rect,point=legacy.slot_source(spec,runs)
        parts=spec.get('parts',[{'text':spec.get('text','')}]);width=0
        for part in parts:
            style=runs[tuple(part.get('style_from',spec['at']))]
            chunks=legacy.split_parts(part,style,catalog,metrics)
            for chunk in chunks:
                if chunk['native']:
                    profile=chunk['profile']
                    unsupported=[char for char,code in zip(chunk['text'],chunk['codes'])if not char.isspace()and profile['widths'].get(code,profile['default'])==0]
                    if unsupported:errors.append(dict(at=spec['at'],font=style['font'],zero_width_native_target_characters=unsupported))
                width+=chunk['advance']
        if width>rect.width+.05:errors.append(dict(at=spec['at'],width=width,available=rect.width,text=''.join(p['text']for p in parts)))
    doc.close();print(json.dumps(errors,ensure_ascii=False,indent=2),flush=True)
    return errors

def valid(proof,plan):
    path=proof.with_suffix('.qa.json')
    if not proof.exists()or not path.exists():return False
    qa=json.loads(path.read_text('utf8'))
    return qa.get('authoring_sha256')==hashes(plan)and qa.get('proof_sha256')==sha(proof)and not any(qa.get(k)for k in[
        'native_glyphs_changed','protected_glyphs_selected_for_erasure','changed_pixels_outside_prose','changed_pixels_in_native_glyph_neighborhood',
        'changed_pixels_outside_raster_language_regions','changed_pixels_in_visible_raster_graphics'])and all(qa.get(k)is True for k in[
        'source_font_programs_and_names_unchanged','source_images_bytes_and_rects_unchanged'])and(
        qa.get('source_original_vector_drawings_preserved',qa.get('source_vector_drawings_unchanged'))is True)

def build(plan,proof):
    data=json.loads(plan.read_text('utf8'))
    fitz.TOOLS.set_small_glyph_heights(data.get('small_glyph_heights',True))
    source=legacy.ensure_reviewed_source(data,plan);doc=fitz.open(source);page=doc[data['page']]
    runs=legacy.runs_of(page);selected=[]
    for spec in data['slots']:selected.extend(legacy.slot_source(spec,runs)[1])
    raw,removed=suppress_prose(source,data['page']+1,selected);doc.close()
    proof.parent.mkdir(parents=True,exist_ok=True);proof.with_suffix('.control.pdf').write_bytes(raw)
    labels=data.get('raster_language_overlays',[])
    base=proof.with_name(proof.stem+'.base.pdf')if labels else proof
    qa=legacy.build(plan,base)
    if labels:qa.update(bitmap_labels(source,data['page']+1,base,proof,labels))
    qa['authoring_sha256']=hashes(plan)
    proof.with_suffix('.qa.json').write_text(json.dumps(qa,ensure_ascii=False,indent=2),encoding='utf8')
    return qa

def rgb(page):
    pix=page.get_pixmap(matrix=fitz.Matrix(4,4),colorspace=fitz.csRGB,alpha=False)
    return np.frombuffer(pix.samples,np.uint8).reshape(pix.height,pix.width,3)

def rebuild(year,kind):
    folder=ROOT/'tools/ko/izho'/str(year)/kind/'original_style'
    plans=sorted(folder.glob('page*.json'),key=lambda p:int(p.stem[4:]))
    if not plans:raise ValueError('No reviewed plans')
    data=[json.loads(p.read_text('utf8'))for p in plans]
    source=legacy.ensure_reviewed_source(data[0],plans[0]);doc=fitz.open(source)
    selection=data[0].get('source_page_selection',list(range(len(doc))))
    if not selection or selection!=sorted(set(selection))or any(type(i)is not int or not 0<=i<len(doc)for i in selection):
        raise ValueError('Source-page selection must be an explicit ordered set of valid source pages')
    if 'source_page_selection'in data[0]:
        if not data[0].get('source_page_selection_note')or any(d.get('source_page_selection')!=selection for d in data):
            raise ValueError('A reviewed multilingual source selection and its explanation must be present in every plan')
    if len(selection)!=len(plans)or [d['page']for d in data]!=selection:raise ValueError('Complete ordered plans required')
    source_count=len(doc)
    doc.close();scratch=ROOT/'tmp/original-style-repair'/str(year)/kind;scratch.mkdir(parents=True,exist_ok=True)
    proofs=[]
    for plan in plans:
        if check(plan):raise ValueError('Fixed-size prose overflow')
        target=scratch/(plan.stem+'.pdf')
        if not valid(target,plan):build(plan,target)
        proofs.append(target)
    target=scratch/f'IZhO_{year}_{kind}_KO.pdf'
    with pikepdf.Pdf.new()as joined:
        for proof in proofs:
            with pikepdf.open(proof)as src:joined.pages.append(src.pages[0])
        joined.save(target,compress_streams=False)
    final=fitz.open(target);audits=[]
    for i,(plan,proof)in enumerate(zip(plans,proofs)):
        single=fitz.open(proof);diff=int(np.any(rgb(single[0])!=rgb(final[i]),axis=2).sum())
        if diff:raise ValueError('Final assembly changed reviewed pixels')
        if [key(g)for g in glyphs(single[0])]!=[key(g)for g in glyphs(final[i])]:raise ValueError('Final assembly changed glyph geometry')
        qa=json.loads(proof.with_suffix('.qa.json').read_text('utf8'));qa.pop('placements')
        qa['final_vs_reviewed_proof_changed_pixels']=diff;qa['final_page']=i+1;audits.append(qa);single.close()
    final.close();report=dict(output=str(target.relative_to(ROOT)),output_sha256=sha(target),pages=len(plans),
        source_sha256=sha(source),source_page_count=source_count,source_pages_1based=[i+1 for i in selection],
        source_page_selection_note=data[0].get('source_page_selection_note'),
        assembly='pikepdf native page append',no_autoshrink=True,no_equation_rasterization=True,no_paragraph_reflow=True,
        no_added_editorial_notes=True,page_audits=audits,visual_review_required=True)
    ascii_result=ascii_audit(target,scratch,[proof.stem for proof in proofs])
    (folder/'native-ascii-audit.json').write_text(json.dumps(ascii_result,ensure_ascii=False,indent=2),encoding='utf8')
    if ascii_result['nonpositive_or_missing_width_count']:raise ValueError('New native prose has an unsupported PDF Width')
    report['new_native_ascii_codes_checked']=ascii_result['ascii_codes_checked']
    report['new_native_ascii_nonpositive_widths']=ascii_result['nonpositive_or_missing_width_count']
    (folder/'audit.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
    print(json.dumps({k:v for k,v in report.items()if k!='page_audits'},ensure_ascii=False,indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('year',nargs='?',type=int);p.add_argument('kind',nargs='?',choices=['T','TS','E','ES'])
    p.add_argument('--plan',type=Path);p.add_argument('--out',type=Path);p.add_argument('--check',action='store_true');a=p.parse_args()
    if a.plan:
        plan=a.plan if a.plan.is_absolute()else ROOT/a.plan
        if a.check:raise SystemExit(bool(check(plan)))
        if not a.out:raise ValueError('--out required for a single proof')
        proof=a.out if a.out.is_absolute()else ROOT/a.out
        if check(plan):raise ValueError('Fixed-size prose overflow')
        build(plan,proof)
    else:rebuild(a.year,a.kind)

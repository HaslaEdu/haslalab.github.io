"""Rebuild reviewed early IZhO original-style pages and audit the joined PDF."""
from pathlib import Path
import argparse,hashlib,json
import pymupdf as fitz
import pikepdf
from izho_early_fixed_style import build,ROOT,ensure_reviewed_source,native_font_programs,native_image_programs
from pdf_original_style_audit import audit
from pdf_hangul_visibility import audit as hangul_audit

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def rebuild(year,kind,assemble_only=False):
    folder=ROOT/f'tools/ko/izho/{year}/{kind}/original_style'
    plans=sorted(folder.glob('page*.json'),key=lambda p:int(p.stem[4:]))
    if not plans:raise ValueError('No reviewed page plans: '+str(folder))
    expected=list(range(1,len(plans)+1))
    if [int(p.stem[4:])for p in plans]!=expected:raise ValueError('Page plan numbering must be complete and contiguous')
    work=ROOT/f'tmp/izho-original-style/{year}/{kind}';work.mkdir(parents=True,exist_ok=True)
    data=[json.loads(p.read_text('utf8'))for p in plans]
    for entry,plan in zip(data,plans):ensure_reviewed_source(entry,plan)
    unique_sources={d['source']for d in data}
    if len(unique_sources)==1:
        with fitz.open(ROOT/data[0]['source'])as source:
            if len(source)!=len(plans):raise ValueError('Incomplete source document plans')
        if [d['page']for d in data]!=list(range(len(plans))):raise ValueError('Source pages must appear exactly once in order')
    pages=[]
    for index,plan in enumerate(plans,1):
        target=work/f'page{index}.pdf'
        if not assemble_only:build(plan,target)
        report=json.loads(target.with_suffix('.qa.json').read_text('utf8'))
        if report['plan_sha256']!=sha(plan)or report['proof_sha256']!=sha(target)or report['source_sha256']!=sha(ROOT/data[index-1]['source']):raise ValueError('Stale page proof: '+str(plan))
        pages.append(target)
    target=ROOT/f'pdfx/izho/original-style/IZhO_{year}_{kind}_KO.pdf';target.parent.mkdir(parents=True,exist_ok=True)
    # PyMuPDF insert_pdf can alter native text rasterization while grafting
    # page resources. Copy the complete page object graph with qpdf instead.
    joined=pikepdf.Pdf.new()
    for page in pages:
        with pikepdf.Pdf.open(page)as one:joined.pages.append(one.pages[0])
    with pikepdf.Pdf.open(ROOT/data[0]['source'])as source:joined.docinfo.update({key:str(value)for key,value in source.docinfo.items()})
    joined.save(target);joined.close()
    reports=[]
    for index,(page,entry)in enumerate(zip(pages,data),1):
        spec=json.loads(page.with_suffix('.audit-spec.json').read_text('utf8'));spec['proof_page']=index
        result=audit(ROOT/entry['source'],target,spec)
        result['source_font_programs_and_names_unchanged']=all(font in native_font_programs(target,index)for font in native_font_programs(ROOT/entry['source'],entry['page']+1))
        result['source_image_and_alpha_streams_unchanged']=native_image_programs(ROOT/entry['source'],entry['page']+1)==native_image_programs(target,index)
        if result['native_glyphs_changed']or result['protected_glyphs_selected_for_erasure']or result['changed_pixels_outside_prose']or result['changed_pixels_in_native_glyph_neighborhood']:raise ValueError('Joined PDF native audit failed: '+str(index))
        if not result['source_font_programs_and_names_unchanged']or not result['source_image_and_alpha_streams_unchanged']:raise ValueError('Joined PDF native resource audit failed: '+str(index))
        reports.append(result)
    visibility=hangul_audit(target)
    if visibility['flagged_components']:raise ValueError('Joined PDF contains hidden Hangul glyphs')
    record=dict(year=year,kind=kind,status='READY',file=str(target.relative_to(ROOT)).replace('\\','/'),sha256=sha(target),bytes=target.stat().st_size,pages=len(pages),
        scope='Original source prose only; fixed source sizes/baselines, matched serif/sans and actual weights, original Latin font resources, native formula and figure objects.',
        autoshrink=False,reflow=False,equation_images=0,added_titles_or_errata=False,
        native_glyphs_checked=sum(r['native_glyphs_checked']for r in reports),protected_glyph_origins_checked=sum(r['protected_glyph_origins_checked']for r in reports),
        native_glyphs_changed=0,protected_glyphs_selected_for_erasure=0,changed_pixels_in_native_glyph_neighborhood=0,changed_pixels_outside_prose=0,
        hangul_visibility_candidates=0,plans=[str(p.relative_to(ROOT)).replace('\\','/')for p in plans],sources={name:sha(ROOT/name)for name in unique_sources},
        page_audits=reports,hangul_visibility=visibility)
    target.with_suffix('.qa.json').write_text(json.dumps(record,ensure_ascii=False,indent=2),'utf8')
    ready=ROOT/'tools/izho_early_original_style_ready.json'
    records=json.loads(ready.read_text('utf8'))if ready.exists()else[]
    records=[r for r in records if(r['year'],r['kind'])!=(year,kind)]+[record]
    records.sort(key=lambda r:(r['year'],r['kind']));ready.write_text(json.dumps(records,ensure_ascii=False,indent=2)+'\n','utf8')
    print(json.dumps({k:v for k,v in record.items()if k not in ['page_audits','hangul_visibility']},ensure_ascii=False),flush=True)
    return record

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--year',type=int,required=True);p.add_argument('--kind',choices=['T','TS','E','ES'],default='T');p.add_argument('--assemble-only',action='store_true');a=p.parse_args();rebuild(a.year,a.kind,a.assemble_only)

"""Rebuild and audit a complete IZhO edition using its reviewed original slots.

    python tools/izho_original_style_rebuild.py 2026 T

The native originals are immutable SHA-256-bound archive assets. There is no
automatic translation, re-extraction, font shrink, equation rasterization or
paragraph reflow. Cached proofs are used only when all authoring hashes match.
"""
from __future__ import annotations
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import urllib.request
import pikepdf
import numpy as np
from PIL import Image,ImageDraw
import izho_original_style as engine

ROOT=engine.ROOT
ZERO_CHECKS=('outside_prose_changed_pixels','missing_or_moved_native_glyphs',
             'missing_or_moved_math_glyphs','original_math_ink_changed_pixels',
             'original_native_ink_changed_pixels','original_figure_ink_changed_pixels',
             'source_to_suppression_control_native_ink_changed_pixels',
             'korean_intrusion_on_native_ink_pixels',
             'source_to_suppression_control_figure_ink_changed_pixels',
             'korean_intrusion_on_figure_ink_pixels')
TRUE_CHECKS=('native_images_unchanged','native_vector_drawings_unchanged',
             'source_embedded_glyph_outline_bounds','suppression_control_native_geometry_unchanged',
             'suppression_control_source_font_programs_unchanged','native_font_gid_size_unchanged',
             'original_source_font_programs_preserved_in_final')

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def fetch_source(data):
    source=ROOT/data['source']
    if not source.exists():
        source.parent.mkdir(parents=True,exist_ok=True)
        url='https://github.com/HaslaEdu/haslalab.github.io/releases/download/pdf-izho/'+source.name
        request=urllib.request.Request(url,headers={'User-Agent':'HaslaLab original-style rebuild'})
        with urllib.request.urlopen(request,timeout=120)as response:raw=response.read()
        if not raw.startswith(b'%PDF-'):raise ValueError('Archive did not return a PDF')
        if hashlib.sha256(raw).hexdigest()!=data['source_sha256']:
            raise ValueError('Downloaded original hash changed')
        source.write_bytes(raw)
    if sha(source)!=data['source_sha256']:raise ValueError('Reviewed original hash changed')
    return source

def valid_proof(target):
    qa_path=target.with_suffix('.qa.json')
    if not target.exists()or not qa_path.exists():return False
    qa=json.loads(qa_path.read_text('utf8'))
    if sha(target)!=qa['output_sha256']:return False
    for name,digest in qa.get('authoring_sha256',{}).items():
        path=ROOT/name
        if not path.exists()or sha(path)!=digest:return False
    if not qa.get('authoring_sha256'):return False
    return all(qa.get(key)==0 for key in ZERO_CHECKS)and all(qa.get(key)is True for key in TRUE_CHECKS)

def assemble(plans,proofs,target,report_path):
    # insert_pdf changes native antialiasing for some embedded source fonts.
    # pikepdf retains each proof's resources and unmodified content bytes.
    with pikepdf.Pdf.new()as joined:
        for path in proofs:
            with pikepdf.open(path)as proof:joined.pages.append(proof.pages[0])
        joined.save(target)
    final=engine.fitz.open(target)
    results=[]
    for i,(plan,proof)in enumerate(zip(plans,proofs)):
        qa=json.loads(proof.with_suffix('.qa.json').read_text('utf8'))
        source=engine.fitz.open(proof)
        before=engine.rgb(source[0],4);after=engine.rgb(final[i],4)
        pixels=int(np.any(before!=after,axis=2).sum())
        trace_equal=engine.native_trace(source[0])==engine.native_trace(final[i])
        if pixels or not trace_equal:
            raise ValueError(f'Final assembly changed reviewed page {i+1}: {pixels} pixels')
        if not valid_proof(proof):raise ValueError(f'Stale or failed proof {i+1}')
        if any(abs(row['size']-row['source_size'])>1e-6 or abs(row['point'][1]-row['source_baseline'])>1e-5 for row in qa['placements']):
            raise ValueError('Original font size/baseline changed')
        qa.pop('prose_frames');qa.pop('placements')
        qa.update(final_page=i+1,final_vs_reviewed_proof_changed_pixels=pixels,
                  final_vs_reviewed_proof_glyph_geometry_identical=trace_equal,
                  original_font_sizes_and_baselines_identical=True,
                  plan=str(plan.relative_to(ROOT)),plan_sha256=sha(plan))
        results.append(qa)
        source.close()
    report={'output':str(target.relative_to(ROOT)),'output_sha256':sha(target),
            'pages':len(results),'assembly':'pikepdf native page append',
            'no_autoshrink':True,'no_equation_rasterization':True,'no_paragraph_reflow':True,
            'no_added_editorial_notes':True,'page_audits':results,
            'visual_review_required':True}
    report_path.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
    final.close()
    print(json.dumps({key:value for key,value in report.items()if key!='page_audits'},ensure_ascii=False,indent=2))
    return report

def rebuild(year,kind,output=None,force=False):
    folder=ROOT/'tools/ko/izho'/str(year)/kind/'original_style'
    plans=sorted(folder.glob('page*.json'),key=lambda p:int(p.stem[4:]))
    if not plans:raise ValueError('No reviewed original-style plans')
    data=[json.loads(p.read_text('utf8'))for p in plans]
    source=fetch_source(data[0]);doc=engine.fitz.open(source)
    if len(doc)!=len(plans)or [d['page']for d in data]!=list(range(len(doc))):
        raise ValueError('Complete ordered page plans are required')
    if any(d['source']!=data[0]['source']or d['source_sha256']!=data[0]['source_sha256']for d in data):
        raise ValueError('Plans reference different originals')
    scratch=ROOT/'tmp/original-style-repair'/str(year)/kind
    scratch.mkdir(parents=True,exist_ok=True)
    proofs=[]
    for plan in plans:
        if engine.check_plan(plan):raise ValueError('Reviewed Korean prose exceeds a source slot')
        target=scratch/(plan.stem+'.pdf')
        if force or not valid_proof(target):engine.build(plan,target)
        proofs.append(target)
    target=output or scratch/f'IZhO_{year}_{kind}_KO.pdf'
    target=target if target.is_absolute()else ROOT/target
    target.parent.mkdir(parents=True,exist_ok=True)
    return assemble(plans,proofs,target,folder/'audit.json')

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('year',type=int);parser.add_argument('kind',choices=('T','TS','E','ES'))
    parser.add_argument('--output',type=Path);parser.add_argument('--force',action='store_true')
    args=parser.parse_args();rebuild(args.year,args.kind,args.output,args.force)

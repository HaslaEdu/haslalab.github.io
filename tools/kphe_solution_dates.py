"""Add verified sitting dates without retypesetting any worked explanation.

Examples:
    python tools/kphe_solution_dates.py --modern-only
    python tools/kphe_solution_dates.py --check-only

Every page is verified for date text, original font family, point size and bbox.
Changed documents are rendered before/after at 144 dpi; not one pixel outside
the date rectangle (0.3 pt padding) may change. Four measured 2024 header-rule
exceptions also allow only the narrow old/new rule rectangles. A temporary PDF is validated
before atomic replacement.  A second run leaves already correct PDFs untouched.
"""
from pathlib import Path
import argparse
import hashlib
import json
import math
import os
import re
import shutil

import numpy as np
import pymupdf as fitz

from kphe_key_design import ROOT, A4, draw_exam_date, exam_date_profile, solution_header_prepared

WORK = ROOT/'tmp/kphe-solution-dates'
PAD = .3
ZOOM = 2.0


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def selected(modern_only=False):
    profiles=json.loads((ROOT/'tools/kphe_exam_dates.json').read_text(encoding='utf-8'))['profiles']
    for key,profile in profiles.items():
        year,part=key.split(':')
        if modern_only and int(year[:4])<2024:
            continue
        target=ROOT/'pdfx/kphe'/f'KPhE_{year[:4]}_{part}S.pdf'
        if not target.is_file():
            raise FileNotFoundError(target)
        yield year,part,target,profile


def date_box(page,profile):
    values=profile['a4_bbox']
    sx,sy=page.rect.width/A4.width,page.rect.height/A4.height
    return fitz.Rect(values[0]*sx,values[1]*sy,values[2]*sx,values[3]*sy)


def verify_page(page,profile):
    box=date_box(page,profile)
    search=box+(-PAD,-PAD,PAD,PAD)
    text=page.get_text('text',clip=search).strip()
    spans=[s for b in page.get_text('dict',clip=search)['blocks'] if b['type']==0
           for line in b['lines'] for s in line['spans'] if s['text'].strip()]
    if not spans or text!=profile['text']:
        raise ValueError(f'Date text mismatch: page {page.number+1}: {text!r}')
    if any(profile['font'].replace(' ','') not in s['font'].replace(' ','') for s in spans):
        raise ValueError(f'Date font mismatch: page {page.number+1}: {[s["font"] for s in spans]}')
    actual=fitz.Rect(spans[0]['bbox'])
    for span in spans[1:]:
        actual |= fitz.Rect(span['bbox'])
    if max(abs(a-b) for a,b in zip(actual,box))>.035:
        raise ValueError(f'Date bbox mismatch: page {page.number+1}: {actual} expected {box}')
    for span in spans:
        if abs(span['size']-profile['a4_point'])>.035:
            raise ValueError(f'Date point mismatch: page {page.number+1}: {span["size"]}')
    if not solution_header_prepared(page,profile['year'],profile['part']):
        raise ValueError(f'Colliding 2024 header rule not prepared: page {page.number+1}')
    return {'page':page.number+1,'text':text,'fonts':sorted(set(s['font'] for s in spans)),
            'point':spans[0]['size'],'bbox':list(actual),'profile_bbox':list(box)}


def outside_pixels(before,after,profile):
    if len(before)!=len(after):
        raise ValueError('Overlay changed the page count')
    count=0
    maxdiff=0
    for old,new in zip(before,after):
        a=old.get_pixmap(matrix=fitz.Matrix(ZOOM,ZOOM),alpha=False)
        b=new.get_pixmap(matrix=fitz.Matrix(ZOOM,ZOOM),alpha=False)
        if (a.width,a.height,a.n)!=(b.width,b.height,b.n):
            raise ValueError('Overlay changed the rendered page dimensions')
        x=np.frombuffer(a.samples,np.uint8).reshape(a.height,a.width,a.n)
        y=np.frombuffer(b.samples,np.uint8).reshape(b.height,b.width,b.n)
        difference=np.any(x!=y,axis=2)
        allowed_boxes=[date_box(old,profile)+(-PAD,-PAD,PAD,PAD)]
        adjustment=profile.get('header_rule_adjustment')
        if adjustment:
            rule_pad=adjustment.get('allowed_padding_pt',PAD)
            allowed_boxes += [fitz.Rect(adjustment[key])+(-rule_pad,-rule_pad,rule_pad,rule_pad)
                              for key in ('old_a4_bbox','new_a4_bbox')]
        for allowed in allowed_boxes:
            difference[max(0,math.floor(allowed.y0*ZOOM)):math.ceil(allowed.y1*ZOOM),
                       max(0,math.floor(allowed.x0*ZOOM)):math.ceil(allowed.x1*ZOOM)]=False
        changed=int(difference.sum())
        maxdiff=max(maxdiff,changed)
        count+=changed
    if count:
        raise ValueError(f'{count} rendered pixels changed outside the date region; max/page {maxdiff}')
    return {'pages':len(before),'dpi':72*ZOOM,'outside_allowed_regions_changed_pixels':count,
            'allowed_padding_pt':PAD,'header_rule_adjustment':profile.get('header_rule_adjustment')}


def overlay_one(year,part,target,profile,check_only=False):
    before_sha=sha(target)
    before=fitz.open(target)
    existing=[]
    for page in before:
        try:
            existing.append(verify_page(page,profile))
        except ValueError:
            existing=None
            break
    if existing is not None:
        before.close()
        return {'file':target.relative_to(ROOT).as_posix(),'year':year,'part':part,
                'changed':False,'sha256':before_sha,'pages':existing,
                'verification':'Existing date text/font/point/bbox correct; no bytes rewritten'}
    if check_only:
        raise ValueError(f'Missing or incorrect sitting date: {target.name}')
    WORK.mkdir(exist_ok=True)
    backup=WORK/'before'/target.name
    backup.parent.mkdir(exist_ok=True)
    if backup.is_file() and sha(backup)!=before_sha:
        backup=backup.with_name(target.stem+'-'+before_sha[:12]+'.pdf')
    shutil.copyfile(target,backup)
    changed=fitz.open(target)
    for page in changed:
        box=date_box(page,profile)+(-PAD,-PAD,PAD,PAD)
        page.add_redact_annot(box,fill=(1,1,1))
        page.apply_redactions(images=0,graphics=0)
        draw_exam_date(page,year,part)
    temporary=WORK/(target.stem+'.new.pdf')
    changed.save(temporary,garbage=4,deflate=True)
    changed.close()
    after=fitz.open(temporary)
    verified=[verify_page(page,profile) for page in after]
    pixelcheck=outside_pixels(before,after,profile)
    before.close();after.close()
    if sha(target)!=before_sha:
        raise RuntimeError(f'Concurrent change detected; target retained: {target}')
    os.replace(temporary,target)
    return {'file':target.relative_to(ROOT).as_posix(),'year':year,'part':part,
            'changed':True,'before_sha256':before_sha,'sha256':sha(target),
            'backup':backup.relative_to(ROOT).as_posix(),'pages':verified,
            'pixel_check':pixelcheck}


def run(modern_only=False,check_only=False):
    report={'scope':'modern24' if modern_only else 'all29','check_only':check_only,
            'font_and_date_source':'tools/kphe_exam_dates.json','files':[]}
    suffix=('modern' if modern_only else 'all')+('-check' if check_only else '')
    report_path=WORK/f'validation-{suffix}.json'
    previous={}
    if report_path.is_file():
        previous={entry['file']:entry for entry in json.loads(report_path.read_text(encoding='utf-8'))['files']}
    for year,part,target,profile in selected(modern_only):
        result=overlay_one(year,part,target,profile,check_only)
        prior=previous.get(result['file'],{})
        if not result['changed'] and prior.get('sha256')==result['sha256']:
            for field in ('pixel_check','before_sha256','backup'):
                if field in prior:
                    result[field]=prior[field]
        report['files'].append(result)
        print(json.dumps({'file':target.name,'changed':result['changed'],
                          'pages':len(result['pages']),'verified':True}),flush=True)
        WORK.mkdir(exist_ok=True)
        report_path.write_text(
            json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--modern-only',action='store_true')
    parser.add_argument('--check-only',action='store_true')
    args=parser.parse_args()
    result=run(args.modern_only,args.check_only)
    print(json.dumps({'passed':True,'files':len(result['files']),
        'pages':sum(len(f['pages']) for f in result['files']),
        'changed':sum(f['changed'] for f in result['files'])}),flush=True)

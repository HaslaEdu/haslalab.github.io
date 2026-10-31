"""Reviewed two-dimensional native math atoms for CPhO natural line repair."""
import json
import pymupdf as fitz
from pdf_native_inline_reposition import inspect_inline_groups
from cpho_natural_spacing import ROOT,native_records,baseline


def explicit_image_atoms(spec):
    path=ROOT/f'tools/ko/cpho/{spec["year"]}/natural/atomic-images.json'
    if not path.exists():return[]
    data=json.loads(path.read_text('utf8'))
    if data['source_sha256']!=spec['original_sha256']:raise ValueError('Reviewed mathematical bitmap source SHA changed')
    rules=[v for v in data['images']if v['page']==spec['page']]
    if not rules:return[]
    current=inspect_inline_groups(spec['input'],spec['input_page'])
    original=inspect_inline_groups(baseline(spec['year'],spec['language']),spec['page'])
    result=[]
    for rule in rules:
        def select(inv):
            matches=[i for i in inv['images']if i['original_raw_sha256']==rule['original_raw_sha256']and all(abs(a-b)<.01 for a,b in zip(i['bbox'],rule['paint_rect']))]
            if len(matches)!=1:raise ValueError('A mathematical bitmap is not one exact original paint instance')
            if matches[0]['ancestor_clip_rects']:raise ValueError('Reviewed alpha ink bounds require a separate clip-aware source proof')
            return matches[0]
        image=select(current);old=select(original);box=rule['alpha_ink_rect']
        result.append(dict(text=rule['label'],kind='native',glyphs=[],x0=box[0],x1=box[2],y=rule['baseline'],
            size=rule['size'],fonts=[],bbox=box,shift_kwargs=dict(image_path=image['path']),
            original_image_path=old['path'],atomic_native_group='original mathematical bitmap',source_rule=rule))
    return result


def explicit_atoms(spec):
    path=ROOT/f'tools/ko/cpho/{spec["year"]}/natural/atomic-inline.json'
    if not path.exists():return[]
    rules=json.loads(path.read_text('utf8'))
    if rules['source_sha256']!=spec['original_sha256']:raise ValueError('Reviewed atomic math source SHA changed')
    rules=[r for r in rules['atoms'] if r['page']==spec['page']]
    if not rules:return[]
    inv=inspect_inline_groups(spec['input'],spec['input_page'])
    native=native_records(spec['year'],spec['page'],spec['input'],spec['input_page']);result=[]
    for rule in rules:
        box=fitz.Rect(rule['rect']);glyphs=[dict(g,gid=g['trace_gid']) for g in native
            if g['c'].strip() and g['trace_gid']>=0 and box.contains(fitz.Point(g['origin']))]
        if len(glyphs)!=rule['expected_physical_glyphs']:
            raise ValueError(('Reviewed native math atom glyph count changed',rule,len(glyphs)))
        paths=[]
        for rect in rule['vector_rects']:
            candidates=[p for p in inv['vector_paths'] if all(abs(a-b)<.01 for a,b in zip(p['rect'],rect))]
            if len(candidates)!=1:raise ValueError('Reviewed original fraction bar is not one exact source path')
            paths.append(candidates[0])
        x0=min([g['origin'][0] for g in glyphs]+[p['rect'][0] for p in paths])
        x1=max([g['bbox'][2] for g in glyphs]+[p['rect'][2]+.24 for p in paths])
        result.append(dict(text=rule.get('label','[native E fraction]'),kind='native',glyphs=glyphs,x0=x0,x1=x1,
            y=rule['baseline'],size=max(g['size'] for g in glyphs),fonts=sorted({g['font'] for g in glyphs}),
            shift_kwargs=dict(vector_paths=paths),atomic_native_group='reviewed native fraction',
            bbox=rule['rect'],source_rule=rule))
    return result

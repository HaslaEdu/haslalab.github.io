"""Keep the reviewed mixed-face 2022 English date as one centered line.

The SimHei face stage already lays out the complete date with the original
Calibri numeral CIDs. Those interleaved numbers must not be repacked as a
single source trace followed by all of the newly translated words.
"""
import json
import pymupdf as fitz
import cpho_natural_spacing as core
from pdf_native_inline_reposition import _traces


def verify(path):
    plan=json.loads(path.with_suffix('.plan.json').read_text('utf8'))
    date=next(p for p in plan['prose_placements']if p['id']=='1-1-0')
    with fitz.open(path)as doc:
        glyphs=sorted([g for g in _traces(doc[0])if g['c'].strip()and g['trace_gid']>=0
            and abs(g['origin'][1]-date['point'][1])<.02],key=lambda g:g['origin'][0])
        center=doc[0].rect.width/2
    actual=''.join(g['c']for g in glyphs)
    if actual!=''.join(date['text'].split()):raise ValueError(('English date changed visible order',actual,date['text']))
    if {g['font']for g in glyphs}!={'Calibri','SimHei'}:raise ValueError('English date must retain Calibri numbers and original-family SimHei prose')
    if any(abs(g['size']-date['size'])>.0001 for g in glyphs):raise ValueError('Date point size changed')
    left=min(g['origin'][0]for g in glyphs);right=max(g['bbox'][2]for g in glyphs)
    error=abs((left+right)/2-center)
    if error>.001:raise ValueError(('Full date is not centered',error))
    return dict(passed=True,visible_text=date['text'],visible_sequence=actual,
        source_numeric_face='Calibri',translated_prose_face='SimHei5.03',
        source_point_size=date['size'],source_baseline=date['point'][1],
        full_line_center_error_pt=error,
        method='Keep the complete centered English face-stage date unchanged; original numerical CID/font/size/y are retained.')


def build():
    prepare=core.prepare
    def locked_prepare(year,language,number,*args,**kwargs):
        spec=prepare(year,language,number,*args,**kwargs)
        staged_input=args[0]if args else kwargs.get('input_path')
        if (year,language,number)==(2022,'en',1)and staged_input is not None:
            date=next(p for p in spec['prose_placements']if p['id']=='1-1-0')
            y=date['point'][1]
            scopes=[r for r in spec['regions']if abs(r['baseline']-y)<.02]
            if len(scopes)!=1:raise ValueError('Reviewed whole English date is not one source scope')
            spec['regions']=[r for r in spec['regions']if r not in scopes]
            spec['centered_lines']=[r for r in spec['centered_lines']if abs(r['baseline']-y)>=.02]
            spec['locked_reviewed_date_scope']=dict(text=date['text'],baseline=y,region=scopes[0],
                reason='Already composed and centered as a complete mixed-face prose line in the English face stage.')
        return spec
    core.prepare=locked_prepare
    try:path=core.build(2022,'en',1)
    finally:core.prepare=prepare
    report=verify(path);q=json.loads(path.with_suffix('.qa.json').read_text('utf8'))
    q['whole_English_date_review']=report
    path.with_suffix('.qa.json').write_text(json.dumps(q,ensure_ascii=False,indent=2),'utf8')
    return path

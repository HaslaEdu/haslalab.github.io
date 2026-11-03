"""Actual PDF counterexamples for the narrowly source-bound p32 amendment."""
from pathlib import Path
from io import BytesIO
import hashlib
import json
import sys
sys.dont_write_bytecode = True
import pikepdf
import pymupdf as fitz
import audit_p32_source_stroke_support as audit

A=Path(__file__).resolve().parent
F=audit.F
good=F/'page32.pdf'
q=json.loads(good.with_suffix('.layout.json').read_text('utf8'))
positive=audit.audit(good)
results=[]


def save(pdf):
    out=BytesIO();pdf.save(out,compress_streams=False);return out.getvalue()


def rejected(name,data,error,actual_mutation,layout_edit=None):
    folder=A/'actual-PDF-negatives'/name;folder.mkdir(parents=True,exist_ok=False)
    p=folder/'page32.pdf';p.write_bytes(data)
    fake=json.loads(json.dumps(q));fake['output_sha256']=audit.sha(p)
    if layout_edit:layout_edit(fake)
    lp=p.with_suffix('.layout.json');lp.write_text(json.dumps(fake,ensure_ascii=False,indent=2)+'\n','utf8')
    try:
        audit.audit(p)
    except AssertionError as exc:
        assert error in str(exc),(name,str(exc))
        results.append(dict(case=name,rejected=True,actual_PDF_mutation=actual_mutation,
            fake_layout_fresh_output_sha256_supplied=True,proof_sha256=audit.sha(p),layout_sha256=audit.sha(lp),
            expected_actual_check=error,observed_error=str(exc)[:7000]))
    else:raise AssertionError(name+' accepted an actual PDF mutation')


# Erase a segment of the original header rule, far from both named correction rows.
with fitz.open(good) as doc:
    rules=[d for d in doc[0].get_drawings() if d['rect'].width>100 and d['rect'].height<.01 and d['rect'].y0<200]
    assert rules
    r=list(rules[0]['rect']);erase=[r[0]+5,r[1]-1,r[0]+10,r[1]+1]
with pikepdf.open(good) as pdf:
    page=pdf.pages[0];old=list(page.Contents) if isinstance(page.Contents,pikepdf.Array) else [page.Contents]
    h=float(page.MediaBox[3])-float(page.MediaBox[1])
    code=f'q 1 1 1 rg {erase[0]:.12f} {h-erase[3]:.12f} {erase[2]-erase[0]:.12f} {erase[3]-erase[1]:.12f} re f Q'
    page.Contents=pikepdf.Array([pdf.make_stream(b'q\n'),*old,pdf.make_stream(b'\nQ\n'),pdf.make_stream(code.encode('ascii'))])
    erased=save(pdf)
rejected('unrelated-native-header-rule-erased',erased,'Actual pixels outside exact source/target stroke support union',
    dict(kind='white paint removes real native header stroke',rect=erase,no_text_glyph_changed=True))

# Move the original native numeral5 only; retain its font/GID/point/baseline.
with fitz.open(good) as doc:
    gs=audit.visible(doc[0])
    group=next(v for v in q['native_shifts'] if len(v['glyphs'])==1 and v['glyphs'][0]['c']=='5' and v['glyphs'][0]['size']>15 and v['glyphs'][0]['origin'][1]<200)
    source_native=group['glyphs'][0]
    expected=[source_native['origin'][0]+group['dx'],source_native['origin'][1]]
    chosen=[g for g in gs if g['c']==source_native['c'] and g['gid']==source_native['gid'] and g['size']==source_native['size'] and max(abs(x-y)for x,y in zip(g['origin'],expected))<.001]
assert len(chosen)==1,('Actual source-native numeral matching known GID/point/position',source_native,expected,chosen)
g=chosen[0]
assert not any(abs(g['origin'][1]-y)<.001 for y in positive['source_bound_changed_row_baselines'])
data,move_audit=audit.c.motion.reposition_inline(good,1,
    shifts=[dict(glyphs=[{k:g[k] for k in ['c','gid','font','size','origin','bbox','paint']}],dx=.75)],validate=True)
assert move_audit['passed']
with fitz.open(stream=data,filetype='pdf') as doc:
    after=audit.visible(doc[0])
    candidates=[v for v in after if v['c']==g['c'] and v['font']==g['font'] and v['gid']==g['gid'] and v['size']==g['size']
        and abs(v['origin'][0]-g['origin'][0]-.75)<.001 and v['origin'][1]==g['origin'][1]]
assert len(candidates)==1
rejected('original-native-numeral5-moved',data,'Actual visible glyph geometry differs from audited immutable p32 proof',
    dict(kind='original native numeral5 moved .75pt horizontally outside named rows',original_source_native=source_native,source_to_current_dx=group['dx'],original_actual=g,actual=candidates[0],motion_audit_passed=True))

# Replace the actual reviewed Some-hints construction with another source path.
spec=next(v for v in q['prose_vector_decorations'] if v['semantic_mapping_index']==34)
fragment=spec['source_program']['source_construction_and_paint_fragment_latin1'].encode('latin1')
replacement=b' 42.691 -416.399 m 70.049 -416.399 l S'
with pikepdf.open(good) as pdf:
    page=pdf.pages[0];streams=list(page.Contents) if isinstance(page.Contents,pikepdf.Array) else [page.Contents]
    changed=0
    for stream in streams:
        raw=stream.read_bytes()
        if fragment in raw:
            assert raw.count(fragment)==1;stream.write(raw.replace(fragment,replacement));changed+=1
    assert changed==1
    badpath=save(pdf)
rejected('actual-source-path-replaced',badpath,'Original source underline construction bytes missing or replaced',
    dict(kind='actual m/l/S source construction replaced by the other underline path',
        original_fragment_sha256=hashlib.sha256(fragment).hexdigest(),replacement_fragment_sha256=hashlib.sha256(replacement).hexdigest()))

def expand_declared_mask(fake):
    row=next(v for v in fake['line_reports'] if abs(v['baseline']-486.906982421875)<.001)
    row['left']=0;row['right']=600;row['source_bounds']=[0,0,600,500]
rejected('forged-layout-expands-mask-around-erased-native-rule',erased,'Certified layout changed beyond output_sha256',
    dict(kind='same actual native-rule deletion plus fake changed row bounds; layout-binding control, not an extra PDF pixel-test claim'),expand_declared_mask)
assert len(results)==4
report=dict(status='PASS',actual_PDF_counterexamples=3,additional_layout_binding_counterexamples=1,all_rejected=True,
    positive_proof_sha256=audit.sha(good),positive_layout_sha256=audit.sha(good.with_suffix('.layout.json')),
    positive_actual_source_support_audit_program_sha256=audit.sha(audit.__file__),program_sha256=audit.sha(__file__),cases=results)
out=A/'actual-PDF-negative-regressions.json';assert not out.exists()
out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n','utf8')
print('P32-THREE-ACTUAL-PDF-PLUS-LAYOUT-BINDING-NEGATIVES-PASS',out,audit.sha(out),flush=True)

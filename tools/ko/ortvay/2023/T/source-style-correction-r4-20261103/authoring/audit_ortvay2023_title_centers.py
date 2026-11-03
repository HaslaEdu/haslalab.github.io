"""Independently verify actual source and new title glyph geometry."""
from pathlib import Path
import json,hashlib
import pymupdf as f
from PIL import Image,ImageChops,ImageDraw
import ortvay2023_write_guard as g
B=g.B;P=g.PROOF_ROOT/'page01.pdf'
old=g.PROOF_ROOT/'superseded/pre-title-center-engine-5fd90839/page01.pdf'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
q=json.loads(P.with_suffix('.layout.json').read_text('utf8'))
assert q['output_sha256']==sha(P)
source=f.open(q['source']);target=f.open(P);prior=f.open(old)
def glyphs(page):
    return [dict(c=chr(cp),gid=gid,font=t['font'],size=t['size'],origin=list(origin),bbox=list(bbox),type=t['type'])
            for t in page.get_texttrace()for cp,gid,origin,bbox in t['chars']]
sg=glyphs(source[0]);tg=glyphs(target[0]);og=glyphs(prior[0])
profile=json.loads((g.PROFILE_ROOT/'title-center-source-profile.json').read_text('utf8'))
rows=[]
for spec in profile['rows']:
    baseline=spec['baseline']
    def row(items):return [v for v in items if v['type']!=3 and v['c'].strip()and abs(v['origin'][1]-baseline)<.001]
    a=row(sg);b=row(tg);c=row(og)
    assert len(b)==len(c)
    ac=(min(v['bbox'][0]for v in a)+max(v['bbox'][2]for v in a))/2
    bc=(min(v['bbox'][0]for v in b)+max(v['bbox'][2]for v in b))/2
    assert abs(ac-bc)<=.001
    dx=ac-(min(v['bbox'][0]for v in c)+max(v['bbox'][2]for v in c))/2
    errors=[]
    for before,after in zip(c,b):
        assert (before['c'],before['gid'],before['font'],before['size'])==(after['c'],after['gid'],after['font'],after['size'])
        assert before['origin'][1]==after['origin'][1]==baseline
        error=max(abs(after['origin'][0]-before['origin'][0]-dx),
                  *(abs(x-y-(dx if i%2==0 else 0))for i,(x,y)in enumerate(zip(after['bbox'],before['bbox']))))
        assert error<=.001;errors.append(error)
    rows.append(dict(baseline=baseline,source_center_pt=ac,actual_target_center_pt=bc,
                     center_error_pt=abs(ac-bc),only_horizontal_translation_pt=dx,
                     glyphs=len(b),max_glyph_translation_error_pt=max(errors),
                     original_source_point_size_pt=a[0]['size'],actual_target_point_size_pt=b[0]['size'],
                     unchanged_glyphs_font_GIDs_size_baseline=True))
assert [v for v in og if v['origin'][1]>=170]==[v for v in tg if v['origin'][1]>=170]
with Image.open(old.with_suffix('.png'))as before,Image.open(P.with_suffix('.png'))as after:
    assert before.size==after.size
    diff=ImageChops.difference(before.convert('RGB'),after.convert('RGB'))
    ImageDraw.Draw(diff).rectangle([0,65*1.5,before.width,157*1.5],fill=(0,0,0))
    assert diff.getbbox()is None
report=dict(schema='ortvay2023-independent-actual-source-title-center-audit-v1',passed=True,
            program_sha256=sha(Path(__file__)),
            source_sha256=q['source_sha256'],proof_sha256=sha(P),layout_sha256=sha(P.with_suffix('.layout.json')),
            previous_proof_sha256=sha(old),composer_sha256=q['composer_sha256'],position_tolerance_pt=.001,
            rows=rows,nonheader_all_glyph_traces_identical=True,nonheader_changed_pixels=0)
out=g.PROOF_ROOT/'original-title-center-independent-audit.json'
out.write_text(json.dumps(report,ensure_ascii=False,indent=2),'utf8')
source.close();target.close();prior.close()
print(json.dumps(dict(passed=True,max_center_error_pt=max(v['center_error_pt']for v in rows),path=str(out))))

from pathlib import Path
import json,sys,hashlib
import pymupdf as f
B=Path(__file__).resolve().parent;sys.path.insert(0,str(B/'engine'))
import latex_native_motion as m
import icho2019_write_guard as g
source=m.inspect_inline_groups(g.SOURCE,2)
paths=[p for p in source['vector_paths']if max(abs(a-b)for a,b in zip(p['rect'],[262.1300048828125,104.05999755859375,273.1700134277344,117.5]))<.001]
assert len(paths)==1
doc=f.open(g.SOURCE);page=doc[1]
glyphs=[dict(c=chr(cp),gid=gid,font=t['font'],size=t['size'],origin=list(origin),bbox=list(bbox),paint=t['type'])for t in page.get_texttrace()if t['type']!=3 for cp,gid,origin,bbox in t['chars']if chr(cp).strip()and 262<=origin[0]<274 and 104<=origin[1]<=117.5]
drawings=[d for d in page.get_drawings()if max(abs(a-b)for a,b in zip(d['rect'],paths[0]['rect']))<.001]
assert len(drawings)==1 and drawings[0]['fill']==(1.,1.,0.)
assert ''.join(v['c']for v in glyphs)=='60',glyphs
spec=dict(id='p2-original-yellow-60-highlight',source_sha256=g.SOURCE_SHA,glyphs=glyphs,vector_path=paths[0],rendered_source_rect=list(drawings[0]['rect']),fill=list(drawings[0]['fill']),review='Original yellow rectangle highlights exactly the native page count60; translate its original glyph and complete pure vector path together without resizing, restyling or repainting.')
(B/'page02-native-highlight-profile.json').write_text(json.dumps(spec,ensure_ascii=False,indent=2)+'\n','utf8')
print(json.dumps(spec,ensure_ascii=False),flush=True)

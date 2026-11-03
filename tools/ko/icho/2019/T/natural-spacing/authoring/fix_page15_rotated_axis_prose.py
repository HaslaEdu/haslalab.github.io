"""Retain original 90-degree axis typography and native V/SHE glyphs."""
from pathlib import Path
import json
import pymupdf as f
import icho2019_write_guard as g
B=Path(__file__).resolve().parent;path=B/'page15.overrides.json';q=json.loads(path.read_text('utf8'));edits=q.setdefault('__slot_edits__',{})
for id in['p15:b18:l0:s0-0:c1-5','p15:b18:l0:s0-0:c8-9']:edits.setdefault(id,{})['text']=''
doc=f.open(g.SOURCE);l=doc[14].get_text('rawdict')['blocks'][18]['lines'][0];assert l['dir'][1]==-1. and abs(l['dir'][0])<1e-8
s=l['spans'][0];chars=s['chars'];assert ''.join(c['c']for c in chars)=='V vs SHE '
labels=[]
for id,index,text in[('p15-axis-comma',2,','),('p15-axis-reference',8,' 기준')]:
    labels.append(dict(id=id,source_label_kind='selectable-source-graphic-prose',source_sha256=g.SOURCE_SHA,source_slot_id='p15:b18:l0:s0-0:c1-5'if index==2 else'p15:b18:l0:s0-0:c8-9',source_chars=chars[1:5]if index==2 else chars[8:9],source_font=s['font'],source_size=s['size'],source_direction=l['dir'],text=text,point=chars[index]['origin'],size=s['size'],font_role='sans',rotate=90,source_font_point_and_baseline_metadata_available=True,review='Exact original Arial14.04pt axis direction90deg and source origins retained. Native V and SHE are untouched. Korean reads V, SHE 기준; no image mask or resized/native redrawn symbols.'))
q['__selected_graphic_labels__']=labels;path.write_text(json.dumps(q,ensure_ascii=False,indent=2)+'\n','utf8')

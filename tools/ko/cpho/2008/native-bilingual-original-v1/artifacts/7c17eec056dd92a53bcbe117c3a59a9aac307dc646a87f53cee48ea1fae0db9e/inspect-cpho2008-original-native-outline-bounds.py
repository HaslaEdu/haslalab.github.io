"""Read actual source SVG glyph paths to bind native ink overhang to atoms."""
from pathlib import Path
from io import BytesIO
import sys,json,re,hashlib,xml.etree.ElementTree as ET
import pymupdf as f
from fontTools.svgLib.path import parse_path
from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.transformPen import TransformPen
B=Path(__file__).resolve().parents[1]
sys.path.insert(0,'D:/CodexBuilds/Hasla-publish-20261031/tools')
from pdf_memory_gate import page_worker
S=B/'source/CPhO_2008_original_combined_ZH.pdf'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
authored='--authored'in sys.argv;args=[v for v in sys.argv[1:]if v!='--authored']
for n in map(int,args):
 with page_worker():
  with f.open(S)as doc:svg=doc[n-1].get_svg_image(text_as_path=True)
  root=ET.fromstring(svg);defs={v.get('id'):v for v in root.iter()if v.get('id')};uses=[]
  for v in root.iter():
   if 'data-text'not in v.attrib:continue
   match=re.fullmatch(r'matrix\(([^)]+)\)',v.get('transform',''))
   assert match,ET.tostring(v)
   matrix=list(map(float,match[1].replace(',',' ').split()))
   ref=(v.get('{http://www.w3.org/1999/xlink}href')or v.get('href')).lstrip('#');d=defs[ref].get('d','')
   pen=BoundsPen(None)
   if d:parse_path(d,TransformPen(pen,matrix))
   uses.append(dict(c=v.get('data-text'),origin=matrix[-2:],actual_original_outline_bounds=list(pen.bounds)if pen.bounds else None,source_svg_ref=ref,actual_original_outline_path_sha256=hashlib.sha256(d.encode()).hexdigest(),actual_original_transform=matrix))
  plan=B/f'authoring/page{n:02}-native-language.json'if authored else B/f'authoring/page{n:02}-native-row-proposals.json';q=json.loads(plan.read_text('utf8'));atoms=[]
  for row in q['rows']:
   for a in row['native_atoms']:
    records=[]
    for g in a['glyphs']:
     matched=[v for v in uses if v['c']==g['c']and max(abs(x-y)for x,y in zip(v['origin'],g['origin']))<.003]
     assert len(matched)==1,(n,a['id'],g,matched)
     records.append(matched[0])
    bounds=[v['actual_original_outline_bounds']for v in records if v['actual_original_outline_bounds']]
    rect=a['rect'];ink=[min(v[0]for v in bounds),min(v[1]for v in bounds),max(v[2]for v in bounds),max(v[3]for v in bounds)]if bounds else rect
    atoms.append(dict(id=a['id'],source_metric_rect=rect,actual_original_ink_rect=ink,complete_glyphs=records))
  result=dict(source_sha256=sha(S),source_page=n,authoring_selections_path=str(plan),authoring_selections_sha256=sha(plan),method='actual original native CID-resolved SVG path + literal glyph transform; no PDF/font/math changes',atoms=atoms)
  suffix='-authored'if authored else'';p=B/f'inspection/page{n:02}{suffix}-original-native-outline-bounds.json';assert not p.exists(),'Original outline evidence must be immutable';p.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n','utf8')
  print('SOURCE_NATIVE_OUTLINE_BOUNDS',n,[(v['id'],v['source_metric_rect'],v['actual_original_ink_rect'])for v in atoms if v['actual_original_ink_rect'][0]<v['source_metric_rect'][0]or v['actual_original_ink_rect'][2]>v['source_metric_rect'][2]],flush=True)

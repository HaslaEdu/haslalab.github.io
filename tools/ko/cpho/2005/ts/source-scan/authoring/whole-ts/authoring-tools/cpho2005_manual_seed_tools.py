"""Generate private tools from explicitly authored source geometry, never infer it."""
from pathlib import Path
import json
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/cpho2005/TS')
def generate(page,rows,samples,geometry,protected,specs,right_edges=None,ko_math_gaps=None,center_slots=None):
 name=f'page{page:02}';source='9867b5116f1feb921515844332d43ed08a7c790292d5eecd89c70aacdf698b4f'
 data=[('authoring/'+name+'-language-row-proposals.json',dict(rows=rows,reviewed=False,scope='Explicit human-authored bilingual source-line translations; no mathematical retyping.')),
  (name+'-row-baseline-proposals.json',dict(rows=samples,scope='Explicit human-read original CJK-only source measurement samples, not erase geometry.')),
  ('authoring/'+name+'-source-geometry-proposal.json',dict(source_sha256=source,geometry=geometry,protected=protected,math_specs=specs,right_edges=right_edges or{},ko_math_gaps=ko_math_gaps or{},center_slots=center_slots or{},reviewed=False))]
 for path,value in data:(B/path).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n','utf8')
 for what in ['per-row-type','row-weights']:
  s=Path(f'D:/CodexBuilds/calibrate-cpho2005-page08-{what}.py').read_text('utf8').replace('page08',name).replace('source[7]',f'source[{page-1}]').replace('original[7]',f'original[{page-1}]').replace('page=8',f'page={page}')
  if what=='per-row-type':
   s=s.replace("old['source_text']==row['source_text']:","old['source_text']==row['source_text'] and old.get('source_size_range',[11.5,14.751,.025])==row.get('source_size_range',[11.5,14.751,.025]):")
   s=s.replace('for size in np.arange(11.5,14.751,.025):',"for size in np.arange(*row.get('source_size_range',[11.5,14.751,.025])):")
   s=s.replace("for size in np.arange(7.5 if row['id']=='caption'else 11.5,14.751,.025):", "for size in np.arange(*row.get('source_size_range',[11.5,14.751,.025])):")
   s=s.replace("source_measurement_window=rect,best=", "source_measurement_window=rect,source_size_range=row.get('source_size_range',[11.5,14.751,.025]),best=")
  Path(f'D:/CodexBuilds/calibrate-cpho2005-{name}-{what}.py').write_text(s,'utf8')
 s=Path('D:/CodexBuilds/propose-cpho2005-page08-native-math.py').read_text('utf8');a=s.index('specs=[]');b=s.index('S=8;out=[]',a)
 s=s[:a]+f"specs=json.loads((B/'authoring/{name}-source-geometry-proposal.json').read_text('utf8'))['math_specs']\n"+s[b:]
 a=s.index('corrections=');b=s.index('boxes=',a);s=s[:a]+s[b:]
 s=s.replace('page08',name).replace("original.pdf',8)",f"original.pdf',{page})").replace('page=d[7]',f'page=d[{page-1}]').replace('page=8',f'page={page}')
 s=s.replace("  touched=bool(","  rect=spec.get('reviewed_rect',rect)\n  touched=bool(")
 Path(f'D:/CodexBuilds/propose-cpho2005-{name}-native-math.py').write_text(s,'utf8')
 s=Path('D:/CodexBuilds/author-cpho2005-ts-page08-layout.py').read_text('utf8').replace('page08',name).replace('source[7]',f'source[{page-1}]').replace('source_page=8',f'source_page={page}').replace('PAGE08',name.upper())
 a=s.index('geometry={');b=s.index('\nrows=[]',a);s=s[:a]+f"source_geometry=json.loads((B/'authoring/{name}-source-geometry-proposal.json').read_text('utf8'));geometry=source_geometry['geometry']"+s[b:]
 a=s.index('protected_source_display_and_figure_rects=');b=s.index('\nerrors=[]',a);s=s[:a]+"protected_source_display_and_figure_rects=source_geometry['protected'])\n"+s[b:]
 s=s.replace("({'eq11-12':.5,'F-prime':.75} if id=='recovery-force-first'else{})", "source_geometry['ko_math_gaps'].get(id,{})")
 s=s.replace('right=409.95 if left<420 else 784.85','right=source_geometry[\'right_edges\'].get(id,409.95 if left<420 else 784.85)')
 s=s.replace('erase_rects=[erase]', 'erase_rects=erase if isinstance(erase[0],list)else[erase]')
 s=s.replace(';w=weights[id];ids=', ";w=weights[id];assert w['source_point_size']==t['best']['source_point_size'] and w['source_measurement_window']==t['source_measurement_window'];ids=")
 s=s.replace('  try:row_layout(row,lang,metric)',"  try:\n   if row['id']in source_geometry['center_slots']:\n    _,end=row_layout(row,lang,metric);center=source_geometry['center_slots'][row['id']]['original_source_center']\n    row.setdefault('left_by_language',{})[lang]=center-(end-row['left'])/2;row['original_source_center']=center\n   row_layout(row,lang,metric)")
 Path(f'D:/CodexBuilds/author-cpho2005-ts-{name}-layout.py').write_text(s,'utf8')
 print('GENERATED_PRIVATE_MANUAL_SOURCE_SEED_TOOLS',page,len(rows),len(specs),flush=True)

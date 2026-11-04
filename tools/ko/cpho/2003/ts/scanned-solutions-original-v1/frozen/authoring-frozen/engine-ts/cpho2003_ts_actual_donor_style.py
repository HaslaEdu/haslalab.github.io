"""Independent actual embedded outlines/advances/points, not a cached-font assertion."""
from pathlib import Path
from io import BytesIO
from collections import Counter
import sys,json,hashlib,re
import pikepdf,pymupdf as f
from fontTools.ttLib import TTFont
from fontTools.pens.recordingPen import DecomposingRecordingPen
B=Path('C:/Users/andre/CodexWork/HaslaLab/translation-builds/cpho2003-original-native');T=B/'TS'
sys.path[:0]=[str(T/'engine'),str(B/'engine'),'D:/CodexBuilds']
from pdf_memory_gate import page_worker
from izho_new_prose_outline_qa import trace_font_resources
from pdf_native_inline_reposition import _traces
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def shape(font,gid):
 gs=font.getGlyphSet();p=DecomposingRecordingPen(gs);gs[font.getGlyphOrder()[gid]].draw(p);u=font['head'].unitsPerEm
 def norm(v):
  if isinstance(v,(tuple,list)):return[norm(x)for x in v]
  return round(v/u,8)if isinstance(v,(int,float))else v
 return hashlib.sha256(json.dumps(norm(p.value),separators=(',',':')).encode()).hexdigest()
def audit(number,lang,proof_override=None,output_override=None):
 reference=T/f'proofs/{lang}/page{number:02}.pdf';proof=Path(proof_override)if proof_override else reference;output=Path(output_override)if output_override else proof.with_suffix('.actual-donor-style-and-advances.json')
 if output.exists():
  old=json.loads(output.read_text('utf8'));assert old['passed']and old['proof_sha256']==sha(proof);return old
 layout=json.loads((T/f'authoring/page{number:02}-layout.json').read_text('utf8'));composition=json.loads(reference.with_suffix('.composition.json').read_text('utf8'))
 inventory=json.loads((T/'inputs/native-slots.json').read_text('utf8'));slots={r['id']:r for r in inventory['pages'][number-1]['slots']}
 assert composition['output_sha256']==sha(reference)
 for suffix in ['.source-qa.json','.poppler-qa.json']:
  positive=json.loads(reference.with_suffix(suffix).read_text('utf8'));assert positive['passed'] and positive.get('proof_sha256',positive.get('final_sha256',positive.get('output_sha256')))==sha(reference),(suffix,'Positive current-renderer proof is not pinned')
 pins=json.loads((B/'inputs/external-font-source-pins.json').read_text('utf8'));donors={}
 for pin in pins:
  p=Path(pin['path']);name=p.name.lower();role='Batang'if name=='batang.ttc'else'SimSun'if name.startswith('simsun')else'SimHei'if name=='simhei.ttf'else'NotoSansCJKkr-Regular'if name.startswith('notosans')else None
  if role is None:continue
  assert sha(p)==pin['sha256'];donors[role]=(TTFont(p,fontNumber=0)if p.suffix.lower()=='.ttc'else TTFont(p),pin)
 embedded={};cache={};checked=[];centers=[]
 with pikepdf.open(proof)as pdf,f.open(proof)as doc:
  actual,programs=trace_font_resources(pdf,doc[0]);traces=_traces(doc[0])
  for g in actual:
   if not g['font_alias'].startswith(('/TSHeader','/TSScanBody'))or g['c'].isspace():continue
   role=g['font'].replace('CPhO2003Translation','');assert role in donors,('Unexpected actual new face',g)
   if lang=='en':assert role in ['SimSun','SimHei']
   face='SimHei'if role in ['SimHei','NotoSansCJKkr-Regular']else'SimSun'
   if g['font_alias'].startswith('/TSScanBody'):
    matches=[r for r in layout['rows']if r['source_prose_face']==face and abs(r['baseline']-g['origin'][1])<=.001 and abs(r['size']-g['size'])<=1e-6]
    assert len(matches)==1,('No unique measured original scan role/point/baseline',g,matches)
    r=matches[0];assert r.get('independent_original_baseline_measurement')or r.get('source_only_baseline_evidence'),('Original-only baseline evidence absent',r['id'])
    sourceid=r['id'];point=r['size'];baseline=r['baseline'];mode=r.get('render_mode',0)
   else:
    matches=[r for r in composition['header']['placements']if r['source_font']==face and abs(r['baseline']-g['origin'][1])<=.001 and abs(r['size']-g['size'])<=1e-6]
    assert len(matches)==1,('No unique original native role/point/baseline',g,matches)
    r=matches[0];slot=slots[r['source_slot']];sourceid=slot['id'];point=slot['size'];baseline=slot['origin'][1];mode=slot['render_mode']
   assert g['render_type']==mode==0 and g['color']==[0,0,0],g
   if lang=='ko'and'\uac00'<=g['c']<='\ud7a3':assert role==('NotoSansCJKkr-Regular'if face=='SimHei'else'Batang')
   digest=g['font_program_sha256'];assert digest in programs
   if digest not in embedded:embedded[digest]=TTFont(BytesIO(programs[digest]['raw']))
   font=embedded[digest];donor,pin=donors[role];name=donor.getBestCmap().get(ord(g['c']));assert name
   donor_gid=donor.getGlyphID(name);gid=g['gid'];assert font.getBestCmap().get(ord(g['c']))==font.getGlyphOrder()[gid]
   key=(digest,gid,role,donor_gid)
   if key not in cache:
    a=shape(font,gid);b=shape(donor,donor_gid);assert a==b,('Actual PDF glyph differs from full donor',role,g['c'],gid);cache[key]=a
   advance=font['hmtx'][font.getGlyphOrder()[gid]][0]/font['head'].unitsPerEm*g['size'];full=donor['hmtx'][name][0]/donor['head'].unitsPerEm*g['size'];bbox=g['bbox'][2]-g['bbox'][0]
   assert abs(advance-full)<.001 and abs(bbox-advance)<.001,('Actual horizontal scaling or substituted advance',g,advance,full,bbox)
   same=[t for t in traces if t['c']==g['c']and t['font']==g['font']and t['trace_gid']==gid and abs(t['origin'][0]-g['origin'][0])<.001 and abs(t['origin'][1]-g['origin'][1])<.001]
   assert len(same)==1 and same[0]['direction']==(1,0)and same[0]['opacity']==1 and same[0]['wmode']==0,g
   checked.append(dict(character=g['c'],actual_font=role,actual_alias=g['font_alias'],actual_gid=gid,full_donor_gid=donor_gid,actual_point=g['size'],actual_origin=g['origin'],actual_trace_advance=bbox,embedded_hmtx_advance=advance,full_donor_hmtx_advance=full,actual_embedded_program_sha256=digest,full_role_donor_sha256=pin['sha256'],actual_decomposed_outline_sha256=cache[key],actual_outline_matches_full_donor=True,source_slot=sourceid,source_point=point,source_baseline=baseline,source_face_role=face,actual_render_mode=g['render_type']))
  for r in composition['header']['placements']:
   slot=slots[r['source_slot']]
   if slot.get('align')!='center':continue
   gs=[g for g in traces if g['c'].strip()and abs(g['origin'][1]-r['baseline'])<=.001]
   left=min(g['origin'][0]for g in gs);right=max(g['bbox'][2]for g in gs);center=(left+right)/2
   assert abs(center-slot['original_horizontal_center'])<.001,('Native original title/footer center differs',r,center)
   centers.append(dict(source_slot=slot['id'],actual_center=center,original_native_center=slot['original_horizontal_center'],source_point=slot['size'],passed=True))
  for r in layout['rows']:
   if 'source_caption_horizontal_center'not in r:continue
   gs=[g for g in traces if g['c'].strip()and abs(g['origin'][1]-r['baseline'])<=.001]
   paints=[a for a in composition['inline_math_replay']['atoms']if a['id'].startswith(r['id']+'-')]
   assert gs and paints,('Caption must contain both actual new glyphs and complete original numeric label',r['id'])
   left=min([g['origin'][0]for g in gs]+[a['destination_rect'][0]for a in paints]);right=max([g['bbox'][2]for g in gs]+[a['destination_rect'][2]for a in paints]);center=(left+right)/2
   assert abs(center-r['source_caption_horizontal_center'])<.001,('Actual combined caption center differs from manually reviewed original source frame',r['id'],center,r['source_caption_horizontal_center'])
   centers.append(dict(source_slot=r['id'],actual_combined_new_glyph_and_original_image_label_center=center,manual_original_caption_frame_center=r['source_caption_horizontal_center'],original_numeric_label_actual_math_RGB_controls_pinned=True,source_point=r['size'],passed=True))
 for r in layout['rows']:
   if 'original_horizontal_center'not in r:continue
   gs=[g for g in traces if g['c'].strip()and abs(g['origin'][1]-r['baseline'])<=.001];center=(min(g['origin'][0]for g in gs)+max(g['bbox'][2]for g in gs))/2
   assert abs(center-r['original_horizontal_center'])<.001
   centers.append(dict(source_slot=r['id'],actual_center=center,manual_original_advance_center=r['original_horizontal_center'],passed=True))
 assert checked
 expected=0
 for r in layout['rows']:expected+=sum(not c.isspace()for c in re.sub(r'\[\[[^\]]+\]\]','',r[lang]))
 for r in composition['header']['placements']:
  text=re.sub(r'\[\[[^\]]+\]\]','',r['text'])
  if r.get('original_numbers'):text=re.sub(r'\d+','',text)
  expected+=sum(not c.isspace()for c in text)
 assert len(checked)==expected,('Actual new-prose glyph coverage mismatch',len(checked),expected)
 q=dict(schema='cpho2003-scanned-original-actual-donor-style-and-advances-v1',passed=True,source_original_sha256=sha(B/'inputs/CPhO_2003_Chinese_original.pdf'),source_page=number,language=lang,proof_sha256=sha(proof),layout_sha256=sha(T/f'authoring/page{number:02}-layout.json'),native_header_plan_sha256=sha(T/f'authoring/page{number:02}.json'),actual_new_nonspace_glyphs_checked=len(checked),all_actual_embedded_outlines_and_advances_match_hash_pinned_full_role_donors=True,actual_point_sizes_and_baselines_match_native_or_original_scan_measurement=True,actual_horizontal_font_scaling=False,actual_type_size_fitting=False,source_caption_frames_checked=True,full_installed_font_programs_exported=False,glyphs=checked,original_title_footer_centers=centers)
 output.write_text(json.dumps(q,ensure_ascii=False,indent=2)+'\n','utf8');print('C03_TS_ACTUAL_FULL_DONOR_OUTLINE_POINT_ADVANCE_PASS',number,lang,len(checked),flush=True);return q

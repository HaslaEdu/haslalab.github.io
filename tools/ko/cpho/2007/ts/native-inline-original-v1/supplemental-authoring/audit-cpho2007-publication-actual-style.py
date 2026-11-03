"""Read-only final-proof font/point/paint audit; never edits the frozen master."""
from pathlib import Path
from io import BytesIO
import sys,json,hashlib,re
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/cpho2007/TS')
M=B/'master-v1';F=M/'authoring-frozen';OUT=B/'publication-adapter20261104'
sys.path.insert(0,str(F/'engine'))
from pdf_memory_gate import page_worker
from pdf_native_inline_reposition import _traces
import pymupdf as fitz
from fontTools.ttLib import TTFont
from fontTools.pens.recordingPen import DecomposingRecordingPen
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,q):
 p.parent.mkdir(parents=True,exist_ok=True);assert not p.exists(),p
 p.write_text(json.dumps(q,ensure_ascii=False,indent=2)+'\n','utf8')
def norm(s):return re.sub('[^a-z0-9]','',s.lower())
def outline(font,gid):
 gs=font.getGlyphSet();pen=DecomposingRecordingPen(gs);gs[font.getGlyphOrder()[gid]].draw(pen)
 # A subset can rename component glyphs. Decomposed geometry is compared.
 u=font['head'].unitsPerEm
 def v(x):
  if isinstance(x,(tuple,list)):return [v(a)for a in x]
  return round(x/u,8)if isinstance(x,(int,float))else x
 return hashlib.sha256(json.dumps(v(pen.value),separators=(',',':')).encode()).hexdigest()
def audit_page(lang,n):
 assert lang in ['ko','en']and 5<=n<=19
 proof=F/f'natural/2007/{lang}/page{n:02}.pdf'
 slots=json.loads((F/'inputs/original-all20-source-slots.json').read_text('utf8'))['pages'][n-1]['slots']
 plan=json.loads((F/f'natural/2007/{lang}/page{n:02}.plan.json').read_text('utf8'))
 pins=json.loads((F/'external-font-source-pins.json').read_text('utf8'))
 donors={}
 for pin in pins:
  p=Path(pin['path']);assert sha(p)==pin['sha256'];s=p.name.lower()
  role='Batang'if s=='batang.ttc'else 'SimSun'if s.startswith('simsun')else 'SimHei'if s=='simhei.ttf'else 'NotoSerifCJKkr-Regular'if s.startswith('notoserif')else 'NotoSansCJKkr-Regular'
  font=TTFont(p,fontNumber=0)if p.suffix.lower()=='.ttc'else TTFont(p)
  donors[role]=(font,pin,{})
 with fitz.open(F/'inputs/CPhO_2007_Chinese_original.pdf')as source:
  native_names={g['font']for pg in source for g in _traces(pg)}
 with fitz.open(proof)as doc:
  page=doc[0];embedded={}
  for row in page.get_fonts(full=True):
   if row[3]in native_names:continue
   xref=row[0];name,ext,typ,raw=doc.extract_font(xref)
   if not raw:continue
   try:font=TTFont(BytesIO(raw))
   except Exception:continue
   keys={norm(fitz.Font(fontbuffer=raw).name)}
   keys.update(norm(r.toUnicode())for r in font['name'].names if r.nameID==6)
   for key in keys:embedded.setdefault(key,[]).append((font,hashlib.sha256(raw).hexdigest()))
  rows=[]
  for g in _traces(page):
   if not g['c'].strip()or g['font']in native_names or g['render_mode']==3:continue
   role=g['font'];assert role in donors,('Unknown translated font',role)
   expected=('SimSun'if role=='SimSun'else 'SimHei'if role=='SimHei'else role)
   fam='sans'if expected in ['SimHei','NotoSansCJKkr-Regular']else 'serif'
   candidates=[s for s in slots if s['family']==fam and abs(s['origin'][1]-g['origin'][1])<=.002 and abs(s['size']-g['size'])<=1e-6]
   assert candidates,('No original source role/size/baseline for translated glyph',g)
   assert all(s.get('render_mode',0)==g['render_mode']for s in candidates)
   colors={tuple(((c.get('color',s['color'])>>16)&255,(c.get('color',s['color'])>>8)&255,c.get('color',s['color'])&255))for s in candidates for c in s['source_characters']}
   source_color=tuple(round(v*255)for v in g['color'])
   assert g['render_mode']==0 and source_color in colors and g['opacity']==1.0,g
   if lang=='en':assert expected in ['SimSun','SimHei']
   elif '\uac00'<=g['c']<='\ud7a3'and fam=='serif':assert role=='Batang'
   donor,pin,cache=donors[role]
   cp=ord(g['c']);glyphname=donor.getBestCmap().get(cp);assert glyphname,(role,g['c'])
   dg=donor.getGlyphID(glyphname);gid=g['trace_gid']
   programs=[(a,h)for a,h in embedded[norm(role)]if gid<len(a.getGlyphOrder())and ('cmap'not in a or a.getBestCmap().get(cp)==a.getGlyphOrder()[gid])]
   assert programs,('No actual embedded font resource matches trace Unicode/GID',role,g['c'],gid)
   for actual,programsha in programs:
    cachekey=(programsha,gid,dg)
    if cachekey not in cache:
     a=outline(actual,gid);b=outline(donor,dg);assert a==b,('Actual embedded glyph outline differs from donor',role,g['c'],a,b)
     cache[cachekey]=a
   advance=actual['hmtx'].metrics[actual.getGlyphOrder()[gid]][0]/actual['head'].unitsPerEm*g['size']
   rows.append(dict(character=g['c'],actual_font=role,actual_gid=gid,actual_point_size=g['size'],actual_origin=g['origin'],actual_advance_width=advance,actual_render_mode=g['render_mode'],actual_fill_color=g['color'],actual_fill_opacity=g['opacity'],actual_embedded_program_sha256=programsha,all_matching_embedded_program_sha256=sorted(set(h for a,h in programs)),donor_full_face_sha256=pin['sha256'],decomposed_outline_sha256=cache[cachekey],source_slots=[s['id']for s in candidates],source_point_size=candidates[0]['size'],source_baseline=candidates[0]['origin'][1],source_family=fam,source_original_color=list(source_color),actual_embedded_outline_matches_pinned_full_role_donor=True))
  assert rows
  centers=[]
  for line in plan['centered_lines']:
   glyphs=[g for g in rows if abs(g['actual_origin'][1]-line['baseline'])<=.002];assert glyphs
   left=min(g['actual_origin'][0]for g in glyphs);right=max(g['actual_origin'][0]+g['actual_advance_width']for g in glyphs);center=(left+right)/2
   assert abs(center-line['center'])<=.001,('Actual heading advance box is not source centered',center,line)
   centers.append(dict(passed=True,baseline=line['baseline'],source_center=line['center'],actual_left=left,actual_right=right,actual_center=center,error_pt=abs(center-line['center'])))
  result=dict(schema='cpho2007-actual-embedded-prose-style-v1',passed=True,source_sha256=sha(F/'inputs/CPhO_2007_Chinese_original.pdf'),source_page=n,language=lang,proof_sha256=sha(proof),source_slot_inventory_sha256=sha(F/'inputs/original-all20-source-slots.json'),source_plan_sha256=sha(F/f'natural/2007/{lang}/page{n:02}.plan.json'),method='Read-only actual final PDF glyph GIDs, embedded decomposed outlines, source slot point sizes/baselines and fill paint; full donors are hash pinned and not exported.',original_point_sizes_scaled=False,original_baselines_changed=False,all_actual_embedded_outlines_match_pinned_donors=True,all_source_roles_and_point_sizes_and_paint_verified=True,actual_nonspace_glyphs_checked=len(rows),actual_glyph_style_checks=rows,actual_centered_heading_checks=centers,font_policy='EN actual original-family SimSun/SimHei; KO Batang serif body Hangul and NotoSansCJKkr title/section at original source points; original math stays native.',full_installed_font_programs_exported=False)
 save(OUT/f'actual-style/{lang}-page{n:02}.json',result)
 print('CPHO2007_ACTUAL_STYLE_PASS',lang,n,len(rows),flush=True)
if __name__=='__main__':
 with page_worker():
  tasks=[(lang,n)for lang in ['ko','en']for n in range(5,20)]if sys.argv[1:] == ['--all-missing']else [(sys.argv[1],int(sys.argv[2]))]
  for lang,n in tasks:
   if not (OUT/f'actual-style/{lang}-page{n:02}.json').exists():audit_page(lang,n)

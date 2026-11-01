"""Check every final Hangul font outline, source point and baseline independently."""
from pathlib import Path
from io import BytesIO
from collections import Counter
import json,hashlib,re
import pikepdf,pymupdf as fitz
from fontTools.ttLib import TTFont
from fontTools.cffLib import CFFFontSet
from fontTools.pens.recordingPen import DecomposingRecordingPen
from izho_initial_outline_qa import trace_font_resources
from pdf_original_style_fonts import FONTS
from pdf_original_text_ops import family_name
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def data(raw):
 if raw[:4]in[b'\x00\x01\x00\x00',b'OTTO',b'true']:
  f=TTFont(BytesIO(raw),lazy=True);return dict(font=f,glyphs=f.getGlyphSet(),order=f.getGlyphOrder(),upm=f['head'].unitsPerEm,cmap=f.getBestCmap(),name=f['name'].getDebugName(6))
 c=CFFFontSet();c.decompile(BytesIO(raw),None);t=c[c.fontNames[0]];return dict(cff=c,glyphs=t.CharStrings,order=t.charset,upm=round(1/t.FontMatrix[0]),name=c.fontNames[0])
def outline(d,name):
 p=DecomposingRecordingPen(d['glyphs']);d['glyphs'][name].draw(p)
 return [(op,[None if pt is None else tuple(round(x/d['upm'],7)for x in pt)for pt in pts])for op,pts in p.value]
def audit(plan_path,cache=None):
 cache={}if cache is None else cache;plan_path=Path(plan_path);p=json.loads(plan_path.read_text('utf8'));target=plan_path.parents[1]/f"page{p['page']:02}.pdf";expected=Counter()
 paths={'Batang':Path('D:/CodexBuilds/Hasla-original-style-20261031/cpho2024-original-natural/fonts/Batang-Regular.ttf'),'NotoSerifCJKkr-Regular':FONTS['serif'],'NotoSerifCJKkr-Bold':FONTS['serif-bold'],'NotoSansCJKkr-Regular':FONTS['sans'],'NotoSansCJKkr-Bold':FONTS['sans-bold']}
 for placement in p['prose_placements']:
  for part in placement['parts']:
   if not part['font'].startswith('KO_'):continue
   role=part['font'][3:];family={'serif':'NotoSerifCJKkr-Regular','serif_bold':'NotoSerifCJKkr-Bold','sans':'NotoSansCJKkr-Regular','sans_bold':'NotoSansCJKkr-Bold'}[role]
   if role=='serif'and not part.get('oblique_angle')and not re.search('Ital|Oblique',part['source_font']):family='Batang'
   for c in part['text']:
    if 0xac00<=ord(c)<=0xd7a3:expected[c,family,round(part['size'],5),round(placement['source_baseline'],2)]+=1
 with fitz.open(target)as doc,pikepdf.open(target)as pdf:
  mapped,programs=trace_font_resources(pdf,doc[0]);actual=[g for g in mapped if len(g['c'])==1 and 0xac00<=ord(g['c'])<=0xd7a3 and g['gid']>=0]
  got=Counter((g['c'],family_name(g['font']),round(g['size'],5),round(g['origin'][1],2))for g in actual)
  assert got==expected,('Original font-role, point or baseline mismatch',list((got-expected).items())[:5],list((expected-got).items())[:5])
  programs_data={digest:data(programs[digest]['raw'])for digest in {g['font_program_sha256']for g in actual}};donors={};rows=[]
  for g in actual:
   family=family_name(g['font']);path=paths[family]
   if family not in donors:donors[family]=data(path.read_bytes())
   a=programs_data[g['font_program_sha256']];d=donors[family];key=(g['font_program_sha256'],g['gid'],str(path),g['c'])
   if key not in cache:
    wanted=d['cmap'][ord(g['c'])];o=outline(a,a['order'][g['gid']]);assert o and o==outline(d,wanted),('Actual embedded outline differs from role donor',g);cache[key]=True
   assert g['render_type']==0 and g['color']==[0.,0.,0.]
   rows.append(dict(c=g['c'],font_family=family,actual_gid=g['gid'],point_size=g['size'],baseline=g['origin'][1],source_role_point_and_baseline_matched=True,actual_outline_matches_complete_role_donor=True))
  for d in list(programs_data.values())+list(donors.values()):
   if d.get('font'):d['font'].close()
 q=dict(page=p['page'],proof_sha256=sha(target),plan_sha256=sha(plan_path),method='Every final Hangul occurrence must match the authored original source role, exact point size and original prose baseline. Every actual embedded font/GID outline must match the complete role-donor Unicode glyph; no family name or nonempty-outline shortcut.',source_role_point_baseline_counter_matched=True,hangul_glyphs_checked=len(rows),donors={name:dict(path=str(paths[name]),sha256=sha(paths[name]))for name in donors},actual_glyph_checks=rows,passed=True)
 target.with_suffix('.font-source-style.json').write_text(json.dumps(q,ensure_ascii=False,indent=2)+'\n','utf8');return q

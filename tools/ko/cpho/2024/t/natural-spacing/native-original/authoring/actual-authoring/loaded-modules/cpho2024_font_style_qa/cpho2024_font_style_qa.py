"""Check actual source font roles/points/paint and embedded donor outlines."""
from pathlib import Path
from io import BytesIO
from collections import Counter
import hashlib,json,sys,re
import pikepdf,pymupdf as fitz
from fontTools.ttLib import TTFont
from fontTools.cffLib import CFFFontSet
from fontTools.pens.recordingPen import DecomposingRecordingPen
from cpho2024_natural import BASE,SOURCE,font_source
from pdf_native_inline_reposition import _traces
from izho_new_prose_outline_qa import trace_font_resources
from pdf_memory_gate import page_worker
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def family(n):return re.sub(r'^[A-Z]{6}\+','',n)
def prose_family(n):
 n=family(n)
 return 'DengXian'if n=='DengXian-Regular'else n

def font_data(raw):
 if raw[:4]in[b'\x00\x01\x00\x00',b'OTTO',b'true',b'ttcf']:
  ft=TTFont(BytesIO(raw),lazy=True);return dict(font=ft,glyphs=ft.getGlyphSet(),order=ft.getGlyphOrder(),upm=ft['head'].unitsPerEm,name=ft['name'].getDebugName(6),weight=ft['OS/2'].usWeightClass,cmap=ft.getBestCmap())
 cff=CFFFontSet();cff.decompile(BytesIO(raw),None);top=cff[cff.fontNames[0]]
 return dict(cff=cff,glyphs=top.CharStrings,order=top.charset,upm=round(1/top.FontMatrix[0]),name=family(cff.fontNames[0]),weight=None)

def outline(fd,name):
 pen=DecomposingRecordingPen(fd['glyphs']);fd['glyphs'][name].draw(pen);unit=fd['upm']
 return [(op,[None if point is None else tuple(round(v/unit,7)for v in point)for point in points])for op,points in pen.value]

def audit(number,language):
 target=BASE/f'T/pages/page{number:02}-{language}.pdf';q=json.loads(target.with_suffix('.json').read_text('utf8'));assert sha(target)==q['output_sha256']
 with fitz.open(SOURCE)as source,fitz.open(target)as final,pikepdf.open(target)as pdf:
  source_fonts={}
  for r in source[number-1].get_fonts(full=True):
   raw=source.extract_font(r[0])[3]
   if not raw:continue
   fd=font_data(raw);source_fonts[r[3]]=dict(name=fd['name'],weight=fd['weight'],program_sha256=hashlib.sha256(raw).hexdigest());fd['font'].close()
  source_styles={(g['font'],round(g['size'],5),g['render_mode'],round(g['origin'][1],3)):g for g in _traces(source[number-1])if g['c'].strip()}
  aliases={};reference={};unit_styles={}
  for row in q['rows']:
   for u in row['units']:
    if u['kind']!='prose':continue
    alias=aliases.setdefault(u['font_path'],'/TranslatedProse'+str(len(aliases)));style=u['source_style'];path=font_source(style,language)
    if path not in reference:reference[path]=dict(data=font_data(path.read_bytes()),sha256=sha(path),path=str(path))
    key=(style['source_font'],round(style['size'],5),style.get('render_mode',0),round(style['origin'][1],3));assert key in source_styles,key
    original=source_styles[key];actual_source=source_fonts[style['source_font']]
    expected_weight=actual_source['weight'];expected_family=actual_source['name']
    if language=='EN':expected_name=expected_family
    elif expected_family in ['DengXian','DengXian-Bold','SimHei']:expected_name='NotoSansCJKkr-'+('Bold'if expected_weight>=600 else'Regular')
    elif expected_family=='SimSun':expected_name='NotoSerifCJKkr-Bold'if expected_weight>=600 else'Batang'
    else:raise ValueError(('Unreviewed actual source prose face',expected_family))
    assert prose_family(reference[path]['data']['name'])==prose_family(expected_name),(reference[path]['data']['name'],expected_name)
    if language=='EN':assert reference[path]['data']['weight']==expected_weight
    unit_styles.setdefault(alias,[]).append(dict(source_font=style['source_font'],actual_original_face=expected_family,actual_original_weight=expected_weight,target_face=expected_name,size=style['size'],source_baseline=style['origin'][1],render_mode=style.get('render_mode',0),source_linewidth=original.get('linewidth'),reference=path))
  mapped,programs=trace_font_resources(pdf,final[0]);added=[g for g in mapped if g['font_alias'].startswith('/TranslatedProse')and g['c'].strip()and g['gid']>=0]
  actual_data={digest:font_data(programs[digest]['raw'])for digest in{g['font_program_sha256']for g in added}};traces=_traces(final[0]);checked=[];cache={}
  for g in added:
   candidates=[s for s in unit_styles[g['font_alias']]if abs(s['size']-g['size'])<1e-6 and abs(s['source_baseline']-g['origin'][1])<.001 and s['render_mode']==g['render_type']]
   assert candidates,('Actual source font/point/paint/y unavailable',g)
   s=candidates[0];expected=reference[s['reference']]['data'];actual=actual_data[g['font_program_sha256']]
   assert prose_family(actual['name'])==prose_family(s['target_face']),(actual['name'],s['target_face'])
   signature=(g['font_program_sha256'],g['gid'],str(s['reference']),g['c'])
   if signature not in cache:
    expected_name=expected['cmap'][ord(g['c'])];actual_name=actual['order'][g['gid']]
    a=outline(expected,expected_name);b=outline(actual,actual_name);assert a and a==b,('Actual embedded glyph differs from full original-role donor',g['c'],s['target_face'])
    cache[signature]=True
   if g['render_type']==2:
    paint=[t for t in traces if t['c']==g['c']and t['trace_gid']==g['gid']and family(t['font'])==g['font']and max(abs(a-b)for a,b in zip(t['origin'],g['origin']))<.001]
    assert len(paint)==1 and abs(paint[0]['linewidth']-s['source_linewidth'])<1e-6
   checked.append(dict(c=g['c'],font_alias=g['font_alias'],actual_source_face=s['actual_original_face'],actual_embedded_face=actual['name'],source_point_size=s['size'],actual_point_size=g['size'],source_baseline=s['source_baseline'],actual_baseline=g['origin'][1],source_render_mode=s['render_mode'],actual_render_mode=g['render_type'],actual_GID=g['gid'],actual_embedded_outline_matches_complete_source_role_donor=True))
  report=dict(proof_sha256=sha(target),source_sha256=sha(SOURCE),page=number,language=language,passed=True,actual_nonspace_glyphs_checked=len(checked),distinct_actual_outlines_checked=len(cache),original_source_fonts=source_fonts,full_donor_fonts=[dict(path=r['path'],sha256=r['sha256'],postscript_name=r['data']['name'])for r in reference.values()],actual_glyph_style_checks=checked,original_source_point_baseline_paint_and_stroke_checked=True,source_roles_recovered_from_actual_embedded_font_programs=True,all_actual_embedded_GID_outlines_match_full_role_donor=True,original_font_sizes_scaled=False)
  out=BASE/f'T/body-qa/page{number:02}-{language}.font-style.json';out.write_text(json.dumps(report,ensure_ascii=False,indent=1)+'\n','utf8')
  for data in [r['data']for r in reference.values()]+list(actual_data.values()):
   if data.get('font'):data['font'].close()
  print('ACTUAL_FONT_STYLE',number,language,len(checked),len(cache),'PASS',flush=True)
 return report

if __name__=='__main__':
 with page_worker():audit(int(sys.argv[1]),sys.argv[2])

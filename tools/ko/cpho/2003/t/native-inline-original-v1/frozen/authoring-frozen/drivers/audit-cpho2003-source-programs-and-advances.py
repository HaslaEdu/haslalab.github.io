"""Original resource programs and actual unscaled prose advances, read-only."""
from pathlib import Path
from collections import Counter,defaultdict
import sys,json,hashlib,re
B=Path('C:/Users/andre/CodexWork/HaslaLab/translation-builds/cpho2003-original-native');sys.path.insert(0,str(B/'engine'))
from pdf_memory_gate import page_worker
from pdf_native_inline_reposition import _traces
from cpho_natural_full_qa import native_font_programs
from izho_early_fixed_style import native_image_programs
from izho_natural_spacing_qa import semantic
from fontTools.ttLib import TTFont
import pymupdf as f,pikepdf
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
pins=json.loads((B/'inputs/external-font-source-pins.json').read_text('utf8'));donors={}
with page_worker():
 for pin in pins:
  path=Path(pin['path']);assert sha(path)==pin['sha256'];name=path.name.lower();role='Batang'if name=='batang.ttc'else'SimSun'if name.startswith('simsun')else'SimHei'if name=='simhei.ttf'else'NotoSerifCJKkr-Regular'if name.startswith('notoserif')else'NotoSansCJKkr-Regular';donors[role]=TTFont(path,fontNumber=0)if path.suffix.lower()=='.ttc'else TTFont(path)
 source=B/'inputs/CPhO_2003_Chinese_original.pdf'
 for lang in ['ko','en']:
  for n in [1,2,3]:
   proof=B/f'natural/2003/{lang}/page{n:02}.pdf';stylepath=B/f'evidence/actual-style/{lang}-page{n:02}.json';style=json.loads(stylepath.read_text('utf8'));assert style['passed']and style['proof_sha256']==sha(proof)
   originalfonts=Counter(native_font_programs(source,n));finalfonts=Counter(native_font_programs(proof,1));assert all(finalfonts[k]>=v for k,v in originalfonts.items())
   images=Counter(native_image_programs(source,n));finalimages=Counter(native_image_programs(proof,1));assert all(finalimages[k]>=v for k,v in images.items())
   with pikepdf.open(source)as a,pikepdf.open(proof)as b:
    for key in ['/MediaBox','/CropBox','/Rotate','/Group']:assert semantic(a.pages[n-1].get(key))==semantic(b.pages[0].get(key)),(n,lang,key)
    assert semantic(a.pages[n-1].Resources.get('/ColorSpace'))==semantic(b.pages[0].Resources.get('/ColorSpace'))
   with f.open(proof)as doc:
    buckets=defaultdict(list)
    for g in _traces(doc[0]):buckets[(g['c'],g['font'],g['trace_gid'])].append(g)
    checks=[]
    for row in style['actual_glyph_style_checks']:
     candidates=[g for g in buckets[(row['character'],row['actual_font'],row['actual_gid'])]if abs(g['size']-row['actual_point_size'])<1e-6 and max(abs(a-b)for a,b in zip(g['origin'],row['actual_origin']))<=.001];assert len(candidates)==1;g=candidates[0];donor=donors[row['actual_donor_role']];name=donor.getBestCmap()[ord(g['c'])];advance=donor['hmtx'].metrics[name][0]/donor['head'].unitsPerEm*g['size'];actual=g['bbox'][2]-g['origin'][0]
     assert abs(advance-row['actual_advance_width'])<=.001 and abs(actual-advance)<=.001,(row,advance,actual)
     assert tuple(g['direction'])==(1.,0.)
     checks.append(dict(character=g['c'],font=g['font'],gid=g['trace_gid'],origin=g['origin'],source_point_size=row['source_point_size'],actual_point_size=g['size'],actual_trace_advance_width=actual,actual_embedded_hmtx_advance_width=row['actual_advance_width'],full_donor_advance_width=advance,unscaled_horizontal_advance_verified=True))
   report=dict(passed=True,source_sha256=sha(source),source_page=n,language=lang,proof_sha256=sha(proof),actual_style_sha256=sha(stylepath),all_original_font_programs_names_and_ToUnicode_preserved=True,original_font_resource_records=len(originalfonts),all_original_image_palette_icc_mask_graphs_and_programs_preserved=True,original_image_resource_records=len(images),original_media_crop_rotation_group_and_colorspace_preserved=True,actual_full_donor_advances_and_trace_widths_identical=True,actual_unscaled_prose_glyphs_checked=len(checks),point_or_horizontal_scale_fitting=False,glyph_checks=checks)
   out=B/f'evidence/source-programs-and-advances/{lang}-page{n:02}.json';out.parent.mkdir(parents=True,exist_ok=True);assert not out.exists();out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n','utf8');print('CPHO2003_SOURCE_PROGRAMS_AND_UNSCALED_ADVANCES_PASS',lang,n,len(checks),flush=True)

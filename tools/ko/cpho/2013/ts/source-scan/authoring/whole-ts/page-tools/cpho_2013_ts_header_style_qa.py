"""Read-only actual header font/CID/size/baseline/paint and source-center audit."""
from pathlib import Path
import json,re,hashlib
import pikepdf,pymupdf as fitz
from fontTools.ttLib import TTFont
from pdf_original_text_ops import widths
from izho_new_prose_outline_qa import trace_font_resources
from cpho_2013_ts_compose import digits
BASE=Path('D:/CodexBuilds/Hasla-original-style-20261031/cpho2013/TS')
ROOT=Path('C:/Users/andre/OneDrive/문서/ChatGPT/Hasla 노술/haslalab')
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()

def audit(number,lang):
 pdf=BASE/f'proofs/{lang}/page{number:02d}.pdf';meta=json.loads(pdf.with_suffix('.composition.json').read_text('utf8'))
 inv=json.loads((ROOT/'tools/ko/cpho/2013/original/native-slots.json').read_text('utf8'))
 slots={s['id']:s for s in inv['pages'][number-1]['slots']};expected=[];errors=[];centers=[]
 with pikepdf.open(pdf)as doc,fitz.open(pdf)as mu:
  page=doc.pages[0];allglyphs,_=trace_font_resources(doc,mu[0]);actual=[g for g in allglyphs if g['font_alias'].startswith('/TSHeader')and not g['c'].isspace()];remain=list(actual)
  for r in meta['header']['placements']:
   slot=slots[r['source_slot']];font_path=Path(r['font']['subset']);metric=fitz.Font(fontbuffer=font_path.read_bytes());alias='/TSHeader'+r['source_font'];decl,default=widths(page.Resources.Font[alias]);x=r['left'];text=r['text'];size=slot['size'];baseline=slot['source_characters'][0]['origin'][1]
   with TTFont(font_path)as font:
    cmap=font.getBestCmap();groups=digits(slot);matches=list(re.finditer(r'\d+',text))if groups else[];parts=[];end=0
    for match,group in zip(matches,groups):
     parts.append(('prose',text[end:match.start()]));parts.append(('native',group));end=match.end()
    parts.append(('prose',text[end:]))
    for kind,part in parts:
     if kind=='native':x+=part[-1]['bbox'][2]-part[0]['origin'][0];continue
     for match in re.finditer(r' +|[^ ]+',part):
      word=match.group()
      if word.isspace():x+=len(word)*size/4;continue
      xx=x
      for c in word:
       gid=font.getGlyphID(cmap[ord(c)]);w=decl.get(gid,default)
       if w is None or w<=0:errors.append(dict(reason='Actual nonpositive header CID Width',c=c,gid=gid))
       expected.append(dict(c=c,gid=gid,font_alias=alias,font_program_sha256=r['font']['subset_sha256'],size=size,origin=[xx,baseline],render_type=slot['render_mode'],line_width=slot['line_width']))
       xx+=(w or 0)*size/1000
      x+=metric.text_length(word,fontsize=size)
   if abs(x-r['right'])>.001:errors.append(dict(reason='Header full width differs',source_slot=r['source_slot']))
   if slot.get('align')=='center':
    delta=(r['left']+r['right'])/2-slot['original_horizontal_center'];centers.append(dict(source_slot=r['source_slot'],source_center=slot['original_horizontal_center'],translation_center=(r['left']+r['right'])/2,error_pt=delta))
    if abs(delta)>.001:errors.append(dict(reason='Whole title no longer source centered',error=delta))
  for e in expected:
   hits=[(i,g)for i,g in enumerate(remain)if g['c']==e['c']and g['gid']==e['gid']and g['font_alias']==e['font_alias']and abs(g['size']-e['size'])<.001 and max(abs(g['origin'][j]-e['origin'][j])for j in[0,1])<.001]
   if len(hits)!=1:errors.append(dict(reason='Expected header actual CID/size/baseline/point not unique',expected=e,matches=len(hits)));continue
   i,g=hits[0];remain.pop(i)
   if g['font_program_sha256']!=e['font_program_sha256']or g['render_type']!=e['render_type']:errors.append(dict(reason='Header actual font program/paint differs',expected=e,actual=g))
   if e['render_type']in[1,2]:
    traces=[t for t in mu[0].get_texttrace()if t['type']==1 and abs(t['size']-e['size'])<.001 and any(cp==ord(e['c'])and gid==e['gid']and max(abs(p[j]-e['origin'][j])for j in[0,1])<.001 for cp,gid,p,b in t['chars'])]
    if not traces or any(abs(t['linewidth']-e['line_width'])>1e-5 for t in traces):errors.append(dict(reason='Header actual source stroke differs',expected=e))
  if remain:errors.append(dict(reason='Unexpected new header glyphs',glyphs=remain))
 report=dict(source_sha256=meta['source_sha256'],source_page=number,proof_sha256=sha(pdf),language=lang,actual_new_header_CIDs_checked=len(expected),full_title_source_center=centers,actual_font_GID_pointsize_baseline_and_source_paint_failures=errors,passed=not errors)
 pdf.with_suffix('.header-actual-style.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),'utf8');return report

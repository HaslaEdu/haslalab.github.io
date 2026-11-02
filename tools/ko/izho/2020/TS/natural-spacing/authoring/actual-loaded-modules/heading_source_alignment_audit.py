"""Compare actual final nonspace glyph envelopes with original source centers."""
from pathlib import Path
import json,hashlib,re
import pymupdf as fitz
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def audit(plan_path,final_override=None,report_override=None):
 plan_path=Path(plan_path);p=json.loads(plan_path.read_text('utf8'));target=Path(final_override)if final_override else plan_path.parents[1]/(plan_path.stem+'.pdf');rows=[]
 assert sha(p['original_english_source'])==p['original_english_source_sha256']
 fitz.TOOLS.set_small_glyph_heights(True)
 with fitz.open(p['original_english_source'])as original,fitz.open(target)as doc:
  source=original[p['source_page']-1].get_text('rawdict')
  gs=[dict(c=chr(cp),origin=origin,bbox=bbox)for t in doc[0].get_texttrace()for cp,gid,origin,bbox in t['chars']if gid>=0 and not chr(cp).isspace()]
  for intent in p.get('centered_lines',[]):
   rect=intent['rect'];bound=rect in p['allowed_line_rects'];actual=[g for g in gs if abs(g['origin'][1]-intent['baseline'])<.02 and rect[0]-.001<=g['origin'][0]<=rect[2]+.001]
   left=min(g['bbox'][0]for g in actual)if actual else None;right=max(g['bbox'][2]for g in actual)if actual else None;center=(left+right)/2 if actual else None;error=center-intent['center']if actual else None
   scopes=[]
   for s in p['source_line_scopes']:
    r=s['rect'][:]
    if r[1]>60:r[0]=max(63.59,r[0]);r[2]=min(558.,r[2])
    if abs(s['baseline']-intent['baseline'])<.02 and max(abs(a-b)for a,b in zip(r,rect))<.001:scopes.append(s)
   original_centers=[]
   for scope in scopes:
    bi,li=scope['source_at'];line=source['blocks'][bi]['lines'][li];chars=[c for s in line['spans']for c in s['chars']if c['c'].strip()]
    original_centers.append((min(c['bbox'][0]for c in chars)+max(c['bbox'][2]for c in chars))/2)
   source_match=bool(original_centers)and all(abs(c-intent['center'])<=.001 for c in original_centers)
   rows.append(dict(source_line_ats=[s['source_at']for s in scopes],baseline=intent['baseline'],source_center=intent['center'],independent_original_source_centers=original_centers,source_center_matches_original_glyphs=source_match,actual_nonspace_glyph_left=left,actual_nonspace_glyph_right=right,actual_center=center,center_error_pt=error,original_alignment_frame_resolves_to_active_composer_scope=bound,glyphs=len(actual),passed=bound and source_match and error is not None and abs(error)<=.001))
  headings=[]
  for bi,block in enumerate(source['blocks']):
   if block['type']:continue
   for li,line in enumerate(block['lines']):
    value=''.join(c['c']for s in line['spans']for c in s['chars'])
    if not re.search('[A-Za-z]{2,}',value)or not any(s['flags']&16 and s['size']>=14 and 'TimesNewRoman'in s['font']for s in line['spans']):continue
    chars=[c for s in line['spans']for c in s['chars']if c['c'].strip()]
    if not chars:continue
    center=(min(c['bbox'][0]for c in chars)+max(c['bbox'][2]for c in chars))/2
    hits=[r for r in rows if [bi,li]in r['source_line_ats']and abs(r['source_center']-center)<=.001]
    headings.append(dict(source_at=[bi,li],source_text=value,original_center=center,alignment_intent_present=len(hits)==1,actual_center_preserved=len(hits)==1 and hits[0]['passed'],passed=len(hits)==1 and hits[0]['passed']))
 q=dict(source_sha256=p['original_english_source_sha256'],source_page=p['source_page'],proof_sha256=sha(target),plan_sha256=sha(plan_path),method='Independently read every final nonspace glyph envelope against its original source center. Also inventory every original bold14pt-or-larger English prose heading, including subtitles, and require its alignment intent and actual center to be present.',headings_and_captions_checked=len(rows),rows=rows,original_bold_prose_heading_coverage=dict(headings_checked=len(headings),rows=headings,passed=all(r['passed']for r in headings)),passed=all(r['passed']for r in rows)and all(r['passed']for r in headings))
 report=Path(report_override)if report_override else target.with_suffix('.source-alignment.json');report.write_text(json.dumps(q,ensure_ascii=False,indent=2)+'\n','utf8');return q
if __name__=='__main__':
 import sys
 q=audit(sys.argv[1]);print(json.dumps(q,ensure_ascii=False));assert q['passed']

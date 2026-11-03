"""Independent original mathematical bitmap invocation geometry, fail closed."""
from pathlib import Path
import json,hashlib
from pdf_native_inline_reposition import inspect_inline_groups
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def audit(plan,final_override=None,report_override=None):
 plan=Path(plan);p=json.loads(plan.read_text('utf8'));rule=p['reviewed_mathematical_image_invocations'];final=Path(final_override)if final_override else plan.parents[1]/f"page{p['page']:02}.pdf"
 original=inspect_inline_groups(p['original_english_source'],p['source_page'])['images'];actual=inspect_inline_groups(final,1)['images'];assert len(original)==len(actual)==rule['images']
 inline=set(rule['inline_indices']);stationary=set(rule['stationary_display_indices']);assert not inline&stationary and inline|stationary==set(range(len(original)))
 rows=[]
 for i,(a,b)in enumerate(zip(original,actual)):
  old=a['entry_ctm'];new=b['entry_ctm'];dx=b['bbox'][0]-a['bbox'][0];errors=[]
  if a['original_raw_sha256']!=b['original_raw_sha256']:errors.append('Original encoded colour image changed')
  if max(abs(x-y)for x,y in zip(old[:4],new[:4]))>.002:errors.append('Original image linear CTM changed')
  if abs(b['bbox'][1]-a['bbox'][1])>.002 or abs(b['bbox'][3]-a['bbox'][3])>.002:errors.append('Original image y/height changed')
  if abs(b['bbox'][2]-a['bbox'][2]-dx)>.002:errors.append('Original image width changed')
  if i in stationary and max(abs(x-y)for x,y in zip(old,new))>.002:errors.append('Display formula moved from original complete CTM')
  rows.append(dict(source_image_index=i,source_raw_sha256=a['original_raw_sha256'],final_raw_sha256=b['original_raw_sha256'],source_ctm=old,final_ctm=new,source_bbox=a['bbox'],final_bbox=b['bbox'],dx_pt=dx,role='reviewed complete inline formula'if i in inline else'fixed original display formula',errors=errors,passed=not errors))
 q=dict(source_sha256=p['original_english_source_sha256'],source_page=p['source_page'],final_sha256=sha(final),plan_sha256=sha(plan),method='Independent ordered original Image Do inventory; every original encoded colour stream, physical width/height, full linear CTM and y retained. Each explicitly reviewed display formula also retains exact x/full CTM. Only listed whole original inline formulas may translate horizontally.',images=rows,original_images_checked=len(rows),fixed_display_images_checked=len(stationary),reviewed_inline_images_checked=len(inline),passed=all(r['passed']for r in rows))
 report=Path(report_override)if report_override else final.with_suffix('.native-math-images.json');report.write_text(json.dumps(q,ensure_ascii=False,indent=2)+'\n','utf8');return q

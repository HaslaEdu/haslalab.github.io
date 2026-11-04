"""Actual original math ink regression independent of the MuPDF-only audits."""
from pathlib import Path
from collections import Counter
import sys,json,hashlib
B=Path('C:/Users/andre/CodexWork/HaslaLab/translation-builds/cpho2003-original-native');sys.path.insert(0,str(B/'engine'))
from pdf_memory_gate import page_worker
from cpho_natural_full_qa import native_font_programs
from PIL import Image
import numpy as np,pikepdf
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
source=B/'inputs/CPhO_2003_Chinese_original.pdf';positive=B/'natural/2003/en/page02.pdf';negative=B/'evidence/diagnostics/visually-suspected-math-loss-actually-zero-diff.pdf'
sourcepng=B/'source-renders-144/page02.png';positivepng=B/f'proof-renders-144/en/page02-{sha(positive)[:16]}.png';negativepng=B/'proof-history/en-all-before-font-identity-isolation/proof-renders-144/en/page02-a0a17d84a27d7af4.png'
assert sha(source)=='52f8a891d6129becf4d21ccb60f46997cedf9aa50123ffd147294cedcb121b63'
assert sha(negative)=='a0a17d84a27d7af494ba3ff8def3cbb8752adc462d3319de46dac56e03699206'
with page_worker():
 original=Counter(native_font_programs(source,2));final=Counter(native_font_programs(positive,1));assert all(final[k]>=v for k,v in original.items())
 rois=[]
 for name,rect in [('Original stationary Delta-theta display equation',[71.5,426.5,124.,455.]),('Original stationary left rest-mass scientific notation',[71.5,708.5,137.5,721.5])]:
  box=tuple(round(v*2)for v in rect)
  with Image.open(sourcepng)as im:a=np.array(im.convert('RGB').crop(box))
  with Image.open(positivepng)as im:b=np.array(im.convert('RGB').crop(box))
  with Image.open(negativepng)as im:c=np.array(im.convert('RGB').crop(box))
  changed=int(np.any(a!=b,axis=2).sum());missing=int(((a.min(axis=2)<80)&(b.min(axis=2)>=220)).sum());bad_missing=int(((a.min(axis=2)<80)&(c.min(axis=2)>=220)).sum())
  assert changed==0 and missing==0 and bad_missing==0,(name,changed,missing,bad_missing)
  rois.append(dict(name=name,source_rect_points=rect,positive_changed_RGB_pixels=changed,positive_missing_original_dark_pixels=missing,before_isolation_missing_original_dark_pixels=bad_missing))
 with pikepdf.open(positive)as pdf:
  names={str(k):str(font.BaseFont)for k,font in pdf.pages[0].Resources.Font.items()if str(k).startswith('/Translation')};assert names and all(v.startswith('/CPhO2003Translation')for v in names.values())
 q=dict(passed=True,source_sha256=sha(source),source_page=2,positive_sha256=sha(positive),positive_Poppler144_sha256=sha(positivepng),source_Poppler144_sha256=sha(sourcepng),before_isolation_pdf_sha256=sha(negative),before_isolation_Poppler144_sha256=sha(negativepng),not_a_negative_control=True,initial_visual_hypothesis_disproved=True,method='Exact stationary source-math RGB comparison disproves the initial full-page visual reading. Before/after new-font-name isolation have identical native equation/scientific-notation pixels. This diagnostic is not a rejected PDF fixture.',original_font_programs_names_and_ToUnicode_retained=True,only_new_english_font_identities_isolated=True,actual_new_font_resource_names=names,all_nonname_font_tables_and_original_family_names_retained=True,rois=rois)
 out=B/'evidence/diagnostics/Poppler-math-visual-reading-resolution.json';assert not out.exists();out.write_text(json.dumps(q,ensure_ascii=False,indent=2)+'\n','utf8');print(json.dumps(q,ensure_ascii=False,indent=2))

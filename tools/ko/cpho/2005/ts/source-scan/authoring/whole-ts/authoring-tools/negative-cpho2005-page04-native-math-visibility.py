from pathlib import Path
import sys,json,hashlib
import pikepdf,pymupdf as f,numpy as np
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/cpho2005/TS')
sys.path[:0]=[str(B/'tools'),'D:/CodexBuilds/Hasla-publish-20261031/tools','D:/CodexBuilds/Hasla-original-style-20261031/cpho2013/TS/tools']
from cpho_2005_ts_qa import single_math_reference
number=int(sys.argv[1])if len(sys.argv)>1 else 4
results=[]
for lang in ['ko','en']:
 good=B/f'proofs/{lang}/page{number:02}.pdf';bad=good.with_suffix('.negative-omitted-first-native-math.pdf')
 composition=json.loads(good.with_suffix('.composition.json').read_text('utf8'));atom=composition['inline_math_replay']['atoms'][0]
 with pikepdf.open(good)as d:
  count=0
  for stream in d.pages[0].Contents:
   raw=stream.read_bytes();token=b'/IndependentNativeImageInstance1 Do'
   if token in raw:count+=raw.count(token);stream.write(raw.replace(token,b'% omitted exactly one original mathematical paint\n'))
  assert count==1
  d.save(bad,compress_streams=False)
 reference=single_math_reference(number,atom)
 with f.open(stream=reference,filetype='pdf')as d:
  pix=d[0].get_pixmap(matrix=f.Matrix(4,4),clip=f.Rect(atom['destination_rect']),alpha=False,colorspace=f.csRGB);expected=np.frombuffer(pix.samples,np.uint8).reshape(pix.height,pix.width,3).copy()
 errors=[]
 for pdf in [good,bad]:
  with f.open(pdf)as d:
   p=d[0].get_pixmap(matrix=f.Matrix(4,4),alpha=False,colorspace=f.csRGB);actual=np.frombuffer(p.samples,np.uint8).reshape(p.height,p.width,3)[pix.y:pix.y+pix.height,pix.x:pix.x+pix.width]
   errors.append(int(np.any(actual!=expected,axis=2).sum()))
 assert errors[0]==0 and errors[1]>0,(lang,errors)
 results.append(dict(language=lang,atom=atom['id'],good_sha256=hashlib.sha256(good.read_bytes()).hexdigest(),mutant_sha256=hashlib.sha256(bad.read_bytes()).hexdigest(),good_actual_RGB_errors=errors[0],mutant_actual_RGB_errors=errors[1],rejected=True))
report=dict(fault='Delete exactly one actual original native bitmap mathematical invocation from the final PDF; retain all new prose and other mathematics.',results=results,passed=True,publication_ready=False)
(B/f'proofs/page{number:02}-negative-native-math-visibility.json').write_text(json.dumps(report,indent=2)+'\n','utf8');print(json.dumps(report),flush=True)

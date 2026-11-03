"""Real final-PDF caption omission and plot damage controls; no QA relaxation."""
from pathlib import Path
import sys,json,hashlib
import pikepdf,pymupdf as f,numpy as np
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/cpho2005/TS');sys.path[:0]=[str(B/'tools'),'D:/CodexBuilds/Hasla-publish-20261031/tools','D:/CodexBuilds/Hasla-original-style-20261031/cpho2013/TS/tools']
from cpho_2005_ts_qa import single_math_reference
from pdf_memory_gate import page_worker
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
results=[];source=B/'inputs/CPhO_2005_Chinese_original.pdf';plot=[515,215,695,345]
with page_worker():
 with f.open(source)as d:
  p=d[11].get_pixmap(matrix=f.Matrix(4,4),clip=f.Rect(plot),alpha=False,colorspace=f.csRGB);plot_reference=np.frombuffer(p.samples,np.uint8).reshape(p.height,p.width,3).copy()
 for lang in ['ko','en']:
  good=B/f'proofs/{lang}/page12.pdf';j=json.loads(good.with_suffix('.composition.json').read_text('utf8'))
  for suffix,key in [('source-qa','final_sha256'),('poppler-qa','proof_sha256')]:q=json.loads(good.with_suffix('.'+suffix+'.json').read_text('utf8'));assert q['passed']and q[key]==sha(good)
  caption=next(r for r in j['body_placements']if r['id']=='figure-caption');assert abs((caption['left']+caption['right'])/2-608)<1e-8 and caption['size']==8.95 and caption['baseline']==360.5
  atom_index=next(i for i,r in enumerate(j['inline_math_replay']['atoms'])if r['id']=='figure-caption-caption2');atom=j['inline_math_replay']['atoms'][atom_index]
  bad=good.with_suffix('.negative-omitted-native-caption.pdf')
  with pikepdf.open(good)as d:
   token=f'/IndependentNativeImageInstance{atom_index+1} Do'.encode();count=0
   for stream in d.pages[0].Contents:
    raw=stream.read_bytes()
    if token in raw:count+=raw.count(token);stream.write(raw.replace(token,b'% exactly one original figure-caption numeral omitted\n'))
   assert count==1;d.save(bad,compress_streams=False)
  with f.open(stream=single_math_reference(12,atom),filetype='pdf')as d:
   p=d[0].get_pixmap(matrix=f.Matrix(4,4),clip=f.Rect(atom['destination_rect']),alpha=False,colorspace=f.csRGB);expected=np.frombuffer(p.samples,np.uint8).reshape(p.height,p.width,3).copy()
  errors=[]
  for path in [good,bad]:
   with f.open(path)as d:
    q=d[0].get_pixmap(matrix=f.Matrix(4,4),alpha=False,colorspace=f.csRGB);actual=np.frombuffer(q.samples,np.uint8).reshape(q.height,q.width,3)[p.y:p.y+p.height,p.x:p.x+p.width];errors.append(int(np.any(actual!=expected,axis=2).sum()))
  assert errors[0]==0 and errors[1]>0,(lang,'native_caption',errors)
  damaged=good.with_suffix('.negative-extra-plot-dot.pdf')
  with f.open(good)as d:d[0].draw_circle((570,235),.5,color=(0,0,0),fill=(0,0,0),width=0,overlay=True);d.save(damaged,garbage=0,deflate=False)
  plot_errors=[]
  for path in [good,damaged]:
   with f.open(path)as d:
    q=d[0].get_pixmap(matrix=f.Matrix(4,4),clip=f.Rect(plot),alpha=False,colorspace=f.csRGB);actual=np.frombuffer(q.samples,np.uint8).reshape(q.height,q.width,3);assert actual.shape==plot_reference.shape;plot_errors.append(int(np.any(actual!=plot_reference,axis=2).sum()))
  assert plot_errors[0]==0 and plot_errors[1]>0,(lang,'original_plot',plot_errors)
  results.append(dict(language=lang,good_sha256=sha(good),actual_caption_math_font_point_baseline_shape_and_original_center_checked=True,native_caption_digit_omitted=dict(path=str(bad),sha256=sha(bad),good_RGB_errors=errors[0],mutant_RGB_errors=errors[1],rejected=True),extra_plot_dot=dict(path=str(damaged),sha256=sha(damaged),original_source_plot_rect=plot,good_RGB_errors=plot_errors[0],mutant_RGB_errors=plot_errors[1],rejected=True)))
report=dict(source_sha256=sha(source),source_page=12,actual_PDF_mutations=True,results=results,passed=True,publication_ready=False)
(B/'proofs/page12-native-caption-and-plot-negatives.json').write_text(json.dumps(report,indent=2)+'\n','utf8');print(json.dumps(report),flush=True)

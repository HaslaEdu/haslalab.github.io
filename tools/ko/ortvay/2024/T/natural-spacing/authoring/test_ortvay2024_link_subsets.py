from pathlib import Path
import os
for name in ['OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS']:os.environ[name]='1'
import json,hashlib,copy
import pikepdf,pymupdf as f,numpy as np
import ortvay2024_link_annotations as link
B=Path(__file__).resolve().parents[1]
P=Path('C:/Users/andre/CodexWork/HaslaLab/translation-proof-work/proofs/ortvay/2024/page02.pdf')
Q=json.loads(P.with_suffix('.layout.json').read_text('utf8'))
O=Path('C:/Users/andre/CodexWork/HaslaLab/translation-proof-work/experiments/ortvay2024-link-subsets');O.mkdir(parents=True,exist_ok=True)
source=f.open(Q['source']);proof=f.open(P);output=O/'page02-links.pdf'
with pikepdf.Pdf.open(P)as d:
 rows=link.adjust_links(d.pages[0],source[1],proof[0],Q);d.save(output,compress_streams=False)
with f.open(output)as final:
 assert proof[0].get_texttrace()==final[0].get_texttrace()
 a=proof[0].get_pixmap(matrix=f.Matrix(1.5,1.5),alpha=False);b=final[0].get_pixmap(matrix=f.Matrix(1.5,1.5),alpha=False)
 assert a.width==b.width and a.height==b.height
 changed=int(np.any(np.frombuffer(a.samples,np.uint8).reshape(a.height,a.width,3)!=np.frombuffer(b.samples,np.uint8).reshape(b.height,b.width,3),axis=2).sum());assert changed==0
 for row in rows:
  found=[l for l in final[0].get_links()if l.get('uri')==row['uri']and link.same_origin(list(l['from']),row['expected_target_rect_mupdf'],.001)]
  assert len(found)==1;row['actual_target_rect_mupdf']=list(found[0]['from']);row['passed']=True
assert rows[0]['dx']!=rows[1]['dx']==0
negative=[]
with pikepdf.Pdf.open(P)as d:
 q=copy.deepcopy(Q);q['native_shifts']=q['native_shifts'][1:]
 try:link.adjust_links(d.pages[0],source[1],proof[0],q)
 except AssertionError:negative.append('missing native URL movement rejected')
 else:raise AssertionError('Missing movement accepted')
with pikepdf.Pdf.open(P)as d:
 q=copy.deepcopy(Q);q['selected_glyphs'].append(copy.deepcopy(q['native_shifts'][0]['glyphs'][0]))
 try:link.adjust_links(d.pages[0],source[1],proof[0],q)
 except AssertionError:negative.append('URL glyph incorrectly hidden as prose rejected')
 else:raise AssertionError('Hidden URL accepted')
with pikepdf.Pdf.open(P)as d:
 uri=rows[1]['uri'];rect=rows[1]['source_rect_mupdf']
 a=next(a for a in d.pages[0].obj['/Annots']if str(a.get('/A',{}).get('/URI',''))==uri and link.same_origin(list(f.Rect(list(map(float,a['/Rect'])))*source[1].transformation_matrix),rect,.001))
 r=list(map(float,a['/Rect']));dx=rows[0]['dx'];a['/Rect']=pikepdf.Array([r[0]+dx,r[1],r[2]+dx,r[3]])
 try:link.adjust_links(d.pages[0],source[1],proof[0],Q)
 except AssertionError:negative.append('wrong shared-URI shift on stationary second rectangle rejected')
 else:raise AssertionError('Wrong split movement accepted')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
report=dict(status='PASS',source_sha256=Q['source_sha256'],proof_sha256=sha(P),helper_sha256=sha(Path(link.__file__)),
 program_sha256=sha(Path(__file__)),changed_pixels=changed,all_visible_glyph_geometry_identical=True,
 links=rows,negative_regressions=negative)
(O/'regression.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n','utf8')
print(json.dumps(dict(status='PASS',links=len(rows),moved=sum(r['dx']!=0 for r in rows),stationary=sum(r['dx']==0 for r in rows),changed_pixels=changed,negative_regressions=negative)))

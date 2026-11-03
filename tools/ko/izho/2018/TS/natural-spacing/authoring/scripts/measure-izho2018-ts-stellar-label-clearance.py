from pathlib import Path
import sys,json,hashlib,os,math
os.environ.update(PYTHONDONTWRITEBYTECODE='1',OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1')
B=Path('C:/Users/andre/CodexWork/HaslaLab/translation-builds/izho2018-complete-solutions');sys.path[:0]=[str(B/'engine'),'D:/CodexBuilds/Hasla-publish-20261031/tools']
from pdf_memory_gate import page_worker
from initial_bitmap_language_labels import specifications
from pdf_text_motion_ink import ink_envelope
import pymupdf as f,numpy as np
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
F=B/'natural/2018/TS';p=json.loads((F/'plans/page10.json').read_text('utf8'));pdf=F/'page10.pdf';placements=json.loads(pdf.with_suffix('.language-overlay.json').read_text('utf8'))['placements'];scale=4
with page_worker():
 with f.open(p['original_english_source'])as original,f.open(pdf)as final:
  pix=original[9].get_pixmap(matrix=f.Matrix(scale,scale),colorspace=f.csRGB,alpha=False);a=np.frombuffer(pix.samples,np.uint8).reshape(pix.height,pix.width,3);foreground=np.any(a!=255,2);old=np.zeros(a.shape[:2],bool)
  for r in specifications(p):
   x0,y0,x1,y1=r['erase_rect_pt'];x0=max(0,math.floor(x0*scale));y0=max(0,math.floor(y0*scale));x1=min(a.shape[1],math.ceil(x1*scale));y1=min(a.shape[0],math.ceil(y1*scale));old[y0:y1,x0:x1]|=foreground[y0:y1,x0:x1]
  foreground&=~old;rows=[]
  for r in placements:
   metric=f.Font(fontfile=r['replacement_font_path']);offset=0.;origins=[]
   for c in r['text']:
    if not c.isspace():origins.append([r['origin'][0]+offset,r['origin'][1]])
    offset+=metric.text_length(c,fontsize=r['measured_source_size_pt'])
   actual=[]
   for expected,c in zip(origins,r['text']):
    hits=[point for trace in final[0].get_texttrace()if 'NotoSerif'in trace['font']and abs(trace['size']-r['measured_source_size_pt'])<.001 for cp,gid,point,box in trace['chars']if chr(cp)==c and max(abs(a-b)for a,b in zip(point,expected))<.02]
    assert len(hits)==1,(r['source_label'],expected,hits);actual.append(list(hits[0]))
   mask,uses=ink_envelope(final[0],actual,scale);assert uses==len(actual)and mask.any();attempts=[]
   for pixels_left in range(41):
    moved=np.zeros_like(mask)
    if pixels_left:moved[:,:-pixels_left]=mask[:,pixels_left:]
    else:moved=mask.copy()
    overlap=int((moved&foreground).sum());attempts.append(dict(horizontal_dx_pt=-pixels_left/scale,original_nonlanguage_foreground_overlap_pixels=overlap))
    if overlap==0:break
   assert overlap==0
   rows.append(dict(reviewed=True,source_label=r['source_label'],text=r['text'],horizontal_dx_pt=-pixels_left/scale,actual_original_center_preserved=pixels_left==0,source_point_size_unchanged=r['measured_source_size_pt'],source_baseline_unchanged=r['measured_source_baseline_pt'],italic_slant_unchanged=r['measured_source_italic_slant_degrees'],reason='Minimum quarter-point leftward label-only clearance for the wider Korean translation and its original measured italic role; actual new-font outline envelope must cover zero original nonlanguage pixels. Source image, geometry, mathematical labels, font point and baseline remain unchanged.',attempts=attempts))
 q=dict(source_sha256=p['original_english_source_sha256'],source_page=10,diagnostic_proof_sha256=sha(pdf),source_measurements_sha256=p['reviewed_bitmap_source_measurements_sha256'],actual_font_reference_source='Exact embedded Korean glyph outlines from the original-centre diagnostic proof, not bounding-box fitting',scale=4,rows=rows,passed=all(r['attempts'][-1]['original_nonlanguage_foreground_overlap_pixels']==0 for r in rows));out=B/'2018/inspection/page10-stellar-label-translation-clearance.json';out.write_text(json.dumps(q,ensure_ascii=False,indent=2)+'\n','utf8');print('SOURCE_FIGURE_ALL_NONLANGUAGE_PIXELS_PROTECTED_LABEL_CLEARANCE',[(r['source_label'],r['horizontal_dx_pt'])for r in rows],sha(out),flush=True)

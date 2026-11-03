"""Actual native atom appearance versus the original translated by its sole dx."""
from pathlib import Path
from io import BytesIO
import hashlib,json,sys
sys.dont_write_bytecode=True
import pikepdf,pymupdf as f,numpy as np
ROOT=Path('D:/CodexBuilds/Hasla-poi-natural-20261102/style-corrections/icho2024-20261103')
REV=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(REV/'working/style-engine'))
import latex_native_motion as motion

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def run(folder,require_pass=True):
 path=Path(folder)/'page39.pdf';q=json.loads(path.with_suffix('.layout.json').read_text('utf8'));profile=REV/'p39-reviewed-whole-inline-wedge-atom-v2.json';ref=json.loads(profile.read_text('utf8'))
 assert sha(profile)=='60f010c33b97f27a5347f187c141dddc46e740bb3023cb98ba66f43413f5153e'
 groups=[s for s in q['native_shifts']if ''.join(g['c']for g in s['glyphs'])=='(;)'];assert len(groups)==1;group=groups[0];dx=group['dx'];fields=['c','gid','font','size','origin','bbox','paint'];assert[{k:g[k]for k in fields}for g in group['glyphs']]==ref['source_glyphs']
 bounds=[g['native_ink_bbox']for g in group['glyphs']]+[p['rect']for p in ref['source_paths']if p['paint_operator']=='B'];r=[min(b[0]for b in bounds)+dx-.1,min(b[1]for b in bounds)-.25,max(b[2]for b in bounds)+dx+.1,max(b[3]for b in bounds)+.25];clip=f.Rect(r)
 source=ROOT/'frozen/source/IChO_2024_T_EN.pdf'
 with pikepdf.Pdf.open(source)as src:
  expected=pikepdf.Pdf.new();expected.pages.append(src.pages[38]);raw,_=motion._raw_regions(src.pages[38]);prefix=('q 1 0 0 1 '+motion._number(dx)+' 0 cm ').encode('ascii');expected.pages[0].Contents=expected.make_stream(prefix+raw+b' Q');buf=BytesIO();expected.save(buf,compress_streams=False)
 control=Path(folder)/'page39.native-original-shift-control.pdf';assert not control.exists();control.write_bytes(buf.getvalue())
 with f.open(stream=buf.getvalue(),filetype='pdf')as before,f.open(path)as after:
  pix=[]
  for pg in [before[0],after[0]]:
   p=pg.get_pixmap(matrix=f.Matrix(4,4),clip=clip,colorspace=f.csGRAY,alpha=False);pix.append(np.frombuffer(p.samples,np.uint8).reshape(p.height,p.width).copy())
  assert pix[0].shape==pix[1].shape;changed=int((pix[0]!=pix[1]).sum());ink=int((pix[0]<220).sum());assert ink>0
  a=Path(folder)/'page39.native-atom-original-4x.png';b=Path(folder)/'page39.native-atom-candidate-4x.png';before[0].get_pixmap(matrix=f.Matrix(4,4),clip=clip,alpha=False).save(a);after[0].get_pixmap(matrix=f.Matrix(4,4),clip=clip,alpha=False).save(b)
 result=dict(page=39,passed=changed==0,proof_sha256=sha(path),layout_sha256=sha(path.with_suffix('.layout.json')),source_sha256=sha(source),source_profile_sha256=sha(profile),common_dx=dx,comparison_clip=r,comparison_scale=4,actual_grayscale_pixels_different=changed,nonempty_original_native_atom_ink_pixels=ink,expected_original_shift_control_sha256=sha(control),expected_image=str(a),expected_image_sha256=sha(a),candidate_image=str(b),candidate_image_sha256=sha(b),source_glyph_font_size_baselines_and_both_native_graphic_programs_compared=True,program_sha256=sha(__file__))
 out=Path(folder)/'page39.native-atom-appearance-audit.json';assert not out.exists();out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n','utf8')
 if require_pass:assert changed==0,result
 return result
if __name__=='__main__':
 result=run(Path(sys.argv[1]),len(sys.argv)<3);print(json.dumps(dict(passed=result['passed'],changed_pixels=result['actual_grayscale_pixels_different'],original_ink=result['nonempty_original_native_atom_ink_pixels'])))

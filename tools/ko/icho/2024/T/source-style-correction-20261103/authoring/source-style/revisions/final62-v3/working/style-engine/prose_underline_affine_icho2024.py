"""Wrap only exact original source m/l/S underline bytes in a page-x affine."""
from pathlib import Path
from io import BytesIO
import hashlib,math
import pikepdf,pymupdf as fitz
import latex_native_motion as motion
ROOT=Path('D:/CodexBuilds/Hasla-poi-natural-20261102/style-corrections/icho2024-20261103')
SOURCE=ROOT/'frozen/source/IChO_2024_T_EN.pdf';SOURCE_SHA='959174ab5ddc8be71c251c8fe95a12c810ba730edbcbbef3b771197e32929a4a'
def inverse(m):
 a,b,c,d,e,f=m;det=a*d-b*c
 if abs(det)<1e-14:raise ValueError('Singular source CTM')
 return(d/det,-b/det,-c/det,a/det,(c*f-d*e)/det,(b*e-a*f)/det)
def apply(moved,source,n,specs):
 if Path(source).resolve()!=SOURCE or hashlib.sha256(SOURCE.read_bytes()).hexdigest()!=SOURCE_SHA:raise ValueError('2024 private source guard')
 with fitz.open(source)as d:page_matrix=tuple(map(float,d[n-1].transformation_matrix))
 journal=[]
 with pikepdf.Pdf.open(BytesIO(moved))as pdf:
  page=pdf.pages[0];raw,regions=motion._raw_regions(page);original=raw;claims=[]
  parsed=list(pikepdf.parse_content_stream(page));states=[];ctm=(1.,0.,0.,1.,0.,0.);at={}
  for i,ins in enumerate(parsed):
   at[i]=ctm;op=str(ins.operator)
   if op=='q':states.append(ctm)
   elif op=='Q':ctm=states.pop()
   elif op=='cm':ctm=motion._multiply(tuple(map(float,ins.operands)),ctm)
  if states:raise ValueError('Moved source graphics stack is not balanced')
  for spec in specs:
   ref=spec['source_program'];fragment=ref['source_construction_and_paint_fragment_latin1'].encode('latin1')
   if hashlib.sha256(fragment).hexdigest()!=ref['source_construction_and_paint_fragment_sha256']or raw.count(fragment)!=1:raise ValueError('Source underline bytes missing/ambiguous')
   a=raw.index(fragment);z=a+len(fragment);indices=[i for i,(b,e,op)in enumerate(regions)if a<=b and e<=z]
   if [str(parsed[i].operator)for i in indices]!=['m','l','S']:raise ValueError('Only original pure m/l/S source prose underline allowed')
   here=at[indices[0]]
   if max(abs(x-y)for x,y in zip(here,ref['source_entry_ctm']))>1e-12:raise ValueError('Original underline source entry CTM changed')
   r=spec['source_rect'];t=spec['target_rect'];sx=(t[2]-t[0])/(r[2]-r[0]);tx=t[0]-sx*r[0]
   if not(math.isfinite(sx)and math.isfinite(tx)and sx>0)or t[1]!=r[1]or t[3]!=r[3]:raise ValueError('Only finite positive horizontal underline affine allowed')
   m=motion._multiply(here,page_matrix);h=(sx,0.,0.,1.,tx,0.);local=motion._multiply(motion._multiply(m,h),inverse(m))
   for point in [(r[0],r[1]),(r[2],r[3])]:
    pp=motion._point(h,*point)
    if abs(pp[1]-point[1])>1e-12:raise ValueError('Underline y changed')
   prefix=('\nq '+' '.join(format(v,'.17g')for v in local)+' cm ').encode('ascii');replacement=prefix+fragment+b'\nQ\n'
   claims.append((a,z,replacement));journal.append(dict(id=spec['id'],source_fragment_sha256=hashlib.sha256(fragment).hexdigest(),source_fragment_literal_preserved=True,source_operator_names=['m','l','S'],source_page_entry_ctm=here,page_matrix=page_matrix,page_x_affine=h,local_matrix=local,source_rect=r,target_rect=t,source_y_and_vertical_stroke_scale_unchanged=True))
  for a,z,replacement in sorted(claims,reverse=True):raw=raw[:a]+replacement+raw[z:]
  if len(claims)!=len(specs):raise ValueError('Not every source underline claimed exactly once')
  page.Contents=pdf.make_stream(raw);out=BytesIO();pdf.save(out,compress_streams=False)
 return out.getvalue(),dict(passed=True,input_moved_sha256=hashlib.sha256(moved).hexdigest(),output_moved_sha256=hashlib.sha256(out.getvalue()).hexdigest(),source_sha256=SOURCE_SHA,source_paths=len(specs),paths=journal,all_other_source_content_bytes_preserved_by_exact_splices=True,original_content_sha256=hashlib.sha256(original).hexdigest(),new_content_sha256=hashlib.sha256(raw).hexdigest(),program_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())

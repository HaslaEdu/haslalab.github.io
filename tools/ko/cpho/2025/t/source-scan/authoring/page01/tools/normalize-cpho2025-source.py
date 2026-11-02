from pathlib import Path
import json,hashlib,pikepdf
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/cpho2025');B.mkdir(exist_ok=True);source=Path.cwd()/'haslalab/tmp/original-style-sources/CPhO_2025_Chinese_original.pdf';target=B/'CPhO_2025_T_original-explicit-page-clip.pdf'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();assert sha(source)=='b7c3ff8e024d4805306b7cd7e11bb22dd487ff1ee1aa6a504f096a1676296957'
rows=[]
with pikepdf.open(source)as doc:
 for n,page in enumerate(doc.pages,1):
  assert list(page.MediaBox)==[0,0,595,842]
  streams=list(page.Contents)if isinstance(page.Contents,pikepdf.Array)else[page.Contents];raw=b'\n'.join(s.read_bytes()for s in streams)
  assert len([op for op in pikepdf.parse_content_stream(page)if str(op.operator)=='Do'])==1
  old_images={str(name):hashlib.sha256(obj.read_raw_bytes()).hexdigest()for name,obj in page.Resources.XObject.items()if str(obj.get('/Subtype'))=='/Image'}
  page.Contents=doc.make_stream(b'q\n0 0 595 842 re W n\n'+raw+b'\nQ\n')
  rows.append(dict(page=n,original_contents_raw_sha256=hashlib.sha256(raw).hexdigest(),original_encoded_image_sha256=old_images,only_change='Explicit page-boundary clip equal to the existing page extent; every original q/cm/ri/Do/Q paint byte retained within it.'))
 doc.save(target,compress_streams=False)
with pikepdf.open(target)as doc:
 for row,page in zip(rows,doc.pages):
  images={str(name):hashlib.sha256(obj.read_raw_bytes()).hexdigest()for name,obj in page.Resources.XObject.items()if str(obj.get('/Subtype'))=='/Image'}
  assert images==row['original_encoded_image_sha256']
q=dict(source=str(source),source_sha256=sha(source),normalized_source=str(target),normalized_sha256=sha(target),original_bitmap_programs_retained=True,mathematics_recognized_or_retyped=False,pages=rows,render_validation='PENDING')
(B/'source-clip-normalization.json').write_text(json.dumps(q,ensure_ascii=False,indent=2)+'\n','utf8');print(json.dumps(dict(file=str(target),pages=len(rows),bytes=target.stat().st_size,sha256=sha(target))))

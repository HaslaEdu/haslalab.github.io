"""Unreviewed source character locations only; never mathematical transcription."""
from pathlib import Path
import sys,json,hashlib
import numpy as np
from PIL import Image
from rapidocr_onnxruntime import RapidOCR
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/cpho2005/TS')
page=int(sys.argv[1]);source=B/'inputs/CPhO_2005_Chinese_original.pdf';expected='9867b5116f1feb921515844332d43ed08a7c790292d5eecd89c70aacdf698b4f'
assert hashlib.sha256(source.read_bytes()).hexdigest()==expected
draft=json.loads((B/f'row-hints/ocr-page{page:02}-draft.json').read_text('utf8'))
image=Image.open(B/f'source-renders/page{page:02}.png').convert('RGB');scale=draft['scale']
rec=RapidOCR(intra_op_num_threads=1,inter_op_num_threads=1).text_recognizer;rows=[]
for index,line in enumerate(draft['lines']):
 xs=[v[0]for v in line['polygon']];ys=[v[1]for v in line['polygon']]
 box=[int(min(xs)),int(min(ys)),int(max(xs)+.999),int(max(ys)+.999)]
 if box[2]<=box[0]or box[3]<=box[1]:continue
 crop=np.array(image.crop(box));h,w=crop.shape[:2];normal=rec.resize_norm_img(crop,w/h)
 preds=rec.session(normal[np.newaxis,:].astype(np.float32))[0];decoded=rec.postprocess_op(preds)[0]
 ids=preds.argmax(axis=2)[0];prob=preds.max(axis=2)[0];peaks=[]
 for step,code in enumerate(ids):
  if not code or(step and code==ids[step-1]):continue
  x=(box[0]+(step+.5)/len(ids)*(box[2]-box[0]))/scale
  peaks.append(dict(c=rec.postprocess_op.character[int(code)],x=x,confidence=float(prob[step])))
 rows.append(dict(hint=index,rect=[v/scale for v in box],draft_text=line['text'],ctc_text=decoded[0],ctc_peaks=peaks,reviewed=False,may_erase=False,mathematical_transcription_forbidden=True))
target=B/f'row-hints/page{page:02}-ctc-location-proposals.json'
target.write_text(json.dumps(dict(source_sha256=expected,page=page,location_only=True,requires_manual_source_bitmap_review=True,may_erase=False,rows=rows),ensure_ascii=False,indent=2)+'\n','utf8')
print('UNREVIEWED_SOURCE_LOCATIONS',page,len(rows),target,flush=True)

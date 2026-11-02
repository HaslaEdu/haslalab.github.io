"""Read-only CTC location candidates for manually transcribed scanned rows.

Candidates are never erase regions. Source CJK/math boundaries and complete
two-dimensional mathematical objects must be approved in the document plan.
"""
from pathlib import Path
import argparse,json,re,sys
import numpy as np
from PIL import Image,ImageDraw,ImageFont
from rapidocr_onnxruntime import RapidOCR

BASE=Path('D:/CodexBuilds/Hasla-original-style-20261031/cpho2013/TS')
MANUAL_ROWS={
 (5,'angular-speed-definition'):[76,367.5,286,395],
 (5,'roots-original-reference13'):[75,641.5,521,665],
 (5,'root-conclusion-intro'):[75,665,87,678],
 (6,'equivalent-radius'):[75,378,87,391],
 (7,'equivalent-quadratic'):[73,204,86,219],
 (10,'ratio-result'):[75,703,88,717],
 (12,'trigonometric-and'):[75,70,89,84],
 (12,'small-angle-when'):[280,85.5,292,98],
}

def main(page):
    plan=json.loads((BASE/'authoring'/f'page{page:02d}.json').read_text('utf8'))
    draft=json.loads((BASE/'authoring'/f'page{page:02d}-language-draft.json').read_text('utf8'))
    filename=BASE/'source-renders'/f'page{page:02d}.png'
    if page==4:filename=BASE.parent/'page04-source-2x.png'
    original=Image.open(filename).convert('RGB');scale=2
    rec=RapidOCR(intra_op_num_threads=1,inter_op_num_threads=1).text_recognizer
    byhint={int(h['id'].split('ocr')[1]):h for h in plan['ocr_location_hints']}
    rows=[];out=BASE/'row-hints';out.mkdir(exist_ok=True)
    for row in draft['rows']:
        hints=[byhint[i] for i in row.get('hints',[]) if i in byhint]
        manual=MANUAL_ROWS.get((page,row['id']))
        if not hints and not manual:
            rows.append(dict(id=row['id'],manual_source_row_required=True));continue
        rect=manual or[min(h['approximate_rect'][0] for h in hints),min(h['approximate_rect'][1] for h in hints),max(h['approximate_rect'][2] for h in hints),max(h['approximate_rect'][3] for h in hints)]
        box=[int(rect[0]*scale),int(rect[1]*scale),int(rect[2]*scale+.999),int(rect[3]*scale+.999)]
        crop=np.array(original.crop(box));h,w=crop.shape[:2]
        normal=rec.resize_norm_img(crop,w/h)
        preds=rec.session(normal[np.newaxis,:].astype(np.float32))[0]
        decoded=rec.postprocess_op(preds)[0];ids=preds.argmax(axis=2)[0];prob=preds.max(axis=2)[0]
        peaks=[]
        for step,code in enumerate(ids):
            if not code or(step and code==ids[step-1]):continue
            x=rect[0]+(step+.5)/len(ids)*(rect[2]-rect[0])
            peaks.append(dict(c=rec.postprocess_op.character[int(code)],x=x,confidence=float(prob[step])))
        rows.append(dict(id=row['id'],source=row['source'],rect=rect,ocr_text=decoded[0],ctc_peaks=peaks,manual_review_required=True,may_erase=False))
    target=out/f'page{page:02d}-ctc.json'
    target.write_text(json.dumps(dict(source_page=page,source_sha256=plan['source_sha256'],location_only=True,rows=rows),ensure_ascii=False,indent=2)+'\n','utf8')
    print(target)

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('page',type=int)
    from pdf_memory_gate import page_worker
    with page_worker():main(parser.parse_args().page)

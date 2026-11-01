"""Location candidates only; no candidate is approved or usable for erasure.

The source template is manually transcribed. CTC supplies rough locations,
and original bitmap columns only refine candidate separators. Every result
requires contact-sheet and complete-page review before becoming a layout.
"""
from pathlib import Path
import json,re,difflib,argparse,math
import numpy as np
from PIL import Image,ImageDraw

BASE=Path('D:/CodexBuilds/Hasla-original-style-20261031/cpho2013/TS')
MATH=re.compile(r'[^\u3400-\u9fff，。；：、？！“”（）《》 \t]+')
ORDERS={
 (5,'wall-normal-force'):['ball1-normal','normal-T','cm-c','x-motion'],
 (5,'leaving-wall'):['ball1-leave-a','eq11-leave','ball1-leave-b','theta-leave'],
 (5,'roots-original-reference13'):['eq13-root-a','sin-zero','theta-zero','eq13-root-b','other-root'],
 (6,'centrifugal-work-a'):['m-work-L','W-L','radius-proportional'],
 (7,'tube-force-e'):['eq3-model','eq4-model','dl-local','radius-local'],
 (9,'general-motion'):['time-t','coordinate-z'],
 (10,'divide-conduction-equations'):['eq6-divisor','eq7-dividend','eq4-sum'],
 (11,'reference-ray-a'):['part1','angle45-a','AP','z-positive'],
 (11,'reference-ray-b'):['PB','axis-y-Q','point-Q'],
 (11,'nearby-ray-c'):['axis-y-E','point-E'],
 (12,'PPplus-angle'):['segment-PPplus','segment-QB','angle45-b'],
 (12,'second-method-right-triangle'):['ray-PplusBplus','axis-y-E2','point-E2','triangle-EQplusPplus'],
 (13,'event1-Wang-time'):['S-Wang-event1','event1-time','t-doubleprime1'],
 (13,'event2-Zhang-time'):['S-Zhang-time2','event2-time','tprime2'],
 (13,'nth-clap-time-a'):['nth-clap','event-2n-minus1','S-Zhang-nth','tprime-nth'],
}

def anchor(c):return '\u3400'<=c<='\u9fff'or c in'，。；：、,.;:（）'
def strong(c):return '\u3400'<=c<='\u9fff'or c in'（）'
def normalize(c):return {'，':',','。':'.','；':';','：':':','、':',','间':'问','（':'(', '）':')','−':'-'}.get(c,c)

def create(page):
    plan=json.loads((BASE/'authoring'/f'page{page:02d}.json').read_text('utf8'))
    draft=json.loads((BASE/'authoring'/f'page{page:02d}-language-draft.json').read_text('utf8'))
    hints=json.loads((BASE/'row-hints'/f'page{page:02d}-ctc.json').read_text('utf8'))
    byid={r['id']:r for r in hints['rows']}
    src=Image.open(BASE/'source-renders'/f'page{page:02d}.png').convert('RGB');gray=np.asarray(src).min(axis=2)
    rows=[];pictures=[]
    for row in draft['rows']:
        h=byid[row['id']]
        if 'rect'not in h:rows.append(dict(**row,manual_source_row_required=True));continue
        rect=h['rect'];images=[im for im in plan['source_images']if im['bbox'][1]-.1<=(rect[1]+rect[3])/2<=im['bbox'][3]+.1]
        if len(images)!=1:raise ValueError(('Source image ambiguity',page,row['id'],images))
        image=images[0]
        # Source image dimensions are resolved from original metadata, never OCR.
        import pymupdf as fitz
        with fitz.open(plan['source'])as doc:
            meta=doc[page-1].get_image_info()[plan['source_images'].index(image)]
        size=round(21.70*(image['bbox'][3]-image['bbox'][1])/meta['height'],3)
        spans=[m for m in MATH.finditer(row['source'])if m.group()not in['“','”']]
        ids=ORDERS.get((page,row['id']),re.findall(r'\[\[([^\]]+)\]\]',row['en']))
        if len(spans)!=len(ids):raise ValueError(('Manual source math-span mapping required',page,row['id'],[s.group()for s in spans],ids))
        excluded=set(i for s in spans for i in range(s.start(),s.end()))
        source_anchor=[(i,c)for i,c in enumerate(row['source'])if i not in excluded and anchor(c)]
        ocr_anchor=[p for p in h['ctc_peaks']if anchor(p['c'])]
        seq=difflib.SequenceMatcher(None,[normalize(c)for i,c in source_anchor],[normalize(p['c'])for p in ocr_anchor],autojunk=False)
        mapped={}
        for block in seq.get_matching_blocks():
            for off in range(block.size):
                pos,c=source_anchor[block.a+off];mapped[pos]=ocr_anchor[block.b+off]
        full_source=[(i,c)for i,c in enumerate(row['source'])if not c.isspace()and c not in'_^{}']
        full_ocr=h['ctc_peaks'];full_map={}
        full_match=difflib.SequenceMatcher(None,[normalize(c)for i,c in full_source],[normalize(p['c'])for p in full_ocr],autojunk=False)
        for block in full_match.get_matching_blocks():
            for offset in range(block.size):full_map[full_source[block.a+offset][0]]=full_ocr[block.b+offset]
        atoms=[]
        for span_index,(span,name)in enumerate(zip(spans,ids)):
            previous=[p for p in mapped if p<span.start()and strong(mapped[p]['c'])]
            following=[p for p in mapped if p>=span.end()and strong(mapped[p]['c'])]
            # Only use weak punctuation to separate adjacent mathematical
            # atoms. A phantom OCR comma inside an isolated formula may not
            # truncate that formula before the next known Chinese character.
            if span_index and(not previous or spans[span_index-1].end()>max(previous)):
                weak=[p for p in mapped if spans[span_index-1].end()<=p<span.start()]
                if weak:previous=weak
            if span_index+1<len(spans)and(not following or spans[span_index+1].start()<min(following)):
                weak=[p for p in mapped if span.end()<=p<spans[span_index+1].start()]
                if weak:following=weak
            if previous:
                p=mapped[max(previous)];left=p['x']+size*(.43 if strong(p['c'])else .12)
            else:left=rect[0]
            if following:
                p=mapped[min(following)];right=p['x']-size*(.43 if strong(p['c'])else .12)
            else:right=rect[2]
            def separator(x):
                lo=max(0,int((x-1.8)*2));hi=min(gray.shape[1]-1,int((x+1.8)*2)+1)
                yy0,yy1=max(0,int(rect[1]*2)),min(gray.shape[0],int(rect[3]*2+.999))
                cols=(gray[yy0:yy1,lo:hi]<160).sum(axis=0)
                candidates=sorted(range(lo,hi),key=lambda v:(cols[v-lo],abs(v/2-x)))
                return candidates[0]/2
            clip=image['bbox'][:]
            for boundary in image['ancestor_clip_rects']:
                if boundary is None:raise ValueError('Unknown source image clip')
                clip=[max(clip[0],boundary[0]),max(clip[1],boundary[1]),min(clip[2],boundary[2]),min(clip[3],boundary[3])]
            box=[max(separator(left),clip[0]),max(rect[1]-.2,clip[1]),min(separator(right),clip[2]),min(rect[3]+.1,clip[3])]
            endpoint_refinement=False
            if re.fullmatch(r'\(\d+\)',span.group())and span.start()in full_map and span.end()-1 in full_map:
                first,last=full_map[span.start()]['x'],full_map[span.end()-1]['x']
                if box[0]-1<=first<last<=box[2]+1:
                    refined_left=separator(max(box[0],first-size*.42));refined_right=separator(min(box[2],last+size*.42))
                    if refined_left<refined_right:
                        box[0]=max(box[0],refined_left);box[2]=min(box[2],refined_right);endpoint_refinement=True
            atom=dict(id=name,expected_original=span.group(),rect=box,image_path=image['path'],reviewed=False,
                location_only=True,exact_reference_ctc_endpoint_hint=endpoint_refinement,reason='Candidate matched from manually transcribed source prose anchors; requires whole-math/adjacent-CJK pixel review.')
            atoms.append(atom)
            pictures.append((row['id'],atom))
        rows.append(dict(**row,size=size,baseline=None,left=rect[0],right=min(522.75,image['bbox'][2]),erase_rects=[[rect[0]-.6,rect[1]-.2,rect[2]+.8,min(rect[3]+.1,image['bbox'][3])]],atoms=atoms,source_atom_ids=ids,
            reviewed=False,location_only=True,source_anchor_match_count=len(mapped),source_anchor_count=len(source_anchor),source_image_path=image['path']))
    out=BASE/'row-hints'/f'page{page:02d}-geometry-candidates.json'
    out.write_text(json.dumps(dict(source_page=page,source_sha256=plan['source_sha256'],manual_rois_reviewed=False,publication_ready=False,rows=rows),ensure_ascii=False,indent=2)+'\n','utf8')
    contact=Image.new('RGB',(1000,max(1,(len(pictures)+3)//4)*115),'white');draw=ImageDraw.Draw(contact)
    for i,(rid,atom)in enumerate(pictures):
        x,y=(i%4)*250,(i//4)*115;box=atom['rect']
        draw.text((x+3,y+2),f"{i}: {atom['id']}",fill='black')
        if box[2]<=box[0]:draw.text((x+3,y+25),'NEEDS MANUAL BOUNDS',fill='red');continue
        crop=src.crop(((box[0]-3)*2,(box[1]-2)*2,(box[2]+3)*2,(box[3]+2)*2));crop=crop.resize((crop.width*2,crop.height*2))
        if crop.width>245:crop=crop.resize((245,round(crop.height*245/crop.width)))
        contact.paste(crop,(x,y+22));factor=crop.width/(box[2]-box[0]+6)
        draw.rectangle((x+3*factor,y+22+2*factor,x+(box[2]-box[0]+3)*factor,y+22+(box[3]-box[1]+2)*factor),outline='red')
    contact.save(BASE/'row-hints'/f'page{page:02d}-candidate-contact.png')
    print(page,len(rows),len(pictures),out,flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('page',type=int);create(p.parse_args().page)

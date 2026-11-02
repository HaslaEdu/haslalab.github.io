"""Manually reviewed original page4 language rows and complete inline atoms."""
from pathlib import Path
import json,re
import cv2,numpy as np
import pymupdf as fitz
cv2.setNumThreads(1)
BASE=Path('D:/CodexBuilds/Hasla-original-style-20261031/cpho2013/TS')
SOURCE=Path('tmp/original-style-sources/CPhO_2013_Chinese_original.pdf')

def source_baseline(page,rect,source,size):
    candidates=re.findall(r'[\u3400-\u9fff]+',source)
    text=max(candidates,key=len)[:min(14,max(1,int((rect[2]-rect[0]-1)/size)))]
    measurement_rect=[rect[0]-1,rect[1]-1.5,rect[2]+1,rect[3]+1.5]
    pic=page.get_pixmap(matrix=fitz.Matrix(4,4),clip=fitz.Rect(measurement_rect),colorspace=fitz.csGRAY)
    mask=(np.frombuffer(pic.samples,np.uint8).reshape(pic.height,pic.width)<160).astype(np.float32)
    font=fitz.open();p=font.new_page(width=max(200,size*len(text)+15),height=32)
    p.insert_font(fontname='MeasuredSource',fontfile='C:/Windows/Fonts/simsun.ttc')
    p.insert_text((3,23),text,fontname='MeasuredSource',fontsize=size)
    pix=p.get_pixmap(matrix=fitz.Matrix(4,4),colorspace=fitz.csGRAY)
    glyphs=(np.frombuffer(pix.samples,np.uint8).reshape(pix.height,pix.width)<128).astype(np.uint8)
    glyphs=cv2.dilate(glyphs,np.ones((3,3),np.uint8));yy,xx=np.nonzero(glyphs)
    template=glyphs[yy.min():yy.max()+1,xx.min():xx.max()+1].astype(np.float32)
    _,intersection,_,point=cv2.minMaxLoc(cv2.matchTemplate(mask,template,cv2.TM_CCORR))
    # Comparison score is against the local matching patch, not unrelated row ink.
    patch=mask[point[1]:point[1]+template.shape[0],point[0]:point[0]+template.shape[1]]
    score=float(intersection/(template.sum()+patch.sum()-intersection))
    baseline=pic.y/4+point[1]/4+(23*4-int(yy.min()))/4
    font.close()
    return baseline,dict(character_run=text,source_rect=rect,read_only_measurement_rect=measurement_rect,size_fixed_before_translation=size,baseline=baseline,iou=score,source_threshold=160,reference_threshold=128,scan_spread_px_at4x=1)

def create():
    page=4;draft=json.loads((BASE/'authoring/page04-language-draft.json').read_text('utf8'))
    hints=json.loads((BASE/'row-hints/page04-ctc.json').read_text('utf8'))
    byhint={r['id']:r for r in hints['rows']}
    # Source image0/1 have slightly different pasted scales; image2 is about4.4%larger.
    scales=[9.78,9.715,10.215]
    atom_geometry={
      'first-impact': [('lambda',[332,136,339,149])],
      'nth-bounce': [('n',[117,351,125,365]),('n-plus-one',[174,351,196,365]),('v-n',[433.5,351,447,365]),('h-n',[456,351,468,365])],
      'geometric-series':[('series-terms',[77,455,112,469])],
      'from-six-twelve':[('eq6',[86,500.5,99.2,512.5]),('eq12',[105.5,500.5,123,512.5])],
      'impulse-definition':[('impulse-n',[105.5,539.5,115.5,552.5]),('collision-n',[173.5,539.5,184.2,552.5]),('n-condition',[185.5,539.5,223.5,552.5])],
      'upward-substitute':[('eq13',[139.3,628.5,156.5,642.5]),('eq15',[185.5,628.5,204.5,642.5])],
      'marking-title':[('total15',[148.5,660,163.5,671.5])],
      'marking-detail':[('mark1',[98,672,111.5,685.32]),('mark6',[119.6,672,131,685.32]),('point1a',[150.5,672,158.5,685.32]),('mark11',[177.2,672,195.2,685.32]),('point4',[206.5,672,214.8,685.32]),('mark12',[233.2,672,251.5,685.32]),('mark16',[261.5,672,276,685.32]),('point1b',[298,672,306.3,685.32])],
    }
    rows=[]
    with fitz.open(SOURCE)as doc:
        for row in draft['rows']:
            h=byhint[row['id']];rect=h['rect'];idx=0 if rect[1]<350 else 1 if rect[1]<593.12 else 2;size=scales[idx]
            if row['id']in['marking-title','marking-detail']:size=9.58
            original_rect=[rect[0]-.6,rect[1]-.2,rect[2]+.8,min(rect[3]+.1,685.32)]
            y,evidence=source_baseline(doc[3],rect,row['source'],size)
            atoms=[dict(id=name,rect=box,image_path=[[369],[378],[387]][idx],reason='Entire original inline notation, manually checked against the source page and CTC location hints; no OCR reconstruction.')for name,box in atom_geometry.get(row['id'],[])]
            r=dict(**row,size=size,baseline=y,left=rect[0],right=522.75,erase_rects=[original_rect],atoms=atoms,source_atom_ids=[a['id']for a in atoms],reviewed=True,baseline_evidence=evidence,
                printed_regular_stroke=round(.45*size/9.78,4),printed_bold_stroke=round((.55 if row['id']in['marking-title','marking-detail']else .6)*size/(9.58 if row['id']in['marking-title','marking-detail']else 9.78),4),
                scan_weight_evidence='font-calibration/p4-first-ten-actual-stroke.json, p4-speed-clause-actual-stroke.json, p4-reference-bold-actual-stroke.json; marking role independently p4-marking-prefix-joint.json. Source pointsize/stroke estimates only, no translated text or character-width adjustment.')
            if row['id']=='reference':r.update(render_mode=2,line_width=.15)
            if row['id']=='marking-title':r.update(render_mode=2,line_width=.1)
            r['printed_stroke_by_language']={'en':dict(regular=r['printed_regular_stroke'],bold=r['printed_bold_stroke']),
                'ko':dict(regular=round(.3*size/9.78,4),bold=round(.4*size/9.78,4),evidence='source-vs-Batang-stems.json/.png: original two regular CJK runs V/H medians .875/.50pt; Batang9.78 stroke.30 is the thinnest candidate matching both medians and contrast1.75. Fontpoint/advances fixed. Bold role modest.40, separately visually reviewed.')}
            rows.append(r)
    data=dict(source_page=4,source_sha256=draft['source_sha256'],manual_rois_reviewed=True,publication_ready=False,rows=rows,
        protected_source_display_and_figure_rects=[[200,149.8,255,165],[185,180,289,195],[184,209,254,237],[194,249,271,278],[191,298,275,312],[190,326,275,350],[187,379,246,454],[191,469.2,370,498],[190,513,218,535],[193,554,331,569],[198,593.12,417,627.5],[202,643,291,659],[430,657,453,685.32]],
        font_profiles=[dict(source_image=i,size=size,face='SimSun',basis='p4-first-ten/p4-speed-clause original-run calibration9.78pt; other chunks use original image physical-scale ratio, checked against original row pitch.',is_estimate=True)for i,size in enumerate(scales)],
        language_scope='Original Chinese prose only; entire original display formulae, equation numbers, existing partial figure and all other source ink remain stationary. Source raster dust inside manually reviewed language row background is classified separately from meaningful nonlanguage ink.',
        full_page_visual_review_required=True)
    from cpho_2013_ts_background_evidence import prepare
    data['reviewed_blank_background_rects']=prepare(data)
    target=BASE/'authoring/page04-layout.json';target.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n','utf8')
    print(target)
    for row in rows:print(row['id'],row['baseline'],round(row['baseline_evidence']['iou'],3),flush=True)

if __name__=='__main__':
    from pdf_memory_gate import page_worker
    with page_worker():create()

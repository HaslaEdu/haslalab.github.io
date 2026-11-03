"""Read-only fixed-source-face/point source-word baseline proposals."""
from pathlib import Path
import json,sys
import pymupdf as f,numpy as np,cv2
from PIL import Image,ImageDraw
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/cpho2005/TS')
fields={r['field']:r for r in json.loads((B/'page05-source-font-calibration.json').read_text('utf8'))['fields']}
# Explicit human-read source CJK samples. These are font measurement windows,
# never language erase regions or mathematical-object selection.
runs=[('angle-threshold','angle-top','故存在某一入射角',[149,61,254,81]),('angle-transit','angle-top','入射光以此',[65,92,132,112]),('angle-transit-end','angle-top','经历的时间相同',[65,113,159.5,132]),('section-two','left-narrow','二、',[89,133,117,150]),('axis-direction','left-narrow','取一水平',[89,149,143,168]),('axis-origin','left-narrow','与小物块',[129,168,181,187]),('axis-position','left-narrow','始位置重合',[66,186,133,206]),('release','left-narrow','弹簧尚未',[153,205,208,225]),('spring-system','left-narrow','弹力为零',[99,224,153,244]),('one-system','left-wide','作为一个系统',[62,247,139,265]),('system-force','left-wide','平直线上',[61,265,116,285]),('initial-friction','left-wide','给的数据可知',[61,284,140,305]),('initial-acceleration','left-wide','一起加速运动',[108,303,202,324]),('acceleration-definition','left-wide','则有',[76,322,107,342]),('zero-acceleration','left-wide','作用在',[130,361,171,381]),('equilibrium-position','left-wide','平衡时',[107,381,148,401]),('overshoot','left-wide','此时系统',[61,430,115,450]),('constant-gravity','left-wide','度变为零',[61,447,116,470]),('spring-restoration','left-wide','皆为恒力',[88,466,145,487]),('shm-period','left-wide','为平衡位置',[76,486,144,507]),('amplitude-and-time','right-top','振幅为',[438,97,478,115]),('right-travel','right-top','开始向右',[470,145,590,168]),('turning-forces','right-top','弹簧的伸',[460,164,516,185]),('turning-resultant','right-top','由题给的',[529,185,584,207]),('left-acceleration','right-middle','因此系统',[438,229,491,247]),('left-coordinates','right-middle','设系统加',[569,246,623,268]),('second-equilibrium','right-middle','系统平衡',[533,284,587,305]),('left-SHM-first','right-bottom','因系统具',[528,331,583,356]),('left-SHM-second','right-bottom','速度变为',[437,351,492,377]),('left-SHM-third','right-bottom','为平衡位置',[517,370,585,395]),('left-SHM-fourth','right-bottom','经历时间',[470,392,525,416]),('last-rest','right-bottom','的速度变',[471,439,526,463]),('extension','right-bottom','此时弹簧',[490,479,556,499])]
results=[];samples=[];cv2.setNumThreads(1)
with f.open(B/'inputs/CPhO_2005_Chinese_original.pdf')as doc,f.open()as probe:
 page=probe.new_page(width=180,height=40);page.insert_font(fontname='OriginalFace',fontfile='C:/Windows/Fonts/simsun.ttc')
 for id,field,text,rect in runs:
  size=fields[field]['best_by_face']['SimSun']['point_size'];pix=doc[4].get_pixmap(matrix=f.Matrix(4,4),clip=f.Rect(rect),colorspace=f.csGRAY,alpha=False);gray=np.frombuffer(pix.samples,np.uint8).reshape(pix.height,pix.width).copy();source=(gray<160).astype(np.float32)
  xref=probe.get_new_xref();probe.update_object(xref,'<<>>');probe.update_stream(xref,b'');page.set_contents(xref);page.insert_text((4,27),text,fontname='OriginalFace',fontsize=size)
  p=page.get_pixmap(matrix=f.Matrix(4,4),colorspace=f.csGRAY,alpha=False);a=(np.frombuffer(p.samples,np.uint8).reshape(p.height,p.width)<128).astype(np.uint8);candidates=[]
  for sx,sy in[(1,1),(2,1),(1,2)]:
   grown=cv2.dilate(a,np.ones((2*sy+1,2*sx+1),np.uint8))
   for angle in[-1,-.5,0,.5,1]:
    ink=grown if not angle else cv2.warpAffine(grown,cv2.getRotationMatrix2D((16,108),angle,1),grown.shape[::-1],flags=cv2.INTER_NEAREST,borderValue=0)
    yy,xx=np.nonzero(ink);template=ink[yy.min():yy.max()+1,xx.min():xx.max()+1].astype(np.float32)
    if template.shape[0]>source.shape[0]or template.shape[1]>source.shape[1]:continue
    _,inter,_,loc=cv2.minMaxLoc(cv2.matchTemplate(source,template,cv2.TM_CCORR));patch=source[loc[1]:loc[1]+template.shape[0],loc[0]:loc[0]+template.shape[1]];score=float(inter/(patch.sum()+template.sum()-inter))
    origin=[pix.x/4+(loc[0]+16-int(xx.min()))/4,pix.y/4+(loc[1]+108-int(yy.min()))/4]
    candidates.append(dict(source_origin=origin,source_baseline=origin[1],source_point_size=size,baseline_angle_degrees=-angle,spread=[sx,sy],iou=score))
  candidates.sort(key=lambda r:-r['iou']);assert candidates,(id,rect)
  r=dict(id=id,source_region=field,source_text=text,source_measurement_window=rect,best=candidates[0],top5=candidates[:5],reviewed=False,may_erase=False);results.append(r);samples.append((id+' '+str(candidates[0]['source_baseline']),gray));print(id,round(candidates[0]['iou'],3),candidates[0]['source_origin'],flush=True)
width=max(a.shape[1]for _,a in samples);height=sum(a.shape[0]+22 for _,a in samples);image=Image.new('RGB',(width,height),'white');draw=ImageDraw.Draw(image);y=0
for label,gray in samples:draw.text((2,y+2),label,fill='black');image.paste(Image.fromarray(gray),(0,y+21));y+=gray.shape[0]+22
image.save(B/'source-renders/page05-source-baseline-measurement-samples.png')
(B/'page05-row-baseline-proposals.json').write_text(json.dumps(dict(source_sha256='9867b5116f1feb921515844332d43ed08a7c790292d5eecd89c70aacdf698b4f',page=5,scope='Source CJK-only measurement at already independently measured physical font points. These are not erase ROIs. No mathematical transcription or target text fitting.',rows=results),ensure_ascii=False,indent=2)+'\n','utf8')

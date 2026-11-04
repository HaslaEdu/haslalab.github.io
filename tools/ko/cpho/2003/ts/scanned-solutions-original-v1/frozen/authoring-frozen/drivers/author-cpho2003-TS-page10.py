"""C03 hybrid last TS page: scanned native math above, digital native math below."""
from pathlib import Path
import json,math
from PIL import Image
import numpy as np
from fontTools.ttLib import TTFont
from fontTools.pens.boundsPen import BoundsPen
B=Path('C:/Users/andre/CodexWork/HaslaLab/translation-builds/cpho2003-original-native');T=B/'TS'
SHA='52f8a891d6129becf4d21ccb60f46997cedf9aa50123ffd147294cedcb121b63'
bbox=[54,79.67000732421877,336,201.92000732421877];w,h=861,373
def rect(v):
 x,y,r,b=v
 return[bbox[0]+x*282/w,bbox[1]+y*122.25/h,bbox[0]+r*282/w,bbox[1]+b*122.25/h]
def atom(id,box):
 v=rect(box)
 return dict(id=id,rect=[max(bbox[0],math.floor(v[0]*4)/4),max(bbox[1],math.floor(v[1]*4)/4),min(bbox[2],math.ceil(v[2]*4)/4),min(bbox[3],math.ceil(v[3]*4)/4)],image_path=[958],reason='Manually reviewed whole original scanned symbol and subscript; encoded image/scale/clip/CTM/y remain original.')
font=TTFont('D:/CodexBuilds/Hasla-original-style-20261031/english-face-repair/font-faces/SimSun-5.24.ttf');gs=font.getGlyphSet();em=font['head'].unitsPerEm
im=np.array(Image.open(T/'source-image-reading/page10-image01.jpeg').convert('L'))
def baseline(char,cell):
 x,y,r,b=cell;yy,xx=np.where(im[y:b,x:r]<100);lo=int(yy.min()+y);hi=int(yy.max()+y+1)
 p=BoundsPen(gs);gs[font.getBestCmap()[ord(char)]].draw(p);x0,y0,x1,y1=p.bounds
 a=bbox[1]+lo*122.25/h+y1/em*10.5;b=bbox[1]+hi*122.25/h+y0/em*10.5
 return(a+b)/2,dict(source_char=char,manual_source_cell_raw_pixels=cell,actual_original_ink_y_pixels=[lo,hi],fixed_original_point=10.5,source_top_bottom_baseline_estimate_spread_pt=abs(a-b),independent_source_baseline_estimate=(a+b)/2)
rows=[]
for id,box,c,cell,source,ko,en,atoms in [
 ('scan-intro',[0,0,780,38],'复',[31,0,64,34],'设复合粒子的速度为v1，动量和能量分别为p1和E1，有','복합 입자의 속력 [[v1]], 운동량 [[p1]], 에너지 [[E1]]:','Composite: speed [[v1]], momentum [[p1]], energy [[E1]]:',[atom('v1',[294,0,328,35]),atom('p1',[603,0,637,36]),atom('E1',[684,0,722,36])]),
 ('scan-conservation',[0,237,490,279],'粒',[0,239,33,278],'粒子复合过程中动量、能量守恒，有','입자의 결합 중 운동량과 에너지는 보존되므로','Momentum and energy are conserved in combination:',[]),
]:
 base,evidence=baseline(c,cell);v=rect(box);rows.append(dict(id=id,reviewed=True,source=source,ko=ko,en=en,size=10.5,source_prose_face='SimSun',render_mode=0,baseline=base,left=54,right=336,erase_rects=[v],source_atom_ids=[a['id']for a in atoms],atoms=atoms,independent_original_baseline_measurement=evidence))
q=dict(source_page=10,source_sha256=SHA,manual_rois_reviewed=True,publication_ready=False,rows=rows,hybrid_complete_native_expression_header_control=True,source_scanned_body_fixed_physical_point=10.5,original_native_body_prose_point=10.5600004196167,original_native_mathematical_points_and_scripts_unchanged=True,protected_source_display_and_figure_rects=[[144,94,336,124],[144,125,336,155],[170,173,336,189],[144,191,336,201.92000732421877],[90,244,275,277],[90,304,250,321],[90,350,326,395],[90,420,300,445]],reviewed_blank_background_rects=[],right_half_and_large_original_blank_regions_retained=True)
p=T/'authoring/page10-layout.json';assert not p.exists();p.write_text(json.dumps(q,ensure_ascii=False,indent=2)+'\n','utf8')
print('Hybrid10 complete bilingual prose plans prepared, native/scanned mathematical text remains original.')

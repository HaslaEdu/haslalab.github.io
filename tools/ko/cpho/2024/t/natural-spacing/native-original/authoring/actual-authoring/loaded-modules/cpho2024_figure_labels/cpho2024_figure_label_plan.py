"""Manually isolated original Chinese diagram words; native symbols stay put."""
from pathlib import Path
import json
B=Path(__file__).resolve().parents[1]
def label(id,page,image,source,rect,ko,en,group,align='center',rotation=0):
 return dict(id=id,page=page,image_index=image,source_text=source,source_word_roi_px=rect,ko=ko,en=en,source_font_measurement_group=group,alignment=align,rotation=rotation,reviewed=True)
LABELS=[
 label('spectrum-energy',1,0,'电子动能',[152,369,263,398],'전자 운동 에너지','Electron kinetic energy','spectrum-x','right'),
 label('spectrum-count',1,0,'电子的相对数目',[0,77,32,266],'상대 전자 수','Relative electron count','spectrum-y',rotation=90),
 label('single-splitter',2,2,'分束器',[279,198,413,240],'분할기','BS','beam-splitter'),
 label('mz-incident',2,4,'入射光',[45,33,153,70],'입사광','Input light','mz-incident'),
 label('mz-mirror1',2,4,'全反镜',[277,5,376,39],'전반사경','Mirror','mz-mirror','left'),
 label('mz-mirror2',2,4,'全反镜',[280,306,378,339],'전반사경','Mirror','mz-mirror','left'),
 label('mz-splitter-left',2,4,'分束器',[7,159,114,197],'분할기','BS','mz-incident'),
 label('mz-splitter-right',2,4,'分束器',[485,156,594,194],'분할기','BS','mz-incident'),
 label('mz-detector',2,4,'探测器',[540,290,627,332],'검출기','Det.','mz-incident'),
 label('optics-mirror',2,7,'全反镜',[136,27,262,73],'전반사경','Mirror','optics-slow','left'),
 label('optics-slow',2,7,'慢轴',[465,49,560,101],'느린 축','Slow','optics-slow'),
 label('optics-fast',2,7,'快轴',[496,258,582,307],'빠른 축','Fast','optics-slow'),
 label('optics-linear',2,7,'线偏振',[983,65,1106,116],'선편광','linear pol.','optics-slow','left'),
 label('quad-mirror1',3,1,'全反镜',[1,6,42,25],'전반사경','Mirror','quadrature-mirror','right'),
 label('quad-splitter1',3,1,'分束器',[56,12,95,29],'분할기','BS','quadrature-mirror','right'),
 label('quad-path2',3,1,'光路',[166,12,194,29],'광로','arm','quadrature-mirror','right'),
 label('quad-mirror2',3,1,'全反镜',[251,9,292,26],'전반사경','Mirror','quadrature-mirror','right'),
 label('quad-vertical-polarizer',3,1,'线偏振片',[34,44,49,113],'선편광판','LP','quadrature-mirror',rotation='stack'),
 label('quad-path1',3,1,'光路',[86,75,111,92],'광로','arm','quadrature-mirror','right'),
 label('quad-mirror4',3,1,'全反镜',[91,49,132,65],'전반사경','Mirror','quadrature-mirror','right'),
 label('quad-polarizer45',3,1,'线偏振片',[157,82,209,102],'선편광판','LP','quadrature-mirror','right'),
 label('quad-degree-unit',3,1,'度',[227,83,240,102],'도','°','quadrature-mirror','left'),
 label('quad-polarizer-h',3,1,'线偏振片',[178,102,227,120],'선편광판','LP','quadrature-mirror','right'),
 label('quad-mirror3',3,1,'全反镜',[256,81,296,98],'전반사경','Mirror','quadrature-mirror','right'),
 label('quad-mirror5',3,1,'全反镜',[39,139,80,154],'전반사경','Mirror','quadrature-mirror','right'),
 label('quad-splitter2',3,1,'分束器',[149,137,188,153],'분할기','BS','quadrature-mirror','right'),
 label('quad-detector-b',3,1,'探测器',[241,145,281,164],'검출기','Det.','quadrature-mirror','right'),
 label('quad-laser',3,1,'激光器',[0,183,46,199],'레이저','Laser','quadrature-mirror'),
 label('quad-polarizer-v',3,1,'线偏振片',[157,177,209,198],'선편광판','LP','quadrature-mirror','right'),
 label('quad-detector-a',3,1,'探测器',[158,202,196,221],'검출기','Det.','quadrature-mirror','right'),
 label('wheel-torque',4,1,'扭矩',[137,424,231,478],'토크','Torque','wheel-torque'),
]
for item in LABELS:
 if item['source_text']=='全反镜':
  item['ko']='반사경'
  item['terminology_note']='Conventional compact diagram noun, mirror; total reflection is explicitly retained in the surrounding original translated body and native mirror matrices.'
 if item['id']=='wheel-torque':item['source_word_regions_px']=[[137,424,183,478],[183,426,231,478]]
 if item['id']=='wheel-torque':item['source_named_glyph_measurement']=dict(char='扭',rect=[137,424,183,478])
 if item['id']=='mz-splitter-left':item['source_named_glyph_measurement']=dict(char='束',rect=[45,159,79,197])
 if item['id']=='mz-splitter-right':item['source_named_glyph_measurement']=dict(char='束',rect=[520,156,558,194])
 if item['id']=='quad-degree-unit':item['english_original_closing_parenthesis_reuse']=dict(source_image_index=1,source_clip_rect_px=[240,83,248,103],original_character=')',reason='The Chinese degree unit becomes the narrower English degree symbol. Move the exact original bitmap closing parenthesis horizontally with the translated unit, retaining its source pixels, size, original CTM scale and y; do not retype it.')
 if item['source_text']=='光路':item['english_terminology_note']='An interferometer optical path is labelled as an arm; the original1/2 indices are retained.'
 if item['id']in['quad-path1','quad-polarizer-h','quad-splitter2','quad-detector-a']:
  item['reviewed_shared_source_bitmap_component_partition']=dict(reviewed=True,reason='The named Chinese glyph touches the original diagram component in the low-resolution source bitmap. Only its tightly reviewed Chinese word area is replaced; every source component pixel outside this area, including the arrow/element edge, native indices and parentheses, remains protected. No diagram geometry is newly drawn.',native_component_ids=[31]if item['id']=='quad-path1'else[20])
assert len(LABELS)==31
if __name__=='__main__':
 out=B/'authoring/T/figure-language-labels.json';out.write_text(json.dumps(dict(source_sha256='894111e1298dc785e9447252219e1f72fe0bb3fdf35b7573affec64f844ff6f6',labels=LABELS,font_sizes_are_source_only_measured_estimates=True,no_target_font_fitting=True,native_indices_units_and_geometry_are_not_retyped=True,english_standard_figure_abbreviations={'BS':'beam splitter','LP':'linear polarizer','Det.':'detector'}),ensure_ascii=False,indent=2)+'\n','utf8');print('AUTHORED',len(LABELS),'source-word label records')

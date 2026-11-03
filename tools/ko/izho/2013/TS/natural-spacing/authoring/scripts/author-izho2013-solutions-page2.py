from izho2013_authoring import begin,around,finish
p=begin(2)
around(p,'1,1,0',['용기 안의 공기가 ','에서 만드는 압력은 다음과 같다: '],['200ºC'])
for at,text in{
 '3,1,0':'같은 온도에서 증기압은 ',
 '5,0,0':'이다. 따라서 ',
 '5,1,0':'물이 모두 증발한 뒤, 온도 ',
 '5,1,2':'에서의 증기압은 다음과 같다: ',
 '7,1,0':'포화 증기압을 ',
 '7,2,0':'물이 모두 증발하는 온도는 다음 방정식의 해로 구한다: ',
 '9,1,0':'함수 모양을 몰라도 잘 알려진 관계로 해를 확인할 수 있다. 함수 ',
 '11,0,0':'를 만족하므로, 이 온도가 해이다. ',
 '13,1,0':'평가 항목 ',
 '13,2,0':'배점 ',
 '15,3,0':'임의의 온도에서 증기압을 구함 ',
 '15,6,0':'증발 온도 ',
 '15,6,3':'의 조건 제시 ',
 '15,9,0':'올바른 최종 답 ',
 '15,11,0':'합계 ',
 '15,17,0':'입사하는 광선을 생각하자. ',
 '15,18,0':'옆면에 대한 입사각은 옆면과 밑면 사이의 ',
 '15,19,0':'각과 같으며, 이 각은 ',
 '15,20,0':' ',
 '15,24,0':'이다. 기하학적으로 ',
 '16,0,0':'다음을 얻는다 ',
 '17,5,0':', 따라서 ',
 '18,0,0':'굴절 법칙에 따라 각 ',
 '18,0,2':'는 ',
 '18,1,0':'다음과 같다: ',
 '19,11,0':'. 따라서 ',
 '21,0,0':'피라미드 옆면의 높이는 ',
 '22,0,0':'피라미드의 높이는 ',
 '23,0,0':'따라서 ',
 '23,14,0':'이다. 구하는 점의 ',
 '24,0,0':'위치는 다음 거리로 나타난다: ',
 '25,0,0':' ',
 '25,17,0':'. 또한 ',
 '26,0,0':'같은 점은 다음 거리만큼 떨어져 있다: ',
}.items():p.add(at,text)
around(p,'7,1,4',['','라 하자. '],[')'])
around(p,'9,2,3',['','는 '],[')'])
around(p,'12,0,0',['채점 기준: 문제 ',': '],['1B'])
around(p,'13,4,0',['올바른 공기 압력: ',''],['T=200'])
around(p,'15,15,0',['문제 ',' 피라미드 '],['1.С'])
around(p,'15,16,0',['',' 피라미드 꼭짓점 부근의 옆면으로 '],['1.'])
around(p,'20,0,0',['광선이 밑면에 도달하는 점 ','를 구하자. '],['F'])
for slot in p.slots:
 if slot['at']in[[13,1,0],[13,2,0]]:slot['align']='center'
finish(p,[[12,0],[15,15]],'Complete original2013 page2 viewed at144dpi. Keep every original low-resolution vapor-pressure math bitmap, source200ºC text and T=200 glyphs exactly, native vap subscript at8.04pt, all table scores/decimal comma values and2.0 total, original pyramid/ray/construction figures, every Greek angle, AEO/AE/AO/OF/DF native expression, original cos/sin/tg and italic mm unit typography, original fractional script points and original source figure geometry. Source CyrillicС in the1C title remains native. Only explicit narrative language is translated, with no font fitting. Private authoring plan; not a publication PDF.')

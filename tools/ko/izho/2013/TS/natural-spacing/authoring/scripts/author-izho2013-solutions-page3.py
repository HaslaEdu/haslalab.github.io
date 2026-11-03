from izho2013_authoring import begin,around,finish
p=begin(3)
for at,text in{
 '1,11,0':'만큼 밑변의 중점에서 떨어져 있다. 따라서 옆면 ',
 '2,0,1':'에서 굴절한 광선은 피라미드 밑면의 삼각형을 비춘다. 다른 두 옆면도 ',
 '2,1,0':'대칭인 삼각형을 비춘다(그림 2). ',
 '2,3,2':'를 구하자. ',
 '2,4,0':'그림 1과 굴절 법칙을 이용하면 다음을 얻는다: ',
 '4,0,0':'이 각의 값은 ',
 '4,4,0':'이다. 한 옆면에서 굴절한 광선은 ',
 '4,5,0':'서로 평행하므로, 스크린에도 밑면과 닮은 영역이 생긴다. ',
 '4,6,0':'차이는 이 삼각형 영역들이 ',
 '4,17,0':'다음 거리만큼 옮겨진다는 점이다: ',
 '4,21,0':'그 거리는 ',
 '4,33,0':'따라서 ',
 '4,34,0':'스크린에 보이는 작은 삼각형 세 개는 한 변의 길이가 ',
 '4,35,0':'다음과 같은 삼각형의 꼭짓점들에 놓인다: ',
 '6,1,0':'평가 항목 ',
 '6,2,0':'배점 ',
 '6,4,0':'빛의 굴절 법칙 ',
 '6,7,0':'피라미드 옆면에 대한 입사각 ',
 '6,13,0':'피라미드 밑면의 밝은 영역 ',
 '6,16,0':'밑면에서의 출사각 ',
 '6,19,0':'스크린의 밝은 영역 ',
 '6,21,0':'합계 ',
 '8,0,0':'정사각형 고리 ',
}.items():p.add(at,text)
for i in [7,8,9,10,11,12,13,14,15,16,18,19,20,22,23,24]:p.add(f'4,{i},0','')
around(p,'2,3,0',['',' 피라미드 밑면에서 굴절한 광선의 각 '],['2.'])
around(p,'5,0,0',['채점 기준: 문제 ',': '],['1C'])
around(p,'6,10,0',['점 ','의 위치 '],['F'])
around(p,'7,0,0',['문제 ','점',' '],['2 (10 ',')'])
around(p,'9,1,0',['',' 자기력선은 북극에서 나와 남극으로 들어가는 것으로 정한다. '],['1.'])
p.add('9,2,0','따라서 그림은 다음과 같아야 한다. ')
around(p,'11,1,0',['',' 고리를 균일한 자기장 밖으로 꺼낼 때 유도 기전력은 '],['2.'])
p.add('11,2,0','패러데이 법칙으로 구할 수 있다. ')
for slot in p.slots:
 if slot['at']in[[6,1,0],[6,2,0]]:slot['align']='center'
finish(p,[[5,0],[7,0],[8,0]],'Complete original2013 page3 viewed at144dpi. Preserve original refracted-ray triangle and magnetic-pole/frame illustrations, all native equation symbols/roots/fraction rules and trigonometric function typography, source decimal commas, italic mm/cm units, the original gamma root and degree glyph, equation(1), original1C/2/10/1./2./F table references and all scores. Long English words previously individually justified are translated as a complete Korean clause on the same original physical row; empty selected prose fragments remove only the old word spacing. Full natural native-math packing and source-style audits remain required before publication.')

"""Source9 original-image myopia/diffraction and relativistic cosmic rays."""
from pathlib import Path
import sys
B=Path('C:/Users/andre/CodexWork/HaslaLab/translation-builds/cpho2003-original-native')
sys.path[:0]=[str(B/'TS/engine'),str(B/'engine')]
from cpho2003_manual_scan_layout import ManualPage
p=ManualPage(9);A=p.atom;R=p.row
R('pupil-hole',1,[0,0,862,34],'个',[0,1,34,33],'个小于瞳孔的小圆孔会使模糊像斑比由瞳孔决定的模糊像斑','동공보다 작은 원형 구멍은 흐린 빛 얼룩을 줄여','hole smaller than the pupil gives a smaller blur patch than')
R('clearer-than-pupil',1,[0,44,259,83],'小',[0,48,34,81],'小，能看得清晰些。','동공만일 때보다 선명하게 보이게 한다.','the pupil alone; the view is clearer.')
R('retinal-patch-lens',1,[65,92,862,130],'下',[66,96,100,129],'下面计算视网膜上光斑的直径。由图决解20-5-1，根据透','망막 얼룩 지름을 구하자. 그림 [[ref]]에서 렌즈','For retinal patch diameter, Fig. [[ref]] gives the lens',[A(1,'ref',[633,96,758,132])])
R('lens-formula',1,[0,140,106,178],'镜',[0,144,34,177],'镜公式','공식을 쓰면','formula:')
R('focal-length',1,[0,264,302,303],'可',[0,268,34,302],'可求得此时的焦距为','이때의 초점 거리는','The focal length is:')
R('far-object-reference-prefix',1,[65,386,428,425],'当',[66,390,100,424],'当眼睛处于图决解20-5-','그림 [[ref-prefix]]','In Fig. [[ref-prefix]]',[A(1,'ref-prefix',[329,389,423,426])],right=197)
R('parallel-object-rays',1,[0,434,862,474],'状',[22,438,57,472],'2状态观察远物时，从光轴上一物点射来的平行光，经过直径为','[[ref-tail]]처럼 먼 광축 위 물체점의 평행광이 지름','[[ref-tail]], rays from a distant axial point pass through a hole:',[A(1,'ref-tail',[0,437,18,477])],left=54,first_known_char_is_first_token=False)
R('hole-focus-retinal-patch',1,[0,482,862,521],'的',[31,486,66,520],'D的小孔后将会聚于焦点F，在网膜上出现直径为D′的光斑，','[[D]]인 구멍을 지나 [[F]]로 모여 망막에 지름 [[Dp]]인 얼룩이 생긴다.','diameter [[D]]. They converge at [[F]]; the retinal patch has [[Dp]].',[A(1,'D',[0,486,28,525]),A(1,'F',[364,486,393,526]),A(1,'Dp',[708,485,751,526])],left=54,first_known_char_is_first_token=False)
R('patch-reference',1,[0,530,345,569],'如',[0,534,34,568],'如图决解20-5-2所示。','그림 [[ref]]과 같다.','See Fig. [[ref]].',[A(1,'ref',[137,534,264,573])])
R('geometry-patch-diameter',1,[65,578,633,617],'由',[66,582,100,616],'由几何关系和式(2)，可得光斑的直径D′','기하학적 관계와 식 [[two]]에서 얼룩 지름 [[Dp]]은','Geometry and [[two]] give patch diameter [[Dp]]:',[A(1,'two',[295,581,339,620]),A(1,'Dp',[587,581,630,621])])
R('geometrical-optics',1,[0,701,783,740],'由',[0,705,34,739],'由式(3)可知，从几何光学的角度考虑，D越小，D′越小。','식 [[three]]에서 기하광학적으로 [[D]]가 작을수록 [[Dp]]도 작다.','By [[three]], geometric optics: smaller [[D]], smaller [[Dp]].',[A(1,'three',[66,704,115,744]),A(1,'D',[538,704,568,745]),A(1,'Dp',[654,704,694,745])])
R('diffraction-setup',1,[65,748,862,788],'现',[94,752,128,787],'2.现在考虑衍射问题。入射的平行光束经小孔后在透镜后','[[two]] 이제 회절을 고려하자. 평행광이 구멍을 지나 렌즈 뒤','[[two]] Include diffraction. A parallel beam through the hole forms',[A(1,'two',[65,752,96,792])],left=75,first_known_char_is_first_token=False)
R('diffraction-retina',1,[0,796,862,836],'的',[0,800,34,834],'的网膜上产生衍射圆斑，设其直径为D″，则根据题给公式的近','망막에 원형 회절 무늬를 만든다. 지름 [[Dpp]]에 문제의 근사식을','a round retinal spot. For its diameter [[Dpp]], the approximation',[A(1,'Dpp',[516,799,560,841])])
R('diffraction-approximation',1,[0,843,119,883],'似',[0,847,34,882],'似，可得','쓰면','gives:')
R('diffraction-tradeoff',1,[0,966,862,1006],'由',[0,971,34,1004],'由式(4)可知，D越小，D″越大，将使“像点”变得更为模糊。所以','식 [[four]]에서 [[D]]가 작을수록 [[Dpp]]는 커져 상의 점이 흐려진다.','By [[four]], smaller [[D]] gives larger [[Dpp]]: a blurrier point.',[A(1,'four',[66,970,115,1010]),A(1,'D',[200,970,231,1010]),A(1,'Dpp',[309,970,352,1012])])
R('optimum-hole',1,[0,1014,862,1054],'不',[0,1018,34,1053],'不能用太小的圆孔。最恰当的圆孔直径D的大小应使视网膜上','구멍이 너무 작아서는 안 된다. 최적 지름 [[D]]는 망막에서','So do not make the hole too small. The optimum diameter [[D]]',[A(1,'D',[539,1017,568,1058])])
R('equal-blur-diffraction',1,[0,1061,577,1102],'几',[0,1065,34,1101],'几何光学模糊光斑和衍射光斑一样大，即','기하광학적 흐림과 회절 무늬의 크기를 같게 한다. 즉','makes the geometric and diffraction spots equally large:')
r=R('pinhole-diagram-caption',1,[556,385,735,423],'图',[558,389,587,422],'图决解20-5-2','그림 [[number]]','Fig. [[number]]',[A(1,'number',[634,389,734,425])],size=8,left=247,right=303)
r['align']='center';v=p.rect(1,[556,385,735,423]);r['source_caption_horizontal_center']=(v[0]+v[2])/2
R('clearest-hole',2,[0,0,706,42],'此',[0,6,34,40],'此时“像”最为清晰。设此时小孔的直径为D0，则有','상이 가장 선명하다. 이때 구멍 지름을 [[D0]]라 하면','The image is clearest. For hole diameter [[D0]]:',[A(2,'D0',[583,6,621,45])])
R('substitute-wavelength',3,[0,52,682,107],'以',[0,66,42,106],'以λ=600×10−9m、a=0.20m代入得','[[lambda]], [[condition]]를 대입하면','Substitute [[lambda]] and [[condition]]:',[A(3,'lambda',[46,54,337,108]),A(3,'condition',[355,62,554,108])])
R('problem6',3,[76,174,139,219],'六',[78,181,120,217],'六、','6.','6.')
R('cosmic-ray-setup',3,[75,230,1039,277],'设',[116,236,157,275],'1.设带电宇宙射线粒子速度为v，在地磁场的洛伦兹力作','[[one]] 속력 [[v]]인 하전 우주선 입자가 지구 자기장의 로런츠 힘으로','[[one]] A charged cosmic-ray particle at speed [[v]], in Earth’s field,',[A(3,'one',[75,236,109,281]),A(3,'v',[601,236,624,281])],left=452,first_known_char_is_first_token=False)
R('cosmic-ray-motion',3,[0,287,529,333],'用',[0,292,42,331],'用下做圆周运动，其运动方程为','원운동을 한다. 운동 방정식은','moves circularly under the Lorentz force:')
R('relativistic-mass',3,[0,437,931,484],'式',[0,442,42,482],'式中m为运动粒子的相对论质量，与静止质量的关系为','[[m]]은 입자의 상대론적 질량이다. 정지 질량과의 관계는','Here [[m]] is relativistic mass, related to rest mass by:',[A(3,'m',[89,442,125,488])])
R('kinetic-energy',3,[0,602,244,649],'该',[0,607,42,647],'该粒子的动能','입자의 운동 에너지는','Its kinetic energy is:')
R('derive-speed',3,[0,717,269,764],'由',[0,722,42,762],'由式(1)可求得','식 [[one]]에서','From [[one]]:',[A(3,'one',[80,722,136,767])])
R('speed-data',3,[0,882,205,929],'代',[0,887,42,927],'代入数据得','수치를 대입하면','Using the data:')
R('energy-equations',3,[0,994,269,1041],'由',[0,999,42,1039],'由式(2)、(3)得','식 [[two]], [[three]]에서','From [[two]], [[three]]:',[A(3,'two',[80,999,136,1045]),A(3,'three',[155,999,210,1045])])
R('energy-data',3,[0,1153,452,1201],'代',[0,1158,42,1199],'代入数据，注意到式(5)，得','식 [[five]]와 수치를 대입하면','Using [[five]] and the data:',[A(3,'five',[329,1158,386,1205])])
R('energy-momentum-definitions',3,[75,1271,931,1317],'用',[116,1276,158,1315],'2.用p、E分别表示宇宙射线粒子的动量和能量，有','[[two]] 운동량과 에너지를 [[p]], [[E]]로 나타내면','[[two]] Let [[p]], [[E]] be the particle’s momentum and energy:',[A(3,'two',[75,1276,109,1321]),A(3,'p',[165,1275,190,1322]),A(3,'E',[210,1275,241,1322])],left=452,first_known_char_is_first_token=False)
protected=[]
for image,box in [(1,[102,185,428,262]),(1,[103,316,428,383]),(1,[448,190,810,380]),(1,[290,624,862,695]),(1,[290,890,862,963]),(1,[355,1106,862,1146]),(2,[331,47,848,121]),(3,[346,0,1039,48]),(3,[346,111,1039,168]),(3,[383,344,1039,433]),(3,[344,493,1039,600]),(3,[344,650,1039,715]),(3,[342,778,1039,884]),(3,[343,934,1039,989]),(3,[308,1047,1039,1149]),(3,[342,1207,1039,1264]),(3,[344,1325,1039,1433]),(3,[344,1438,1039,1536])]:protected.append(p.rect(image,box))
p.save(protected)
print('C03 TS9:',len(p.rows),'rows',sum(len(r['atoms'])for r in p.rows),'source expressions')

import sys
sys.path.insert(0,'C:/Users/andre/CodexWork/HaslaLab/translation-builds/izho2018-complete-solutions/engine')
from izho2018_ts_authoring import *
p=begin(9);point_labels(p);part(p,'24,20,0','2','도플러 효과와 광행차','4,6')
for at,text in{'10,0,2':' 임의의 관성 기준계에서 운동량은 다음과 같이 주어진다 ','16,0,0':'전체 에너지는 다음과 같다 ','23,0,0':'따라서 구하는 불변량은 다음과 같다 ','24,22,0':'광자의 운동량과 에너지 사이에는 다음 관계가 성립한다 ','26,0,0':'광자의 에너지는 다음 플랑크 식으로 주어진다 ','29,10,0':'각 좌표축 방향의 광자 운동량 성분은 ','38,0,0':'이는 잘 알려진 상대론적 도플러 효과의 공식이다. ','44,1,2':' 별의 천구상 위치는 지구의 공전과 광행차 때문에 일 년 동안 변한다. ','44,2,0':'그 개략적인 모습은 그림에 나타나 있다. 지구의 공전 속력은 빛의 속력보다 ','44,3,0':'훨씬 작으므로, ','47,0,0':'여기서 ','47,0,2':'는 속도 ','47,0,4':'와 별을 향하는 방향 사이의 각이다. '}.items():p.add(at,text)
around(p,'24,21,2',['광자의 정지 질량은 영이므로 식 ','에 따라 '],['(7)'])
around(p,'30,28,0',['이를 식 ','에 대입하면 '],['(B1.4)'])
around(p,'38,1,2',[' 식 ', ', ',' 및 ','로부터 '],['(2)','8)','(9)'])
around(p,'41,0,0',['식 ','를 이용하면 '],['(12)'])
around(p,'44,0,0',['식 ','는 고전적인 광행차 공식이다. '],['(14)'])
around(p,'44,4,0',['식 ','로부터 광행차각은 다음과 같다 '],['(14)'])
finish(p,[[24,20,0]],'Full original page9 read: four-vector invariance, photon momentum/energy, Doppler effect and aberration2.1–2.3 through definition of stellar angle. Original malformed references(B1.4) and2),8),(9) retained literally; all original MathType cos/sin/inv functions, hbar, fractional points, scripts and display labels2–15 remain native.')

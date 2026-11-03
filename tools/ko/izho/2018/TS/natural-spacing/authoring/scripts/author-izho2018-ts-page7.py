import sys
sys.path.insert(0,'C:/Users/andre/CodexWork/HaslaLab/translation-builds/izho2018-complete-solutions/engine')
from izho2018_ts_authoring import *
p=begin(7);point_labels(p)
for at,text in{'1,0,2':' 수증기는 주변 공기와 열역학적 평형을 이루므로, ','1,1,0':'모든 고도에서 온도가 같다. 수증기의 평형 조건은 ','1,14,0':'이상 기체 상태방정식으로부터 수증기의 밀도는 ','4,0,0':'문제의 조건에 따라 산기슭의 불포화 수증기압은 ','5,9,0':'한편 고도 ','5,9,2':'에서 포화 수증기압은 다음과 같이 표시한다 ','6,10,0':'다음 결과를 얻는다 ','13,0,0':'한편 주어진 참고 자료에 따라 ','30,11,0':'이로부터 구하는 공기의 습도는 다음과 같다 ','37,2,0':'평가 항목','37,3,0':'배점','45,0,0':'올바른 수치 ','54,0,0':'올바른 수치 ','59,3,0':'올바른 수치 ','59,5,2':'또는 이와 동등한 ','69,0,0':'올바른 수치 '}.items():p.add(at,text)
around(p,'1,2,0',['식 ','와 마찬가지로 다음과 같다 '],['(4)'])
around(p,'3,10,0',['여기서 고도에 따른 온도 변화는 식 ','로 주어진다. '],['(15)'])
around(p,'6,9,0',['식 ','을 식 ',' 및 ','와 초기 조건 ',' 및 ','를 이용해 적분하면 '],['(25)','(26)','(15)','(28)','(29)'])
around(p,'18,0,0',['이 식을 식 ','과 함께 풀면 고도 '],['(30)'])
around(p,'22,0,0',['다음으로 식 ','로부터 고도는 '],['(15)'])
around(p,'30,0,2',['산에 안개가 없으려면 식 ','에 다음을 대입해야 한다 '],['(33)'])
for at in['39,0,0','40,1,0','42,0,0','47,0,0','48,1,0','51,0,0','55,1,0','59,5,0','61,0,0','63,1,0']:formula(p,at)
finish(p,[[37,2,0],[37,3,0]],'Full original page7 read: water vapor/ambient-air equilibrium and humidity2.7–2.8; original reference(25) in integration sentence retained literally. Complete isothermal-grading rows1.1–1.4, all formulas/numerical values/alternative CP expression and original scores translated without changing native Word fractions or ln/exp programs.')

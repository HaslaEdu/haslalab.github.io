import sys
sys.path.insert(0,'C:/Users/andre/CodexWork/HaslaLab/translation-builds/izho2018-complete-solutions/engine')
from izho2018_ts_authoring import *
p=begin(5);point_labels(p)
for at in['2,0,0','3,0,0','3,6,0','4,0,0','11,10,0','12,0,0']:formula(p,at)
for at,text in{'1,0,0':'평가 항목','1,1,0':'배점','11,0,2':'을 무시한 경우 ','11,2,0':'수치 ','14,0,2':'을 무시한 경우 ','14,2,0':'수치 ','14,10,0':'합계','16,1,2':'지표면의 대기압은 대기에 작용하는 지구 중력으로 생기므로, ','16,2,0':'평형 조건에 따라 다음이 성립한다 ','16,16,0':'여기서 ','17,10,0':'는 지구의 표면적이다. ','22,0,2':'대기압은 기체에 작용하는 중력 때문에 고도에 따라 변한다. ','22,1,0':'두께가 ','22,1,2':'인 기체층의 평형을 생각하자. 이 높이 차에 따른 압력 차 ','22,2,1':'는 밀도가 ','22,3,0':'인 기체층의 중력을 상쇄해야 하므로 ','22,16,0':'한편 이상 기체 상태방정식에 따라 밀도와 압력의 관계는 ','22,17,0':'다음과 같다 ','25,0,2':'에서의 대기압은 ','25,1,0':'다음 기압 공식으로 주어진다 ','28,0,0':'고도가 ','28,0,2':'일 때의 압력은 ','28,12,2':'균일한 중력장에서 대기압은 그 위에 있는 공기의 질량으로 ','28,13,0':'결정된다. 따라서 가열은 등압 과정으로 볼 수 있으며, ','33,0,0':'여기서 이원자 분자 기체의 단열 지수는 '}.items():p.add(at,text)
around(p,'15,0,0',['문제 ',' 산의 물리학 (','점',''],['2.','10,0',')'])
part(p,'16,0,0','1','등온 대기','3,2')
around(p,'18,0,0',['식 ','과 ','로부터 '],['(1)','(2)'])
around(p,'25,0,0',['식 ','와 ','에 따라 고도 '],['(4)','(5)'])
finish(p,[[1,0,0],[1,1,0],[15,0,0],[16,0,0]],'Full original page5 read: complete opticsC grading table including two alpha-squared penalties, both numerical radii and total; mountain physics problem2, isothermal atmosphere1.1–1.3 including every bold point label. Original equations1–9 and all native air subscripts, units, numeric conventions and optical sm spellings preserved.')

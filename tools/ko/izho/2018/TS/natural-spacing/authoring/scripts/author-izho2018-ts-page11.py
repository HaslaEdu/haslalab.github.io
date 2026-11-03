import sys
sys.path.insert(0,'C:/Users/andre/CodexWork/HaslaLab/translation-builds/izho2018-complete-solutions/engine')
from izho2018_ts_authoring import *
p=begin(11);point_labels(p);part(p,'29,0,0','C','움직이는 매질 속의 빛','4,0')
for at,text in{'1,0,0':'따라서 별로부터 무한히 먼 거리에서 광자의 진동수는 ','7,0,0':'여기서 탈출 속력은 다음 고전적인 식으로 주어진다 ','20,0,0':'수치를 대입하면 ','29,1,2':'정의에 따라 물체 속도의 각 성분은 기준계 ','29,1,4':'에서 ','29,2,0':'다음과 같이 주어진다 ','34,0,0':'기준계 ','34,0,2':'에서 같은 성분은 다음과 같다 ','39,0,0':'로런츠 변환을 유한 차분 형태로 쓰면 ','56,1,0':'다음 결과를 얻는다 ','76,0,2':' 물과 함께 움직이는 기준계에서 생각하자. 식 ','76,1,2':'는 ','76,2,0':'다음과 같다 '}.items():p.add(at,text)
around(p,'11,0,0',['식 ','와 ','를 결합하면 '],['(19)','(25)'])
around(p,'56,0,0',['식 ','의 양변을 항별로 나눈 뒤 식 ','를 이용하면 '],['(33)-(35)','(29)-(32)'])
around(p,'76,1,0',['','에 따라 이 기준계에는 광행차가 나타나며, 수면에 입사하는 평면파의 입사각 '],['(14)'])
finish(p,[[29,0,0]],'Full original page11 read: gravitational redshift/escape speed through28, original Part C moving-medium light, velocity components29–32, Lorentz differentials33–35, velocity addition36–37 and full start of3.2. Source labels C and reference/frame primes remain literal; all original native fractional points and script/root geometry preserved.')

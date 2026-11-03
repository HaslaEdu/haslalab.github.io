import sys
sys.path.insert(0,'C:/Users/andre/CodexWork/HaslaLab/translation-builds/izho2018-complete-solutions/engine')
from izho2018_ts_authoring import *
p=begin(4);title(p,'1,0,0','С','3.0')
for at,text in{'1,1,0':'다각형의 한 변에 평행한 광선 ','1,1,2':'를 생각하자. 광선의 경로가 닫히려면, ','1,2,0':'렌즈에서 굴절한 광선이 다음 변에 평행하게 나아가야 한다. ','1,3,0':'따라서 광선은 다음 각도만큼 꺾여야 한다 ','3,1,0':'이 광선은 광축과 평행하므로 굴절한 뒤 초점 ','3,2,1':'를 지난다. 광축에서 다음 거리만큼 떨어진 광선은 ','4,15,0':'이 조건을 만족한다. 이 광선의 경로는 정다각형의 각 변을 이루며, ','4,16,2':'의 길이와 같다. 즉, ','11,0,0':'발산 렌즈도 같은 방법으로 풀 수 있지만, 광축 아래에서 ','11,1,0':'렌즈에 입사하는 광선을 생각해야 한다. ','12,2,0':'다음과 같다 ','13,21,0':'따라서 내접원의 반지름은 다음과 같다 '}.items():p.add(at,text)
around(p,'4,16,0',['','각형의 한 변의 길이는 선분 '],['17'])
around(p,'4,37,0',['이 정','각형에 내접하는 원의 반지름은 '],['17'])
around(p,'12,1,0',['이 경우 광선의 경로가 이루는 정','각형의 한 변의 길이는 '],['17'])
finish(p,[[1,0,0]],'Full original page4 read: converging and diverging-lens17-gon ray trajectories. Original optical diagrams and triangle retained, all6 source equation numbers and full original MathType fraction/tangent/root programs preserved. Source native sm and Cyrillic см unit spellings retained as native mathematical units, without silently correcting original conventions.')

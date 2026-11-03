import sys
sys.path.insert(0,'C:/Users/andre/CodexWork/HaslaLab/translation-builds/izho2018-complete-solutions/engine')
from izho2018_ts_authoring import *
p=begin(10);point_labels(p)
for at,text in{'1,1,0':'그림에서 각 ','1,1,2':'는 주기적으로 변한다. 최솟값 ','1,1,4':'는 점 ','1,2,1':'에서 나타나고, 값 ','1,2,3':'는 점 ','1,2,5':'에서, 최댓값 ','1,2,7':'는 점 ','1,2,9':'에서 나타난다. ','1,3,0':'마지막으로 값 ','1,3,2':'는 점 ','1,3,4':'에서 나타난다. 따라서 천구에서 별의 겉보기 위치는 ','1,4,0':'반장축의 각크기가 다음과 같은 타원을 따라 변한다 ','3,0,0':'및 ','5,0,0':'주어진 수치를 대입하면 ','10,3,0':'에서의 상대 진동수 변화는 ','17,0,0':'따라서 도플러 효과만으로는 별 스펙트럼의 적색편이를 완전히 설명할 수 없다. ','17,1,0':'빛이 별 표면을 벗어날 때 중력 적색편이로 광자의 진동수가 ','17,2,0':'낮아진다고 가정하는 것이 자연스럽다. ','17,4,0':'등가 원리에 따라 광자의 중력 질량은 ','22,0,0':'별에서 거리 ','22,0,2':'에 있는 광자에 작용하는 중력은 ','22,1,0':'뉴턴 법칙에 따라 다음과 같다 ','24,0,0':'광자의 운동에 대한 에너지 보존 법칙은 ','27,9,0':'따라서 ','30,0,2':'부터 ','30,0,4':'까지 적분하면 ','30,1,0':'다음 식을 얻는다 ','34,0,0':'여기서 ','34,0,3':'와 ','34,0,5':'는 각각 별 표면과 별로부터 무한히 먼 거리에서의 ','34,1,0':'광자 진동수이다. '}.items():p.add(at,text)
around(p,'10,0,2',[' 도플러 효과의 식 ','에 따라 '],['(12)'])
around(p,'30,0,0',['식 ','를 별의 반지름 '],['(B4.5)'])
finish(p,[],'Full original page10 read: annual aberration ellipse geometry through stellar declination, Doppler/gravitational redshift and integrated photon energy. Original(B4.5) reference and Russian connective до translated only as prose, native R/infinity and all mathematical programs retained. Diagram Star/Sun/Earth labels will receive separately measured, source-bound language overlays only, keeping original image bytes/CTM and nonlanguage ink exact.')

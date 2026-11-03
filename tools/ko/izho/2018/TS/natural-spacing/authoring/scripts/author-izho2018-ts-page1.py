import sys
sys.path.insert(0,'C:/Users/andre/CodexWork/HaslaLab/translation-builds/izho2018-complete-solutions/engine')
from izho2018_ts_authoring import *
p=begin(1)
for at,text in{'1,0,0':'이론시험 문제','2,0,0':'해설','2,1,0':'주의. 각 채점 항목은 부분 점수를 주지 않습니다!','4,1,2':'만큼 잠기면 시험관에 부력과 ','4,2,0':'중력이 작용한다. 따라서 뉴턴의 제2법칙에 따른 시험관의 ','4,3,0':'운동 방정식은 다음과 같다 ','5,17,0':'여기서 ','5,17,2':'은 시험관의 질량이고, ','5,17,4':'는 물의 밀도이다. ','5,18,0':'평형 위치에서는 다음 조건이 성립한다 ','6,12,0':'따라서 곧바로 다음 결과를 얻는다 ','10,0,0':'이는 주기가 다음과 같은 조화 진동의 방정식이다 ','12,0,2':'만큼 내리면 시험관의 위치 에너지는 ','12,1,0':'다음 양만큼 감소한다 ','13,13,0':'시험관을 깊이 ','13,13,2':'만큼 내리면 용기 안 수면이 올라간다. ','13,14,0':'높이 ','13,14,2':'는 물의 부피가 일정하다는 조건을 ','13,15,0':'만족한다 ','18,0,0':'따라서 시험관 아래에 있던 물은 용기의 원래 수면보다 ','18,1,0':'높이 올라간다. 이 물의 질량은 다음과 같다 ','19,14,0':'이 물의 질량 중심이 올라가는 높이는 ','28,0,0':'물의 위치 에너지 변화는 다음과 같다 ','35,1,0':'다음과 같이 얻는다: ','41,1,2':'로 내려가면 용기 벽과 시험관 사이의 물은 ','41,2,0':'다음 속력으로 올라간다 ','45,0,0':'올라가는 물의 질량은 다음과 같다 '}.items():p.add(at,text)
title(p,'3,0,0','1','10.0');title(p,'4,0,0','A','3.0')
around(p,'4,1,0',['',' 시험관이 깊이 '],['А1.'])
around(p,'12,0,0',['',' 시험관을 깊이 '],['А2.1'])
around(p,'35,0,0',['전체 위치 에너지의 변화는 식 ','를 이용하면 '],['(2)'])
around(p,'41,0,0',['',' 시험관이 속력 '],['А2.2'])
finish(p,[[1,0,0],[2,0,0],[2,1,0],[3,0,0],[4,0,0]],'Full original page1 read: floating test-tube buoyancy, A1, all A2.1/A2.2 prose through the final rising-water mass prompt. Preserve original three test-tube diagrams, all11 display labels and native MathType fractional points. Every variable/formula remains an original source program.')

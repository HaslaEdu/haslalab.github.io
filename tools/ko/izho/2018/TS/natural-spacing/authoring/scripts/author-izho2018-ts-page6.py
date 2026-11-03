import sys
sys.path.insert(0,'C:/Users/andre/CodexWork/HaslaLab/translation-builds/izho2018-complete-solutions/engine')
from izho2018_ts_authoring import *
p=begin(6);point_labels(p);part(p,'8,0,0','2','단열 대기','6,8')
for at,text in{'1,0,2':'시간 ','1,0,4':'동안 지구가 흡수하는 태양 에너지는 ','1,1,0':'다음과 같다 ','2,9,0':'따라서 구하는 시간 간격은 ','8,1,2':'대기의 온도는 고도에 따라 일정하게 유지되지 않으므로, ','10,10,0':'대기가 단열 상태라고 가정하면 다음과 같이 쓸 수 있다 ','17,1,0':'다음과 같이 감소함을 보여 준다 ','20,0,0':'고도 ','20,0,2':'에서의 온도는 ','20,13,2':'고도에 따른 압력 분포는 다음 단열 방정식으로 주어진다 ','25,0,0':'고도 ','25,0,2':'에서의 압력은 ','25,12,2':'대류권 상부의 온도는 일정하게 유지되므로, ','27,0,2':'주어진 온도와 압력 범위에서 포화 수증기압은 ','27,1,0':'다음 선형 함수로 근사할 수 있다 ','27,1,1':'','30,0,0':'포화 수증기압이 외부 대기압과 같아지면, 생겨나는 기포 안에서 ','30,1,0':'증발이 활발하게 일어날 수 있으므로 액체가 끓기 시작한다. ','30,15,2':'얼음의 녹는점은 외부 압력에 거의 영향을 받지 않으므로, ','30,30,0':'다음과 같다 ','33,0,2':'산기슭의 공기가 충분히 뜨거우면 산비탈 전체에서 온도가 ','33,2,0':'산의 높이는 다음과 같다 '}.items():p.add(at,text)
around(p,'8,2,0',['식 ','를 다음과 같이 다시 써야 한다 '],['(5)'])
around(p,'12,10,0',['식 ', '와 ', ' 및 ','을 함께 풀면 '],['(4)','(12)','(13)'])
around(p,'17,0,0',['식 ','는 단열 대기의 온도가 고도에 따라 '],['(14)'])
p.slots[next(i for i,s in enumerate(p.slots)if s['at']==[25,12,2])]['text']='대류권 상부의 온도는 일정하게 유지되므로, 식 '
around(p,'25,13,0',['','에 따라 대류권의 높이는 다음 조건으로 결정된다 '],['(15)'])
around(p,'30,2,0',['식 ','과 ','을 같게 놓으면 '],['(18)','(21)'])
around(p,'30,16,0',['온도가 ','에 이르면 눈이 나타난다. 즉, '],['0 ℃'])
around(p,'30,29,0',['따라서 식 ','로부터 적설이 나타나는 고도는 '],['(15)'])
around(p,'33,1,0',['섭씨 영 도까지 내려가지 못한다. 이때 식 ','에 따라 '],['(24)'])
p.add('25,25,0','따라서 낮과 밤의 대류권 높이 차이는 다음과 같다 ')
finish(p,[[8,0,0]],'Full original page6 read: solar heating interval1.4 and adiabatic atmosphere2.1–2.6, temperature/pressure/troposphere height, boiling, snow and mountain height. Every source point label and reference retained; original Word equations10–25, air/boil/melt/dn subscripts, source fractional points and source Kelvin/Celsius units remain native.')

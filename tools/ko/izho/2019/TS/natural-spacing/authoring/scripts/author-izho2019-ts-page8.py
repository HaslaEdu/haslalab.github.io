import sys
sys.path.insert(0,'C:/Users/andre/CodexWork/HaslaLab/translation-builds/izho2019-complete-solutions')
from izho2019_ts_authoring import begin,around,finish
p=begin(8)
for at,text in{
 '2,0,0':'분포 반전: 3준위계 ',
 '2,1,1':'이 계에는 아래쪽으로 향하는 유도 전이가 없다. 따라서 ',
 '4,0,0':'이때 분자는 다음 두 상태 중 하나에만 있다고 보았다: ',
 '4,2,1':'정상 상태에서는 ',
 '4,8,0':'들뜬 상태의 점유율은 다음과 같다 ',
 '14,0,0':'들뜬 상태와 바닥 상태의 점유율 차이는 ',
 '14,1,0':'다음 식으로 구한다 ',
 '19,0,1':'레이저 빛은 분포 반전이 일어났을 때, 즉 ',
 '19,4,0':'일 때 증폭된다. ',
 '20,16,0':'분포 반전: 4준위계 ',
 '24,1,0':'즉, ',
 '25,16,0':'공진기 ',
 '25,17,1':'공진기 안의 광자 수 변화량 ',
 '25,17,3':'은 광자가 반투명 거울을 통해 빠져나가면서만 생긴다. ',
 '25,18,0':'짧은 시간 ',
 '25,18,2':'동안 거울을 통해 공진기 밖으로 나가는 광자 수는 ',
 '25,19,0':'다음과 같다 ',
 '27,0,0':'여기서 ','27,0,2':'는 공진기의 단면적이다. ',
 '28,0,0':'레이저 빛의 세기 ','28,1,2':'는 공진기 안의 평균 광자 ',
 '29,0,0':'밀도 ','30,0,1':'와 전파 속도 ',
 '31,0,1':'를 이용하여 다음과 같이 쓸 수 있다 ',
 '34,0,0':'계수 ','34,0,2':'는 공진기 안에서 레이저 빛이 서로 반대인 두 방향으로 ',
 '34,1,0':'진행함을 반영한다. 공진기 안의 광자 수를 발생 광속의 세기로 ',
 '34,2,0':'나타내면 ',
}.items():p.add(at,text)
around(p,'2,2,0',['상태 ','의 점유율에 대한 수지 방정식은 다음과 같다: '],['2'])
around(p,'4,1,0',['들뜬 상태 ',' 또는 바닥 상태 ','. '],['2','0'])
around(p,'4,7,0',['이므로, 식 ','에 따라 '],['(4)'])
around(p,'19,5,0',['식 ','에 따라 이 조건은 다음과 같다 '],['(6)'])
around(p,'20,17,1',['4준위계에서 상태 ','의 점유율에 대한 수지 방정식은 '],['2'])
around(p,'20,18,0',['식 ','과 같고, 이 상태의 정상 점유율도 '],['(4)'])
around(p,'20,19,0',['식 ','로 주어진다. 이 계의 핵심 차이는 '],['(5)'])
around(p,'20,20,0',['상태 ','에서 중간 상태 ','으로 전이하며, 그 상태의 점유율이 '],['2','3'])
around(p,'20,21,0',['거의 ','이라는 점이다. 따라서 이 계의 점유율 차이는 '],['0'])
around(p,'24,0,0',['상태 ','와 ',' 사이의 분포 반전은 사실상 어떤 매개변수 값에서도 일어난다. '],['2','3'])
finish(p,[[2,0],[20,16],[25,16]],'Full original2019 sourcepage8 read at144dpi. Complete three-/four-level population inversion and resonator/photon-flow prose translated, including all original state2/0/3 numeral references preserved as source CIDs. Keep all three original12pt subsection centers and the two unchanged original transition diagrams with their source narrow text columns. Left-column source display4 has its genuine source counter beside the upper diagram; all display4–12 labels and MathType formulas retain original source positions/fonts/GIDs/fractional points/Y/paint. Inline dn2/dt=0,Delta n>0,dN,dt,S,IG,N/(Sl),c/r and source factor1/2 move as complete original mathematical objects including every original bar/script/clip/Form. Native pumping thresholds, optical rho symbol, original units and speed c/r convention remain literal. No new math typesetting/rasterization/figure replacement or font fitting.')

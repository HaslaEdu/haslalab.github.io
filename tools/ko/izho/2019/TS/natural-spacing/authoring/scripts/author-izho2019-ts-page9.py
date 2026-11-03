import sys
sys.path.insert(0,'C:/Users/andre/CodexWork/HaslaLab/translation-builds/izho2019-complete-solutions')
from izho2019_ts_authoring import begin,around,finish
p=begin(9)
for at,text in{
 '3,0,0':'이 식은 요구된 다음 형태로 쓸 수 있다 ',
 '6,0,0':'여기서 공진기 안의 광자 수명은 다음 식으로 정해진다 ',
 '11,0,1':'유도 방출은 일어나지만 거울을 통한 손실은 없는 경우, 광자 수의 변화를 구하자. ',
 '11,1,0':'유도 방출 단면적의 정의에 따라, 생성되는 광자 수는 ',
 '11,2,0':'다음 방정식으로 나타난다 ',
 '12,26,0':'여기서 ','12,26,2':'는 공진기 안에서 들뜬 상태에 있는 염료 분자의 수이며, ',
 '13,2,0':'는 공진기의 부피이다. ',
 '14,1,0':'구하고자 하는 방정식을 최종적으로 얻는다 ',
 '17,0,0':'여기서 공진기의 이득 계수는 ',
 '19,0,0':'정상 발진 상태 ',
 '19,1,1':'레이저 빛의 세기가 시간에 따라 변하는 양상을 나타내기 위해 ',
 '22,0,0':'들뜬 상태의 점유율은 다음 수지 방정식으로 주어진다 ',
 '25,0,0':'여기에는 펌프광의 흡수와 들뜬 상태에서 일어나는 ',
 '25,1,0':'자발 방출 및 유도 방출이 포함되어 있다. ',
 '25,3,0':'양수이어야 한다. 따라서 들뜬 상태 점유율의 문턱값은 ',
 '25,4,0':'다음과 같다 ',
 '30,0,1':'펌프광 세기의 문턱값을 구하기 위해, 레이저 빛이 없는 경우의 ',
 '30,5,0':'을 적용하면 ',
 '37,1,0':'광자 한 개의 에너지를 곱해야 한다 ',
 '40,0,0':'따라서 펌프광의 에너지 유속은 다음과 같다 ',
}.items():p.add(at,text)
around(p,'1,0,0',['이를 식 ','에 대입하면 '],['(10)'])
around(p,'14,0,0',['공진기 안의 광자 수를 나타내는 식 ','를 마지막 방정식에 대입하면 '],['(12)'])
around(p,'19,2,0',['식 ','와 ','을 연립해야 한다: '],['(14)','(17)'])
around(p,'25,2,1',['레이저 빛이 증폭되기 시작하려면 식 ','의 시간 미분계수가 '],['(19)'])
around(p,'30,1,0',['식 ','에 '],['(20)'])
around(p,'37,0,0',['펌프광의 에너지 유속을 구하려면 식 ','의 광자속에 '],['(22)'])
finish(p,[[19,0]],'Full original2019 sourcepage9 read at144dpi. Entire resonator/photon-lifetime/stimulated-emission/gain/stationary-generation/threshold/energy-flux prose translated, preserving all original equation references and enumerators3.9–3.12. Source MathType displayed equations13–23, every original numerical value/decimal comma/unit/photon-density convention, n_gamma V and V=Sl inline expressions and IG=0 remain exact native CID/Form/clip/point/Y/paint. Equation21 comparison glyph is retained exactly as rendered in the original, without mathematical correction. Native theta/gamma/rho/epsilon/tau and all script/rule programs remain source-original. Keep source12pt stationary-mode heading center, original body12pt physical rows and original source mathematical typo/reference conventions. No fitting, rasterization, formula retyping or source numerical edits.')

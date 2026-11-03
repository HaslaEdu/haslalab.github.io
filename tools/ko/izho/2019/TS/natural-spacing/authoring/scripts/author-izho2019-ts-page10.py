import sys
sys.path.insert(0,'C:/Users/andre/CodexWork/HaslaLab/translation-builds/izho2019-complete-solutions')
from izho2019_ts_authoring import begin,around,finish
p=begin(10)
for at,text in{
 '3,1,0':'그러면 다음과 같다 ',
 '15,0,0':'펌프광의 세기를 문턱값을 이용하여 다음과 같이 나타내고 ',
 '25,0,0':'공진기 밖으로 나오는 레이저 빛의 세기는 다음과 같다 ',
 '29,0,0':'여기서 상수 계수를 다음과 같이 정의하였다 ',
 '33,1,1':'한편, 단위 시간 동안 공진기 안에서 흡수되는 광자 수는 ',
 '33,2,0':'다음 식으로 구한다 ',
 '35,0,0':'다른 한편으로, 단위 시간 동안 공진기 밖으로 나오는 광자 수는 ',
 '36,18,0':'따라서 양자 수율은 다음과 같다 ',
 '44,0,0':'이 식에 포함된 매개변수를 모두 대입하면 최종 결과를 얻는다 ',
}.items():p.add(at,text)
around(p,'3,0,1',['정상 상태에서는 식 ','와 ','의 시간 미분항이 영이 된다. 식 ','에서 '],['(19)','(20)','(19)'])
around(p,'5,0,0',['식 ','에서는 '],['(20)'])
around(p,'18,0,0',['이를 식 ','에 대입하면 '],['(23)'])
around(p,'32,0,0',['관계식 ','의 그래프는 아래 그림과 같은 직선이다. '],['(29)'])
finish(p,[],'Full original2019 sourcepage10 read at144dpi. Translate complete stationary laser population/generation/output-intensity/quantum-yield derivation and enumerators3.13/3.14. Keep original MathType equations24–34 with every original fractional Tf/Tm/point/Y/paint, numerator/denominator/root/rule/overbar/script and native unit/cm/W/J conventions exact. Original prose reference to formula(23) remains the literal source number, without correcting the original reference. Original straight-line intensity graph, axes/grid/Greek eta/Cyrillic unit lettering remain the original source bitmap and geometry; no diagram editing or new rasterization. Preserve nbar, sigmaA/E, eta and source subscripttr/th differences exactly as printed. All source body12pt and original paragraph/figure positions retained, normal Korean word gaps, no fitting or math retyping.')

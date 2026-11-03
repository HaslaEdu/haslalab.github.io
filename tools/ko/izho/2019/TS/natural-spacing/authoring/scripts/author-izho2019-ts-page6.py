import sys
sys.path.insert(0,'C:/Users/andre/CodexWork/HaslaLab/translation-builds/izho2019-complete-solutions')
from izho2019_ts_authoring import begin,around,finish
p=begin(6)
for at,text in{
 '1,0,0':'고리의 전기장이 영이 되기 때문이다. 따라서 에너지 보존 법칙에서 곧바로 ',
 '1,1,0':'다음 결론을 얻는다 ',
 '2,12,0':'문항 ','2,13,0':'평가 항목 ','2,14,0':'배점 ',
}.items():p.add(at,text)
around(p,'2,10,0',['물론 식 ','을 영에서 무한대까지 적분해도 같은 답을 얻는다. '],['(40)'])
ats=['4,0,0','7,1,0','10,0,0','14,1,0','14,4,0','19,0,0','21,0,0','26,0,0','26,2,0','26,4,0','26,6,0','27,0,0','32,0,0','35,0,0','38,1,0','40,3,0','44,0,0','47,1,0','48,0,0','52,0,0','55,1,0','55,3,0','58,0,0','62,0,0','65,1,0','68,0,0','73,0,0','74,1,0','75,0,0','80,0,0','81,1,0']
for number,at in enumerate(ats,1):
 literal=f'({number})';around(p,at,['식 ',''if p.runs[at]['text'].endswith(literal)else' '],[literal])
for s in p.slots:
 if s['at']in[[2,12,0],[2,13,0],[2,14,0]]:s['align']='center'
finish(p,[],'Full original2019 sourcepage6 read at144dpi. Complete continuation work argument and all31 rubric Formula labels translated; source display47 remains at exact original position. The dense original grading table has genuine separate Part, Content, score and bold subtotal columns; preserve every grid and exact native score/decimal comma and source Part enumerator. Each table row is one source run-in native reference(n)+complete formula: retain entire original outer Word clip, every CambriaMath12/8.52/6.96pt CID, fraction/root rule and vector-arrow accent at exact font/GID/fractional Tf/Tm/point/paint/Y; pack row with Korean 식 without the old English Formula-width hole. Never bind two neighboring physical rows by a protruding script metric. Preserve all source original field/root/formula conventions and typography; no new math or image generation, fitting or threshold change.')

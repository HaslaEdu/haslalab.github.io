import sys
sys.path.insert(0,'C:/Users/andre/CodexWork/HaslaLab/translation-builds/izho2018-complete-solutions/engine')
from izho2018_ts_authoring import *
p=begin(3);formula(p,'1,0,0');p.add('2,0,0','합계');title(p,'2,5,0','В','4.0')
for at,text in{'3,0,0':'기호 ','3,1,0':'그림 참조), ','3,1,3':'는 다이오드가 닫힐 때까지 저항을 지나간 ','3,2,0':'전하량, ','3,2,2':'는 다이오드를 지나간 ','3,3,0':'전하량, ','3,3,2':'는 축전기의 전하량이다. ','4,0,0':'스위치를 닫은 직후 축전기의 전압은 영이고, ','4,1,0':'둘째 저항의 전압도 영이다. 따라서 ','5,5,0':'다이오드 전류가 영이 되는 순간, ','5,6,0':'첫째와 둘째 저항의 전류가 같으므로 ','5,7,0':'두 저항의 전압도 같다: ','5,8,0':'이때 축전기의 전하량은 다음과 같다: 다이오드 전류가 영이면, ','5,9,0':'첫째와 둘째 저항의 전류가 같고, 따라서 두 저항의 ','5,10,0':'전압도 같다: ','5,11,0':'전하량은 다음과 같다: ','6,11,0':'키르히호프 법칙에 따라: ','8,10,0':'이 연립방정식을 풀면 최종 답은 다음과 같다 ','12,8,0':'평가 항목','12,9,0':'배점','12,12,0':'수치 ','17,0,0':'수치 ','17,2,0':'합계'}.items():p.add(at,text)
around(p,'3,0,3',['는 저항 ','의 전류이고('],['k'])
around(p,'4,2,2',['','이므로 첫째 물음의 답은 '],[' = 0'])
around(p,'5,7,8',['',' 축전기의 전압도 같다. '],['/2.'])
around(p,'5,10,8',['',' 축전기에도 같은 전압이 걸리므로, 이때의 '],['/2.'])
around(p,'7,53,0',['마지막 식을 시간 ','부터 ','까지 적분하면: '],['0','τ'])
for at in['12,10,0','12,14,0','12,16,0','12,18,0','12,20,0','12,22,0','12,24,0','13,0,0']:formula(p,at)
finish(p,[[2,5,0],[12,8,0],[12,9,0]],'Full original page3 read, INCLUDING original Russian paragraph and its duplicated English continuation. Both language versions translated without omitting the original duplicate content or changing any mathematical U1/U2/U/2 source glyphs. All circuit diagrams, native equation/cell numbers, source fractional1/3 and179μCl remain exact; grading table15 on top and B1–8 plus numeric grades on bottom complete.')

from izho2012_authoring import begin,around,finish
p=begin(10)
def graded(at,no,score,text):around(p,at,['',' ','점',text],[no,'['+score+' ',']'])
graded('0,3,0','3.5','2',' 핵분열이 에너지상 유리하려면 핵들의 위치 에너지가 ')
for at,text in{
 '0,4,0':'감소해야 한다. 즉 ',
 '1,0,0':'이로부터 ',
 '10,0,0':'함수 ',
 '10,2,2':'의 그래프는 아래와 같다. ',
 '12,3,2':'는 ',
 '12,6,0':'에 대해 대칭이므로, 이 ',
 '13,0,0':'지점에서 최솟값을 갖는다. 이에 대응하는 값은 다음과 같다. ',
 '14,1,0':'타원체의 부피 공식과 다음 조건을 이용하면 ',
 '14,4,0':'다음을 얻는다. ',
 '16,0,0':'이로부터 ',
 '19,0,0':'이에 따른 표면 에너지의 증가량은 다음과 같다. ',
 '22,0,0':'양성자 사이의 쿨롱 상호작용 에너지는 다음만큼 감소한다. ',
 '27,0,0':'핵이 불안정해지는 조건은 다음과 같다. ',
}.items():p.add(at,text)
graded('12,1,0','3.6','0.5',' 함수 ')
graded('14,0,0','3.7','0.5',' 핵을 액체로 취급하므로 부피가 변하지 않는다. ')
graded('16,8,0','3.8','2',' 핵의 작은 변형에 테일러 전개를 적용하고, ')
around(p,'16,9,0',['식 ','을 고려하면 액체 표면적의 증가량은 다음과 같다. '],['(16)'])
finish(p,[],'Full original page10 viewed at144dpi. Preserve the exact original complete graph bitmap/curve/grid/labels/colored ink, all displayed equations12..20, source malformed epsilon/lambda approximation glyphs exactly as encoded, complete native inline f(k) and k=0.50 expressions, all original source subsection/grade/reference glyphs, gray backgrounds, native fractions/scripts and source points/baselines. No graph redrawing, missing bitmap labels, formula retyping or type-size fitting.')

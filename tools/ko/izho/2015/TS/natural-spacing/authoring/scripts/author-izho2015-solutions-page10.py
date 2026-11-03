from izho2015_authoring import begin,around,finish
p=begin(10)
for at,text in{
 '3,0,0':'또는 ',
 '14,0,0':'이는 역시 힘 (',
 '15,0,0':'채점 기준 ',
 '15,2,0':'평가 항목 ',
 '15,3,0':'배점 ',
 '15,6,0':'축 위의 자기장을 구함 ',
 '16,3,0':'정확한 ',
 '16,8,0':'다음 성분 사이의 관계: ',
 '16,8,3':'과 ',
 '17,1,0':'반지름 성분을 구함 ',
 '17,11,0':' (부호가 중요함) ',
 '18,0,0':'위 식에 음의 부호가 없을 때 ',
 '20,8,0':'(부호는 중요하지 않음) ',
 '21,17,0':' (부호가 중요함) ',
 '23,0,0':'옴의 법칙의 미분형 ',
 '24,0,0':'자기 모멘트 ',
 '26,0,0':'힘 ',
 '28,0,0':'위 식에 음의 부호가 없을 때 ',
 '30,3,0':'감쇠에 따른 각진동수 변화 ',
 '31,5,0':'올바른 답 ',
 '38,1,0':'원판의 에너지 손실을 구함 ',
 '38,4,0':'마찰력의 일률을 구함 ',
 '38,6,0':'두 값이 같음 ',
 '38,9,0':'쌍극자의 장을 구함 ',
}.items():p.add(at,text)
around(p,'10,0,0',['',' 줄의 법칙에 따라 원판에서 순간적으로 발생하는 열의 전력은 '],['2.2.9'])
around(p,'16,1,0',['조건 ',''],['z'])
around(p,'16,1,2',['','에서 단순화 '],['R'])
around(p,'16,5,0',['정확한 ',' '],['β'])
around(p,'28,1,0',['위 식의 계수가 ','이며 ','가 아닌 경우 '],['21/32','9/32'])
for slot in p.slots:
 if slot['at']in[[15,2,0],[15,3,0]]:slot['align']='center'
finish(p,[[15,0]],'Full original2015 page10 read at144dpi: completed damped electrostatic motion, Joule heating and first extensive grading page. Retain original page-number10/11 wrapped at left on the second header line, exact source typography/points of every Cambria/Times formula and table script, source definitions b/beta/tau and bv2 power, all scores including dot-versus-comma source punctuation. Protect literal z/R/b/beta/Br/Bz and21/32/9/32 while translating only prose around them. Preserve source table errors such as F label on the E formula and every source sign unchanged. No original mathematics or grid is regenerated.')

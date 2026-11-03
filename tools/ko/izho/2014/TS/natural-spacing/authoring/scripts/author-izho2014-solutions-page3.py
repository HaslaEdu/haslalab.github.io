from izho2014_authoring import begin,around,finish
p=begin(3)
for at,text in{
 '2,0,0':'채점 기준 ',
 '4,1,0':'평가 항목 ',
 '4,2,0':'배점 ',
 '6,1,0':'저항 ',
 '6,1,2':'의 전류 또는 ',
 '6,2,0':'축전기의 전하를 나타내는 올바른 식 ',
 '7,1,0':'저항을 흐르는 전류 제곱의 도함수를 올바르게 구함 ',
 '7,2,0':'저항 ',
 '7,2,2':'에 대해 구하거나, 올바른 시간 의존성 ',
 '7,4,0':'앞선 오류의 전파는 인정하지 않음 ',
 '9,1,0':'다음 열량에 대한 올바른 식 ',
 '10,0,0':'합계 ',
 '10,6,0':'앞선 오류의 전파는 인정하지 않음 ',
 '11,1,0':'평가 항목 ',
 '11,2,0':'배점 ',
 '11,4,0':'발상: 회로의 왼쪽 부분을 등가 전원으로 바꾸고 ',
 '11,5,0':'에너지 보존 법칙을 적용함 ',
 '12,1,0':'등가 전원의 매개변수 ',
 '12,8,0':'또는 ',
 '12,9,0':'다음 의존성 ',
 '12,9,4':')를 구함 ',
 '12,12,0':'(등가 회로에 대한 정당화는 필요하지 않음) ',
 '15,3,0':'등가 회로에서 발생한 전체 열량 ',
 '15,6,0':'올바른 답 ',
 '15,8,0':'합계 ',
 '16,1,0':'렌즈의 초점을 지나 입사한 광선은 굴절한 뒤 광축과 평행하게 진행한다. ',
 '16,2,0':'따라서 그림에 나타낸 모든 물체는 크기가 같은 상을 만든다. ',
 '16,3,0':'즉, 렌즈의 배율은 물체에서 초점까지의 거리에 ',
 '16,4,0':'반비례한다. ',
}.items():p.add(at,text)
around(p,'3,1,0',['',' 직접 풀이 '],['I.'])
around(p,'4,4,0',['답을 구할 수 있는 올바른 연립방정식 ',''],['– '])
around(p,'4,6,0',['방정식이 틀리거나 불완전하면 ',' '],['– 0.'])
around(p,'7,3,0',['계산 오류 시 배점 ','점(총 ','점) '],['– 1.0','2.0'])
around(p,'10,5,0',['',' 등가 전원을 이용한 풀이 '],['II.'])
around(p,'12,3,0',['',' 아래 내용 중 두 가지를 제시함: '],['2.1'])
around(p,'12,4,0',['',' 무부하 전압 ',' '],['1.','Ɛ/2'])
around(p,'12,6,0',['',' 단락 전류 ',''],['2.','Ɛ/'])
around(p,'12,7,0',['',' 내부 저항은 두 저항의 병렬 연결 '],['3.'])
around(p,'12,11,0',['',' 다음을 얻음: ',''],['2.2','Ɛ'])
around(p,'12,11,7',['','각각 ','점',' '],['/2 (','0.5',')'])
around(p,'16,0,0',['문제 ','점',' '],['1С (2 ',')'])
for slot in p.slots:
 if slot['at']in[[4,1,0],[4,2,0],[11,1,0],[11,2,0]]:slot['align']='center'
finish(p,[[2,0],[16,0]],'Full original2014 page3 read at144dpi, including both long grading tables and beginning of the lens solution. Preserve original leading Q formula, every source charge/current integral and native epsilon written as LatinƐ in the second table, all source scores/decimal points and original Roman table labels. Preserve source order and wording of the unusual1.0-of2.0 manipulation-error rubric literally. Both table grids, original Content/Points centers, bold/original point sizes and CyrillicС title remain source-native. Only explicit prose is translated.')

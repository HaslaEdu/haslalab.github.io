from izho2015_authoring import begin,around,finish
p=begin(8)
for at,text in{
 '1,3,0':'따라 계산하면 다음과 같다 ',
 '33,0,0':'거리가 충분히 큰 ',
 '33,2,2':'에서는 다음과 같이 단순해진다 ',
 '45,0,0':'따라서 ',
 '47,1,0':'도체 원판 안의 전기장은 영이어야 한다. 전기장 ',
 '49,0,0':'을 만드는 ',
 '49,1,0':'전하 ',
 '49,1,2':'는 원판 양면에 표면 전하 밀도 ',
 '49,4,0':'를 유도한다. 이 전하들이 만드는 ',
 '50,0,0':'전기장 ',
 '52,0,0':'은 점전하의 전기장과 크기가 같고 방향이 반대이다. 원판의 ',
 '52,1,0':'크기가 전하까지의 거리에 비해 작으므로, 원판 내부에서 ',
 '52,2,0':'전기장 ',
 '54,0,0':'의 변화를 무시할 수 있다. 따라서 전기장은 균일하고, ',
 '54,1,0':'유도 전하의 표면 밀도도 일정하다고 볼 수 있다. ',
 '55,0,0':'점전하의 전기장 세기는 다음 식으로 정해진다 ',
 '56,0,0':'유도 전하의 전기장 세기와 표면 전하 밀도의 관계는 ',
 '59,0,0':'두 식을 같게 놓으면 유도 전하의 표면 밀도는 ',
 '60,0,0':'원판의 각 면에 유도된 전하의 크기는 ',
 '60,12,0':', 여기서 ',
 '61,0,0':'는 원판의 넓이이다. 따라서 원판의 유도 쌍극자 모멘트는 ',
 '63,0,0':'그러므로 구에 작용하는 힘은 ',
 '68,0,0':'구가 움직이므로, 마지막 식의 ',
 '68,0,2':'를 ',
 '68,4,0':'로 바꿔야 한다. 조건 ',
 '68,8,0':'를 쓰면 힘의 식은 다음과 같이 단순해진다 ',
 '82,0,0':'이 경우 구의 운동 방정식은 다음과 같다 ',
}.items():p.add(at,text)
around(p,'1,0,0',['제','부: 전기 '],['2'])
around(p,'1,2,0',['',' 전기 쌍극자의 전기장을 중첩 원리에 '],['2.1.1'])
around(p,'47,0,0',['',' 원판이 구에 가하는 힘의 식을 유도하자. '],['2.2.1'])
finish(p,[[1,0]],'Full original2015 page8 read at144dpi: electric dipole field, conducting-disc polarization, induced moment and electrostatic force. Preserve exact original dipole diagram with q/E/vector-arrow labels; all native fractional Times MathType fonts/points, source complete inline E0/E-prime/sigma/q-prime/S=piR2 and x<<z expressions, all fraction/radical rules, dipole indices and source equation labels(19)-(24). The missing epsilon factors or original algebra are not corrected. Only prose is translated; explicit complete inline-expression policies are required before natural packing to keep every original fraction bar and CID cluster together.')

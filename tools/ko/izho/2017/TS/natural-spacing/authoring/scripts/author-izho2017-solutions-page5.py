from izho2017_authoring import begin,around,finish
p=begin(5)
for at,text in {
 '1,1,0':'다음과 같다 ',
 '5,2,0':'중심력이 작용하는 계의 각운동량 보존 법칙은 다음과 같다 ',
 '5,6,0':'따라서 ',
 '11,0,0':'마찬가지로 ',
 '11,0,2':'축 성분은 다음과 같다 ',
 '17,0,0':'이후 계산을 간단히 하기 위해 다음 무차원량을 도입하면 ',
 '20,0,0':'다음과 같다 ',
 '21,3,0':'이 방정식을 ',
 '21,3,2':'에 대해 풀면 ',
 '31,0,0':'또는 ',
 '39,1,0':'전체 편향각과 마찬가지로, 극좌표로 쓴 에너지 보존 법칙과 각운동량 보존 법칙을 ',
 '39,2,0':'결합한 방정식을 적분하여 구할 수 있다. 적분이 상당히 복잡하므로 ',
 '39,3,0':'그 식은 여기에서 제시하지 않는다. ',
 '39,4,2':'먼저 구름과 우주선 사이의 상호작용 퍼텐셜 에너지가 ',
 '39,5,0':'구름 중심에서 거리 ',
 '39,5,2':'에 따라 어떻게 변하는지 구하자. 구대칭 구름에서 ',
 '39,7,0':'우주선에 작용하는 전체 힘은 다음과 같다 ',
 '45,0,0':'이에 해당하는 퍼텐셜 에너지는 다음 형태이다 ',
 '48,3,0':'적분 상수 ',
 '48,3,2':'를 정하려면 퍼텐셜 에너지가 ',
 '48,4,0':'다음 경계 ',
 '48,4,2':'에서 연속이어야 함을 이용한다 ',
 '51,3,0':'따라서 최종적으로 다음 영역에서 ',
 '54,3,0':'구름 중심까지의 거리가 최소가 되는 순간에는 속도의 방사 성분이 ',
 '54,4,0':'영이 된다. 따라서 에너지 보존 법칙과 각운동량 보존 법칙에서 ',
}.items():p.add(at,text)
around(p,'1,0,0',['직교좌표계의 ','축 방향 우주선 운동량 변화는 '],['x'])
around(p,'20,7,0',['식 ','과 ','를 ','에 대입하면 '],['(23)','(24)','(17)'])
around(p,'39,0,0',['각도 ','는 우주선이 먼지 구름 속을 이동할 때 궤적의 '],['θ'])
around(p,'39,4,1',['','점',' '],['[2.0 ',']'])
# This single upright r is present in the original selected prose, not retypeset.
source=p.runs['39,6,0']['text'];pos=source.index('than r,')+5
p.prose_range('39,6,0',0,pos,'중심에서 거리 ');p.protect_range('39,6,0',pos,pos+1,'Original upright Times12pt r in source prose, physical CID retained.');p.prose_range('39,6,0',pos+1,len(source),'보다 먼 구각은 우주선에 힘을 작용하지 않으므로, ')
finish(p,[],'Full original2017 page5 read at144dpi. Preserve original12pt serif body and10.08pt italic explanatory note, including exact original Times theta and upright source r/x prose variables. All display expressions18–33 retain original Cambria Math glyphs, arbitrary fractional points, superscripts, roots, fraction bars, integrals and original counter positions. Same-cell prose/math natural gaps only; no font scaling or newly typeset math.')

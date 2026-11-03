"""Explicit human-read source2013 rope solution and complete first grading table."""
from pathlib import Path
import sys,json
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/izho2013-complete-solutions');sys.path.insert(0,'D:/CodexBuilds/Hasla-original-style-20261031/izho2012-complete-solutions/engine')
import source_slot_authoring as author
author.B=B;p=author.PagePlan(2013,1);p.fragments=[]
def around(at,parts,literals):
 text=p.runs[at]['text'];assert len(parts)==len(literals)+1;cursor=0
 for target,literal in zip(parts,literals):
  start=text.index(literal,cursor)
  if cursor<start:p.prose_range(at,cursor,start,target)
  else:assert not target
  p.protect_range(at,start,start+len(literal),'Exact original reference, mathematical symbol, equation/score numeral, header edition or source punctuation; retain encoded native font/GID/point/baseline.')
  cursor=start+len(literal)
 if cursor<len(text):p.prose_range(at,cursor,len(text),parts[-1])
 else:assert not parts[-1]
p.add('0,0,0','국제 자우티코프 올림피아드/이론시험 해설','International Zhautykov Olympiad/Theoretical Competition/Solutions')
p.add('0,0,0','쪽 ','Page ');p.protect_fragment('0,0,0','IX','Original Roman ninth-edition label in actual9.96pt Arial-Bold.')
for at,target in{
 '1,0,0':'이론시험 문제 ',
 '2,0,0':'해설 ',
 '4,1,0':'매달린 줄의 양 끝 길이를 ',
 '4,1,3':'과 ',
 '4,2,0':'라 하자. ',
 '4,3,0':'','4,4,0':'','4,5,0':'','4,6,0':'','4,7,0':'','4,8,0':'','4,9,0':'','4,10,0':'','4,11,0':'',
 '6,0,0':'및 ',
 '8,0,0':', 이로부터 ',
 '13,0,0':'동안 줄의 운동을 보자. 처음에 양쪽 ',
 '13,1,0':'끝의 높이 차는 ',
 '15,0,0':'이고, 그 사이 한쪽 끝이 움직인 ',
 '16,0,0':'작은 거리를 ',
 '18,0,0':'라 하자. 마찰이 없으므로 ',
 '18,1,0':'줄의 운동 에너지 증가는 위치 에너지 감소량과 같다. ',
 '18,2,0':'','18,3,0':'','18,4,0':'','18,5,0':'',
 '18,6,0':'줄이 길이 방향으로 움직이는 효과는 ',
 '18,7,0':'다음과 같이 작은 줄 조각을 아래로 내리는 것과 같다. ',
 '18,8,0':'질량 ',
 '20,0,0':'을 높이 ',
 '20,0,2':'만큼 내리면 된다: ',
 '25,0,0':'따라서 ',
 '28,1,0':'에너지 보존을 적용한다. 고려하는 짧은 시간 간격은 ',
 '31,0,0':'길이 ',
 '31,13,0':', 질량 ',
 '31,23,0':', 맨 위 장력 ',
 '31,23,2':'로 두자. ',
 '32,0,0':'또한 ',
 '34,0,0':'는 맨 위점과 줄의 가장 낮은 점 사이의 ',
 '35,0,0':'높이 차이다. 그러면 다음과 같다: ',
 '45,1,0':'장력이 최대인 점에서 작은 줄 조각을 택하면 ',
 '47,0,0':'이므로, ',
 '47,1,0':'다음 결과를 얻는다: ',
 '51,3,0':'평가 항목 ',
 '51,4,0':'배점 ',
 '51,6,0':'올바른 가속도 값 ',
 '51,9,0':'올바른 추론과 최종 답을 뒷받침하는 ',
 '51,10,0':'근거 제시 ',
 '53,1,0':'올바른 계산법으로 ',
 '53,1,3':'를 구함 ',
 '53,4,0':'정확한 값 ',
 '53,13,0':'합계 ',
}.items():p.add(at,target)
around('3,1,0',['문제 ','점',' '],['1 (10 ',')'])
around('4,0,0',['문제 ',' '],['1.A'])
around('4,12,6',['',' 그러면'],[').'])
for at,target in[('11,0,1','아주 짧은 시간 '),('43,0,1','작은 줄 조각에 뉴턴의 두 번째 법칙을 접선 방향으로 적용하면 ' )]:
 text=p.runs[at]['text'];assert text.startswith('. ');p.protect_range(at,0,2,'Original subsection period and separator at the original body point.');p.prose_range(at,2,len(text),target)
around('28,0,1',['',' 항목 ','과 같은 방법으로, 맨 위점부터 줄의 오른쪽 부분에 '],['. ','1'])
around('51,1,0',['채점 기준: 문제 ',' '],['1.A'])
around('53,7,0',['각 ','를 구하는 타당한 방법 '],['α'])
around('53,10,0',['각 ','의 최종 값 '],['α'])
around('53,15,0',['문제 ',' 도우미 증기 '],['1.В'])
for slot in p.slots:
 if slot['at']in[[51,3,0],[51,4,0]]:slot['align']='center'
selected={tuple(s['at'])for s in p.slots};fragments={tuple(s['at'])for s in p.fragments}
for at in p.runs:
 coords=tuple(map(int,at.split(',')))
 if coords not in selected and coords not in fragments:p.protect(at,'Human-read source page1: keep original rope variables, complete mathematical bitmaps/vector fractions, inline source scripts, actual T_top subscript text at8.04pt, Greek alpha, score/table enumerators, source decimal commas and all native punctuation/math glyphs. None is regenerated from Unicode mathematics.')
path=p.save();q=json.loads(path.read_text('utf8'));q['centered']=[[1,0],[2,0],[3,1],[4,0],[51,1],[53,15]];q['source_visual_review_note']='Complete original2013 page1 read at144dpi. Preserve9.96pt Arial-Bold header, original two-line15.96pt bold italic title,14.04/12pt original bold subsection/table headings, every original fuzzy blue/black math image exactly, source inline l1/l2/T_top/alpha glyphs, vector fractions, full grading grid and decimal-comma values. Widely spaced English word fragments are explicitly erased and the complete translated Korean clause is authored in the same physical source row; no type-size fitting or mathematics retyping. Source task1B CyrillicВ is retained unchanged. This is a private authored plan, not a delivery PDF.'
path.write_text(json.dumps(q,ensure_ascii=False,indent=2)+'\n','utf8');print('PRIVATE_IZHO2013_SOURCE_PAGE1_PROSE_PLAN',len(q['slots']),path,flush=True)

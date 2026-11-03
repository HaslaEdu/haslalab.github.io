"""Source image reviewed: original mechanics, gray fields, diagram and counters."""
from pathlib import Path
import sys,json,re
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/izho2012-complete-solutions')
sys.path.insert(0,'C:/Users/andre/.codex/tmp/Hasla-original-style-20261102/izho2011-complete-solutions/engine')
import source_slot_authoring as author
author.B=B;p=author.PagePlan(2012,1);p.fragments=[]
p.add('0,0,0',' 국제 자우티코프 올림피아드, 알마티, 카자흐스탄, ',' International Zhautykov Olympiad, Almaty, Kazakhstan, ')
p.protect_fragment('0,0,0','VIII','Original eighth-edition Roman numeral in its exact Cambria-Bold source font/point/baseline.')
p.protect_fragment('0,0,0','2012','Original source year; retain encoded glyphs and14.04pt face.')
p.add('1,0,0','이론시험 문제 해설 ',align='center')
p.add('2,0,0','문제 ','Problem ');p.add('2,0,0','점','points')
p.protect_fragment('2,0,0','1. (10 ','Original problem number, score and punctuation in original15.96pt CambriaMath.')
p.protect_fragment('2,0,0',')','Original closing score parenthesis.')
p.add('2,2,0','문제 ','Problem ');p.protect_fragment('2,2,0','1A. 2012','Original source subproblem label and year at14.04pt.')
for at,text in {
 '2,3,0':'계에 작용하는 힘은 ',
 '2,4,0':'그림과 같다. 강체인 ',
 '2,4,1':'막대와 ',
 '2,5,0':'늘어나지 않는 실로 추의 가속도 ',
 '2,6,1':'질량 없는 막대의 ',
 '2,7,0':'토크 합은 영이다. ',
 '2,8,0':'이 두 조건에 각 추의 ',
 '2,10,0':'적용하면 다음 ',
 '2,11,0':'연립식을 얻는다. ',
 '20,0,0':'이를 풀면 ',
 '24,0,0':'그러나 두 번째 추의 이 가속도는 중력 가속도보다 크다. ',
 '24,1,0':'따라서 ',
 '24,1,1':'두 번째 추의 실은 느슨해져 그 추는 자유 낙하하며, ',
 '24,3,0':'음의 장력이 나와 불가능하다. ',
 '24,3,1':'따라서 두 번째 추의 실은 ',
 '24,4,0':'막대에 힘을 못 준다. ',
 '24,5,0':'잘못 나타낸다. ',
 '24,5,1':'막대와 나머지 추들의 가속도를 구할 때에는 ',
 '24,6,0':'둘째 추는 뺀다. ',
 '25,0,0':'첫 번째와 세 번째 추의 실제 가속도는 다음 ',
 '25,1,0':'연립식으로 구한다. ',
 '43,0,0':'최종적으로 ',
}.items():p.add(at,text)
p.add('2,6,0','비는 ','are as ')
p.protect_fragment('2,6,0','1:2:3.','Original complete acceleration ratio and punctuation; never retype the mathematics.')
p.add('2,9,0','뉴턴 제','the equations of the ')
p.protect_fragment('2,9,0','2','Original second-law ordinal numeral, same CambriaMath program/size/baseline.')
p.add('2,9,0','법칙을 ','nd law of ')
p.add('24,2,0','가속도는 ','acceleration is equal to ')
p.protect_fragment('24,2,0','g.','Original native gravitational-acceleration variable and punctuation.')
for at,before,after in [('24,2,1','형식적으로 풀어도 식 ','은 '),('24,4,1','그러므로 식 ','은 실제 운동을 ')]:
 text=p.runs[at]['text'];start=text.index('(1)');end=start+3
 p.prose_range(at,0,start,before);p.protect_range(at,start,end,'Original complete equation-reference parentheses/numeral, exact source font/point/baseline.')
 p.prose_range(at,end,len(text),after)
selected={tuple(s['at'])for s in p.slots};fragments={tuple(s['at'])for s in p.fragments}
for at in p.runs:
 coords=tuple(map(int,at.split(',')))
 if coords not in selected and coords not in fragments:p.protect(at,'Reviewed full source page: original complete equations, scalar results, equation tags, page numeral, braces or physical diagram variables. Keep all encoded glyphs, fonts/points/baselines and vector/clip programs.')
path=p.save();q=json.loads(path.read_text('utf8'));q['centered']=[[1,0],[2,0]]
q['reviewed_math_font_prose_words']=[]
for slot in q['slots']:
 source=p.runs[','.join(map(str,slot['at']))]
 if re.fullmatch(r'Cambria.?Math',source['font']):
  assert not re.search(r'[0-9]',slot['source_text']),slot
  q['reviewed_math_font_prose_words'].append(dict(at=slot['at'],substring=slot['source_text'],source_substring=slot.get('substring'),range=slot.get('range'),translated_text=slot['text'],reviewed=True,reason='Human-read source2012 page1 narrative English in CambriaMath/OLE text fields. Only this exact authored prose selection is language; all source ratio digits, ordinal2, variableg, formula references, problem/grade/year digits and every adjoining mathematical glyph are explicitly protected.'))
q['source_gray_fields_and_original_diagram_unchanged_required']=True
q['source_visual_review_note']='Full original page1 viewed at144dpi. Keep the original gray OLE/math-field backgrounds, force diagram, source fraction/brace rules and all four equation counters. The formal solution gives negative second-thread tension, as confirmed directly by source equations; its impossibility explains removing the second hanging mass. No source font-size fitting or math retyping.'
path.write_text(json.dumps(q,ensure_ascii=False,indent=2)+'\n','utf8')
print('PRIVATE_IZHO2012_PAGE1_EXPLICIT_PROSE_PLAN',len(q['slots']),'MATH_FONT_PROSE_SELECTIONS',len(q['reviewed_math_font_prose_words']),path,flush=True)

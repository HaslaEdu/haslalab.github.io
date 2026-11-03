"""Explicit source2012 page2 prose; original diode math, grid and scores retained."""
from pathlib import Path
import sys,json,re,hashlib
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/izho2012-complete-solutions');sys.path.insert(0,str(B/'engine'))
import source_slot_authoring as author
author.B=B;p=author.PagePlan(2012,2);p.fragments=[]
p.add('0,0,0',' 국제 자우티코프 올림피아드, 알마티, 카자흐스탄, ',' International Zhautykov Olympiad, Almaty, Kazakhstan, ')
p.protect_fragment('0,0,0','VIII','Original Roman edition numeral, source Cambria-Bold face/point/baseline.')
p.protect_fragment('0,0,0','2012','Original source year, exact encoded glyphs.')
def prose_around(at,parts,literals):
 source=p.runs[at]['text'];assert len(parts)==len(literals)+1
 start=0
 for text,literal in zip(parts,literals):
  end=source.index(literal,start)
  if start<end:p.prose_range(at,start,end,text)
  else:assert not text
  p.protect_range(at,end,end+len(literal),'Reviewed complete original reference, digit or variable. Retain the actual source font/GID/point/baseline; no formula retyping.')
  start=end+len(literal)
 if start<len(source):p.prose_range(at,start,len(source),parts[-1])
 else:assert not parts[-1]
prose_around('1,0,0',['채점 기준: 문제 ',''],['1A.'])
for at,text in {
 '2,2,0':'배점 ',
 '2,4,0':'모든 힘을 표시한 그림 ',
 '3,1,0':'제외 근거: 둘째 추의 가속도가 중력 가속도보다 크거나 ',
 '3,2,0':'실의 장력이 음수임) ',
 '4,10,0':'합계 ',
 '7,0,0':'병렬 연결한 두 다이오드에 걸리는 전압을 ',
 '7,2,1':', 세 다이오드의 전압을 ',
 '8,0,0':'각각 ',
 '8,2,1':'라 하자. ',
 '8,3,1':'두 다이오드 중 하나를 흐르는 전류의 두 배: ',
 '9,11,1':'세 다이오드 중 하나를 흐르는 전류의 ',
 '9,12,0':'세 배: ',
 '11,0,0':'그래프 ',
 '11,5,0':'와 ',
 '11,10,0':'를 그린다. ',
 '11,10,1':'원래 그래프 ',
 '12,0,0':'즉 ',
 '12,4,0':'에 배수를 곱하면 된다. ',
 '12,4,1':'여러 ',
 '12,5,0':'전압에서 그래프의 ',
 '12,6,0':'대응하는 전류를 읽어 ',
 '12,8,0':'곱한 점을 그래프에 ',
 '12,9,0':'표시한다. ',
 '12,9,1':'직렬 연결에서는 전체 전압이 각 부분 전압의 합이므로 ',
 '12,10,0':'다음과 같다. ',
 '14,0,0':'이는 그래프에서 다음 두 곡선을 가로 방향으로 더하는 것이다: ',
 '15,0,0':'와 ',
 '15,5,0':'. 주어진 전류에서 전압 ',
 '15,7,1':'와 ',
 '15,9,1':'를 읽어, 그 합을 ',
 '15,10,0':'그래프의 전압 값으로 표시한다. ',
 '16,0,0':'역함수를 이용하면 이 문제의 형식적인 해를 다음과 같이 ',
 '16,1,0':'쓸 수 있다: ',
}.items():p.add(at,text)
prose_around('2,7,0',['연립방정식 ',' '],['(1)'])
prose_around('2,10,0',['식 ','의 해, 가속도 ',' '],['(1)','(2)'])
prose_around('2,13,0',['제외 ',': 둘째 추를 운동 방정식에서 제외 '],['4'])
prose_around('4,1,0',['둘째 추의 가속도는 ',' '],['g'])
prose_around('4,4,0',['연립방정식 ',' '],['(3)'])
prose_around('4,7,0',['식 ','의 해, 가속도 ',' '],['(3)','(4)'])
prose_around('6,0,0',['문제 ',' 그리고 다이오드 '],['1.B.'])
prose_around('8,2,2',['회로의 전체 전류 ','는 두 가지로 구한다: '],['I'])
prose_around('12,7,0',['각각 ','배, ','배를 '],['2','3'])
selected={tuple(s['at'])for s in p.slots};fragments={tuple(s['at'])for s in p.fragments}
for at in p.runs:
 coords=tuple(map(int,at.split(',')))
 if coords not in selected and coords not in fragments:p.protect(at,'Human-read source page2: exact source score values including decimal commas, numbered rows, circuit/curve symbols, complete displayed equations and references, punctuation, header page numeral and original gray-field/native-figure graphics.')
path=p.save();q=json.loads(path.read_text('utf8'));q['centered']=[[1,0]];q['reviewed_math_font_prose_words']=[]
for slot in q['slots']:
 source=p.runs[','.join(map(str,slot['at']))]
 if re.fullmatch(r'Cambria.?Math',source['font']):
  assert not re.search(r'[0-9]',slot['source_text']),slot
  q['reviewed_math_font_prose_words'].append(dict(at=slot['at'],substring=slot['source_text'],source_substring=slot.get('substring'),range=slot.get('range'),translated_text=slot['text'],reviewed=True,reason='Human-read complete source2012 page2: only this exact narrative language selection is translated. Every adjacent original reference, numeral, variable, equation, vector rule, diode diagram and score remains native.'))
q['source_gray_fields_and_original_diagram_unchanged_required']=True
q['source_visual_review_note']='Full original page2 source viewed at144dpi. Retain the complete original grading grid, actual decimal-comma score glyphs, true fill/stroke faux-bold headings/Total, diode circuit, all U/I subscripts, equation tags and complete native curve expressions. The source stray4 in Exception4 is explicitly retained. No type-size fitting.'
path.write_text(json.dumps(q,ensure_ascii=False,indent=2)+'\n','utf8')
print('PRIVATE_IZHO2012_PAGE2_EXPLICIT_PROSE_PLAN',len(q['slots']),'MATH_FONT_PROSE_SELECTIONS',len(q['reviewed_math_font_prose_words']),flush=True)

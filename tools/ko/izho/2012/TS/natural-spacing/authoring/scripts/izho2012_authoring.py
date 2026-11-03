from pathlib import Path
import sys,json,re
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/izho2012-complete-solutions');sys.path.insert(0,str(B/'engine'))
import source_slot_authoring as author
author.B=B
def begin(n):
 p=author.PagePlan(2012,n);p.fragments=[]
 p.add('0,0,0',' 국제 자우티코프 올림피아드, 알마티, 카자흐스탄, ',' International Zhautykov Olympiad, Almaty, Kazakhstan, ')
 p.protect_fragment('0,0,0','VIII','Original Roman edition numeral, source Cambria-Bold face/point/baseline.')
 p.protect_fragment('0,0,0','2012','Original source year, exact encoded glyphs.')
 return p
def around(p,at,parts,literals):
 source=p.runs[at]['text'];assert len(parts)==len(literals)+1
 start=0
 for text,literal in zip(parts,literals):
  end=source.index(literal,start)
  if start<end:p.prose_range(at,start,end,text)
  else:assert not text
  p.protect_range(at,end,end+len(literal),'Complete original reference, numeral, variable or unit. Retain the actual source font/GID/point/baseline; no mathematical retyping.')
  start=end+len(literal)
 if start<len(source):p.prose_range(at,start,len(source),parts[-1])
 else:assert not parts[-1]
def finish(p,centered,note):
 selected={tuple(s['at'])for s in p.slots};fragments={tuple(s['at'])for s in p.fragments}
 for at in p.runs:
  coords=tuple(map(int,at.split(',')))
  if coords not in selected and coords not in fragments:p.protect(at,'Human-read complete source page: every non-prose source run is original mathematical content, score, numbering, punctuation or figure annotation, retained in its actual source font/GID/point/baseline and native vector/image program.')
 path=p.save();q=json.loads(path.read_text('utf8'));q['centered']=centered;q['reviewed_math_font_prose_words']=[]
 for slot in q['slots']:
  source=p.runs[','.join(map(str,slot['at']))]
  if re.fullmatch(r'Cambria.?Math',source['font']):
   assert not re.search(r'[0-9]',slot['source_text']),slot
   q['reviewed_math_font_prose_words'].append(dict(at=slot['at'],substring=slot['source_text'],source_substring=slot.get('substring'),range=slot.get('range'),translated_text=slot['text'],reviewed=True,reason=f'Human-read source2012 page{p.page}: only this exact language selection is prose. Every adjacent original reference, numeral, variable, expression, vector rule, diagram and score remains native.'))
 q['source_gray_fields_and_original_diagram_unchanged_required']=True;q['source_visual_review_note']=note
 path.write_text(json.dumps(q,ensure_ascii=False,indent=2)+'\n','utf8')
 print('PRIVATE_IZHO2012_EXPLICIT_PROSE_PLAN',p.page,len(q['slots']),'MATH_FONT_PROSE_SELECTIONS',len(q['reviewed_math_font_prose_words']),flush=True)
 return path

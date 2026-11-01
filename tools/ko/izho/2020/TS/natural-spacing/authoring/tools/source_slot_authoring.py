"""Explicit reviewed source-run slots; no prose classifier decides publication."""
from pathlib import Path
import json,hashlib
B=Path(__file__).resolve().parents[1]
class PagePlan:
 def __init__(self,year,page):
  self.year=year;self.page=page;self.runs=json.loads((B/f'{year}/inspection/page{page:02}-runs.json').read_text('utf8'));self.slots=[];self.protected=[];self.evidence=[];self.fragments=[dict(at=[0,0,0],substring='XVI',source_text='XVI')]
 def add(self,at,text,substring=None,align=None):
  coords=list(map(int,at.split(',')));source=self.runs[at]['text'];selected=source if substring is None else substring
  if substring is not None:assert source.count(substring)==1,(at,substring,source)
  row=dict(at=coords,text=text,source_text=selected)
  if substring is not None:row['substring']=substring
  if align:row['align']=align
  self.slots.append(row)
 def protect(self,at,reason):
  assert at in self.runs;coords=list(map(int,at.split(',')));self.protected.append(coords);self.evidence.append(dict(at=coords,source_text=self.runs[at]['text'],reason=reason))
 def protect_fragment(self,at,text,reason):
  assert self.runs[at]['text'].count(text)==1;coords=list(map(int,at.split(',')));self.fragments.append(dict(at=coords,substring=text,source_text=text));self.evidence.append(dict(at=coords,source_text=text,reason=reason))
 def header(self):
  self.add('0,0,0',' 국제 자우티코프 올림피아드 / 이론시험 ',' International Zhautykov Olympiad/Theoretical Competition ');self.add('0,1,0','쪽 ','Page ')
 def save(self):
  source=B/f'{self.year}/source/IZhO_{self.year}_TS.pdf';q=dict(source=str(source),source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),source_language='English',page=self.page-1,slots=self.slots,staging_only_prose_baseline=True,journal_selected_prose_whitespace=True,native_prose_tokens=['XVI','sin','cos','max','min','log','exp','const'],native_text_exceptions=[],protected_runs=self.protected,protected_substrings=self.fragments,reviewed_formula_protection_evidence=self.evidence,policy='Explicit selected source prose only; original physical mathematics, counters, grades, source images and vector paths remain native. Staging is not a deliverable.')
  q['reviewed_math_font_prose_words']=[dict(at=s['at'],substring=s['source_text'],reviewed=True,reason='Literal English grading-table label in CambriaMath. Only the word Equation or Formula is narrative; every adjoining original numeral, punctuation, variable and mathematical glyph remains native.')for s in self.slots if self.runs[','.join(map(str,s['at']))]['font']=='CambriaMath'and s['source_text']in ['Equation','Formula']]
  dest=B/f'{self.year}/original_style/page{self.page}.json';dest.parent.mkdir(exist_ok=True);dest.write_text(json.dumps(q,ensure_ascii=False,indent=2)+'\n','utf8');return dest

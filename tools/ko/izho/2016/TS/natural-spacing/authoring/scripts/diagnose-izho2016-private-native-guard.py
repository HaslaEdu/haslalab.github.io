from pathlib import Path
import json,sys,traceback
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/izho2016-complete-solutions');sys.path[:0]=[str(B/'engine'),'D:/CodexBuilds/Hasla-publish-20261031/tools']
from izho_natural_spacing_rebuild import page_build
def clean(v):
 if isinstance(v,dict):return{k:clean(x)for k,x in v.items()if k in['c','font','size','origin','bbox','dx','rect','path','clips','own_clips','parent_clips','start','end','operator_indices','keys','glyphs','native_page_bbox','form_path']}
 if isinstance(v,(set,frozenset)):return list(v)
 if isinstance(v,(list,tuple)):return[clean(x)for x in v]
 try:json.dumps(v);return v
 except:return repr(v)
def trace(frame,event,arg):
 if event=='exception'and frame.f_code.co_name=='reposition_inline'and str(arg[1])in['Partial native Form selection would strand vector/image mathematics','Moved atomic clip group would leave an unchanged ancestor clip']:
  ls=frame.f_locals;row=dict(error=str(arg[1]),line=frame.f_lineno)
  for key in['ch','clip','visible','v','group','contained','remaining','atomic_clip_keys']:
   if key in ls:row[key]=clean(ls[key])
  print(json.dumps(row,ensure_ascii=False,default=str),flush=True)
 return trace
for n in map(int,sys.argv[1:]):
 log=B/f'natural/2016-page{n:02}-native-guard-diagnostic.jsonl'
 with log.open('w',encoding='utf8')as out:
  old=sys.stdout;sys.stdout=out;sys.settrace(trace)
  try:page_build(B/f'natural/2016/TS/plans/page{n:02}.json')
  except Exception as exc:print(type(exc).__name__,str(exc),flush=True)
  finally:sys.settrace(None);sys.stdout=old
 print('IZHO2016_SOURCE_NATIVE_GUARD_DIAGNOSTIC_READY',n,log,flush=True)

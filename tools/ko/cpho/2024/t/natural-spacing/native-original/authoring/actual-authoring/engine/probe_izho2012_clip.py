"""Read-only requested clip diagnosis; writes evidence only, never editions."""
from pathlib import Path
import sys,json,os,builtins,io

ENGINE=Path(r'D:/CodexBuilds/Hasla-original-style-20261031/izho-initial-theory/engine')
EVIDENCE=Path(r'D:/CodexBuilds/Hasla-original-style-20261031/izho-initial-theory/2012/source-clip-review')
PLAN=Path(r'D:/CodexBuilds/Hasla-original-style-20261031/izho-initial-theory/natural/2012/T/plans/page04.json')
sys.path.insert(0,str(ENGINE))
import izho_natural_spacing_rebuild as engine
import pdf_korean_natural_composer as composer
from pdf_original_text_ops import glyph_key
from pdf_memory_gate import page_worker

class Captured(Exception):pass
real_move=composer.reposition_inline
failures=[]

def trace(frame,event,arg):
    if event=='exception'and frame.f_code.co_name=='reposition_inline'and isinstance(arg[1],ValueError)and str(arg[1]).startswith('Native shift would leave an unchanged clip'):
        v=frame.f_locals;ch=v['ch'];k=glyph_key(ch);old=v['trace'];offsets=v['offsets']
        groups=[]
        for node in v['nodes']:
            for group in node['clip_groups']:
                if k not in group['keys']:continue
                gs=[g for g in old if glyph_key(g)in group['keys']and g['c'].strip()]
                groups.append(dict(path=node['path'],operator_indices=[group['start'],group['end']],
                    own_clips=group['own_clips'],parent_clips=group['parent_clips'],glyphs=gs,
                    unselected_visible_glyphs=[g for g in gs if glyph_key(g)not in offsets],
                    selected_offsets=[dict(c=g['c'],origin=g['origin'],dx=offsets.get(glyph_key(g)))for g in gs]))
        failures.append(dict(message=str(arg[1]),glyph=ch,dx=v['dx'],moved_bbox=list(v['moved']),unchanged_clip=v['clip'],complete_original_clip_candidates=groups))
    return trace

def capture(source,page_number,**kwargs):
    payload=dict(source=str(source),page_number=page_number,kwargs=kwargs)
    (EVIDENCE/'page04-native-move-request.json').write_text(json.dumps(payload,ensure_ascii=False,indent=1),'utf8')
    sys.settrace(trace)
    try:real_move(source,page_number,**kwargs)
    except ValueError as e:
        (EVIDENCE/'page04-clip-diagnosis.json').write_text(json.dumps(dict(error=str(e),failures=failures),ensure_ascii=False,indent=1),'utf8')
    finally:sys.settrace(None)
    raise Captured('Captured movement request and native clip diagnosis; no edition written')

def guarded(original):
    def open_readonly(file,mode='r',*args,**kwargs):
        if isinstance(file,(str,bytes,os.PathLike))and any(c in mode for c in'wax+'):
            path=Path(file).resolve()
            if not path.is_relative_to(EVIDENCE.resolve()):raise RuntimeError('Read-only probe blocked write: '+str(path))
        return original(file,mode,*args,**kwargs)
    return open_readonly

if __name__=='__main__':
    EVIDENCE.mkdir(parents=True,exist_ok=True);print('PID',os.getpid(),flush=True)
    composer.reposition_inline=capture
    with page_worker():
        builtins.open=guarded(builtins.open);io.open=guarded(io.open)
        try:engine._page_build(PLAN)
        except Captured as e:print(e,flush=True)

"""Read-only original right-hand display-equation marker audit / plan locks."""
from pathlib import Path
import sys,json,re,hashlib,argparse
import pymupdf as fitz
sys.path.insert(0,str(Path.cwd()/"tools"))
from pdf_native_inline_reposition import _traces
from pdf_original_text_ops import glyph_key
B=Path(__file__).resolve().parent

def references(plan):
    result=[]
    with fitz.open(plan['original_english_source'])as source,fitz.open(plan['source_base'])as base:
        page=source[plan['source_page']-1];old=_traces(base[plan['page']-1]);lookup={(glyph_key(g),g['trace_gid']):g for g in old if g['c'].strip()and g['trace_gid']>=0}
        native=_traces(page)
        for bi,block in enumerate(page.get_text('dict')['blocks']):
            if block['type']:continue
            for li,line in enumerate(block['lines']):
                text=''.join(s['text']for s in line['spans']).strip()
                if not re.fullmatch(r'\(\d+[a-z]?\)',text)or line['bbox'][0]<page.rect.width*.8:continue
                box=fitz.Rect(line['bbox'])+(-.01,-.01,.01,.01)
                glyphs=[g for g in native if g['c'].strip()and g['trace_gid']>=0 and g['render_mode']!=3 and box.contains(fitz.Point(g['origin']))]
                if ''.join(g['c']for g in glyphs)!=text:raise ValueError(('Original equation marker trace differs',text,glyphs))
                matched=[lookup.get((glyph_key(g),g['trace_gid']))for g in glyphs]
                if any(g is None for g in matched):raise ValueError(('An original equation marker was already changed in the input Korean edition',plan['page'],text))
                result.append(dict(label=text,source_at=[bi,li],rect=list(box),baseline=matched[0]['origin'][1],glyphs=matched))
    return result

def audit(plan,proof):
    refs=references(plan);changed=[]
    with fitz.open(proof)as doc:actual=_traces(doc[0])
    for tag in refs:
        for g in tag['glyphs']:
            same=[h for h in actual if h['c']==g['c']and h['font']==g['font']and h['trace_gid']==g['trace_gid']and abs(h['size']-g['size'])<1e-6 and max(abs(a-b)for a,b in zip(h['origin'],g['origin']))<=.001]
            if not same:changed.append(dict(label=tag['label'],source=g))
    return dict(original_display_equation_markers=len(refs),original_display_equation_marker_glyphs=sum(len(v['glyphs'])for v in refs),changed_marker_glyphs=changed,passed=not changed)

def apply(path):
    plan=json.loads(path.read_text('utf8'));refs=references(plan)
    plan['stationary_table_math']=[g for g in plan.get('stationary_table_math',[])if g.get('source_layout_role')!='display_equation_number']
    for tag in refs:
        plan['stationary_table_math'].append(dict(source_layout_role='display_equation_number',source_at=tag['source_at'],label=tag['label'],rect=tag['rect'],baseline=tag['baseline'],glyphs=len(tag['glyphs']),native_glyphs=[{k:g[k]for k in('c','font','size','origin')}for g in tag['glyphs']],policy='The original standalone right-hand display equation number remains at its exact source coordinates; translated units in the equation do not turn this marker into an inline prose token.'))
    plan['stationary_display_equation_number_labels']=[g['label']for g in refs]
    path.write_text(json.dumps(plan,ensure_ascii=False,indent=2),encoding='utf8')
    return len(refs)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--apply',nargs=2,metavar=('YEAR','KIND'));a=p.parse_args();report=[]
    for year in[2026,2025,2024,2023]:
        for kind in['T','TS']:
            for path in sorted((B/str(year)/kind/'plans').glob('page*.json')):
                plan=json.loads(path.read_text('utf8'))
                if a.apply and [str(year),kind]==a.apply:apply(path)
                proof=path.parents[1]/f"page{plan['page']:02}.pdf"
                if proof.exists():
                    row=dict(year=year,kind=kind,page=plan['page'],**audit(plan,proof));report.append(row)
                    if not row['passed']:print(json.dumps(row,ensure_ascii=False),flush=True)
    out=B/'modern-display-equation-number-position-audit.json';out.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
    print(json.dumps(dict(pages=len(report),markers=sum(r['original_display_equation_markers']for r in report),changed_pages=[(r['year'],r['kind'],r['page'])for r in report if not r['passed']])),flush=True)

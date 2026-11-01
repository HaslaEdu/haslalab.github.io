"""Independently compare native script/base relative geometry after line packing.

This is a read-only diagnostic, not an automatic mathematical parser. Supply
the physical source-native glyph list to exclude translated prose. Candidates
are smaller source glyphs immediately to the right of a larger glyph and on a
different baseline. Every candidate is reported; a nonzero relative dx fails.
Reviewed complete expressions can additionally be supplied as glyph groups.
"""
from pathlib import Path
from collections import defaultdict
import argparse, hashlib, json, re
import pymupdf as fitz
from pdf_native_inline_reposition import _traces
from pdf_original_text_ops import family_name


def _key(g):
    return (g['c'], family_name(g['font']), round(g['size'], 4),
            round(g['origin'][0], 3), round(g['origin'][1], 3))


def _id(g):
    return (g['c'], family_name(g['font']), round(g['size'], 3),
            g.get('trace_gid', g.get('gid')))


def audit(source, page_number, final, final_page=1, shifts=None, *,
          native_glyphs=None, expression_groups=None, excluded_script_origins=None,
          tolerance_pt=.001):
    """Return candidate pairs and complete-expression rigid-translation checks.

    ``shifts`` is the compositor's native_shifts list. ``native_glyphs`` uses
    c/font/size/origin and gid or trace_gid from this source page. Exclusions
    require {origin:[x,y], reason:...} and remain explicit in the report.
    Metadata matching also requires the original font, GID, point size and y.
    """
    shifts=shifts or []; expression_groups=expression_groups or []
    exclusions=excluded_script_origins or []
    if any(not x.get('reason') for x in exclusions):
        raise ValueError('Every script exclusion requires a reviewed reason')
    with fitz.open(source) as doc: old=_traces(doc[page_number-1])
    with fitz.open(final) as doc: new=_traces(doc[final_page-1])
    old=[g for g in old if g['c'].strip() and g['trace_gid']>=0]
    new=[g for g in new if g['c'].strip() and g['trace_gid']>=0]
    if native_glyphs is not None:
        wanted={_key(g) for g in native_glyphs if g['c'].strip() and g.get('trace_gid',g.get('gid',-1))>=0}
        old=[g for g in old if _key(g) in wanted]
        if {_key(g) for g in old}!=wanted:
            raise ValueError('Requested original physical native glyph is missing')
    offsets=defaultdict(list)
    for shift in shifts:
        for g in shift['glyphs']: offsets[_key(g)].append(float(shift['dx']))
    buckets=defaultdict(list)
    for g in new: buckets[_id(g)].append(g)
    matched={}; errors=[]
    for g in old:
        values=offsets.get(_key(g),[0.])
        if max(values)-min(values)>tolerance_pt:
            raise ValueError('One source glyph has conflicting displacement journals')
        dx=values[0];expected=[g['origin'][0]+dx,g['origin'][1]]
        candidates=buckets[_id(g)]
        if not candidates:
            errors.append(dict(source=g,reason='Original glyph signature not found'));continue
        actual=min(candidates,key=lambda h:abs(h['origin'][0]-expected[0])+abs(h['origin'][1]-expected[1]))
        err=max(abs(a-b) for a,b in zip(actual['origin'],expected))
        if err>tolerance_pt:
            errors.append(dict(source=g,expected=expected,actual=actual['origin'],position_error_pt=err));continue
        matched[_key(g)]=dict(glyph=g,dx=actual['origin'][0]-g['origin'][0],actual=actual['origin'])
    pairs=[]
    for script in old:
        x,y=script['origin']
        if any(max(abs(a-b)for a,b in zip([x,y],e['origin']))<.002 for e in exclusions):continue
        bases=[g for g in old if g['size']>=1.25*script['size']
            and -.15<=x-g['origin'][0]<1.1*g['size']
            and .5<abs(y-g['origin'][1])<.9*g['size']]
        if not bases:continue
        base=min(bases,key=lambda g:(max(0,x-g['origin'][0]),abs(y-g['origin'][1])))
        a=matched.get(_key(script));b=matched.get(_key(base))
        if not a or not b:continue
        delta=a['dx']-b['dx']
        pairs.append(dict(script={k:script[k]for k in('c','font','size','origin')},
            base={k:base[k]for k in('c','font','size','origin')},
            script_dx=a['dx'],base_dx=b['dx'],relative_x_change_pt=delta,
            relative_y_change_pt=(a['actual'][1]-b['actual'][1])-(y-base['origin'][1]),
            passed=abs(delta)<=tolerance_pt))
    groups=[]
    for group in expression_groups:
        glyphs=group.get('glyphs',group) if isinstance(group,dict) else group
        members=[matched.get(_key(g))for g in glyphs if g['c'].strip() and g.get('trace_gid',g.get('gid',-1))>=0]
        values=[m['dx']for m in members if m]
        complete=len(values)==len(members) and bool(values)
        spread=max(values)-min(values) if values else None
        groups.append(dict(label=group.get('label')if isinstance(group,dict)else None,
            physical_glyphs=len(members),matched_glyphs=len(values),
            relative_x_spread_pt=spread,passed=complete and spread<=tolerance_pt))
    failures=[p for p in pairs if not p['passed']]
    digest=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
    return dict(source=str(source),source_page=page_number,source_sha256=digest(source),
        final=str(final),final_page=final_page,final_sha256=digest(final),
        scope='Read-only native scripts and reviewed complete expressions; source font/GID/size/y exact within numeric serialization tolerance',
        tolerance_pt=tolerance_pt,source_physical_glyphs=len(old),matched_physical_glyphs=len(matched),
        glyph_signature_or_position_errors=errors,script_base_pairs=pairs,
        relative_geometry_failures=failures,reviewed_expression_groups=groups,
        reviewed_script_exclusions=exclusions,
        passed=not errors and not failures and all(g['passed']for g in groups))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('source');p.add_argument('page',type=int);p.add_argument('final')
    p.add_argument('--final-page',type=int,default=1);p.add_argument('--journal',required=True)
    p.add_argument('--native-glyphs');p.add_argument('--output',required=True)
    a=p.parse_args();j=json.loads(Path(a.journal).read_text('utf8'))
    native=json.loads(Path(a.native_glyphs).read_text('utf8'))if a.native_glyphs else None
    q=audit(a.source,a.page,a.final,a.final_page,j['native_shifts'],native_glyphs=native)
    Path(a.output).write_text(json.dumps(q,ensure_ascii=False,indent=2),'utf8')
    print(json.dumps(dict(passed=q['passed'],pairs=len(q['script_base_pairs']),failures=len(q['relative_geometry_failures']))))
    raise SystemExit(not q['passed'])

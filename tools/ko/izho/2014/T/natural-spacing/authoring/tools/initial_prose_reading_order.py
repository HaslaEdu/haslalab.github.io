"""Restore source-slot reading order for initial, non-deliverable native baselines.

Every new prose glyph is independently identified by an exact final-content
suffix journal. A whole authored source slot stays together despite temporary
staging overlap; no source math glyph is regrouped with translated prose.
"""
import hashlib
from izho_natural_spacing import records,token,visible

def journal(page,placements):
    expected=''.join(p['text']for p in placements)
    if not expected:return []
    raw=records(page)
    if len(raw)<len(expected):raise ValueError('Initial prose trace suffix is truncated')
    tail=raw[-len(expected):]
    if ''.join(g['c']for g in tail)!=expected:raise ValueError('Initial prose trace suffix differs from exact authored placement order')
    if any(g['gid']<0 or g['paint']!=0 for g in tail):raise ValueError('Unsupported initial prose cluster or painting style')
    result=[];offset=0
    for index,p in enumerate(placements):
        gs=tail[offset:offset+len(p['text'])];offset+=len(p['text'])
        if ''.join(g['c']for g in gs)!=p['text']:raise ValueError('Authored source-slot text differs from trace journal')
        if gs and any(abs(g['origin'][1]-p['point'][1])>.001 for g in gs):raise ValueError('Source-slot prose has an unreviewed mixed baseline')
        result.append(dict(index=index,placement=p,glyphs=gs,trace_keys={(g['trace'],g['index'])for g in gs}))
    return result

def rewrite(lines,page,rect,placements,journal_rows,baseline_tolerance_pt=.12):
    allkeys=set().union(*(j['trace_keys']for j in journal_rows))if journal_rows else set()
    rewritten=[]
    for line in lines:
        kept=[]
        for item in line['tokens']:
            remaining=[g for g in item['glyphs']if(g['trace'],g['index'])not in allkeys]
            if not visible(remaining):continue
            kept.append(dict(item)if len(remaining)==len(item['glyphs'])else token(remaining,'native'))
        rewritten.append(dict(line,tokens=kept))
    used=[]
    for j in journal_rows:
        p=j['placement'];x,y=p['point'];gs=visible(j['glyphs'])
        if not gs or not(rect[0]-.03<=x<=rect[2]+.03 and rect[1]<=y<=rect[3]):continue
        candidates=[line for line in rewritten if abs(line['baseline']-y)<=baseline_tolerance_pt]
        if len(candidates)>1:raise ValueError('One source prose slot matches multiple logical rows')
        if not candidates:
            line=dict(baseline=y,rect=list(rect),tokens=[]);rewritten.append(line)
        else:line=candidates[0]
        item=token(gs,'korean');item.update(text=p['text'],placement=j['index'],authored_source_slot=p.get('source_slot',p.get('at')),source_slot_reading_order=True)
        line['tokens'].append(item);used.append(dict(placement=j['index'],source_slot=item['authored_source_slot'],text_sha256=hashlib.sha256(p['text'].encode('utf8')).hexdigest(),glyphs=len(gs)))
    for line in rewritten:line['tokens'].sort(key=lambda t:t['x0'])
    return sorted((line for line in rewritten if line['tokens']),key=lambda l:l['baseline']),dict(rect=list(rect),authored_slots=used,exact_prose_trace_suffix_verified=True)

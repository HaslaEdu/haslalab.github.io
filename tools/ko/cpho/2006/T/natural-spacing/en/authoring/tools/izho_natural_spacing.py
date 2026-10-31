"""Pack existing Korean prose and native inline mathematics without new fonts.

The reviewed PDF is the input. Only horizontal displacement is requested from
the native text-show helper; character codes, source programs, point sizes,
baselines and mathematical spacing inside each expression remain intact.
Display equations and diagrams are excluded unless explicitly selected.
"""
from __future__ import annotations
import argparse, hashlib, json, math, re
from pathlib import Path
import pymupdf as fitz

ROOT=Path(__file__).resolve().parents[1]
BUILD=Path('D:/CodexBuilds/Hasla-original-style-20261031/izho-natural-spacing')
HANGUL=re.compile('[가-힣]')
JOSA=re.compile(r'^(?:(?:[은는이가을를의와과도에로면며인]|라|일|임을|임에|와의|과의)(?=\s|$|[,.!?;:，。；：)\]）])|(?:으로|이고|이며|이다|이면|이라|이므로|에서|에는|까지|부터|보다|처럼|만큼)|[,.!?;:，。；：)\]）])')

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def records(page):
    out=[];values=page.get_texttrace();ti=0
    while ti<len(values):
        trace=values[ti];mode=trace['type'];stroke=trace if mode==1 else None;ti+=1
        if mode==0 and ti<len(values):
            other=values[ti]
            if other['type']==1 and all(other[k]==trace[k]for k in('font','size','chars'))and other.get('seqno')==trace.get('seqno',-2)+1:
                mode=2;stroke=other;ti+=1
        for ci,(cp,gid,origin,bbox)in enumerate(trace['chars']):
            out.append(dict(c=chr(cp),gid=gid,font=trace['font'],size=trace['size'],
                            origin=list(origin),bbox=list(bbox),trace=ti,index=ci,
                            direction=list(trace['dir']),paint=mode,
                            color=trace.get('color'),opacity=trace.get('opacity',1),
                            linewidth=stroke.get('linewidth')if stroke else trace.get('linewidth'),
                            stroke_color=stroke.get('color')if stroke else None,
                            stroke_opacity=stroke.get('opacity',1)if stroke else None))
    return out

def visible(rows):return [r for r in rows if r['c'].strip()and r['gid']>=0]

def token(rows,kind):
    ink=visible(rows)
    if not ink:raise ValueError('Empty token')
    return dict(text=''.join(r['c']for r in rows),kind=kind,glyphs=rows,
                x0=min(r['origin'][0]for r in ink),x1=max(r['bbox'][2]for r in ink),
                y=min(ink,key=lambda r:-r['size'])['origin'][1],
                size=max(r['size']for r in ink),
                fonts=sorted({r['font']for r in ink}))

def native_chunks(rows,prose_tokens):
    """A single source trace may span erased prose or several columns."""
    chunks=[];current=[]
    for row in [r for r in rows if r['c'].strip()]:
        if row['gid']<0:
            painted=next((r for r in reversed(current)if r['gid']>=0),None)
            if painted is None or row['origin']!=painted['origin']or row['size']!=painted['size']:
                raise ValueError('Unmatched source Unicode continuation')
            current.append(row);continue
        split=False
        if current:
            prev=next(r for r in reversed(current)if r['gid']>=0);gap=row['origin'][0]-prev['bbox'][2]
            split=(abs(row['origin'][1]-prev['origin'][1])>.12*max(row['size'],prev['size'])
                   or gap>.65*max(row['size'],prev['size'])
                   or row['origin'][0]<prev['origin'][0]-.01
                   or any(prev['bbox'][2]<=p['x0']<row['origin'][0]and abs(p['y']-row['origin'][1])<.5*row['size']for p in prose_tokens))
        if split:chunks.append(current);current=[]
        current.append(row)
    if current:chunks.append(current)
    return chunks

def annotate_placements(tokens,placements):
    """Retain intentional joins inside each already authored prose placement.

    Legacy plans write a Korean word, native-font digits and a Korean suffix in
    separate text shows. Those are one prose token, e.g. ``2021년``/``10.0점``.
    Their original intra-placement geometry is kept exactly rather than adding
    a fresh word space at each font-resource boundary.
    """
    for item in tokens:
        candidates=[]
        for i,p in enumerate(placements or[]):
            point=p.get('point');width=p.get('advance',p.get('width'))
            if point is None or width is None:continue
            text=p.get('korean',p.get('text',''))
            if (abs(item['y']-point[1])<.02 and point[0]-.03<=item['x0'] and
                item['x1']<=point[0]+width+.15 and ''.join(item['text'].split())in ''.join(text.split())):candidates.append(i)
        if len(candidates)==1:item['placement']=candidates[0];item['kind']='korean'
    return tokens

def baseline_lines(page, bounds=None, *, allowed_line_rects=None, excluded_figure_rects=None,prose_placements=None,prose_trace_predicate=None,baseline_tolerance_pt=.12,stationary_native_glyphs=None):
    """Conservative final-PDF line inventory anchored by Korean text runs.

    Native spans are assigned only inside the requested paragraph rectangle.
    Superscript/subscript glyphs inherit their nearest Korean baseline. Pure
    mathematical lines are absent from this inventory and cannot move.
    """
    allowed=[fitz.Rect(r)for r in(allowed_line_rects or([bounds]if bounds else[]))]
    excluded=[fitz.Rect(r)for r in(excluded_figure_rects or[])]
    def eligible(rs):
        ink=visible(rs)
        if not ink:return False
        if allowed and not any(all(rect.contains(fitz.Point(r['origin']))for r in ink)for rect in allowed):return False
        return not any(rect.intersects(fitz.Rect(r['bbox']))for rect in excluded for r in ink)
    from pdf_original_text_ops import glyph_key
    stationary={glyph_key(g)for g in stationary_native_glyphs or[]}
    rows=[r for r in records(page)if glyph_key(r)not in stationary];traces={}
    for row in rows:traces.setdefault(row['trace'],[]).append(row)
    prose={ti:rs for ti,rs in traces.items()if(prose_trace_predicate(rs)if prose_trace_predicate else HANGUL.search(''.join(r['c']for r in rs)))}
    prose={ti:rs for ti,rs in prose.items()if eligible(rs)}
    anchors=sorted(visible(rs)[0]['origin'][1]for rs in prose.values());clusters=[]
    for y in anchors:
        if clusters and y-clusters[-1][0]<=baseline_tolerance_pt:clusters[-1].append(y)
        else:clusters.append([y])
    # Source text generators sometimes differ by 0.011pt within one visible
    # baseline. Cluster the line identity only; every glyph keeps its real y.
    ys=[sum(values)/len(values)for values in clusters]
    lines={y:[]for y in ys}
    for ti,rs in prose.items():
        y=min(ys,key=lambda y:abs(y-visible(rs)[0]['origin'][1]));lines[y].append(token(rs,'korean'))
    prose_tokens=[t for ts in lines.values()for t in ts]
    for ti,raw_rs in traces.items():
        if ti in prose:continue
        for rs in native_chunks(raw_rs,prose_tokens):
            ink=visible(rs)
            if not ink or not eligible(rs):continue
            mid=sum(r['origin'][1]for r in ink)/len(ink)
            if not ys:continue
            y=min(ys,key=lambda y:abs(y-mid))
            size=max([r['size']for t in lines[y]for r in t['glyphs']]or[12])
            # Small-font scripts must stay with the nearest body baseline.
            limit=.48*size if max(r['size']for r in ink)<.85*size else .12*size
            limit=max(limit,baseline_tolerance_pt)
            if abs(y-mid)>limit:continue
            lines[y].append(token(rs,'native'))
    result=[]
    for y,tokens in lines.items():
        tokens.sort(key=lambda t:t['x0']);annotate_placements(tokens,prose_placements);merged=[]
        for item in tokens:
            same_placement=bool(merged and 'placement'in item and item.get('placement')==merged[-1].get('placement'))
            native_neighbors=bool(merged and item['kind']=='native'and merged[-1]['kind']=='native'and 'placement'not in item and 'placement'not in merged[-1]and item['x0']-merged[-1]['x1']<=.65*max(item['size'],merged[-1]['size']))
            if same_placement or native_neighbors:
                prev=merged.pop();allrows=prev['glyphs']+item['glyphs']
                # Keep the native expression's absolute internal geometry.
                item=token(sorted(allrows,key=lambda r:(r['origin'][0],r['origin'][1])),'korean'if same_placement else'native')
                if same_placement:item['placement']=prev['placement']
            merged.append(item)
        for item in merged:
            if 'placement'in item:
                journal=(prose_placements or[])[item['placement']]
                authored=journal.get('korean',journal.get('text',''))
                if ''.join(authored.split())==''.join(item['text'].split()):item['text']=authored
        result.append(dict(baseline=y,tokens=merged))
    return result

def boundary_gap(left,right,word_space_pt=None):
    """A single ordinary word space, or direct Korean particle attachment."""
    size=min(left['size'],right['size'])
    tail=left['text'].rstrip();head=right['text'].lstrip()
    if not tail or not head:return 0
    old_gap=right['x0']-left['x1']
    if left['kind']=='native'and right['kind']=='native':return old_gap
    if tail.split()[-1]=='제'and re.match('[0-9０-９]',head):return 0
    if head[0]in ',.;:!?，。；：)]）'or tail[-1]in '([（-':return 0
    if left['kind']=='native'and right['kind']=='korean'and JOSA.match(head):return 0
    if left['kind']=='native'and re.search('[0-9]$',tail)and re.match(r'^(?:년|월|일|점|회|번|쪽|차)(?=\s|$|[,.!?;:)）])',head):return 0
    if left['kind']=='native'and re.search('[0-9]$',tail)and re.match(r'^(?:st|nd|rd|th)\b',head):return 0
    if left['kind']=='native'and re.match(r"^['’]s(?:\b|$)",head):return 0
    # The source math layout inside a native token has already been retained.
    return .25*size if word_space_pt is None else float(word_space_pt)

def inject_atomic_tokens(lines,atoms):
    """Replace ordinary fragments by complete source Form/clip expressions."""
    from pdf_original_text_ops import glyph_key
    claimed={glyph_key(r)for atom in atoms for r in atom['glyphs']}
    for line in lines:
        kept=[]
        for item in line['tokens']:
            remaining=[r for r in item['glyphs']if glyph_key(r)not in claimed]
            if visible(remaining):
                if len(remaining)==len(item['glyphs']):revised=dict(item)
                else:
                    revised=token(remaining,item['kind'])
                    if 'placement'in item:revised['placement']=item['placement']
                kept.append(revised)
        kept.extend(atom for atom in atoms if abs(atom['y']-line['baseline'])<.02)
        line['tokens']=sorted(kept,key=lambda t:t['x0'])
    return lines

def pack_line(line,center=None,word_space_pt=None):
    tokens=line['tokens'];cursor=tokens[0]['x0'];packed=[];gaps=[]
    for i,item in enumerate(tokens):
        if i:
            gap=boundary_gap(tokens[i-1],item,word_space_pt);cursor+=gap
            gaps.append(dict(left=tokens[i-1]['text'],right=item['text'],
                             old_gap=item['x0']-tokens[i-1]['x1'],new_gap=gap))
        dx=cursor-item['x0'];packed.append(dict(item,dx=dx,new_x0=cursor))
        cursor+=item['x1']-item['x0']
    if center is not None:
        adjustment=center-(packed[0]['new_x0']+cursor)/2
        for item in packed:item['dx']+=adjustment;item['new_x0']+=adjustment
        cursor+=adjustment
    shifts=[dict(glyphs=[{k:r[k]for k in('c','font','size','origin')}for r in item['glyphs']if r['c'].strip()],dx=item['dx'])for item in packed if abs(item['dx'])>1e-5]
    return dict(baseline=line['baseline'],tokens=packed,gaps=gaps,shifts=shifts,
                old_right=max(t['x1']for t in tokens),new_right=cursor,
                center=center)

def inspect(pdf,page,bounds=None):
    doc=fitz.open(pdf);result=[pack_line(line)for line in baseline_lines(doc[page-1],bounds)]
    doc.close();return result

def plan_page(page, *, allowed_line_rects, excluded_figure_rects=None, centered_lines=None,word_space_pt=None,prose_placements=None,prose_trace_predicate=None,baseline_tolerance_pt=.12,stationary_native_glyphs=None):
    """Build reviewed rectangular line plans for an existing translated page.

    ``centered_lines`` contains ``{baseline, center}`` entries. The center is
    the original source content/column center, never an assumed page center.
    Explicit rectangles are mandatory: callers must exclude display equations,
    table columns and illustrations. No unsupported vector line is moved.
    """
    if not allowed_line_rects:raise ValueError('Reviewed line/paragraph rectangles are required')
    centers=centered_lines or[];out=[];claimed=set()
    # Each explicit rectangle is a separate column/paragraph. Never merge two
    # intentional columns merely because their baselines are equal.
    for rect in allowed_line_rects:
        lines=baseline_lines(page,allowed_line_rects=[rect],excluded_figure_rects=excluded_figure_rects,prose_placements=prose_placements,prose_trace_predicate=prose_trace_predicate,baseline_tolerance_pt=baseline_tolerance_pt,stationary_native_glyphs=stationary_native_glyphs)
        for line in lines:
            keys={(r['c'],r['font'],r['size'],tuple(r['origin']))for t in line['tokens']for r in visible(t['glyphs'])}
            if claimed&keys:raise ValueError('Overlapping reviewed line rectangles select a glyph twice')
            claimed.update(keys)
            matches=[r['center']for r in centers if abs(r['baseline']-line['baseline'])<.02 and ('rect'not in r or list(r['rect'])==list(rect))]
            if len(matches)>1:raise ValueError('Ambiguous centered line')
            packed=pack_line(line,matches[0]if matches else None,word_space_pt)
            if packed['new_right']>rect[2]+.1 or min(t['new_x0']for t in packed['tokens'])<rect[0]-.1:
                raise ValueError(('Packed line exceeds reviewed content rectangle',line['baseline'],packed['new_right'],rect))
            out.append(packed)
    return dict(lines=out,shifts=[s for line in out for s in line['shifts']],
                excluded_figure_rects=excluded_figure_rects or[],allowed_line_rects=allowed_line_rects)

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('pdf',type=Path);p.add_argument('--page',type=int,default=1)
    p.add_argument('--bounds',type=float,nargs=4);p.add_argument('--out',type=Path);p.add_argument('--apply',action='store_true');a=p.parse_args()
    result=inspect(a.pdf,a.page,a.bounds);report=dict(input=str(a.pdf),input_sha256=sha(a.pdf),page=a.page,bounds=a.bounds,
        unchanged_font_programs_and_sizes=True,display_equations_excluded=True,lines=result)
    target=a.out or BUILD/'prototype.pdf';target.parent.mkdir(parents=True,exist_ok=True)
    if a.apply:
        if not a.bounds:raise ValueError('--apply requires a reviewed paragraph --bounds')
        from pdf_native_inline_reposition import reposition_inline
        raw,qa=reposition_inline(a.pdf,a.page,shifts=[s for line in result for s in line['shifts']])
        target.write_bytes(raw);report['output_sha256']=sha(target);report['shift_qa']=qa
        doc=fitz.open(target);doc[0].get_pixmap(matrix=fitz.Matrix(1.5,1.5)).save(target.with_suffix('.png'));doc.close()
    target.with_suffix('.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
    print(json.dumps(dict(lines=len(result),shifted_groups=sum(len(r['shifts'])for r in result),
        largest_gaps=sorted([g for r in result for g in r['gaps']],key=lambda g:-g['old_gap'])[:12]),ensure_ascii=False,indent=2))

if __name__=='__main__':main()

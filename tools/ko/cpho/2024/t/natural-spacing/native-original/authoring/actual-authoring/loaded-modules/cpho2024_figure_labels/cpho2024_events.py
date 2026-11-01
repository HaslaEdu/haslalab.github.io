"""Read-only source inventory for the actual five-page Chinese 2024 paper.

Original encoded native glyphs and vector paths are the only math inputs.
Language replacements are recorded separately; none of these native objects
is converted into text, images or a newly drawn mathematical expression.
"""
from pathlib import Path
from collections import defaultdict
import json, math,hashlib

BASE=Path(__file__).resolve().parents[1]
PLAN=json.loads((BASE/'authoring/T/slots.json').read_text('utf8'))
SOURCE_SHA='894111e1298dc785e9447252219e1f72fe0bb3fdf35b7573affec64f844ff6f6'
if hashlib.sha256((BASE/'source/CPhO_2024_Chinese_original.pdf').read_bytes()).hexdigest()!=SOURCE_SHA:
    raise ValueError('Actual Chinese original source SHA changed')

def key(g):return(g['c'],g['font'],round(g['size'],3),*map(lambda x:round(x,3),g['origin']))
def bounds(gs):
    return[min(g['bbox'][0]for g in gs),min(g['bbox'][1]for g in gs),max(g['bbox'][2]for g in gs),max(g['bbox'][3]for g in gs)]
def overlap(a,b):return min(a[2],b[2])-max(a[0],b[0])
def distance(a,b):return max(a[0]-b[2],b[0]-a[2],0)

def events(number):
    p=next(p for p in PLAN['pages']if p['source_page']==number)
    allg=json.loads((BASE/f'inspection/page{number:02}-source-glyphs.json').read_text('utf8'))
    objects=json.loads((BASE/f'inspection/page{number:02}-objects.json').read_text('utf8'))
    erase={key(g)for s in p['slots']if not s.get('retain_native')for g in s['source_characters']if not g['c'].isspace()}
    native=[g for g in allg if not g['c'].isspace()and key(g)not in erase]
    # Native Chinese physical subscripts remain native, not prose.
    parents=list(range(len(native)))
    def find(i):
        while parents[i]!=i:parents[i]=parents[parents[i]];i=parents[i]
        return i
    def join(i,j):parents[find(i)]=find(j)
    prose=[s['source_rect']for s in p['slots']if not s.get('retain_native')]
    def barrier(a,b):
        lo,hi=sorted((a['origin'][0],b['origin'][0]));y=(a['origin'][1]+b['origin'][1])/2
        return any(r[0]>lo+.1 and r[2]<hi-.1 and r[1]<y<r[3]for r in prose)
    for i,a in enumerate(native):
        for j in range(i):
            b=native[j];dy=abs(a['origin'][1]-b['origin'][1]);dx=distance(a['bbox'],b['bbox'])
            common=dy<.7 and dx<5.5
            script=dy<max(a['size'],b['size'])*.8 and dx<2.3 and min(a['size'],b['size'])<max(a['size'],b['size'])*.84
            if(common or script)and not barrier(a,b):join(i,j)
    path_owners={}
    for v in objects['vector_paths']:
        r=v['rect'];near=[]
        # Pure equation strokes: fraction bars, large delimiters and radicals.
        for i,g in enumerate(native):
            b=g['bbox'];dx=max(r[0]-b[2],b[0]-r[2],0)
            dy=max(r[1]-b[3],b[1]-r[3],0)
            if dx<1.5 and dy<8:near.append(i)
        if near:
            for i in near[1:]:join(near[0],i)
            path_owners[tuple(v['operator_indices'])]=near[0]
    comps=defaultdict(list)
    for i,g in enumerate(native):comps[find(i)].append(g)
    parts=[]
    for k,gs in comps.items():
        r=bounds(gs);paths=[v for v in objects['vector_paths']if tuple(v['operator_indices'])in path_owners and find(path_owners[tuple(v['operator_indices'])])==k]
        for v in paths:
            q=v['rect'];r=[min(r[0],q[0]),min(r[1],q[1]),max(r[2],q[2]),max(r[3],q[3])]
        # Main-size native baselines are a strong anchor; the complete 2D
        # expression stays together and is reviewed in the event inventory.
        ys=[g['origin'][1]for g in gs if g['size']>=max(g['size']for g in gs)*.85]
        y=sum(ys)/len(ys)
        rows=sorted(p['rows'],key=lambda q:abs(q['baseline']-y))
        row=rows[0]if abs(rows[0]['baseline']-y)<12 else None
        text=''.join(g['c']for g in sorted(gs,key=lambda g:(round(g['origin'][1]/3)*3,g['origin'][0])))
        parts.append(dict(glyphs=gs,rect=r,baseline=y,row=row['row']if row else None,source=text,vector_paths=paths))
    parts.sort(key=lambda a:(a['row']if a['row']is not None else 1000,a['rect'][0],a['rect'][1]))
    for i,q in enumerate(parts):q['id']=f'm{i}'
    language_punctuation=[]
    if number==1:
        # In "displacement x_i, x_i's positive direction", the comma is
        # sentence punctuation rather than part of either physical variable.
        # Keep each x_i as an intact native cluster and translate the comma.
        original=next(q for q in parts if q['id']=='m87')
        comma=[g for g in original['glyphs']if g['c']=='，']
        if len(comma)!=1:raise ValueError('Reviewed repeated-displacement punctuation changed')
        cut=comma[0]['origin'][0]
        first=[g for g in original['glyphs']if g['origin'][0]<cut]
        second=[g for g in original['glyphs']if g['origin'][0]>cut]
        if len(first)!=2 or len(second)!=2:raise ValueError('Reviewed x_i clusters changed')
        original.update(glyphs=first,rect=bounds(first),source=''.join(g['c']for g in first))
        parts.append(dict(original,id='m106',glyphs=second,rect=bounds(second),source=''.join(g['c']for g in second)))
        language_punctuation=comma
    if number==2:
        # The matrix below the prose is a display equation; (a)/(b) belong
        # to the adjacent original figure, not to the prose on that baseline.
        for q in parts:
            if q['id']in{'m68','m69','m70','m71','m72','m73','m74','m75','m76'}:q['row']=None;q['role']='stationary display/figure'
        # The caption's -45-degree fast-axis direction is a glyph-free
        # original bitmap inside a large white padded image. This is the
        # reviewed visible ink frame, not the padded image's logical width.
        image=next(q for q in objects['images']if q['path']==[3492])
        parts.append(dict(id='m125',glyphs=[],image_path=image['path'],
            rect=[386.64,699.60,407.04,708.96],physical_image_bbox=image['bbox'],
            baseline=707.6437377929688,row=36,source='−45° (original bitmap)',vector_paths=[],
            reviewed=True,reason='Original caption (b) fast-axis angle; complete image+own clip moves together.'))
        matrix=next(q for q in parts if q['id']=='m97')
        period=[g for g in matrix['glyphs']if g['c']=='.']
        if len(period)!=1:raise ValueError('Reviewed matrix sentence period changed')
        matrix['glyphs']=[g for g in matrix['glyphs']if g not in period]
        matrix.update(rect=bounds(matrix['glyphs']),source=''.join(g['c']for g in matrix['glyphs']))
        parts.append(dict(id='m126',glyphs=period,rect=bounds(period),baseline=period[0]['origin'][1],
            row=39,source='.',vector_paths=[],role='original sentence punctuation'))
    if number==4:
        for label,newid in [('m5','m91'),('m26','m92'),('m27','m93'),('m56','m94')]:
            q=next(q for q in parts if q['id']==label)
            punct=[g for g in q['glyphs']if g['c']in'.。．']
            if len(punct)!=1:raise ValueError('Reviewed source sentence punctuation changed: '+label)
            q['glyphs']=[g for g in q['glyphs']if g not in punct]
            q.update(rect=bounds(q['glyphs']),source=''.join(g['c']for g in q['glyphs']))
            parts.append(dict(id=newid,glyphs=punct,rect=bounds(punct),baseline=punct[0]['origin'][1],
                row=q['row'],source=punct[0]['c'],vector_paths=[],role='original sentence punctuation'))
    if number==5:
        q=next(q for q in parts if q['id']=='m13')
        a=[g for g in q['glyphs']if g['c']=='𝑎']
        if len(a)!=1:raise ValueError('Reviewed plate-spacing scalar changed')
        rest=[g for g in q['glyphs']if g not in a]
        q.update(glyphs=a,rect=bounds(a),source='𝑎')
        parts.append(dict(id='m71',glyphs=rest,rect=bounds(rest),baseline=rest[0]['origin'][1],row=9,
            source=''.join(g['c']for g in rest),vector_paths=[],role='plate-pair reference and native comma'))
    if number==1:
        # The complete native cycle-average brackets around E_k comprise two
        # left and two right vector strokes. The right pair lies2.39pt from
        # the k outline, beyond the generic1.5pt proximity heuristic. It is
        # part of this expression and must travel with E_k.
        average=next(q for q in parts if q['id']=='m100')
        right_indices={(3018,3019,3020),(3028,3029,3030)}
        right=[v for v in objects['vector_paths']if tuple(v['operator_indices'])in right_indices]
        if len(right)!=2:raise ValueError('Original E_k right average bracket strokes changed')
        existing={tuple(v['operator_indices'])for v in average['vector_paths']}
        average['vector_paths'] += [v for v in right if tuple(v['operator_indices'])not in existing]
        boxes=[average['rect']]+[v['rect']for v in right]
        average['rect']=[min(r[0]for r in boxes),min(r[1]for r in boxes),max(r[2]for r in boxes),max(r[3]for r in boxes)]
        average['reviewed_complete_average_brackets']='Both original left and both original right vector strokes move with the original E_k CIDs; no new bracket is drawn.'
    ink_path=BASE/f'inspection/page{number:02}-native-ink-bounds.json'
    if ink_path.exists():
        ink=json.loads(ink_path.read_text('utf8'))
        for q in parts:
            rects=[ink['boxes'][str(key(g))]for g in q['glyphs']if str(key(g))in ink['boxes']]
            if rects:
                q['source_ink_rect']=[min(r[0]for r in rects),min(r[1]for r in rects),max(r[2]for r in rects),max(r[3]for r in rects)]
                r=q['source_ink_rect'];old=q['rect'];q['rect']=[min(old[0],r[0]),min(old[1],r[1]),max(old[2],r[2]),max(old[3],r[3])]
    rows=[]
    for row in p['rows']:
        slots=[s for s in p['slots']if s['row']==row['row']and not s.get('retain_native')]
        atoms=[q for q in parts if q['row']==row['row']]
        items=[dict(x=s['origin'][0],kind='prose',id=s['id'],source=s['source'])for s in slots]
        items += [dict(x=q['rect'][0],kind='math',id=q['id'],source=q['source'])for q in atoms]
        items.sort(key=lambda a:a['x'])
        rows.append(dict(row=row['row'],baseline=row['baseline'],source=row['source'],events=items,
                         marked=''.join(i['source']if i['kind']=='prose'else'{'+i['id']+':'+i['source']+'}'for i in items)))
    return dict(page=number,source=p,erased_glyphs=[g for g in allg if key(g)in erase]+language_punctuation,
                reviewed_language_punctuation=language_punctuation,native_parts=parts,rows=rows)

if __name__=='__main__':
    for n in range(1,6):
        d=events(n)
        (BASE/f'authoring/T/page{n:02}.events.json').write_text(json.dumps(d,ensure_ascii=False,indent=1),'utf8')
        text='\n'.join(f"{q['row']}\t{q['baseline']:.2f}\t{q['marked']}"for q in d['rows'])
        (BASE/f'authoring/T/page{n:02}.events.txt').write_text(text,'utf8')
        print(n,len(d['erased_glyphs']),len(d['native_parts']))

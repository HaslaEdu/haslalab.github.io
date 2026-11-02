"""Read-only replay of partial atom claims against reviewed authored word spaces."""
from pathlib import Path
import json,copy,importlib.util,sys
import pymupdf as fitz
from pdf_original_text_ops import glyph_key
from izho_native_atomic_tokens import atomic_tokens
from izho_natural_spacing import ROOT,baseline_lines,inject_atomic_tokens,authored_fragment
from pdf_korean_natural_composer import normalize_placements,_units,BATANG,_plain,_replace,_style
from izho_natural_spacing import visible
def old_units(item,placements,metric):
    p=placements[item['placement']]if 'placement'in item else None
    rows=sorted(visible(item['glyphs']),key=lambda r:(r['origin'][0],r['origin'][1]))
    if item['kind']=='native':
        return[dict(kind='native',glyphs=item['glyphs'],width=item['x1']-item['x0'],old_x=item['x0'],shift_kwargs=item.get('shift_kwargs',{}))]
    text=(p or{}).get('text',item['text'])
    if _plain(text)!=''.join(r['c']for r in rows):
        text=item['text']
    if _plain(text)!=''.join(r['c']for r in rows):
        raise ValueError(('Authored prose text differs from visible glyph sequence',text,''.join(r['c']for r in rows)))
    # Edge spaces are represented once by boundary_gap. Keeping authored
    # trailing/leading blanks here would produce a doubled word space.
    text=text.strip()
    units=[];ri=0
    for c in text:
        if c.isspace():
            if not units or units[-1]['kind']!='space':units.append(dict(kind='space',width=item['size']/4))
            continue
        row=rows[ri];ri+=1;replace=_replace(row,p)
        signature=(replace,row['font'],row['size'],row.get('paint',0),tuple(row['origin'][1:]),str(row.get('color')),row.get('linewidth'))
        if units and units[-1]['kind']!='space'and units[-1]['signature']==signature:
            unit=units[-1];unit['glyphs'].append(row);unit['text']+=c
            if replace:unit['width']=metric.text_length(unit['text'],fontsize=row['size'])
            else:unit['width']=max(r['bbox'][2]for r in unit['glyphs'])-unit['old_x']
        else:
            units.append(dict(kind='batang'if replace else'native',signature=signature,text=c,glyphs=[row],
                              old_x=row['origin'][0],width=metric.text_length(c,fontsize=row['size'])if replace else row['bbox'][2]-row['origin'][0],
                              style=_style(row,p)if replace else None))
    return units


def old_inject(lines,atoms):
    claimed={glyph_key(r)for atom in atoms for r in atom['glyphs']}
    from izho_natural_spacing import token,visible
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


def compare(lines,atoms,placements,metric):
    historical=copy.deepcopy(lines)
    from izho_natural_spacing import visible
    for line in historical:
        for item in line['tokens']:
            if 'placement'not in item:continue
            authored=placements[item['placement']]['text']
            compact=''.join(g['c']for g in visible(item['glyphs']))
            item['text']=authored if ''.join(authored.split())==compact else compact
    before=old_inject(historical,atoms)
    after=inject_atomic_tokens(copy.deepcopy(lines),atoms)
    changes=[]
    from izho_natural_spacing import boundary_gap
    for left,right in zip(before,after):
        for i,(a,b)in enumerate(zip(left['tokens'],right['tokens'])):
            if a['text']==b['text']:continue
            au=old_units(a,placements,metric);bu=_units(b,placements,metric)
            spaces_before=sum(u['kind']=='space'for u in au)
            spaces_after=sum(u['kind']=='space'for u in bu)
            oldgap=boundary_gap(left['tokens'][i-1],a)if i else None
            newgap=boundary_gap(right['tokens'][i-1],b)if i else None
            oldfollowing=boundary_gap(a,left['tokens'][i+1])if i+1<len(left['tokens'])else None
            newfollowing=boundary_gap(b,right['tokens'][i+1])if i+1<len(right['tokens'])else None
            if spaces_before==spaces_after and oldgap==newgap and oldfollowing==newfollowing:continue
            changes.append(dict(baseline=left['baseline'],source_glyph_origins=[g['origin']for g in a['glyphs']],
                old_text=a['text'],restored_authored_text=b['text'],placement_index=a.get('placement'),
                old_units=[dict(kind=u['kind'],text=u.get('text',''),width=u['width'])for u in au],
                restored_units=[dict(kind=u['kind'],text=u.get('text',''),width=u['width'])for u in bu],
                missing_authored_internal_word_spaces=spaces_after-spaces_before,
                before_gap_pt=oldgap,after_gap_pt=newgap,before_following_gap_pt=oldfollowing,after_following_gap_pt=newfollowing))
    return changes


def audit(plan_path,composition_path=None):
    plan_path=Path(plan_path);d=json.loads(plan_path.read_text(encoding='utf8'))
    comp=Path(composition_path)if composition_path else plan_path.parents[1]/('page%02d.qa.json'%d['page'])
    q=json.loads(comp.read_text(encoding='utf8'))
    stationary=[g for region in d.get('stationary_table_math',[])for g in region['native_glyphs']]
    locked={glyph_key(g)for g in stationary}
    explicit=q.get('reviewed_explicit_native_math_atoms',[])
    metric=fitz.Font(fontfile=str(BATANG));changes=[]
    with fitz.open(d['source_base'])as doc:
        page=doc[d['page']-1];placements=normalize_placements(page,d['prose_placements'])
        for rect in d['allowed_line_rects']:
            lines=baseline_lines(page,allowed_line_rects=[rect],excluded_figure_rects=d.get('excluded_figure_rects',[]),
                prose_placements=placements,baseline_tolerance_pt=d.get('baseline_tolerance_pt',.12),stationary_native_glyphs=stationary)
            atoms=atomic_tokens(d['source_base'],d['page'],rect,[dict(baseline=line['baseline'],size=max(t['size']for t in line['tokens']))for line in lines],d.get('excluded_figure_rects',[]),include_image_only=d.get('include_image_only_native_math',False))
            atoms=[a for a in atoms if not any(glyph_key(g)in locked for g in a['glyphs'])]
            selected=[]
            for a in explicit:
                if not(rect[0]-1<=a['x0']and a['x1']<=rect[2]+1 and rect[1]<=a['y']<=rect[3]):continue
                box=fitz.Rect(a.get('bbox',[a['x0'],a['y']-a['size'],a['x1'],a['y']+a['size']/3]))
                if any(box.intersects(fitz.Rect(r))for r in d.get('excluded_figure_rects',[])):continue
                selected.append(a)
            keys={glyph_key(g)for a in selected for g in a['glyphs']}
            atoms=[a for a in atoms if not any(glyph_key(g)in keys for g in a['glyphs'])]+selected
            for change in compare(lines,atoms,placements,metric):
                change['rect']=rect
                old_runs=[u['text']for u in change['old_units']if u['kind']=='batang']
                actual=[p['text']for p in q.get('new_batang_placements',[])]
                change['collapsed_batang_runs_present_in_recorded_proof']=all(t in actual for t in old_runs)
                changes.append(change)
    return dict(plan=str(plan_path),composition=str(comp),year=d['year'],kind=d['kind'],page=d['page'],
        recorded_output_sha256=q['output_sha256'],partial_claim_affected_tokens=len(changes),
        missing_authored_internal_word_spaces=sum(c['missing_authored_internal_word_spaces']for c in changes),
        changes=changes,read_only=True)

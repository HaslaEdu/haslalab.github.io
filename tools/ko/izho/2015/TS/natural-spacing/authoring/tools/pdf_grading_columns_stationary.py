"""Independent original grading numerals must stay in their table cells."""
from collections import defaultdict
import re
import pymupdf as fitz
from pdf_native_inline_reposition import _traces,inspect_inline_groups
from pdf_original_text_ops import glyph_key

def audit(source,target,placements,*,reviewed_score_column=None):
    with fitz.open(source)as original,fitz.open(target)as final:
        page=original[0];segments=[]
        for drawing in page.get_drawings():
            for item in drawing['items']:
                if item[0]=='l':
                    a,b=item[1:3];rect=fitz.Rect(min(a.x,b.x),min(a.y,b.y),max(a.x,b.x),max(a.y,b.y))
                elif item[0]=='re':rect=fitz.Rect(item[1])
                else:continue
                if rect.width<.6 and rect.height>4:segments.append(rect)
        form_keys={glyph_key(g)for group in inspect_inline_groups(source,1)['forms']for g in group['glyphs']}
        actual=_traces(final[0]);wanted=[];changed=[]
        content_numbers=[]
        if reviewed_score_column:
            if reviewed_score_column.get('original_source_sha256')!='c1bc32cc38c3f3b65121439f41feee3a8bcb48dcce1a41e14b16ba177eccbcde'or reviewed_score_column.get('source_page')!=5 or reviewed_score_column.get('left')!=482.35:raise ValueError('Unreviewed source grading-score column')
            boundary=sorted([r for r in segments if abs(r.x0-482.35)<.01],key=lambda r:r.y0)
            if not boundary or boundary[0].y0>=173 or boundary[-1].y1<=550 or any(b.y0-a.y1>.7 for a,b in zip(boundary,boundary[1:])):raise ValueError('Actual original segmented content/score grid boundary is absent')
        for g in _traces(page):
            if g['c']not in'0123456789.,'or g['trace_gid']<0 or g['origin'][0]<.75*page.rect.width:continue
            if reviewed_score_column and reviewed_score_column['top']<=g['origin'][1]<=reviewed_score_column['bottom']and g['origin'][0]<reviewed_score_column['left']:
                content_numbers.append({k:g[k]for k in('c','font','size','origin')});continue
            if re.search('Ital|Oblique',g['font'])or glyph_key(g)in form_keys:continue
            x,y=g['origin'];boundaries=[]
            for r in segments:
                if r.y0-.5<=y<=r.y1+.5 and not any(abs(r.x0-v)<.7 for v in boundaries):boundaries.append(r.x0)
            if len(boundaries)<3 or not(min(boundaries)<x<max(boundaries)):continue
            # Native-font ASCII authored inside a translated sentence is prose,
            # not an original grading numeral.
            if any(p.get('point')and p.get('width')is not None and abs(y-p['point'][1])<.03
                and p['point'][0]-.03<=x<p['point'][0]+p['width']+.03 for p in placements):continue
            wanted.append(g)
            matches=[h for h in actual if h['c']==g['c']and h['font']==g['font']and h['trace_gid']==g['trace_gid']
                and abs(h['size']-g['size'])<1e-6 and abs(h['origin'][0]-x)<=.001 and abs(h['origin'][1]-y)<=.001]
            if not matches:changed.append({k:g[k]for k in('c','font','size','origin')})
        return dict(method='Independent source vertical cell primitives plus original top-level, non-prose numeric glyphs in the page right grading columns; every original grading glyph must remain at its source position.',reviewed_actual_score_column=reviewed_score_column,original_numeric_content_entries_checked_as_mathematics_by_separate_complete_expression_and_native_ink_audits=content_numbers,
            original_grading_glyphs_checked=len(wanted),grading_glyphs_moved_from_source_cells=changed,passed=not changed)

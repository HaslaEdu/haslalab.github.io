"""Split packed mixed text/Form groups into exact native invocation units."""
from pdf_original_text_ops import glyph_key,family_name
from pdf_native_inline_reposition import inspect_inline_groups

def key(g):
    return glyph_key(dict(g,font=family_name(g['font'])))

def atomic_shifts(source,page_number,shifts):
    forms=inspect_inline_groups(source,page_number)['forms'];out=[]
    for shift in shifts:
        if not shift['glyphs']and('form_path'in shift or'image_path'in shift):
            # Reviewed bitmap mathematics has no encoded text glyphs. Its
            # original invocation still defines a complete movable object.
            out.append(shift);continue
        remaining={key(g):g for g in shift['glyphs']};original=set(remaining)
        for form in sorted(forms,key=lambda f:len(f['path'])):
            glyphs=[g for g in form['glyphs']if g['c'].strip()]
            keys={key(g)for g in glyphs}
            if not keys or not keys&set(remaining):continue
            if keys<=set(remaining):
                out.append(dict(glyphs=glyphs,dx=shift['dx'],form_path=form['path']))
                for token in keys:remaining.pop(token)
            elif keys&original:
                raise ValueError('Packing split a source math Form between different movements: '+str(form['path']))
        if remaining:out.append(dict(glyphs=list(remaining.values()),dx=shift['dx']))
    return out

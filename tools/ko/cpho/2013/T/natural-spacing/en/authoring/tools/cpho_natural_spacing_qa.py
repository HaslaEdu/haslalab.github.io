"""Independent rendered native-math visibility for naturally spaced CPhO pages.

Native font/GID/size/paint/expected x checks are performed by the CID mover.
This additionally renders independently extracted original glyph outlines at
their final positions, without their text clips, and checks their dark ink
against the actual final page. Thus an unchanged CID hidden by a stale clip
cannot pass merely because its metadata survived.
"""
from collections import Counter
from pathlib import Path
import argparse,html,json,re
import numpy as np
import pymupdf as fitz
from pdf_native_inline_reposition import _traces
from pdf_original_text_ops import glyph_key
from cpho_natural_spacing import baseline,original,OUT,sha


def _physical_key(g):
    return(g['c'],g['font'],g['trace_gid'],round(g['size'],5),round(g['origin'][0],4),round(g['origin'][1],4))


def original_native_glyphs(year,language,page_number):
    with fitz.open(original(year)) as source,fitz.open(baseline(year,language)) as proof:
        old=Counter(_physical_key(g) for g in _traces(source[page_number-1]));native=[]
        for g in _traces(proof[page_number-1]):
            key=_physical_key(g)
            if old[key]:old[key]-=1;native.append(g)
        return native


def audit(year,language,page_number,scale=4):
    folder=OUT/str(year)/language;target=folder/f'page{page_number:02}.pdf'
    journal=json.loads(target.with_suffix('.qa.json').read_text('utf8'))
    native=[g for g in original_native_glyphs(year,language,page_number) if g['c'].strip() and g['trace_gid']>=0]
    from pdf_moved_native_ink import audit_moved_native_ink
    report=audit_moved_native_ink(baseline(year,language),page_number,target,
        shifts=journal['native_shifts'],erased_glyphs=journal['erased_hangul_glyphs'],
        protected_glyphs=native,scale=scale)
    report.update(year=year,language=language,page=page_number)
    target.with_suffix('.math-visibility.json').write_text(json.dumps(report,indent=2),'utf8')
    print(json.dumps(report));return report


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('year',type=int);p.add_argument('language',choices=['ko','en']);p.add_argument('page',type=int)
    a=p.parse_args();raise SystemExit(not audit(a.year,a.language,a.page)['passed'])

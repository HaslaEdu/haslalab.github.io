from pathlib import Path
from collections import Counter,defaultdict
import hashlib
import pikepdf,pymupdf as fitz
from izho_natural_spacing import records
from initial_prose_reading_order import journal
from pdf_korean_natural_composer import normalize_placements
from izho_initial_outline_qa import trace_font_resources,outline_results,svg_outline_status
from pdf_original_text_ops import family_name

def audit(source,source_page,target,placements,cache=None):
    cache={}if cache is None else cache
    with fitz.open(source)as base,fitz.open(target)as final,pikepdf.open(target)as pdf:
        raw=records(base[source_page-1]);js=journal(base[source_page-1],normalize_placements(base[source_page-1],placements));count=sum(len(j['glyphs'])for j in js);prefix=raw[:-count]if count else raw
        mapped,programs=trace_font_resources(pdf,final[0])
        if len(mapped)<len(prefix):raise ValueError('Original source-native prefix was dropped')
        for a,b in zip(prefix,mapped):
            if(a['c'],family_name(a['font']),a['gid'],a['paint'])!=(b['c'],b['font'],b['gid'],b['render_type'])or abs(a['size']-b['size'])>1e-6:
                raise ValueError(('Original native prefix paint order changed',a,b))
        new=[g for g in mapped[len(prefix):]if g['gid']>=0 and not g['c'].isspace()]
        expected=Counter(c for j in js for c in j['placement']['text']if not c.isspace())
        if Counter(g['c']for g in new)!=expected:raise ValueError('New translated prose characters were dropped or added')
        by_program=defaultdict(list)
        for g in new:by_program[g['font_program_sha256']].append(g)
        checked=[]
        for digest,gs in by_program.items():
            if digest is None:checked.extend(svg_outline_status(final[0],gs))
            else:checked.extend(outline_results(dict(programs[digest],sha=digest),gs,cache))
        empty=[g for g in checked if g['outline_empty']]
        return dict(source_page=source_page,source_sha256=hashlib.sha256(Path(source).read_bytes()).hexdigest(),proof_sha256=hashlib.sha256(Path(target).read_bytes()).hexdigest(),source_native_paint_prefix_glyphs_excluded=len(prefix),new_prose_nonspace_glyphs_checked=len(checked),new_native_ascii_prose_glyphs_checked=sum(len(g['c'])==1 and ord(g['c'])<128 for g in checked),actual_embedded_gid_empty_outlines=empty,translated_prose_character_multiset_matches_authored_text=True,method='Exact authored-prose suffix journal identifies original native paint prefix; final translated prose is checked by actual PDF resource/GID embedded outlines, without counting moved original mathematical glyphs as new prose.',passed=not empty)

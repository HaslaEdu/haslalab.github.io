"""Read-only exact source-slot coverage, with explicitly retained units/math."""
from pathlib import Path
import json,re,hashlib
import pymupdf as fitz
from izho_initial_fixed_style import runs_of,slot_source,characters,glyph_key

UNITS={'см','мм','км','Па','кг','моль','Дж','МэВ','Кл','еВ','Ф','Вт','Гц','kg','cm','mm','km','Pa','mol','MeV','Hz','mbar','kPa','MPa','ms'}
REVIEWED_ITALIC_VARIABLE_PRODUCTS={'Mg','RT','Af','Bg','Ch','Zm','Nm','Mc','kA','AB'}
def audit(plan_path):
    plan_path=Path(plan_path);d=json.loads(plan_path.read_text('utf8'));selected=set();explicit=set()
    with fitz.open(d['source'])as doc:
        runs=runs_of(doc[d['page']])
        for spec in d['slots']:selected.update(glyph_key(c)for c in slot_source(spec,runs)[1])
        for at in d.get('protected_runs',[]):explicit.update(glyph_key(c)for c in characters(runs[tuple(at)]))
        for spec in d.get('protected_substrings',[]):explicit.update(glyph_key(c)for c in slot_source(spec,runs)[1])
        remaining=[];unknown=[]
        for at,run in runs.items():
            if re.search('Cambria.?Math|Symbol|MT.?Extra',run['font'],re.I):continue
            text=''.join(' 'if glyph_key(c)in selected or glyph_key(c)in explicit else c['c']for c in characters(run))
            for word in re.findall('[A-Za-zА-Яа-яёЁ]{2,}',text):
                mathematical=word in d.get('native_prose_tokens',[])or(bool(run['flags']&2)and word in REVIEWED_ITALIC_VARIABLE_PRODUCTS)
                row=dict(at=list(at),text=word,font=run['font'],kind='Explicit original mathematical label'if mathematical else'Original encoded unit symbol'if word in UNITS else'Unselected language')
                remaining.append(row)
                if row['kind']=='Unselected language':unknown.append(row)
    return dict(source_sha256=d['source_sha256'],source_page=d['page']+1,plan_sha256=hashlib.sha256(plan_path.read_bytes()).hexdigest(),selected_source_glyphs=len(selected),explicitly_protected_original_field_or_formula_glyphs=len(explicit),retained_original_words=remaining,unselected_language_words=unknown,passed=not unknown,method='Exact selected source glyphs, including through/substring slots; source math fonts and explicit physical field labels protected; remaining narrative words must be original unit symbols or specifically reviewed native math labels.')
if __name__=='__main__':
    import sys
    b=Path(__file__).resolve().parents[1];year=sys.argv[1];out=b/year/'source-language-coverage.json';rows=[audit(p)for p in sorted((b/year/'original_style').glob('page*.json'))];out.write_text(json.dumps(dict(pages=rows,passed=all(r['passed']for r in rows)),ensure_ascii=False,indent=2),encoding='utf8');print([(r['source_page'],r['unselected_language_words'])for r in rows]);assert all(r['passed']for r in rows)

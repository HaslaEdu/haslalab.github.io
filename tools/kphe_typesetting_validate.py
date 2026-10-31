"""Audit marked mathematics with the exact production equation renderer."""
import json
import re
from pathlib import Path
from kphe_template import math_pdf, set_typography

ROOT = Path(__file__).resolve().parents[1]

def fields(row):
    for name in ('explanation', 'formula', 'caveat', 'review_note'):
        values = row.get(name, [])
        for i, value in enumerate([values] if isinstance(values, str) else values):
            yield f'{name}[{i}]', value
    for name in ('statement', 'after_figure', 'givens', 'choices'):
        for i, value in enumerate(row.get('problem', {}).get(name, [])):
            yield f'problem.{name}[{i}]', value

def main():
    expressions, errors, raw = {}, [], []
    rows = runs = 0
    for path in sorted((ROOT/'tools/kphe_solutions').glob('*.json')):
        for part, items in json.loads(path.read_text(encoding='utf-8')).items():
            if not isinstance(items, list): continue
            face = 'HyhwpEQ' if path.name == '2024-2-cd.json' and part == 'T2d' else 'HancomEQN'
            for row in items:
                rows += 1
                for field, value in fields(row):
                    where = f'{path.name}:{part}:{row["number"]}:{field}'
                    if value.count('$') % 2:
                        errors.append({'where':where,'error':'unbalanced math delimiter'})
                    outside = re.sub(r'\$[^$]+\$', '', value)
                    if re.search(r'[_^α-ωΑ-Ω√∫Σ∑ħℏ²³₀-₉]|\bsqrt\s*\(', outside):
                        raw.append({'where':where,'text':outside})
                    for match in re.finditer(r'\$([^$]+)\$', value):
                        runs += 1
                        expressions.setdefault((face, match[1]), []).append(where)
    wide, maximum = [], 0
    active_face = None
    for i, ((face, expression), locations) in enumerate(expressions.items(),1):
        try:
            if face != active_face:
                source = 'KPhE_2024_T2d_KO.pdf' if face == 'HyhwpEQ' else 'KPhE_2026_T2c_KO.pdf'
                set_typography(ROOT/'pdfx/kphe'/source)
                active_face = face
            doc, width, height, depth = math_pdf(expression, 9.8)
            maximum = max(maximum, width)
            if width > 230:
                wide.append({'where':locations,'expression':expression,'width':width})
        except Exception as error:
            errors.append({'where':locations,'expression':expression,'error':str(error)})
        if i % 500 == 0: print(f'Equation outlines checked: {i}/{len(expressions)}', flush=True)
    report = {'questions':rows,'math_runs':runs,'unique_math':len({expression for face, expression in expressions}),
              'equation_font_variants':len(expressions),
              'font':'Original HancomEQN and legacy HyhwpEQ outlines; original italic PUA glyph mapping',
              'maximum_width_at_body_size':maximum,'overwide_runs':wide,'errors':errors,'unmarked_math':raw}
    (ROOT/'tools/kphe_typesetting_report.json').write_text(json.dumps(report,ensure_ascii=False,indent=1)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k not in ('errors','unmarked_math','overwide_runs')},ensure_ascii=False))
    print(f'Render errors: {len(errors)}; unmarked mathematics: {len(raw)}; overwide runs: {len(wide)}')
    if errors or raw or wide: raise SystemExit(1)

if __name__=='__main__': main()

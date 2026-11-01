from pathlib import Path
import sys,json
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/izho2010-complete-solutions');sys.path[:0]=[str(B/'engine'),'D:/CodexBuilds/Hasla-publish-20261031/tools']
from final_translation_font_audit import audit
from initial_final_prose_outline_audit import audit as all_prose
from initial_source_language_coverage import audit as language
from pdf_display_equation_numbers import audit as numbers
cache={};rows=[]
for n in range(1,12):
 plan=B/f'natural/2010/TS/plans/page{n:02}.json';p=json.loads(plan.read_text('utf8'));target=plan.parents[1]/f'page{n:02}.pdf'
 f=audit(plan,cache);a=all_prose(p['source_base'],n,target,p['prose_placements'],cache);l=language(B/f'2010/original_style/page{n}.json');e=numbers(p,target)
 assert a['passed']and l['passed']and e['passed'];q=dict(page=n,font_source_style=f,all_new_prose=a,source_language=l,equation_numbers=e,passed=True);target.with_suffix('.final-extra-checks.json').write_text(json.dumps(q,ensure_ascii=False,indent=2)+'\n','utf8');rows.append(q);print('FINAL_TRANSLATION_FONTS_AND_SOURCE_COVERAGE PASS',n,f['hangul_glyphs_checked'],flush=True)
(B/'natural/2010/TS/final-extra-checks.json').write_text(json.dumps(dict(pages=rows,passed=True),ensure_ascii=False,indent=2)+'\n','utf8')

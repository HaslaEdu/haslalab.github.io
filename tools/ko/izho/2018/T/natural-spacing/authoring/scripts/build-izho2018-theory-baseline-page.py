from pathlib import Path
import sys,json,contextlib
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/izho2018-theory-original')
sys.path[:0]=[str(B/'engine'),'D:/CodexBuilds/Hasla-publish-20261031/tools']
from izho_initial_fixed_style import build
from pdf_memory_gate import page_worker
n=int(sys.argv[1])
with (B/f'2018/native-baseline/page{n:02}-build.log').open('w',encoding='utf8')as log,contextlib.redirect_stdout(log),page_worker():build(B/f'2018/original_style/page{n}.json',B/f'2018/native-baseline/page{n:02}.pdf')
q=json.loads((B/f'2018/native-baseline/page{n:02}.qa.json').read_text('utf8'))
print('PRIVATE_NATIVE_BASELINE',n,'font_programs',q['source_font_programs_and_names_unchanged'],'images',q['source_images_bytes_and_rects_unchanged'],'vectors',q['source_vector_drawings_unchanged'],'untranslated',len(q['unreviewed_english_prose_runs']),'publication_ready',False,flush=True)

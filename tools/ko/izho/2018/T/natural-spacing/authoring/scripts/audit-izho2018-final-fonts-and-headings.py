from pathlib import Path
import sys,subprocess,os
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/izho2018-theory-original')
env=dict(os.environ,PYTHONIOENCODING='utf8',PYTHONDONTWRITEBYTECODE='1',OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1')
for n in list(map(int,sys.argv[1:]))or range(1,7):
 code=f"import sys;from pathlib import Path;sys.path[:0]=[{str(B/'engine')!r},'D:/CodexBuilds/Hasla-publish-20261031/tools'];from pdf_memory_gate import page_worker;from final_translation_font_audit import audit as font;from heading_source_alignment_audit import audit as heading\nwith page_worker():\n p=Path({str(B/f'natural/2018/T/plans/page{n:02}.json')!r});q=font(p);h=heading(p);assert q['passed']and h['passed'];print('SOURCE_FONT_OUTLINE_POINTS_BASELINES_AND_TITLE_CENTERS_PASS',{n},q['hangul_glyphs_checked'],h['headings_and_captions_checked'],h['original_bold_prose_heading_coverage']['headings_checked'],flush=True)"
 subprocess.run([sys.executable,'-u','-c',code],env=env,check=True)

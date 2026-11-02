from pathlib import Path
import sys,subprocess,os,json
B=Path('C:/Users/andre/.codex/tmp/Hasla-original-style-20261102/izho2011-complete-solutions')
env=dict(os.environ,PYTHONIOENCODING='utf8',PYTHONDONTWRITEBYTECODE='1',OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1')
for n in list(map(int,sys.argv[1:]))or range(1,11):
 code=f"import sys;from pathlib import Path;sys.path[:0]=[{str(B/'engine')!r},'D:/CodexBuilds/Hasla-publish-20261031/tools'];from pdf_memory_gate import page_worker;from final_translation_font_audit import audit as font;from heading_source_alignment_audit import audit as heading\nwith page_worker():\n p=Path({str(B/f'natural/2011/TS/plans/page{n:02}.json')!r});q=font(p);h=heading(p);assert q['passed']and h['passed'];print('SOURCE_FONT_OUTLINE_POINTS_BASELINES_ORIENTATION_AND_CENTERS_PASS',{n},q['hangul_glyphs_checked'],h['headings_and_captions_checked'],h['original_bold_prose_heading_coverage']['headings_checked'],flush=True)"
 subprocess.run([sys.executable,'-u','-c',code],env=env,check=True)
 if n==3:
  q=json.loads((B/'natural/2011/TS/page03.qa.json').read_text('utf8'));row=next(r for r in q['lines']if abs(r['baseline']-84.84)<.02);assert len(row['gaps'])==2 and row['gaps'][0]['left']=='1C(2.5'and row['gaps'][0]['right']=='점'and row['gaps'][1]['right']==')'and all(g['new_gap']==0 for g in row['gaps']);print('EXACT_MIXED_HEADING_BOTH_NATURAL_BOUNDARIES_PASS',flush=True)

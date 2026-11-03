from pathlib import Path
import sys,os,subprocess
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/izho2012-complete-solutions');env=dict(os.environ,PYTHONIOENCODING='utf8',PYTHONDONTWRITEBYTECODE='1',OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1')
for n in map(int,sys.argv[1:]):
 plan=B/f'natural/2012/TS/plans/page{n:02}.json'
 code=f"import sys;from pathlib import Path;sys.path[:0]=[{str(B/'engine')!r},'D:/CodexBuilds/Hasla-publish-20261031/tools'];from pdf_memory_gate import page_worker;from izho_2012_non_hangul_prose_collision import audit\nwith page_worker():q=audit(Path({str(plan)!r}))\nassert q['passed'],q;print('ALL_NEW_BODY_NON_HANGUL_PROSE_NATIVE_TEXT_AND_GRAPHICS_COLLISIONS_ZERO',{n},q['body_non_Hangul_prose_glyphs'],flush=True)"
 subprocess.run([sys.executable,'-u','-X','utf8','-c',code],env=env,check=True)

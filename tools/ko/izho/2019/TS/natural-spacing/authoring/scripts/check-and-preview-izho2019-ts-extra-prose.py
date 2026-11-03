from pathlib import Path
import sys,subprocess,os
B=Path('C:/Users/andre/CodexWork/HaslaLab/translation-builds/izho2019-complete-solutions');env=dict(os.environ,PYTHONIOENCODING='utf8',PYTHONDONTWRITEBYTECODE='1',OPENBLAS_NUM_THREADS='1')
for n in map(int,sys.argv[1:]):
 plan=B/f'natural/2019/TS/plans/page{n:02}.json';code=f"import sys;from pathlib import Path;sys.path[:0]=[{str(B/'engine')!r},'D:/CodexBuilds/Hasla-publish-20261031/tools'];from pdf_memory_gate import page_worker;from izho_2019_ts_non_hangul_prose_collision import audit\nwith page_worker():q=audit(Path({str(plan)!r}))\nassert q['passed'],q;print('ALL_2019_NEW_PROSE_PUNCTUATION_NATIVE_INK_COLLISIONS_ZERO',{n},q['new_non_Hangul_prose_glyphs'],flush=True)"
 subprocess.run([sys.executable,'-u','-X','utf8','-c',code],env=env,check=True)
 subprocess.run([sys.executable,'-u','-X','utf8','D:/CodexBuilds/render-izho2019-ts-reviewed-previews.py',str(n)],env=env,check=True)

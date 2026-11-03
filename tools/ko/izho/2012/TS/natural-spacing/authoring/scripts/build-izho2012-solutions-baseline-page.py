from pathlib import Path
import sys,json,contextlib,os,hashlib,shutil
os.environ.update(OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1',PYTHONDONTWRITEBYTECODE='1')
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/izho2012-complete-solutions')
sys.path[:0]=[str(B/'engine'),'D:/CodexBuilds/Hasla-publish-20261031/tools']
from izho_initial_fixed_style import build
from pdf_memory_gate import page_worker
n=int(sys.argv[1]);folder=B/'2012/native-baseline';folder.mkdir(exist_ok=True)
prior=folder/f'page{n:02}.pdf'
if prior.exists():
 digest=hashlib.sha256(prior.read_bytes()).hexdigest();archive=folder/'history'/digest[:16];archive.mkdir(parents=True,exist_ok=True)
 for item in folder.glob(f'page{n:02}*'):
  if item.is_file():
   target=archive/item.name
   if target.exists():assert hashlib.sha256(target.read_bytes()).hexdigest()==hashlib.sha256(item.read_bytes()).hexdigest()
   else:shutil.copy2(item,target)
with(folder/f'page{n:02}-build.log').open('w',encoding='utf8')as log,contextlib.redirect_stdout(log),page_worker():
 build(B/f'2012/original_style/page{n}.json',folder/f'page{n:02}.pdf')
q=json.loads((folder/f'page{n:02}.qa.json').read_text('utf8'))
print('PRIVATE_IZHO2012_BASELINE',n,'source_fonts',q['source_font_programs_and_names_unchanged'],'source_images',q['source_images_bytes_and_rects_unchanged'],'source_vectors',q['source_vector_drawings_unchanged'],'untranslated',len(q['unreviewed_english_prose_runs']),flush=True)

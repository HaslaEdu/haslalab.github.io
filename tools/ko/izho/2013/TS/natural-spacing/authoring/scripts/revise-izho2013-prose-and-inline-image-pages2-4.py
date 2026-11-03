from pathlib import Path
import sys,os,json,hashlib,shutil,subprocess
R=Path('D:/CodexBuilds');B=R/'Hasla-original-style-20261031/izho2013-complete-solutions';F=B/'natural/2013/TS';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
env=dict(os.environ,PYTHONIOENCODING='utf8',PYTHONDONTWRITEBYTECODE='1',OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1')
changes={2:[("'7,1,0':'포화 증기압의 온도 의존성을 '","'7,1,0':'포화 증기압을 '"),("['','라 하자. 물이 모두 증발하는 ']","['','라 하자. ']"),("'7,2,0':'온도는 다음 방정식의 해로 구한다: '","'7,2,0':'물이 모두 증발하는 온도는 다음 방정식의 해로 구한다: '")],4:[("around(p,'29,8,0',['','부터 '],['0'])","around(p,'29,8,0',['시간 ','부터 '],['0'])")]}
for n,replacements in changes.items():
 p=R/f'author-izho2013-solutions-page{n}.py';text=p.read_text('utf8');saved=B/'authoring-history'/sha(p)[:16];saved.mkdir(parents=True,exist_ok=True);shutil.copy2(p,saved/p.name);shutil.copy2(B/f'2013/original_style/page{n}.json',saved/f'page{n}.json')
 for a,b in replacements:assert text.count(a)==1,(n,a);text=text.replace(a,b)
 p.write_text(text,'utf8')
 files=sorted(p for p in F.glob(f'page{n:02}*')if p.is_file());version=hashlib.sha256(''.join(p.name+sha(p)for p in files).encode()).hexdigest()[:16];archive=F/'history'/f'preserved-before-prose-image-review-{version}';archive.mkdir(parents=True,exist_ok=True)
 for item in files:
  target=archive/item.name;assert item.resolve().is_relative_to(B.resolve())and target.resolve().is_relative_to(B.resolve());assert not target.exists();digest=sha(item);item.rename(target);assert sha(target)==digest
 subprocess.run([sys.executable,'-u','-X','utf8',str(p)],env=env,check=True)
 subprocess.run([sys.executable,'-u','-X','utf8',str(R/'build-izho2013-solutions-baseline-page.py'),str(n)],env=env,check=True)
 prepare=R/'prepare-izho2013-solutions-natural.py';code=prepare.read_text('utf8');head,tail=code.split('sys.path[:0]=',1);prefix='\n'.join(head.splitlines()[:3])+'\n';sys.argv=[str(prepare),str(n)];exec(compile(prefix+'sys.path[:0]='+tail,str(prepare)+'#reuse-reviewed-engine','exec'),{'__name__':'__main__'})
 if n==2:
  plan=F/'plans/page02.json';d=json.loads(plan.read_text('utf8'));rects=[r[:]for r in d['excluded_figure_rects']];matches=[r for r in rects if abs(r[0]-259.54998779296875)<.001 and abs(r[3]-128.75)<.001];assert len(matches)==1;before=matches[0][:];matches[0][3]-=.001;d['reviewed_layout_figure_rects']=rects
  d['reviewed_exact_neighboring_math_bitmap_boundary']={'source_figure_bbox':before,'layout_only_exclusion_bbox':matches[0],'unaltered_inline_image_bbox':[366.95001220703125,128.74998474121094,488.5,143.04998779296875],'reason':'Two original mathematical bitmap envelopes touch at128.75pt; their serialized float32 bounds overlap by0.00001526pt. Only the layout exclusion for the preceding display object ends0.001pt earlier, allowing the separate complete inline bitmap to join its own140.06pt prose row. Original bitmap bytes/CTMs and full figure pixel-audit rectangle are unchanged, and actual new-prose/native-ink collision checks remain strict zero. No source image is cropped or resampled.','full_source_figure_QA_rectangle_unchanged':True}
  plan.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n','utf8')
print('SOURCE_2013_PAGES2_4_PROSE_IMAGE_LAYOUT_REVIEWED',flush=True)

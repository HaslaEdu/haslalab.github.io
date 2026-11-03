from pathlib import Path
import subprocess,sys,os,hashlib
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/izho2012-complete-solutions');n=int(sys.argv[1]);plan=B/f'natural/2012/TS/plans/page{n:02}.json';env=dict(os.environ,PYTHONIOENCODING='utf8',PYTHONDONTWRITEBYTECODE='1',OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1');prefix=f"import sys;from pathlib import Path;sys.path[:0]=[{str(B/'engine')!r},'D:/CodexBuilds/Hasla-publish-20261031/tools'];from pdf_memory_gate import page_worker;"
jobs=[prefix+f"from izho_natural_spacing_rebuild import page_build;page_build(Path({str(plan)!r}))",prefix+f"from izho_natural_spacing_qa import audit\nwith page_worker():q=audit(2012,'TS',{n})\nassert q['passed']",prefix+f"from modern_new_prose_collision_audit import audit_plan\nwith page_worker():q=audit_plan(Path({str(plan)!r}))\nassert q['passed']",prefix+f"from heading_source_alignment_audit import audit;q=audit(Path({str(plan)!r}));assert q['passed']"]
audit_only='--audit-only'in sys.argv[2:];log=B/f'natural/2012/TS/page{n:02}-build.log'
prior=log.parent/f'page{n:02}.pdf'
if not audit_only and prior.exists():
 history=log.parent/'history'/hashlib.sha256(prior.read_bytes()).hexdigest()[:16];history.mkdir(parents=True,exist_ok=True)
 for item in log.parent.glob(f'page{n:02}*'):
  if not item.is_file():continue
  target=history/item.name;raw=item.read_bytes()
  if target.exists():assert target.read_bytes()==raw,('Historical proof evidence differs',target)
  else:target.write_bytes(raw)
if n==1:jobs.append(prefix+f"from izho_2012_complete_inline_fractions import audit;q=audit(Path({str(plan)!r}));assert q['passed'];print('EXACT_ORIGINAL_NATIVE_FRACTION_RULES_SHARE_GLYPH_DX',q['reviewed_complete_expressions'],q['original_fraction_rules_checked'],flush=True)")
jobs.append(prefix+f"from izho_2012_equation_counters import audit;q=audit(Path({str(plan)!r}));assert q['passed'];print('ALL_ORIGINAL_DISPLAY_EQUATION_COUNTER_XY_FONT_GID_POINTS_PASS',q['equation_counters_checked'],flush=True)")
jobs.append(prefix+f"from izho_2012_non_hangul_prose_collision import audit\nwith page_worker():q=audit(Path({str(plan)!r}))\nassert q['passed'];print('ALL_NEW_NON_HANGUL_PROSE_PUNCTUATION_ACTUAL_INK_COLLISIONS_ZERO',q['new_non_Hangul_prose_glyphs'],flush=True)")
with log.open('a'if audit_only else'w',encoding='utf8')as out:
 for i,code in enumerate(jobs[1:]if audit_only else jobs,2 if audit_only else 1):
  r=subprocess.run([sys.executable,'-u','-c',code],env=env,stdout=out,stderr=subprocess.STDOUT)
  if r.returncode:print('NATIVE_2012_TS_PAGE_FAILED',n,'stage',i,'log',log,flush=True);raise SystemExit(r.returncode)
  print('NATIVE_2012_TS_PAGE_STAGE_PASS',n,i,flush=True)
print('NATIVE_2012_TS_PAGE_ALL_CHECKS_PASS',n,flush=True)

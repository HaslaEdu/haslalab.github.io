from pathlib import Path
import json,hashlib,sys,shutil
B=Path(__file__).resolve().parents[1];sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
n=int(sys.argv[1]);reason=sys.argv[2];A=B/f'authoring/page{n:02}-native-language.json'
for lang in(sys.argv[3:]or['ko','en']):
 stem=B/f'proofs/{lang}/page{n:02}';pdf=stem.with_suffix('.pdf')
 if not pdf.exists():continue
 report=json.loads(stem.with_suffix('.composition.json').read_text('utf8'));assert sha(pdf)==report['output_sha256'];plan=Path(report['actual_immutable_producing_plan']);assert plan.resolve().is_relative_to(B.resolve())and sha(plan)==report['plan_sha256']
 H=B/f'history/page{n:02}-{lang}-{sha(pdf)[:16]}';H.mkdir(parents=True,exist_ok=False);records=[]
 for p in[plan,A]:
  dst=H/p.name;shutil.copy2(p,dst);assert sha(p)==sha(dst);records.append(dict(path=str(dst),sha256=sha(dst),bytes=dst.stat().st_size))
 for p in list(stem.parent.glob(stem.name+'.*'))+list((B/'inspection').glob(f'page{n:02}-{lang}-current144.*')):
  assert p.resolve().is_relative_to(B.resolve())and p.is_file();dst=H/p.name;shutil.copy2(p,dst);assert sha(p)==sha(dst);records.append(dict(path=str(dst),sha256=sha(dst),bytes=dst.stat().st_size));p.unlink()
 (H/'history.json').write_text(json.dumps(dict(reason=reason,actual_proof_sha256=report['output_sha256'],actual_producing_plan_sha256=report['plan_sha256'],files=records),ensure_ascii=False,indent=2)+'\n','utf8');print('C08_ACTUAL_REVIEW_ARCHIVED',n,lang,report['output_sha256'])

from pathlib import Path
import json,hashlib
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/cpho2025/master-v1');output=B/'editions/CPhO_2025_T_KO.pdf';spec=json.loads((B/'assembly-ko-input.json').read_text('utf8'));log=Path('D:/CodexBuilds/cpho2025-master-assembly.log');sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
identity=dict(proofs=[dict(source_page=r['source_page'],sha256=r['sha256'])for r in spec['proofs']],output_sha256=sha(output));output.with_suffix('.assembly-source-identity.json').write_text(json.dumps(identity,indent=2),'utf8')
rows=[json.loads(line)for line in log.read_text('utf8').splitlines()if line.startswith('{')]
for row in rows:
 assert row['passed']and row['poppler_144dpi_changed_pixels']==0
 number=row['page'];assert row['proof_sha256']==spec['proofs'][number-1]['sha256'];folder=output.parent/(output.stem+'-assembly-render');a=folder/f'page{number:02}-proof.png';b=folder/f'page{number:02}-joined.png';assert sha(a)==sha(b)
 cache=dict(proof_sha256=row['proof_sha256'],output_sha256=identity['output_sha256'],renderer='pdftoppm144dpiRGB',proof_png=dict(path=str(a),sha256=sha(a)),joined_png=dict(path=str(b),sha256=sha(b)),migration_evidence=dict(initial_completed_assembly_log=str(log),log_sha256=sha(log),actual_completed_comparison=row))
 (folder/f'page{number:02}-poppler-identity.json').write_text(json.dumps(cache,indent=2),'utf8')
print('Preserved actual completed Poppler comparisons',len(rows),'for exact output',identity['output_sha256'])

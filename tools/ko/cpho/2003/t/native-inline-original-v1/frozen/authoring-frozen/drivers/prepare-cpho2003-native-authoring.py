"""Create private C: authoring inputs from verified read-only predecessors."""
from pathlib import Path
import sys,shutil,json,hashlib,ast
B=Path('C:/Users/andre/CodexWork/HaslaLab/translation-builds/cpho2003-original-native')
F=Path('D:/CodexBuilds/Hasla-original-style-20261031/cpho2007/TS/master-v1/authoring-frozen')
E=B/'engine';sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
provenance=[]
for p in sorted((F/'engine').glob('*.py')):
 if p.name.startswith('cpho2007'):continue
 out=E/p.name
 if out.exists():assert sha(out)==sha(p)
 else:shutil.copy2(p,out)
 provenance.append(dict(source=str(p),target=str(out),sha256=sha(out),unchanged=True))
p=F/'engine/cpho2007_ts_initial_native_baseline.py';s=p.read_text('utf8')
s=s.replace('2007','2003').replace('2e30b56ab9274363686cbf5bc1ef7532dcf579e0703de2c01098b003ab70cdd9','52f8a891d6129becf4d21ccb60f46997cedf9aa50123ffd147294cedcb121b63')
s=s.replace("all(c['font']=='ºÚÌå+FPEF'for c in owned)","all(c['font']=='SimHei'for c in owned)").replace("c['font']=='ºÚÌå+FPEF'and", "c['font']=='SimHei'and")
s=s.replace('right=506','right=524.3')
s=s.replace("if item[3]==name)","if item[3].split('+',1)[-1]==name)")
s=s.replace("if allhei and first['size']>14:","if first['size']>14 and first['origin'][1]<140:")
s=s.replace("if pi==0 and ri==1:","if pi==0 and ri==1 and first['size']>14:")
s=s.replace("'provenance_notes':[{'page':18,'description':'The original recoil-approximation comparison glyph is an empty square / unmapped character. Its native glyph is retained without a printed editorial note.'}]", "'provenance_notes':[{'description':'Original source has physical T1-3 and TS4-10; preserve the actual source folios and all blank regions.'}]")
out=E/'cpho2003_initial_native_baseline.py'
if out.exists():
 history=B/'engine-history/cpho2003_initial_native_baseline-before-subset-name-read.py';history.parent.mkdir(exist_ok=True);assert not history.exists();shutil.copy2(out,history)
ast.parse(s);out.write_text(s,'utf8')
sys.path.insert(0,str(E));import cpho2003_initial_native_baseline as m
m.SOURCE=B/'inputs/CPhO_2003_Chinese_original.pdf';m.SOURCE_SHA='52f8a891d6129becf4d21ccb60f46997cedf9aa50123ffd147294cedcb121b63';m.BASE=B/'native-inventory';m.AUTHOR=B/'authoring/native';m.ROOT=B
from pdf_memory_gate import page_worker
with page_worker():data=m.extract()
target=B/'inputs/original-all10-source-slots.json';assert not target.exists();shutil.copy2(m.BASE/'slots.json',target)
(B/'inputs/native-engine-copy-provenance.json').write_text(json.dumps(dict(readonly_source_engine=provenance,derived_initial_engine=dict(path=str(out),sha256=sha(out),changes='Year/source identity, source SimHei names, original 524.3pt body right, centered source titles, and actual10-page provenance only.'),native_guard_sha256=sha(E/'pdf_native_inline_reposition.py')),ensure_ascii=False,indent=2)+'\n','utf8')
assert sha(E/'pdf_native_inline_reposition.py')=='ab04f78a8de1845269742c3e95828c635ee5b3d5bd957d226577390bfe25279f'
print('CPHO2003_NATIVE_INVENTORY_PREPARED',sha(target),flush=True)

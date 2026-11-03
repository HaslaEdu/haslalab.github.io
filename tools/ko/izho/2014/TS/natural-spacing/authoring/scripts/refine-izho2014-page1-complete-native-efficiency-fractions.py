from pathlib import Path
import json,hashlib,shutil,sys,pymupdf as f
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/izho2014-complete-solutions');F=B/'natural/2014/TS';sys.path.insert(0,str(B/'engine'));from pdf_native_inline_reposition import _traces
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();p=F/'plans/page01.json';d=json.loads(p.read_text('utf8'));assert d['original_english_source_sha256']=='1e526966f308280accc9fe747d08259279f35324e7e7f2e0290271adcaf6536c';history=F/'history'/('plan-before-complete-efficiency-fractions-'+sha(p)[:16]);history.mkdir(parents=True,exist_ok=True);shutil.copy2(p,history/p.name)
rect=[312,523,442,555]
with f.open(d['original_english_source'])as doc:glyphs=[g for g in _traces(doc[0])if g['c'].strip()and f.Rect(rect).contains(f.Point(g['origin']))]
assert len(glyphs)>15 and any(g['c']=='η'for g in glyphs)
d.setdefault('explicit_native_math_atoms',[]).append(dict(rect=rect,baseline=538.6799926757812,font_regex='.*',source_native_glyphs=glyphs,original_source_only=True,include_zero_height_vector_bounds=True,reviewed=True,reason='Complete original inline steam-engine efficiency eta=(T1-T2)/T1=4.2/379=1.1%, including both original fraction-rule vectors, original Times/Symbol CIDs, scripts, source decimal commas and punctuation. Full original/final page1 review found top-level fraction rules were not bound to their moving native CID expressions. Preserve all original points/GIDs/paint/Y and move the complete original expression and both rule endpoints by one common dx. No formula retyping, scaling or guard changes.'))
d['reviewed_complete_original_inline_fraction_profiles']=[dict(rect=rect,baseline=538.6799926757812,label='Complete original native inline Carnot efficiency with both fractional rules')]
files=sorted(p for p in F.glob('page01*')if p.is_file());version=hashlib.sha256(''.join(p.name+sha(p)for p in files).encode()).hexdigest()[:16];saved=F/'history'/f'automated-positive-before-visual-fraction-rule-review-{version}';saved.mkdir(parents=True,exist_ok=True)
for item in files:
 target=saved/item.name;assert item.resolve().is_relative_to(B.resolve())and target.resolve().is_relative_to(B.resolve());assert not target.exists();digest=sha(item);item.rename(target);assert sha(target)==digest
p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n','utf8');assert sha(B/'engine/pdf_native_inline_reposition.py')=='ab04f78a8de1845269742c3e95828c635ee5b3d5bd957d226577390bfe25279f';print('2014_PAGE1_BOTH_FRACTION_BARS_AND_COMPLETE_NATIVE_GLYPHS_BOUND_TO_ONE_DX',len(glyphs),flush=True)

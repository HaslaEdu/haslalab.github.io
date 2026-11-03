from pathlib import Path
import json,sys,hashlib,re,shutil,pymupdf as f
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/izho2014-complete-solutions');F=B/'natural/2014/TS';sys.path.insert(0,str(B/'engine'));from pdf_native_inline_reposition import _traces
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();path=F/'plans/page02.json';d=json.loads(path.read_text('utf8'));assert d['original_english_source_sha256']=='1e526966f308280accc9fe747d08259279f35324e7e7f2e0290271adcaf6536c';assert not json.loads((F/'page02.audit.json').read_text('utf8'))['passed']
history=F/'history'/('plan-before-complete-native-fractions-'+sha(path)[:16]);history.mkdir(parents=True,exist_ok=True);shutil.copy2(path,history/path.name)
with f.open(d['original_english_source'])as doc:rows=_traces(doc[1])
atoms=list(d.get('explicit_native_math_atoms',[]));profiles=[([256,130,334,164],148.44000244140625,'Complete original equivalent-source pair epsilon0=epsilon/2,r0=r/2'),([234,276,284,308],292.79998779296875,'Complete original inline heat expression Q0=C epsilon squared/2'),([184,749,226,766],760.9199829101562,'Complete original initial charge q(0)=0'),([250,743,306.4,774],760.9199829101562,'Complete original final charge q(infinity)=C epsilon/2')]
for rect,baseline,label in profiles:
 box=f.Rect(rect);gs=[g for g in rows if g['c'].strip()and box.contains(f.Point(g['origin']))];assert len(gs)>=4,(label,gs)
 atoms.append(dict(rect=rect,baseline=baseline,font_regex='.*',source_native_glyphs=gs,original_source_only=True,include_zero_height_vector_bounds=True,reviewed=True,reason=label+'. Full original source page2 visually read. This entire expression, including all original scripts/parentheses/Greek glyphs and every original fraction-rule vector within the reviewed bounds, must move by one common dx. Retain exact source fonts/GIDs/fractional points/paint/Y and original bar lengths; never split numerator or denominator from its bar. No formula retyping, scaling, font substitution or native guard change.'))
d['explicit_native_math_atoms']=atoms;d['reviewed_complete_original_inline_fraction_profiles']=[dict(rect=r,baseline=y,label=label)for r,y,label in profiles]
files=sorted(p for p in F.glob('page02*')if p.is_file());version=hashlib.sha256(''.join(p.name+sha(p)for p in files).encode()).hexdigest()[:16];archive=F/'history'/f'rejected-before-complete-inline-fractions-{version}';archive.mkdir(parents=True,exist_ok=True)
for item in files:
 target=archive/item.name;assert item.resolve().is_relative_to(B.resolve())and target.resolve().is_relative_to(B.resolve());assert not target.exists();digest=sha(item);item.rename(target);assert sha(target)==digest
path.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n','utf8');assert sha(B/'engine/pdf_native_inline_reposition.py')=='ab04f78a8de1845269742c3e95828c635ee5b3d5bd957d226577390bfe25279f';print('2014_PAGE2_FOUR_ORIGINAL_INLINE_EXPRESSIONS_COMMON_GLYPH_AND_FRACTION_BAR_MOTION_REQUIRED',flush=True)

from pathlib import Path
import hashlib,json,sys,pymupdf as f
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/izho2013-complete-solutions');F=B/'natural/2013/TS';sys.path.insert(0,str(B/'engine'));from pdf_native_inline_reposition import _traces
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();checks={1:('3,1,0','문제1(10점)',[70,557]),3:('7,0,0','문제2(10점)',[70,557]),7:('3,6,0','북극N과남극S를올바르게표시',[110,455]),8:('2,0,0','문제3(10점)',[70,557])};records=[]
for n in map(int,sys.argv[1:]):
 at,expected,bounds=checks[n];runs=json.loads((B/f'2013/inspection/page{n:02}-runs.json').read_text('utf8'));y=runs[at]['origin'][1];path=F/f'page{n:02}.pdf'
 with f.open(path)as doc:rows=[g for g in _traces(doc[0])if abs(g['origin'][1]-y)<.001 and bounds[0]<=g['origin'][0]<=bounds[1]and g['c'].strip()and g['render_mode']!=3]
 unique={}
 for g in rows:unique[(g['c'],round(g['origin'][0],4),round(g['origin'][1],4),round(g['size'],4))]=g
 rows=sorted(unique.values(),key=lambda g:g['origin'][0]);actual=''.join(g['c']for g in rows);r=dict(page=n,pdf_sha256=sha(path),original_source_slot=at,original_baseline=y,expected_actual_spatial_glyph_order=expected,actual_spatial_glyph_order=actual,passed=actual==expected,actual_physical_glyphs=[{k:g[k]for k in['c','font','size','origin','trace_gid']}for g in rows]);records.append(r)
 output=F/f'page{n:02}-actual-native-prose-order-audit.json';output.write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n','utf8');print('ACTUAL_NATIVE_PROSE_REFERENCE_ORDER',n,r['passed'],actual,flush=True)
assert all(r['passed']for r in records),records

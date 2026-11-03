"""Read actual final glyphs to verify the source-centered cover and TOC columns."""
from pathlib import Path
from collections import Counter
import hashlib,json
import pymupdf as f
import icho2019_write_guard as g
B=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def glyphs(page):return[dict(c=chr(cp),gid=gid,font=t['font'],size=t['size'],origin=list(origin),bbox=list(bbox))for t in page.get_texttrace()if t['type']!=3 for cp,gid,origin,bbox in t['chars']if chr(cp).strip()]
def run(n):
    if n not in[1,2,3]:return None
    path=g.PROOFS/f'page{n:02}.pdf';q=json.loads(path.with_suffix('.layout.json').read_text('utf8'));assert sha(path)==q['output_sha256']
    source=f.open(g.SOURCE);final=f.open(path);actual=glyphs(final[0]);report=dict(page=n,proof_sha256=sha(path),source_sha256=g.SOURCE_SHA,measurement_code_sha256=sha(__file__))
    if n in[1,2]:
        metadata=B/('source-cover-centering.json'if n==1 else'source-page02-message-centering.json')
        specs=json.loads(metadata.read_text('utf8'))['pages'][str(n)];rows=[]
        for spec in specs:
            baseline=spec['original_baselines'][0];new=[v for v in actual if abs(v['origin'][1]-baseline)<.001 and v['font'].startswith('Noto')]
            assert new
            center=(min(v['bbox'][0]for v in new)+max(v['bbox'][2]for v in new))/2
            error=abs(center-spec['source_center_x'])
            assert error<=.001,(n,spec,center,error)
            assert {round(v['size'],5)for v in new}=={round(v,5)for v in spec['original_point_sizes']}
            rows.append(dict(source_line=spec['source_line'],source_center_x=spec['source_center_x'],actual_target_glyph_box_center_x=center,center_error_pt=error,source_baseline=baseline,actual_target_baselines=sorted({v['origin'][1]for v in new}),source_point_sizes=spec['original_point_sizes'],actual_target_point_sizes=sorted({v['size']for v in new})))
        report.update(passed=True,rows=rows,center_tolerance_pt=.001,method='Read actual output glyph boxes rather than authored placement claims; compare the complete nonspace Korean run with the measured original full nonspace source run. Source drop-cap size distinctions and exact baselines are retained.')
        if n==2:
            old=[v for v in glyphs(source[1])if v['c']=='½'];new=[v for v in actual if v['c']=='½'];assert len(old)==len(new)==1
            a,b=old[0],new[0]
            assert (a['gid'],a['font'],a['size'],a['origin'][1])==(b['gid'],b['font'],b['size'],b['origin'][1]),(a,b)
            report['source_half_fraction']=dict(source=a,actual=b,original_gid_font_point_size_and_baseline_exact=True,translation='½분 이상',no_numerical_conversion=True)
    else:
        original=[v for v in glyphs(source[2])if 400<=v['origin'][0]<=525 and 185<=v['origin'][1]<=430]
        remaining=list(actual);errors=[]
        for v in original:
            matches=[(i,w)for i,w in enumerate(remaining)if w['c']==v['c']and w['gid']==v['gid']and w['font']==v['font']and abs(w['size']-v['size'])<=.001 and max(abs(a-b)for a,b in zip(w['origin'],v['origin']))<=.001]
            if len(matches)!=1:errors.append(v)
            else:remaining.pop(matches[0][0])
        assert not errors,errors
        report.update(passed=True,source_column_origins_pt=[402.42999267578125,494.5],stationary_original_glyphs_verified=len(original),errors=[],position_and_point_size_tolerance_pt=.001,method='Read each actual final glyph/GID/font/point size/origin in the two original independent TOC columns; do not infer preservation from source-copy metadata.')
    final.close();source.close();(g.PROOFS/f'page{n:02}.template-geometry.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n','utf8');return report
if __name__=='__main__':
    import sys
    for n in map(int,sys.argv[1:]or[1,3]):print(json.dumps(run(n),ensure_ascii=False),flush=True)

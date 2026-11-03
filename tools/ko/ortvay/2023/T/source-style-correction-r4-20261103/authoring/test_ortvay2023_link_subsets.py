"""Actual O2023 p1/p6 annotation-only changes and adversarial regressions."""
from pathlib import Path
import os
for name in ['OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS']:os.environ[name]='1'
import copy,hashlib,json
import pikepdf,pymupdf as f,numpy as np
import ortvay2023_link_annotations as link

B=Path(__file__).resolve().parents[1]
F=B/'proofs/ortvay/2023'
S=Path('D:/CodexBuilds/Hasla-plancks-ortvay-icho-20261102/source/ortvay/Ortvay_2023_T_EN.pdf')
O=B/'experiments/ortvay2023-link-subsets';O.mkdir(parents=True,exist_ok=True)
sha=link.sha
assert sha(S)==link.SOURCE_SHA

def semantic(value,seen=None):
    """Compare settings after save independently of PDF object renumbering."""
    if isinstance(value,pikepdf.Dictionary):
        return {str(k):semantic(v) for k,v in value.items() if str(k)!='/P'}
    if isinstance(value,pikepdf.Array):return [semantic(v) for v in value]
    return value.unparse().decode('latin1') if hasattr(value,'unparse') else repr(value)

def nonrect(annotation):
    return {str(k):semantic(v) for k,v in annotation.items() if str(k) not in ['/Rect','/P']}

page_results=[];all_negative=[]
with f.open(S) as source:
    for n in [1,6]:
        P=F/f'page{n:02}.pdf';qp=P.with_suffix('.layout.json')
        Q=json.loads(qp.read_text('utf8'))
        assert Q['page']==n and Q['output_sha256']==sha(P)
        with f.open(P) as proof:
            output=O/f'page{n:02}-links.pdf'
            with pikepdf.Pdf.open(P) as d:
                before=[nonrect(a) for a in d.pages[0].obj.get('/Annots',[])]
                rows=link.adjust_links(d.pages[0],source[n-1],proof[0],Q)
                d.save(output,compress_streams=False)
            with pikepdf.Pdf.open(output) as d:
                assert [nonrect(a) for a in d.pages[0].obj.get('/Annots',[])]==before
            with f.open(output) as final:
                assert proof[0].get_texttrace()==final[0].get_texttrace()
                a=proof[0].get_pixmap(matrix=f.Matrix(1.5,1.5),alpha=False)
                b=final[0].get_pixmap(matrix=f.Matrix(1.5,1.5),alpha=False)
                assert (a.width,a.height,a.n)==(b.width,b.height,b.n)
                changed=int(np.any(np.frombuffer(a.samples,np.uint8).reshape(a.height,a.width,a.n)
                                   !=np.frombuffer(b.samples,np.uint8).reshape(b.height,b.width,b.n),axis=2).sum())
                assert changed==0
                for row in rows:
                    matches=[v for v in final[0].get_links() if v.get('uri')==row['uri']
                             and link.same_origin(list(v['from']),row['expected_target_rect_mupdf'],.001)]
                    assert len(matches)==1
                    row['actual_target_rect_mupdf']=list(matches[0]['from']);row['passed']=True

            first=next(row for row in rows if row['dx']!=0)
            index=first['glyph_references'][0]['native_shift_index']
            assert index is not None
            negative=[]
            with pikepdf.Pdf.open(P) as d:
                q=copy.deepcopy(Q);del q['native_shifts'][index]
                try:link.adjust_links(d.pages[0],source[n-1],proof[0],q)
                except AssertionError:negative.append('missing native URL movement rejected')
                else:raise AssertionError('Missing original URL movement accepted')
            with pikepdf.Pdf.open(P) as d:
                q=copy.deepcopy(Q);q['selected_glyphs'].append(copy.deepcopy(first['glyph_references'][0]['source_glyph']))
                try:link.adjust_links(d.pages[0],source[n-1],proof[0],q)
                except AssertionError:negative.append('URL glyph incorrectly hidden as prose rejected')
                else:raise AssertionError('Hidden URL glyph accepted')
            with pikepdf.Pdf.open(P) as d:
                selected=rows[-1]
                annotation=next(a for a in d.pages[0].obj['/Annots']
                                if str(a.get('/A',{}).get('/URI',''))==selected['uri']
                                and link.same_origin(list(f.Rect(list(map(float,a['/Rect'])))*source[n-1].transformation_matrix),selected['source_rect_mupdf'],.001))
                rect=list(map(float,annotation['/Rect']))
                wrong=rows[0]['source_rect_pdf'] if len(rows)>1 else selected['target_rect_pdf']
                assert not link.same_origin(rect,wrong,.001)
                annotation['/Rect']=pikepdf.Array(wrong)
                try:link.adjust_links(d.pages[0],source[n-1],proof[0],Q)
                except AssertionError:negative.append('correct URI with wrong original rectangle rejected')
                else:raise AssertionError('URI-only annotation match accepted')
            result=dict(page=n,proof_sha256=sha(P),layout_sha256=sha(qp),output_sha256=sha(output),
                        changed_pixels=changed,all_visible_glyph_geometry_identical=True,
                        all_nonrect_annotation_settings_identical_after_save=True,
                        links=rows,negative_regressions=negative)
            page_results.append(result);all_negative.extend(dict(page=n,check=v) for v in negative)

report=dict(status='PASS',source_sha256=sha(S),helper_sha256=sha(Path(link.__file__)),
            program_sha256=sha(Path(__file__)),pages=page_results,links=[v for p in page_results for v in p['links']],
            changed_pixels=sum(v['changed_pixels'] for v in page_results),
            all_visible_glyph_geometry_identical=True,all_nonrect_annotation_settings_identical_after_save=True,
            negative_regressions=all_negative)
(O/'regression.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n','utf8')
print(json.dumps(dict(status=report['status'],pages=len(page_results),links=len(report['links']),
                      moved=sum(v['dx']!=0 for v in report['links']),changed_pixels=report['changed_pixels'],
                      negative_regressions=all_negative),ensure_ascii=False))

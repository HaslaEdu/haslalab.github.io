"""Independent annotation-only regressions for explicitly selected private proofs."""
from pathlib import Path
import argparse,copy,hashlib,importlib.util,json,math,os,sys
sys.dont_write_bytecode=True
for name in ['OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS']:os.environ[name]='1'
import numpy as np
import pikepdf,pymupdf as fitz

OWN=Path(__file__).resolve().parent
SOURCE_SHA={2023:'c0a5117145c67edc2dfe8953dcc7865438f65e099fe6e73b2ec19616ab27b5f7',
            2024:'d7b856084d0159122329b2a3f86f123a2517d99b2f2a05607d9df93acf02f2c9',
            2025:'84291fb1a1f4cb47fb4421eff335da153122895da349ce09c1b25f00461c7ab8'}
URL2025='https://arxiv.org/abs/2412.13580'
GLYPH_TOLERANCE=.001

def sha(path):
    with Path(path).open('rb')as stream:return hashlib.file_digest(stream,'sha256').hexdigest()

def read(path):return json.loads(Path(path).read_text('utf8'))

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    assert Path(module.__file__).resolve()==Path(path).resolve()
    return module

def same(a,b,tolerance=1e-5):
    return len(a)==len(b)and max(abs(x-y)for x,y in zip(a,b))<=tolerance

def glyphs(page):
    return [dict(c=chr(cp),gid=gid,font=t['font'],size=t['size'],origin=list(origin),bbox=list(bbox),
                 color=t.get('color'),opacity=t.get('opacity'),render_type=t['type'])
            for t in page.get_texttrace()if t['type']!=3 for cp,gid,origin,bbox in t['chars']]

def semantic(value,seen=None,path='$'):
    """Follow indirect values so saving/object renumbering cannot hide changes."""
    seen={}if seen is None else seen
    indirect=getattr(value,'is_indirect',False)
    key=value.objgen if indirect else None
    if key in seen:return {'cycle_to':seen[key]}
    if indirect:seen=dict(seen);seen[key]=path
    if isinstance(value,pikepdf.Stream):
        return dict(stream_raw_sha256=hashlib.sha256(value.read_raw_bytes()).hexdigest(),
                    dictionary={str(k):semantic(v,seen,path+'/'+str(k))for k,v in value.items()})
    if isinstance(value,pikepdf.Dictionary):return {str(k):semantic(v,seen,path+'/'+str(k))for k,v in value.items()}
    if isinstance(value,pikepdf.Array):return [semantic(v,seen,path+'/'+str(i))for i,v in enumerate(value)]
    return value.unparse().decode('latin1')if hasattr(value,'unparse')else repr(value)

def annotation_records(page):
    records=[]
    for annotation in page.obj.get('/Annots',[]):
        settings={}
        for key,value in annotation.items():
            if str(key)=='/Rect':continue
            if str(key)=='/P':
                assert getattr(value,'is_indirect',False)and value.objgen==page.obj.objgen,'Annotation /P must reference its own page'
                settings['/P']={'same_page_reference':True}
            else:settings[str(key)]=semantic(value)
        records.append(dict(rect=list(map(float,annotation['/Rect'])),settings=settings,
                            uri=str(annotation.get('/A',{}).get('/URI',''))))
    return records

def check_saved_annotations(before,page,rows):
    after=annotation_records(page);assert len(after)==len(before),'Annotation count changed'
    for old,new in zip(before,after):
        assert old['settings']==new['settings'],'Non-Rect annotation settings changed'
        selected=[r for r in rows if r['uri']==old['uri']and same(r['source_rect_pdf'],old['rect'],.001)]
        assert len(selected)<=1,'Ambiguous annotation row'
        expected=selected[0]['target_rect_pdf']if selected else old['rect']
        assert same(new['rect'],expected,1e-6),'Saved rectangle differs from independently expected value'
        assert old['rect'][1]==new['rect'][1]and old['rect'][3]==new['rect'][3],'Annotation changed vertically'
    return after

def audit_native_urls(source,proof,qa,expected):
    links=[v for v in source.get_links()if v.get('uri')]
    assert len(links)==len(expected),'Unexpected original URL annotation count'
    original=glyphs(source);visible=glyphs(proof);results=[]
    for number,(annotation,(uri,fragment))in enumerate(zip(links,expected)):
        assert annotation['uri']==uri
        rect=list(annotation['from']);box=fitz.Rect(rect)
        selected=[v for v in original if(fitz.Rect(v['bbox']).tl+fitz.Rect(v['bbox']).br)*.5 in box]
        assert selected and ''.join(v['c']for v in selected)==fragment,'Original URL subset changed'
        references=[];deltas=[];errors=[]
        for native in selected:
            assert not any(v['c']==native['c']and same(v['origin'],native['origin'])for v in qa['selected_glyphs']),'URL glyph hidden as Korean prose'
            matches=[(i,j,shift,v)for i,shift in enumerate(qa['native_shifts'])for j,v in enumerate(shift['glyphs'])
                     if v['c']==native['c']and same(v['origin'],native['origin'])]
            assert len(matches)<=1,'Duplicate/ambiguous URL movement'
            i,j,shift,bound=matches[0]if matches else(None,None,None,None)
            dx=float(shift['dx'])if shift else 0.
            assert math.isfinite(dx),'Nonfinite URL movement'
            if bound:
                assert bound['gid']==native['gid']and bound['font']==native['font'],'URL movement glyph identity changed'
                assert abs(bound['size']-native['size'])<=.001 and same(bound['bbox'],native['bbox'],.001),'URL movement source geometry changed'
            expected_origin=[native['origin'][0]+dx,native['origin'][1]]
            expected_bbox=[v+(dx if k%2==0 else 0)for k,v in enumerate(native['bbox'])]
            actual=[v for v in visible if v['c']==native['c']and v['gid']==native['gid']and v['font']==native['font']
                    and abs(v['size']-native['size'])<=.001 and same(v['origin'],expected_origin,.001)]
            assert len(actual)==1,'Visible native URL glyph does not match its reviewed movement'
            item=actual[0];error=max(abs(x-y)for x,y in zip(item['bbox'],expected_bbox))
            assert error<=GLYPH_TOLERANCE,'Visible URL bbox changed'
            assert (item['color'],item['opacity'],item['render_type'])==(native['color'],native['opacity'],native['render_type']),'Native URL rendering style changed'
            deltas.append(dx);errors.append(error)
            references.append(dict(source_glyph=native,native_shift_index=i,shift_glyph_index=j,dx=dx))
        assert max(deltas)-min(deltas)<1e-8,'One link rectangle spans different movements'
        results.append(dict(source_link_index=number,uri=uri,display_fragment=fragment,source_rect_mupdf=rect,
                            dx=deltas[0],glyph_references=references,source_url_glyphs=len(selected),
                            max_url_glyph_geometry_error_pt=max(errors),position_tolerance_pt=GLYPH_TOLERANCE,
                            native_url_glyphs_verified_in_proof=True))
    return results

def find_annotation(page,row,source_page):
    matches=[a for a in page.obj.get('/Annots',[])if str(a.get('/A',{}).get('/URI',''))==row['uri']
             and same(list(fitz.Rect(list(map(float,a['/Rect'])))*source_page.transformation_matrix),row['source_rect_mupdf'],.001)]
    assert len(matches)==1
    return matches[0]

def check_ready(path,proof_dir,year,inputs):
    ready=read(path);assert ready['year']==year
    assert ready['status']=='YEAR_STRICT_SOURCE_STYLE_CORRECTION_READY_FOR_ROOT_ASSEMBLY_REVIEW'
    assert ready['source']['sha256']==SOURCE_SHA[year]
    records=ready['page_results'];assert len(records)==ready['pages']
    assert sorted(v['page']for v in records)==list(range(1,ready['pages']+1))
    for record in records:
        for key,suffix in [('proof','.pdf'),('layout','.layout.json')]:
            item=record[key];file=Path(item['path']).resolve()
            assert file==(proof_dir/f"page{record['page']:02}{suffix}").resolve(),'READY references a different proof directory'
            assert sha(file)==item['sha256'],'READY has a stale proof/layout'
            inputs[str(file)]=item['sha256']
    inputs[str(path)]=sha(path)
    return dict(path=str(path),sha256=inputs[str(path)],schema=ready['schema'],pages=ready['pages'],proof_and_layout_files_rehashed=2*ready['pages'])

def main(year,program):
    parser=argparse.ArgumentParser(description=f'Actual O{year} private annotation regression; input paths are explicit and read-only.')
    parser.add_argument('--proof-dir',type=Path,required=True)
    parser.add_argument('--output-dir',type=Path,required=True)
    parser.add_argument('--engine-dir',type=Path,default=OWN.parents[2]/'engine')
    parser.add_argument('--source',type=Path)
    parser.add_argument('--ready-manifest',type=Path,required=True)
    parser.add_argument('--page',type=int)
    args=parser.parse_args()
    proof_dir=args.proof_dir.resolve();output_dir=args.output_dir.resolve();engine_dir=args.engine_dir.resolve()
    assert proof_dir.is_dir()and engine_dir.is_dir()
    assert output_dir!=proof_dir and not output_dir.is_relative_to(proof_dir),'Output cannot be inside the proof inputs'
    assert not proof_dir.is_relative_to(output_dir),'Output cannot be an ancestor of proof inputs'
    assert output_dir!=engine_dir and not output_dir.is_relative_to(engine_dir),'Output cannot be inside engine inputs'
    if output_dir.exists():assert output_dir.is_dir()and not any(output_dir.iterdir()),'Output directory must be absent or empty; no overwrites allowed'
    sys.path.insert(0,str(engine_dir))
    join=load('_private_link_join',engine_dir/'assemble_natural.py')
    link=load(f'_private_link_{year}',engine_dir/f'ortvay{year}_link_annotations.py')if year in(2023,2024)else None
    if year==2023:
        assert args.page in(1,6),'O2023 requires an explicit reviewed link page1 or6'
        page=args.page
    else:
        page=2 if year==2024 else 10
        assert args.page is None or args.page==page
    proof_path=proof_dir/f'page{page:02}.pdf';layout_path=proof_path.with_suffix('.layout.json')
    qa=read(layout_path);assert qa['page']==page and qa['source_sha256']==SOURCE_SHA[year]
    assert qa['output_sha256']==sha(proof_path),'Stale private proof/layout pair'
    source_path=args.source.resolve()if args.source else Path(join.resolve_source(qa['source'],qa['source_sha256'])).resolve()
    assert sha(source_path)==SOURCE_SHA[year]
    inputs={str(p):sha(p)for p in[Path(program).resolve(),Path(__file__).resolve(),source_path,proof_path,layout_path,Path(join.__file__).resolve()]}
    if link:inputs[str(Path(link.__file__).resolve())]=sha(link.__file__)
    resolver=sys.modules.get('source_path_resolver')
    if resolver and getattr(resolver,'__file__',None):inputs[str(Path(resolver.__file__).resolve())]=sha(resolver.__file__)
    original_test=engine_dir/(f'test_ortvay{year}_link_subsets.py'if year in(2023,2024)else'test_ortvay2025_link.py')
    assert original_test.is_file();inputs[str(original_test)]=sha(original_test)
    ready=check_ready(args.ready_manifest.resolve(),proof_dir,year,inputs)
    output_dir.mkdir(parents=True,exist_ok=True)
    output=output_dir/f'page{page:02}-links.pdf'
    expected=link.EXPECTED[page]if year==2023 else(link.EXPECTED if link else[(URL2025,URL2025)])
    negative=[]
    with fitz.open(source_path)as source,fitz.open(proof_path)as proof:
        assert len(proof)==1
        src=source[page-1];target=proof[0]
        def execute(pdf,q):
            verified=audit_native_urls(src,target,q,expected)
            if link:
                rows=link.adjust_links(pdf.pages[0],src,target,q)
            else:
                rows=[join.move_reviewed_url_link(pdf.pages[0],src,q)]
            assert len(rows)==len(verified)
            for row,check in zip(rows,verified):
                assert row['uri']==check['uri']and same(row['source_rect_mupdf'],check['source_rect_mupdf'],.001)
                assert abs(row['dx']-check['dx'])<1e-8
                row['independent_native_url_glyph_audit']=check
            return rows
        with pikepdf.Pdf.open(proof_path)as pdf:
            before=annotation_records(pdf.pages[0]);rows=execute(pdf,qa)
            if year==2024:
                assert len(rows)==6 and rows[0]['dx']!=0 and rows[1]['dx']==rows[2]['dx']==0
                assert rows[0]['uri']==rows[1]['uri']
            elif year==2023:
                assert len(rows)==len(expected)and all(row['dx']!=0 for row in rows)
            else:assert len(rows)==1 and 0<rows[0]['dx']<100
            pdf.save(output,compress_streams=False)
        with pikepdf.Pdf.open(output)as pdf:after=check_saved_annotations(before,pdf.pages[0],rows)
        with fitz.open(output)as saved:
            assert target.get_texttrace()==saved[0].get_texttrace(),'Full visible trace changed after annotation-only save'
            assert join.traces(target)==join.traces(saved[0])
            a=join.pixels(target);b=join.pixels(saved[0]);assert a.shape==b.shape
            changed=int(np.any(a!=b,axis=2).sum());assert changed==0,'Annotation-only save changed visible pixels'
            for row in rows:
                matches=[v for v in saved[0].get_links()if v.get('uri')==row['uri']
                         and same(list(v['from']),row['expected_target_rect_mupdf'],.001)]
                assert len(matches)==1
                row.update(actual_target_rect_mupdf=list(matches[0]['from']),passed=True)
            trace_sha=hashlib.sha256(json.dumps(target.get_texttrace(),sort_keys=True).encode()).hexdigest()
            pixel_sha=hashlib.sha256(a.tobytes()).hexdigest()
        first=next(v for v in rows if v['dx']!=0)
        ref=first['independent_native_url_glyph_audit']['glyph_references'][0]
        index=ref['native_shift_index'];position=ref['shift_glyph_index'];assert index is not None
        def reject(name,mutate_qa=None,mutate_pdf=None):
            with pikepdf.Pdf.open(proof_path)as pdf:
                q=copy.deepcopy(qa)
                if mutate_qa:mutate_qa(q)
                if mutate_pdf:mutate_pdf(pdf.pages[0])
                try:execute(pdf,q)
                except (AssertionError,ValueError)as error:
                    negative.append(dict(check=name,rejected=True,error_type=type(error).__name__,reason=str(error)[:500]))
                else:raise AssertionError('Negative regression accepted: '+name)
        reject('missing native URL movement',lambda q:q['native_shifts'].pop(index))
        reject('URL glyph incorrectly hidden as prose',lambda q:q['selected_glyphs'].append(copy.deepcopy(ref['source_glyph'])))
        reject('duplicate/ambiguous URL movement',lambda q:q['native_shifts'].append(copy.deepcopy(q['native_shifts'][index])))
        reject('URL movement metadata has wrong original GID',lambda q:q['native_shifts'][index]['glyphs'][position].update(gid=-1))
        reject('nonfinite URL movement',lambda q:q['native_shifts'][index].update(dx=float('nan')))
        def wrong_rect(page_obj):
            a=find_annotation(page_obj,first,src);r=list(map(float,a['/Rect']));a['/Rect']=pikepdf.Array([r[0]+17,r[1],r[2]+17,r[3]])
        reject('correct URI with wrong original rectangle',mutate_pdf=wrong_rect)
        def wrong_uri(page_obj):find_annotation(page_obj,first,src)['/A']['/URI']=pikepdf.String(first['uri']+'-wrong')
        reject('wrong URI with correct original rectangle',mutate_pdf=wrong_uri)
        reject('unreviewed QuadPoints annotation',mutate_pdf=lambda pg:find_annotation(pg,first,src).__setitem__('/QuadPoints',pikepdf.Array([0,0,1,0,0,1,1,1])))
        if year==2024:
            stationary=rows[1]
            def wrong_shared_shift(page_obj):
                a=find_annotation(page_obj,stationary,src);r=list(map(float,a['/Rect']));dx=first['dx']
                a['/Rect']=pikepdf.Array([r[0]+dx,r[1],r[2]+dx,r[3]])
            reject('wrong shared-URI shift on stationary second rectangle',mutate_pdf=wrong_shared_shift)
        with pikepdf.Pdf.open(output)as pdf:
            pdf.pages[0].obj['/Annots'][0]['/Contents']=pikepdf.String('adversarial non-Rect change')
            try:check_saved_annotations(before,pdf.pages[0],rows)
            except AssertionError as error:negative.append(dict(check='non-Rect setting tampering after save',rejected=True,error_type='AssertionError',reason=str(error)))
            else:raise AssertionError('Saved annotation setting tampering accepted')
    for path,digest in inputs.items():assert sha(path)==digest,('Input/helper/program changed during regression',path)
    report=dict(schema='parameterized-private-ortvay-source-style-link-regression-v1',status='PASS',passed=True,year=year,page=page,
                proof_dir=str(proof_dir),output_dir=str(output_dir),engine_dir=str(engine_dir),
                logical_source=qa['source'],resolved_source_read_path=str(source_path),source_sha256=SOURCE_SHA[year],
                proof_sha256=sha(proof_path),layout_sha256=sha(layout_path),output_pdf=str(output),output_sha256=sha(output),
                ready_manifest=ready,program_path=str(Path(program).resolve()),program_sha256=sha(program),test_program_sha256=sha(program),
                core_program_path=str(Path(__file__).resolve()),core_program_sha256=sha(__file__),assembler_path=str(Path(join.__file__).resolve()),assembler_sha256=sha(join.__file__),
                helper_path=str(Path(link.__file__).resolve())if link else str(Path(join.__file__).resolve()),
                helper_sha256=sha(link.__file__)if link else sha(join.__file__),original_test_path=str(original_test),original_test_sha256=sha(original_test),
                links=rows,negative_regressions=[v['check']+' rejected'for v in negative],negative_regression_details=negative,changed_pixels=changed,pixel_scale=1.5,
                full_visible_trace_sha256=trace_sha,visible_pixel_sha256=pixel_sha,
                all_visible_glyph_geometry_identical=True,all_nonrect_annotation_settings_identical_after_save=True,
                annotation_P_same_page_semantics_verified=True,all_annotation_rectangles_checked_after_save=True,
                annotation_count=len(before),before_nonrect_semantics_sha256=hashlib.sha256(json.dumps([v['settings']for v in before],sort_keys=True).encode()).hexdigest(),
                after_nonrect_semantics_sha256=hashlib.sha256(json.dumps([v['settings']for v in after],sort_keys=True).encode()).hexdigest(),
                inputs_rehashed_after_run=inputs,no_input_or_frozen_file_written=True,no_existing_output_overwritten=True,
                runtime_dependency_files=[dict(role='independent_test_entry',path=str(Path(program).resolve()),sha256=sha(program)),
                                          dict(role='independent_test_core',path=str(Path(__file__).resolve()),sha256=sha(__file__))])
    if year==2025:
        # Preserve the legacy single-link audit schema as well as the new list.
        report.update(rows[0])
    report_path=output_dir/'regression.json';assert not report_path.exists()
    report_path.write_text(json.dumps(report,ensure_ascii=False,indent=2,allow_nan=False)+'\n','utf8')
    print(json.dumps(dict(status='PASS',year=year,page=page,links=len(rows),native_URL_glyphs=sum(v['independent_native_url_glyph_audit']['source_url_glyphs']for v in rows),
                         changed_pixels=changed,negative_cases=len(negative),report=str(report_path),report_sha256=sha(report_path),
                         program_sha256=sha(program),core_program_sha256=sha(__file__),assembler_sha256=sha(join.__file__)),ensure_ascii=False,indent=2))

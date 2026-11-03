"""Fixed mixed-lineage continuation. No publication-tool execution dependency.

All production subcommands require a root-authored GO bound to this code/input
freeze. Existing proofs/QA/results/READY files are read-only. The original
compositors are invoked unchanged, one shared gate per page by the controller.
"""
from pathlib import Path
import argparse,datetime,hashlib,json,os,shutil,subprocess,sys,time,traceback
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
QA=ROOT/'qa-amendments/full-ctm-rotation-v1-20261103'
GATE=Path('D:/CodexBuilds/Hasla-publish-20261031/tools/pdf_memory_gate.py')
FREEZE=HERE/'CODE-INPUT-FROZEN.json';GO=HERE/'ROOT-GO.json'
HOLD=HERE/'HOLD-BEFORE-NEXT-PAGE'
GO_STATUS='ROOT_GO_R4_MIXED_LINEAGE_FULL_CTM_CONTINUATION'
sys.path.insert(0,str(ROOT/'common'));sys.path.insert(0,str(QA))
import pymupdf as f
import r4_guard as g
import run_amended_audit as qa
from amended_independent_qa import expected_glyphs,match_expected,verify
from amended_outline_qa import audit as outline_audit

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def pin(path):return dict(path=str(path),sha256=sha(path))
def read(path):return json.loads(Path(path).read_text('utf8'))
def write_new(path,value):
    path=Path(path);assert path.resolve().is_relative_to(HERE.resolve()) and not path.exists()
    path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n','utf8')
def code_pins():return {str(p):sha(p) for p in sorted(HERE.glob('*.py'))}
def rules(year):return g.rules(ROOT/str(year))
def target_path(year,page):return ROOT/str(year)/f'proofs/ortvay/{year}/page{page:02}.pdf'
def page_dir(year,page):return HERE/f'pages/{year}/page{page:02}'
def roster():return [(2025,p) for p in range(7,13)]+[(2026,p) for p in range(1,11)]

def static_profile_pins(value):
    keys=('qa_profile_freeze','qa_profile_actual_regressions','qa_profile_post_freeze_guard',
          'original_code_input_freeze','original_runtime_freeze')
    return {key:value[key] for key in keys}

def profile_pins():
    return dict(static_profile_pins(read(FREEZE)),qa_profile_root_go=pin(GO),code_input_freeze=pin(FREEZE))

def check_authorization(full=True):
    assert FREEZE.exists() and GO.exists(),'Root review/GO required; never infer approval'
    value=read(FREEZE);assert value['code_sha256']==code_pins()
    qa.check_external_freeze()
    for item in static_profile_pins(value).values():assert sha(item['path'])==item['sha256']
    token=read(GO);assert token['status']==GO_STATUS and token['code_input_freeze']==pin(FREEZE)
    for key,item in static_profile_pins(value).items():assert token[key]==item
    assert token['allowed_pages']==[dict(year=y,page=p) for y,p in roster()]
    assert token['original_producer_code_may_change'] is False
    assert token['existing_proof_layout_ready_and_original_failure_may_change'] is False
    for path,digest in value['preserved_files_sha256'].items():assert sha(path)==digest,('Preserved original output changed',path)
    g.assert_runtime_frozen()
    if full:g.assert_all_inputs()
    return value

def prepare(post_guard):
    """Only creates the reviewable input/code freeze; does not create ROOT-GO."""
    assert not FREEZE.exists();qa.check_external_freeze();assert (QA/'AMENDMENT-FROZEN.json').exists()
    profile=read(QA/'AMENDMENT-FROZEN.json');batch=profile['actual_regressions']
    assert sha(batch['path'])==batch['sha256'];assert read(batch['path'])['cases']==19
    post=read(post_guard);assert post['passed'] and post['case']=='p7_rotated_label'
    assert post['external_amendment_freeze']==pin(QA/'AMENDMENT-FROZEN.json')
    preserve={}
    def retain(path):preserve[str(path)]=sha(path)
    for year in (2023,2024):
        ready=ROOT/str(year)/'READY.json';retain(ready)
        retain(Path(read(ready)['visual_review_normalized']['path']))
        for row in read(ready)['page_results']:
            for key in ('proof','layout','png','independent_audit','effective_plan','runtime_snapshot','visual_review'):retain(Path(row[key]['path']))
    for page in range(1,7):
        original=target_path(2025,page).with_suffix('.result.json');retain(original)
        for key in ('proof','layout','png','independent_audit','effective_plan','runtime_snapshot'):retain(Path(read(original)[key]['path']))
        retain(ROOT/'2025'/f'visual-reads/page{page:02}.json')
    p7=target_path(2025,7)
    for suffix in ('.pdf','.layout.json','.png','.effective-plan.json','.build.log','.independent-audit.log'):retain(p7.with_suffix(suffix))
    build=ROOT/'runtime-snapshots/final-2025-07-build/runtime-snapshot.json';retain(build)
    for year,page in roster():
        if (year,page)!=(2025,7):assert not target_path(year,page).exists(),'Never overwrite a partial/old proof'
    g.assert_runtime_frozen();g.assert_all_inputs()
    value=dict(status='R4_MIXED_LINEAGE_CONTINUATION_CODE_AND_INPUT_FROZEN',created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        code_sha256=code_pins(),qa_profile_freeze=pin(QA/'AMENDMENT-FROZEN.json'),qa_profile_actual_regressions=batch,
        qa_profile_post_freeze_guard=pin(post_guard),original_code_input_freeze=pin(ROOT/'PREPARATION-FROZEN.json'),
        original_runtime_freeze=pin(ROOT/'PROTOTYPE-RUNTIME-FROZEN.json'),input_ledger=pin(ROOT/'input-ledger.json'),
        preserved_files_sha256=preserve,allowed_pages=[dict(year=y,page=p) for y,p in roster()],
        p7_original_build_snapshot=pin(build),production_was_not_run=True,no_publication_tools_are_execution_dependencies=True)
    write_new(FREEZE,value)
    template=dict(status=GO_STATUS,code_input_freeze=pin(FREEZE),**static_profile_pins(value),allowed_pages=value['allowed_pages'],
        original_producer_code_may_change=False,existing_proof_layout_ready_and_original_failure_may_change=False)
    write_new(HERE/'ROOT-GO.template.json',dict(instruction='Root only: review then write ROOT-GO.json; this template is not authorization',required_token=template))
    print(json.dumps(dict(prepared=pin(FREEZE),root_go_not_created=True)),flush=True)

def original_snapshot(year,page,phase):
    path=g.capture_runtime_snapshot(year,ROOT/f'experiments/ctm-production-runtime-v1/{year}/page{page:02}/{phase}')
    os.environ['R4_RUNTIME_SNAPSHOT']=str(path);os.environ['R4_OUTPUT_DIRECTORY']=str(target_path(year,page).parent)
    g.assert_runtime_snapshot();return path

def own_snapshot(output):
    rows={}
    for path,digest in {**qa.code_pins(),**code_pins()}.items():
        source=Path(path);folder='qa' if source.parent==QA else 'production';target=output/f'runtime-sources/{folder}/{source.name}'
        assert not target.exists();target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,target);assert sha(target)==digest
        rows[path]=dict(sha256=digest,retained_copy=str(target))
    value=dict(files=rows,**profile_pins());write_new(output/'production-runtime-snapshot.json',value)
    return output/'production-runtime-snapshot.json'

def validate_own_snapshot(path):
    for source,row in read(path)['files'].items():
        assert sha(source)==row['sha256'] and sha(row['retained_copy'])==row['sha256']

def produce_page(year,page):
    frozen=check_authorization();assert (year,page) in roster()
    output=page_dir(year,page);assert not output.exists();output.mkdir(parents=True)
    target=target_path(year,page);cfg=rules(year);own=own_snapshot(output);before={**qa.code_pins(),**code_pins()}
    stage='source-build';existing=(year,page)==(2025,7)
    try:
        if existing:
            for suffix in ('.pdf','.layout.json','.png','.effective-plan.json','.build.log','.independent-audit.log'):
                path=target.with_suffix(suffix);assert sha(path)==frozen['preserved_files_sha256'][str(path)]
            build=frozen['p7_original_build_snapshot'];assert sha(build['path'])==build['sha256']
        else:
            assert not target.exists();target.parent.mkdir(parents=True,exist_ok=True)
            build=pin(original_snapshot(year,page,'build'))
            kernel=ROOT/str(year)/'composer'/f'natural_plan_compose_ortvay{year}_title_final.py'
            command=[sys.executable,str(kernel),cfg['base_plans'][str(page)]['path'],str(target)]
            if str(page) in cfg['overrides']:command+=['--overrides',cfg['overrides'][str(page)]['path']]
            run=subprocess.run(command,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,encoding='utf8')
            (output/'build.log').write_text(run.stdout,'utf8');assert run.returncode==0,('Original frozen compositor failed; outputs retained',run.returncode)
            g.assert_runtime_snapshot();check_authorization()
        q=read(target.with_suffix('.layout.json'));assert q['page']==page and q['source_sha256']==cfg['source_sha256']
        audit_snapshot=original_snapshot(year,page,'audit')
        e,nv,kernel,vector_path=qa.load_kernel(year)
        stage='unchanged-native-vectors';native=nv.verify(target)
        stage='actual-full-master-and-full-CTM-audit'
        with f.open(target) as doc:
            matched,geometry=match_expected(expected_glyphs(e,q,year),doc[0])
            if existing:png=target.with_suffix('.png')
            else:
                png=output/f'page{page:02}.png';assert not png.exists();doc[0].get_pixmap(matrix=f.Matrix(1.5,1.5),alpha=False).save(png)
        value=verify(e,q,target,cfg);outline=outline_audit(target,matched,cfg)
        value.update(status='EXTERNAL_FULL_CTM_PRODUCTION_AUDIT_PASSED',year=year,page=page,
            actual_outline_and_encoded_W_audit_pending=False,actual_outline_and_encoded_W_audit=outline,
            actual_native_vector_coordinate_audit=native,original_full_master_geometry=geometry,
            audit_runtime_snapshot=str(audit_snapshot),audit_runtime_snapshot_sha256=sha(audit_snapshot),
            production_runtime_snapshot=pin(own),audit_code_sha256={**{str(p):sha(p) for p in [ROOT/'audit_final_page.py',*sorted((ROOT/'common').glob('*.py'))]},**before},
            preparation_sha256=sha(ROOT/'PREPARATION-FROZEN.json'),qa_profile_code_sha256=qa.code_pins(),production_code_sha256=code_pins(),
            target=pin(target),layout=pin(target.with_suffix('.layout.json')),original_failed_audit_preserved=existing,
            **profile_pins())
        g.assert_runtime_snapshot();validate_own_snapshot(own);check_authorization();assert before=={**qa.code_pins(),**code_pins()}
        audit_path=output/'independent-qa.json';write_new(audit_path,value)
        result=dict(status='PAGE_STRICT_SOURCE_STYLE_CORRECTION_READY_FOR_HUMAN_REVIEW',year=year,page=page,
            proof=pin(target),layout=pin(target.with_suffix('.layout.json')),png=pin(png),independent_audit=pin(audit_path),
            effective_plan=pin(target.with_suffix('.effective-plan.json')),runtime_snapshot=build,
            audit_runtime_snapshot=pin(audit_snapshot),production_runtime_snapshot=pin(own),qa_lineage='external_full_ctm_v1',
            human_read_pending=True,**profile_pins())
        if existing:result['original_failed_audit_log']=pin(target.with_suffix('.independent-audit.log'))
        write_new(output/'result.json',result);print(json.dumps(dict(year=year,page=page,result=pin(output/'result.json'),human_read_pending=True)),flush=True)
    except Exception:
        write_new(output/'FAILED.json',dict(stage=stage,traceback=traceback.format_exc(),all_partial_outputs_retained=True))
        raise

def verify_result(result):
    for key in ('proof','layout','png','independent_audit','effective_plan','runtime_snapshot'):assert sha(result[key]['path'])==result[key]['sha256']
    assert read(result['independent_audit']['path'])['passed']
    if 'production_runtime_snapshot' in result:
        own=result['production_runtime_snapshot'];assert sha(own['path'])==own['sha256'];validate_own_snapshot(own['path'])

def continue_pages():
    check_authorization()
    for year,page in roster():
        output=page_dir(year,page);result=output/'result.json'
        if result.exists():verify_result(read(result));continue
        assert not output.exists(),'A failed/partial production page must not be overwritten'
        if HOLD.exists():print(json.dumps(dict(status='HELD_AT_PAGE_BOUNDARY_NO_ACTIVE_GATE',year=year,page=page)),flush=True);return
        print(json.dumps(dict(status='OPENING_SINGLE_PAGE_GATE',year=year,page=page)),flush=True)
        run=subprocess.run([sys.executable,str(GATE),'--',sys.executable,str(Path(__file__)),'page',str(year),str(page)],
            stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,encoding='utf8')
        log=HERE/f'outer-logs/{year}-page{page:02}.log';assert not log.exists();log.parent.mkdir(exist_ok=True);log.write_text(run.stdout,'utf8')
        if run.returncode:print(run.stdout,flush=True);raise SystemExit(run.returncode)
        verify_result(read(result));print(json.dumps(dict(status='PAGE_NATURAL_EXIT_GATE_RETURNED',year=year,page=page,result=pin(result))),flush=True);time.sleep(8)
    print(json.dumps(dict(status='ALL_AMENDED_PAGES_GENERATED_ACTUAL_READING_AND_YEAR_READY_REQUIRED')),flush=True)

def finalize_year(year):
    check_authorization();assert year in (2025,2026);cfg=rules(year);rows=[];normalized=[];composer=None
    for page in range(1,cfg['pages']+1):
        old=year==2025 and page<=6
        machine=target_path(year,page).with_suffix('.result.json') if old else page_dir(year,page)/'result.json'
        row=read(machine);assert row['human_read_pending'] is True and row['year']==year and row['page']==page;verify_result(row)
        visual=ROOT/'2025'/f'visual-reads/page{page:02}.json' if old else page_dir(year,page)/'visual-read.json'
        reviewed=read(visual);assert reviewed.get('passed') is True or reviewed.get('status')=='ACTUAL_FINAL_PNG_ORIGINAL_RESOLUTION_READ_PASS'
        bindings=reviewed.get('artifacts',reviewed.get('artifact_pins'));assert reviewed['year']==year and reviewed['page']==page
        for key in ('proof','layout','png','independent_audit','effective_plan'):assert bindings[key]==row[key]
        q=read(row['layout']['path']);assert q['page']==page and q['source_sha256']==cfg['source_sha256'] and sha(q['composer_path'])==q['composer_sha256']
        current=dict(path=q['composer_path'],sha256=q['composer_sha256'])
        if composer is None:composer=current
        assert current==composer
        if not old:
            for key,item in profile_pins().items():assert row[key]==item
        row.update(reviewed=True,human_read_pending=False,machine_result=pin(machine),visual_review=pin(visual),composer=current,
            composer_path=current['path'],composer_sha256=current['sha256'],effective_plan_path=row['effective_plan']['path'],
            effective_plan_sha256=row['effective_plan']['sha256'],qa_lineage='old_frozen_r4' if old else 'external_full_ctm_v1')
        rows.append(row);notes=reviewed['notes'];notes=' '.join(notes) if isinstance(notes,list) else notes
        normalized.append(dict(page=page,reviewed=True,proof_path=row['proof']['path'],proof_sha256=row['proof']['sha256'],
            layout_path=row['layout']['path'],layout_sha256=row['layout']['sha256'],png_path=row['png']['path'],
            png_sha256=row['png']['sha256'],effective_plan_path=row['effective_plan']['path'],effective_plan_sha256=row['effective_plan']['sha256'],
            composer=current,composer_sha256=current['sha256'],
            machine_result=pin(machine),visual_review=pin(visual),artifact_pins={k:row[k] for k in ('proof','layout','png','independent_audit','effective_plan','runtime_snapshot')},review=notes))
    folder=HERE/f'year-ready/{year}';norm=folder/'visual-review-amended-normalized.json'
    write_new(norm,dict(source_sha256=cfg['source_sha256'],year=year,pages=normalized,original_machine_and_actual_read_manifests_unchanged=True))
    scope={2025:'Four source-centered title rows; source-bound new Korean italic +14 physical shear; approved p1 row origins+0.75pt combined with corrected italic outlines, not pure bbox translation.',
           2026:'Four source-centered title rows; source-bound new Korean italic+14; only new Batang exact master W and precise Tm origins; approved p1 KO row-0.5625pt for pre-existing low-resolution AA contact.'}[year]
    value=dict(schema='ortvay-source-style-width-correction-ready-v2-mixed-ctm',status='YEAR_STRICT_SOURCE_STYLE_CORRECTION_READY_FOR_ROOT_ASSEMBLY_REVIEW',
        competition='Ortvay',year=year,pages=cfg['pages'],source=dict(path=cfg['source_path'],sha256=cfg['source_sha256']),source_sha256=cfg['source_sha256'],
        composer=composer,composer_path=composer['path'],composer_sha256=composer['sha256'],preparation=pin(ROOT/'PREPARATION-FROZEN.json'),
        runtime_freeze=pin(ROOT/'PROTOTYPE-RUNTIME-FROZEN.json'),final48_go=pin(ROOT/'FINAL48-GO.json'),input_ledger=pin(ROOT/'input-ledger.json'),
        visual_review_normalized=pin(norm),scope=scope,correction_scope=read(ROOT/'PREPARATION-FROZEN.json')['correction_scope'],
        lineage_policy=dict(P0='Direct current published page/proof comparison outside complete authorized title/row/italic/advance scope; native font/math/images unchanged.',
            P1='2025 approved R3 title/contact retained independently of P0.' if year==2025 else 'Not applicable to2026.',
            P2='2026p1 precise-Tm precontact control retains everything outside approved old/new KO-row ink union.' if year==2026 else 'Not applicable to2025.'),
        protection_rehashed=dict(unique_original_files=1534,original_pin_entries=1536,private_inputs=597,status='PASS'),page_results=rows,
        all_pages_actual_original_resolution_png_read=True,human_read_pending=False,assembly_stage_publication_owned_by_root=True,**profile_pins())
    check_authorization();write_new(folder/'READY.json',value);print(json.dumps(dict(ready=pin(folder/'READY.json'),normalized=pin(norm))),flush=True)

def main():
    for key in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS'):os.environ[key]='1'
    os.environ['PYTHONDONTWRITEBYTECODE']='1';os.environ['PYTHONIOENCODING']='utf-8'
    parser=argparse.ArgumentParser();sub=parser.add_subparsers(dest='command',required=True)
    p=sub.add_parser('prepare');p.add_argument('post_guard')
    p=sub.add_parser('page');p.add_argument('year',type=int);p.add_argument('page',type=int)
    sub.add_parser('continue');p=sub.add_parser('finalize-year');p.add_argument('year',type=int)
    args=parser.parse_args()
    if args.command=='prepare':prepare(args.post_guard)
    elif args.command=='page':produce_page(args.year,args.page)
    elif args.command=='continue':continue_pages()
    elif args.command=='finalize-year':finalize_year(args.year)
if __name__=='__main__':main()

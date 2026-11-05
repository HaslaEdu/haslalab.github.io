"""SDK 0.31 flattening regression, synthetic values only; no SDK/model imports."""
import ast,inspect,io,json,unittest
from contextlib import redirect_stdout
from pathlib import Path
from types import SimpleNamespace
import private_qwq_gpu_eval as worker
import private_qwq_gpu_run as parent
from private_qwq_bootstrap_diagnostic import bootstrap_diagnostic_source

class FlatteningSummary(dict):
    def update(self,rows):
        def flatten(key,value):
            if type(value) is dict and value:
                for child,item in value.items():flatten(key+'.'+child,item)
            else:self[key]=value
        for key,value in rows.items():flatten(key,value)

def calls(source):
    return [n for n in ast.walk(ast.parse(source)) if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and n.func.attr=='update' and isinstance(n.func.value,ast.Attribute) and n.func.value.attr=='summary']
def execute_call(call,summary,**context):
    statement=ast.fix_missing_locations(ast.Expression(call))
    eval(compile(statement,'<actual-summary-callsite>','eval'),{'run':SimpleNamespace(summary=summary),'canonical':worker.canonical,'json':json,**context})
def fixtures():
    run_id='41970000000';commit='a'*40
    bootstrap={'version':1,'run_id':run_id,'code_commit':commit,'status':'passed','stages':[{'stage':s,'status':'passed','exit_code':0,'exception_type':None} for s in ('core_compare','module_import','GPU_check')],
               'artifact':parent.ENTITY+'/'+parent.resume.PROJECT+'/hasla-qwq-bootstrap-'+run_id+':v0','files':[{'name':n,'bytes':10,'sha256':'0'*64} for n in ('diagnostics.json','traceback.txt')],'model_calls':0}
    progress={'phase':'evaluating','case_id':'momentum_energy','mode':'base','completed_attempts':1,'paired_completed_cases':0,'evaluation_only':True,'weights_updated':False}
    result={'version':1,'kind':'private_qwq_gpu_evaluation_result','run_id':run_id,'status':'uploaded','execution_status':'completed','artifact':parent.ENTITY+'/'+parent.resume.PROJECT+'/hasla-qwq-gpu-comparison-'+run_id+':v0',
            'files':[{'name':n,'bytes':10,'sha256':'0'*64} for n in ('report.json','metadata.json')],'evaluation_only':True,'optimizer_steps':0,'weights_updated':False,'paired_completed_cases':8,'case_set_sha256':worker.CASE_SHA,
            'comparison_plan_sha256':worker.digest(worker.canonical(worker.evaluation_plan())),'metrics':{mode:{'paired_passed_cases':7,'paired_correct_numeric_quantities':9,'abstention_passed':True,'failures':{'length':1}} for mode in ('base','adapted')},'raw_reasoning_included':False}
    return run_id,commit,bootstrap,progress,result

class Tests(unittest.TestCase):
    def test_parent_real_default_emitter_preserves_kind_without_duplicate_argument(self):
        _,_,_,_,result=fixtures()
        with self.assertRaises(TypeError):parent.cloud.safe_event('private_qwq_gpu_evaluation',**result)
        self.assertIs(inspect.signature(parent.run).parameters['emit'].default,parent.emit_event)
        self.assertIs(inspect.signature(parent.cleanup).parameters['emit'].default,parent.emit_event)
        output=io.StringIO()
        with redirect_stdout(output):parent.emit_event('private_qwq_gpu_evaluation',**result)
        self.assertEqual(json.loads(output.getvalue()),{'event':'private_qwq_gpu_evaluation',**result})

    def test_actual_bootstrap_callsite_survives_flattening_and_existing_parent_reader(self):
        run_id,commit,bootstrap,_,_=fixtures();sites=calls(bootstrap_diagnostic_source());self.assertEqual(len(sites),1)
        summary=FlatteningSummary();execute_call(sites[0],summary,result=bootstrap)
        key='private_qwq_gpu_bootstrap_result_json';self.assertEqual(set(summary),{key});self.assertIs(type(summary[key]),str)
        self.assertEqual(parent.safe_bootstrap_result(summary,run_id,commit),bootstrap)
        self.assertEqual(summary[key],worker.canonical(bootstrap).decode())

    def test_both_actual_worker_callsites_store_four_scalar_json_values(self):
        run_id,_,_,progress,result=fixtures();sites=calls(Path(worker.__file__).read_text());self.assertEqual(len(sites),2)
        summary=FlatteningSummary();execute_call(sites[0],summary,safe=progress)
        self.assertEqual(parent.safe_progress(summary)['completed_attempts'],1)
        execute_call(sites[1],summary,result=result,metadata={'paired_completed_cases':8})
        self.assertEqual(set(summary),{'private_qwq_gpu_progress','private_qwq_gpu_result_json'})
        self.assertTrue(all(type(value) is str for value in summary.values()))
        parsed=parent.resume._json(summary['private_qwq_gpu_result_json']);self.assertEqual(worker.validate_result(parsed,run_id),result)
        self.assertEqual(parent.safe_progress(summary)['phase'],'uploaded')
        self.assertEqual(parent.safe_progress(summary)['paired_completed_cases'],8)

    def test_old_dict_is_demonstrably_flattened_and_nonfinite_serialization_rejects(self):
        _,_,_,progress,_=fixtures();old=FlatteningSummary();old.update({'private_qwq_gpu_progress':progress})
        self.assertNotIn('private_qwq_gpu_progress',old);self.assertIn('private_qwq_gpu_progress.phase',old)
        new=FlatteningSummary();site=calls(Path(worker.__file__).read_text())[0]
        with self.assertRaises(ValueError):execute_call(site,new,safe={**progress,'completed_attempts':float('nan')})
        self.assertFalse(new)

if __name__=='__main__':unittest.main()

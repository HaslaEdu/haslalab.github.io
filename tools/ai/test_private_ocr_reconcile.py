import json
from types import SimpleNamespace
import unittest
import private_ocr_reconcile as r


class Clock:
    def __init__(self):self.value=0
    def __call__(self):return self.value
    def sleep(self,seconds):self.value+=seconds


class ReconciliationTests(unittest.TestCase):
    def run_fixture(self,body,**kwargs):
        calls=[];clock=Clock()
        def get(url,**options):
            calls.append((url,options));clock.value+=1
            return SimpleNamespace(status_code=200,content=json.dumps(body).encode(),json=lambda:body,close=lambda:None)
        event=r.observe('123','private-batch',{'RUNPOD_API_KEY':'fixture'},get=get,clock=clock,sleep=clock.sleep,**kwargs)
        return event,calls,clock

    def test_two_spaced_absences_never_release_money_or_claim_deletion(self):
        event,calls,clock=self.run_fixture({'pods':[]})
        self.assertEqual(len(calls),2);self.assertGreaterEqual(clock.value,17)
        self.assertTrue(event['absence_observed_twice']);self.assertFalse(event['reservation_release_authorized'])
        self.assertFalse(event['creation_attempted']);self.assertFalse(event['deletion_attempted'])
        self.assertTrue(all(url=='https://api.runpod.io/v2/pods' and options['allow_redirects'] is False for url,options in calls))

    def test_foreign_pods_never_appear_in_output(self):
        event,_,_=self.run_fixture({'pods':[{'id':'foreign','name':'other-private-job','env':{'SECRET':'do-not-print'}},
            {'id':'target','name':'hasla-private-ocr-batch-123','gpu':{'id':'NVIDIA L40S','count':1},'cost':1.09}]})
        self.assertFalse(event['absence_observed_twice']);self.assertEqual(event['observations'][0]['matched_pods'],1)
        self.assertNotIn('foreign',json.dumps(event));self.assertNotIn('do-not-print',json.dumps(event))

    def test_incomplete_or_unrecognized_pagination_never_proves_absence(self):
        for body in ({'pods':[],'hasMore':True},{'pods':[],'total':1},
                     {'pods':[],'pagination':{'offset':1}},{'pods':[],'next_page_token':'x'}):
            with self.subTest(body=body),self.assertRaises(r.ObservationError):self.run_fixture(body)

    def test_scope_cannot_be_arbitrary_prefix_or_non_ascii_id(self):
        for run,scope in [('１２３','private-batch'),('123','training'),('../123','private-batch')]:
            with self.assertRaises(r.ObservationError):r.observe(run,scope,{})

    def test_model_credential_rejected_before_network(self):
        with self.assertRaisesRegex(r.ObservationError,'unexpected_credential'):
            r.inventory({'RUNPOD_API_KEY':'fixture','WANDB_API_KEY':'forbidden'},get=lambda *a,**kw:self.fail('network'))


if __name__=='__main__':unittest.main()

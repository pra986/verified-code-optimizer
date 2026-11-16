import copy
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import MagicMock,patch
from fastapi.testclient import TestClient
from optimizer.app import create_app
from optimizer.provider import generate
from optimizer.runner import run_benchmark,execute,integer_output,distribution,RunError
from optimizer.storage import Reports
from optimizer.workload import reference,FIXTURES,CPP_SOURCE,CANDIDATES

class WorkloadTests(unittest.TestCase):
    def test_oracle_small(self):
        for n in [0,1,2,7,31,999]:self.assertEqual(reference(n),sum(i*i for i in range(1,n+1))%1000000007)
    def test_boundary(self):self.assertEqual(reference(1000000),163183)
    def test_oracle_rejects_out_of_contract(self):
        for n in [-1,1000001,True,'3',1.5]:
            with self.subTest(n=n),self.assertRaises(ValueError):reference(n)
    def test_fixtures_include_boundaries(self):self.assertIn(0,FIXTURES);self.assertIn(1000000,FIXTURES)
    def test_integer_output(self):self.assertEqual(integer_output(subprocess.CompletedProcess([],0,'12\n','')),12)
    def test_bad_output(self):
        for code,text in [(1,'12'),(0,''),(0,'1 2'),(0,'NaN'),(0,'1.0'),(0,'-1')]:
            with self.subTest(text=text),self.assertRaises(RunError):integer_output(subprocess.CompletedProcess([],code,text,''))
    def test_distribution(self):
        d=distribution([1,2,5]);self.assertEqual(d['median_ms'],2);self.assertEqual(d['min_ms'],1);self.assertEqual(d['max_ms'],5);self.assertGreater(d['population_stdev_ms'],0)
    def test_bad_runner_arguments(self):
        for args in [('custom',1,3),('correct',-1,3),('correct',True,3),('correct',1,2),('correct',1,10)]:
            with self.subTest(args=args),self.assertRaises(RunError):run_benchmark(*args)
    def test_compiler_missing(self):
        with patch('optimizer.runner.shutil.which',return_value=None),self.assertRaises(RunError) as e:run_benchmark('correct',1,3)
        self.assertEqual(e.exception.status,503)
    def test_timeout(self):
        with tempfile.TemporaryDirectory() as d,patch('optimizer.runner.subprocess.run',side_effect=subprocess.TimeoutExpired('fixture',1)),self.assertRaises(RunError) as e:execute([sys.executable],d)
        self.assertEqual(e.exception.status,408)
    def test_server_secret_not_in_child(self):
        with tempfile.TemporaryDirectory() as d,patch.dict(os.environ,{'OPENAI_API_KEY':'must-not-forward','OPTIMIZER_FAKE_SECRET':'hidden'}):
            result,_=execute([sys.executable,'-c','import os; print(os.getenv("OPENAI_API_KEY")); print(os.getenv("OPTIMIZER_FAKE_SECRET"))'],d)
        self.assertEqual(result.stdout.strip(),'None\nNone')
    @unittest.skipUnless(sys.platform.startswith('linux'),'Linux resource contract')
    def test_limits_in_child(self):
        with tempfile.TemporaryDirectory() as d:
            result,_=execute([sys.executable,'-c','import resource; print(resource.getrlimit(resource.RLIMIT_CPU)[0]);print(resource.getrlimit(resource.RLIMIT_AS)[0])'],d)
        self.assertEqual(result.stdout.strip(),'8\n1073741824')

class CompilerIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.good=run_benchmark('correct',12345,3);cls.wrong=run_benchmark('wrong',12345,3);cls.broken=run_benchmark('compile-error',12345,3)
    def test_good_matches_oracle(self):
        self.assertEqual(self.good['status'],'verified_fixture_agreement');self.assertTrue(all(f['passed'] for f in self.good['fixtures']))
    def test_requested_input_checked(self):self.assertIn(12345,[f['n'] for f in self.good['fixtures']])
    def test_raw_samples(self):
        for name in ['python','cpp']:
            self.assertEqual(len(self.good['timing'][name]['samples_ms']),3);self.assertTrue(all(x>0 for x in self.good['timing'][name]['samples_ms']))
    def test_ratio_matches_samples(self):self.assertEqual(self.good['timing']['python_over_cpp_median_ratio'],self.good['timing']['python']['median_ms']/self.good['timing']['cpp']['median_ms'])
    def test_wrong_rejected_before_timing(self):self.assertEqual(self.wrong['status'],'correctness_failed');self.assertIsNone(self.wrong['timing']);self.assertTrue(any(not f['passed'] for f in self.wrong['fixtures']))
    def test_compile_failure(self):self.assertEqual(self.broken['status'],'compile_failed');self.assertIsNone(self.broken['timing']);self.assertEqual(self.broken['fixtures'],[]);self.assertNotEqual(self.broken['compile']['exit_code'],0)
    def test_sources_identified(self):self.assertEqual(self.good['cpp_source_sha256'],hashlib.sha256(CPP_SOURCE.encode()).hexdigest())
    def test_environment_evidence(self):
        self.assertIn('-O2',self.good['environment']['compiler_flags']);self.assertIn('g++',self.good['environment']['compiler']);self.assertIn('not a sandbox',' '.join(self.good['limitations']))

FAKE={'candidate':'correct','candidate_label':'Mock','n':7,'repeats':3,'status':'verified_fixture_agreement','fixtures':[],'timing':None}
class StorageTests(unittest.TestCase):
    def setUp(self):self.tmp=tempfile.TemporaryDirectory();self.store=Reports(self.tmp.name)
    def tearDown(self):self.tmp.cleanup()
    def test_persistent_report(self):
        r=self.store.save(FAKE);self.assertEqual(Reports(self.tmp.name).get(r['id']),r)
    def test_recent_excludes_full_payload(self):
        r=self.store.save(dict(FAKE,sources={'cpp':'private report text'}));self.assertNotIn('sources',self.store.recent()[0]);self.assertEqual(self.store.recent()[0]['id'],r['id'])
    def test_sql_injection_id(self):
        self.store.save(FAKE)
        with self.assertRaises(RunError):self.store.get("' OR 1=1 --")
        self.assertEqual(len(self.store.recent()),1)
    def test_missing_report(self):
        with self.assertRaises(RunError) as e:self.store.get('missing')
        self.assertEqual(e.exception.status,404)

class ApiTests(unittest.TestCase):
    def setUp(self):self.tmp=tempfile.TemporaryDirectory();self.client=TestClient(create_app(self.tmp.name,runner=lambda *_:copy.deepcopy(FAKE)))
    def tearDown(self):self.client.close();self.tmp.cleanup()
    def test_health_ui(self):self.assertEqual(self.client.get('/api/health').status_code,200);self.assertIn('Verified Code Optimizer',self.client.get('/').text)
    def test_fixed_source_endpoint(self):
        r=self.client.get('/api/workload').json();self.assertEqual(set(r['candidates']),set(CANDIDATES));self.assertEqual(r['candidates']['correct']['source'],CPP_SOURCE)
    def test_report_flow(self):
        r=self.client.post('/api/benchmark',json={}).json();base='/api/reports/'+r['id'];self.assertEqual(self.client.get(base).json(),r);download=self.client.get(base+'/download');self.assertEqual(download.json(),r);self.assertIn('attachment',download.headers['content-disposition'])
    def test_custom_code_rejected(self):
        for body in [{'code':'print(1)'},{'candidate':'custom'},{'command':'whoami'},{'source':'int main(){}'}]:
            self.assertEqual(self.client.post('/api/benchmark',json=body).status_code,422)
    def test_strict_input_bounds(self):
        for body in [{'n':True},{'n':'4'},{'n':4.5},{'n':-1},{'n':1000001},{'repeats':2},{'repeats':10}]:
            with self.subTest(body=body):self.assertEqual(self.client.post('/api/benchmark',json=body).status_code,422)
    def test_cross_origin(self):self.assertEqual(self.client.post('/api/benchmark',json={},headers={'Origin':'https://other.example'}).status_code,403)
    def test_same_origin(self):self.assertEqual(self.client.post('/api/benchmark',json={},headers={'Origin':'http://testserver'}).status_code,200)
    def test_untrusted_host(self):self.assertEqual(self.client.get('/',headers={'Host':'other.example'}).status_code,400)
    def test_json_required(self):self.assertEqual(self.client.post('/api/benchmark',content='{}').status_code,415)
    def test_body_limit(self):self.assertEqual(self.client.post('/api/benchmark',content=' '*4097,headers={'Content-Type':'application/json'}).status_code,413)
    def test_missing(self):self.assertEqual(self.client.get('/api/reports/missing').status_code,404)
    def test_generation_extra_body_rejected(self):self.assertEqual(self.client.post('/api/generate',json={'code':'x'}).status_code,400)
    def test_generation_is_review_only(self):
        with TestClient(create_app(self.tmp.name,generator=lambda:{'code':'untrusted','execution':'not_executed'})) as c:
            self.assertEqual(c.post('/api/generate',json={}).json()['execution'],'not_executed');self.assertEqual(c.get('/api/reports').json()['reports'],[])
    def test_run_gate(self):
        entered=threading.Event();release=threading.Event()
        def runner(*_):entered.set();release.wait(5);return copy.deepcopy(FAKE)
        with TestClient(create_app(self.tmp.name,runner=runner)) as c,ThreadPoolExecutor(max_workers=1) as pool:
            future=pool.submit(c.post,'/api/benchmark',json={});self.assertTrue(entered.wait(5))
            try:self.assertEqual(c.post('/api/benchmark',json={}).status_code,429)
            finally:release.set()
            self.assertEqual(future.result(timeout=5).status_code,200)
    def test_failed_run_releases_gate(self):
        runner=MagicMock(side_effect=[RunError('Simulated failure',502),copy.deepcopy(FAKE)])
        with TestClient(create_app(self.tmp.name,runner=runner)) as c:
            self.assertEqual(c.post('/api/benchmark',json={}).status_code,502);self.assertEqual(c.post('/api/benchmark',json={}).status_code,200)

class ProviderTests(unittest.TestCase):
    def test_unconfigured(self):
        with patch.dict(os.environ,{},clear=True),self.assertRaises(RunError) as e:generate()
        self.assertEqual(e.exception.status,503)
    def test_generation_contract(self):
        mock=MagicMock();mock.__enter__.return_value=mock;mock.post.return_value.json.return_value={'choices':[{'message':{'content':'int main() {}'}}]}
        with patch.dict(os.environ,{'OPENAI_API_KEY':'fake','OPENAI_MODEL':'fake-model'}),patch('optimizer.provider.httpx.Client',return_value=mock):r=generate()
        self.assertEqual(r['execution'],'not_executed');self.assertIn('cannot be submitted',r['notice']);self.assertIn('argv',mock.post.call_args.kwargs['json']['messages'][0]['content'])
    def test_provider_failure_sanitized(self):
        mock=MagicMock();mock.__enter__.return_value=mock;mock.post.return_value.json.return_value={}
        with patch.dict(os.environ,{'OPENAI_API_KEY':'fake','OPENAI_MODEL':'fake-model'}),patch('optimizer.provider.httpx.Client',return_value=mock),self.assertRaises(RunError) as e:generate()
        self.assertEqual(e.exception.status,502);self.assertNotIn('fake',e.exception.detail)
    def test_oversized_output_rejected(self):
        mock=MagicMock();mock.__enter__.return_value=mock;mock.post.return_value.json.return_value={'choices':[{'message':{'content':'x'*64001}}]}
        with patch.dict(os.environ,{'OPENAI_API_KEY':'fake','OPENAI_MODEL':'fake-model'}),patch('optimizer.provider.httpx.Client',return_value=mock),self.assertRaises(RunError):generate()

if __name__=='__main__':unittest.main()

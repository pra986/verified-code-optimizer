"""Run only packaged trusted fixtures; resource limits are not a security sandbox."""
import hashlib
import os
from pathlib import Path
import platform
import shutil
import statistics
import subprocess
import sys
import tempfile
import time
from .workload import PYTHON_SOURCE,CANDIDATES,FIXTURES,reference

FLAGS = ['-std=c++17','-O2','-Wall','-Wextra','-pedantic']
class RunError(Exception):
    def __init__(self,message,status=400):self.detail=message;self.status=status;super().__init__(message)

def limits():
    # Called only by a fresh interpreter, never preexec_fn inside a web-server thread.
    if sys.platform.startswith('linux'):
        import resource
        resource.setrlimit(resource.RLIMIT_CPU,(8,8))
        resource.setrlimit(resource.RLIMIT_AS,(1024**3,1024**3))
        resource.setrlimit(resource.RLIMIT_FSIZE,(1024**2,1024**2))
        resource.setrlimit(resource.RLIMIT_CORE,(0,0))

LAUNCHER = '''import os,sys
from optimizer.runner import limits
limits()
os.execv(sys.argv[1],sys.argv[1:])
'''

def execute(command,directory,timeout=15):
    """Only callers inside run_benchmark construct command; no API command input."""
    env={'PATH':os.defpath,'LANG':'C','LC_ALL':'C','HOME':str(directory),'TMPDIR':str(directory)}
    # -c imports this installed package before changing cwd; developer source path
    # is explicitly supplied for editable runs, without forwarding server secrets.
    env['PYTHONPATH']=str(Path(__file__).resolve().parent.parent)
    started=time.perf_counter_ns()
    try:
        result=subprocess.run([sys.executable,'-c',LAUNCHER,*map(str,command)],cwd=directory,env=env,capture_output=True,text=True,timeout=timeout,check=False)
    except subprocess.TimeoutExpired as exc:raise RunError('A trusted fixture exceeded its wall-clock timeout.',408) from exc
    elapsed=(time.perf_counter_ns()-started)/1_000_000
    return result,elapsed

def integer_output(result):
    if result.returncode!=0:raise RunError('A trusted benchmark process failed; timing was not reported.',502)
    text=result.stdout.strip()
    if not text or len(text)>30 or not text.isdecimal():raise RunError('Benchmark output must be one nonnegative integer.',502)
    return int(text)

def distribution(samples):
    return {'samples_ms':samples,'median_ms':statistics.median(samples),'min_ms':min(samples),'max_ms':max(samples),'population_stdev_ms':statistics.pstdev(samples)}

def run_benchmark(candidate,n,repeats):
    if candidate not in CANDIDATES:raise RunError('Choose a packaged candidate.')
    if type(n) is not int or not 0<=n<=1_000_000:raise RunError('Use n from 0 to 1000000.')
    if type(repeats) is not int or not 3<=repeats<=9:raise RunError('Use 3 to 9 repeated measurements.')
    compiler=shutil.which('g++')
    if not compiler:raise RunError('g++ is not installed. Install a C++17 toolchain; no benchmark was run.',503)
    source=CANDIDATES[candidate]['source']
    report={'candidate':candidate,'candidate_label':CANDIDATES[candidate]['label'],'workload':'sum(i*i for i in 1..n) modulo 1000000007','n':n,'repeats':repeats,'tolerance':{'absolute':0,'relative':0,'comparison':'exact integer equality'},'python_source_sha256':hashlib.sha256(PYTHON_SOURCE.encode()).hexdigest(),'cpp_source_sha256':hashlib.sha256(source.encode()).hexdigest(),'sources':{'python':PYTHON_SOURCE,'cpp':source},'fixtures':[],'status':'pending','timing':None,'limitations':['Fixtures establish agreement only for tested inputs, not a proof of universal equivalence.','End-to-end process timings include interpreter/launcher/startup and IPC; these are not isolated kernel timings.','Fixed reviewed programs only. Resource limits do not isolate filesystem or network; this is not a sandbox for untrusted code.','No live model accuracy or universal speedup is claimed.']}
    with tempfile.TemporaryDirectory(prefix='optimizer-') as tmp:
        root=Path(tmp);py=root/'baseline.py';cpp=root/'candidate.cpp';exe=root/'candidate'
        py.write_text(PYTHON_SOURCE);cpp.write_text(source)
        version,_=execute([compiler,'--version'],root)
        report['environment']={'platform':platform.platform(),'machine':platform.machine(),'processor':platform.processor() or 'Not reported','logical_cpus':os.cpu_count(),'python_version':platform.python_version(),'compiler':version.stdout.splitlines()[0] if version.returncode==0 and version.stdout else 'Unknown','compiler_flags':FLAGS,'timer':'time.perf_counter_ns','timing_scope':'subprocess wall-clock, including common resource-limit launcher','resource_limits':'Linux: 8 CPU seconds, 1 GiB address space, 1 MiB output files, no core dump; other platforms: wall timeout only','execution_policy':'packaged trusted programs only; no arbitrary code execution'}
        compiled,elapsed=execute([compiler,*FLAGS,str(cpp),'-o',str(exe)],root)
        report['compile']={'exit_code':compiled.returncode,'wall_ms':elapsed,'stderr':compiled.stderr[:12000]}
        if compiled.returncode!=0:
            report['status']='compile_failed';return report
        # Include requested timing input in correctness, even if absent from fixtures.
        for size in dict.fromkeys([*FIXTURES,n]):
            expected=reference(size)
            baseline=integer_output(execute([sys.executable,str(py),str(size)],root)[0])
            optimized=integer_output(execute([str(exe),str(size)],root)[0])
            report['fixtures'].append({'n':size,'expected':expected,'python':baseline,'cpp':optimized,'passed':expected==baseline==optimized})
        if not all(f['passed'] for f in report['fixtures']):
            report['status']='correctness_failed';return report
        # Warm up both processes once; alternate measurement order to reduce drift.
        for command in [[sys.executable,str(py),str(n)],[str(exe),str(n)]]:integer_output(execute(command,root)[0])
        samples={'python':[],'cpp':[]}
        for iteration in range(repeats):
            for name in (['python','cpp'] if iteration%2==0 else ['cpp','python']):
                command=[sys.executable,str(py),str(n)] if name=='python' else [str(exe),str(n)]
                result,ms=execute(command,root)
                if integer_output(result)!=reference(n):
                    report['status']='timing_output_failed';report['timing']=None;return report
                samples[name].append(ms)
        report['timing']={name:distribution(values) for name,values in samples.items()}
        report['timing']['python_over_cpp_median_ratio']=report['timing']['python']['median_ms']/report['timing']['cpp']['median_ms']
        report['status']='verified_fixture_agreement'
        return report

import json
import os
from pathlib import Path
import shutil
import threading
from typing import Literal
from fastapi import FastAPI,Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import HTMLResponse,JSONResponse,Response
from pydantic import BaseModel,ConfigDict,Field
from starlette.middleware.trustedhost import TrustedHostMiddleware
from .runner import run_benchmark,RunError
from .provider import generate
from .storage import Reports
from .workload import PYTHON_SOURCE,CANDIDATES,FIXTURES

class Benchmark(BaseModel):
    model_config=ConfigDict(extra='forbid',strict=True)
    candidate:Literal['correct','wrong','compile-error']='correct'
    n:int=Field(default=100000,ge=0,le=1000000)
    repeats:int=Field(default=5,ge=3,le=9)

def create_app(directory=None,runner=None,generator=None):
    app=FastAPI(title='Verified Code Optimizer',version='0.1.0')
    reports=Reports(directory or os.getenv('OPTIMIZER_DATA_DIR','.data'));gate=threading.BoundedSemaphore(1)
    app.add_middleware(TrustedHostMiddleware,allowed_hosts=os.getenv('TRUSTED_HOSTS','127.0.0.1,localhost,testserver').split(','))
    @app.middleware('http')
    async def boundary(request,call_next):
        if request.method=='POST':
            if request.headers.get('origin') and request.headers['origin']!=f'{request.url.scheme}://{request.headers.get("host")}':return JSONResponse({'detail':'Cross-origin writes are not allowed.'},status_code=403)
            if request.headers.get('content-type','').split(';')[0]!='application/json':return JSONResponse({'detail':'Send application/json.'},status_code=415)
            # Enforce the limit for chunked requests too, before schema decoding.
            body=await request.body()
            if len(body)>4096:return JSONResponse({'detail':'Request body exceeds 4096 bytes.'},status_code=413)
        response=await call_next(request);response.headers['Cache-Control']='no-store';response.headers['X-Content-Type-Options']='nosniff';return response
    @app.exception_handler(RunError)
    async def rule(request,exc):return JSONResponse({'detail':exc.detail},status_code=exc.status)
    @app.exception_handler(RequestValidationError)
    async def bad(request,exc):return JSONResponse({'detail':'Invalid fields: choose a packaged candidate, n 0–1000000 and repeats 3–9. No code or command input is accepted.'},status_code=422)
    @app.get('/',response_class=HTMLResponse)
    def home():return (Path(__file__).parent/'static/index.html').read_text()
    @app.get('/api/health')
    def health():return {'status':'ok','compiler_available':bool(shutil.which('g++')),'generation_configured':bool(os.getenv('OPENAI_API_KEY') and os.getenv('OPENAI_MODEL'))}
    @app.get('/api/workload')
    def workload():return {'python':PYTHON_SOURCE,'candidates':CANDIDATES,'fixtures':FIXTURES,'contract':'Integer n in [0,1000000]; exact integer equality, no floating-point tolerance; stdout only.'}
    @app.post('/api/benchmark')
    def benchmark(body:Benchmark):
        if not gate.acquire(blocking=False):raise RunError('A run or generation is already in progress. Try again shortly.',429)
        try:return reports.save((runner or run_benchmark)(body.candidate,body.n,body.repeats))
        finally:gate.release()
    @app.post('/api/generate')
    def proposal(body:dict):
        if body:raise RunError('Generation uses only the packaged Python source; send an empty object.')
        if not gate.acquire(blocking=False):raise RunError('A run or generation is already in progress. Try again shortly.',429)
        try:return (generator or generate)()
        finally:gate.release()
    @app.get('/api/reports')
    def recent():return {'reports':reports.recent()}
    @app.get('/api/reports/{identifier}')
    def get(identifier:str):return reports.get(identifier)
    @app.get('/api/reports/{identifier}/download')
    def download(identifier:str):return Response(json.dumps(reports.get(identifier),indent=2),media_type='application/json',headers={'Content-Disposition':f'attachment; filename="benchmark-{reports.get(identifier)["id"]}.json"'})
    return app
app=create_app()

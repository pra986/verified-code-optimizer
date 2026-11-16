"""Optional generation is review-only: returned code never reaches the runner."""
import os
import httpx
from .runner import RunError
from .workload import PYTHON_SOURCE

def generate():
    key,model=os.getenv('OPENAI_API_KEY'),os.getenv('OPENAI_MODEL')
    if not key or not model:raise RunError('Configure OPENAI_API_KEY and OPENAI_MODEL on the server for optional generation.',503)
    base=os.getenv('OPENAI_BASE_URL','https://api.openai.com/v1').rstrip('/')
    try:
        with httpx.Client(timeout=45,follow_redirects=False) as client:
            response=client.post(base+'/chat/completions',headers={'Authorization':'Bearer '+key},json={'model':model,'messages':[{'role':'system','content':'Translate the supplied Python program into a standalone C++17 program. Return only code, no markdown fences. Preserve the integer contract n in [0,1000000], argv input, and exactly one nonnegative integer on stdout. Use int64_t; prevent overflow. Never add network, filesystem writes, subprocesses or external dependencies.'},{'role':'user','content':PYTHON_SOURCE}],'max_tokens':3000})
            response.raise_for_status();code=response.json()['choices'][0]['message']['content']
            if not isinstance(code,str) or not code.strip() or len(code)>64000:raise ValueError('Invalid output')
            return {'code':code.strip(),'model':model,'execution':'not_executed','notice':'Untrusted model output for review/download only. It has not been compiled or checked. It cannot be submitted to this app’s benchmark runner.'}
    except (httpx.HTTPError,KeyError,IndexError,TypeError,ValueError) as exc:raise RunError('The generation provider failed or returned invalid output. The fixed offline demo remains available.',502) from exc

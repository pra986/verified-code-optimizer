# Verified Code Optimizer — Project 04

A correctness-gated Python-to-C++ benchmark studio built with AI assistance for Pranil Deshmukh. Inspect fixed source programs, compile a reviewed candidate, compare outputs against an independent oracle, and measure only candidates that pass. The offline demo requires no AI key.

Inspired by Ed Donner's [LLM Engineering, week 4](https://github.com/ed-donner/llm_engineering/tree/main/week4) optimization exercise. This implementation adds a fixed execution boundary, independent oracle, failure demos, saved reproducible reports, browser UI and automated tests. It is a course-inspired, AI-assisted portfolio project; the packaged translation is reviewed demo code, not a newly generated model result.

## Run locally

**Supported execution environment: Linux or Ubuntu in WSL2 on Windows.** Use Python 3.11+ and a C++17 `g++` compiler. Native Windows/macOS benchmark execution has not been verified. On Windows, run the commands inside your Ubuntu/WSL terminal.

For Ubuntu/WSL, install prerequisites if needed:

```bash
sudo apt-get update
sudo apt-get install -y python3 python3-venv python3-pip g++ git
```

Then:

```bash
git clone https://github.com/pra986/verified-code-optimizer.git
cd verified-code-optimizer
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
python -m uvicorn optimizer.app:app --host 127.0.0.1 --port 8004
```

Open **[http://localhost:8004](http://localhost:8004)** after starting the server. Stop with Ctrl+C. Port 8004 keeps this demo separate from earlier projects; choose another free port if needed. The URL starts working on your computer only after you run the app.

## Demonstration

1. Keep **Reviewed C++ loop**, choose n=100000 and 3 or 5 repeats. Inspect both programs.
2. Click **Check correctness and benchmark**. The app compiles once and checks eight fixed fixture sizes plus your requested n if distinct.
3. Inspect all oracle/Python/C++ outputs, medians, raw samples, compiler flags and source hashes. Download the full JSON report.
4. Select **Off-by-one regression**. Its incorrect outputs produce a failure report with **no timing ratio**.
5. Select **Compile-error fixture**. Compilation fails before correctness or timing.
6. Reload and reopen any of the 20 most recent reports from local history.

The workload is `sum(i*i for i in 1..n) modulo 1000000007`, with integer n in [0,1000000]. All outputs are compared exactly: absolute and relative tolerances are zero. The independent oracle uses the closed-form sum of squares with arbitrary-precision Python integers. The C++ intermediate `i*i` remains within signed 64-bit range under this contract.

## How measurements work

Only fixture agreement enables timing. Both programs warm up once. Each runs 3–9 times, alternating Python-first and C++-first order. Every timed result is checked against the oracle again. Reports include all wall-clock samples, median, minimum, maximum and population standard deviation. Compilation is measured separately and is **excluded** from the runtime ratio.

**These are end-to-end subprocess measurements**, including the common Python resource-limit launcher, interpreter startup, process scheduling and IPC. The ratio is Python median divided by C++ median, not a kernel-only speedup, confidence interval or universal claim about C++. Small workloads may be dominated by startup overhead. Fixture agreement is regression evidence, not a mathematical proof of equivalence for all inputs. No cross-machine performance claim is made.

## Execution boundary

The benchmark API accepts only a candidate enum, n and repetition count. It cannot accept arbitrary source, file paths, compiler flags or shell commands. It runs only the packaged Python baseline and three packaged C++ candidates. There is no shell interpolation. Temporary compile files are removed after each run. A per-process gate allows one benchmark or generation request at a time.

On Linux, each child receives limits of 8 CPU seconds, 1 GiB address space, 1 MiB regular output-file size and disabled core dumps, plus a 15-second wall timeout. The launcher uses a fresh interpreter and `execv`, avoiding `preexec_fn` in a threaded server. The child environment does not inherit API credentials. **These limits are not an isolation sandbox**: processes can still access the host filesystem/network under their OS identity. Never modify this runner to execute untrusted user/model code without a separately designed execution environment. Compiler subprocess limits may cause compilation to fail on constrained hosts; that failure is reported, not treated as a speedup.

## Optional AI proposal — review and download only

Set these server variables before starting:

```bash
export OPENAI_API_KEY='your-key'
export OPENAI_MODEL='your-compatible-chat-model'
```

The app uses an OpenAI-compatible chat-completions endpoint. `OPENAI_BASE_URL` defaults to `https://api.openai.com/v1`. Choose a model supported by your account and endpoint; compatibility is provider-specific. `.env.example` lists variables; `.env` is not loaded automatically.

Click **Generate C++ for review** and confirm sending the fixed, nonprivate Python fixture to your configured provider. The returned proposal is untrusted text and can be downloaded as `unverified-proposal.cpp.txt`. It is **not compiled, executed, benchmarked or added to trusted candidates**. This deliberate boundary keeps the demo honest about execution risks. No live paid provider calls were used in verification; mocked contract tests cannot establish model output quality.

## Data and scope

Local single-user demo with no authentication or account isolation. Keep it on loopback; do not expose it publicly. All reports on one server are accessible to its users. SQLite at `.data/reports.sqlite3` stores complete reports and fixed source text. Override `OPTIMIZER_DATA_DIR` if needed. AI proposals stay in browser memory and any downloaded copy; the app does not save them into SQLite. Provider requests may be retained under the provider's policies. Host/Origin validation is not authentication. Request bodies are capped after reading; use a gateway streaming limit before public deployment.

## Checks and documentation

```bash
python -m unittest discover -s tests -v
python -m pip install 'playwright>=1.50,<2'
python -m playwright install chromium
python tests/browser_smoke.py
```

The test suite includes real g++ compilation and execution of all three fixed candidates. GitHub CI runs Python 3.11/3.12/3.13 tests and real Chromium smoke tests. See [verification results](evaluation/results.md), [system architecture and flow](docs/architecture.md), and [interview walkthrough](docs/interview.md).

This is a separate repository for Project 04. Portfolio policy: **one project per repository**, with 39 projects planned. This repository does not represent all 39 completed projects.

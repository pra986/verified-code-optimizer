# Interview walkthrough and contribution guide

## Introduction you can defend

“This is my course-inspired, AI-assisted implementation of a correctness-first Python-to-C++ benchmark studio. I can show source inspection, an independent oracle, failure rejection, repeated timings and saved reports. Ed Donner's optimization project inspired the use case. I did not independently author the course, and I do not execute newly generated model code in this demo.” Claim only the personal contributions you actually made and can explain.

## Five-minute demo

1. Run the app and show the exact integer workload. Explain why n is bounded and `int64_t` is sufficient.
2. Show the Python and C++ loops, then the independent closed-form oracle.
3. Run the reviewed candidate. Inspect zero, upper-bound and requested-input fixtures.
4. Show the raw timing samples, median ratio, startup overhead disclosure and compiler flags. Download the JSON report.
5. Run the off-by-one candidate. Demonstrate that an incorrect program receives no runtime ratio.
6. Run the compile-error candidate. Explain why failure is evidence rather than a benchmark result.
7. Explain that optional model generation is review-only and resource limits do not provide secure isolation.

## Questions to prepare

| Interview question | Answer to understand |
|---|---|
| Does passing tests prove equivalence? | No. They show agreement on selected cases; a proof would require reasoning over all valid inputs or formal techniques. |
| Why an independent oracle? | Comparing only Python and C++ could accept a shared bug. The closed-form formula uses a different algorithm and arbitrary-precision arithmetic. |
| What prevents overflow? | n ≤ 1,000,000 gives i² ≤ 10¹²; the modulo accumulator stays below the modulus before each addition. This is well within signed 64-bit capacity. |
| Why exact comparison? | Outputs are integers. There is no floating-point rounding, so an epsilon would conceal mistakes. |
| What does the ratio measure? | Python median subprocess wall time divided by C++ median subprocess wall time, including common launcher/startup overhead. It is not pure compute throughput. |
| Why alternate order? | To reduce systematic order bias from machine drift; it does not eliminate thermal, scheduler or load effects. |
| Why not execute model output? | It is untrusted code. A subprocess timeout and resource limits do not prevent host filesystem or network access. |
| Why no repair agent? | This scope prioritizes an observable evaluation gate. Automated repair belongs behind a separately designed isolation boundary. |
| How are secrets protected? | Credentials stay in the server environment for provider calls; a minimal child environment does not forward them. That does not replace OS isolation. |
| What would you add? | A second workload with its own oracle, stronger evaluation, kernel-only timing in a controlled worker, and a properly isolated generated-code evaluation service. |

## Make a real contribution

Run the existing tests, explain every boundary case and reproduce a report on your own machine. Add one reviewed workload, derive its numeric contract, construct an independent oracle and introduce a deliberate wrong implementation to test rejection. Record your actual changes and measurements. Do not claim production readiness, model quality or universal speedups without supporting evidence.

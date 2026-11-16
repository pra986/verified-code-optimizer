# Verification results

- Tested application commit: `514e93a4c40e1064d34f2e9d508e4b920ff50876`.
- [GitHub Actions run 43847119241](https://github.com/pra986/verified-code-optimizer/actions/runs/43847119241): **all four jobs passed** — 43 tests on Python 3.11, 3.12 and 3.13, plus real Chromium browser smoke against the compiler-backed server.
- Browser checked successful real compilation, exact oracle agreement, displayed timings, JSON report download, rejection of an off-by-one candidate, rejection of a compile-error candidate, persistent report history and 390px responsive layout. No page JavaScript errors were observed.
- Desktop and mobile screenshots were visually reviewed. Screenshots and a fixed-source example report are available in the workflow artifact subject to GitHub retention, not committed as user data.
- Local Linux / Python 3.12: 43 tests passed from source and after a built-package installation outside the source directory. The local install inherited runtime dependencies; CI independently checked clean dependency installation.
- JavaScript syntax passed `node --check`.
- Eight fixed fixture sizes plus the requested n when distinct. All comparisons use exact integer equality against the independent oracle. Incorrect and compile-error candidates have no timing ratio.
- Hosted generation was tested using mocked provider responses only. No live paid provider calls or model-quality evaluation were performed. Generated code is not compiled or executed.

Timings are machine-specific end-to-end subprocess measurements. They include launcher/interpreter startup and IPC, and exclude compilation. No universal speedup or kernel-throughput claim is asserted. The linked run records the exact tested application commit; this verification update changes documentation only.

# Verification results

- Local Linux / Python 3.12: **43 tests passed**, including real g++ compile/run integration for reviewed, wrong and compile-error candidates.
- JavaScript syntax passed `node --check`.
- Fixed fixture counts: eight standard inputs, plus the requested n when distinct. Correctness requires exact integer equality against an independent oracle.
- Correct candidate passed fixtures; incorrect candidate and compile-error candidate produced no timing ratio.
- Hosted generation was tested using mocked provider responses only. No live paid provider calls or model-quality evaluation were performed.
- Clean CI matrix and real browser verification: pending upload.

Timings are machine-specific subprocess measurements; no performance target or universal speedup is asserted.

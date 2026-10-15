# AI-assisted work log (QryptoNox Quantum Oracle Forensics)

Rules (section 10): AI assistants are permitted; assistance must be declared and results
independently verified. Tool: Claude Code (Claude Sonnet 5.5), working inside this repository
at the request of a 3-person team of quantum-computing beginners. The AI wrote code and text;
the team chose the strategy changes listed under "Human decisions".

## Chronological log

| # | Date | What the AI did | How it was verified |
|---|------|-----------------|---------------------|
| 1 | 2026-10-15 | Read the problem PDF; explained task and scoring in plain words. | Team re-read sections 3, 5, 8, 13. |
| 2 | 2026-10-15 | Created `.venv`; installed qiskit 2.5.2, numpy 2.5.4, scipy 1.18.1; pinned `requirements.txt`. | `pip freeze`; `logs*/versions.json`. |
| 3 | 2026-10-15 | Wrote `oracle_sim.py` (8 families, noisy harness, query counter) and `test_sim.py`. | Section 4 example values reproduced; family properties on 50 random instances each; measured noise rates match analytic values (0.9423 vs 0.9416, 0.8509 vs 0.8508). |
| 4 | 2026-10-15 | Proposed the solving strategy before any solver code. | Reviewed and amended by the team (see human decisions). |
| 5 | 2026-10-15 | Wrote `solver.py` (Bayesian posterior, information-gain query choice, confirmations), `test_solver_model.py`, `evaluate.py`. | Every likelihood table compared with 20,000 simulated shots (max abs. error 0.013); smoke tests on all families. |
| 6 | 2026-10-15 | Added noise-level mixture, judge-safety hardening, `test_regressions.py`, reproducibility seeds. | 8 regression tests; mutation check confirmed the slicing test fails when the bug is reintroduced. |
| 7 | 2026-10-16 | Ran the paired tau sweep and `compare_tau.py` with a decision rule fixed beforehand; froze tau = 0.98 and the mixture. | `logs_tau/` (40 oracles/family/noise, identical oracles across settings). |
| 8 | 2026-10-16 | Drafted REPORT.md, AI_DISCLOSURE.md, README.md; final evaluation (100 oracles/family/noise). | Numbers in the report are copied from `logs/` by script output, not typed from memory. |

## Errors made by the AI and corrected (kept for honesty)

1. A vacuous test (`... or True`) was written and later removed.
2. `choose()` returned `(action, cost)` instead of `action`, so every query silently ran a
   1-iteration Grover; found by tracing a linear oracle whose posterior never moved. Fixed;
   regression tests added.
3. The perm "different values" pair model first failed its check; the cause was my test
   (a fixed offset samples only 128 fixed pairs of one permutation), not the model.
4. A report claim of "~3x information" for the g1 action was measured and corrected to 2.2-2.7x.
5. A sweep wait-loop was initially mistaken for the evaluation still running; the process list
   was re-checked and the finished results were used.

## Human decisions (team, not AI)

- Constant 0: keep spending budget while the posterior is uncertain (stop on posterior).
- Linear b by classical reads at random x; grover confirmed by 2 reads; constant 1 decided first.
- Use stress-noise-aware likelihoods; later: noise level as hidden variable (mixture).
- Pre-registered selection rules for tau and for mixture vs stress-only.

## What was NOT done by AI

Hard-coded answers, seed lookups, reading oracle tables: none exist in `solver.py`
(`test_regressions.py` checks that it does not import the simulator or open files).
All strategy and code were produced during the hackathon.

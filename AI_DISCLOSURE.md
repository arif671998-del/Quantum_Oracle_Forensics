# AI-use disclosure (one page)

**Project:** QryptoNox "Quantum Oracle Forensics" solver. **Team:** 3 members (beginners in
quantum computing). **Date:** 2026-10-15/16.

## What AI was used
Claude Code (Anthropic, model Claude Sonnet 5.5) was used inside our repository as a coding and
writing assistant for the whole project: reading the problem statement, building the local
noisy oracle simulator, designing and writing `solver.py`, the test suite, the evaluation
harness, and drafting the report and README. We also used Claude in the Claude app (claude.ai) to explain the problem statement, advise on
strategy, review our results against the report, and typeset the report PDF. A line-by-line
log of the Claude Code work is in `AI_USE_LOG.md`.

## What the AI did and what the team did
| AI | Team |
|---|---|
| Wrote the simulator, solver, tests, evaluation scripts and first drafts of all documents | Set the goals; decided constant-0 policy, confirmation rules, use of stress-noise likelihoods and the noise-level mixture; fixed the selection rules for the stopping threshold and mixture before seeing the data; reviewed every result |

## How results were independently verified
- Simulator checked against every example value in section 4 and against analytic noise rates.
- Each likelihood table in the solver was compared with 20,000 simulated shots.
- Eight regression tests (including a mutation check) guard bugs found along the way.
- Tau and the noise model were chosen by paired comparison on identical oracles with
  pre-declared rules (`compare_tau.py`, `logs_tau/`).
- Final numbers in the report come from `logs/` (fixed seeds; library versions in
  `logs/versions.json`) and can be reproduced with the commands in `README.md`.

## Integrity statement
- The solver decides only from `run()` results. It does not read oracle tables, use seed
  lookups or hard-coded answers, and does not import the simulator or touch files
  (checked by a test).
- Event-specific strategy and code were developed during the hackathon.
- Mistakes the AI made, and how they were caught, are listed in `AI_USE_LOG.md`.
- The AI has no ownership claim; the team keeps ownership of the work.

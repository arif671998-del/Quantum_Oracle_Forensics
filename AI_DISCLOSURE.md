# AI-use disclosure

Project: QryptoNox "Quantum Oracle Forensics" solver. 
Team: 3 members. 
Date: 2026-10-15/16.

## What AI was used
Claude Code (Anthropic, Claude Sonnet 5.5) was used inside our repository as a coding and writing
assistant: building the local noisy oracle simulator, writing and debugging `solver.py`, the test suite and the
evaluation harness, and drafting the report and README, working from the team's decisions and reviews.
We also used Claude in the Claude app to explain the problem statement, discuss strategy, check our
results against the report, and typeset the report and this disclosure as PDFs. A log of the
AI-assisted work is in `AI_USE_LOG.md`.

## What the AI did and what the team did
**AI:** wrote the simulator, solver, tests, evaluation scripts and first drafts of all documents.

**Team:**
- Studied and practised the algorithms the solver uses (Deutsch–Jozsa, Bernstein–Vazirani, Grover,
  Simon) in our own Qiskit lab before the event.
- Made the design decisions: constant-0 policy, confirmation rules, stress-noise likelihoods and the
  noise-level mixture; fixed the selection rules for the stopping threshold before seeing the data.
- Ran every test and the full 17,600-task evaluation on our own machine and checked the outputs.
- Tested the solver by hand on all eight families under normal and doubled noise (`try_solver.py`).
- Reviewed every number in the report against `logs/` before submission.

## How results were independently verified
- Simulator checked against every example value in section 4 of the problem statement and against
  analytic noise rates.
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
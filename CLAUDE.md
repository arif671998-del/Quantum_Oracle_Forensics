# QryptoNox Quantum Oracle Forensics (PS1) - project notes

Hackathon task: `solver.py` defines `solve(n, m, budget, families, run) -> (family, secret)`
identifying one of 8 sealed noisy oracle families within 60 queries. Spec: the PDF in this folder.

## Layout
- `solver.py` - the submission (qiskit/numpy only). Bayesian posterior + expected-information-gain query choice.
- `oracle_sim.py` - local noisy oracle simulator (`Harness.run`, `make_oracle`). NOT part of the submission.
- `test_sim.py` - simulator vs spec section 4 values and noise rates.
- `test_solver_model.py` - solver likelihood tables vs simulator at stress noise.
- `evaluate.py` - baselines, confusion matrix, budget caps, both noise levels; writes `logs/`.
- `AI_USE_LOG.md` - AI-use disclosure log (rules require it; keep it updated).

## Commands
- `.venv/bin/python test_sim.py && .venv/bin/python test_solver_model.py`
- `.venv/bin/python evaluate.py --suite quick` (1 min) / `--suite all --reps 20` (~15 min, 8 cores)

## Rules to respect
- solver.py must not import oracle_sim or read anything outside itself; decisions only from run() results.
- Never exceed the budget (a query = oracle gates in circuit x shots); solver tracks its own count.
- Likelihoods assume stress noise (8% misfire / 4% readout) on purpose; do not "tune" to normal noise silently.
- Secrets: linear -> [a, b]; simon2 -> sorted list of 3; constant/grover/simon -> int; others None.

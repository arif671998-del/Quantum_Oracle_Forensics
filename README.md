# QryptoNox Quantum Oracle Forensics: solver

`solver.py` defines `solve(n, m, budget, families, run) -> (family, secret)`. It identifies
which of 8 sealed noisy oracle families it faces, and its secret, in at most 60 queries.

**How it works (one paragraph):** an exact Bayesian posterior over every (family, secret)
hypothesis consistent with `m`; each query (Bernstein-Vazirani probe, classical read,
Grover(k), a one-iteration-Grover-then-read action, Simon probe, pair check) is chosen by
expected information gain per query; the noise level (4%/2% or 8%/4%) is a hidden variable
with a 50/50 prior; it stops when the best hypothesis passes tau = 0.98 and the
family-specific classical confirmations are done. Details and results: `REPORT.md`.

## Requirements
Python 3.10+ (tested 3.13.9), `qiskit>=2,<3`, `numpy`, `scipy` (solver uses only qiskit and numpy
plus the standard library).

## Install
```bash
git clone <repo-url> qryptonox && cd qryptonox
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt     # qiskit 2.5.2, numpy 2.5.4, scipy 1.18.1
```

## Run
```bash
# use the solver (the judges supply run(circuit, shots))
python -c "import solver; print(solver.solve)"

# tests (about 2 minutes)
.venv/bin/python test_sim.py              # simulator vs spec section 4 + noise rates
.venv/bin/python test_solver_model.py     # solver likelihood tables vs simulator
.venv/bin/python test_regressions.py      # regression + judge-harness safety tests

# evaluation (writes logs/; fixed seeds)
.venv/bin/python evaluate.py --suite quick                      # ~1 min, 2 oracles/family
.venv/bin/python evaluate.py --suite all --reps 100 --workers 8  # final run, a few hours
.venv/bin/python evaluate.py --suite tau --reps 40 --out logs_tau   # tau sweep
.venv/bin/python compare_tau.py logs_tau                         # paired comparisons
```

## Files
| file | purpose |
|---|---|
| `solver.py` | the submission |
| `oracle_sim.py` | local noisy oracle simulator (not used by the solver) |
| `evaluate.py`, `compare_tau.py` | baselines, confusion matrices, budget caps, paired comparisons |
| `test_*.py` | tests |
| `logs/` | final evaluation; `logs_tau/` tau sweep; `logs_before_mixture/` and `logs_mixture_prelim_tau995/` earlier runs |
| `REPORT.md`, `AI_DISCLOSURE.md`, `AI_USE_LOG.md` | report and AI-use disclosure |

## Results
Final run: 100 oracles per family per noise level, tau = 0.98, budget 60, fixed seeds
(`logs/`, 17,600 tasks, 2.2 h on 8 cores, qiskit 2.5.2 / numpy 2.5.4 / scipy 1.18.1).

| | normal (4%/2%) | stress (8%/4%) |
|---|---|---|
| accuracy | 0.990 | 0.964 |
| worst family | 0.98 | 0.91 (grover, randfun) |
| mean queries | 28.5 | 33.0 |

Baselines (accuracy normal / stress): classical-only 0.552 / 0.481, single algorithm
0.731 / 0.724, random 0.064 / 0.061, adaptivity off 0.944 / 0.886. Accuracy at caps
20/30/40/50/60 (normal): 0.896 / 0.958 / 0.978 / 0.985 / 0.990. Max 24 s per oracle, 16 qubits.
Details, confusion matrices and failure analysis: `REPORT.md`, `logs/evaluation_report.md`.

# QryptoNox Quantum Oracle Forensics: solver

Team: Arif, Rohit, Mehul. Qiskit Fall Fest 2026 (QC@IITI, IIT Indore), QryptoNox industry challenge.

`solver.py` defines `solve(n, m, budget, families, run) -> (family, secret)`. It identifies
which of 8 sealed noisy oracle families it faces, and its secret, in at most 60 queries.

**How it works (one paragraph):** an exact Bayesian posterior over every (family, secret)
hypothesis consistent with `m`; each query (Bernstein-Vazirani probe, classical read,
Grover(k), a one-iteration-Grover-then-read action, Simon probe, pair check) is chosen by
expected information gain per query; the noise level (4%/2% or 8%/4%) is a hidden variable
with a 50/50 prior; it stops when the best hypothesis passes tau = 0.98 and the
family-specific classical confirmations are done. Details and results: `REPORT.pdf`
(source `REPORT.md`).

## Requirements
Python 3.10+ (tested 3.13.9), `qiskit>=2,<3`, `numpy`, `scipy` (solver uses only qiskit and numpy
plus the standard library).

## Install
```bash
git clone https://github.com/arif671998-del/Quantum_Oracle_Forensics.git && cd Quantum_Oracle_Forensics
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt     # tested with qiskit 2.5.2, numpy 2.5.4, scipy 1.18.1
```

## Run
```bash
# use the solver (the judges supply run(circuit, shots))
.venv/bin/python -c "import solver; print(solver.solve)"

# try the solver by hand: one oracle per family, or --family grover --verbose to watch each query
.venv/bin/python try_solver.py

# tests (about 2 minutes)
.venv/bin/python test_sim.py              # simulator vs spec section 4 + noise rates
.venv/bin/python test_solver_model.py     # solver likelihood tables vs simulator
.venv/bin/python test_regressions.py      # regression + judge-harness safety tests

# evaluation (writes logs/; fixed seeds)
.venv/bin/python evaluate.py --suite quick --out logs_quick     # ~1 min, 2 oracles/family (keeps logs/ intact)
.venv/bin/python evaluate.py --suite all --reps 100 --workers 8  # final run, a few hours
.venv/bin/python evaluate.py --suite tau --reps 40 --out logs_tau   # tau sweep
.venv/bin/python compare_tau.py logs_tau                         # paired comparisons
```

## Files
| file | purpose |
|---|---|
| `solver.py` | the submission |
| `oracle_sim.py` | local noisy oracle simulator (not used by the solver) |
| `try_solver.py` | manual test: runs the solver and checks answer format and rules (budget, qubits, measurements, time) |
| `test_*.py` | tests |
| `evaluate.py`, `compare_tau.py` | baselines, confusion matrices, budget caps, paired comparisons |
| `budget_split.py`, `make_report_tables.py` | budget split per family; fills the report tables from `logs/` |
| `logs/` | final evaluation; `logs_tau/` tau sweep; `logs_before_mixture/` and `logs_mixture_prelim_tau995/` earlier runs; `logs_budget_split.json` |
| `REPORT.pdf` (3 pages), `AI_DISCLOSURE.pdf` (1 page) | the submitted report and AI-use disclosure, typeset from the .md files |
| `REPORT.md`, `REPORT.template.md`, `AI_DISCLOSURE.md`, `AI_USE_LOG.md` | report source (numbers filled from `logs/` by `make_report_tables.py`) and AI-use notes |
| `CLAUDE.md` | the project brief the AI coding assistant (Claude Code) worked from |

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

Note on timing: the `seconds` column of `logs/tasks.csv` is wall-clock time with 8 solver processes
sharing 8 cores. One block of cap-30 tasks shows 135-225 s: the laptop paused during the overnight run, so
neighbouring tasks of different families share identical times. Run alone, one solve takes 1-3 s on the same
laptop (`try_solver.py`), far below the 120 s limit.

Details, confusion matrices and failure analysis: `REPORT.pdf`, `logs/evaluation_report.md`.
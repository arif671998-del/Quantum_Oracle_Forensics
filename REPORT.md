# Quantum Oracle Forensics: strategy and evidence

*Team of 3 (beginners in quantum computing). Code: `solver.py`. All numbers below are copied
from `logs/` by `make_report_tables.py` (fixed seeds, versions in `logs/versions.json`).
AI-use disclosure: `AI_DISCLOSURE.md` (separate page).*

## 1. Approach

`m` is given, so the problem splits: **m = 1** {constant, balanced, linear, grover, randfun},
**m = 8** {simon, simon2, perm}. The solver keeps an exact **Bayesian posterior** over every
(family, secret) hypothesis (m=1: 2 + 510 + 256 + 1 + 7 randfun-grid points; m=8: 1 + 255 +
10,795 subspaces; equal prior per family). Each observation updates it with an *exact*
likelihood including both noise types (each table checked against 20,000 simulated shots,
`test_solver_model.py`, max error 0.013).

| action | what it measures | cost |
|---|---|---|
| `bv` (Bernstein-Vazirani/DJ probe) | Walsh index: one repeated string = linear; mostly 0 = constant/grover; P(0)=0.16 randfun, 0 balanced | 1 |
| `read(x)` | f(x) classically (needed for b, c, confirmations) | 1 |
| `grover(k)` | marked item t | k |
| `g1`: one Grover step then read f(z) | after one step P(f(z)=1) = sin²(3θ) = p(3-4p)²: **0.97 for randfun (p=0.3) vs 0.5 for balanced**, 2.2-2.7x the information of two plain reads | 2 |
| `probe` (Simon, m=8) | y ⟂ s (simon), y ⟂ H (simon2), uniform (perm) | 1 |
| `pair(d)` | f(x) vs f(x⊕d): Hamming distance <= 1 means d is a period | 2 |

**Noise.** The solver is not told the noise level, so it is a hidden variable: likelihoods are
kept under 4%/2% and 8%/4% with a 50/50 prior and decisions use the posterior marginalised
over it. In a paired test on identical oracles this kept accuracy equal (10 oracles won, 10
lost) and saved 1.1 queries on average (95% CI -1.4 to -0.8) (§3).

**Choosing the next query.** Maximise expected decision-entropy reduction per query cost over
{`bv`, `read` at a fresh x, `read` at the best Grover candidate, `g1`, `grover(k)`, k=2..12;
m=8: `probe`, `pair` on the two likeliest periods}. Fixed opening: 2 `bv` (m=1) or 3 probes
(m=8). *Constant 1 is decided first*: if constant/grover mass >= 0.5, up to 6 reads at distinct
random x until P(constant 1) leaves (0.005, tau), so it never reaches the Grover branch.

**Stopping and confirmations.** Stop when the best (family, secret) has posterior >= tau and its
confirmations are done; otherwise spend the budget and answer the MAP group (constant 0 is
therefore never "proved", only made likely).

| answer | confirmation (classical reads) |
|---|---|
| linear (a,b), constant | >= 2 reads, b = f(x) xor a·x |
| grover t | 2 reads at t returning 1; near-miss candidates (Hamming 1) are counted by the posterior |
| simon s / simon2 H | 2 checks f(x)=f(x⊕s), Hamming <= 1 / 1 check per element of H |
| balanced, randfun, perm | posterior only |

## 2. Statistics and thresholds behind each decision

* **randfun variation**: ones-fraction p ~ N(0.3, 0.029²) (Binomial(256,0.3)/256), 7-point grid, so
  one randfun instance cannot be mistaken for a different p by chance.
* **balanced vs randfun** is one sequential test combining the `bv` zero-string rate (0.04-0.08 vs
  0.19-0.23), plain reads (0.46-0.48 vs 0.29-0.30 ones) and `g1` bits (0.46-0.48 vs 0.82-0.89).
* **tau = 0.98** by a *pre-registered* paired sweep (40 oracles/family/noise, same oracles for
  every setting): the lowest tau within 0.5 points of the best accuracy.

| tau (mixture, pooled both noises, 640 oracles) | accuracy | mean queries | worst family |
|---|---|---|---|
| 0.98 | 0.9766 | 30.6 | 0.900 |
| 0.99 | 0.9797 | 33.6 | 0.925 |
| 0.995 | 0.9812 | 35.5 | 0.925 |

* **perm is the expensive family** because its data (uniform) cannot reveal the noise level and
  ~11,000 alternatives are only softly penalised: a wrong simon `s` is contradicted by a sample
  with y·s=1, but readout noise produces such samples from a true oracle with probability
  0.04/0.08/0.14/0.24 for |s|=1,2,4,8 (likelihood ratio 0.08-0.49 per violating sample, not 0).
* **Grover limit under noise** (exact enumeration of misfire patterns): success per shot after
  readout, normal/stress: k=4 0.22/0.16, k=6 0.38/0.28, k=8 0.53/0.37, k=12 0.68/0.47 (noise-free
  k=12 gives 1.0). A k=12 circuit has zero misfires only 61%/37% of the time, so the solver uses
  k=6-8; a 1-in-256 item is typically found in 2-4 shots, but absence can never be certain.

## 3. Results (100 oracles per family per noise level)

Main solver (cap 60, tau 0.98), 100 oracles per family per noise level.

| family | acc normal | mean q normal | acc stress | mean q stress |
|---|---|---|---|---|
| constant | 1.00 | 33.4 | 1.00 | 33.6 |
| balanced | 0.98 | 25.7 | 0.98 | 29.7 |
| linear | 0.99 | 5.0 | 0.99 | 5.9 |
| grover | 0.99 | 23.0 | 0.91 | 29.0 |
| randfun | 0.98 | 26.3 | 0.91 | 35.4 |
| simon | 1.00 | 40.0 | 0.94 | 46.6 |
| simon2 | 0.98 | 24.6 | 0.98 | 32.4 |
| perm | 1.00 | 49.8 | 1.00 | 51.3 |
| **all** | **0.990** | **28.5** | **0.964** | **33.0** |

Worst-family accuracy: normal 0.98, stress 0.91. Query saving (correct tasks, vs 60): normal 0.526, stress 0.457. Max time per oracle 24.1 s; max qubits 16.

**Budget split** (mean queries per oracle spent on each action, normal noise; the rest of the 60 is unspent):

**constant** bv 2.5, grover 15.7, read 4.5; **balanced** bv 3.3, g1 22.0; **linear** bv 3.4, read 2.3; **grover** bv 2.5, grover 13.3, read 5.3; **randfun** bv 3.3, g1 20.1, grover 0.7, read 0.5; **simon** probe 20.4, read8 18.0; **simon2** probe 18.3, read8 7.3; **perm** probe 26.4, read8 25.1.

**Accuracy as a function of the query cap** (solver told budget = cap; saving always vs 60):

| cap | acc normal | worst fam | mean q | acc stress | worst fam | mean q |
|---|---|---|---|---|---|---|
| 20 | 0.896 | 0.73 | 16.5 | 0.754 | 0.44 | 16.8 |
| 30 | 0.958 | 0.89 | 21.4 | 0.875 | 0.68 | 23.0 |
| 40 | 0.978 | 0.94 | 24.7 | 0.931 | 0.86 | 27.7 |
| 50 | 0.985 | 0.96 | 27.1 | 0.946 | 0.88 | 31.0 |
| 60 | 0.990 | 0.98 | 28.5 | 0.964 | 0.91 | 33.0 |

| method | acc normal | worst fam | saving | acc stress | worst fam | saving |
|---|---|---|---|---|---|---|
| ours | 0.990 | 0.98 | 0.526 | 0.964 | 0.91 | 0.457 |
| (1) classical-only (no superposition) | 0.552 | 0.00 | 0.445 | 0.481 | 0.00 | 0.414 |
| (2) single algorithm (BV/Simon probe only) | 0.731 | 0.00 | 0.339 | 0.724 | 0.00 | 0.260 |
| (3) random guessing | 0.064 | 0.00 | 1.000 | 0.061 | 0.00 | 1.000 |
| (4) ours, adaptivity off (fixed schedule, no early stop) | 0.944 | 0.82 | 0.000 | 0.886 | 0.59 | 0.000 |

## 4. Baselines and where classical is enough

Per-family accuracy at cap 60 (normal / stress):

| method | constant | balanced | linear | grover | randfun | simon | simon2 | perm |
|---|---|---|---|---|---|---|---|---|
| full | 1.00 / 1.00 | 0.98 / 0.98 | 0.99 / 0.99 | 0.99 / 0.91 | 0.98 / 0.91 | 1.00 / 0.94 | 0.98 / 0.98 | 1.00 / 1.00 |
| classical | 1.00 / 0.99 | 0.97 / 0.96 | 1.00 / 1.00 | 0.23 / 0.20 | 0.00 / 0.00 | 0.50 / 0.24 | 0.54 / 0.41 | 0.18 / 0.05 |
| single | 0.52 / 0.52 | 1.00 / 0.94 | 0.50 / 0.50 | 0.00 / 0.00 | 0.83 / 0.92 | 1.00 / 0.92 | 1.00 / 1.00 | 1.00 / 0.99 |
| nonadaptive | 0.98 / 0.92 | 0.90 / 0.89 | 1.00 / 0.99 | 0.82 / 0.59 | 0.85 / 0.77 | 1.00 / 0.94 | 1.00 / 1.00 | 1.00 / 0.99 |

A classical-only strategy (same inference, reads only; birthday search for m=8) reaches 0.55 (normal): it is adequate for constant (1.00), balanced (0.97) and linear (1.00) but fails where structure is hidden in a single input or an XOR period: grover 0.23, simon 0.50, simon2 0.54, perm 0.18. A single quantum circuit reused for everything reaches 0.73: it cannot learn the phase-invisible secrets (constant c, linear b) nor find a grover item (grover 0.00). Switching adaptivity off lowers accuracy by 0.046 (normal) and removes all query saving.

## 5. Failure analysis

* **normal**: 26 wrong of 2400: balanced -> randfun x6; randfun -> grover x5; simon2 -> simon x5; linear (right family, wrong secret) x3; grover -> constant x3; randfun -> balanced x2; randfun -> linear x1; simon -> simon2 x1.
* **stress**: 98 wrong of 2400: grover -> constant x24; randfun -> balanced x23; simon -> perm x22; balanced -> randfun x9; randfun -> grover x6; simon2 -> simon x6; linear (right family, wrong secret) x3; grover (right family, wrong secret) x3; randfun -> linear x1; simon -> simon2 x1.

Reading: **grover -> constant** is the dominant structural error: a 1-in-256 item that the
2-4 affordable Grover shots (about 3 at stress) miss is indistinguishable from constant 0, and the posterior is
right to fall back on it. **balanced <-> randfun** is the weakest-signal pair: it rests on a
zero-string count and one-bit statistics, with randfun's ones-fraction overlapping balanced
only at its tails. **simon -> perm / simon2** occurs when the period's weight is large
(|s| near 8), where readout noise makes violating samples common. Fixes we did not make:
spending more shots on Grover costs queries on every constant-0 task; a lower tau would
convert some of these into early wrong answers.

## 6. Where quantum helps

* **grover**: found with a few k=6-8 Grover shots plus two confirming reads (see budget table),
  against about 128 expected classical queries (a classical reader finds t with probability
  ~60/256 ≈ 0.23 in 60 queries; measured baseline accuracy in §4).
* **linear**: one `bv` shot gives a; with b by classical reads that is ~6 queries, versus 9+
  noisy reads classically; `bv` also separates constant/linear/balanced/randfun at once.
* **simon/simon2**: a probe returns a linear equation per query; classical birthday search needs
  ~13-23 distinct reads before one collision and fails under misfires.
* **classical is enough** for constant 1/0 vs balanced, and for linear once a is known: reads
  give b and confirm. At n=8 the quantum advantage is moderate, not exponential.

## 7. Reproduce

`.venv/bin/python evaluate.py --suite all --reps 100 --workers 8` (about 2.2 h on 8 cores);
`evaluate.py --suite tau --reps 40 --out logs_tau`; `compare_tau.py logs_tau`. Max per-oracle time
24 s (limit 120 s); max 16 qubits (limit 20); only qiskit/numpy/stdlib.

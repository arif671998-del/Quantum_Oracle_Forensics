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
lost) and saved 1.1 queries on average (95% CI -1.4 to -0.8) (`logs_tau/pairwise_tau.md`).

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

<<T_TAU>>

<<T_TAUSENS>>

* **perm is the expensive family** because its data (uniform) cannot reveal the noise level and
  ~11,000 alternatives are only softly penalised: a wrong simon `s` is contradicted by a sample
  with y·s=1, but readout noise produces such samples from a true oracle with probability
  0.04/0.08/0.14/0.24 for |s|=1,2,4,8 (stress noise, readout flip 4%) (likelihood ratio 0.08-0.49 per violating sample, not 0).
* **Grover limit under noise** (exact enumeration of misfire patterns): success per shot after
  readout, normal/stress: k=4 0.22/0.16, k=6 0.38/0.28, k=8 0.53/0.37, k=12 0.68/0.47 (noise-free
  k=12 gives 1.0). A k=12 circuit has zero misfires only 61%/37% of the time, so the solver uses
  k=6-8; a 1-in-256 item is typically found in 2-4 shots, but absence can never be certain.

## 3. Results (100 oracles per family per noise level)

<<T_MAIN>>

<<T_BUDGET>>

<<T_CAPS>>

<<T_BASE>>

## 4. Baselines and where classical is enough

<<T_BASE_TEXT>>

## 5. Failure analysis

<<T_FAIL>>

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

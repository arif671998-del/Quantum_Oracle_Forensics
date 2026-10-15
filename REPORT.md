# QryptoNox Quantum Oracle Forensics: technical report (DRAFT)

> **Status:** sections 1-5 are final text. Sections marked `<<RESULTS ...>>` are filled
> from `logs_tau/` and `logs/` when the sweep finishes. The submitted report must be
> **at most 3 pages**; this draft is longer and will be trimmed (tables to key rows).
> AI-use disclosure goes on a separate one-page sheet (see `AI_USE_LOG.md`).

## 1. Problem in brief

Given a sealed oracle |x>|y> -> |x>|y xor f(x)> (n = 8, m in {1, 8}) with 4% misfire per
oracle application and 2% flip per measured bit, name its family (8 families) and, where
one exists, its secret, using at most 60 queries (one query = one oracle gate in one shot).
Scored on exact correctness, queries saved on correct tasks, worst-family accuracy and
accuracy at doubled noise (8% / 4%).

Because m is given, the problem splits in two:

| m | families | secrets |
|---|---|---|
| 1 | constant, balanced, linear, grover, randfun | c; none; (a, b); t; none |
| 8 | simon, simon2, perm | s; H (3 elements); none |

## 2. Bayesian model

**Hypotheses.** m = 1: constant 0/1 (2), linear (a, b) (510), grover t (256), balanced (1),
randfun on a 7-point grid of ones-fractions p ~ N(0.3, 0.029^2) (the instance-to-instance
spread of Binomial(256, 0.3)/256). m = 8: perm (1), simon s (255), simon2 H (10,795
subspaces). Prior: equal weight per family, uniform inside a family.

**Observations and their exact likelihoods** (all tables validated against the simulator,
`test_solver_model.py`, max abs. error 0.013 on 20,000 shots, i.e. within sampling error):

| action | circuit | outcome | cost |
|---|---|---|---|
| `bv` | H, phase oracle (output in \|->), H, measure | Walsh index y | 1 |
| `read(x)` | basis input x, oracle, measure output | f(x) | 1 |
| `grover(k)` | k Grover iterations | candidate t | k |
| `g1` | one Grover iteration, then read f(z) at the sampled z | (z, f(z)) | 2 |
| `probe` (m=8) | H, oracle, H, measure inputs | y with y.s = 0 (simon), y in H-perp (simon2), uniform (perm) | 1 |
| `pair(d)` (m=8) | read f(x), f(x xor d) | Hamming distance of the two values | 2 |

A misfire makes the oracle the identity, which is modelled exactly per action (for example a
misfired `bv`/`probe` always returns y = 0, which carries no information). Readout flips are
convolved exactly (8-bit Hamming noise matrix).

**Noise model and why.** The judges' stress setting doubles the noise and the solver is not
told which setting it faces. We therefore treat the noise level as a hidden variable:
log-likelihoods are kept under both (4%/2%) and (8%/4%) with a 50/50 prior, and the decision
posterior is marginalised over it. `<<RESULTS: whether the mixture beat stress-only; see 6>>`

**Choosing the next query.** For each candidate action the solver computes the expected
reduction of decision entropy (entropy over family+secret groups, noise marginalised) and
divides by its query cost; it executes the maximiser. Candidates: `bv`, `read` at a fresh
random x, `read` at the current best grover candidate, `g1`, `grover(k)` for k in
{2, 4, 6, 8, 10, 12}; for m = 8: `probe` and `pair` on the two most probable period
elements. Fixed opening: 2 `bv` probes (m = 1), 3 probes (m = 8).

**Constant-1 first.** If the mass of {constant, grover} is >= 0.5, up to 6 sequential reads
at distinct random x are made until P(constant 1 | constant or grover) leaves (0.005, tau).
Constant 1 is then decided before any Grover search is paid for.

**Stopping rule and confirmations.** Stop when the best (family, secret) group has posterior
>= tau and its confirmations are done; otherwise keep spending until the budget ends, then
answer the MAP group.

| answer | required confirmation |
|---|---|
| linear (a, b) or constant | >= 2 classical reads (b = f(x) xor a.x) |
| grover t | 2 reads at t returning 1 (near-miss candidates, Hamming distance 1, are counted by the posterior itself) |
| simon s | 2 pair checks f(x) = f(x xor s) with Hamming distance <= 1 |
| simon2 H | 1 pair check per element of H |
| balanced, randfun, perm | posterior only |

The solver charges the cost of a circuit before running it, never asks for more than the
remaining budget, tolerates empty or short `run()` results and space-separated count keys
(`test_regressions.py`).

## 3. The g1 action: why it separates randfun from balanced

Phase-oracle Grover on the uniform state with a fraction p of ones: one iteration rotates
the state to angle 3 theta with sin^2 theta = p, so a measured z has f(z) = 1 with
probability sin^2(3 theta) = p (3 - 4p)^2.

| function | p | P(f(z) = 1) after one iteration | plain read |
|---|---|---|---|
| randfun | 0.3 | 0.3 x 1.8^2 = **0.972** | 0.30 |
| balanced | 0.5 | 0.5 x 1^2 = **0.500** | 0.50 |

With noise the observed bit rates are 0.891 vs 0.481 (normal) and 0.817 vs 0.463 (stress),
against 0.296 vs 0.481 / 0.294 vs 0.463 for a plain read. One g1 shot costs 2 queries but
carries 2.7x (normal) / 2.2x (stress) the information of 2 plain reads (KL divergence randfun vs
balanced of the observed bit: 0.379 vs 0.142 nats, and 0.267 vs 0.119). The other probe, `bv`, only sees the
zero-string rate (randfun about 0.19-0.23 vs balanced 0.04-0.08), which is weaker still.
The posterior combines all three sources in one sequential test.

## 4. The Grover limit under noise

Noise-free, 12.6 iterations give success ~1. Every oracle gate can misfire and misfires
break the rotation, so deep circuits stop paying off (computed exactly by enumerating
misfire patterns, `grover_ps`):

| iterations k | noise-free | 4% misfire | 8% misfire | after readout (normal / stress) |
|---|---|---|---|---|
| 4 | 0.285 | 0.253 | 0.225 | 0.216 / 0.163 |
| 6 | 0.528 | 0.449 | 0.383 | 0.382 / 0.276 |
| 8 | 0.764 | 0.625 | 0.518 | 0.532 / 0.374 |
| 12 | 1.000 | 0.794 | 0.652 | 0.675 / 0.470 |

Success per shot rises with k but cost rises linearly; a k = 12 circuit has only 61% (normal)
or 37% (stress) chance of zero misfires. Roughly 4-6 shots of k = 6-8 fit in 60 queries, so a
grover instance is found in a handful of shots but **constant 0 can never be proven**, only
made increasingly unlikely: each failed shot multiplies the odds by (1 - success) ~ 0.5-0.75.
This is why constant-0 tasks cost most of the budget while constant-1 tasks cost about 6.

## 5. Why perm needs many queries

For perm the probe output is uniform over 256 values, and uniform data is exactly what
readout noise turns any structured sample into. Two consequences:

1. **The data cannot reveal the noise level.** Readout flips leave uniform data uniform;
   the only trace of noise is the excess of y = 0 from misfires: about 1.5 expected zeros in
   40 probes at 4% vs 2.5 at 8%, which Poisson noise swamps. The noise level can only be
   learned from structured data (a found s, or pair-check distances).
2. **~11,000 alternatives are penalised only softly.** A wrong simon hypothesis s is
   contradicted by a sample with y.s = 1, but readout noise produces such samples from a true
   oracle too: P(violation | s true) = 0.04 / 0.08 / 0.14 / 0.24 for |s| = 1, 2, 4, 8 at 4%
   readout noise, i.e. a likelihood ratio of only 0.08-0.49 per violating sample instead of 0.
   Hypotheses with large |s| (and most simon2 subspaces) are never eliminated outright;
   among 11,000 of them some fit the noise by chance, so the posterior of perm climbs slowly
   (mean final posterior 0.985 after 60 queries in the first evaluation).

Perm cannot be distinguished by its own signature, only by the failure of every alternative,
which is why it is the budget-limiting family. `<<RESULTS: perm accuracy / queries vs tau>>`

## 6. Results `<<RESULTS>>`

<<RESULTS: before/after table per tau, both noise levels (logs_tau/tau_sweep_report.md)>>

<<RESULTS: pairwise tau comparison on identical oracles>>

<<RESULTS: per-family accuracy and mean queries, confusion matrices (logs/)>>

<<RESULTS: accuracy vs budget cap 20/30/40/50/60>>

<<RESULTS: baselines: classical-only, single algorithm, random guessing, adaptivity off>>

## 7. Where the solver fails `<<RESULTS>>`

<<RESULTS: failure analysis from confusion matrices; honest statement of misreads>>

## 8. Where quantum helps

Locating a single marked input (grover) takes about 20 queries here against ~128 expected
classical queries; linear takes ~6 queries (one `bv` shot determines a, a few reads give b)
against 9+ classical reads with noisy outputs; simon/simon2 find a 1- or 2-dimensional
hidden subspace with a few dozen probes where a birthday search needs ~sqrt(256) = 16
collisions-worth of reads and fails under noise. `<<RESULTS: numbers from the baselines table>>`
At n = 8 the advantage is moderate: a classical solver with 60 reads gets most of the
easy families right.

## 9. Reproducibility

`python evaluate.py --suite tau --reps 40 --out logs_tau` reproduces the sweep; seeds are
fixed (oracle: `default_rng([family, rep, 99])`; harness: `default_rng([family, rep,
noise, 7])`; solver: 12345); library versions are in `logs*/versions.json`
(qiskit 2.5.2, numpy 2.5.4, scipy 1.18.1).

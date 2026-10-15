# Pairwise comparisons on identical oracles

40 oracles per family per noise level; 'wrong-only' = oracles that the lower tau gets wrong and tau=0.995 gets right.


## Lower tau vs tau=0.995, mixture solver

| noise | tau | wrong-only | right-only | net acc change | mean queries saved | constant: wrong/saved | balanced: wrong/saved | linear: wrong/saved | grover: wrong/saved | randfun: wrong/saved | simon: wrong/saved | simon2: wrong/saved | perm: wrong/saved |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| normal | 0.98 | 1 | 1 | +0.000 | 4.9 | 0/0.8 | 0/8.6 | 1/1.1 | 0/1.0 | 0/6.5 | 0/9.2 | 0/1.7 | 0/10.2 |
| normal | 0.99 | 1 | 0 | -0.003 | 1.9 | 0/0.4 | 0/2.5 | 1/0.5 | 0/0.8 | 0/3.2 | 0/3.9 | 0/0.8 | 0/2.8 |
| stress | 0.98 | 3 | 0 | -0.009 | 4.9 | 0/0.9 | 0/7.8 | 1/1.4 | 0/1.1 | 1/9.3 | 1/8.6 | 0/2.4 | 0/7.6 |
| stress | 0.99 | 0 | 0 | +0.000 | 2.0 | 0/0.6 | 0/4.0 | 0/0.7 | 0/0.6 | 0/3.6 | 0/2.9 | 0/1.4 | 0/1.9 |

## Lower tau vs tau=0.995, stress-only solver

| noise | tau | wrong-only | right-only | net acc change | mean queries saved | constant: wrong/saved | balanced: wrong/saved | linear: wrong/saved | grover: wrong/saved | randfun: wrong/saved | simon: wrong/saved | simon2: wrong/saved | perm: wrong/saved |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| normal | 0.98 | 2 | 0 | -0.006 | 4.7 | 0/0.5 | 1/10.4 | 1/1.2 | 0/1.6 | 0/7.8 | 0/9.8 | 0/1.7 | 0/4.9 |
| normal | 0.99 | 1 | 0 | -0.003 | 1.8 | 0/0.4 | 1/4.3 | 0/0.5 | 0/0.7 | 0/3.7 | 0/3.3 | 0/1.1 | 0/0.6 |
| stress | 0.98 | 3 | 0 | -0.009 | 4.5 | 0/0.7 | 0/8.8 | 0/1.3 | 1/2.1 | 2/10.6 | 0/7.5 | 0/2.1 | 0/3.4 |
| stress | 0.99 | 1 | 0 | -0.003 | 1.9 | 0/0.2 | 0/4.6 | 0/0.8 | 1/1.3 | 0/3.5 | 0/3.2 | 0/1.3 | 0/0.7 |

## Mixture vs stress-only (same tau, same oracles)

| noise | tau | mixture-only right | stress-only right | sign-test p | queries mixture - stress (95% CI) | acc mixture | acc stress-only |
|---|---|---|---|---|---|---|---|
| normal | 0.98 | 1 | 0 | 1.00 | -1.7 [-2.4, -1.0] | 0.991 | 0.988 |
| normal | 0.99 | 1 | 2 | 1.00 | -1.6 [-2.3, -0.9] | 0.988 | 0.991 |
| normal | 0.995 | 1 | 2 | 1.00 | -1.6 [-2.3, -0.9] | 0.991 | 0.994 |
| stress | 0.98 | 3 | 3 | 1.00 | -0.8 [-1.5, -0.0] | 0.963 | 0.963 |
| stress | 0.99 | 2 | 1 | 1.00 | -0.5 [-1.1, +0.2] | 0.972 | 0.969 |
| stress | 0.995 | 2 | 2 | 1.00 | -0.4 [-1.1, +0.2] | 0.972 | 0.972 |

Pooled: mixture-only right 10, stress-only right 10, sign-test p = 1.000; mean queries (mixture - stress) = -1.10 [-1.38, -0.81].

**Decision rule verdict: KEEP the noise mixture**

## tau recommendation (accuracy within 0.5 percentage points of the best, then fewest queries)

| solver | tau | pooled accuracy | pooled mean queries | worst family (min over noise) |
|---|---|---|---|---|
| mixture | 0.98 | 0.9766 | 30.6 | 0.900 |
| mixture | 0.99 | 0.9797 | 33.6 | 0.925 |
| mixture | 0.995 | 0.9812 | 35.5 | 0.925 |
| stress-only | 0.98 | 0.9750 | 31.8 | 0.875 |
| stress-only | 0.99 | 0.9797 | 34.6 | 0.900 |
| stress-only | 0.995 | 0.9828 | 36.5 | 0.925 |

Recommended tau: {'mixture': 0.98, 'stress-only': 0.99}

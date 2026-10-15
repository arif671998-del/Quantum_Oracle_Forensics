# Tau sweep: before (stress-only likelihood) vs after (noise mixture)

40 oracles per family per noise level, cap 60, fixed seeds; wall 2081s


## normal noise

| tau | solver | accuracy | worst family | mean queries | query saving | q:constant | q:balanced | q:linear | q:grover | q:randfun | q:simon | q:simon2 | q:perm |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 0.98 | before | 0.988 | 0.950 | 30.0 | 0.501 | 32.8 | 27.5 | 5.5 | 23.2 | 26.3 | 44.9 | 25.1 | 55.1 |
| 0.98 | after | 0.991 | 0.975 | 28.3 | 0.528 | 32.5 | 24.6 | 5.2 | 22.3 | 27.7 | 40.0 | 24.8 | 49.3 |
| 0.99 | before | 0.991 | 0.950 | 33.0 | 0.453 | 32.9 | 33.6 | 6.2 | 24.0 | 30.4 | 51.4 | 25.7 | 59.4 |
| 0.99 | after | 0.988 | 0.975 | 31.3 | 0.479 | 32.9 | 30.7 | 5.8 | 22.6 | 30.9 | 45.3 | 25.7 | 56.8 |
| 0.995 | before | 0.994 | 0.975 | 34.8 | 0.423 | 33.3 | 37.9 | 6.8 | 24.7 | 34.1 | 54.7 | 26.8 | 60.0 |
| 0.995 | after | 0.991 | 0.975 | 33.2 | 0.449 | 33.3 | 33.2 | 6.3 | 23.3 | 34.2 | 49.2 | 26.4 | 59.5 |

Per-family accuracy:

| tau | solver | constant | balanced | linear | grover | randfun | simon | simon2 | perm |
|---|---|---|---|---|---|---|---|---|---|
| 0.98 | before | 1.000 | 0.950 | 0.975 | 0.975 | 1.000 | 1.000 | 1.000 | 1.000 |
| 0.98 | after | 1.000 | 0.975 | 0.975 | 0.975 | 1.000 | 1.000 | 1.000 | 1.000 |
| 0.99 | before | 1.000 | 0.950 | 1.000 | 0.975 | 1.000 | 1.000 | 1.000 | 1.000 |
| 0.99 | after | 1.000 | 0.975 | 0.975 | 0.975 | 1.000 | 0.975 | 1.000 | 1.000 |
| 0.995 | before | 1.000 | 0.975 | 1.000 | 0.975 | 1.000 | 1.000 | 1.000 | 1.000 |
| 0.995 | after | 1.000 | 0.975 | 1.000 | 0.975 | 1.000 | 0.975 | 1.000 | 1.000 |

Errors, tau=0.98 before: balanced->randfun x2, grover->constant x1

Errors, tau=0.98 after: balanced->randfun x1, grover->constant x1

Errors, tau=0.99 before: balanced->randfun x2, grover->constant x1

Errors, tau=0.99 after: balanced->randfun x1, grover->constant x1, simon->simon2 x1

Errors, tau=0.995 before: balanced->randfun x1, grover->constant x1

Errors, tau=0.995 after: balanced->randfun x1, grover->constant x1, simon->simon2 x1

## stress noise

| tau | solver | accuracy | worst family | mean queries | query saving | q:constant | q:balanced | q:linear | q:grover | q:randfun | q:simon | q:simon2 | q:perm |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 0.98 | before | 0.963 | 0.875 | 33.6 | 0.447 | 32.8 | 31.5 | 6.6 | 29.9 | 33.0 | 48.1 | 30.6 | 56.6 |
| 0.98 | after | 0.963 | 0.900 | 32.9 | 0.456 | 32.6 | 29.5 | 6.0 | 30.1 | 36.2 | 46.0 | 30.2 | 52.3 |
| 0.99 | before | 0.969 | 0.900 | 36.2 | 0.405 | 33.3 | 35.6 | 7.0 | 30.7 | 40.0 | 52.5 | 31.4 | 59.3 |
| 0.99 | after | 0.972 | 0.925 | 35.8 | 0.412 | 32.9 | 33.2 | 6.8 | 30.6 | 41.9 | 51.7 | 31.2 | 58.0 |
| 0.995 | before | 0.972 | 0.925 | 38.2 | 0.373 | 33.5 | 40.2 | 7.8 | 32.0 | 43.6 | 55.6 | 32.7 | 60.0 |
| 0.995 | after | 0.972 | 0.925 | 37.8 | 0.378 | 33.5 | 37.3 | 7.4 | 31.2 | 45.5 | 54.6 | 32.6 | 59.9 |

Per-family accuracy:

| tau | solver | constant | balanced | linear | grover | randfun | simon | simon2 | perm |
|---|---|---|---|---|---|---|---|---|---|
| 0.98 | before | 1.000 | 0.950 | 1.000 | 0.900 | 0.875 | 0.975 | 1.000 | 1.000 |
| 0.98 | after | 1.000 | 0.975 | 0.975 | 0.925 | 0.900 | 0.925 | 1.000 | 1.000 |
| 0.99 | before | 1.000 | 0.950 | 1.000 | 0.900 | 0.925 | 0.975 | 1.000 | 1.000 |
| 0.99 | after | 1.000 | 0.975 | 1.000 | 0.925 | 0.925 | 0.950 | 1.000 | 1.000 |
| 0.995 | before | 1.000 | 0.950 | 1.000 | 0.925 | 0.925 | 0.975 | 1.000 | 1.000 |
| 0.995 | after | 1.000 | 0.975 | 1.000 | 0.925 | 0.925 | 0.950 | 1.000 | 1.000 |

Errors, tau=0.98 before: balanced->randfun x2, grover->constant x3, randfun->balanced x5, simon->simon2 x1

Errors, tau=0.98 after: balanced->randfun x1, grover->constant x2, randfun->balanced x4, simon->perm x3

Errors, tau=0.99 before: balanced->randfun x2, grover->constant x3, randfun->balanced x3, simon->simon2 x1

Errors, tau=0.99 after: balanced->randfun x1, grover->constant x2, randfun->balanced x3, simon->perm x2

Errors, tau=0.995 before: balanced->randfun x2, grover->constant x3, randfun->balanced x3, simon->simon2 x1

Errors, tau=0.995 after: balanced->randfun x1, grover->constant x2, randfun->balanced x3, simon->perm x2

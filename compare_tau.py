"""Paired comparisons on identical oracles for the tau sweep (logs_tau/tasks.csv).

Decision rule fixed BEFORE seeing the data:
  keep the noise mixture over stress-only only if, pooled over all tau and both noise
  levels, it (a) loses no more oracles than it wins AND (b) either wins correctness with
  two-sided sign-test p < 0.05, or saves mean queries with a 95% paired-bootstrap CI
  entirely below 0.  Otherwise go back to stress-only.
"""
import csv, sys, json
from collections import defaultdict
import numpy as np
from scipy.stats import binomtest

D = sys.argv[1] if len(sys.argv) > 1 else "logs_tau"
rows = list(csv.DictReader(open(f"{D}/tasks.csv")))
FAM = ["constant", "balanced", "linear", "grover", "randfun", "simon", "simon2", "perm"]
rec = {}
for r in rows:
    rec[(r["noise"], r["method"], float(r["tau"]), r["family"], int(r["rep"]))] = (
        r["correct"] == "True", int(r["queries"]), r["pred"])
taus = sorted({k[2] for k in rec})
noises = ["normal", "stress"]
reps = sorted({k[4] for k in rec})
rng = np.random.default_rng(0)
out = []

def pair(noise, mA, tA, mB, tB, fams=FAM):
    """A vs B on the same oracles: returns arrays (correctA, correctB, qA, qB)."""
    ks = [(noise, f, rep) for f in fams for rep in reps]
    a = np.array([rec[(n, mA, tA, f, r)][:2] for n, f, r in ks], float)
    b = np.array([rec[(n, mB, tB, f, r)][:2] for n, f, r in ks], float)
    return a[:, 0], b[:, 0], a[:, 1], b[:, 1]

out.append("# Pairwise comparisons on identical oracles\n")
out.append(f"{len(reps)} oracles per family per noise level; 'wrong-only' = oracles that "
           "the lower tau gets wrong and tau=0.995 gets right.\n")
for method, nm in (("full", "mixture"), ("full_stress", "stress-only")):
    out.append(f"\n## Lower tau vs tau=0.995, {nm} solver\n")
    out.append("| noise | tau | wrong-only | right-only | net acc change | mean queries saved | " +
               " | ".join(f"{f}: wrong/saved" for f in FAM) + " |")
    out.append("|" + "---|" * (6 + len(FAM)))
    for noise in noises:
        for t in taus[:-1]:
            ca, cb, qa, qb = pair(noise, method, t, method, 0.995)
            wrong_only = int(((ca == 0) & (cb == 1)).sum())
            right_only = int(((ca == 1) & (cb == 0)).sum())
            cells = []
            for f in FAM:
                a_, b_, qa_, qb_ = pair(noise, method, t, method, 0.995, [f])
                cells.append(f"{int(((a_==0)&(b_==1)).sum())}/{(qb_-qa_).mean():.1f}")
            out.append(f"| {noise} | {t} | {wrong_only} | {right_only} | {(ca.mean()-cb.mean()):+.3f} | "
                       f"{(qb-qa).mean():.1f} | " + " | ".join(cells) + " |")

out.append("\n## Mixture vs stress-only (same tau, same oracles)\n")
out.append("| noise | tau | mixture-only right | stress-only right | sign-test p | queries mixture - stress (95% CI) | acc mixture | acc stress-only |")
out.append("|---|---|---|---|---|---|---|---|")
win = loss = 0
dq_all = []
for noise in noises:
    for t in taus:
        ca, cb, qa, qb = pair(noise, "full", t, "full_stress", t)
        w = int(((ca == 1) & (cb == 0)).sum()); l = int(((ca == 0) & (cb == 1)).sum())
        win += w; loss += l
        p = binomtest(w, w + l, 0.5).pvalue if w + l else 1.0
        dq = qa - qb; dq_all.append(dq)
        bs = [rng.choice(dq, len(dq)).mean() for _ in range(2000)]
        out.append(f"| {noise} | {t} | {w} | {l} | {p:.2f} | {dq.mean():+.1f} "
                   f"[{np.percentile(bs,2.5):+.1f}, {np.percentile(bs,97.5):+.1f}] | "
                   f"{ca.mean():.3f} | {cb.mean():.3f} |")
dq = np.concatenate(dq_all)
bs = [rng.choice(dq, len(dq)).mean() for _ in range(4000)]
lo, hi = np.percentile(bs, [2.5, 97.5])
p_all = binomtest(win, win + loss, 0.5).pvalue if win + loss else 1.0
keep = (win >= loss) and ((win > loss and p_all < 0.05) or hi < 0)
out.append(f"\nPooled: mixture-only right {win}, stress-only right {loss}, sign-test p = {p_all:.3f}; "
           f"mean queries (mixture - stress) = {dq.mean():+.2f} [{lo:+.2f}, {hi:+.2f}].")
out.append(f"\n**Decision rule verdict: {'KEEP the noise mixture' if keep else 'GO BACK to stress-only'}**")

# tau recommendation: within 0.5% (absolute) of best accuracy, fewest queries; per method, pooled over noise
out.append("\n## tau recommendation (accuracy within 0.5 percentage points of the best, then fewest queries)\n")
out.append("| solver | tau | pooled accuracy | pooled mean queries | worst family (min over noise) |")
out.append("|---|---|---|---|---|")
rec_by_method = {}
for method, nm in (("full", "mixture"), ("full_stress", "stress-only")):
    tab = []
    for t in taus:
        acc = np.mean([rec[(n, method, t, f, r)][0] for n in noises for f in FAM for r in reps])
        q = np.mean([rec[(n, method, t, f, r)][1] for n in noises for f in FAM for r in reps])
        wf = min(np.mean([rec[(n, method, t, f, r)][0] for r in reps]) for n in noises for f in FAM)
        tab.append((t, acc, q, wf))
        out.append(f"| {nm} | {t} | {acc:.4f} | {q:.1f} | {wf:.3f} |")
    best = max(a for _, a, _, _ in tab)
    ok = [x for x in tab if x[1] >= best - 0.005]
    rec_by_method[nm] = min(ok, key=lambda x: x[2])[0]
out.append(f"\nRecommended tau: {rec_by_method}")
open(f"{D}/pairwise_tau.md", "w").write("\n".join(out) + "\n")
print("\n".join(out))

"""Evaluation harness for solver.py on locally generated oracles (section 9).

Usage:  python evaluate.py [--reps 12] [--workers 8] [--suite all|main|quick]
Writes everything to logs/.
"""
import argparse, csv, json, os, sys, time
from concurrent.futures import ProcessPoolExecutor
import numpy as np

import solver
from oracle_sim import make_oracle, Harness, FAMILIES, M_OF, BudgetExceeded

NOISE = {"normal": (0.04, 0.02), "stress": (0.08, 0.04)}
LOG = "logs"


def norm(sec):
    if sec is None:
        return None
    if isinstance(sec, (tuple, list, np.ndarray)):
        return [int(v) for v in sec]
    return int(sec)


def run_task(job):
    noise, method, cap, tau, fam, rep = job
    orng = np.random.default_rng([FAMILIES.index(fam), rep, 99])      # same oracle for every method
    oracle = make_oracle(fam, orng)
    po, pr = NOISE[noise]
    hseed = [FAMILIES.index(fam), rep, list(NOISE).index(noise), 7]
    h = Harness(oracle, budget=cap, p_oracle=po, p_read=pr,
                seed=int(np.random.default_rng(hseed).integers(1 << 31)))
    width = [0]
    inner = h.run

    def run(circ, shots):
        width[0] = max(width[0], circ.num_qubits)
        return inner(circ, shots)
    m = M_OF[fam]
    t0 = time.time()
    err = None
    try:
        if method == "random":
            r = np.random.default_rng(hseed + [1])
            pf = FAMILIES[int(r.integers(8))]
            fake = make_oracle(pf, r)
            ans = (pf, norm(fake.secret))
        elif method == "full":
            ans = solver._solve(8, m, cap, FAMILIES, run, mode="full", tau=tau)
        elif method == "full_stress":       # old behaviour: stress likelihoods only
            ans = solver._solve(8, m, cap, FAMILIES, run, mode="full", tau=tau,
                                noises=(solver.STRESS,))
        else:
            ans = solver._solve(8, m, cap, FAMILIES, run, mode=method, tau=tau)
    except BudgetExceeded as e:
        ans, err = (None, None), "budget"
    dt = time.time() - t0
    info = dict(solver.LAST_INFO) if method not in ("random", "classical") else {}
    true_sec = norm(oracle.secret)
    ok = (ans[0] == fam) and (fam not in ("constant", "linear", "grover", "simon", "simon2")
                              or norm(ans[1]) == true_sec) and err is None
    return dict(noise=noise, method=method, cap=cap, tau=tau, family=fam, rep=rep,
                pred=ans[0], pred_secret=norm(ans[1]), true_secret=true_sec,
                queries=h.queries, correct=bool(ok), seconds=dt, qubits=width[0], err=err,
                p_answer=info.get('p_answer'), p_noise_normal=(info.get('p_noise') or [None])[0])


def summarise(rows):
    out = {}
    fam_acc = {}
    for f in FAMILIES:
        r = [x for x in rows if x["family"] == f]
        fam_acc[f] = float(np.mean([x["correct"] for x in r])) if r else None
    corr = [x for x in rows if x["correct"]]
    out["accuracy"] = float(np.mean([x["correct"] for x in rows]))
    out["worst_family_acc"] = min(v for v in fam_acc.values() if v is not None)
    out["query_saving"] = float(np.mean([1 - x["queries"] / 60 for x in corr])) if corr else 0.0
    out["mean_queries"] = float(np.mean([x["queries"] for x in rows]))
    out["family_acc"] = fam_acc
    out["family_mean_q"] = {f: float(np.mean([x["queries"] for x in rows if x["family"] == f]))
                            for f in FAMILIES}
    pa = [x["p_answer"] for x in rows if x.get("p_answer") is not None]
    out["mean_final_posterior"] = float(np.mean(pa)) if pa else None
    out["frac_stopped_early"] = float(np.mean([x["queries"] < 60 for x in rows]))
    out["max_seconds"] = float(max(x["seconds"] for x in rows))
    out["max_qubits"] = int(max(x["qubits"] for x in rows))
    out["n"] = len(rows)
    return out


def confusion(rows):
    M = np.zeros((8, 9), int)
    for x in rows:
        j = FAMILIES.index(x["pred"]) if x["pred"] in FAMILIES else 8
        M[FAMILIES.index(x["family"]), j] += 1
    return M


def finish_tau(a, jobs):
    """Run the tau sweep and write before(stress-only)/after(mixture) tables."""
    print(f"{len(jobs)} tasks on {a.workers} workers", flush=True)
    t0 = time.time()
    rows = []
    with ProcessPoolExecutor(a.workers) as ex:
        for i, r in enumerate(ex.map(run_task, jobs, chunksize=2)):
            rows.append(r)
            if (i + 1) % 200 == 0:
                print(f"  {i+1}/{len(jobs)}  {time.time()-t0:.0f}s", flush=True)
    with open(f"{LOG}/tasks.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader(); w.writerows(rows)
    G = {}
    for r in rows:
        G.setdefault((r["noise"], r["method"], r["tau"]), []).append(r)
    S = {k: summarise(v) for k, v in G.items()}
    json.dump({"|".join(map(str, k)): v for k, v in S.items()}, open(f"{LOG}/summary.json", "w"), indent=1)
    reps = len({r["rep"] for r in rows})
    md = [f"# Tau sweep: before (stress-only likelihood) vs after (noise mixture)\n",
          f"{reps} oracles per family per noise level, cap 60, fixed seeds; wall {time.time()-t0:.0f}s\n"]
    for noise in NOISE:
        md.append(f"\n## {noise} noise\n")
        md.append("| tau | solver | accuracy | worst family | mean queries | query saving | " +
                  " | ".join(f"q:{f}" for f in FAMILIES) + " |")
        md.append("|" + "---|" * (6 + len(FAMILIES)))
        for tau in (0.98, 0.99, 0.995):
            for meth, nm in (("full_stress", "before"), ("full", "after")):
                s = S[(noise, meth, tau)]
                md.append(f"| {tau} | {nm} | {s['accuracy']:.3f} | {s['worst_family_acc']:.3f} | "
                          f"{s['mean_queries']:.1f} | {s['query_saving']:.3f} | " +
                          " | ".join(f"{s['family_mean_q'][f]:.1f}" for f in FAMILIES) + " |")
        md.append("\nPer-family accuracy:\n")
        md.append("| tau | solver | " + " | ".join(FAMILIES) + " |\n|" + "---|" * (2 + len(FAMILIES)))
        for tau in (0.98, 0.99, 0.995):
            for meth, nm in (("full_stress", "before"), ("full", "after")):
                s = S[(noise, meth, tau)]
                md.append(f"| {tau} | {nm} | " + " | ".join(f"{s['family_acc'][f]:.3f}" for f in FAMILIES) + " |")
        for tau in (0.98, 0.99, 0.995):
            for meth, nm in (("full_stress", "before"), ("full", "after")):
                M = confusion(G[(noise, meth, tau)])
                np.savetxt(f"{LOG}/confusion_{noise}_{nm}_tau{tau}.csv", M, fmt="%d", delimiter=",",
                           header="rows=true cols=pred " + ",".join(FAMILIES) + ",none")
                wrong = [(FAMILIES[i], FAMILIES[j] if j < 8 else "none", int(M[i, j]))
                         for i in range(8) for j in range(9) if M[i, j] and (j >= 8 or i != j)]
                md.append(f"\nErrors, tau={tau} {nm}: " + (", ".join(f"{t}->{p} x{c}" for t, p, c in wrong) or "none"))
    open(f"{LOG}/tau_sweep_report.md", "w").write("\n".join(md) + "\n")
    print("\n".join(md))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--reps", type=int, default=12)
    ap.add_argument("--workers", type=int, default=os.cpu_count() or 4)
    ap.add_argument("--suite", default="all")
    ap.add_argument("--out", default="logs")
    a = ap.parse_args()
    global LOG
    LOG = a.out
    os.makedirs(LOG, exist_ok=True)
    import platform, qiskit, scipy
    json.dump(dict(python=platform.python_version(), qiskit=qiskit.__version__,
                   numpy=np.__version__, scipy=scipy.__version__, platform=platform.platform(),
                   seeds="oracle: default_rng([family_index, rep, 99]); harness: "
                         "default_rng([family_index, rep, noise_index, 7]); solver rng seed 12345",
                   reps=(2 if a.suite == 'quick' else a.reps), suite=a.suite, solver_tau=solver.TAU),
              open(f"{LOG}/versions.json", "w"), indent=1)
    jobs = []
    R = range(a.reps)
    if a.suite == "quick":
        R = range(2)
    if a.suite == "tau":
        for noise in NOISE:
            for meth in ("full_stress", "full"):
                for tau in (0.98, 0.99, 0.995):
                    for fam in FAMILIES:
                        for rep in R:
                            jobs.append((noise, meth, 60, tau, fam, rep))
        return finish_tau(a, jobs)
    for noise in NOISE:
        for fam in FAMILIES:
            for rep in R:
                jobs.append((noise, "full", 60, solver.TAU, fam, rep))
    if a.suite in ("all", "main"):
        for noise in NOISE:
            for cap in (20, 30, 40, 50):
                for fam in FAMILIES:
                    for rep in R:
                        jobs.append((noise, "full", cap, solver.TAU, fam, rep))
            for meth in ("classical", "single", "nonadaptive", "random"):
                for fam in FAMILIES:
                    for rep in R:
                        jobs.append((noise, meth, 60, solver.TAU, fam, rep))
    print(f"{len(jobs)} tasks on {a.workers} workers", flush=True)
    t0 = time.time()
    rows = []
    with ProcessPoolExecutor(a.workers) as ex:
        for i, r in enumerate(ex.map(run_task, jobs, chunksize=2)):
            rows.append(r)
            if (i + 1) % 200 == 0:
                print(f"  {i+1}/{len(jobs)}  {time.time()-t0:.0f}s", flush=True)
    with open(f"{LOG}/tasks.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader(); w.writerows(rows)
    G = {}
    for r in rows:
        G.setdefault((r["noise"], r["method"], r["tau"]), []).append(r)
    S = {k: summarise(v) for k, v in G.items()}
    json.dump({"|".join(map(str, k)): v for k, v in S.items()}, open(f"{LOG}/summary.json", "w"), indent=1)
    reps = len({r["rep"] for r in rows})
    md = [f"# Tau sweep: before (stress-only likelihood) vs after (noise mixture)\n",
          f"{reps} oracles per family per noise level, cap 60, fixed seeds; wall {time.time()-t0:.0f}s\n"]
    for noise in NOISE:
        md.append(f"\n## {noise} noise\n")
        md.append("| tau | solver | accuracy | worst family | mean queries | query saving | " +
                  " | ".join(f"q:{f}" for f in FAMILIES) + " |")
        md.append("|" + "---|" * (6 + len(FAMILIES)))
        for tau in (0.98, 0.99, 0.995):
            for meth, nm in (("full_stress", "before"), ("full", "after")):
                s = S[(noise, meth, tau)]
                md.append(f"| {tau} | {nm} | {s['accuracy']:.3f} | {s['worst_family_acc']:.3f} | "
                          f"{s['mean_queries']:.1f} | {s['query_saving']:.3f} | " +
                          " | ".join(f"{s['family_mean_q'][f]:.1f}" for f in FAMILIES) + " |")
        md.append("\nPer-family accuracy:\n")
        md.append("| tau | solver | " + " | ".join(FAMILIES) + " |\n|" + "---|" * (2 + len(FAMILIES)))
        for tau in (0.98, 0.99, 0.995):
            for meth, nm in (("full_stress", "before"), ("full", "after")):
                s = S[(noise, meth, tau)]
                md.append(f"| {tau} | {nm} | " + " | ".join(f"{s['family_acc'][f]:.3f}" for f in FAMILIES) + " |")
        for tau in (0.98, 0.99, 0.995):
            for meth, nm in (("full_stress", "before"), ("full", "after")):
                M = confusion(G[(noise, meth, tau)])
                np.savetxt(f"{LOG}/confusion_{noise}_{nm}_tau{tau}.csv", M, fmt="%d", delimiter=",",
                           header="rows=true cols=pred " + ",".join(FAMILIES) + ",none")
                wrong = [(FAMILIES[i], FAMILIES[j] if j < 8 else "none", int(M[i, j]))
                         for i in range(8) for j in range(9) if M[i, j] and (j >= 8 or i != j)]
                md.append(f"\nErrors, tau={tau} {nm}: " + (", ".join(f"{t}->{p} x{c}" for t, p, c in wrong) or "none"))
    open(f"{LOG}/tau_sweep_report.md", "w").write("\n".join(md) + "\n")
    print("\n".join(md))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--reps", type=int, default=12)
    ap.add_argument("--workers", type=int, default=os.cpu_count() or 4)
    ap.add_argument("--suite", default="all")
    ap.add_argument("--out", default="logs")
    a = ap.parse_args()
    global LOG
    LOG = a.out
    os.makedirs(LOG, exist_ok=True)
    import platform, qiskit, scipy
    json.dump(dict(python=platform.python_version(), qiskit=qiskit.__version__,
                   numpy=np.__version__, scipy=scipy.__version__, platform=platform.platform(),
                   seeds="oracle: default_rng([family_index, rep, 99]); harness: "
                         "default_rng([family_index, rep, noise_index, 7]); solver rng seed 12345",
                   reps=(2 if a.suite == 'quick' else a.reps), suite=a.suite, solver_tau=solver.TAU),
              open(f"{LOG}/versions.json", "w"), indent=1)
    jobs = []
    R = range(a.reps)
    if a.suite == "quick":
        R = range(2)
    if a.suite == "tau":
        for noise in NOISE:
            for meth in ("full_stress", "full"):
                for tau in (0.98, 0.99, 0.995):
                    for fam in FAMILIES:
                        for rep in R:
                            jobs.append((noise, meth, 60, tau, fam, rep))
        return finish_tau(a, jobs)
    for noise in NOISE:
        for fam in FAMILIES:
            for rep in R:
                jobs.append((noise, "full", 60, solver.TAU, fam, rep))
    if a.suite in ("all", "main"):
        for noise in NOISE:
            for cap in (20, 30, 40, 50):
                for fam in FAMILIES:
                    for rep in R:
                        jobs.append((noise, "full", cap, solver.TAU, fam, rep))
            for meth in ("classical", "single", "nonadaptive", "random"):
                for fam in FAMILIES:
                    for rep in R:
                        jobs.append((noise, meth, 60, solver.TAU, fam, rep))
            for tau in (0.95, 0.99):
                for fam in FAMILIES:
                    for rep in R:
                        jobs.append((noise, "full", 60, tau, fam, rep))
    print(f"{len(jobs)} tasks on {a.workers} workers", flush=True)
    t0 = time.time()
    rows = []
    with ProcessPoolExecutor(a.workers) as ex:
        for i, r in enumerate(ex.map(run_task, jobs, chunksize=2)):
            rows.append(r)
            if (i + 1) % 100 == 0:
                print(f"  {i+1}/{len(jobs)}  {time.time()-t0:.0f}s", flush=True)
    with open(f"{LOG}/tasks.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader(); w.writerows(rows)
    groups = {}
    for r in rows:
        groups.setdefault((r["noise"], r["method"], r["cap"], r["tau"]), []).append(r)
    summ = {"|".join(map(str, k)): summarise(v) for k, v in groups.items()}
    json.dump(summ, open(f"{LOG}/summary.json", "w"), indent=1)
    md = ["# Evaluation results (local oracles, generated by evaluate.py)\n",
          f"reps per family: {len(list(R))}; tasks: {len(rows)}; wall time {time.time()-t0:.0f}s\n"]
    for noise in NOISE:
        main_rows = groups[(noise, "full", 60, solver.TAU)]
        md.append(f"\n## Main solver, {noise} noise (cap 60, tau={solver.TAU})\n")
        s = summarise(main_rows)
        md.append(f"accuracy {s['accuracy']:.3f} | worst-family {s['worst_family_acc']:.3f} | "
                  f"query saving {s['query_saving']:.3f} | mean queries {s['mean_queries']:.1f} | "
                  f"max time/oracle {s['max_seconds']:.1f}s | max qubits {s['max_qubits']}\n")
        md.append("\n| family | accuracy | mean queries | stopped before 60 | mean final posterior |\n|---|---|---|---|---|")
        for f in FAMILIES:
            fr = [x for x in main_rows if x["family"] == f]
            pa = [x["p_answer"] for x in fr if x.get("p_answer") is not None]
            md.append(f"| {f} | {s['family_acc'][f]:.2f} | {s['family_mean_q'][f]:.1f} | "
                      f"{np.mean([x['queries'] < 60 for x in fr]):.2f} | {np.mean(pa):.3f} |")
        M = confusion(main_rows)
        md.append("\nConfusion matrix (rows true, cols predicted; last col = no answer):\n")
        md.append("| true \\ pred | " + " | ".join(FAMILIES) + " | none |\n|" + "---|" * 10)
        for i, f in enumerate(FAMILIES):
            md.append(f"| {f} | " + " | ".join(str(v) for v in M[i]) + " |")
        np.savetxt(f"{LOG}/confusion_{noise}.csv", M, fmt="%d", delimiter=",",
                   header="rows=true cols=pred " + ",".join(FAMILIES) + ",none")
    if a.suite in ("all", "main"):
        md.append("\n## Accuracy vs budget cap (full solver; query saving always vs 60)\n")
        md.append("| noise | cap | accuracy | worst family | query saving | mean queries |\n|---|---|---|---|---|---|")
        for noise in NOISE:
            for cap in (20, 30, 40, 50, 60):
                s = summ[f"{noise}|full|{cap}|{solver.TAU}"]
                md.append(f"| {noise} | {cap} | {s['accuracy']:.3f} | {s['worst_family_acc']:.3f} | "
                          f"{s['query_saving']:.3f} | {s['mean_queries']:.1f} |")
        md.append("\n## Baselines (cap 60)\n")
        md.append("| noise | method | accuracy | worst family | query saving | mean queries |\n|---|---|---|---|---|---|")
        names = {"full": "ours (noise mixture)", "full_stress": "ours, stress-only likelihood (before)", "classical": "(1) classical-only", "single": "(2) single algorithm",
                 "random": "(3) random guessing", "nonadaptive": "(4) ours, adaptivity off"}
        for noise in NOISE:
            for meth in ("full", "classical", "single", "random", "nonadaptive"):
                s = summ[f"{noise}|{meth}|60|{solver.TAU}"]
                md.append(f"| {noise} | {names[meth]} | {s['accuracy']:.3f} | {s['worst_family_acc']:.3f} | "
                          f"{s['query_saving']:.3f} | {s['mean_queries']:.1f} |")
        md.append("\n## Per-family accuracy for baselines (cap 60)\n")
        md.append("| noise | method | " + " | ".join(FAMILIES) + " |\n|" + "---|" * (len(FAMILIES) + 2))
        for noise in NOISE:
            for meth in ("full", "classical", "single", "random", "nonadaptive"):
                s = summ[f"{noise}|{meth}|60|{solver.TAU}"]
                md.append(f"| {noise} | {meth} | " + " | ".join(f"{s['family_acc'][f]:.2f}" for f in FAMILIES) + " |")
    open(f"{LOG}/evaluation_report.md", "w").write("\n".join(md) + "\n")
    print("\n".join(md))


if __name__ == "__main__":
    main()

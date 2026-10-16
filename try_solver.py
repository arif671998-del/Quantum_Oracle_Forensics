"""Try solver.py by hand on local oracles and watch what it does.

In VS Code: open this file and press the Run button (top right), or run in the terminal:

    .venv/bin/python try_solver.py                         # one oracle of every family, normal noise
    .venv/bin/python try_solver.py --family grover --verbose
    .venv/bin/python try_solver.py --noise stress --reps 5
    .venv/bin/python try_solver.py --family linear --secret 178,1 --verbose
    .venv/bin/python try_solver.py --family simon2 --secret 15,49 --noise off

At the end it checks every answer against the required (family, secret) format and the
rules: query budget, at most 20 qubits, measurements only at the end, 120 s per oracle.

The settings below are used when no command-line options are given, so you can also just
edit them and press Run. Not part of the submission: solver.py never imports this file.
"""
import argparse
import time

import numpy as np

import solver
from oracle_sim import FAMILIES, M_OF, BudgetExceeded, Harness, make_oracle

# ---------------------------------------------------------------- settings for the Run button
FAMILY = "all"      # "all" or one of: constant balanced linear grover randfun simon simon2 perm
NOISE = "normal"    # "normal" (4% misfire, 2% readout), "stress" (8%, 4%) or "off" (no noise)
REPS = 1            # oracles per family
SEED = 2026         # change it to get different random oracles
VERBOSE = False     # True: print every query the solver makes
BUDGET = 60

NOISE_LEVELS = {"normal": (0.04, 0.02), "stress": (0.08, 0.04), "off": (0.0, 0.0)}
HAS_SECRET = {"constant", "linear", "grover", "simon", "simon2"}


def same_secret(a, b):
    """Compare secrets the way the judges do (lists/tuples become plain int lists)."""
    def norm(s):
        if s is None:
            return None
        if isinstance(s, (list, tuple, np.ndarray)):
            return [int(v) for v in s]
        return int(s)
    return norm(a) == norm(b)


def fixed_secret(family, text):
    """--secret for the families that have one: c | a,b | t | s | h1,h2 (simon2 generators)."""
    if not text:
        return {}
    v = [int(p) for p in text.split(",")]
    return {"constant": {"c": v[0]}, "linear": {"a": v[0], "b": v[1]}, "grover": {"t": v[0]},
            "simon": {"s": v[0]}, "simon2": {"H": v[:2]}}.get(family, {})


def format_problem(family, secret):
    """Check an answer against the secret formats of the problem statement ('' = fine)."""
    def isint(v):
        return type(v) is int            # plain Python int (not bool, not numpy int)
    if family not in FAMILIES:
        return f"family {family!r} is not one of the 8 family names"
    if family == "constant":
        ok = isint(secret) and secret in (0, 1)
    elif family == "linear":
        ok = (type(secret) is list and len(secret) == 2 and all(map(isint, secret))
              and 1 <= secret[0] <= 255 and secret[1] in (0, 1))
    elif family == "grover":
        ok = isint(secret) and 0 <= secret <= 255
    elif family == "simon":
        ok = isint(secret) and 1 <= secret <= 255
    elif family == "simon2":
        ok = (type(secret) is list and len(secret) == 3 and all(map(isint, secret))
              and secret == sorted(secret) and 0 not in secret and secret[0] ^ secret[1] == secret[2])
    else:                                 # balanced, randfun, perm
        ok = secret is None
    return "" if ok else f"secret {secret!r} ({type(secret).__name__}) has the wrong format for {family}"


def describe(circuit, shots, counts):
    """One line per run() call: what kind of circuit, how many queries, the top outcomes."""
    k = sum(1 for ins in circuit.data if ins.operation.name == "oracle")
    has_h = any(ins.operation.name == "h" for ins in circuit.data)
    kind = "classical read" if not has_h else ("probe (BV/Simon)" if k == 1 else f"{k} oracle calls")
    top = sorted(counts.items(), key=lambda kv: -kv[1])[:4]
    return f"{circuit.num_qubits:2d} qubits, {kind:16s} x {shots} shot(s) -> {top}"


def try_one(family, noise, seed, verbose, secret_text=""):
    rng = np.random.default_rng(seed)
    oracle = make_oracle(family, rng, **fixed_secret(family, secret_text))
    p_oracle, p_read = NOISE_LEVELS[noise]
    harness = Harness(oracle, budget=BUDGET, p_oracle=p_oracle, p_read=p_read, seed=seed + 1)

    rules = {"max_qubits": 0, "measure_at_end": True}

    def run(circuit, shots):
        rules["max_qubits"] = max(rules["max_qubits"], circuit.num_qubits)
        measured = False
        for ins in circuit.data:                     # rule: measurements only at the end
            if ins.operation.name == "measure":
                measured = True
            elif measured and ins.operation.name != "barrier":
                rules["measure_at_end"] = False
        before = harness.queries
        counts = harness.run(circuit, shots)
        if verbose:
            print(f"   q{before + 1:>2}-{harness.queries:<2} {describe(circuit, shots, counts)}")
        return counts

    m = M_OF[family]
    t0 = time.time()
    try:
        fam, sec = solver.solve(8, m, BUDGET, FAMILIES, run)
    except BudgetExceeded:
        fam, sec, over = None, None, True
    else:
        over = False
    secs = time.time() - t0
    correct = fam == family and (family not in HAS_SECRET or same_secret(sec, oracle.secret))
    return dict(family=family, true_secret=oracle.secret, answer=fam, answer_secret=sec,
                queries=harness.queries, seconds=secs, correct=correct, over_budget=over,
                format_error="budget exceeded" if over else format_problem(fam, sec), **rules)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--family", default=FAMILY)
    ap.add_argument("--noise", default=NOISE, choices=list(NOISE_LEVELS))
    ap.add_argument("--reps", type=int, default=REPS)
    ap.add_argument("--seed", type=int, default=SEED)
    ap.add_argument("--secret", default="", help="fix the secret, e.g. 178,1 for linear")
    ap.add_argument("--verbose", action="store_true", default=VERBOSE)
    a = ap.parse_args()

    families = FAMILIES if a.family == "all" else [a.family]
    print(f"noise = {a.noise} {NOISE_LEVELS[a.noise]}, budget = {BUDGET}, seed = {a.seed}\n")
    results = []
    for fam in families:
        for r in range(a.reps):
            if a.verbose:
                print(f"--- {fam} (oracle {r + 1}) ---")
            res = try_one(fam, a.noise, a.seed + 1000 * r + FAMILIES.index(fam), a.verbose, a.secret)
            results.append(res)
            mark = "OK   " if res["correct"] else "WRONG"
            print(f"{mark} {fam:9s} true secret {str(res['true_secret']):16s} -> answer "
                  f"({res['answer']}, {res['answer_secret']})  {res['queries']:2d} queries  "
                  f"{res['seconds']:.1f} s")
            if res["format_error"]:
                print(f"      FORMAT PROBLEM: {res['format_error']}")
            info = solver.LAST_INFO
            if a.verbose and "p_noise" in info:
                print(f"   posterior of the answer {info['p_answer']:.3f}; "
                      f"P(noise is normal, not stress) = {info['p_noise'][0]:.2f}\n")
    n_ok = sum(r["correct"] for r in results)
    mean_q = np.mean([r["queries"] for r in results])
    print(f"\n{n_ok}/{len(results)} correct, mean queries {mean_q:.1f}")

    def tick(ok):
        return "OK  " if ok else "FAIL"
    n = len(results)
    n_fmt = sum(not r["format_error"] for r in results)
    max_q = max(r["queries"] for r in results)
    max_qb = max(r["max_qubits"] for r in results)
    max_t = max(r["seconds"] for r in results)
    at_end = all(r["measure_at_end"] for r in results)
    print("\nChecks against the problem statement:")
    print(f"  {tick(n_fmt == n)} answers in the required (family, secret) format: {n_fmt}/{n}")
    print(f"  {tick(max_q <= BUDGET)} most queries used on one oracle: {max_q} (budget {BUDGET})")
    print(f"  {tick(max_qb <= 20)} most qubits in one circuit: {max_qb} (limit 20)")
    print(f"  {tick(at_end)} measurements only at the end of every circuit")
    print(f"  {tick(max_t <= 120)} slowest oracle: {max_t:.1f} s (limit 120 s)")


if __name__ == "__main__":
    main()

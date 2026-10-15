"""Budget split per family: which queries the frozen solver spends them on.
Classifies each run() call from the circuit structure (solver.py is not modified)."""
import sys, json
import numpy as np
import solver
from oracle_sim import make_oracle, Harness, FAMILIES, M_OF

def classify(circ):
    ops = [i.operation.name for i in circ.data]
    k = ops.count("oracle")
    has_h = "h" in ops
    nc = circ.num_clbits
    if circ.num_qubits == 9:
        if nc == 1: return "read", 1
        if nc == 9: return "g1", 2
        return ("bv", 1) if k == 1 else (f"grover", k)
    return ("probe", 1) if has_h else ("read8", 1)

def main(reps=20):
    out = {}
    for noise, (po, pr) in (("normal", (.04, .02)), ("stress", (.08, .04))):
        for fam in FAMILIES:
            tot = {}
            for rep in range(reps):
                o = make_oracle(fam, np.random.default_rng([FAMILIES.index(fam), rep, 99]))
                h = Harness(o, 60, po, pr, seed=int(np.random.default_rng([FAMILIES.index(fam), rep, 5]).integers(1 << 30)))
                inner = h.run
                def run(c, s, inner=inner):
                    n, cost = classify(c)
                    tot[n] = tot.get(n, 0) + cost * s
                    return inner(c, s)
                solver.solve(8, M_OF[fam], 60, FAMILIES, run)
            out[f"{noise}|{fam}"] = {k: round(v / reps, 1) for k, v in sorted(tot.items())}
    json.dump(out, open("logs_budget_split.json", "w"), indent=1)
    print("| noise | family | queries by action (mean per oracle) |\n|---|---|---|")
    for k, v in out.items():
        n, f = k.split("|")
        print(f"| {n} | {f} | " + ", ".join(f"{a}: {b}" for a, b in v.items()) + " |")

main(int(sys.argv[1]) if len(sys.argv) > 1 else 20)

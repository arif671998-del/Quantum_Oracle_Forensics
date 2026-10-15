"""Fill the <<T_*>> markers of REPORT.md.template-style REPORT.md from logs/ (numbers are copied, never typed)."""
import csv, json, sys
import numpy as np

FAM = ["constant", "balanced", "linear", "grover", "randfun", "simon", "simon2", "perm"]
S = json.load(open("logs/summary.json"))
TAU = "0.98"
rows = list(csv.DictReader(open("logs/tasks.csv")))
V = json.load(open("logs/versions.json"))
reps = V["reps"]
def g(noise, meth="full", cap=60): return S[f"{noise}|{meth}|{cap}|{TAU}"]

def t_main():
    out = [f"Main solver (cap 60, tau {TAU}), {reps} oracles per family per noise level.\n",
           "| family | acc normal | mean q normal | acc stress | mean q stress |", "|---|---|---|---|---|"]
    n, s = g("normal"), g("stress")
    for f in FAM:
        out.append(f"| {f} | {n['family_acc'][f]:.2f} | {n['family_mean_q'][f]:.1f} | "
                   f"{s['family_acc'][f]:.2f} | {s['family_mean_q'][f]:.1f} |")
    out.append(f"| **all** | **{n['accuracy']:.3f}** | **{n['mean_queries']:.1f}** | "
               f"**{s['accuracy']:.3f}** | **{s['mean_queries']:.1f}** |")
    out.append(f"\nWorst-family accuracy: normal {n['worst_family_acc']:.2f}, stress {s['worst_family_acc']:.2f}. "
               f"Query saving (correct tasks, vs 60): normal {n['query_saving']:.3f}, stress {s['query_saving']:.3f}. "
               f"Max time per oracle {max(n['max_seconds'], s['max_seconds']):.1f} s; max qubits "
               f"{max(n['max_qubits'], s['max_qubits'])}.")
    return "\n".join(out)

def t_caps():
    out = ["**Accuracy as a function of the query cap** (solver told budget = cap; saving always vs 60):\n",
           "| cap | acc normal | worst fam | mean q | acc stress | worst fam | mean q |", "|---|---|---|---|---|---|---|"]
    for cap in (20, 30, 40, 50, 60):
        n, s = g("normal", cap=cap), g("stress", cap=cap)
        out.append(f"| {cap} | {n['accuracy']:.3f} | {n['worst_family_acc']:.2f} | {n['mean_queries']:.1f} | "
                   f"{s['accuracy']:.3f} | {s['worst_family_acc']:.2f} | {s['mean_queries']:.1f} |")
    return "\n".join(out)

NAMES = {"full": "ours", "classical": "(1) classical-only (no superposition)",
         "single": "(2) single algorithm (BV/Simon probe only)", "random": "(3) random guessing",
         "nonadaptive": "(4) ours, adaptivity off (fixed schedule, no early stop)"}
def t_base():
    out = ["| method | acc normal | worst fam | saving | acc stress | worst fam | saving |", "|---|---|---|---|---|---|---|"]
    for m in NAMES:
        n, s = g("normal", m), g("stress", m)
        out.append(f"| {NAMES[m]} | {n['accuracy']:.3f} | {n['worst_family_acc']:.2f} | {n['query_saving']:.3f} | "
                   f"{s['accuracy']:.3f} | {s['worst_family_acc']:.2f} | {s['query_saving']:.3f} |")
    return "\n".join(out)

def t_base_text():
    out = ["Per-family accuracy at cap 60 (normal / stress):\n",
           "| method | " + " | ".join(FAM) + " |", "|" + "---|" * (len(FAM) + 1)]
    for m in NAMES:
        n, s = g("normal", m), g("stress", m)
        out.append(f"| {m} | " + " | ".join(f"{n['family_acc'][f]:.2f} / {s['family_acc'][f]:.2f}" for f in FAM) + " |")
    n, c = g("normal", "full"), g("normal", "classical")
    sg = g("normal", "single")
    out.append(
        f"\nA classical-only strategy (same inference, reads only; birthday search for m=8) reaches "
        f"{c['accuracy']:.2f} (normal): it is adequate for constant ({c['family_acc']['constant']:.2f}), "
        f"balanced ({c['family_acc']['balanced']:.2f}) and linear ({c['family_acc']['linear']:.2f}) but "
        f"fails where structure is hidden in a single input or an XOR period: grover "
        f"{c['family_acc']['grover']:.2f}, simon {c['family_acc']['simon']:.2f}, simon2 "
        f"{c['family_acc']['simon2']:.2f}, perm {c['family_acc']['perm']:.2f}. A single quantum circuit "
        f"reused for everything reaches {sg['accuracy']:.2f}: it cannot learn the phase-invisible secrets "
        f"(constant c, linear b) nor find a grover item (grover {sg['family_acc']['grover']:.2f}). "
        f"Switching adaptivity off costs {n['accuracy'] - g('normal','nonadaptive')['accuracy']:+.3f} accuracy "
        f"(normal) and all query saving.")
    return "\n".join(out)

def t_fail():
    out = []
    for noise in ("normal", "stress"):
        rs = [r for r in rows if r["noise"] == noise and r["method"] == "full" and int(r["cap"]) == 60]
        errs = {}
        for r in rs:
            if r["correct"] != "True":
                key = f"{r['family']} -> {r['pred']}" + ("" if r["pred"] == r["family"] else "")
                if r["pred"] == r["family"]:
                    key = f"{r['family']} (right family, wrong secret)"
                errs[key] = errs.get(key, 0) + 1
        tot = len(rs)
        out.append(f"* **{noise}**: {sum(errs.values())} wrong of {tot}: " +
                   ("; ".join(f"{k} x{v}" for k, v in sorted(errs.items(), key=lambda kv: -kv[1])) or "none") + ".")
    out.append("""
Reading: **grover -> constant** is the dominant structural error: a 1-in-256 item that the
2-4 affordable Grover shots miss is indistinguishable from constant 0, and the posterior is
right to fall back on it. **balanced <-> randfun** is the weakest-signal pair: it rests on a
zero-string count and one-bit statistics, with randfun's ones-fraction overlapping balanced
only at its tails. **simon -> perm / simon2** occurs when the period's weight is large
(|s| near 8), where readout noise makes violating samples common. Fixes we did not make:
spending more shots on Grover costs queries on every constant-0 task; a lower tau would
convert some of these into early wrong answers.""")
    return "\n".join(out)

def t_tau():
    T = json.load(open("logs_tau/summary.json"))
    out = ["", "| tau (mixture, pooled both noises, 640 oracles) | accuracy | mean queries | worst family |", "|---|---|---|---|"]
    for t in ("0.98", "0.99", "0.995"):
        a = [T[f"{n}|full|{t}"] for n in ("normal", "stress")]
        out.append(f"| {t} | {np.mean([x['accuracy'] for x in a]):.4f} | "
                   f"{np.mean([x['mean_queries'] for x in a]):.1f} | {min(x['worst_family_acc'] for x in a):.3f} |")
    out.append("")
    return "\n".join(out)

def t_budget():
    try:
        B = json.load(open("logs_budget_split.json"))
    except FileNotFoundError:
        return "(budget split not available)"
    out = ["**Budget split** (mean queries per oracle spent on each action, normal noise; the "
           "rest of the 60 is unspent):\n", "| family | queries by action |", "|---|---|"]
    for f in FAM:
        v = B[f"normal|{f}"]
        out.append(f"| {f} | " + ", ".join(f"{a} {b}" for a, b in v.items()) + " |")
    return "\n".join(out)

txt = open("REPORT.md").read()
for k, fn in (("T_MAIN", t_main), ("T_CAPS", t_caps), ("T_BASE", t_base), ("T_BASE_TEXT", t_base_text),
              ("T_FAIL", t_fail), ("T_TAU", t_tau), ("T_BUDGET", t_budget)):
    txt = txt.replace(f"<<{k}>>", fn())
open("REPORT_filled.md", "w").write(txt)
print("wrote REPORT_filled.md;", len(txt.split()), "words")

"""Tests for oracle_sim.py: section 4 examples, family properties, noise model."""
import numpy as np
from qiskit import QuantumCircuit
from oracle_sim import (FAMILIES, make_oracle, oracle_from_function, Harness,
                        BudgetExceeded, new_oracle_gate, _parity)

rng = np.random.default_rng(1)
ok = True


def check(name, cond):
    global ok
    ok &= bool(cond)
    print(("PASS " if cond else "FAIL ") + name)


# ---- section 4 reference values
lin = oracle_from_function("linear", lambda x: _parity(178 & x) ^ 1)
check("linear a=178,b=1", [lin.table[v] for v in (0, 1, 2, 255)] == [1, 1, 0, 1])
s = 105
sim = oracle_from_function("simon", lambda x: min(x, x ^ s))
check("simon s=105", [sim.table[v] for v in (5, 108, 105, 200)] == [5, 5, 0, 161])
H = {0, 15, 49, 62}
s2 = oracle_from_function("simon2", lambda x: min(x ^ h for h in H))
check("simon2 H", [s2.table[v] for v in (0, 15, 49, 62, 1, 200)] == [0, 0, 0, 0, 1, 199])
pm = oracle_from_function("perm", lambda x: (37 * x + 11) % 256)
check("perm (37x+11)", [pm.table[v] for v in (0, 1, 2, 255)] == [11, 48, 85, 230])
gr = make_oracle("grover", rng, t=173)
check("grover t=173", gr.table[173] == 1 and gr.table.sum() == 1)
co = make_oracle("constant", rng, c=1)
check("constant c=1", (co.table == 1).all())

# ---- family properties on random instances
for _ in range(50):
    o = make_oracle("balanced", rng); assert o.table.sum() == 128
    o = make_oracle("linear", rng); a, b = o.secret
    assert 1 <= a <= 255 and all(o.table[x] == _parity(a & x) ^ b for x in range(256))
    o = make_oracle("simon", rng); s = o.secret
    t = o.table
    assert all(t[x] == t[x ^ s] for x in range(256))
    assert len(set(t)) == 128                       # otherwise all distinct
    o = make_oracle("simon2", rng); h1, h2, h3 = o.secret
    assert h1 ^ h2 == h3 and list(o.secret) == sorted(o.secret)
    t = o.table; Hs = [0, h1, h2, h3]
    assert all(t[x] == t[x ^ h] for x in range(256) for h in Hs)
    assert len(set(t)) == 64                        # 4-to-1
    o = make_oracle("perm", rng); assert sorted(o.table) == list(range(256))
fr = np.mean([make_oracle("randfun", rng).table.mean() for _ in range(200)])
check(f"randfun mean ones {fr:.3f} ~ 0.3", abs(fr - 0.3) < 0.01)
check("family properties (50 random instances each)", True)


# ---- noise-free Bernstein-Vazirani: should return a with certainty
def bv_circuit(m=1):
    qc = QuantumCircuit(8 + m, 8)
    qc.x(8); qc.h(range(9))
    qc.append(new_oracle_gate(8, 1), range(9))
    qc.h(range(8)); qc.measure(range(8), range(8))
    return qc


a, b = 178, 1
o = oracle_from_function("linear", lambda x: _parity(a & x) ^ b)
h = Harness(o, budget=10**9, p_oracle=0, p_read=0, seed=3)
c = h.run(bv_circuit(), 50)
check(f"BV noiseless -> {c}", c == {format(a, "08b"): 50})

# ---- noise rates
# constant c=1, circuit: oracle on |0>|0>, measure output. P(1)=0.96*0.98+0.04*0.02
qc = QuantumCircuit(9, 1)
qc.append(new_oracle_gate(8, 1), range(9)); qc.measure(8, 0)
h = Harness(make_oracle("constant", rng, c=1), budget=10**9, seed=4)
c = h.run(qc, 200000)
p1 = c.get("1", 0) / 200000
exp = 0.96 * 0.98 + 0.04 * 0.02
check(f"oracle+readout noise P(1)={p1:.4f} expected {exp:.4f}", abs(p1 - exp) < 0.003)
check("query counter k*s", h.queries == 200000)

# readout only on 8 bits: BV with p_oracle=0, p_read=0.02 -> all-correct prob 0.98^8
h = Harness(o, budget=10**9, p_oracle=0, p_read=0.02, seed=5)
c = h.run(bv_circuit(), 100000)
pc = c.get(format(a, "08b"), 0) / 100000
check(f"BV readout only P(correct)={pc:.4f} expected {0.98**8:.4f}", abs(pc - 0.98 ** 8) < 0.004)

# budget enforcement and multi-oracle-gate cost
h = Harness(o, budget=60, seed=6)
q2 = QuantumCircuit(9, 8); q2.append(new_oracle_gate(8, 1), range(9)); q2.append(new_oracle_gate(8, 1), range(9))
try:
    h.run(q2, 31); check("budget exceeded raises", False)
except BudgetExceeded:
    check("budget exceeded raises (2 gates x 31 shots = 62 > 60)", True)

print("\nALL PASS" if ok else "\nSOME FAILED")

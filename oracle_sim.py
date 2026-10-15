"""Local noisy oracle simulator for QryptoNox "Quantum Oracle Forensics" (section 3).

Not part of the submitted solver: solver.py must only use run() it is given.
"""
import numpy as np
from qiskit import QuantumCircuit
from qiskit.quantum_info import Statevector

N = 8
FAMILIES = ["constant", "balanced", "linear", "grover",
            "randfun", "simon", "simon2", "perm"]
M_OF = {"constant": 1, "balanced": 1, "linear": 1, "grover": 1,
        "randfun": 1, "simon": 8, "simon2": 8, "perm": 8}
SECRETS = {"constant", "linear", "grover", "simon", "simon2"}


class BudgetExceeded(Exception):
    pass


# ---------------------------------------------------------------- oracles
class Oracle:
    """f given as a table of 256 ints, plus the true family and secret."""

    def __init__(self, family, table, secret=None):
        self.family = family
        self.table = np.asarray(table, dtype=np.int64)
        self.secret = secret
        self.m = M_OF[family]


def _parity(v):
    return bin(int(v)).count("1") & 1


def make_oracle(family, rng, **fixed):
    xs = np.arange(256)
    if family == "constant":
        c = int(fixed.get("c", rng.integers(2)))
        return Oracle(family, np.full(256, c), c)
    if family == "balanced":
        t = np.zeros(256, dtype=np.int64)
        t[rng.choice(256, 128, replace=False)] = 1
        return Oracle(family, t, None)
    if family == "linear":
        a = int(fixed.get("a", rng.integers(1, 256)))
        b = int(fixed.get("b", rng.integers(2)))
        t = np.array([_parity(a & x) ^ b for x in xs])
        return Oracle(family, t, (a, b))
    if family == "grover":
        tt = int(fixed.get("t", rng.integers(256)))
        t = np.zeros(256, dtype=np.int64)
        t[tt] = 1
        return Oracle(family, t, tt)
    if family == "randfun":
        return Oracle(family, (rng.random(256) < 0.3).astype(np.int64), None)
    if family == "simon":
        s = int(fixed.get("s", rng.integers(1, 256)))
        t = np.zeros(256, dtype=np.int64)
        reps = [x for x in range(256) if x < (x ^ s)]       # 128 pairs
        vals = rng.choice(256, len(reps), replace=False)
        for x, v in zip(reps, vals):
            t[x] = t[x ^ s] = v
        return Oracle(family, t, s)
    if family == "simon2":
        if "H" in fixed:
            a, b = sorted(fixed["H"])[:2]
        else:
            while True:
                a, b = (int(v) for v in rng.integers(1, 256, 2))
                if a != b:
                    break
        H = sorted({a, b, a ^ b})
        Hfull = [0] + H
        t = np.full(256, -1, dtype=np.int64)
        reps = [x for x in range(256) if x == min(x ^ h for h in Hfull)]  # 64
        vals = rng.choice(256, len(reps), replace=False)
        for x, v in zip(reps, vals):
            for h in Hfull:
                t[x ^ h] = v
        return Oracle(family, t, tuple(H))
    if family == "perm":
        return Oracle(family, rng.permutation(256), None)
    raise ValueError(family)


def oracle_from_function(family, fn, secret=None):
    return Oracle(family, [fn(x) for x in range(256)], secret)


# ---------------------------------------------------------------- simulator
def _apply_oracle(psi, qubits, n, m, table):
    """|x>|y> -> |x>|y xor f(x)> on a flat statevector (qubit k = bit k)."""
    idx = np.arange(psi.size)
    x = np.zeros(psi.size, dtype=np.int64)
    for j in range(n):
        x |= ((idx >> qubits[j]) & 1) << j
    shift = np.zeros(psi.size, dtype=np.int64)
    fx = table[x]
    for j in range(m):
        shift |= ((fx >> j) & 1) << qubits[n + j]
    out = np.empty_like(psi)
    out[idx ^ shift] = psi
    return out


class Harness:
    """Provides run(circuit, shots) for one sealed oracle, counting queries."""

    def __init__(self, oracle, budget=60, p_oracle=0.04, p_read=0.02, seed=None):
        self.oracle = oracle
        self.budget = budget
        self.p_oracle = p_oracle
        self.p_read = p_read
        self.rng = np.random.default_rng(seed)
        self.queries = 0

    def run(self, circuit, shots):
        n, m = N, self.oracle.m
        k = sum(1 for ins in circuit.data if ins.operation.name == "oracle")
        self.queries += k * shots
        if self.queries > self.budget:
            raise BudgetExceeded(f"{self.queries} > {self.budget}")
        for ins in circuit.data:
            if ins.operation.name == "oracle":
                assert ins.operation.num_qubits == n + m, "oracle width"
        nq = circuit.num_qubits
        # measurement map: clbit -> qubit
        cl2q = {}
        for ins in circuit.data:
            if ins.operation.name == "measure":
                cl2q[circuit.find_bit(ins.clbits[0]).index] = \
                    circuit.find_bit(ins.qubits[0]).index
        ncl = circuit.num_clbits
        # split into segments of ordinary gates between oracle calls
        segs, orcl, cur = [], [], QuantumCircuit(nq)
        for ins in circuit.data:
            nm = ins.operation.name
            qs = [circuit.find_bit(q).index for q in ins.qubits]
            if nm == "oracle":
                segs.append(cur)
                orcl.append(qs)
                cur = QuantumCircuit(nq)
            elif nm in ("measure", "barrier"):
                continue
            else:
                cur.append(ins.operation, qs)
        segs.append(cur)
        # per-shot misfire pattern, grouped
        miss = self.rng.random((shots, max(k, 1))) < self.p_oracle
        miss = miss[:, :k]
        pats, counts = np.unique(miss, axis=0, return_counts=True) if k \
            else (np.zeros((1, 0), bool), np.array([shots]))
        qargs = [cl2q[c] for c in sorted(cl2q)]
        cls = sorted(cl2q)
        out = np.zeros(shots, dtype=np.int64)
        pos = 0
        for pat, cnt in zip(pats, counts):
            sv = Statevector.from_int(0, 2 ** nq)
            sv = sv.evolve(segs[0])
            for i in range(k):
                if not pat[i]:
                    psi = _apply_oracle(np.asarray(sv.data), orcl[i], n, m,
                                        self.oracle.table)
                    sv = Statevector(psi)
                sv = sv.evolve(segs[i + 1])
            probs = sv.probabilities(qargs) if qargs else np.array([1.0])
            probs = probs / probs.sum()
            samp = self.rng.choice(probs.size, size=int(cnt), p=probs)
            word = np.zeros(int(cnt), dtype=np.int64)
            for j, c in enumerate(cls):
                word |= ((samp >> j) & 1) << c
            out[pos:pos + cnt] = word
            pos += cnt
        # readout flips on measured bits only
        for c in cls:
            flip = self.rng.random(shots) < self.p_read
            out ^= flip.astype(np.int64) << c
        keys, vals = np.unique(out, return_counts=True)
        return {format(int(kk), f"0{ncl}b"): int(v) for kk, v in zip(keys, vals)}


def new_oracle_gate(n=8, m=1):
    from qiskit.circuit import Gate
    return Gate("oracle", n + m, [])

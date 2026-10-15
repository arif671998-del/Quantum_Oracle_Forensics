"""QryptoNox Quantum Oracle Forensics - solver.

solve(n, m, budget, families, run) -> (family, secret)

Strategy (see REPORT.md): keep an exact Bayesian posterior over every
(family, secret) hypothesis consistent with m; each query is picked by expected
information gain per unit query cost; stop when the best hypothesis passes TAU
and the family-specific confirmations (classical re-reads) are satisfied.
All likelihoods assume the *stress* noise (8% misfire, 4% readout flip), so the
same code is calibrated for both the normal and the doubled-noise setting.

Only qiskit, numpy and the standard library are used; nothing outside this file
is read, and every decision is made from results returned by run().
"""
import numpy as np
from qiskit import QuantumCircuit
from qiskit.circuit import Gate

N = 8
STRESS = (0.08, 0.04)   # (oracle misfire, readout flip) in the stress setting
NORMAL = (0.04, 0.02)   # normal setting
NOISES = (NORMAL, STRESS)   # noise level is a hidden variable: 50/50 prior mixture
TAU = 0.98          # posterior needed to stop (chosen by the paired tau sweep, logs_tau/)
GROVER_KS = (2, 4, 6, 8, 10, 12)

_pc = np.array([bin(i).count("1") for i in range(256)])
_X = np.arange(256)
PAR = _pc[_X[:, None] & _X[None, :]] & 1            # PAR[a, x] = a.x mod 2
HAM = _pc[_X[:, None] ^ _X[None, :]]


def _noise_matrix(r):
    return (r ** HAM) * ((1 - r) ** (8 - HAM))      # [observed, true]




# ------------------------------------------------------------------ circuits
def _gate(m):
    return Gate("oracle", N + m, [])


def _diffusion(qc):
    qc.h(range(8)); qc.x(range(8))
    qc.h(7); qc.mcx(list(range(7)), 7); qc.h(7)
    qc.x(range(8)); qc.h(range(8))


def c_bv():
    """Bernstein-Vazirani / Deutsch-Jozsa probe (m=1): measures the Walsh index."""
    qc = QuantumCircuit(9, 8)
    qc.x(8); qc.h(range(9))
    qc.append(_gate(1), range(9))
    qc.h(range(8)); qc.measure(range(8), range(8))
    return qc


def c_read1(x):
    """Classical query of f(x) for m=1; result on the single clbit."""
    qc = QuantumCircuit(9, 1)
    for i in range(8):
        if (x >> i) & 1:
            qc.x(i)
    qc.append(_gate(1), range(9))
    qc.measure(8, 0)
    return qc


def c_grover(k):
    qc = QuantumCircuit(9, 8)
    qc.x(8); qc.h(range(9))
    for _ in range(k):
        qc.append(_gate(1), range(9))
        _diffusion(qc)
    qc.measure(range(8), range(8))
    return qc


def c_g1():
    """One Grover iteration then a classical read of f(z) at the sampled z.
    Costs 2 queries; outcome index = z + 256 * bit."""
    qc = QuantumCircuit(9, 9)
    qc.x(8); qc.h(range(9))
    qc.append(_gate(1), range(9))
    _diffusion(qc)
    qc.h(8); qc.x(8)                       # |-> -> |0> for the bit-flip read
    qc.append(_gate(1), range(9))
    qc.measure(range(8), range(8)); qc.measure(8, 8)
    return qc


def c_simon():
    qc = QuantumCircuit(16, 8)
    qc.h(range(8))
    qc.append(_gate(8), range(16))
    qc.h(range(8)); qc.measure(range(8), range(8))
    return qc


def c_read8(x):
    qc = QuantumCircuit(16, 8)
    for i in range(8):
        if (x >> i) & 1:
            qc.x(i)
    qc.append(_gate(8), range(16))
    qc.measure(range(8, 16), range(8))
    return qc


# --------------------------------------------------------------- model maths
def grover_ps(k, pm):
    """P(measure the marked item) after k Grover iterations with per-oracle
    misfire probability pm (exact enumeration of misfire patterns, 2-D picture)."""
    th = np.arcsin(1 / 16)
    s = np.array([np.cos(th), np.sin(th)])
    R = 2 * np.outer(s, s) - np.eye(2)
    O = np.diag([1.0, -1.0])
    tot = 0.0
    for mask in range(2 ** k):
        w, psi = 1.0, s.copy()
        for i in range(k):
            if (mask >> i) & 1:
                w *= pm
            else:
                w *= 1 - pm
                psi = O @ psi
            psi = R @ psi
        tot += w * psi[1] ** 2
    return tot


def eig(p, L, r0=None, nl=1):
    """Expected reduction of decision entropy. Rows of L are (noise, hypothesis)
    stacked nl times; noise is marginalised. If r0 is given, hypothesis rows r0..
    are one decision group (the randfun p-grid)."""
    J = p[:, None] * L
    if nl > 1:
        J = J.reshape(nl, -1, J.shape[1]).sum(0)
    if r0 is not None:
        J = np.vstack([J[:r0], J[r0:].sum(0, keepdims=True)])
    pri = J.sum(1)
    pri = pri[pri > 0]
    h0 = -np.sum(pri * np.log(pri))
    po = J.sum(0)
    m = J > 0
    cond = -np.sum(J[m] * (np.log(J[m]) - np.log(np.broadcast_to(po, J.shape)[m])))
    return h0 - cond


class _Base:
    def __init__(self, budget, run):
        self.budget, self.run, self.used = budget, run, 0

    def rem(self):
        return self.budget - self.used

    def shot(self, circ, cost):
        """One shot. The cost is charged *before* running, so the budget can never
        be exceeded; if run() returns nothing usable the query is spent but no
        observation is made (returns None)."""
        if cost > self.rem():
            return None
        self.used += cost
        counts = self.run(circ, 1)
        if not counts:
            return None
        key = max(counts, key=counts.get).replace(" ", "")
        return int(key, 2)


# ===================================================================== m = 1
class _M1(_Base):
    """Hypotheses: constant 0/1, linear (a,b), grover t, balanced, randfun (p-grid).
    Every table is stacked once per noise level in `noises`; the decision posterior
    marginalises over noise (hidden variable, uniform prior)."""

    def __init__(self, fams, budget, run, mode, tau, rng, noises=NOISES):
        super().__init__(budget, run)
        self.mode, self.tau, self.rng, self.noises = mode, tau, rng, tuple(noises)
        self.nl = len(self.noises)
        present = [f for f in ("constant", "linear", "grover", "balanced", "randfun")
                   if f in fams] or ["constant", "linear", "grover", "balanced", "randfun"]
        wf = 1.0 / len(present)
        kinds, A, B, PW, W = [], [], [], [], []

        def add(k, a, b, p, w):
            kinds.append(k); A.append(a); B.append(b); PW.append(p); W.append(w)
        if "constant" in present:
            for c in (0, 1):
                add("c", c, 0, float(c), wf / 2)
        if "linear" in present:
            for a in range(1, 256):
                for b in (0, 1):
                    add("l", a, b, 0.5, wf / 510)
        if "grover" in present:
            for t in range(256):
                add("g", t, 0, 1 / 256, wf / 256)
        if "balanced" in present:
            add("b", 0, 0, 0.5, wf)
        if "randfun" in present:
            zs = np.linspace(-2, 2, 7)
            wz = np.exp(-zs ** 2 / 2); wz /= wz.sum()
            sd = np.sqrt(256 * 0.3 * 0.7) / 256       # instance-to-instance spread
            for z, w in zip(zs, wz):
                add("r", 0, 0, 0.3 + z * sd, wf * w)
        self.kinds = np.array(kinds); self.A = np.array(A); self.B = np.array(B)
        self.PW = np.array(PW)
        pri = np.array(W) / np.sum(W)
        H = self.H = len(kinds)
        ridx = np.where(self.kinds == "r")[0]
        self.r0 = int(ridx[0]) if len(ridx) else None
        F = np.zeros((H, 256))                        # P(f_h(x)=1)
        for h in range(H):
            k = self.kinds[h]
            if k == "c":
                F[h] = self.A[h]
            elif k == "l":
                F[h] = PAR[self.A[h]] ^ self.B[h]
            elif k == "g":
                F[h, self.A[h]] = 1
            else:
                F[h] = self.PW[h]
        self.F = F
        self.NMs = [_noise_matrix(pr) for _, pr in self.noises]
        self.LBV = np.vstack([self._bv_table(pm, NMi) for (pm, _), NMi in zip(self.noises, self.NMs)])
        self.LG1 = np.vstack([self._g1_table(pm, pr, NMi)
                              for (pm, pr), NMi in zip(self.noises, self.NMs)])
        self._LG = {}
        self.logp = np.log(np.tile(pri / self.nl, self.nl))
        self.reads = {}                     # x -> [n_obs0, n_obs1]
        self.n_reads = 0

    # ---- likelihood tables (rows hypotheses, columns outcomes)
    def _bv_table(self, pm, NMi):
        D = np.zeros((self.H, 256))
        for h in range(self.H):
            k = self.kinds[h]
            if k == "c":
                D[h, 0] = 1
            elif k == "l":
                D[h, 0] = pm; D[h, self.A[h]] += 1 - pm
            elif k == "g":
                D[h, 1:] = (1 - pm) * 4 / 256 ** 2
                D[h, 0] = pm + (1 - pm) * (1 - 2 / 256) ** 2
            else:
                p0 = 0.0 if k == "b" else (1 - 2 * self.PW[h]) ** 2
                D[h, 1:] = (1 - pm) * (1 - p0) / 255
                D[h, 0] = pm + (1 - pm) * p0
        return np.maximum(D @ NMi, 1e-12)

    def Lgrover(self, k):
        if k not in self._LG:
            blocks = []
            for (pm, _), NMi in zip(self.noises, self.NMs):
                ps = grover_ps(k, pm)
                D = np.full((self.H, 256), 1 / 256)
                g = np.where(self.kinds == "g")[0]
                if len(g):
                    D[g] = (1 - ps) / 255
                    D[g, self.A[g]] = ps
                blocks.append(np.maximum(D @ NMi, 1e-12))
            self._LG[k] = np.vstack(blocks)
        return self._LG[k]

    def _g1_table(self, pm, pr, NMi):
        H = self.H
        J = np.zeros((H, 256, 2))
        wA, wB, wC1, wC2 = (1 - pm) ** 2, pm * (1 - pm), (1 - pm) * pm, pm ** 2
        u = 1 / 256
        for h in range(H):
            k, p = self.kinds[h], self.PW[h]
            A = np.zeros((256, 2)); Bq = np.zeros((256, 2))
            if k in ("c", "l"):
                f = self.F[h].astype(int)
                A[np.arange(256), f] = u; Bq = A.copy()
            elif k == "g":
                t = self.A[h]
                A[:, 0] = (1 - 4 / 256) ** 2 * u
                A[t] = [0, (3 - 4 / 256) ** 2 * u]
                Bq[:, 0] = u; Bq[t] = [0, u]
            elif k == "b":
                A[:] = 0.5 * u; Bq[:] = 0.5 * u
            else:
                A[:, 1] = p * (3 - 4 * p) ** 2 * u
                A[:, 0] = (1 - p) * (1 - 4 * p) ** 2 * u
                Bq[:, 1] = p * u; Bq[:, 0] = (1 - p) * u
            C1 = np.zeros((256, 2)); C1[:, 0] = A.sum(1)
            C2 = np.zeros((256, 2)); C2[:, 0] = u
            J[h] = wA * A + wB * Bq + wC1 * C1 + wC2 * C2
        Jn = J * (1 - pr) + J[:, :, ::-1] * pr
        out = np.einsum("zy,hyb->hzb", NMi, Jn)          # [h, z_obs, bit]
        return np.maximum(out.transpose(0, 2, 1).reshape(H, 512), 1e-12)

    def Lread(self, x):
        blocks = []
        for pm, pr in self.noises:
            q1 = (1 - pm) * (self.F[:, x] * (1 - pr) + (1 - self.F[:, x]) * pr) + pm * pr
            blocks.append(np.maximum(np.stack([1 - q1, q1], 1), 1e-12))
        return np.vstack(blocks)

    # ---- state
    def post(self):
        """Posterior over hypotheses with the noise level marginalised."""
        p = np.exp(self.logp - self.logp.max())
        p = p / p.sum()
        return p.reshape(self.nl, self.H).sum(0)

    def post_full(self):
        p = np.exp(self.logp - self.logp.max())
        return p / p.sum()

    def noise_posterior(self):
        return self.post_full().reshape(self.nl, self.H).sum(1)

    def upd(self, L, o):
        if o is None:
            return
        self.logp = self.logp + np.log(L[:, o])
        self.logp -= self.logp.max()

    def new_x(self):
        while True:
            x = int(self.rng.integers(256))
            if x not in self.reads or len(self.reads) >= 256:
                return x

    def do_read(self, x):
        o = self.shot(c_read1(x), 1)
        self.upd(self.Lread(x), o)
        if o is not None:
            r = self.reads.setdefault(x, [0, 0]); r[o & 1] += 1
            self.n_reads += 1

    def do_bv(self):
        self.upd(self.LBV, self.shot(c_bv(), 1))

    def do_grover(self, k):
        self.upd(self.Lgrover(k), self.shot(c_grover(k), k))

    def do_g1(self):
        self.upd(self.LG1, self.shot(c_g1(), 2))

    def gain(self, L):
        return eig(self.post_full(), L, self.r0, self.nl)

    def best(self, p):
        if self.r0 is None:
            return int(np.argmax(p)), p.max()
        gm = np.append(p[:self.r0], p[self.r0:].sum())
        i = int(np.argmax(gm))
        return (self.r0 if i == self.r0 else i), gm[i]

    def answer(self, h):
        k = self.kinds[h]
        if k == "c":
            return "constant", int(self.A[h])
        if k == "l":
            return "linear", [int(self.A[h]), int(self.B[h])]
        if k == "g":
            return "grover", int(self.A[h])
        return ("balanced", None) if k == "b" else ("randfun", None)

    def confirm_action(self, h):
        k = self.kinds[h]
        if k in ("c", "l") and self.n_reads < 2:
            return ("read", self.new_x())
        if k == "g" and self.reads.get(int(self.A[h]), [0, 0])[1] < 2:
            return ("read", int(self.A[h]))
        return None

    def choose(self, p):
        """Return the best action *tuple* (e.g. ("read", x)), by information gain
        per query. p is the noise-marginalised hypothesis posterior."""
        rem, cands = self.rem(), []
        m = self.mode
        if m in ("full", "single") and rem >= 1:
            cands.append((self.gain(self.LBV), ("bv",), 1))
        if m in ("full", "classical") and rem >= 1:
            x = self.new_x()
            cands.append((self.gain(self.Lread(x)), ("read", x), 1))
            g = np.where(self.kinds == "g")[0]
            if len(g):
                t = int(self.A[g[np.argmax(p[g])]])
                cands.append((self.gain(self.Lread(t)), ("read", t), 1))
        if m == "full":
            if rem >= 2:
                cands.append((self.gain(self.LG1), ("g1",), 2))
            for k in GROVER_KS:
                if k <= rem:
                    cands.append((self.gain(self.Lgrover(k)), ("grover", k), k))
        if not cands:
            return None
        return max(cands, key=lambda c: c[0] / c[2])[1]

    def exec(self, act):
        name = act[0]
        if name == "bv":
            self.do_bv()
        elif name == "read":
            self.do_read(act[1])
        elif name == "g1":
            self.do_g1()
        elif name == "grover":
            self.do_grover(act[1])
        else:
            raise ValueError(f"unknown action {act!r}")

    def cost(self, act):
        return {"bv": 1, "read": 1, "g1": 2}.get(act[0]) or act[1]

    def solve(self):
        if self.mode == "nonadaptive":
            sched = ["bv"] * 4 + ["read"] * 6 + ["g1"] * 4
            for s in sched:
                if (2 if s == "g1" else 1) > self.rem():
                    break
                self.exec(("read", self.new_x()) if s == "read" else (s,))
            while self.rem() >= 6:
                self.do_grover(6)
            while self.rem() >= 1:
                self.do_read(self.new_x())
            return self.answer(self.best(self.post())[0])
        if self.mode == "full":
            for _ in range(min(2, self.rem())):
                self.do_bv()
        phase_reads = 0
        while self.rem() > 0:
            p = self.post()
            h, pm_ = self.best(p)
            if pm_ >= self.tau:
                act = self.confirm_action(h) if self.mode != "single" else None
                if act is None or self.cost(act) > self.rem():
                    break
                self.exec(act)
                continue
            if self.mode == "full" and phase_reads < 6:
                Z = p[np.isin(self.kinds, ["c", "g"])].sum()
                if Z >= 0.5:
                    c1 = p[(self.kinds == "c") & (self.A == 1)].sum() / Z
                    if 0.005 < c1 < self.tau:
                        self.do_read(self.new_x()); phase_reads += 1
                        continue
            act = self.choose(p)
            if act is None:
                break
            self.exec(act)
        return self.answer(self.best(self.post())[0])


# ===================================================================== m = 8
def _binom(d, n, q):
    from math import comb
    return comb(n, d) * q ** d * (1 - q) ** (n - d)


class _M8(_Base):
    """Hypotheses: perm, simon(s), simon2(H). Tables stacked per noise level."""

    def __init__(self, fams, budget, run, mode, tau, rng, noises=NOISES):
        super().__init__(budget, run)
        self.mode, self.tau, self.rng, self.noises = mode, tau, rng, tuple(noises)
        self.nl = len(self.noises)
        present = [f for f in ("simon", "simon2", "perm") if f in fams] or ["simon", "simon2", "perm"]
        wf = 1.0 / len(present)
        E, basis, W, kinds = [], [], [], []
        if "perm" in present:
            E.append((-1, -1, -1)); basis.append((None, None)); W.append(wf); kinds.append("p")
        if "simon" in present:
            for s in range(1, 256):
                E.append((s, -1, -1)); basis.append((s, None)); W.append(wf / 255); kinds.append("s")
        subs = []
        if "simon2" in present:
            for a in range(1, 256):
                for b in range(a + 1, 256):
                    c = a ^ b
                    if c > b:
                        subs.append((a, b, c))
            for a, b, c in subs:
                E.append((a, b, c)); basis.append((a, b)); W.append(wf / len(subs)); kinds.append("2")
        self.E = np.array(E); self.kinds = np.array(kinds)
        pri = np.array(W) / np.sum(W)
        H = self.H = len(E)
        ind = np.ones((H, 256))
        for h, (a, b) in enumerate(basis):
            if a is None:
                continue
            ind[h] = PAR[a] == 0
            if b is not None:
                ind[h] *= PAR[b] == 0
        ind /= ind.sum(1, keepdims=True)
        LPs, Lsame, Ldiff = [], [], []
        for pm, pr in self.noises:
            D = (1 - pm) * ind
            D[:, 0] += pm
            LPs.append(np.maximum(D @ _noise_matrix(pr), 1e-12))
            s_, d_ = self._pair_tables(pm, pr)
            Lsame.append(s_); Ldiff.append(d_)
        self.LP = np.vstack(LPs)
        self.Lsame, self.Ldiff = np.array(Lsame), np.array(Ldiff)    # [nl, 9]
        self.logp = np.log(np.tile(pri / self.nl, self.nl))
        self.conf = {}                              # delta -> successful checks
        self.used_x = set()

    @staticmethod
    def _pair_tables(pm, pr):
        """P(d) of the Hamming distance between two noisy 8-bit reads."""
        e = 2 * pr * (1 - pr)
        ds = np.arange(9)
        both = (1 - pm) ** 2 + pm ** 2
        one = 2 * pm * (1 - pm)
        bin_e = np.array([_binom(d, 8, e) for d in ds])
        bin_h = np.array([_binom(d, 8, 0.5) for d in ds])
        same = both * bin_e + one * bin_h
        diff_both = np.zeros(9)
        for j in range(1, 9):                       # j differing bits before noise
            pj = _binom(j, 8, 0.5) * 256 / 255
            for u in range(j + 1):                  # kept differing bits
                for v in range(8 - j + 1):          # newly flipped equal bits
                    diff_both[u + v] += pj * _binom(u, j, 1 - e) * _binom(v, 8 - j, e)
        diff = (1 - pm) ** 2 * diff_both + one * bin_h + pm ** 2 * bin_e
        return same, diff

    def post_full(self):
        p = np.exp(self.logp - self.logp.max())
        return p / p.sum()

    def post(self):
        return self.post_full().reshape(self.nl, self.H).sum(0)

    def noise_posterior(self):
        return self.post_full().reshape(self.nl, self.H).sum(1)

    def Lpair(self, delta):
        member = (self.E == delta).any(1)
        blocks = [np.where(member[:, None], self.Lsame[i][None, :], self.Ldiff[i][None, :])
                  for i in range(self.nl)]
        return np.maximum(np.vstack(blocks), 1e-12)

    def _upd(self, L, o):
        if o is None:
            return
        self.logp = self.logp + np.log(L[:, o]); self.logp -= self.logp.max()

    def do_probe(self):
        self._upd(self.LP, self.shot(c_simon(), 1))

    def do_pair(self, delta):
        while True:
            x = int(self.rng.integers(256))
            if x not in self.used_x or len(self.used_x) > 200:
                break
        self.used_x.add(x)
        v1 = self.shot(c_read8(x), 1)
        v2 = self.shot(c_read8(x ^ delta), 1)
        if v1 is None or v2 is None:
            return
        d = int(_pc[(v1 ^ v2) & 255])
        self._upd(self.Lpair(delta), d)
        if d <= 1:
            self.conf[delta] = self.conf.get(delta, 0) + 1

    def top_deltas(self, p, k=2):
        mass = np.zeros(256)
        for j in range(3):
            v = self.E[:, j] >= 0
            mass += np.bincount(self.E[v, j], weights=p[v], minlength=256)
        return [int(i) for i in np.argsort(-mass)[:k] if mass[i] > 0]

    def answer(self, h):
        k = self.kinds[h]
        if k == "p":
            return "perm", None
        if k == "s":
            return "simon", int(self.E[h, 0])
        return "simon2", [int(v) for v in self.E[h]]

    def unconfirmed(self, h):
        k = self.kinds[h]
        if k == "s":
            s = int(self.E[h, 0])
            return s if self.conf.get(s, 0) < 2 else None
        if k == "2":
            for v in self.E[h]:
                if self.conf.get(int(v), 0) < 1:
                    return int(v)
        return None

    def pick(self, p):
        """Best of {probe, pair-check on the two most likely differences}."""
        pf = self.post_full()
        act = pf.reshape(self.nl, self.H).max(0) > 1e-9 * pf.max()      # prune
        idx = np.concatenate([np.where(act)[0] + i * self.H for i in range(self.nl)])
        pa = pf[idx] / pf[idx].sum()
        ng = int(act.sum())

        def gain(L):
            return eig(pa, L[idx], None, self.nl)
        best_u, best_a = gain(self.LP), ("probe",)
        for d in self.top_deltas(p):
            u = gain(self.Lpair(d)) / 2
            if u > best_u:
                best_u, best_a = u, ("pair", d)
        return best_a

    def solve(self):
        if self.mode == "nonadaptive":
            while self.rem() >= 1:
                self.do_probe()
            return self.answer(int(np.argmax(self.post())))
        for _ in range(min(3, self.rem())):
            self.do_probe()
        while self.rem() > 0:
            p = self.post()
            h = int(np.argmax(p))
            if p[h] >= self.tau:
                d = self.unconfirmed(h) if self.mode == "full" else None
                if d is None or self.rem() < 2:
                    break
                self.do_pair(d)
                continue
            act = ("probe",)
            if self.mode == "full" and self.rem() >= 2:
                act = self.pick(p)
            if act[0] == "probe":
                self.do_probe()
            else:
                self.do_pair(act[1])
        return self.answer(int(np.argmax(self.post())))


def _classical_m8(budget, run, rng):
    """Classical-only baseline: read f at distinct random x, find equal values."""
    seen, diffs, used = {}, {}, 0
    for x in rng.permutation(256):
        if used >= budget:
            break
        used += 1
        counts = run(c_read8(int(x)), 1)
        if not counts:
            continue
        v = int(max(counts, key=counts.get).replace(" ", ""), 2)
        if v != 0:
            if v in seen:
                d = seen[v] ^ int(x)
                diffs[d] = diffs.get(d, 0) + 1
            else:
                seen[v] = int(x)
        if len(diffs) == 1 and max(diffs.values()) >= 2:
            break
        if len(diffs) >= 3:
            break
    if not diffs:
        return "perm", None
    if len(diffs) == 1:
        return "simon", int(next(iter(diffs)))
    ds = sorted(diffs, key=lambda d: -diffs[d])[:2]
    return "simon2", sorted({ds[0], ds[1], ds[0] ^ ds[1]})


LAST_INFO = {}      # diagnostics of the most recent solve (not used for decisions)


def _solve(n, m, budget, families, run, mode="full", tau=TAU, seed=12345, noises=NOISES):
    rng = np.random.default_rng(seed)
    fams = list(families)
    LAST_INFO.clear()
    if m == 1:
        eng = _M1(fams, budget, run, mode, tau, rng, noises)
    elif mode == "classical":
        return _classical_m8(budget, run, rng)
    else:
        eng = _M8(fams, budget, run, mode, tau, rng, noises)
    ans = eng.solve()
    p = eng.post()
    LAST_INFO["p_answer"] = float(eng.best(p)[1] if m == 1 else p.max())
    LAST_INFO["p_noise"] = [float(v) for v in eng.noise_posterior()]
    return ans


def solve(n, m, budget, families, run):
    """Entry point required by the judges."""
    return _solve(n, m, budget, families, run, mode="full")

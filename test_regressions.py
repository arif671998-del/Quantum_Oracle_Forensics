"""Regression + judge-harness safety tests for solver.py.  Run: python test_regressions.py"""
import re, sys, traceback
import numpy as np
import solver as S
from oracle_sim import make_oracle, Harness

FAMS = ["constant", "balanced", "linear", "grover", "randfun", "simon", "simon2", "perm"]
ACTIONS = {"bv", "read", "g1", "grover"}
TESTS = []
def test(f): TESTS.append(f); return f

def m1(run=None, mode="full", budget=60, noises=S.NOISES):
    return S._M1(FAMS, budget, run, mode, S.TAU, np.random.default_rng(0), noises)

def m8(run=None, mode="full", budget=60):
    return S._M8(FAMS, budget, run, mode, S.TAU, np.random.default_rng(0))

# ---- regression: choose() once returned (action, cost) -> exec() mis-dispatched to Grover(1)
@test
def choose_returns_flat_action_tuple():
    E = m1()
    for _ in range(3):
        a = E.choose(E.post())
        assert isinstance(a, tuple) and isinstance(a[0], str) and a[0] in ACTIONS, a
        assert not isinstance(a[0], tuple)
    E8 = m8()
    a = E8.pick(E8.post())
    assert isinstance(a, tuple) and a[0] in ("probe", "pair"), a

@test
def exec_dispatches_each_action_to_its_handler():
    E = m1()
    called = []
    E.do_bv = lambda: called.append("bv")
    E.do_read = lambda x: called.append(("read", x))
    E.do_g1 = lambda: called.append("g1")
    E.do_grover = lambda k: called.append(("grover", k))
    for act in (("bv",), ("read", 17), ("g1",), ("grover", 6)):
        E.exec(act)
    assert called == ["bv", ("read", 17), "g1", ("grover", 6)], called
    try:
        E.exec((("read", 3), 1)); assert False, "nested tuple must be rejected"
    except ValueError:
        pass

# ---- regression: the read update must actually move the posterior
@test
def read_update_moves_posterior_in_right_direction():
    for obs in ("0", "1"):
        E = m1(run=lambda circ, shots, o=obs: {o: shots})
        x = 77
        before = E.post()
        E.do_read(x)
        after = E.post()
        assert np.abs(after - before).max() > 1e-3, "read did not change the posterior"
        hi = E.F[:, x] > 0.99     # hypotheses predicting f(x)=1
        lo = E.F[:, x] < 0.01
        ratio = (after[hi].sum() / before[hi].sum()) / (after[lo].sum() / before[lo].sum())
        assert (ratio > 1) == (obs == "1"), (obs, ratio)
        assert E.reads[x][int(obs)] == 1 and E.n_reads == 1

@test
def read_of_consistent_oracle_concentrates_linear_b():
    o = make_oracle("linear", np.random.default_rng(1), a=106, b=1)
    h = Harness(o, 10 ** 9, 0.04, 0.02, seed=2)
    E = m1(run=h.run)
    for _ in range(2):
        E.do_bv()
    for x in (3, 50, 99, 200):
        E.do_read(x)
    i, p = E.best(E.post())
    assert (E.kinds[i], E.A[i], E.B[i]) == ("l", 106, 1) and p > 0.9, (E.kinds[i], E.A[i], E.B[i], p)

# ---- judge-harness safety
class Spy:
    """Fake run(): records requested k*shots; may return fewer shots / spaces / nothing."""
    def __init__(self, kind, seed=0):
        self.kind, self.q, self.rng = kind, 0, np.random.default_rng(seed)
    def __call__(self, circ, shots):
        k = sum(1 for i in circ.data if i.operation.name == "oracle")
        self.q += k * shots
        w = circ.num_clbits
        if self.kind == "empty":
            return {}
        key = format(int(self.rng.integers(2 ** w)), f"0{w}b")
        if self.kind == "spaces":
            key = key[:w // 2] + " " + key[w // 2:] if w > 1 else key
        if self.kind == "fewer":
            return {key: 0} if self.rng.random() < .5 else {key: 1}
        return {key: shots}

@test
def budget_never_exceeded_for_odd_run_behaviour():
    for kind in ("normal", "empty", "spaces", "fewer"):
        for m in (1, 8):
            for budget in (7, 20, 60):
                for mode in ("full", "single", "classical", "nonadaptive"):
                    spy = Spy(kind)
                    ans = S._solve(8, m, budget, FAMS, spy, mode=mode)
                    assert spy.q <= budget, (kind, m, budget, mode, spy.q)
                    assert isinstance(ans, tuple) and len(ans) == 2

@test
def solver_never_imports_the_simulator_or_reads_files():
    src = open("solver.py").read()
    assert not re.search(r"oracle_sim|evaluate|^\s*import (os|sys|socket|requests)", src, re.M)
    assert "open(" not in src

@test
def circuits_are_judge_compatible():
    allowed = {"h", "x", "mcx", "measure", "oracle"}
    circs = [S.c_bv(), S.c_read1(5), S.c_grover(3), S.c_g1(), S.c_simon(), S.c_read8(5)]
    for c in circs:
        assert c.num_qubits <= 20
        assert len(c.cregs) == 1, "exactly one classical register"
        names = {i.operation.name for i in c.data}
        assert names <= allowed, names
        for i in c.data:
            if i.operation.name == "oracle":
                g = i.operation
                assert g.num_qubits in (9, 16) and list(g.params) == [] and type(g).__name__ == "Gate"
        # oracle acts on inputs first, then outputs, contiguous qubits 0..n+m-1
        for i in c.data:
            if i.operation.name == "oracle":
                assert [c.find_bit(q).index for q in i.qubits] == list(range(i.operation.num_qubits))

@test
def secrets_have_the_required_format():
    for fam, m in (("linear", 1), ("simon2", 8), ("simon", 8), ("grover", 1), ("constant", 1)):
        o = make_oracle(fam, np.random.default_rng(3))
        h = Harness(o, 60, 0.04, 0.02, seed=4)
        f, s = S.solve(8, m, 60, FAMS, h.run)
        if f == "linear":
            assert isinstance(s, list) and len(s) == 2 and 1 <= s[0] <= 255 and s[1] in (0, 1)
        if f == "simon2":
            assert isinstance(s, list) and len(s) == 3 and s == sorted(s) and s[0] ^ s[1] == s[2]
        if f in ("constant", "grover", "simon"):
            assert isinstance(s, int)

if __name__ == "__main__":
    bad = 0
    for t in TESTS:
        try:
            t(); print("PASS", t.__name__)
        except Exception:
            bad += 1; print("FAIL", t.__name__); traceback.print_exc()
    print("\nALL PASS" if not bad else f"\n{bad} FAILED"); sys.exit(bool(bad))

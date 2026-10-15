"""Check solver likelihood tables against the simulator at stress noise (8% / 4%)."""
import numpy as np
import solver as S
from oracle_sim import make_oracle, Harness

rng = np.random.default_rng(7)
ok = True
def chk(name, model, emp, tol):
    global ok
    err = float(np.max(np.abs(model - emp)))
    good = err < tol; ok &= good
    print(("PASS " if good else "FAIL ") + f"{name}: max|model-emp|={err:.4f}")

def emp_dist(h, circ, nout, shots, width):
    c = h.run(circ, shots); v = np.zeros(nout)
    for k, n in c.items(): v[int(k, 2)] += n
    return v / shots

def harness(o): return Harness(o, budget=10**12, p_oracle=0.08, p_read=0.04, seed=int(rng.integers(1<<30)))

E = S._M1(["constant","linear","grover","balanced","randfun"], 60, None, "full", .995, rng, noises=(S.STRESS,))
def hyp(kind, a=0, b=0, p=None):
    for h in range(E.H):
        if E.kinds[h]==kind and E.A[h]==a and E.B[h]==b and (p is None or abs(E.PW[h]-p)<1e-9): return h
SH = 20000
# aggregate-level check for BV zero-string rate and read rate on random instances
cases = {"c0": ("constant", dict(c=0), hyp("c",0)), "c1": ("constant", dict(c=1), hyp("c",1)),
         "lin": ("linear", dict(a=178,b=1), hyp("l",178,1)), "gro": ("grover", dict(t=173), hyp("g",173))}
for nm,(fam,kw,h) in cases.items():
    o = make_oracle(fam, rng, **kw); hr = harness(o)
    chk(f"BV {nm}", E.LBV[h], emp_dist(hr, S.c_bv(), 256, SH, 8), 0.012)
    chk(f"g1 {nm}", E.LG1[h], emp_dist(hr, S.c_g1(), 512, SH, 9), 0.012)
    chk(f"grover k=6 {nm}", E.Lgrover(6)[h], emp_dist(hr, S.c_grover(6), 256, SH, 8), 0.012)
    x = 77
    q = emp_dist(hr, S.c_read1(x), 2, SH, 1)
    chk(f"read {nm}", E.Lread(x)[h], q, 0.01)
# randfun / balanced: use instance's true ones-fraction
o = make_oracle("randfun", rng); p = o.table.mean(); hr = harness(o)
Er = S._M1(["randfun"], 60, None, "full", .995, rng, noises=(S.STRESS,))
Er.PW[:] = p; Er.F[:] = p          # rebuild the g1 table at this instance's true ones-fraction
LG1 = Er._g1_table(S.STRESS[0], S.STRESS[1], Er.NMs[0])
chk("g1 randfun (true p)", LG1[0], emp_dist(hr, S.c_g1(), 512, SH, 9), 0.015)
zero = emp_dist(hr, S.c_bv(), 256, SH, 8)[0]
D0 = 0.08 + 0.92*(1-2*p)**2
print(f"BV randfun P(y=0): emp {zero:.4f}  model-true-p {D0*0.96**8 + 0:.4f} (approx, ignoring flips-into-0)")

# ---- m = 8
E8 = S._M8(["simon","simon2","perm"], 60, None, "full", .995, rng, noises=(S.STRESS,))
def h8(kind, e0=-1, e1=-1):
    for h in range(E8.H):
        if E8.kinds[h]==kind and ((kind=="p") or (E8.E[h,0]==e0 and (kind=="s" or E8.E[h,1]==e1))): return h
for nm,(fam,kw,h) in {"simon": ("simon", dict(s=105), h8("s",105)),
                      "simon2": ("simon2", dict(H=[15,49]), h8("2",15,49)),
                      "perm": ("perm", {}, h8("p"))}.items():
    o = make_oracle(fam, rng, **kw); hr = harness(o)
    chk(f"probe {nm}", E8.LP[h], emp_dist(hr, S.c_simon(), 256, SH, 8), 0.012)
    # pair statistic: x, x^delta
    delta = 105 if fam=="simon" else (15 if fam=="simon2" else 105)
    ds = np.zeros(9)
    for i in range(3000):
        x = int(rng.integers(256))
        # perm has no structure: use a fresh random offset each time (a fixed
        # offset samples only 128 fixed pairs of one instance)
        dd = int(rng.integers(1, 256)) if fam == "perm" else delta
        v = []
        for xx in (x, x ^ dd):
            c = hr.run(S.c_read8(xx), 1); v.append(int(next(iter(c)),2))
        ds[bin(v[0]^v[1]).count("1")] += 1
    ds /= ds.sum()
    model = E8.Lpair(delta)[h] if fam != 'perm' else E8.Ldiff[0]
    chk(f"pair d-dist {nm}", model, ds, 0.03)
# ---- normal-noise block of the stacked (mixture) tables
Em = S._M1(["constant","linear","grover","balanced","randfun"], 60, None, "full", .995, rng)
H = Em.H
for nm, (fam, kw) in {"lin": ("linear", dict(a=178, b=1)), "gro": ("grover", dict(t=173))}.items():
    h = [i for i in range(H) if (Em.kinds[i] == fam[0]) and Em.A[i] == (178 if fam == "linear" else 173)
         and (fam != "linear" or Em.B[i] == 1)][0]
    hr = Harness(make_oracle(fam, rng, **kw), budget=10**12, p_oracle=0.04, p_read=0.02, seed=11)
    chk(f"normal-block BV {nm}", Em.LBV[h], emp_dist(hr, S.c_bv(), 256, SH, 8), 0.012)
    chk(f"normal-block g1 {nm}", Em.LG1[h], emp_dist(hr, S.c_g1(), 512, SH, 9), 0.012)
    chk(f"normal-block grover6 {nm}", Em.Lgrover(6)[h], emp_dist(hr, S.c_grover(6), 256, SH, 8), 0.012)
print("\nALL PASS" if ok else "\nSOME FAILED")

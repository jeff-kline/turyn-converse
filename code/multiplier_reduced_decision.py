#!/usr/bin/env python3
"""Exact decision of a Turyn pair at composite q, reduced by the forced
multiplier group M(q) (theory track T3).

By the composite multiplier theorem, any Turyn pair (r,s) of order t=(q+1)/2 is
constant on the orbits of V = decimation part of M^+(q) acting on Z/t.  So we
enumerate only V-invariant candidates.  The pair equation r^2+s^2=q*1 says
    PAF_r(delta) + PAF_s(delta) = 0   for all delta != 0,
and PAF is itself V-invariant, so there is one constraint per nonzero delta-orbit.
The r-side and s-side are INDEPENDENT, so we meet in the middle on the orbit
signs:  store all PAF_r vectors, then look for an s-assignment with PAF_s = -PAF_r.

r_0 = 0 (fixed); off-origin r,s in {+-1}, symmetric (automatic: V contains -1).

Budget guard: refuses if either side exceeds 2**CAP candidates.  Pure
numpy; for q=441 the sides are 2**14 and 2**15 -> seconds, < ~200 MB.
"""
import sys
from functools import reduce
import numpy as np

sys.path.insert(0, sys.path[0] or '.')
from composite_multiplier_scan import cyclic_sub, crt2, factor

CAP = 22  # refuse 2**k candidates beyond this without authorization


def v_group(q):
    t = (q + 1) // 2
    mod = 4 * t
    subs = [cyclic_sub(p, mod) for p in factor(q)]
    M = reduce(lambda a, b: a & b, subs)
    # The extra symmetry is (+1,-1).  Since the unit group is abelian and this
    # symmetry has order two, <M,sym> is just M union M*sym; avoid the generic
    # closure routine, which is unnecessarily expensive in wide sweeps.
    sym = crt2(1, 4, (t - 1) % t, t)
    Mp = M | {(s * sym) % mod for s in M}
    V = sorted({s % t for s in Mp})
    all_plus = all(s % 4 == 1 for s in Mp)   # every multiplier has eps=+1
    return t, V, all_plus


def orbits(t, V):
    seen = set()
    orbs = []
    for j in range(t):
        if j in seen:
            continue
        orb = sorted({(v * j) % t for v in V})
        seen |= set(orb)
        orbs.append(orb)
    return orbs


def orbit_of(orbs, t):
    lab = np.empty(t, dtype=np.int64)
    for idx, o in enumerate(orbs):
        for j in o:
            lab[j] = idx
    return lab


def paf_vectors(cands, t, deltas):
    """cands: (N,t) int8 array of full candidate vectors.
    returns (N, len(deltas)) int array of PAF at each delta."""
    out = np.empty((cands.shape[0], len(deltas)), dtype=np.int32)
    for c, d in enumerate(deltas):
        rolled = np.roll(cands, -d, axis=1)
        out[:, c] = (cands.astype(np.int32) * rolled).sum(axis=1)
    return out


def decide(q, verbose=True):
    t, V, all_plus = v_group(q)
    if not all_plus:
        # M(q) contains a sign-reversing (eps=-1) multiplier: the true pair is
        # sign-ALTERNATING, not constant, on those orbits. The constant-invariant
        # reduction below would be unsound (risk of a false UNSAT). Refuse.
        print(f"q={q}: SKIP (M(q) has an eps=-1 multiplier; constant reduction "
              f"unsound -- use the signed marginal algebra).")
        return None
    orbs = orbits(t, V)
    lab = orbit_of(orbs, t)
    zero_orbit = int(lab[0])
    nz_orbits = [i for i in range(len(orbs)) if i != zero_orbit]
    kr = len(nz_orbits)          # r free signs (origin forced 0)
    ks = len(orbs)               # s free signs (origin free)
    # nonzero delta-orbit representatives (one per orbit, delta != 0)
    reps = sorted({min(o) for o in orbs if o != [0]})
    if verbose:
        print(f"q={q} t={t} |V|={len(V)} #orbits={len(orbs)} "
              f"kr={kr} ks={ks} #constraints={len(reps)}")
    if kr > CAP or ks > CAP:
        print(f"REFUSE: side exceeds 2**{CAP} (kr={kr}, ks={ks}); "
              f"authorize a larger CAP to proceed.")
        return None

    # ---- r side: origin fixed 0 ----
    Nr = 1 << kr
    bits = ((np.arange(Nr)[:, None] >> np.arange(kr)[None, :]) & 1)
    rsign = np.where(bits == 1, 1, -1).astype(np.int8)      # (Nr, kr)
    R = np.zeros((Nr, t), dtype=np.int8)
    for col, oi in enumerate(nz_orbits):
        for j in orbs[oi]:
            R[:, j] = rsign[:, col]
    R[:, 0] = 0
    Pr = paf_vectors(R, t, reps)

    # ---- s side: all orbits free (origin too) ----
    Ns = 1 << ks
    sbits = ((np.arange(Ns)[:, None] >> np.arange(ks)[None, :]) & 1)
    ssign = np.where(sbits == 1, 1, -1).astype(np.int8)      # (Ns, ks)
    S = np.zeros((Ns, t), dtype=np.int8)
    for oi in range(len(orbs)):
        for j in orbs[oi]:
            S[:, j] = ssign[:, oi]
    Ps = paf_vectors(S, t, reps)

    # ---- meet in the middle: need Pr + Ps = 0 ----
    rset = {row.tobytes(): i for i, row in enumerate(Pr)}   # last wins; fine
    for k in range(Ns):
        key = (-Ps[k]).astype(np.int32).tobytes()
        i = rset.get(key)
        if i is not None:
            print(f"SAT: Turyn pair exists at q={q}  (r cand #{i}, s cand #{k})")
            # emit the explicit rows
            print("  r =", R[i].tolist())
            print("  s =", S[k].tolist())
            # independent full verification
            ok = all(int((R[i].astype(int) * np.roll(R[i].astype(int), -d)).sum()
                         + (S[k].astype(int) * np.roll(S[k].astype(int), -d)).sum()) == 0
                     for d in range(1, t))
            d0 = int((R[i].astype(int)**2).sum() + (S[k].astype(int)**2).sum())
            print(f"  full check: all off-diag zero = {ok}, diag = {d0} (q={q})")
            return True
    print(f"UNSAT: no V-invariant Turyn pair at q={q}  "
          f"(searched 2^{kr} x 2^{ks} orbit assignments)")
    return False


if __name__ == "__main__":
    for a in sys.argv[1:] or [441]:
        decide(int(a))
        print()

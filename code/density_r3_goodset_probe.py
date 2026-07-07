#!/usr/bin/env python3
"""Measure the r=3 good-set frequency and bad-set profile on the lane.

Informs density_almost_all.md R2b/R2c (one-probe budget):

- Sub-lane (ell = 7 mod 12, i.e. 3 | ell - 1): fraction of composite
  members q = 6*ell - 1 with ALL p | q cubic non-residues mod ell
  ("good at 3" — each is an unconditional kill by Prop. K + Lemma P),
  stratified by omega(q) over squarefree members, against
    pinned prediction  P_k = (2^k + 2*(-1)^k) / 3^k   (Lemma P model)
    naive independence  (2/3)^k.
- Pinned-spoil rate: members whose small factors (p <= sqrt(q)) are all
  non-residues but whose unique large factor is a residue (chi(P) = 1,
  forced by the smooth part via Lemma P).
- Full lane: bad set (g0 = oddpart(gcd_p ord_ell(p)) = 1); for each bad
  member verify the residue reformulation (every odd prime r | ell - 1
  has some p | q with p in S_r).
- Distribution of #{odd prime r | ell - 1} (R2c bookkeeping).

Usage: density_r3_goodset_probe.py [QMAX]   (default 200000)
"""
import sys
import time
from math import gcd, isqrt

sys.path.insert(0, sys.path[0] or '.')
from orbit_signature_scan import is_prime_number, factor


def oddpart(n: int) -> int:
    while n % 2 == 0:
        n //= 2
    return n


def ord_mod(a: int, ell: int) -> int:
    a %= ell
    n = ell - 1
    for p, e in factor(n).items():
        for _ in range(e):
            if pow(a, n // p, ell) == 1:
                n //= p
            else:
                break
    return n


def main() -> None:
    qmax = int(sys.argv[1]) if len(sys.argv) > 1 else 200_000
    t0 = time.time()
    n_members = 0
    n_sub = 0                      # sub-lane members (3 | ell - 1)
    n_good = 0                     # all p | q cubic non-residue
    sf_tot = {}                    # omega -> squarefree sub-lane members
    sf_good = {}                   # omega -> good among those
    n_smallgood = 0                # all small (<= sqrt q) factors non-residue
    n_spoiled = 0                  # ... but large factor is a residue
    bad = []                       # (q, ell, factors) with g0 = 1
    odd_r_hist = {}                # #{odd r | ell-1} -> count (full lane)
    for ell in range(11, (qmax + 1) // 6 + 1, 4):
        if not is_prime_number(ell):
            continue
        q = 6 * ell - 1
        if q > qmax or is_prime_number(q):
            continue
        n_members += 1
        fq = factor(q)
        ps = list(fq)
        # full-lane badness via the gcd-of-orders formula (Lemma W)
        g = 0
        for p in ps:
            g = gcd(g, ord_mod(p, ell))
        g0 = oddpart(g)
        n_odd_r = len([r for r in factor(ell - 1) if r != 2])
        odd_r_hist[n_odd_r] = odd_r_hist.get(n_odd_r, 0) + 1
        if g0 == 1:
            bad.append((q, ell, dict(fq)))
            # residue reformulation: every odd r | ell-1 has some p in S_r
            for r in factor(ell - 1):
                if r == 2:
                    continue
                assert any(pow(p, (ell - 1) // r, ell) == 1 for p in ps), \
                    f"reformulation FAILS at q={q} r={r}"
        # sub-lane r = 3 statistics
        if (ell - 1) % 3 != 0:
            continue
        n_sub += 1
        res = {p: pow(p, (ell - 1) // 3, ell) == 1 for p in ps}
        good = not any(res.values())
        n_good += good
        if all(e == 1 for e in fq.values()):
            k = len(ps)
            sf_tot[k] = sf_tot.get(k, 0) + 1
            sf_good[k] = sf_good.get(k, 0) + good
        rt = isqrt(q)
        big = [p for p in ps if p > rt]
        small_ok = not any(res[p] for p in ps if p <= rt)
        if small_ok and big:
            n_smallgood += 1
            if res[big[0]]:
                n_spoiled += 1
        if n_members % 2000 == 0:
            print(f"[progress] members={n_members} ell={ell} "
                  f"t={time.time()-t0:.0f}s", flush=True)
    dt = time.time() - t0
    print(f"qmax={qmax}: lane members={n_members}, sub-lane={n_sub}, "
          f"good-at-3={n_good} ({n_good/max(n_sub,1):.3f})")
    print("squarefree sub-lane by omega:  k  members  good  frac  "
          "pinned_pred  naive_pred")
    for k in sorted(sf_tot):
        m, gd = sf_tot[k], sf_good[k]
        pin = (2**k + 2 * (-1)**k) / 3**k
        nai = (2 / 3)**k
        print(f"  k={k}: {m:6d} {gd:6d} {gd/m:.3f}  {pin:.3f}  {nai:.3f}")
    print(f"small-factors-good with a >sqrt(q) factor: {n_smallgood}; "
          f"spoiled by pinned large-factor residue: {n_spoiled} "
          f"({n_spoiled/max(n_smallgood,1):.3f})")
    print(f"bad set (g0=1): {len(bad)} members: {bad}")
    print(f"#odd r | ell-1 histogram (full lane): "
          f"{dict(sorted(odd_r_hist.items()))}")
    print(f"total {dt:.1f}s")


if __name__ == "__main__":
    main()

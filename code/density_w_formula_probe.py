#!/usr/bin/env python3
"""Verify the general-omega multiplier-image formula on the lane.

Claim (density_almost_all.md, Lemma W): for ell = 3 (mod 4) prime and
q = 6*ell - 1 composite with distinct prime factors p_1..p_k,

    w := |image of <M(q), sym> in (Z/ell)^x| = 2 * oddpart(gcd_i ord_ell(p_i))

exactly, independent of exponents e_i, with v2(w) = 1 and d = (ell-1)/w odd.
Also count all_plus=False members (expected: none on the lane).

Usage: density_w_formula_probe.py [QMAX]   (default 100000)
"""
import sys
import time

sys.path.insert(0, sys.path[0] or '.')
from orbit_signature_scan import cached_v_group, is_prime_number, factor


def oddpart(n: int) -> int:
    while n % 2 == 0:
        n //= 2
    return n


def ord_mod(a: int, ell: int) -> int:
    # order of a in (Z/ell)^x, ell prime: factor ell-1, strip primes
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
    qmax = int(sys.argv[1]) if len(sys.argv) > 1 else 100_000
    t0 = time.time()
    from math import gcd
    n_members = 0
    n_not_ap = 0
    n_mismatch = 0
    n_w2 = []
    omega_hist = {}
    checked_cost = False
    for ell in range(11, (qmax + 1) // 6 + 1, 4):
        if not is_prime_number(ell):
            continue
        q = 6 * ell - 1
        if q > qmax or is_prime_number(q):
            continue
        t, V, ap = cached_v_group(q)
        n_members += 1
        if not ap:
            n_not_ap += 1
        w = len({v % ell for v in V})
        ps = list(factor(q))
        g = 0
        for p in ps:
            g = gcd(g, ord_mod(p, ell))
        pred = 2 * oddpart(g)
        if w != pred:
            n_mismatch += 1
            print(f"MISMATCH q={q} ell={ell} w={w} pred={pred} "
                  f"factors={factor(q)}")
        if w < 4:
            n_w2.append((q, ell, dict(factor(q))))
        k = len(ps)
        omega_hist[k] = omega_hist.get(k, 0) + 1
        d = (ell - 1) // w
        assert d % 2 == 1, f"d even at q={q}"
        if n_members == 100 and not checked_cost:
            checked_cost = True
            per = (time.time() - t0) / 100
            est = per * 12 * qmax / 6 / 10  # rough member density ~1/10 lanes
            print(f"[cost] {per*1000:.2f} ms/member after 100; "
                  f"crude ETA {est:.0f}s", flush=True)
    dt = time.time() - t0
    print(f"qmax={qmax}: members={n_members} not_all_plus={n_not_ap} "
          f"mismatches={n_mismatch} omega_hist={omega_hist}")
    print(f"w<4 members: {n_w2}")
    print(f"total {dt:.1f}s")


if __name__ == "__main__":
    main()

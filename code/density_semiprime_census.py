#!/usr/bin/env python3
"""Census + verification for the semiprime h=3 partial-converse family (T1).

Family F: primes ell = 3 (mod 4) with q = 6*ell - 1 composite and
Omega(q) = 2 (q = p1*p2, necessarily distinct primes in this lane).

Theorem A (turyn_theory/density_partial_converse.md): for q in F no Turyn
pair of order t = 3*ell exists.  Mechanism, all deterministic:
  * anchor lemma: no prime factor of composite 6*ell-1 is +-1 mod ell
    (such a factor is >= 2*ell-1 because ell+-1 are even, forcing an odd
    cofactor < 3.5, i.e. 1 or 3; both impossible);
  * semiprime relation p1*p2 = -1 mod ell gives p2 = -p1^{-1}, hence
    <p2^2> = <p1^2> mod ell, and the mod-12 compatibility inside
    (Z/12ell)^* leaves exactly M(q)|_ell = <p1^2>, of odd order
    oddpart(ord_ell(p1)) >= 3;
  * ell = 3 mod 4 makes v2(w) = v2(ell-1) = 1 unconditional (-1 in V_ell),
    so w = 2*oddpart(ord_ell(p1)) >= 6 and d = (ell-1)/w is odd;
  * cor:h3-support-sum-prime (d odd, w >= 4) fires the h=3 support stage.
The {7,11} mod-12 semiprimes are killed classically by two squares; the
{1,5} class is entirely blind-spot and is the new content.

Modes (both cheap; instrumented past 5 s):
  --verify QMAX   check every {1,5} member with q <= QMAX (default 100000)
                  against the repo machinery cached_v_group: all_plus, exact
                  w == 2*oddpart(ord_ell(p1)), d odd, support fires; also
                  blind-spot membership cross-check up to --blindspot-max.
  --census XMAX   classify q = 6*ell-1 for all primes ell = 3 mod 4 with
                  q <= XMAX (default 10^7): q prime / semiprime{1,5} /
                  semiprime{7,11} / Omega>=3; family statistics, and the
                  gcd-of-orders proxy for what the Omega>=3 class would need.

Killable by name: pkill -f density_semiprime_census
"""
from __future__ import annotations

import argparse
import math
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def spf_sieve(limit: int) -> np.ndarray:
    """Smallest-prime-factor table; spf[n] == 0 for n prime (or n < 2)."""
    spf = np.zeros(limit + 1, dtype=np.int32)
    for i in range(2, int(limit ** 0.5) + 1):
        if spf[i] == 0:
            sl = spf[i * i:: i]
            sl[sl == 0] = i
    return spf


def factorize(n: int, spf: np.ndarray) -> list[tuple[int, int]]:
    out: list[tuple[int, int]] = []
    while n > 1:
        p = int(spf[n]) or n
        e = 0
        while n % p == 0:
            n //= p
            e += 1
        out.append((p, e))
    return out


def mult_order(a: int, ell: int, ell1_factors: list[tuple[int, int]]) -> int:
    """Order of a mod ell (ell prime), given the factorization of ell-1."""
    o = ell - 1
    for f, _e in ell1_factors:
        while o % f == 0 and pow(a, o // f, ell) == 1:
            o //= f
    return o


def oddpart(n: int) -> int:
    while n % 2 == 0:
        n //= 2
    return n


def census(xmax: int) -> dict:
    t0 = time.time()
    spf = spf_sieve(xmax)
    print(f"[census] spf sieve to {xmax} built in {time.time()-t0:.1f}s",
          flush=True)
    lmax = (xmax + 1) // 6
    stats = {
        "ell_total": 0, "q_prime": 0, "semi_15": 0, "semi_711": 0,
        "omega2_higher": 0, "big": 0, "big_gcd_ge3": 0,
        "member_w_min": None, "member_w_hist_small": {},
    }
    members: list[tuple[int, int, int, int, int]] = []  # (q, ell, p1, p2, w)
    ells = [i for i in range(7, lmax + 1, 4)
            if i % 4 == 3 and spf[i] == 0]
    n_ell = len(ells)
    last = t0
    for idx, ell in enumerate(ells):
        now = time.time()
        if now - t0 > 5 and now - last > 10:
            eta = (now - t0) / (idx + 1) * (n_ell - idx - 1)
            print(f"  [progress] {idx+1}/{n_ell} ell, elapsed {now-t0:.0f}s, "
                  f"eta {eta:.0f}s", flush=True)
            last = now
        q = 6 * ell - 1
        stats["ell_total"] += 1
        fac = factorize(q, spf)
        omega_big = sum(e for _p, e in fac)
        if omega_big == 1:
            stats["q_prime"] += 1
            continue
        ell1f = factorize(ell - 1, spf)
        if omega_big == 2 and len(fac) == 2:
            p1, p2 = fac[0][0], fac[1][0]
            assert p1 % ell not in (1, ell - 1), (q, ell, p1)  # anchor lemma
            assert p2 % ell not in (1, ell - 1), (q, ell, p2)
            if p1 % 4 == 3:
                assert p2 % 4 == 3, (q, p1, p2)
                stats["semi_711"] += 1  # classical two-squares kill
                continue
            assert {p1 % 12, p2 % 12} == {1, 5}, (q, p1, p2)
            stats["semi_15"] += 1
            n1 = mult_order(p1 % ell, ell, ell1f)
            n2 = mult_order(p2 % ell, ell, ell1f)
            assert oddpart(n1) == oddpart(n2), (q, n1, n2)  # invariance
            w = 2 * oddpart(n1)
            assert w >= 6, (q, w)
            d = (ell - 1) // w
            assert d % 2 == 1, (q, w, d)
            assert ((ell - 1) // 2) % w not in (0, 1), (q, w)  # fires
            members.append((q, ell, p1, p2, w))
            mw = stats["member_w_min"]
            stats["member_w_min"] = w if mw is None else min(mw, w)
            if w <= 20:
                h = stats["member_w_hist_small"]
                h[w] = h.get(w, 0) + 1
            continue
        if omega_big == 2:
            # q = p^2 impossible in this lane: -1 not a QR mod ell = 3 mod 4
            raise AssertionError(f"square semiprime q={q}")
        if len(fac) == 2:
            stats["omega2_higher"] += 1
            continue
        stats["big"] += 1
        g = 0
        for p, _e in fac:
            g = math.gcd(g, mult_order(p % ell, ell, ell1f))
        if oddpart(g) >= 3:
            stats["big_gcd_ge3"] += 1
    stats["members"] = members
    print(f"[census] done in {time.time()-t0:.1f}s", flush=True)
    return stats


def verify(qmax: int, blindspot_max: int) -> None:
    from orbit_signature_scan import blind_spot_qs, cached_v_group
    t0 = time.time()
    spf = spf_sieve(qmax)
    members = []
    for ell in range(11, (qmax + 1) // 6 + 1, 4):
        if ell % 4 != 3 or spf[ell] != 0:
            continue
        q = 6 * ell - 1
        fac = factorize(q, spf)
        if sum(e for _p, e in fac) == 2 and len(fac) == 2 \
                and fac[0][0] % 4 == 1:
            members.append((q, ell, fac[0][0], fac[1][0]))
    print(f"[verify] {len(members)} blind-spot semiprime members with "
          f"q <= {qmax}", flush=True)
    bs = set(blind_spot_qs(blindspot_max))
    n_checked = 0
    last = t0
    for i, (q, ell, p1, p2) in enumerate(members):
        t_, V, all_plus = cached_v_group(q)
        assert t_ == 3 * ell
        assert all_plus, f"q={q} not all-plus"
        w_code = len({v % ell for v in V})
        ell1f = factorize(ell - 1, spf)
        w_pred = 2 * oddpart(mult_order(p1 % ell, ell, ell1f))
        assert w_code == w_pred, (q, w_code, w_pred)
        d = (ell - 1) // w_code
        assert d % 2 == 1 and w_code >= 6, (q, w_code, d)
        assert ((ell - 1) // 2) % w_code not in (0, 1), (q, w_code)
        if q <= blindspot_max:
            assert q in bs, f"q={q} expected blind-spot"
        n_checked += 1
        if n_checked == 100:
            per = (time.time() - t0) / 100
            print(f"  [cost] {per*1000:.1f} ms/order after 100 orders; "
                  f"extrapolated total {per*len(members):.0f}s", flush=True)
        now = time.time()
        if now - t0 > 5 and now - last > 10:
            eta = (now - t0) / (i + 1) * (len(members) - i - 1)
            print(f"  [progress] {i+1}/{len(members)}, elapsed {now-t0:.0f}s,"
                  f" eta {eta:.0f}s", flush=True)
            last = now
    print(f"[verify] all {n_checked} members verified against cached_v_group"
          f" (w exact, all_plus, d odd, support fires); "
          f"blind-spot membership checked for q <= {blindspot_max}; "
          f"{time.time()-t0:.1f}s", flush=True)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--verify", type=int, nargs="?", const=100000,
                    default=None, metavar="QMAX")
    ap.add_argument("--blindspot-max", type=int, default=20000)
    ap.add_argument("--census", type=int, nargs="?", const=10 ** 7,
                    default=None, metavar="XMAX")
    args = ap.parse_args()
    if args.verify is None and args.census is None:
        args.verify = 100000
        args.census = 10 ** 7
    if args.verify is not None:
        verify(args.verify, min(args.blindspot_max, args.verify))
    if args.census is not None:
        s = census(args.census)
        m = s["members"]
        print()
        print(f"== census to q <= {args.census} ==")
        print(f"primes ell = 3 mod 4 (q composite or not): {s['ell_total']}")
        print(f"  q prime (Turyn existence; out of scope): {s['q_prime']}")
        print(f"  q semiprime {{1,5}} mod 12  (THEOREM A, new kill): "
              f"{s['semi_15']}")
        print(f"  q semiprime {{7,11}} mod 12 (two-squares, classical): "
              f"{s['semi_711']}")
        print(f"  q = p^a r^b, Omega >= 3 (remark-only extension): "
              f"{s['omega2_higher']}")
        print(f"  q with omega >= 3 (parity-wall complement): {s['big']}"
              f"  [gcd-of-orders oddpart >= 3: {s['big_gcd_ge3']} — "
              f"upper proxy for what any w >= 4 argument must control]")
        print(f"member minimum w: {s['member_w_min']}   "
              f"w-histogram (w <= 20): {s['member_w_hist_small']}")
        print(f"first 12 members (q, ell, p1, p2, w): {m[:12]}")
        print(f"last member: {m[-1] if m else None}")


if __name__ == "__main__":
    main()

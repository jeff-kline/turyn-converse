#!/usr/bin/env python3
"""Composite-q multiplier scan for Turyn pairs (theory track T3).

For q = 2t-1 = prod p^e, a Turyn pair admits, for every
    sigma in M(q) = intersection over p|q of <p> in (Z/4t)^*,
the forced multiplier
    r^(u) = eps * r,   s^(u) = s,
where sigma <-> (eps, u):  eps = -1 if sigma % 4 == 3 else +1  (action on i),
                           u   = sigma % t                     (decimation on C_t).

KILL: adjoin the symmetry (+1,-1) to get M^+; if some (eps=-1,u) in M^+ forces
r^(u) = -r with an ODD-length <u>-orbit on Z/t \ {0}, then r == 0: no pair.

Everything here is finite integer group theory -- no number fields, no search.
Budget: pure python, < a few seconds, < ~100 MB.
"""
import sys
from functools import reduce


def factor(n):
    f = {}
    d = 2
    while d * d <= n:
        while n % d == 0:
            f[d] = f.get(d, 0) + 1
            n //= d
        d += 1
    if n > 1:
        f[n] = f.get(n, 0) + 1
    return f


def divisors(n):
    ds = []
    d = 1
    while d * d <= n:
        if n % d == 0:
            ds.append(d)
            if d != n // d:
                ds.append(n // d)
        d += 1
    return sorted(ds)


def ord_mod(a, m):
    a %= m
    if a == 0:
        return None
    x = a % m
    k = 1
    while x != 1 % m:
        x = (x * a) % m
        k += 1
        if k > m:
            return None
    return k


def cyclic_sub(g, mod):
    """<g> as a set of residues mod `mod`."""
    g %= mod
    s = {1 % mod}
    x = g
    while x not in s:
        s.add(x)
        x = (x * g) % mod
    return s


def crt2(a1, m1, a2, m2):
    inv = pow(m1 % m2, -1, m2)
    tt = ((a2 - a1) * inv) % m2
    return (a1 + m1 * tt) % (m1 * m2)


def gen_group(elts, mod):
    S = {1 % mod} | {e % mod for e in elts}
    frontier = list(S)
    while frontier:
        x = frontier.pop()
        for y in list(S):
            z = (x * y) % mod
            if z not in S:
                S.add(z)
                frontier.append(z)
    return S


def orbits_mult(u, t):
    """Orbits of j -> u*j mod t on {1,...,t-1}."""
    u %= t
    seen = set()
    out = []
    for j in range(1, t):
        if j in seen:
            continue
        orb = []
        x = j
        while x not in seen:
            seen.add(x)
            orb.append(x)
            x = (u * x) % t
        out.append(orb)
    return out


# ---- classical obstructions, for cross-labelling ----
def two_squares_fail(q):
    """q not a sum of two squares: some prime 3 mod 4 to an odd power."""
    for p, e in factor(q).items():
        if p % 4 == 3 and e % 2 == 1:
            return True
    return False


def selfconj_kill(q, t):
    """Prop 3.5: some ell=3 mod4, ell^k || q with (k odd) or
    (k even and ord_d(ell) odd for every d|t)."""
    fac = factor(q)
    ds = divisors(t)
    for ell, k in fac.items():
        if ell % 4 != 3:
            continue
        if k % 2 == 1:
            return True
        if all((ord_mod(ell, d) or 1) % 2 == 1 for d in ds if d > 1):
            return True
    return False


def analyze(q, verbose=False):
    t = (q + 1) // 2
    mod = 4 * t
    primes = sorted(factor(q))
    subs = [cyclic_sub(p, mod) for p in primes]
    M = reduce(lambda a, b: a & b, subs)
    sym = crt2(1, 4, (t - 1) % t, t)          # (+1, -1)
    Mplus = gen_group(M | {sym}, mod)

    def eu(sigma):
        return (-1 if sigma % 4 == 3 else 1, sigma % t)

    kills = []
    new_mults = set()
    for sigma in Mplus:
        eps, u = eu(sigma)
        if eps == -1:
            if any(len(o) % 2 == 1 for o in orbits_mult(u, t)):
                kills.append((eps, u))
        if u not in (1 % t, (t - 1) % t):     # a genuinely new decimation
            new_mults.add((eps, u))

    res = dict(
        q=q, t=t, primes=primes,
        Mord=len(M), Mplusord=len(Mplus),
        kill=bool(kills),
        kills=sorted(set(kills))[:6],
        new_mults=sorted(new_mults)[:10],
    )
    if verbose:
        print(f"q={q}  t={t}  q=" + "*".join(f"{p}^{e}" for p, e in factor(q).items()))
        print(f"  M(q) order = {len(M)},  M^+ order = {len(Mplus)}")
        # print M elements as (eps,u)
        elems = sorted({eu(s) for s in M})
        print(f"  M elements (eps,u): {elems}")
        print(f"  new decimations (eps,u), u!=+-1: {sorted(new_mults)}")
        print(f"  KILL: {bool(kills)}  witnesses (eps,u): {sorted(set(kills))[:6]}")
        print(f"  classical: two_squares_fail={two_squares_fail(q)} "
              f"selfconj={selfconj_kill(q,t)}")
    return res


def sweep(qmax=2000):
    composite = []
    q = 5
    while q <= qmax:
        if q % 4 == 1 and len(factor(q)) + sum(factor(q).values()) > 2:  # composite
            # composite := not prime and not 1
            fac = factor(q)
            is_prime = (len(fac) == 1 and list(fac.values())[0] == 1)
            if not is_prime:
                composite.append(q)
        q += 4
    total_kill = 0
    new_kill = []          # multiplier kills NOT caught by two-squares or self-conj
    subsumed_kill = 0
    for q in composite:
        r = analyze(q)
        if r["kill"]:
            total_kill += 1
            ts = two_squares_fail(q)
            sc = selfconj_kill(q, r["t"])
            if ts or sc:
                subsumed_kill += 1
            else:
                new_kill.append(q)
    print(f"composite q=1mod4, q<= {qmax}: {len(composite)}")
    print(f"multiplier-theorem KILLs: {total_kill}  "
          f"(subsumed by two-squares/self-conj: {subsumed_kill}, "
          f"NOT subsumed: {len(new_kill)})")
    if new_kill:
        print("NON-SUBSUMED multiplier kills:")
        for q in new_kill:
            r = analyze(q)
            print(f"  q={q}  t={r['t']}  primes={r['primes']}  kills={r['kills']}")
    else:
        print("  (no multiplier kill escapes two-squares/self-conjugacy)")


if __name__ == "__main__":
    args = sys.argv[1:]
    if args and args[0] == "--sweep":
        qmax = int(args[1]) if len(args) > 1 else 2000
        sweep(qmax)
    elif args:
        for a in args:
            analyze(int(a), verbose=True)
            print()
    else:
        # default: q=441 detail + a few survivors + full sweep
        for q in (441, 1469, 1937, 549, 185, 245, 45, 65):
            analyze(q, verbose=True)
            print()
        sweep(2000)

#!/usr/bin/env python3
"""Orbit-algebra inspector for sub-torus marginal Turyn obstructions.

This is the theorem-facing layer underneath subtorus_marginal_decision.py.
For q=2t-1 and a divisor tp=t', it builds the fixed orbit algebra

    A(tp,V') = Z[C_tp]^{V'}

in the orbit-sum basis E_O=sum_{j in O} y^j.  Multiplication is recorded by
integer constants

    E_O E_P^(-1) = sum_Q N[O,P,Q] E_Q.

The marginal pair equations are therefore finite quadratic equations in the
orbit values of A and B, with the same boxes/parities used by the CP-SAT and
independent verification scripts.  This script does not try to solve general
instances; it exposes the algebra, signatures, and the first structural family
(the two-orbit/transitive scalar collapse).
"""
from __future__ import annotations

import argparse
import itertools
import json
import math
import os
import sys
import time
from dataclasses import dataclass

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from multiplier_reduced_decision import orbits, v_group  # noqa: E402


def orbit_labels(n: int, orbit_list: list[list[int]]) -> list[int]:
    labels = [-1] * n
    for idx, orb in enumerate(orbit_list):
        for value in orb:
            labels[value] = idx
    assert all(label >= 0 for label in labels)
    return labels


def odd_domain(h: int) -> list[int]:
    return [v for v in range(-h, h + 1) if v % 2 != 0]


def even_origin_domain(h: int) -> list[int]:
    if h == 1:
        return [0]
    return [v for v in range(-(h - 1), h) if v % 2 == 0]


def compact(values: list[int], limit: int = 10) -> str:
    if len(values) <= limit:
        return str(values)
    head = ", ".join(str(v) for v in values[:limit])
    return f"[{head}, ...] (len={len(values)})"


@dataclass(frozen=True)
class MarginalOrbitAlgebra:
    q: int
    t: int
    tp: int
    h: int
    V: list[int]
    Vp: list[int]
    orbits: list[list[int]]
    labels: list[int]
    zero_orbit: int
    structure: list[list[list[int]]]

    @property
    def reps(self) -> list[int]:
        return [min(orb) for orb in self.orbits]

    @property
    def nonzero_reps(self) -> list[int]:
        return [min(orb) for orb in self.orbits if 0 not in orb]

    @property
    def sizes(self) -> list[int]:
        return [len(orb) for orb in self.orbits]

    @property
    def a_domains(self) -> list[list[int]]:
        origin = even_origin_domain(self.h)
        odd = odd_domain(self.h)
        return [origin if i == self.zero_orbit else odd
                for i in range(len(self.orbits))]

    @property
    def b_domains(self) -> list[list[int]]:
        odd = odd_domain(self.h)
        return [odd for _ in self.orbits]

    def equation_terms(self, q_index: int) -> list[tuple[int, int, int]]:
        """Terms c*x_i*x_j for the Q-th coefficient equation.

        Coefficients are symmetrized for i<=j.  The same term list applies to
        the A and B sides; the marginal equation uses both copies.
        """
        terms: list[tuple[int, int, int]] = []
        n = len(self.orbits)
        for i in range(n):
            for j in range(i, n):
                coeff = self.structure[i][j][q_index]
                if i != j:
                    coeff += self.structure[j][i][q_index]
                if coeff:
                    terms.append((coeff, i, j))
        return terms

    def to_jsonable(self) -> dict:
        return {
            "q": self.q,
            "t": self.t,
            "tp": self.tp,
            "h": self.h,
            "V_size": len(self.V),
            "Vp": self.Vp,
            "orbits": self.orbits,
            "sizes": self.sizes,
            "zero_orbit": self.zero_orbit,
            "A_domains": self.a_domains,
            "B_domains": self.b_domains,
            "structure": self.structure,
        }


def build_algebra(q: int, tp: int) -> MarginalOrbitAlgebra:
    t, V, all_plus = v_group(q)
    if not all_plus:
        raise SystemExit(
            f"q={q}: M(q) has an eps=-1 multiplier; use the signed marginal "
            "algebra from the paper instead of this constant-orbit implementation."
        )
    if tp <= 1 or t % tp:
        raise SystemExit(f"t'={tp} must be a nontrivial divisor of t={t}")
    h = t // tp
    Vp = sorted({v % tp for v in V})
    orbit_list = orbits(tp, Vp)
    labels = orbit_labels(tp, orbit_list)
    zero = labels[0]
    n_orb = len(orbit_list)
    structure = [[[0 for _ in range(n_orb)] for _ in range(n_orb)]
                 for _ in range(n_orb)]

    orbit_arrays = [np.asarray(orb, dtype=np.int64) for orb in orbit_list]
    for oi, left in enumerate(orbit_arrays):
        for pi, right in enumerate(orbit_arrays):
            diffs = (left[:, None] - right[None, :]) % tp
            coeff_by_residue = np.bincount(diffs.ravel(), minlength=tp)
            for qi, target in enumerate(orbit_arrays):
                coeffs = set(coeff_by_residue[target].tolist())
                if len(coeffs) != 1:
                    raise AssertionError(
                        "product coefficients are not constant on a V' orbit: "
                        f"O={oi}, P={pi}, Q={qi}, coeffs={sorted(coeffs)}"
                    )
                structure[oi][pi][qi] = coeffs.pop()

    return MarginalOrbitAlgebra(
        q=q, t=t, tp=tp, h=h, V=V, Vp=Vp, orbits=orbit_list,
        labels=labels, zero_orbit=zero, structure=structure
    )


def constant_row_solutions(alg: MarginalOrbitAlgebra) -> list[tuple[int, int, int, int]]:
    """Enumerate the transitive/two-orbit scalar system."""
    if len(alg.orbits) != 2:
        raise SystemExit(
            f"(q={alg.q}, t'={alg.tp}) has {len(alg.orbits)} orbits; "
            "the scalar two-orbit check requires exactly 2."
        )
    a0_values = alg.a_domains[alg.zero_orbit]
    odd_values = odd_domain(alg.h)
    m = alg.tp

    left: dict[tuple[int, int], list[tuple[int, int]]] = {}
    for a0 in a0_values:
        for c in odd_values:
            paf_a = 2 * a0 * c + (m - 2) * c * c
            sq_a = a0 * a0 + (m - 1) * c * c
            left.setdefault((paf_a, sq_a), []).append((a0, c))

    out: list[tuple[int, int, int, int]] = []
    for b0 in odd_values:
        for d in odd_values:
            paf_b = 2 * b0 * d + (m - 2) * d * d
            sq_b = b0 * b0 + (m - 1) * d * d
            for a0, c in left.get((-paf_b, alg.q - sq_b), []):
                out.append((a0, c, b0, d))
    return out


def two_orbit_rep_status(q: int, m: int, h: int) -> tuple[str, str, dict]:
    """Exact two-orbit feasibility by the representation-pair criterion.

    thm:two-orbit-reps: for a transitive prime node m=t' with fiber h=t/m,
    the scalar system of thm:t2-twoorbit is feasible iff there are
    representations q = X^2+Y^2 (X even, Y odd; conductor 1) and
    q = X'^2+Y'^2 (X' odd, Y' even; conductor m) with X == X' and
    Y == Y' (mod m), whose inverse values
      a0=(X+(m-1)X')/m, c=(X-X')/m, b0=(Y+(m-1)Y')/m, d=(Y-Y')/m
    lie in the fiber boxes |a0|<=h-1 and |c|,|b0|,|d|<=h.  The parities of
    (a0,c,b0,d) are automatic; for h >= 2m+2 the boxes are automatic.
    """
    reps = gaussian_representations(q)
    conductor_one = [(x, y) for x, y in reps if x % 2 == 0]
    conductor_m = [(x, y) for x, y in reps if x % 2 != 0]
    detail: dict = {
        "n_reps": len(reps),
        "n_conductor_one": len(conductor_one),
        "n_conductor_m": len(conductor_m),
        "congruent_pairs": 0,
        "boxed_witnesses": [],
        "auto_box": h >= 2 * m + 2,
    }
    if not reps:
        return "UNSAT", "no_representation", detail
    for x1, y1 in conductor_one:
        for xm, ym in conductor_m:
            if (x1 - xm) % m or (y1 - ym) % m:
                continue
            detail["congruent_pairs"] += 1
            a0 = (x1 + (m - 1) * xm) // m
            c = (x1 - xm) // m
            b0 = (y1 + (m - 1) * ym) // m
            d = (y1 - ym) // m
            assert a0 % 2 == 0 and c % 2 and b0 % 2 and d % 2, \
                "two-orbit parities must be automatic"
            if abs(a0) <= h - 1 and max(abs(c), abs(b0), abs(d)) <= h:
                detail["boxed_witnesses"].append((a0, c, b0, d))
    if detail["boxed_witnesses"]:
        return "SAT", "boxed_witness", detail
    if detail["congruent_pairs"]:
        return "UNSAT", "box_cut", detail
    return "UNSAT", "no_congruent_pair", detail


def two_orbit_representation_check(alg: MarginalOrbitAlgebra,
                                   limit: int) -> None:
    """CLI wrapper: representation criterion + scalar cross-check."""
    if len(alg.orbits) != 2:
        raise SystemExit(
            f"(q={alg.q}, t'={alg.tp}) has {len(alg.orbits)} orbits; "
            "the representation criterion requires a transitive prime node."
        )
    status, mechanism, detail = two_orbit_rep_status(alg.q, alg.tp, alg.h)
    print(
        "two-orbit representation criterion: "
        f"reps={detail['n_reps']} "
        f"(conductor-1 side={detail['n_conductor_one']}, "
        f"conductor-m side={detail['n_conductor_m']}) "
        f"congruent pairs={detail['congruent_pairs']} "
        f"auto_box(h>={2 * alg.tp + 2})={detail['auto_box']}"
    )
    for witness in detail["boxed_witnesses"][:limit]:
        print(f"  witness (a0,c,b0,d)={witness}")
    print(f"  representation result: {status} ({mechanism})")
    scalar = constant_row_solutions(alg)
    scalar_status = "SAT" if scalar else "UNSAT"
    print(
        f"  scalar enumeration cross-check: {scalar_status} "
        f"({len(scalar)} tuples)"
    )
    if (status == "SAT") != bool(scalar):
        raise SystemExit(
            "representation criterion disagrees with the scalar enumeration"
        )


def residue_domains(domains: list[list[int]], modulus: int) -> list[list[int]]:
    return [sorted({value % modulus for value in dom}) for dom in domains]


def vector_dimension(alg: MarginalOrbitAlgebra) -> int:
    # one group-ring coefficient per orbit, plus the augmentation-square cut
    return len(alg.orbits) + 1


def encoded_mod_vectors(
    alg: MarginalOrbitAlgebra,
    domains: list[list[int]],
    modulus: int,
    lo: int,
    hi: int,
) -> np.ndarray:
    """Return exact base-modulus encodings of side vectors for assignments.

    The encoded vector is

        (coefficient at every orbit of XX^*, augmentation(X)^2) mod modulus.

    For a marginal pair, the A-side vector plus the B-side vector must equal
    the corresponding q-vector.  This is the modular analogue of the orbit
    algebra equations, and is separable by side.
    """
    n = len(alg.orbits)
    idx = np.arange(lo, hi, dtype=np.uint64)
    values = np.empty((hi - lo, n), dtype=np.int64)
    work = idx.copy()
    for col, dom in enumerate(domains):
        radix = len(dom)
        dom_arr = np.asarray(dom, dtype=np.int64)
        values[:, col] = dom_arr[work % radix]
        work //= radix

    vec = np.zeros((hi - lo, vector_dimension(alg)), dtype=np.int64)
    for q_idx in range(n):
        for coeff, i, j in alg.equation_terms(q_idx):
            vec[:, q_idx] += coeff * values[:, i] * values[:, j]
    aug = values @ np.asarray(alg.sizes, dtype=np.int64)
    vec[:, n] = aug * aug
    vec %= modulus

    key = np.zeros(hi - lo, dtype=np.uint64)
    for col in range(vec.shape[1]):
        key = key * np.uint64(modulus) + vec[:, col].astype(np.uint64)
    return key


def target_key_for_b_vectors(
    alg: MarginalOrbitAlgebra,
    b_keys: np.ndarray,
    modulus: int,
) -> np.ndarray:
    """Decode B vectors and encode the A vectors needed to complete them."""
    dim = vector_dimension(alg)
    work = b_keys.copy()
    digits = np.empty((len(b_keys), dim), dtype=np.int64)
    for col in range(dim - 1, -1, -1):
        digits[:, col] = (work % np.uint64(modulus)).astype(np.int64)
        work //= np.uint64(modulus)
    rhs = np.zeros(dim, dtype=np.int64)
    rhs[alg.zero_orbit] = alg.q % modulus
    rhs[-1] = alg.q % modulus
    need = (rhs[None, :] - digits) % modulus

    key = np.zeros(len(b_keys), dtype=np.uint64)
    for col in range(dim):
        key = key * np.uint64(modulus) + need[:, col].astype(np.uint64)
    return key


def modular_mitm(alg: MarginalOrbitAlgebra, modulus: int, cap: int,
                 chunk: int) -> bool | None:
    """Exact modular feasibility test by side-separated MITM.

    Returns False when the marginal equations are infeasible modulo modulus,
    True when at least one residue assignment survives, and None when the
    residue-side enumeration exceeds cap.
    """
    if modulus < 2:
        raise SystemExit("--mod-check requires modulus >= 2")
    dim = vector_dimension(alg)
    if modulus ** dim >= 2 ** 63:
        raise SystemExit(
            f"modulus^{dim} is too large for exact uint64 vector encoding"
        )
    a_domains = residue_domains(alg.a_domains, modulus)
    b_domains = residue_domains(alg.b_domains, modulus)
    total_a = math.prod(len(dom) for dom in a_domains)
    total_b = math.prod(len(dom) for dom in b_domains)
    print(
        f"mod {modulus}: A residue assignments={total_a:,} "
        f"B residue assignments={total_b:,} dim={dim}"
    )
    if total_a > cap or total_b > cap:
        print(f"  REFUSE: side exceeds cap={cap:,}")
        return None

    parts = []
    for lo in range(0, total_a, chunk):
        hi = min(lo + chunk, total_a)
        parts.append(encoded_mod_vectors(alg, a_domains, modulus, lo, hi))
    a_keys = np.unique(np.concatenate(parts) if parts else np.empty(0, np.uint64))
    print(f"  A side unique vectors={len(a_keys):,}")

    for lo in range(0, total_b, chunk):
        hi = min(lo + chunk, total_b)
        b_keys = encoded_mod_vectors(alg, b_domains, modulus, lo, hi)
        needed = target_key_for_b_vectors(alg, b_keys, modulus)
        hit = np.isin(needed, a_keys, assume_unique=False)
        if bool(hit.any()):
            print(f"  modular result: PASS (surviving residue join found)")
            return True
    print(f"  modular result: UNSAT modulo {modulus}")
    return False


def side_vector(alg: MarginalOrbitAlgebra, values: tuple[int, ...]) -> tuple[int, ...]:
    """Exact side vector for XX^* plus augmentation-square."""
    terms_by_q = [alg.equation_terms(q_idx) for q_idx in range(len(alg.orbits))]
    return side_vector_from_terms(terms_by_q, alg.sizes, values)


def side_vector_from_terms(
    terms_by_q: list[list[tuple[int, int, int]]],
    sizes: list[int],
    values: tuple[int, ...],
) -> tuple[int, ...]:
    """Exact side vector using precomputed equation terms."""
    out = []
    for terms in terms_by_q:
        total = 0
        for coeff, i, j in terms:
            total += coeff * values[i] * values[j]
        out.append(total)
    aug = sum(size * value for size, value in zip(sizes, values))
    out.append(aug * aug)
    return tuple(out)


def exact_integer_mitm(alg: MarginalOrbitAlgebra, cap: int) -> bool | None:
    """Exact side-separated MITM over integer orbit values.

    This is intended for compact few-orbit certificates.  It is a proof of
    infeasibility when it reports UNSAT, because every integer assignment in the
    stated boxes/parities is enumerated and joined on the exact orbit-algebra
    coefficient vector plus the trivial-character square equation.
    """
    total_a = math.prod(len(dom) for dom in alg.a_domains)
    total_b = math.prod(len(dom) for dom in alg.b_domains)
    print(
        f"integer MITM: A assignments={total_a:,} "
        f"B assignments={total_b:,} dim={vector_dimension(alg)}"
    )
    if total_a > cap or total_b > cap:
        print(f"  REFUSE: side exceeds cap={cap:,}")
        return None

    target = [0] * vector_dimension(alg)
    target[alg.zero_orbit] = alg.q
    target[-1] = alg.q

    a_vectors: set[tuple[int, ...]] = set()
    for values in itertools.product(*alg.a_domains):
        a_vectors.add(side_vector(alg, values))
    print(f"  A side unique exact vectors={len(a_vectors):,}")

    for values in itertools.product(*alg.b_domains):
        b_vec = side_vector(alg, values)
        need = tuple(target[i] - b_vec[i] for i in range(len(target)))
        if need in a_vectors:
            print("  exact integer result: SAT (surviving orbit-value join found)")
            print(f"  B witness values={values}")
            return True
    print("  exact integer result: UNSAT")
    return False


def two_square_row_sums(q: int) -> set[int]:
    out = set()
    limit = math.isqrt(q)
    for x in range(-limit, limit + 1):
        y2 = q - x * x
        if y2 < 0:
            continue
        y = math.isqrt(y2)
        if y * y == y2:
            out.add(x)
    return out


def h3_filtered_rows(
    alg: MarginalOrbitAlgebra,
    side: str,
    allowed_sums_by_support: dict[int, set[int]],
    support_limit: int,
    terms_by_q: list[list[tuple[int, int, int]]],
):
    """Generate h=3 rows passing support and augmentation-side filters."""
    assert side in {"A", "B"}
    zero = alg.zero_orbit
    indices = [idx for idx in range(len(alg.orbits)) if idx != zero]
    sizes = alg.sizes
    origin_values = (-2, 2) if side == "A" else (-3, -1, 1, 3)
    values = [0] * len(alg.orbits)
    allowed_sums = set().union(*allowed_sums_by_support.values())
    allowed_supports = set(allowed_sums_by_support)
    suffix_max = [0] * (len(indices) + 1)
    suffix_support = [0] * (len(indices) + 1)
    for pos in range(len(indices) - 1, -1, -1):
        suffix_max[pos] = suffix_max[pos + 1] + 3 * sizes[indices[pos]]
        suffix_support[pos] = suffix_support[pos + 1] + sizes[indices[pos]]

    def can_hit_allowed(row_sum: int, remaining: int) -> bool:
        lo = row_sum - remaining
        hi = row_sum + remaining
        return any(lo <= target <= hi for target in allowed_sums)

    def rec(pos: int, support: int, row_sum: int):
        if support > support_limit:
            return
        if not any(
            support <= allowed_support <= support + suffix_support[pos]
            for allowed_support in allowed_supports
        ):
            return
        if not can_hit_allowed(row_sum, suffix_max[pos]):
            return
        if pos == len(indices):
            if row_sum in allowed_sums_by_support.get(support, set()):
                row = tuple(values)
                yield support, row, side_vector_from_terms(terms_by_q, sizes, row)
            return
        idx = indices[pos]
        size = sizes[idx]
        for value in (-3, -1, 1, 3):
            values[idx] = value
            next_support = support + (size if abs(value) == 3 else 0)
            yield from rec(pos + 1, next_support, row_sum + size * value)

    for origin in origin_values:
        values[zero] = origin
        origin_support = 1 if side == "B" and abs(origin) == 3 else 0
        yield from rec(0, origin_support, origin)


def side_vectors_from_terms_batch(
    terms_by_q: list[list[tuple[int, int, int]]],
    sizes: list[int],
    rows: np.ndarray,
) -> np.ndarray:
    """Vectorized exact side vectors for a batch of orbit-value rows."""
    out = np.empty((rows.shape[0], len(terms_by_q) + 1), dtype=np.int64)
    for q_idx, terms in enumerate(terms_by_q):
        total = np.zeros(rows.shape[0], dtype=np.int64)
        for coeff, i, j in terms:
            total += coeff * rows[:, i] * rows[:, j]
        out[:, q_idx] = total
    aug = rows @ np.asarray(sizes, dtype=np.int64)
    out[:, -1] = aug * aug
    return out


def h3_filtered_row_batches(
    alg: MarginalOrbitAlgebra,
    side: str,
    allowed_sums_by_support: dict[int, set[int]],
    support_limit: int,
    batch_size: int,
):
    """Generate h=3 filtered rows in numpy-friendly batches."""
    assert side in {"A", "B"}
    zero = alg.zero_orbit
    indices = [idx for idx in range(len(alg.orbits)) if idx != zero]
    sizes = alg.sizes
    origin_values = (-2, 2) if side == "A" else (-3, -1, 1, 3)
    values = [0] * len(alg.orbits)
    allowed_sums = set().union(*allowed_sums_by_support.values())
    allowed_supports = set(allowed_sums_by_support)
    suffix_max = [0] * (len(indices) + 1)
    suffix_support = [0] * (len(indices) + 1)
    for pos in range(len(indices) - 1, -1, -1):
        suffix_max[pos] = suffix_max[pos + 1] + 3 * sizes[indices[pos]]
        suffix_support[pos] = suffix_support[pos + 1] + sizes[indices[pos]]

    rows: list[tuple[int, ...]] = []
    supports: list[int] = []

    def can_hit_allowed(row_sum: int, remaining: int) -> bool:
        lo = row_sum - remaining
        hi = row_sum + remaining
        return any(lo <= target <= hi for target in allowed_sums)

    def flush():
        batch_rows = np.asarray(rows, dtype=np.int64)
        batch_supports = np.asarray(supports, dtype=np.int64)
        rows.clear()
        supports.clear()
        return batch_supports, batch_rows

    def rec(pos: int, support: int, row_sum: int):
        if support > support_limit:
            return
        if not any(
            support <= allowed_support <= support + suffix_support[pos]
            for allowed_support in allowed_supports
        ):
            return
        if not can_hit_allowed(row_sum, suffix_max[pos]):
            return
        if pos == len(indices):
            if row_sum in allowed_sums_by_support.get(support, set()):
                rows.append(tuple(values))
                supports.append(support)
                if len(rows) >= batch_size:
                    yield flush()
            return
        idx = indices[pos]
        size = sizes[idx]
        for value in (-3, -1, 1, 3):
            values[idx] = value
            next_support = support + (size if abs(value) == 3 else 0)
            yield from rec(pos + 1, next_support, row_sum + size * value)

    for origin in origin_values:
        values[zero] = origin
        origin_support = 1 if side == "B" and abs(origin) == 3 else 0
        yield from rec(0, origin_support, origin)
    if rows:
        yield flush()


def h3_possible_sums_by_support(
    alg: MarginalOrbitAlgebra,
    side: str,
    support_limit: int,
) -> dict[int, set[int]]:
    """Coarse h=3 side feasibility map support -> possible row sums."""
    assert side in {"A", "B"}
    zero = alg.zero_orbit
    origin_values = (-2, 2) if side == "A" else (-3, -1, 1, 3)
    states: set[tuple[int, int]] = set()
    for value in origin_values:
        support = 1 if side == "B" and abs(value) == 3 else 0
        if support <= support_limit:
            states.add((support, value))
    for idx, size in enumerate(alg.sizes):
        if idx == zero:
            continue
        next_states: set[tuple[int, int]] = set()
        for support, row_sum in states:
            for value in (-3, -1, 1, 3):
                next_support = support + (size if abs(value) == 3 else 0)
                if next_support <= support_limit:
                    next_states.add((next_support, row_sum + size * value))
        states = next_states
    out: dict[int, set[int]] = {}
    for support, row_sum in states:
        out.setdefault(support, set()).add(row_sum)
    return out


def h3_allowed_sum_maps(
    alg: MarginalOrbitAlgebra,
    target_support: int,
) -> tuple[dict[int, set[int]], dict[int, set[int]]]:
    """Side row sums that can participate in support and two-square joins."""
    a_possible = h3_possible_sums_by_support(alg, "A", target_support)
    b_possible = h3_possible_sums_by_support(alg, "B", target_support)
    a_allowed: dict[int, set[int]] = {}
    b_allowed: dict[int, set[int]] = {}
    for a_support, a_sums in a_possible.items():
        b_support = target_support - a_support
        if b_support not in b_possible:
            continue
        b_sums = b_possible[b_support]
        for a_sum in a_sums:
            remaining = alg.q - a_sum * a_sum
            if remaining < 0:
                continue
            b_abs = math.isqrt(remaining)
            if b_abs * b_abs != remaining:
                continue
            hits = {value for value in (b_abs, -b_abs) if value in b_sums}
            if hits:
                a_allowed.setdefault(a_support, set()).add(a_sum)
                b_allowed.setdefault(b_support, set()).update(hits)
    return a_allowed, b_allowed


def h3_support_paf_check(
    alg: MarginalOrbitAlgebra,
    cap: int,
    batch_size: int = 50_000,
) -> bool | None:
    """Exact h=3 support/augmentation-filtered PAF MITM.

    This is the next layer after the support-augmentation obstruction: enumerate
    only rows satisfying the h=3 support budget and a possible augmentation row
    sum, then join on the full orbit-algebra PAF vector.
    """
    if alg.h != 3:
        raise SystemExit("--h3-support-paf-check requires h=t/t'=3")
    target_support = (alg.tp - 1) // 2
    a_allowed, b_allowed = h3_allowed_sum_maps(alg, target_support)
    terms_by_q = [alg.equation_terms(q_idx) for q_idx in range(len(alg.orbits))]
    print(
        "h=3 support PAF MITM: "
        f"target_support={target_support}"
    )
    print(f"  A allowed sums by support={{{', '.join(f'{k}: {sorted(v)}' for k, v in sorted(a_allowed.items()))}}}")
    print(f"  B allowed sums by support={{{', '.join(f'{k}: {sorted(v)}' for k, v in sorted(b_allowed.items()))}}}")
    if not a_allowed or not b_allowed:
        print("  h=3 support PAF result: UNSAT (no support/augmentation side pair)")
        return False

    target = [0] * vector_dimension(alg)
    target[alg.zero_orbit] = alg.q
    target[-1] = alg.q

    a_by_support: dict[int, set[tuple[int, ...]]] = {}
    a_rows = 0
    for supports, rows in h3_filtered_row_batches(
        alg, "A", a_allowed, target_support, batch_size
    ):
        vecs = side_vectors_from_terms_batch(terms_by_q, alg.sizes, rows)
        a_rows += rows.shape[0]
        if a_rows > cap:
            print(f"  REFUSE: A filtered rows exceed cap={cap:,}")
            return None
        for support, vec in zip(supports.tolist(), vecs.tolist()):
            a_by_support.setdefault(support, set()).add(tuple(vec))
        if a_rows % (10 * batch_size) == 0:
            print(f"  A progress: {a_rows:,} rows", flush=True)
    unique_a = sum(len(vectors) for vectors in a_by_support.values())
    print(
        f"  A filtered rows={a_rows:,} unique vectors={unique_a:,} "
        f"support buckets={sorted(a_by_support)}"
    )

    b_rows = 0
    for supports, rows in h3_filtered_row_batches(
        alg, "B", b_allowed, target_support, batch_size
    ):
        vecs = side_vectors_from_terms_batch(terms_by_q, alg.sizes, rows)
        b_rows += rows.shape[0]
        if b_rows > cap:
            print(f"  REFUSE: B filtered rows exceed cap={cap:,}")
            return None
        for support, values, b_vec in zip(
            supports.tolist(),
            rows.tolist(),
            vecs.tolist(),
        ):
            need_support = target_support - support
            if need_support not in a_by_support:
                continue
            need_vec = tuple(target[i] - b_vec[i] for i in range(len(target)))
            if need_vec in a_by_support[need_support]:
                print("  h=3 support PAF result: SAT")
                print(f"  B witness values={tuple(values)}")
                return True
        if b_rows % (10 * batch_size) == 0:
            print(f"  B progress: {b_rows:,} rows", flush=True)
    print(f"  B filtered rows={b_rows:,}")
    print("  h=3 support PAF result: UNSAT")
    return False


def exact_side_solution_sets(
    alg: MarginalOrbitAlgebra,
    cap: int,
) -> tuple[set[tuple[int, ...]], set[tuple[int, ...]], dict] | None:
    """Return side rows that participate in at least one exact marginal join.

    This is the side-set version of exact_integer_mitm(): it enumerates every
    boxed/parity-valid orbit-value row on both sides, joins on the exact
    coefficient vector plus the trivial-character square equation, and keeps
    only rows with a mate.  None means a side exceeded the requested cap.
    """
    total_a = math.prod(len(dom) for dom in alg.a_domains)
    total_b = math.prod(len(dom) for dom in alg.b_domains)
    if total_a > cap or total_b > cap:
        return None

    target = [0] * vector_dimension(alg)
    target[alg.zero_orbit] = alg.q
    target[-1] = alg.q

    a_by_vector: dict[tuple[int, ...], list[tuple[int, ...]]] = {}
    for values in itertools.product(*alg.a_domains):
        a_by_vector.setdefault(side_vector(alg, values), []).append(values)

    side_a: set[tuple[int, ...]] = set()
    side_b: set[tuple[int, ...]] = set()
    for values in itertools.product(*alg.b_domains):
        b_vec = side_vector(alg, values)
        need = tuple(target[i] - b_vec[i] for i in range(len(target)))
        mates = a_by_vector.get(need)
        if mates:
            side_b.add(values)
            side_a.update(mates)

    meta = {
        "total_a": total_a,
        "total_b": total_b,
        "unique_a_vectors": len(a_by_vector),
    }
    return side_a, side_b, meta


def projection_matrix(
    source: MarginalOrbitAlgebra,
    target: MarginalOrbitAlgebra,
) -> list[tuple[int, ...]]:
    """Matrix for the quotient projection from source orbits to target orbits."""
    if source.tp % target.tp:
        raise SystemExit(
            f"target t'={target.tp} must divide source t'={source.tp}"
        )
    rows: list[tuple[int, ...]] = []
    for target_orbit in target.orbits:
        row: tuple[int, ...] | None = None
        for residue in target_orbit:
            counts = tuple(
                sum(1 for source_residue in source_orbit
                    if source_residue % target.tp == residue)
                for source_orbit in source.orbits
            )
            if row is None:
                row = counts
            elif row != counts:
                raise AssertionError(
                    "projection coefficients are not constant on target orbit: "
                    f"source={source.tp}, target={target.tp}, "
                    f"orbit={target_orbit}, residue={residue}"
                )
        assert row is not None
        rows.append(row)
    return rows


def project_orbit_values(
    matrix: list[tuple[int, ...]],
    values: tuple[int, ...],
) -> tuple[int, ...]:
    """Project source orbit values using a matrix from projection_matrix()."""
    return tuple(
        sum(coeff * value for coeff, value in zip(row, values))
        for row in matrix
    )


def projection_compatible_rows(
    cover: MarginalOrbitAlgebra,
    domains: list[list[int]],
    left_matrix: list[tuple[int, ...]],
    left_allowed: set[tuple[int, ...]],
    right_matrix: list[tuple[int, ...]],
    right_allowed: set[tuple[int, ...]],
) -> list[tuple[int, ...]]:
    """Rows on the cover whose two projections land in allowed side sets."""
    rows = []
    for values in itertools.product(*domains):
        if (
            project_orbit_values(left_matrix, values) in left_allowed
            and project_orbit_values(right_matrix, values) in right_allowed
        ):
            rows.append(values)
    return rows


def projection_gluing_check(
    cover: MarginalOrbitAlgebra,
    left_tp: int,
    right_tp: int,
    cap: int,
    limit: int,
) -> dict:
    """Exact gluing check for two quotient marginal solution sets.

    The quotient side sets are exact: a row is allowed only if it participates
    in at least one boxed/parity-valid solution of that quotient marginal.
    The cover rows are then filtered by the two quotient projections and joined
    against the cover marginal equations.
    """
    if math.lcm(left_tp, right_tp) != cover.tp:
        print(
            "warning: cover t' is not lcm(left,right): "
            f"cover={cover.tp} lcm={math.lcm(left_tp, right_tp)}"
        )
    left = build_algebra(cover.q, left_tp)
    right = build_algebra(cover.q, right_tp)
    print(
        "projection gluing check: "
        f"cover t'={cover.tp} quotients={left_tp},{right_tp} cap={cap:,}"
    )

    left_sets = exact_side_solution_sets(left, cap)
    right_sets = exact_side_solution_sets(right, cap)
    if left_sets is None or right_sets is None:
        print("  gluing result: REFUSED (quotient side enumeration exceeds cap)")
        return {"status": "REFUSED", "mechanism": "quotient_cap"}
    left_a, left_b, left_meta = left_sets
    right_a, right_b, right_meta = right_sets
    print(
        f"  quotient {left_tp}: side solutions "
        f"A={len(left_a)} B={len(left_b)} "
        f"(assignments A={left_meta['total_a']:,}/B={left_meta['total_b']:,})"
    )
    print(
        f"  quotient {right_tp}: side solutions "
        f"A={len(right_a)} B={len(right_b)} "
        f"(assignments A={right_meta['total_a']:,}/B={right_meta['total_b']:,})"
    )

    total_a = math.prod(len(dom) for dom in cover.a_domains)
    total_b = math.prod(len(dom) for dom in cover.b_domains)
    if total_a > cap or total_b > cap:
        print("  gluing result: REFUSED (cover side enumeration exceeds cap)")
        return {"status": "REFUSED", "mechanism": "cover_cap"}

    left_matrix = projection_matrix(cover, left)
    right_matrix = projection_matrix(cover, right)
    cover_a = projection_compatible_rows(
        cover, cover.a_domains, left_matrix, left_a, right_matrix, right_a
    )
    cover_b = projection_compatible_rows(
        cover, cover.b_domains, left_matrix, left_b, right_matrix, right_b
    )
    print(
        "  cover rows projecting to quotient side solutions: "
        f"A={len(cover_a)} B={len(cover_b)} "
        f"(assignments A={total_a:,}/B={total_b:,})"
    )

    if cover_a:
        for values in cover_a[:limit]:
            print(
                f"  A cover row={values} "
                f"left={project_orbit_values(left_matrix, values)} "
                f"right={project_orbit_values(right_matrix, values)}"
            )
    if cover_b:
        for values in cover_b[:limit]:
            print(
                f"  B cover row={values} "
                f"left={project_orbit_values(left_matrix, values)} "
                f"right={project_orbit_values(right_matrix, values)}"
            )

    if not cover_a or not cover_b:
        print("  gluing result: UNSAT (linear_projection_unsat)")
        return {
            "status": "UNSAT",
            "mechanism": "linear_projection_unsat",
            "cover_a": len(cover_a),
            "cover_b": len(cover_b),
        }

    target = [0] * vector_dimension(cover)
    target[cover.zero_orbit] = cover.q
    target[-1] = cover.q
    a_vectors: dict[tuple[int, ...], tuple[int, ...]] = {}
    for values in cover_a:
        a_vectors[side_vector(cover, values)] = values
    witnesses = []
    for values in cover_b:
        b_vec = side_vector(cover, values)
        need = tuple(target[i] - b_vec[i] for i in range(len(target)))
        a_values = a_vectors.get(need)
        if a_values is not None:
            witnesses.append((a_values, values))
            if len(witnesses) >= limit:
                break

    if witnesses:
        print(
            f"  gluing result: SAT ({len(witnesses)} cover witness(es) shown)"
        )
        for avals, bvals in witnesses:
            print(f"  A={avals} B={bvals}")
        return {
            "status": "SAT",
            "mechanism": "cover_marginal_sat",
            "witnesses": witnesses,
        }
    print("  gluing result: UNSAT (cover_marginal_join_unsat)")
    return {
        "status": "UNSAT",
        "mechanism": "cover_marginal_join_unsat",
        "cover_a": len(cover_a),
        "cover_b": len(cover_b),
    }


def gaussian_representations(n: int) -> list[tuple[int, int]]:
    """All signed ordered integer pairs (x,y) with x^2+y^2=n."""
    reps: list[tuple[int, int]] = []
    limit = math.isqrt(n)
    for x in range(-limit, limit + 1):
        y2 = n - x * x
        if y2 < 0:
            continue
        y = math.isqrt(y2)
        if y * y == y2:
            if y == 0:
                reps.append((x, 0))
            else:
                reps.append((x, y))
                reps.append((x, -y))
    return sorted(set(reps))


def inverse_u27_components(values: tuple[int, int, int, int]) -> tuple[int, int, int, int] | None:
    """Invert the full-unit C_27 rational component transform.

    The components are ordered by conductors 1, 3, 9, 27.  For orbit values
    (x0, x1, x2, x3) on the orbits {0}, units, 3*units, and 9*units:

        l1  = x0 + 18*x1 + 6*x2 + 2*x3
        l3  = x0 -  9*x1 + 6*x2 + 2*x3
        l9  = x0          - 3*x2 + 2*x3
        l27 = x0                  -   x3.

    This inverse is integral exactly when the conductor components glue back to
    integer orbit values.
    """
    l1, l3, l9, l27 = values
    numerators = (
        l1 + 2 * l3 + 6 * l9 + 18 * l27,
        l1 - l3,
        l1 + 2 * l3 - 3 * l9,
        l1 + 2 * l3 + 6 * l9 - 9 * l27,
    )
    if any(value % 27 for value in numerators):
        return None
    return tuple(value // 27 for value in numerators)


def u27_component_check(alg: MarginalOrbitAlgebra, limit: int) -> None:
    """Exact C_27 full-unit marginal check by rational Gaussian components."""
    if alg.tp != 27 or alg.Vp != [v for v in range(1, 27) if math.gcd(v, 27) == 1]:
        raise SystemExit(
            "--u27-gaussian-check requires t'=27 and V'=(Z/27Z)^*"
        )
    reps = gaussian_representations(alg.q)
    print(f"C_27 full-unit Gaussian component check: representations={len(reps)}")
    shown = 0
    witnesses: list[tuple[tuple[int, ...], tuple[int, ...], tuple[tuple[int, int], ...]]] = []
    for component_reps in itertools.product(reps, repeat=4):
        avec = inverse_u27_components(tuple(pair[0] for pair in component_reps))
        if avec is None:
            continue
        bvec = inverse_u27_components(tuple(pair[1] for pair in component_reps))
        if bvec is None:
            continue
        if all(value in domain for value, domain in zip(avec, alg.a_domains)) and all(
            value in domain for value, domain in zip(bvec, alg.b_domains)
        ):
            witnesses.append((avec, bvec, component_reps))
            if shown < limit:
                print(f"  A={avec} B={bvec} components={component_reps}")
                shown += 1
    if witnesses:
        print(f"  component result: SAT ({len(witnesses)} witness(es))")
    else:
        print("  component result: UNSAT")


def gaussian_congruent(left: tuple[int, int], right: tuple[int, int],
                       modulus: int) -> bool:
    """Congruence in Z[i] modulo an integer modulus."""
    return (
        (left[0] - right[0]) % modulus == 0
        and (left[1] - right[1]) % modulus == 0
    )


def gaussian_eo(value: tuple[int, int]) -> bool:
    """Even real part, odd imaginary part."""
    return value[0] % 2 == 0 and value[1] % 2 != 0


def gaussian_oe(value: tuple[int, int]) -> bool:
    """Odd real part, even imaginary part."""
    return value[0] % 2 != 0 and value[1] % 2 == 0


def gaussian_residue(value: tuple[int, int], modulus: int) -> tuple[int, int]:
    return (value[0] % modulus, value[1] % modulus)


def u27_full_unit(alg: MarginalOrbitAlgebra) -> bool:
    return (
        alg.tp == 27
        and alg.Vp == [v for v in range(1, 27) if math.gcd(v, 27) == 1]
    )


def u27_nested_congruence_check(alg: MarginalOrbitAlgebra, limit: int) -> None:
    """Exact C_27 check by oriented nested congruences in Z[i]."""
    if not u27_full_unit(alg):
        raise SystemExit(
            "--u27-nested-check requires t'=27 and V'=(Z/27Z)^*"
        )

    reps = gaussian_representations(alg.q)
    eo_residues = {gaussian_residue(z, 27) for z in reps if gaussian_eo(z)}
    oe_residues = {gaussian_residue(z, 27) for z in reps if gaussian_oe(z)}
    residue_join = sorted(eo_residues & oe_residues)
    nested = 0
    oriented = 0
    boxed = 0
    first_nested = None
    first_oriented = None
    boxed_witnesses = []

    for z1 in reps:
        for z3 in reps:
            if not gaussian_congruent(z1, z3, 27):
                continue
            for z9 in reps:
                if not gaussian_congruent(z1, z9, 9):
                    continue
                for z27 in reps:
                    if not gaussian_congruent(z1, z27, 3):
                        continue
                    components = (z1, z3, z9, z27)
                    avec = inverse_u27_components(tuple(z[0] for z in components))
                    bvec = inverse_u27_components(tuple(z[1] for z in components))
                    if avec is None or bvec is None:
                        raise AssertionError(
                            "nested congruence failed to give integral inverse"
                        )
                    nested += 1
                    if first_nested is None:
                        first_nested = (avec, bvec, components)
                    if not (gaussian_eo(z1) and all(gaussian_oe(z) for z in (z3, z9, z27))):
                        continue
                    oriented += 1
                    if first_oriented is None:
                        first_oriented = (avec, bvec, components)
                    in_a = all(value in domain for value, domain in zip(avec, alg.a_domains))
                    in_b = all(value in domain for value, domain in zip(bvec, alg.b_domains))
                    if in_a and in_b:
                        boxed += 1
                        if len(boxed_witnesses) < limit:
                            boxed_witnesses.append((avec, bvec, components))

    print(f"C_27 nested congruence check: representations={len(reps)}")
    print(
        f"  residue pair join mod 27: {'SAT' if residue_join else 'UNSAT'} "
        f"({len(residue_join)} residue(s))"
    )
    if residue_join:
        print(f"    first residue={residue_join[0]}")
    print(f"  nested congruence join: {'SAT' if nested else 'UNSAT'} ({nested} tuple(s))")
    if first_nested is not None:
        avec, bvec, components = first_nested
        print(f"    first nested A={avec} B={bvec} components={components}")
    print(f"  oriented join: {'SAT' if oriented else 'UNSAT'} ({oriented} tuple(s))")
    if first_oriented is not None:
        avec, bvec, components = first_oriented
        print(f"    first oriented A={avec} B={bvec} components={components}")
    print(f"  boxed marginal: {'SAT' if boxed else 'UNSAT'} ({boxed} witness(es))")
    for avec, bvec, components in boxed_witnesses:
        print(f"    boxed A={avec} B={bvec} components={components}")


def inverse_u49_components(values: tuple[int, int, int]) -> tuple[int, int, int] | None:
    """Invert the full-unit C_49 rational component transform.

    The components are ordered by conductors 1, 7, 49.  For orbit values
    (x0, x1, x2) on the orbits {0}, units, and 7*units:

        l1  = x0 + 42*x1 + 6*x2
        l7  = x0 -  7*x1 + 6*x2
        l49 = x0          -   x2.

    This inverse is integral exactly when the conductor components glue back
    to integer orbit values, i.e. when l1 == l7 (mod 49) and
    l1 == l49 (mod 7).
    """
    l1, l7, l49 = values
    numerators = (
        l1 + 6 * l7 + 42 * l49,
        l1 - l7,
        l1 + 6 * l7 - 7 * l49,
    )
    if any(value % 49 for value in numerators):
        return None
    return tuple(value // 49 for value in numerators)


def u49_full_unit(alg: MarginalOrbitAlgebra) -> bool:
    return (
        alg.tp == 49
        and alg.Vp == [v for v in range(1, 49) if math.gcd(v, 49) == 1]
    )


def c49_boxed_join_exists(q: int, h: int, reps: list[tuple[int, int]]) -> bool:
    """Small-h exact boxed C_49 nested join check.

    Orbit order (origin, units, 7*units); A-side origin even with
    |x0| <= h-1, all other coordinates odd with magnitude <= h.
    """
    for z1 in reps:
        if not gaussian_eo(z1):
            continue
        for z7 in reps:
            if not gaussian_oe(z7) or gaussian_residue(z1, 49) != gaussian_residue(z7, 49):
                continue
            for z49 in reps:
                if not gaussian_oe(z49) or gaussian_residue(z1, 7) != gaussian_residue(z49, 7):
                    continue
                avec = inverse_u49_components((z1[0], z7[0], z49[0]))
                bvec = inverse_u49_components((z1[1], z7[1], z49[1]))
                if avec is None or bvec is None:
                    raise AssertionError("nested congruence did not invert integrally")
                if (
                    avec[0] % 2 == 0
                    and abs(avec[0]) <= h - 1
                    and all(value % 2 and abs(value) <= h for value in avec[1:])
                    and all(value % 2 and abs(value) <= h for value in bvec)
                ):
                    return True
    return False


def u49_nested_congruence_check(alg: MarginalOrbitAlgebra, limit: int) -> None:
    """Exact C_49 check by oriented nested congruences in Z[i].

    Mirrors the C_27 nested criterion at t'=49: three rational conductor
    components (1, 7, 49), the congruences z1 == z7 (mod 49) and
    z1 == z49 (mod 7), the orientation z1 in G_eo(q), z7, z49 in G_oe(q),
    and the fiber boxes.  Cross-checked against the exact orbit-value MITM
    when that is affordable.
    """
    if not u49_full_unit(alg):
        raise SystemExit(
            "--u49-nested-check requires t'=49 and V'=(Z/49Z)^*"
        )

    reps = gaussian_representations(alg.q)
    eo_residues = {gaussian_residue(z, 49) for z in reps if gaussian_eo(z)}
    oe_residues = {gaussian_residue(z, 49) for z in reps if gaussian_oe(z)}
    residue_join = sorted(eo_residues & oe_residues)
    nested = 0
    oriented = 0
    boxed = 0
    first_nested = None
    first_oriented = None
    boxed_witnesses = []

    for z1 in reps:
        for z7 in reps:
            if not gaussian_congruent(z1, z7, 49):
                continue
            for z49 in reps:
                if not gaussian_congruent(z1, z49, 7):
                    continue
                components = (z1, z7, z49)
                avec = inverse_u49_components(tuple(z[0] for z in components))
                bvec = inverse_u49_components(tuple(z[1] for z in components))
                if avec is None or bvec is None:
                    raise AssertionError(
                        "nested congruence failed to give integral inverse"
                    )
                nested += 1
                if first_nested is None:
                    first_nested = (avec, bvec, components)
                if not (gaussian_eo(z1) and all(gaussian_oe(z) for z in (z7, z49))):
                    continue
                oriented += 1
                if first_oriented is None:
                    first_oriented = (avec, bvec, components)
                in_a = all(value in domain for value, domain in zip(avec, alg.a_domains))
                in_b = all(value in domain for value, domain in zip(bvec, alg.b_domains))
                if in_a and in_b:
                    boxed += 1
                    if len(boxed_witnesses) < limit:
                        boxed_witnesses.append((avec, bvec, components))

    print(f"C_49 nested congruence check: representations={len(reps)}")
    print(
        f"  residue pair join mod 49: {'SAT' if residue_join else 'UNSAT'} "
        f"({len(residue_join)} residue(s))"
    )
    if residue_join:
        print(f"    first residue={residue_join[0]}")
    print(f"  nested congruence join: {'SAT' if nested else 'UNSAT'} ({nested} tuple(s))")
    if first_nested is not None:
        avec, bvec, components = first_nested
        print(f"    first nested A={avec} B={bvec} components={components}")
    print(f"  oriented join: {'SAT' if oriented else 'UNSAT'} ({oriented} tuple(s))")
    if first_oriented is not None:
        avec, bvec, components = first_oriented
        print(f"    first oriented A={avec} B={bvec} components={components}")
    print(f"  boxed marginal: {'SAT' if boxed else 'UNSAT'} ({boxed} witness(es))")
    for avec, bvec, components in boxed_witnesses:
        print(f"    boxed A={avec} B={bvec} components={components}")

    mitm = exact_integer_mitm(alg, 3_000_000)
    if mitm is None:
        print("  MITM cross-check: refused (assignment cap)")
    elif bool(mitm) == bool(boxed):
        print(f"  MITM cross-check: OK (both {'SAT' if mitm else 'UNSAT'})")
    else:
        raise AssertionError(
            f"C_49 nested check ({'SAT' if boxed else 'UNSAT'}) disagrees "
            f"with exact MITM ({'SAT' if mitm else 'UNSAT'})"
        )


def inverse_p3_components(values: tuple[int, int, int]) -> tuple[int, int, int] | None:
    """Invert the p=3 character-component transform.

    For the three C_9 orbit values (x0, xu, xp), the rational character
    evaluations are

        r1 = x0 + 6*xu + 2*xp,   r3 = x0 - 3*xu + 2*xp,
        r9 = x0 - xp.

    Return (x0,xu,xp) when the inverse is integral.
    """
    r1, r3, r9 = values
    nums = (
        r1 + 2 * r3 + 6 * r9,
        r1 - r3,
        r1 + 2 * r3 - 3 * r9,
    )
    if any(num % 9 for num in nums):
        return None
    return (nums[0] // 9, nums[1] // 9, nums[2] // 9)


def p3_gaussian_component_check(
    alg: MarginalOrbitAlgebra,
    limit: int,
) -> list[tuple[tuple[int, int, int], tuple[int, int, int],
                tuple[tuple[int, int], tuple[int, int], tuple[int, int]]]]:
    """Exact p=3 prime-square lift check via Q[C_9]^V decomposition.

    When t'=9 and V'=(Z/9)^*, the fixed algebra has three rational character
    components, with evaluations at conductors 1, 3, and 9.  The marginal
    equation is equivalent to choosing three Gaussian representations of q whose
    component values invert to valid A and B orbit values.
    """
    if alg.tp != 9 or sorted(alg.sizes) != [1, 2, 6]:
        raise SystemExit("--p3-gaussian-check requires the C_9 full-unit orbit algebra")

    reps = gaussian_representations(alg.q)
    print(f"p=3 Gaussian component check: representations={len(reps)}")
    out = []
    domains_a = [set(dom) for dom in alg.a_domains]
    domains_b = [set(dom) for dom in alg.b_domains]
    for component_reps in itertools.product(reps, repeat=3):
        avec = inverse_p3_components(tuple(pair[0] for pair in component_reps))
        if avec is None:
            continue
        bvec = inverse_p3_components(tuple(pair[1] for pair in component_reps))
        if bvec is None:
            continue
        if all(avec[i] in domains_a[i] for i in range(3)) and all(
            bvec[i] in domains_b[i] for i in range(3)
        ):
            out.append((avec, bvec, component_reps))
            if len(out) >= limit:
                break
    if out:
        print(f"  component result: SAT ({len(out)} witness(es) shown)")
        for avec, bvec, reps_used in out:
            print(f"  A={avec} B={bvec} components={reps_used}")
    else:
        print("  component result: UNSAT")
    return out


def sqrt5_representations(
    q: int,
) -> list[tuple[tuple[int, int], tuple[int, int]]]:
    """Pairs alpha,beta in Z[u], u^2+u-1=0, with alpha^2+beta^2=q.

    Each element is represented as (a,b) for a+b*u.  The coefficient equations
    are

        a^2+c^2+b^2+d^2 = q,
        2ab+2cd-b^2-d^2 = 0.
    """
    limit = math.isqrt(q)
    two_square_cache: dict[int, list[tuple[int, int]]] = {}
    out: list[tuple[tuple[int, int], tuple[int, int]]] = []
    for b in range(-limit, limit + 1):
        for d in range(-limit, limit + 1):
            remaining = q - b * b - d * d
            if remaining < 0:
                continue
            if remaining not in two_square_cache:
                two_square_cache[remaining] = gaussian_representations(remaining)
            target = b * b + d * d
            for a, c in two_square_cache[remaining]:
                if 2 * a * b + 2 * c * d == target:
                    out.append(((a, b), (c, d)))
    return sorted(set(out))


def inverse_p5_components(
    L: int,
    comp5: tuple[int, int],
    comp25: tuple[int, int],
) -> tuple[int, int, int, int, int] | None:
    """Invert the p=5 component transform to orbit values.

    Orbit order is (0, U1, U2, P1, P2), with U1 congruent to +-1 modulo 5,
    U2 congruent to +-2 modulo 5, P1={+-5}, and P2={+-10}.
    """
    A, B = comp5
    C, D = comp25
    if B % 5:
        return None
    if (A - C - 2 * D) % 5:
        return None
    delta_unit = B // 5
    delta_p = (A - C - 2 * D) // 5
    num_x4 = L - C - 2 * D + 20 * delta_p - 2 * B
    if num_x4 % 25:
        return None
    x4 = num_x4 // 25
    x3 = D + x4
    x0 = C + x4
    x2 = x4 - delta_p
    x1 = x2 + delta_unit
    return (x0, x1, x2, x3, x4)


def p5_sqrt5_component_check(
    alg: MarginalOrbitAlgebra,
    limit: int,
) -> list[tuple[
    tuple[int, int, int, int, int],
    tuple[int, int, int, int, int],
    tuple[tuple[int, int],
          tuple[tuple[int, int], tuple[int, int]],
          tuple[tuple[int, int], tuple[int, int]]],
]]:
    """Exact p=5 prime-square lift check by component compatibility."""
    expected_reps = [0, 1, 2, 5, 10]
    if alg.tp != 25 or alg.reps != expected_reps:
        raise SystemExit(
            "--p5-sqrt5-check requires the C_25 prime-square lift orbit algebra"
        )

    reps_z = gaussian_representations(alg.q)
    reps_k = sqrt5_representations(alg.q)
    print(
        "p=5 sqrt5 component check: "
        f"integer representations={len(reps_z)} sqrt5 representations={len(reps_k)}"
    )
    domains_a = [set(dom) for dom in alg.a_domains]
    domains_b = [set(dom) for dom in alg.b_domains]
    out = []
    for z_rep in reps_z:
        L_a, L_b = z_rep
        for rep5 in reps_k:
            comp5_a, comp5_b = rep5
            for rep25 in reps_k:
                comp25_a, comp25_b = rep25
                avec = inverse_p5_components(L_a, comp5_a, comp25_a)
                if avec is None:
                    continue
                bvec = inverse_p5_components(L_b, comp5_b, comp25_b)
                if bvec is None:
                    continue
                if all(avec[i] in domains_a[i] for i in range(5)) and all(
                    bvec[i] in domains_b[i] for i in range(5)
                ):
                    out.append((avec, bvec, (z_rep, rep5, rep25)))
                    if len(out) >= limit:
                        print(f"  component result: SAT ({len(out)} witness(es) shown)")
                        for avec0, bvec0, reps_used in out:
                            print(f"  A={avec0} B={bvec0} components={reps_used}")
                        return out
    if out:
        print(f"  component result: SAT ({len(out)} witness(es) shown)")
        for avec, bvec, reps_used in out:
            print(f"  A={avec} B={bvec} components={reps_used}")
    else:
        print("  component result: UNSAT")
    return out


def cubic7_roots() -> np.ndarray:
    """Real embeddings of u, where u^3+u^2-2u-1=0."""
    return np.sort(np.roots([1, 1, -2, -1]).real)


def cubic7_mul(
    left: tuple[int, int, int],
    right: tuple[int, int, int],
) -> tuple[int, int, int]:
    """Multiply in Z[u], u^3=-u^2+2u+1."""
    a, b, c = left
    d, e, f = right
    cross = b * f + c * e
    high = c * f
    return (
        a * d + cross - high,
        a * e + b * d + 2 * cross - high,
        a * f + b * e + c * d - cross + 3 * high,
    )


def cubic7_square(value: tuple[int, int, int]) -> tuple[int, int, int]:
    return cubic7_mul(value, value)


def cubic7_box(q: int) -> list[tuple[int, int, int]]:
    """All a+b*u+c*u^2 with every real embedding bounded by sqrt(q).

    Any alpha in a solution alpha^2+beta^2=q has this embedding bound at
    every real place.  The floating arithmetic only makes a complete
    coefficient box; the square join below is exact integer arithmetic.
    """
    roots = cubic7_roots()
    emb = np.vstack([np.ones(3), roots, roots * roots]).T
    winv = np.linalg.inv(emb)
    bound = math.sqrt(q) + 1e-6
    caps = [
        int(math.floor(sum(abs(winv[k, r]) for r in range(3)) * bound)) + 2
        for k in range(3)
    ]
    rows: list[tuple[int, int, int]] = []
    for a in range(-caps[0], caps[0] + 1):
        for b in range(-caps[1], caps[1] + 1):
            base = a + b * roots
            for c in range(-caps[2], caps[2] + 1):
                values = base + c * roots * roots
                if np.max(np.abs(values)) <= bound:
                    rows.append((a, b, c))
    return rows


def cubic7_representations(
    q: int,
) -> list[tuple[tuple[int, int, int], tuple[int, int, int]]]:
    """Pairs alpha,beta in Z[u], u^3+u^2-2u-1=0, with alpha^2+beta^2=q."""
    box = cubic7_box(q)
    by_square: dict[tuple[int, int, int], list[tuple[int, int, int]]] = {}
    for value in box:
        by_square.setdefault(cubic7_square(value), []).append(value)
    out: list[tuple[tuple[int, int, int], tuple[int, int, int]]] = []
    for alpha in box:
        sq = cubic7_square(alpha)
        need = (q - sq[0], -sq[1], -sq[2])
        for beta in by_square.get(need, []):
            out.append((alpha, beta))
    return sorted(set(out))


def inverse_p7_components(
    L: int,
    comp7: tuple[int, int, int],
    comp49: tuple[int, int, int],
) -> tuple[int, int, int, int, int, int, int] | None:
    """Invert the p=7 prime-square component transform to orbit values.

    The orbit order is (0,U1,U2,U3,P1,P2,P3), where Ui is congruent to
    +-i modulo 7 and Pi={+-7i}.  Components use the basis 1,u,u^2 with
    u=zeta_7+zeta_7^{-1}.
    """
    A, B, C = comp7
    D, E, F = comp49
    if B % 7 or C % 7:
        return None
    delta_u1 = B // 7
    delta_u2 = C // 7
    base = D + 2 * E + 4 * F
    r_num = A - base + 2 * C
    s_num = L - base - 2 * B - 2 * C
    if r_num % 7 or s_num % 7:
        return None
    r_val = r_num // 7
    s_val = s_num // 7
    if (s_val - r_val) % 7:
        return None
    u3 = (s_val - r_val) // 7
    p3 = r_val + u3
    p1 = E + p3
    p2 = F + p3
    x0 = D + 2 * F + p3
    u1 = u3 + delta_u1
    u2 = u3 + delta_u2
    return (x0, u1, u2, u3, p1, p2, p3)


def p7_forward(
    values: tuple[int, int, int, int, int, int, int],
) -> tuple[int, tuple[int, int, int], tuple[int, int, int]]:
    """Forward p=7 component transform in build_algebra orbit order."""
    x0, u1, u2, u3, p1, p2, p3 = values
    p_sum = p1 + p2 + p3
    return (
        x0 + 14 * (u1 + u2 + u3) + 2 * p_sum,
        (
            x0 + 2 * p_sum + 7 * (-2 * u2 + u3),
            7 * (u1 - u3),
            7 * (u2 - u3),
        ),
        (x0 - 2 * p2 + p3, p1 - p3, p2 - p3),
    )


def p7_selftest(alg: MarginalOrbitAlgebra) -> None:
    """Round-trip validation for the p=7 component transform."""
    import random

    rng = random.Random(7)
    for trial in range(200):
        source = alg.a_domains if trial < 100 else alg.b_domains
        values = tuple(rng.choice(dom) for dom in source)
        L, comp7, comp49 = p7_forward(values)
        back = inverse_p7_components(L, comp7, comp49)
        assert back == values, f"p=7 round-trip failed at trial {trial}"


def p7_side_candidates(
    domains: list[list[int]],
    reps_z: list[tuple[int, int]],
    reps_k: list[tuple[tuple[int, int, int], tuple[int, int, int]]],
) -> dict[tuple[int, tuple[int, int, int], tuple[int, int, int]], tuple[int, ...]]:
    domain_sets = [set(dom) for dom in domains]
    z_halves = sorted({x for x, _y in reps_z})
    k_halves = sorted({alpha for alpha, _beta in reps_k})
    out: dict[
        tuple[int, tuple[int, int, int], tuple[int, int, int]],
        tuple[int, ...],
    ] = {}
    for L in z_halves:
        for comp7 in k_halves:
            for comp49 in k_halves:
                values = inverse_p7_components(L, comp7, comp49)
                if values is None:
                    continue
                if all(values[i] in domain_sets[i] for i in range(7)):
                    out[(L, comp7, comp49)] = values
    return out


def p7_cubic_component_check(
    alg: MarginalOrbitAlgebra,
    limit: int,
) -> list[tuple[tuple[int, ...], tuple[int, ...]]]:
    """Exact p=7 prime-square lift check by cubic component compatibility."""
    expected_reps = [0, 1, 2, 3, 7, 14, 21]
    if alg.tp != 49 or alg.reps != expected_reps:
        raise SystemExit(
            "--p7-cubic-check requires the C_49 prime-square lift orbit algebra"
        )
    p7_selftest(alg)

    reps_z = gaussian_representations(alg.q)
    reps_k = cubic7_representations(alg.q)
    print(
        "p=7 cubic component check: "
        f"integer representations={len(reps_z)} "
        f"cubic representations={len(reps_k)}"
    )
    if not reps_z or not reps_k:
        print("  component result: UNSAT")
        return []

    side_a = p7_side_candidates(alg.a_domains, reps_z, reps_k)
    side_b = p7_side_candidates(alg.b_domains, reps_z, reps_k)
    print(f"  A valid side vectors={len(side_a)}")
    print(f"  B valid side vectors={len(side_b)}")
    if not side_a or not side_b:
        print("  component result: UNSAT (no side vector)")
        return []

    z_mates: dict[int, list[int]] = {}
    for x, y in reps_z:
        z_mates.setdefault(x, []).append(y)
    k_mates: dict[tuple[int, int, int], list[tuple[int, int, int]]] = {}
    for alpha, beta in reps_k:
        k_mates.setdefault(alpha, []).append(beta)

    target = [0] * vector_dimension(alg)
    target[alg.zero_orbit] = alg.q
    target[-1] = alg.q
    witnesses: list[tuple[tuple[int, ...], tuple[int, ...]]] = []
    for L, comp7, comp49 in side_a:
        for M in z_mates[L]:
            for comp7_b in k_mates.get(comp7, []):
                for comp49_b in k_mates.get(comp49, []):
                    bvals = side_b.get((M, comp7_b, comp49_b))
                    if bvals is None:
                        continue
                    avals = side_a[(L, comp7, comp49)]
                    vec_a = side_vector(alg, avals)
                    vec_b = side_vector(alg, bvals)
                    assert all(
                        va + vb == tv
                        for va, vb, tv in zip(vec_a, vec_b, target)
                    ), "witness failed exact marginal verification"
                    witnesses.append((avals, bvals))
                    if len(witnesses) >= limit:
                        print(
                            f"  component result: SAT ({len(witnesses)} "
                            "verified witness(es) shown)"
                        )
                        for w_a, w_b in witnesses:
                            print(f"  A={w_a} B={w_b}")
                        return witnesses
    if witnesses:
        print(
            f"  component result: SAT ({len(witnesses)} verified witness(es) shown)"
        )
        for w_a, w_b in witnesses:
            print(f"  A={w_a} B={w_b}")
    else:
        print("  component result: UNSAT")
    return witnesses


def sqrt21_representations(
    q: int,
) -> list[tuple[tuple[int, int], tuple[int, int]]]:
    """Pairs alpha,beta in Z[eta], eta^2=eta+5, with alpha^2+beta^2=q.

    Each element is represented as (a,b) for a+b*eta, where
    eta=(1+sqrt(21))/2.  The coefficient equations are

        a^2+c^2+5*b^2+5*d^2 = q,
        2ab+2cd+b^2+d^2 = 0.
    """
    limit = math.isqrt(q)
    b_limit = math.isqrt(q // 5)
    two_square_cache: dict[int, list[tuple[int, int]]] = {}
    out: list[tuple[tuple[int, int], tuple[int, int]]] = []
    for b in range(-b_limit, b_limit + 1):
        for d in range(-b_limit, b_limit + 1):
            remaining = q - 5 * b * b - 5 * d * d
            if remaining < 0:
                continue
            if remaining not in two_square_cache:
                two_square_cache[remaining] = gaussian_representations(remaining)
            for a, c in two_square_cache[remaining]:
                if 2 * a * b + 2 * c * d + b * b + d * d == 0:
                    assert abs(a) <= limit and abs(c) <= limit
                    out.append(((a, b), (c, d)))
    return sorted(set(out))


def inverse_c21_components(
    L1: int,
    L3: int,
    L7: int,
    comp21: tuple[int, int],
) -> tuple[int, int, int, int, int] | None:
    """Invert the C_21 component transform to orbit values.

    Orbit order is (0, H, U\\H, 3*(Z/7Z)^*, {7,14}), where
    H={1,4,5,16,17,20}.  The conductor-21 component is A+B*eta with
    eta^2=eta+5.
    """
    A, B = comp21
    nums = (
        L1 + 2 * L3 + 6 * L7 + 12 * A + 6 * B,
        L1 - L3 - L7 + A + 11 * B,
        L1 - L3 - L7 + A - 10 * B,
        L1 + 2 * L3 - L7 - 2 * A - B,
        L1 - L3 + 6 * L7 - 6 * A - 3 * B,
    )
    if any(num % 21 for num in nums):
        return None
    return tuple(num // 21 for num in nums)


def c21_forward(values: tuple[int, ...]) -> tuple[int, int, int, tuple[int, int]]:
    """Forward C_21 component transform in the orbit order used by build_algebra."""
    x0, x1, x2, x3, x4 = values
    return (
        x0 + 6 * x1 + 6 * x2 + 6 * x3 + 2 * x4,
        x0 - 3 * x1 - 3 * x2 + 6 * x3 - x4,
        x0 - x1 - x2 - x3 + 2 * x4,
        (x0 + x2 - x3 - x4, x1 - x2),
    )


def c21_selftest(alg: MarginalOrbitAlgebra) -> None:
    """Round-trip validation for the C_21 component transform."""
    import random

    rng = random.Random(21)
    for trial in range(200):
        source = alg.a_domains if trial < 100 else alg.b_domains
        values = tuple(rng.choice(dom) for dom in source)
        L1, L3, L7, comp21 = c21_forward(values)
        back = inverse_c21_components(L1, L3, L7, comp21)
        assert back == values, f"C_21 round-trip failed at trial {trial}"


def c21_sqrt21_check(
    alg: MarginalOrbitAlgebra,
    limit: int,
) -> list[tuple[tuple[int, int, int, int, int],
                tuple[int, int, int, int, int]]]:
    """Exact C_21 marginal decision by three rational and one sqrt(21) component."""
    expected_vp = [1, 4, 5, 16, 17, 20]
    expected_reps = [0, 1, 2, 3, 7]
    if alg.tp != 21 or alg.Vp != expected_vp or alg.reps != expected_reps:
        raise SystemExit(
            "--c21-sqrt21-check requires t'=21 with V'={1,4,5,16,17,20}"
        )
    c21_selftest(alg)

    reps_z = gaussian_representations(alg.q)
    z_mates: dict[int, list[int]] = {}
    for x, y in reps_z:
        z_mates.setdefault(x, []).append(y)

    reps_k = sqrt21_representations(alg.q)
    k_mates: dict[tuple[int, int], list[tuple[int, int]]] = {}
    for alpha, beta in reps_k:
        k_mates.setdefault(alpha, []).append(beta)

    print(
        "C_21 sqrt21 component check: "
        f"integer representations={len(reps_z)} "
        f"sqrt21 ordered pairs={len(reps_k)} "
        f"sqrt21 halves={len(k_mates)}"
    )

    def side_candidates(
        domains: list[list[int]],
        label: str,
    ) -> dict[tuple[int, int, int, tuple[int, int]], tuple[int, ...]]:
        domain_sets = [set(dom) for dom in domains]
        out: dict[tuple[int, int, int, tuple[int, int]], tuple[int, ...]] = {}
        keys_z = sorted(z_mates)
        for L1, L3, L7 in itertools.product(keys_z, repeat=3):
            for comp21 in sorted(k_mates):
                values = inverse_c21_components(L1, L3, L7, comp21)
                if values is None:
                    continue
                if all(values[i] in domain_sets[i] for i in range(5)):
                    out[(L1, L3, L7, comp21)] = values
        print(f"  {label} valid side vectors={len(out)}")
        return out

    side_a = side_candidates(alg.a_domains, "A")
    side_b = side_candidates(alg.b_domains, "B")

    target = [0] * vector_dimension(alg)
    target[alg.zero_orbit] = alg.q
    target[-1] = alg.q

    witnesses: list[tuple[tuple[int, int, int, int, int],
                          tuple[int, int, int, int, int]]] = []
    for (L1, L3, L7, alpha), avals in side_a.items():
        for M1 in z_mates[L1]:
            for M3 in z_mates[L3]:
                for M7 in z_mates[L7]:
                    for beta in k_mates.get(alpha, []):
                        bvals = side_b.get((M1, M3, M7, beta))
                        if bvals is None:
                            continue
                        vec_a = side_vector(alg, avals)
                        vec_b = side_vector(alg, bvals)
                        assert all(
                            va + vb == tv
                            for va, vb, tv in zip(vec_a, vec_b, target)
                        ), "witness failed exact marginal verification"
                        witnesses.append((avals, bvals))
                        if len(witnesses) >= limit:
                            print(
                                f"  component result: SAT ({len(witnesses)} "
                                "verified witness(es) shown)"
                            )
                            for w_a, w_b in witnesses:
                                print(f"  A={w_a} B={w_b}")
                            return witnesses
    if witnesses:
        print(
            f"  component result: SAT ({len(witnesses)} verified witness(es) shown)"
        )
        for w_a, w_b in witnesses:
            print(f"  A={w_a} B={w_b}")
    else:
        print("  component result: UNSAT")
    return witnesses


def sqrt57_representations(
    q: int,
) -> list[tuple[tuple[int, int], tuple[int, int]]]:
    """Pairs alpha,beta in Z[eta], eta^2=eta+14, with alpha^2+beta^2=q.

    Each element is represented as (a,b) for a+b*eta, where
    eta=(1+sqrt(57))/2.  The coefficient equations are

        a^2+c^2+14*b^2+14*d^2 = q,
        2ab+2cd+b^2+d^2 = 0.
    """
    limit = math.isqrt(q)
    b_limit = math.isqrt(q // 14)
    two_square_cache: dict[int, list[tuple[int, int]]] = {}
    out: list[tuple[tuple[int, int], tuple[int, int]]] = []
    for b in range(-b_limit, b_limit + 1):
        for d in range(-b_limit, b_limit + 1):
            remaining = q - 14 * b * b - 14 * d * d
            if remaining < 0:
                continue
            if remaining not in two_square_cache:
                two_square_cache[remaining] = gaussian_representations(remaining)
            for a, c in two_square_cache[remaining]:
                if 2 * a * b + 2 * c * d + b * b + d * d == 0:
                    assert abs(a) <= limit and abs(c) <= limit
                    out.append(((a, b), (c, d)))
    return sorted(set(out))


C57_EXPECTED_VP = [1, 2, 4, 7, 8, 14, 16, 25, 28, 29, 32, 41, 43, 49, 50, 53, 55, 56]


def inverse_c57_components(
    L1: int,
    L3: int,
    L19: int,
    comp57: tuple[int, int],
) -> tuple[int, int, int, int, int] | None:
    """Invert the C_57 component transform to orbit values.

    Orbit order is (0, H, 3*(Z/19Z)^*, gH, {19,38}), where
    H = ker(chi_3*chi_19) and g is any unit outside H.  The conductor-57
    component is A+B*eta with eta=(1+sqrt(57))/2, eta^2=eta+14.
    """
    A, B = comp57
    nums = (
        L1 + 2 * L3 + 18 * L19 + 36 * A + 18 * B,
        L1 - L3 - L19 + A + 29 * B,
        L1 + 2 * L3 - L19 - 2 * A - B,
        L1 - L3 - L19 + A - 28 * B,
        L1 - L3 + 18 * L19 - 18 * A - 9 * B,
    )
    if any(num % 57 for num in nums):
        return None
    return tuple(num // 57 for num in nums)


def c57_forward(values: tuple[int, ...]) -> tuple[int, int, int, tuple[int, int]]:
    """Forward C_57 component transform in the orbit order used by build_algebra."""
    x0, x1, x2, x3, x4 = values
    return (
        x0 + 18 * x1 + 18 * x2 + 18 * x3 + 2 * x4,
        x0 - 9 * x1 + 18 * x2 - 9 * x3 - x4,
        x0 - x1 - x2 - x3 + 2 * x4,
        (x0 - x2 + x3 - x4, x1 - x3),
    )


def c57_selftest(alg: MarginalOrbitAlgebra) -> None:
    """Round-trip validation for the C_57 component transform."""
    import random

    rng = random.Random(57)
    for trial in range(200):
        source = alg.a_domains if trial < 100 else alg.b_domains
        values = tuple(rng.choice(dom) for dom in source)
        L1, L3, L19, comp57 = c57_forward(values)
        back = inverse_c57_components(L1, L3, L19, comp57)
        assert back == values, f"C_57 round-trip failed at trial {trial}"


def c57_sqrt57_check(
    alg: MarginalOrbitAlgebra,
    limit: int,
) -> list[tuple[tuple[int, int, int, int, int],
                tuple[int, int, int, int, int]]]:
    """Exact C_57 marginal decision by three rational and one sqrt(57) component."""
    expected_reps = [0, 1, 3, 5, 19]
    if alg.tp != 57 or alg.Vp != C57_EXPECTED_VP or alg.reps != expected_reps:
        raise SystemExit(
            "--c57-check requires t'=57 with V'=ker(chi_3*chi_19)"
        )
    c57_selftest(alg)

    reps_z = gaussian_representations(alg.q)
    z_mates: dict[int, list[int]] = {}
    for x, y in reps_z:
        z_mates.setdefault(x, []).append(y)

    reps_k = sqrt57_representations(alg.q)
    k_mates: dict[tuple[int, int], list[tuple[int, int]]] = {}
    for alpha, beta in reps_k:
        k_mates.setdefault(alpha, []).append(beta)

    print(
        "C_57 sqrt57 component check: "
        f"integer representations={len(reps_z)} "
        f"sqrt57 ordered pairs={len(reps_k)} "
        f"sqrt57 halves={len(k_mates)}"
    )

    def side_candidates(
        domains: list[list[int]],
        label: str,
    ) -> dict[tuple[int, int, int, tuple[int, int]], tuple[int, ...]]:
        domain_sets = [set(dom) for dom in domains]
        out: dict[tuple[int, int, int, tuple[int, int]], tuple[int, ...]] = {}
        keys_z = sorted(z_mates)
        for L1, L3, L19 in itertools.product(keys_z, repeat=3):
            for comp57 in sorted(k_mates):
                values = inverse_c57_components(L1, L3, L19, comp57)
                if values is None:
                    continue
                if all(values[i] in domain_sets[i] for i in range(5)):
                    out[(L1, L3, L19, comp57)] = values
        print(f"  {label} valid side vectors={len(out)}")
        return out

    side_a = side_candidates(alg.a_domains, "A")
    side_b = side_candidates(alg.b_domains, "B")

    target = [0] * vector_dimension(alg)
    target[alg.zero_orbit] = alg.q
    target[-1] = alg.q

    witnesses: list[tuple[tuple[int, int, int, int, int],
                          tuple[int, int, int, int, int]]] = []
    for (L1, L3, L19, alpha), avals in side_a.items():
        for M1 in z_mates[L1]:
            for M3 in z_mates[L3]:
                for M19 in z_mates[L19]:
                    for beta in k_mates.get(alpha, []):
                        bvals = side_b.get((M1, M3, M19, beta))
                        if bvals is None:
                            continue
                        vec_a = side_vector(alg, avals)
                        vec_b = side_vector(alg, bvals)
                        assert all(
                            va + vb == tv
                            for va, vb, tv in zip(vec_a, vec_b, target)
                        ), "witness failed exact marginal verification"
                        witnesses.append((avals, bvals))
                        if len(witnesses) >= limit:
                            break
                    if len(witnesses) >= limit:
                        break
                if len(witnesses) >= limit:
                    break
            if len(witnesses) >= limit:
                break
        if len(witnesses) >= limit:
            break
    if witnesses:
        print(
            f"  component result: SAT ({len(witnesses)} verified witness(es) shown)"
        )
        for w_a, w_b in witnesses:
            print(f"  A={w_a} B={w_b}")
    else:
        print("  component result: UNSAT")

    mitm = exact_integer_mitm(alg, 3_000_000)
    if mitm is None:
        print("  MITM cross-check: refused (assignment cap)")
    elif bool(mitm) == bool(witnesses):
        print(f"  MITM cross-check: OK (both {'SAT' if mitm else 'UNSAT'})")
    else:
        raise AssertionError(
            f"C_57 component check ({'SAT' if witnesses else 'UNSAT'}) disagrees "
            f"with exact MITM ({'SAT' if mitm else 'UNSAT'})"
        )
    return witnesses


def period17_cosets() -> tuple[list[list[int]], dict[int, int]]:
    """Cosets of U=<4>={1,4,13,16} in (Z/17)^*, indexed by powers of 3.

    The quartic Gaussian periods eta_k = sum_{r in 3^k U} zeta_17^r form an
    integral basis of the real quartic subfield K of Q(zeta_17); the Galois
    group is cyclic and shifts the index k by one.
    """
    unit_group = sorted(pow(3, 4 * m, 17) for m in range(4))
    cosets: list[list[int]] = []
    index: dict[int, int] = {}
    for k in range(4):
        mult = pow(3, k, 17)
        coset = sorted(mult * u % 17 for u in unit_group)
        cosets.append(coset)
        for r in coset:
            index[r] = k
    return cosets, index


def period17_structure() -> tuple[list[list[int]], list[list[list[int]]]]:
    """Exact multiplication table eta_i*eta_j = const[i][j]*1 + sum_k T[i][j][k]*eta_k.

    Computed by convolution of coset indicators in Z[zeta_17]; the zeta^0
    coefficient is the constant term and the rest must be constant on cosets.
    """
    cosets, _ = period17_cosets()
    const = [[0] * 4 for _ in range(4)]
    tensor = [[[0] * 4 for _ in range(4)] for _ in range(4)]
    for i in range(4):
        for j in range(4):
            counts = [0] * 17
            for u in cosets[i]:
                for w in cosets[j]:
                    counts[(u + w) % 17] += 1
            const[i][j] = counts[0]
            for k in range(4):
                values = {counts[r] for r in cosets[k]}
                if len(values) != 1:
                    raise AssertionError("period product not coset-constant")
                tensor[i][j][k] = values.pop()
    return const, tensor


def period17_values() -> np.ndarray:
    """Numeric period values; each coset is closed under negation, so real."""
    cosets, _ = period17_cosets()
    ang = 2.0 * math.pi / 17.0
    return np.array(
        [sum(math.cos(ang * r) for r in coset) for coset in cosets]
    )


def period17_embedding_matrix() -> np.ndarray:
    """Rows are the four real embeddings sigma_r(eta_k) = eta_{(k+r) mod 4}."""
    v = period17_values()
    return np.array([[v[(k + r) % 4] for k in range(4)] for r in range(4)])


def quartic17_box(q: int) -> np.ndarray:
    """All integer period-coordinate vectors with every embedding <= sqrt(q).

    Any alpha appearing in alpha^2+beta^2=q over the quartic order satisfies
    sigma_r(alpha)^2 <= q at every real place, so this box is complete.  The
    float margin only enlarges the box; membership is never decided by floats.
    """
    emb = period17_embedding_matrix()
    winv = np.linalg.inv(emb)
    bound = math.sqrt(q) + 1e-6
    caps = [
        int(math.floor(sum(abs(winv[k, r]) for r in range(4)) * bound)) + 1
        for k in range(4)
    ]
    c2 = emb[:, 2]
    c3 = emb[:, 3]
    lo3 = np.where(c3 > 0, -1.0, 1.0)
    rows: list[np.ndarray] = []
    a2_grid = np.arange(-caps[2], caps[2] + 1, dtype=np.int64)
    for a0 in range(-caps[0], caps[0] + 1):
        for a1 in range(-caps[1], caps[1] + 1):
            base = a0 * emb[:, 0] + a1 * emb[:, 1]
            rem = base[:, None] + c2[:, None] * a2_grid[None, :]
            end_a = (lo3[:, None] * bound - rem) / c3[:, None]
            end_b = (-lo3[:, None] * bound - rem) / c3[:, None]
            lo = np.ceil(np.maximum.reduce(np.minimum(end_a, end_b))).astype(np.int64)
            hi = np.floor(np.minimum.reduce(np.maximum(end_a, end_b))).astype(np.int64)
            counts = np.maximum(hi - lo + 1, 0)
            total = int(counts.sum())
            if not total:
                continue
            sel = counts > 0
            reps = counts[sel]
            starts = lo[sel]
            a3 = np.repeat(starts, reps) + (
                np.arange(total, dtype=np.int64)
                - np.repeat(np.cumsum(reps) - reps, reps)
            )
            block = np.empty((total, 4), dtype=np.int64)
            block[:, 0] = a0
            block[:, 1] = a1
            block[:, 2] = np.repeat(a2_grid[sel], reps)
            block[:, 3] = a3
            rows.append(block)
    return np.concatenate(rows) if rows else np.empty((0, 4), dtype=np.int64)


def quartic17_square_coords(arr: np.ndarray) -> np.ndarray:
    """Exact canonical period coordinates of alpha^2 for each row alpha.

    Uses 1 = -(eta_0+eta_1+eta_2+eta_3) to fold the constant term back into
    the period basis; all arithmetic is int64.
    """
    const, tensor = period17_structure()
    a = arr.astype(np.int64)
    pair = np.einsum("ni,nj->nij", a, a)
    m = np.einsum("nij,ijk->nk", pair, np.asarray(tensor, dtype=np.int64))
    e = np.einsum("nij,ij->n", pair, np.asarray(const, dtype=np.int64))
    return m - e[:, None]


def quartic17_two_square_pairs(
    q: int,
) -> tuple[list[tuple[int, ...]], dict[tuple[int, ...], list[tuple[int, ...]]]]:
    """All ordered pairs (alpha,beta) in the period order with alpha^2+beta^2=q.

    Exact meet-in-the-middle on the canonical period coordinates of the
    squares: q maps to (-q,-q,-q,-q), so beta must satisfy
    coords(beta^2) = (-q,..) - coords(alpha^2).  Complete over the embedding
    box, which contains every solution.
    """
    box = quartic17_box(q)
    sq = np.concatenate([
        quartic17_square_coords(box[lo:lo + 200_000])
        for lo in range(0, len(box), 200_000)
    ]) if len(box) else np.empty((0, 4), dtype=np.int64)
    off = 1 << 14
    if int(np.abs(sq).max(initial=0)) + q >= off:
        raise AssertionError("square coordinates exceed packing range")

    def pack(mat: np.ndarray) -> np.ndarray:
        return (
            ((mat[:, 0] + off) << 45)
            | ((mat[:, 1] + off) << 30)
            | ((mat[:, 2] + off) << 15)
            | (mat[:, 3] + off)
        )

    keys = pack(sq)
    need = pack(-q - sq)
    order = np.argsort(keys)
    sorted_keys = keys[order]
    left = np.searchsorted(sorted_keys, need, side="left")
    right = np.searchsorted(sorted_keys, need, side="right")
    halves: list[tuple[int, ...]] = []
    mates: dict[tuple[int, ...], list[tuple[int, ...]]] = {}
    for i in np.nonzero(right > left)[0]:
        alpha = tuple(int(v) for v in box[i])
        betas = [
            tuple(int(v) for v in box[order[j]])
            for j in range(int(left[i]), int(right[i]))
        ]
        halves.append(alpha)
        mates[alpha] = betas
    return halves, mates


def c51_orbit_roles(
    alg: MarginalOrbitAlgebra,
) -> tuple[int, int, list[int], list[int]]:
    """Map the ten t'=51 orbits to their component roles.

    Returns (zero_idx, seventeen_idx, unit_idx_by_coset, triple_idx_by_coset),
    where coset k is the mod-17 coset 3^k U of the orbit representative.
    """
    expected_vp = [1, 4, 13, 16, 35, 38, 47, 50]
    if alg.tp != 51 or alg.Vp != expected_vp:
        raise SystemExit(
            "--c51-quartic-check requires t'=51 with V' = {+-1 mod 3} x {+-1,+-4 mod 17}"
        )
    _, coset_index = period17_cosets()
    unit = [-1] * 4
    triple = [-1] * 4
    seventeen = -1
    for idx, orb in enumerate(alg.orbits):
        if idx == alg.zero_orbit:
            continue
        rep = min(orb)
        if rep % 17 == 0:
            assert len(orb) == 2
            seventeen = idx
        elif rep % 3 == 0:
            assert len(orb) == 4
            triple[coset_index[rep % 17]] = idx
        else:
            assert len(orb) == 8
            unit[coset_index[rep % 17]] = idx
            assert coset_index[6 * rep % 17] == (coset_index[rep % 17] + 3) % 4
    assert seventeen >= 0 and -1 not in unit and -1 not in triple
    return alg.zero_orbit, seventeen, unit, triple


def c51_forward(
    alg: MarginalOrbitAlgebra,
    roles: tuple[int, int, list[int], list[int]],
    values: tuple[int, ...],
) -> tuple[int, int, tuple[int, ...], tuple[int, ...]]:
    """Exact components (lambda1, lambda3, conductor-17, conductor-51).

    The quartic components are returned as canonical period coordinates:
    lambda_17 = P + sum g_k eta_k with P = x_zero + 2 x_seventeen and
    g_k = 2 u_k + p_k; lambda_51 = C + sum f_m eta_m with C = x_zero -
    x_seventeen and f_{(k+3) mod 4} = p_k - u_k (the shift is multiplication
    by 6 = zeta_51-to-zeta_17 exponent transport).
    """
    zero, seventeen, unit, triple = roles
    lam1 = sum(size * v for size, v in zip(alg.sizes, values))
    residue_sums = [0, 0, 0]
    for idx, orb in enumerate(alg.orbits):
        for j in orb:
            residue_sums[j % 3] += values[idx]
    assert residue_sums[1] == residue_sums[2]
    lam3 = residue_sums[0] - residue_sums[1]
    big_p = values[zero] + 2 * values[seventeen]
    big_c = values[zero] - values[seventeen]
    a = tuple(
        2 * values[unit[k]] + values[triple[k]] - big_p for k in range(4)
    )
    b_list = [0] * 4
    for k in range(4):
        b_list[(k + 3) % 4] = values[triple[k]] - values[unit[k]] - big_c
    return lam1, lam3, a, tuple(b_list)


def c51_inverse(
    roles: tuple[int, int, list[int], list[int]],
    lam1: int,
    lam3: int,
    a: tuple[int, ...],
    b: tuple[int, ...],
) -> tuple[int, ...] | None:
    """Invert the component transform to orbit values, or None if non-integral."""
    zero, seventeen, unit, triple = roles
    num_p = lam1 - 4 * sum(a)
    if num_p % 17:
        return None
    big_p = num_p // 17
    num_c = lam3 - 4 * sum(b)
    if num_c % 17:
        return None
    big_c = num_c // 17
    if (big_p - big_c) % 3:
        return None
    x_seventeen = (big_p - big_c) // 3
    values = [0] * 10
    values[zero] = x_seventeen + big_c
    values[seventeen] = x_seventeen
    for k in range(4):
        g = a[k] + big_p
        f = b[(k + 3) % 4] + big_c
        if (g - f) % 3:
            return None
        u = (g - f) // 3
        values[unit[k]] = u
        values[triple[k]] = u + f
    return tuple(values)


def c51_selftest(
    alg: MarginalOrbitAlgebra,
    roles: tuple[int, int, list[int], list[int]],
) -> None:
    """Round-trip and numeric character-sum validation of the transform."""
    import random

    rng = random.Random(51)
    v = period17_values()
    for trial in range(200):
        values = tuple(rng.choice(dom) for dom in alg.a_domains)
        lam1, lam3, a, b = c51_forward(alg, roles, values)
        back = c51_inverse(roles, lam1, lam3, a, b)
        assert back == values, f"round-trip failed at trial {trial}"
        if trial < 20:
            acc = [0j, 0j, 0j, 0j]
            for j in range(51):
                val = values[alg.labels[j]]
                for slot, c in enumerate((0, 17, 3, 1)):
                    acc[slot] += val * complex(
                        math.cos(2 * math.pi * c * j / 51),
                        math.sin(2 * math.pi * c * j / 51),
                    )
            big_p = (lam1 - 4 * sum(a)) // 17
            big_c = (lam3 - 4 * sum(b)) // 17
            num17 = big_p + sum((a[k] + big_p) * v[k] for k in range(4))
            num51 = big_c + sum((b[k] + big_c) * v[k] for k in range(4))
            checks = (
                (acc[0], lam1),
                (acc[1], lam3),
                (acc[2], num17),
                (acc[3], num51),
            )
            for got, want in checks:
                assert abs(got - want) < 1e-6, f"character sum mismatch: {got} vs {want}"


def c51_quartic_component_check(
    alg: MarginalOrbitAlgebra,
    limit: int,
) -> list[tuple[tuple[int, ...], tuple[int, ...]]]:
    """Exact t'=51 marginal decision via the quartic component join.

    Q[C_51]^{V'} splits by conductor 1, 3, 17, 51 with dimensions 1,1,4,4;
    the conductor-17 and conductor-51 components both land in the real quartic
    subfield K of Q(zeta_17) with the Gaussian periods as integral basis.  The
    marginal equation is equivalent to four two-square equations (two in Z,
    two in O_K) whose solutions invert to orbit values under exact divisibility
    conditions plus the fiber boxes/parities.  Every component solution is
    enumerated (embedding-bounded), so an empty join is an UNSAT proof.
    """
    roles = c51_orbit_roles(alg)
    c51_selftest(alg, roles)
    zero, seventeen, unit, triple = roles

    reps_z = gaussian_representations(alg.q)
    z_mates: dict[int, list[int]] = {}
    for x, y in reps_z:
        z_mates.setdefault(x, []).append(y)

    halves, k_mates = quartic17_two_square_pairs(alg.q)
    for x, y in reps_z:
        rat_x = (-x, -x, -x, -x)
        rat_y = (-y, -y, -y, -y)
        assert rat_x in k_mates and rat_y in k_mates[rat_x], (
            "rational representation missing from quartic solution set"
        )
    print(
        "c51 quartic component check: "
        f"integer representations={len(reps_z)} "
        f"quartic halves={len(halves)} "
        f"quartic ordered pairs={sum(len(v) for v in k_mates.values())}"
    )

    uniform = [
        h for h in halves
        if len({coord % 2 for coord in h}) == 1
    ]
    print(f"  uniform-parity quartic halves={len(uniform)}")

    def side_candidates(
        domains: list[list[int]],
    ) -> dict[tuple[int, int, tuple[int, ...], tuple[int, ...]], tuple[int, ...]]:
        domain_sets = [set(dom) for dom in domains]
        cand_a: list[tuple[int, tuple[int, ...], int]] = []
        for lam1 in sorted(z_mates):
            for a in uniform:
                num = lam1 - 4 * sum(a)
                if num % 17:
                    continue
                big_p = num // 17
                if any((a[k] + big_p) % 2 == 0 for k in range(4)):
                    continue
                cand_a.append((lam1, a, big_p))
        buckets: dict[
            tuple[int, tuple[int, ...]],
            list[tuple[int, tuple[int, ...], int]],
        ] = {}
        n_b = 0
        for lam3 in sorted(z_mates):
            for b in uniform:
                num = lam3 - 4 * sum(b)
                if num % 17:
                    continue
                big_c = num // 17
                if any((b[k] + big_c) % 2 for k in range(4)):
                    continue
                key = (
                    big_c % 3,
                    tuple((b[(k + 3) % 4] + big_c) % 3 for k in range(4)),
                )
                buckets.setdefault(key, []).append((lam3, b, big_c))
                n_b += 1
        out: dict[
            tuple[int, int, tuple[int, ...], tuple[int, ...]], tuple[int, ...]
        ] = {}
        for lam1, a, big_p in cand_a:
            key = (
                big_p % 3,
                tuple((a[k] + big_p) % 3 for k in range(4)),
            )
            for lam3, b, big_c in buckets.get(key, []):
                values = c51_inverse(roles, lam1, lam3, a, b)
                if values is None:
                    continue
                if all(
                    values[i] in domain_sets[i] for i in range(len(values))
                ):
                    out[(lam1, lam3, a, b)] = values
        print(
            f"    lambda1-compatible halves={len(cand_a)} "
            f"lambda3-compatible halves={n_b} valid side vectors={len(out)}"
        )
        return out

    print("  A side:")
    side_a = side_candidates(alg.a_domains)
    print("  B side:")
    side_b = side_candidates(alg.b_domains)

    target = [0] * vector_dimension(alg)
    target[alg.zero_orbit] = alg.q
    target[-1] = alg.q

    witnesses: list[tuple[tuple[int, ...], tuple[int, ...]]] = []
    for (lam1, lam3, a, b), avals in side_a.items():
        for lam1_b in z_mates[lam1]:
            for lam3_b in z_mates[lam3]:
                for a_b in k_mates.get(a, []):
                    for b_b in k_mates.get(b, []):
                        bvals = side_b.get((lam1_b, lam3_b, a_b, b_b))
                        if bvals is None:
                            continue
                        vec_a = side_vector(alg, avals)
                        vec_b = side_vector(alg, bvals)
                        assert all(
                            va + vb == tv
                            for va, vb, tv in zip(vec_a, vec_b, target)
                        ), "witness failed exact marginal verification"
                        witnesses.append((avals, bvals))
                        if len(witnesses) >= limit:
                            print(
                                f"  component result: SAT ({len(witnesses)} "
                                "verified witness(es) shown)"
                            )
                            for w_a, w_b in witnesses:
                                print(f"  A={w_a} B={w_b}")
                            return witnesses
    if witnesses:
        print(
            f"  component result: SAT ({len(witnesses)} verified witness(es) shown)"
        )
        for w_a, w_b in witnesses:
            print(f"  A={w_a} B={w_b}")
    else:
        print("  component result: UNSAT")
    return witnesses


def is_prime(n: int) -> bool:
    if n < 2:
        return False
    if n % 2 == 0:
        return n == 2
    f = 3
    while f * f <= n:
        if n % f == 0:
            return False
        f += 2
    return True


def primitive_root(ell: int) -> int:
    """Smallest primitive root modulo an odd prime ell."""
    assert is_prime(ell) and ell > 2
    prime_factors = []
    n = ell - 1
    f = 2
    while f * f <= n:
        if n % f == 0:
            prime_factors.append(f)
            while n % f == 0:
                n //= f
        f += 1
    if n > 1:
        prime_factors.append(n)
    for g in range(2, ell):
        if all(pow(g, (ell - 1) // p, ell) != 1 for p in prime_factors):
            return g
    raise AssertionError(f"no primitive root found modulo {ell}")


def prime_subtorus_cosets(
    ell: int,
    Hp: list[int],
) -> tuple[list[list[int]], dict[int, int]]:
    """Cosets g^k * Hp of Hp in (Z/ell)^*, indexed by powers of a generator.

    The Gaussian periods eta_k = sum_{r in g^k Hp} zeta_ell^r form an integral
    basis of K = Q(zeta_ell)^Hp (ell prime, tame, Hilbert-Speiser); the Galois
    group of K is cyclic of order d = (ell-1)/|Hp| and shifts the coset index
    by one.  Requires -1 in Hp, so every coset is negation-closed and the
    periods are real.
    """
    assert is_prime(ell) and ell > 2, f"ell={ell} must be an odd prime"
    H = sorted(set(Hp))
    assert 1 in H and (ell - 1) in H, "Hp must contain +-1 for real periods"
    d = (ell - 1) // len(H)
    g = primitive_root(ell)
    cosets: list[list[int]] = []
    index: dict[int, int] = {}
    for k in range(d):
        mult = pow(g, k, ell)
        coset = sorted(mult * u % ell for u in H)
        for r in coset:
            assert r not in index, "Hp is not a subgroup of (Z/ell)^*"
            index[r] = k
        cosets.append(coset)
    assert len(index) == ell - 1
    return cosets, index


def prime_period_values(ell: int, cosets: list[list[int]]) -> np.ndarray:
    """Numeric period values; each coset is negation-closed, so real."""
    ang = 2.0 * math.pi / ell
    return np.array(
        [sum(math.cos(ang * r) for r in coset) for coset in cosets]
    )


def prime_period_structure(
    ell: int,
    cosets: list[list[int]],
) -> tuple[list[list[int]], list[list[list[int]]]]:
    """Exact table eta_i*eta_j = const[i][j]*1 + sum_k tensor[i][j][k]*eta_k.

    Computed by convolution of coset indicators in Z[zeta_ell]; the zeta^0
    coefficient is the constant term and the rest must be constant on cosets.
    Numerically cross-checked against the float period values.
    """
    d = len(cosets)
    const = [[0] * d for _ in range(d)]
    tensor = [[[0] * d for _ in range(d)] for _ in range(d)]
    coset_arrays = [np.asarray(coset, dtype=np.int64) for coset in cosets]
    for i in range(d):
        for j in range(d):
            sums = (coset_arrays[i][:, None] + coset_arrays[j][None, :]) % ell
            counts = np.bincount(sums.ravel(), minlength=ell)
            const[i][j] = int(counts[0])
            for k in range(d):
                values = set(counts[coset_arrays[k]].tolist())
                if len(values) != 1:
                    raise AssertionError("period product not coset-constant")
                tensor[i][j][k] = values.pop()
    v = prime_period_values(ell, cosets)
    for i in range(d):
        for j in range(d):
            got = v[i] * v[j]
            want = const[i][j] + sum(tensor[i][j][k] * v[k] for k in range(d))
            if abs(got - want) > 1e-6 * max(1.0, ell):
                raise AssertionError("period structure fails numeric check")
    return const, tensor


def prime_period_embedding_matrix(values: np.ndarray) -> np.ndarray:
    """Rows are the d real embeddings sigma_r(eta_k) = eta_{(k+r) mod d}."""
    d = len(values)
    return np.array([[values[(k + r) % d] for k in range(d)] for r in range(d)])


def prime_period_box_prediction(q: int, emb: np.ndarray) -> tuple[int, list[int]]:
    """Predicted outer enumeration size and per-coordinate caps for the box.

    Cheap (no enumeration): this is the exact outer product that
    prime_period_box would iterate, so callers can print an honest decline
    reason or affordability estimate before any work starts.
    """
    d = emb.shape[0]
    winv = np.linalg.inv(emb)
    bound = math.sqrt(q) + 1e-6
    caps = [
        int(math.floor(sum(abs(winv[k, r]) for r in range(d)) * bound)) + 1
        for k in range(d)
    ]
    outer = math.prod(2 * caps[k] + 1 for k in range(d - 1))
    return outer, caps


def prime_period_lattice_prediction(q: int, ell: int, degree: int) -> float:
    """Volume predictor for points in the true embedding cube.

    The period lattice covolume is sqrt(ell^(degree-1)), while the admissible
    embedding region is the cube |sigma(alpha)| <= sqrt(q) at every real place.
    """
    log_est = (
        degree * (math.log(2.0) + 0.5 * math.log(q))
        - 0.5 * (degree - 1) * math.log(ell)
    )
    if log_est > math.log(sys.float_info.max):
        return math.inf
    return math.exp(log_est)


def format_point_prediction(value: float) -> str:
    """Compact formatting for lattice-point predictors in progress messages."""
    if math.isinf(value):
        return "inf"
    if value >= 10_000_000:
        return f"{value:.3e}"
    if value >= 1_000:
        return f"{value:,.0f}"
    return f"{value:.1f}"


def lll_reduced_embedding(
    emb: np.ndarray,
    delta: float = 0.99,
) -> tuple[np.ndarray, np.ndarray]:
    """LLL-reduce the column lattice of emb, returning (emb @ U, U).

    Dimensions in this application are small; a full Gram-Schmidt refresh after
    each integer column operation is simpler and more robust than incremental
    bookkeeping.
    """
    red = np.array(emb, dtype=np.float64, copy=True)
    d = red.shape[1]
    transform = np.eye(d, dtype=np.int64)

    def gram_schmidt() -> tuple[np.ndarray, np.ndarray]:
        mu = np.zeros((d, d), dtype=np.float64)
        orth: list[np.ndarray] = []
        norms = np.zeros(d, dtype=np.float64)
        for i in range(d):
            v = red[:, i].copy()
            for j in range(i):
                if norms[j] <= 1e-24:
                    raise AssertionError("period embedding basis is singular")
                mu[i, j] = float(np.dot(red[:, i], orth[j]) / norms[j])
                v -= mu[i, j] * orth[j]
            orth.append(v)
            norms[i] = float(np.dot(v, v))
        return mu, norms

    mu, norms = gram_schmidt()
    k = 1
    steps = 0
    while k < d:
        for j in range(k - 1, -1, -1):
            coeff = int(np.rint(mu[k, j]))
            if coeff:
                red[:, k] -= coeff * red[:, j]
                transform[:, k] -= coeff * transform[:, j]
                mu, norms = gram_schmidt()
        if norms[k] >= (delta - mu[k, k - 1] * mu[k, k - 1]) * norms[k - 1]:
            k += 1
        else:
            red[:, [k - 1, k]] = red[:, [k, k - 1]]
            transform[:, [k - 1, k]] = transform[:, [k, k - 1]]
            mu, norms = gram_schmidt()
            k = max(k - 1, 1)
        steps += 1
        if steps > 100_000:
            raise AssertionError("LLL reduction did not converge")
    det = round(float(np.linalg.det(transform.astype(np.float64))))
    if abs(det) != 1:
        raise AssertionError("LLL transform is not unimodular")
    return red, transform


def product_chunk(
    domains: list[np.ndarray],
    start: int,
    stop: int,
) -> np.ndarray:
    """Mixed-radix chunk of a Cartesian product of one-dimensional domains."""
    width = len(domains)
    if width == 0:
        return np.empty((1, 0), dtype=np.int64)
    idx = np.arange(start, stop, dtype=np.int64)
    out = np.empty((stop - start, width), dtype=np.int64)
    for col in range(width - 1, -1, -1):
        dom = domains[col]
        size = len(dom)
        out[:, col] = dom[idx % size]
        idx //= size
    return out


def row_key_view(arr: np.ndarray) -> np.ndarray:
    """View an int64 matrix as one structured key per row."""
    mat = np.ascontiguousarray(arr, dtype=np.int64)
    dtype = np.dtype([(f"f{k}", np.int64) for k in range(mat.shape[1])])
    return mat.view(dtype).reshape(mat.shape[0])


def same_int_row_set(a: np.ndarray, b: np.ndarray) -> bool:
    """Return whether two int64 matrices have the same row set."""
    if a.shape != b.shape:
        return False
    if len(a) == 0:
        return True
    return bool(np.array_equal(np.sort(row_key_view(a)), np.sort(row_key_view(b))))


def prime_period_reduced_work(
    q: int,
    emb: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, list[int], int, int]:
    """Reduced basis, coordinate caps, solve index, and head-state count."""
    red, transform = lll_reduced_embedding(emb)
    _red_outer, caps = prime_period_box_prediction(q, red)
    solve_idx = max(range(emb.shape[0]), key=lambda k: caps[k])
    n_heads = math.prod(
        2 * caps[k] + 1 for k in range(emb.shape[0]) if k != solve_idx
    )
    return red, transform, caps, solve_idx, n_heads


def prime_period_lattice_points(
    q: int,
    ell: int,
    emb: np.ndarray,
    point_cap: int = 20_000_000,
    box_crosscheck_cap: int = 5_000_000,
    chunk_heads: int = 200_000,
    head_state_cap: int = 100_000_000,
) -> np.ndarray | None:
    """All integer period-coordinate vectors in the embedding cube.

    The search is performed in an LLL-reduced period-lattice basis.  For any
    admissible point x, the trace-form bound ||E x||_2^2 <= d*q gives the
    Fincke-Pohst containing ellipsoid; the actual enumeration below walks the
    reduced embedding cube directly and keeps the exact sup-norm filter as the
    final membership test.  When the old coordinate box is affordable, its
    output is asserted identical as a completeness audit.
    """
    d = emb.shape[0]
    bound = math.sqrt(q) + 1e-6
    predicted = prime_period_lattice_prediction(q, ell, d)
    old_outer, _old_caps = prime_period_box_prediction(q, emb)
    print(
        f"  [period-lattice] q={q} ell={ell} d={d} "
        f"predicted points~{format_point_prediction(predicted)} "
        f"cap={point_cap:,} coordinate-box outer={old_outer:,}",
        file=sys.stderr,
        flush=True,
    )
    if predicted > point_cap:
        print(
            f"  [period-lattice] q={q} ell={ell} d={d} DECLINED: "
            f"predicted points~{format_point_prediction(predicted)} "
            f"> cap {point_cap:,}",
            file=sys.stderr,
            flush=True,
        )
        return None

    red, transform, caps, solve_idx, n_heads = prime_period_reduced_work(q, emb)
    head_indices = [k for k in range(d) if k != solve_idx]
    head_domains = [
        np.arange(-caps[k], caps[k] + 1, dtype=np.int64)
        for k in head_indices
    ]
    print(
        f"  [period-lattice] reduced caps={caps} "
        f"solve=y{solve_idx} head states={n_heads:,}",
        file=sys.stderr,
        flush=True,
    )
    if n_heads > head_state_cap:
        print(
            f"  [period-lattice] q={q} ell={ell} d={d} DECLINED: "
            f"reduced head states={n_heads:,} > cap {head_state_cap:,}",
            file=sys.stderr,
            flush=True,
        )
        return None

    rows: list[np.ndarray] = []
    kept_total = 0
    start_time = time.monotonic()
    next_report = start_time + 5.0
    solve_col = red[:, solve_idx]
    head_cols = red[:, head_indices]
    solve_cap = caps[solve_idx]
    for head_start in range(0, n_heads, chunk_heads):
        head_stop = min(head_start + chunk_heads, n_heads)
        heads = product_chunk(head_domains, head_start, head_stop)
        base = heads @ head_cols.T if head_indices else np.zeros((1, d))
        lo = np.full(len(heads), -solve_cap, dtype=np.int64)
        hi = np.full(len(heads), solve_cap, dtype=np.int64)
        valid = np.ones(len(heads), dtype=bool)
        for r in range(d):
            coeff = solve_col[r]
            if abs(coeff) <= 1e-14:
                valid &= np.abs(base[:, r]) <= bound + 1e-9
                continue
            end_a = (-bound - base[:, r]) / coeff
            end_b = (bound - base[:, r]) / coeff
            row_lo = np.ceil(np.minimum(end_a, end_b) - 1e-9).astype(np.int64)
            row_hi = np.floor(np.maximum(end_a, end_b) + 1e-9).astype(np.int64)
            lo = np.maximum(lo, row_lo)
            hi = np.minimum(hi, row_hi)
        valid &= hi >= lo
        if np.any(valid):
            heads_valid = heads[valid]
            lo_valid = lo[valid]
            counts = (hi[valid] - lo_valid + 1).astype(np.int64)
            total = int(counts.sum())
            offsets = np.repeat(np.cumsum(counts) - counts, counts)
            solve_values = np.repeat(lo_valid, counts) + (
                np.arange(total, dtype=np.int64) - offsets
            )
            y_block = np.empty((total, d), dtype=np.int64)
            y_block[:, head_indices] = np.repeat(heads_valid, counts, axis=0)
            y_block[:, solve_idx] = solve_values
            x_block = y_block @ transform.T
            embeds = x_block @ emb.T
            keep = np.max(np.abs(embeds), axis=1) <= bound + 1e-9
            if np.any(keep):
                block = np.ascontiguousarray(x_block[keep], dtype=np.int64)
                rows.append(block)
                kept_total += len(block)
                if kept_total > point_cap:
                    print(
                        f"  [period-lattice] q={q} ell={ell} d={d} "
                        f"ABORTED: actual points exceeded cap {point_cap:,}",
                        file=sys.stderr,
                        flush=True,
                    )
                    return None
        now = time.monotonic()
        if now >= next_report:
            done = head_stop
            rate = done / (now - start_time)
            eta = (n_heads - done) / rate if rate else float("inf")
            print(
                f"  [period-lattice] q={q} ell={ell} d={d} "
                f"heads {done:,}/{n_heads:,} kept={kept_total:,} "
                f"elapsed={now - start_time:.0f}s eta={eta:.0f}s",
                file=sys.stderr,
                flush=True,
            )
            next_report = now + 5.0

    out = (
        np.concatenate(rows)
        if rows else np.empty((0, d), dtype=np.int64)
    )
    if old_outer <= box_crosscheck_cap:
        old = prime_period_box(q, emb, box_crosscheck_cap)
        if old is None or not same_int_row_set(out, old):
            old_len = -1 if old is None else len(old)
            raise AssertionError(
                f"period lattice cross-check failed at q={q}, ell={ell}: "
                f"lattice={len(out)} old_box={old_len}"
            )
        print(
            f"  [period-lattice] q={q} ell={ell} cross-check OK "
            f"({len(out):,} embedding points)",
            file=sys.stderr,
            flush=True,
        )
    return out


def prime_period_box(
    q: int,
    emb: np.ndarray,
    outer_cap: int = 5_000_000,
) -> np.ndarray | None:
    """All integer period-coordinate vectors with every embedding <= sqrt(q).

    Any alpha appearing in alpha^2+beta^2=q over the period order satisfies
    sigma_r(alpha)^2 <= q at every real place, so this box is complete.  The
    float margin only enlarges the box; membership is never decided by floats.
    Returns None (refuse) when the outer enumeration exceeds outer_cap.
    Self-reports progress to stderr when the enumeration runs past 5 s.
    """
    d = emb.shape[0]
    bound = math.sqrt(q) + 1e-6
    outer, caps = prime_period_box_prediction(q, emb)
    if outer > outer_cap:
        return None
    c_grid = emb[:, d - 2]
    c_last = emb[:, d - 1]
    lo_sign = np.where(c_last > 0, -1.0, 1.0)
    grid = np.arange(-caps[d - 2], caps[d - 2] + 1, dtype=np.int64)
    rows: list[np.ndarray] = []
    head_domains = [range(-caps[k], caps[k] + 1) for k in range(d - 2)]
    n_heads = math.prod(2 * caps[k] + 1 for k in range(d - 2))
    start = time.monotonic()
    next_report = start + 5.0
    for head_idx, head in enumerate(itertools.product(*head_domains)):
        now = time.monotonic()
        if now >= next_report:
            rate = (head_idx + 1) / (now - start)
            eta = (n_heads - head_idx - 1) / rate if rate else float("inf")
            print(f"  [period-box] q={q} d={d} head {head_idx + 1:,}/{n_heads:,} "
                  f"elapsed={now - start:.0f}s eta={eta:.0f}s",
                  file=sys.stderr, flush=True)
            next_report = now + 5.0
        if head:
            base = emb[:, : d - 2] @ np.asarray(head, dtype=np.float64)
        else:
            base = np.zeros(d)
        rem = base[:, None] + c_grid[:, None] * grid[None, :]
        end_a = (lo_sign[:, None] * bound - rem) / c_last[:, None]
        end_b = (-lo_sign[:, None] * bound - rem) / c_last[:, None]
        lo = np.ceil(np.maximum.reduce(np.minimum(end_a, end_b))).astype(np.int64)
        hi = np.floor(np.minimum.reduce(np.maximum(end_a, end_b))).astype(np.int64)
        counts = np.maximum(hi - lo + 1, 0)
        total = int(counts.sum())
        if not total:
            continue
        sel = counts > 0
        reps = counts[sel]
        starts = lo[sel]
        last = np.repeat(starts, reps) + (
            np.arange(total, dtype=np.int64)
            - np.repeat(np.cumsum(reps) - reps, reps)
        )
        block = np.empty((total, d), dtype=np.int64)
        for k in range(d - 2):
            block[:, k] = head[k]
        block[:, d - 2] = np.repeat(grid[sel], reps)
        block[:, d - 1] = last
        rows.append(block)
    return np.concatenate(rows) if rows else np.empty((0, d), dtype=np.int64)


def prime_period_square_coords(
    arr: np.ndarray,
    const: list[list[int]],
    tensor: list[list[list[int]]],
) -> np.ndarray:
    """Exact canonical period coordinates of alpha^2 for each row alpha.

    Uses 1 = -(eta_0+...+eta_{d-1}) to fold the constant term back into the
    period basis; all arithmetic is int64.
    """
    a = arr.astype(np.int64)
    pair = np.einsum("ni,nj->nij", a, a)
    m = np.einsum("nij,ijk->nk", pair, np.asarray(tensor, dtype=np.int64))
    e = np.einsum("nij,ij->n", pair, np.asarray(const, dtype=np.int64))
    return m - e[:, None]


def prime_period_two_square_pairs(
    q: int,
    ell: int,
    Hp: list[int],
    point_cap: int = 20_000_000,
    box_crosscheck_cap: int = 5_000_000,
) -> tuple[
    list[tuple[int, ...]],
    dict[tuple[int, ...], list[tuple[int, ...]]],
    int,
] | None:
    """All ordered pairs (alpha,beta) in period coordinates with alpha^2+beta^2=q.

    Exact meet-in-the-middle on the canonical period coordinates of the
    squares: q maps to (-q,...,-q), so beta must satisfy
    coords(beta^2) = (-q,...) - coords(alpha^2).  Complete over the true
    embedding cube, enumerated in a reduced period-lattice basis.  Returns None
    if the predicted/actual point count exceeds point_cap.
    """
    cosets, _index = prime_subtorus_cosets(ell, Hp)
    const, tensor = prime_period_structure(ell, cosets)
    emb = prime_period_embedding_matrix(prime_period_values(ell, cosets))
    points = prime_period_lattice_points(
        q, ell, emb, point_cap, box_crosscheck_cap
    )
    if points is None:
        return None
    if not len(points):
        return [], {}, 0

    chunk = 200_000
    sq = np.empty_like(points, dtype=np.int64)
    start = time.monotonic()
    next_report = start + 5.0
    for lo in range(0, len(points), chunk):
        hi = min(lo + chunk, len(points))
        sq[lo:hi] = prime_period_square_coords(points[lo:hi], const, tensor)
        now = time.monotonic()
        if now >= next_report:
            rate = hi / (now - start)
            eta = (len(points) - hi) / rate if rate else float("inf")
            print(
                f"  [period-square] q={q} ell={ell} squared "
                f"{hi:,}/{len(points):,} elapsed={now - start:.0f}s "
                f"eta={eta:.0f}s",
                file=sys.stderr,
                flush=True,
            )
            next_report = now + 5.0
    sq = np.ascontiguousarray(sq, dtype=np.int64)
    print(
        f"  [period-square] q={q} ell={ell} sorting "
        f"{len(points):,} square keys",
        file=sys.stderr,
        flush=True,
    )
    keys = row_key_view(sq)
    order = np.argsort(keys, kind="mergesort")
    sorted_keys = keys[order]
    halves: list[tuple[int, ...]] = []
    mates: dict[tuple[int, ...], list[tuple[int, ...]]] = {}
    next_report = time.monotonic() + 5.0
    for lo in range(0, len(sq), chunk):
        hi = min(lo + chunk, len(sq))
        need = np.ascontiguousarray(-q - sq[lo:hi], dtype=np.int64)
        need_keys = row_key_view(need)
        left = np.searchsorted(sorted_keys, need_keys, side="left")
        right = np.searchsorted(sorted_keys, need_keys, side="right")
        hit_rows = np.nonzero(left < right)[0]
        for local_i in hit_rows:
            i = lo + int(local_i)
            alpha = tuple(int(v) for v in points[i])
            js = order[left[local_i]:right[local_i]]
            halves.append(alpha)
            mates[alpha] = [
                tuple(int(v) for v in points[int(j)])
                for j in js
            ]
        now = time.monotonic()
        if now >= next_report:
            rate = hi / (now - start)
            eta = (len(sq) - hi) / rate if rate else float("inf")
            print(
                f"  [period-square] q={q} ell={ell} matched "
                f"{hi:,}/{len(sq):,} halves={len(halves):,} "
                f"elapsed={now - start:.0f}s eta={eta:.0f}s",
                file=sys.stderr,
                flush=True,
            )
            next_report = now + 5.0
    return halves, mates, len(points)


def prime_subtorus_roles(
    alg: MarginalOrbitAlgebra,
) -> tuple[int, list[int], list[list[int]]]:
    """Map the prime sub-torus orbits to their period-coset roles.

    Returns (zero_idx, orbit_idx_by_coset, cosets), where coset k is g^k*Hp
    in the Galois-shift order of prime_subtorus_cosets.
    """
    ell = alg.tp
    if not is_prime(ell):
        raise SystemExit(
            "--prime-subtorus-check requires a prime sub-torus order t'"
        )
    cosets, index = prime_subtorus_cosets(ell, alg.Vp)
    d = len(cosets)
    assert d >= 2, "degree-1 prime sub-torus is the two-orbit scalar lane"
    orbit_by_coset = [-1] * d
    for idx, orb in enumerate(alg.orbits):
        if idx == alg.zero_orbit:
            continue
        k = index[min(orb)]
        assert sorted(orb) == cosets[k], "orbit does not match a period coset"
        orbit_by_coset[k] = idx
    assert -1 not in orbit_by_coset
    return alg.zero_orbit, orbit_by_coset, cosets


def prime_subtorus_forward(
    alg: MarginalOrbitAlgebra,
    roles: tuple[int, list[int], list[list[int]]],
    values: tuple[int, ...],
) -> tuple[int, tuple[int, ...]]:
    """Exact components (lambda_1, canonical period coordinates of lambda_ell).

    lambda_1 is the trivial character value; lambda_ell = sum_k a_k eta_k with
    a_k = x_{coset k} - x_0 after folding 1 = -(sum of periods).
    """
    zero, orbit_by_coset, _cosets = roles
    lam1 = sum(size * v for size, v in zip(alg.sizes, values))
    a = tuple(values[idx] - values[zero] for idx in orbit_by_coset)
    return lam1, a


def prime_subtorus_inverse(
    alg: MarginalOrbitAlgebra,
    roles: tuple[int, list[int], list[list[int]]],
    lam1: int,
    a: tuple[int, ...],
) -> tuple[int, ...] | None:
    """Invert the component transform to orbit values, or None if non-integral.

    With m = |Hp| and d cosets, lambda_1 = ell*x_0 + m*sum(a), so integrality
    is the single congruence lambda_1 == m*sum(a) (mod ell).
    """
    zero, orbit_by_coset, cosets = roles
    ell = alg.tp
    m = len(cosets[0])
    num = lam1 - m * sum(a)
    if num % ell:
        return None
    x0 = num // ell
    values = [0] * len(alg.orbits)
    values[zero] = x0
    for k, idx in enumerate(orbit_by_coset):
        values[idx] = x0 + a[k]
    return tuple(values)


def prime_subtorus_selftest(
    alg: MarginalOrbitAlgebra,
    roles: tuple[int, list[int], list[list[int]]],
) -> None:
    """Round-trip and numeric character-sum validation of the transform."""
    import random

    rng = random.Random(alg.tp)
    _zero, _orbit_by_coset, cosets = roles
    ell = alg.tp
    d = len(cosets)
    v = prime_period_values(ell, cosets)
    for trial in range(200):
        source = alg.a_domains if trial < 100 else alg.b_domains
        values = tuple(rng.choice(dom) for dom in source)
        lam1, a = prime_subtorus_forward(alg, roles, values)
        back = prime_subtorus_inverse(alg, roles, lam1, a)
        assert back == values, f"round-trip failed at trial {trial}"
        if trial < 10:
            for r in range(min(d, 2)):
                c = min(cosets[r])
                acc = 0j
                for j in range(ell):
                    acc += values[alg.labels[j]] * complex(
                        math.cos(2 * math.pi * c * j / ell),
                        math.sin(2 * math.pi * c * j / ell),
                    )
                want = sum(a[k] * v[(k + r) % d] for k in range(d))
                assert abs(acc - want) < 1e-6 * max(1.0, ell), (
                    f"character sum mismatch at coset {r}: {acc} vs {want}"
                )
        if trial == 0:
            assert lam1 == sum(values[alg.labels[j]] for j in range(ell))


def prime_subtorus_join(
    alg: MarginalOrbitAlgebra,
    point_cap: int = 20_000_000,
    max_witnesses: int = 12,
    box_crosscheck_cap: int = 5_000_000,
) -> dict:
    """Exact prime sub-torus marginal decision via the Q x K component join.

    Q[C_ell]^{Hp} = Q x K with K = Q(zeta_ell)^{Hp}; the marginal equation is
    equivalent to one integer two-square equation and one two-square equation
    in the period order of K, joined by the inverse-transform congruence
    lambda_1 == m*sum(a) (mod ell) and the fiber boxes/parities.  Parities
    force the A-side period coordinates all odd with lambda_1(A) even, and the
    B-side coordinates all even with lambda_1(B) odd.  Every component
    solution is enumerated (embedding-bounded), so an empty join is an UNSAT
    proof.  Returns a result dict; status REFUSED means the predicted or actual
    embedding-region lattice-point count exceeded point_cap and nothing was
    decided.
    """
    roles = prime_subtorus_roles(alg)
    prime_subtorus_selftest(alg, roles)
    _zero, _orbit_by_coset, cosets = roles
    ell = alg.tp
    d = len(cosets)
    values = prime_period_values(ell, cosets)
    emb = prime_period_embedding_matrix(values)
    predicted_outer, _caps = prime_period_box_prediction(alg.q, emb)
    predicted_points = prime_period_lattice_prediction(alg.q, ell, d)
    out = {
        "ell": ell,
        "degree": d,
        "m": len(cosets[0]),
        "predicted_box_outer": predicted_outer,
        "predicted_lattice_points": predicted_points,
        "period_point_count": 0,
        "n_reps_z": 0,
        "n_halves": 0,
        "n_pairs": 0,
        "n_odd_halves": 0,
        "n_even_halves": 0,
        "n_side_a": 0,
        "n_side_b": 0,
        "status": "REFUSED",
        "mechanism": "lattice_point_refused",
        "witnesses": [],
        "witness_nonrational": False,
    }

    reps_z = gaussian_representations(alg.q)
    out["n_reps_z"] = len(reps_z)
    if not reps_z:
        out["status"], out["mechanism"] = "UNSAT", "no_integer_norm_rep"
        return out
    pairs = prime_period_two_square_pairs(
        alg.q, ell, alg.Vp, point_cap, box_crosscheck_cap
    )
    if pairs is None:
        return out
    halves, k_mates, point_count = pairs
    out["period_point_count"] = point_count
    for x, y in reps_z:
        rat_x = (-x,) * d
        rat_y = (-y,) * d
        assert rat_x in k_mates and rat_y in k_mates[rat_x], (
            "rational representation missing from period solution set"
        )
    out["n_halves"] = len(halves)
    out["n_pairs"] = sum(len(v) for v in k_mates.values())

    z_mates: dict[int, list[int]] = {}
    for x, y in reps_z:
        z_mates.setdefault(x, []).append(y)
    odd_halves = [a for a in halves if all(c % 2 for c in a)]
    even_halves = [a for a in halves if not any(c % 2 for c in a)]
    out["n_odd_halves"] = len(odd_halves)
    out["n_even_halves"] = len(even_halves)

    def side_candidates(
        domains: list[list[int]],
        parity_halves: list[tuple[int, ...]],
    ) -> dict[tuple[int, tuple[int, ...]], tuple[int, ...]]:
        domain_sets = [set(dom) for dom in domains]
        cands: dict[tuple[int, tuple[int, ...]], tuple[int, ...]] = {}
        for lam1 in sorted(z_mates):
            for a in parity_halves:
                values = prime_subtorus_inverse(alg, roles, lam1, a)
                if values is None:
                    continue
                if all(
                    values[i] in domain_sets[i] for i in range(len(values))
                ):
                    cands[(lam1, a)] = values
        return cands

    side_a = side_candidates(alg.a_domains, odd_halves)
    side_b = side_candidates(alg.b_domains, even_halves)
    out["n_side_a"] = len(side_a)
    out["n_side_b"] = len(side_b)
    if not side_a or not side_b:
        out["status"], out["mechanism"] = "UNSAT", "no_side_vector"
        return out

    target = [0] * vector_dimension(alg)
    target[alg.zero_orbit] = alg.q
    target[-1] = alg.q

    witnesses: list[tuple[tuple[int, ...], tuple[int, ...]]] = []
    for (lam1, a), avals in side_a.items():
        for lam1_b in z_mates[lam1]:
            for b in k_mates.get(a, []):
                bvals = side_b.get((lam1_b, b))
                if bvals is None:
                    continue
                vec_a = side_vector(alg, avals)
                vec_b = side_vector(alg, bvals)
                assert all(
                    va + vb == tv
                    for va, vb, tv in zip(vec_a, vec_b, target)
                ), "witness failed exact marginal verification"
                if len({*a}) > 1 or len({*b}) > 1:
                    out["witness_nonrational"] = True
                witnesses.append((avals, bvals))
                if len(witnesses) >= max_witnesses:
                    out["status"], out["mechanism"] = "SAT", "component_sat"
                    out["witnesses"] = witnesses
                    return out
    if witnesses:
        out["status"], out["mechanism"] = "SAT", "component_sat"
    else:
        out["status"], out["mechanism"] = "UNSAT", "component_join_unsat"
    out["witnesses"] = witnesses
    return out


def prime_subtorus_component_check(
    alg: MarginalOrbitAlgebra,
    limit: int,
    point_cap: int = 20_000_000,
) -> dict:
    """CLI wrapper for prime_subtorus_join with printed summary."""
    res = prime_subtorus_join(alg, point_cap, max_witnesses=limit)
    print(
        "prime subtorus component check: "
        f"ell={res['ell']} degree={res['degree']} |H|={res['m']}"
    )
    point_count = (
        "not enumerated"
        if res["status"] == "REFUSED"
        else f"{res['period_point_count']:,}"
    )
    print(
        f"  predicted lattice points~"
        f"{format_point_prediction(res['predicted_lattice_points'])} "
        f"actual embedding points={point_count} "
        f"coordinate-box outer={res['predicted_box_outer']:,}"
    )
    print(
        f"  integer representations={res['n_reps_z']} "
        f"period halves={res['n_halves']} "
        f"period ordered pairs={res['n_pairs']}"
    )
    print(
        f"  odd-parity halves={res['n_odd_halves']} "
        f"even-parity halves={res['n_even_halves']}"
    )
    print(
        f"  A side valid side vectors={res['n_side_a']} "
        f"B side valid side vectors={res['n_side_b']}"
    )
    if res["status"] == "REFUSED":
        print(
            f"  component result: REFUSED ({res['mechanism']}; "
            f"predicted lattice points~"
            f"{format_point_prediction(res['predicted_lattice_points'])}); "
            "raise --box-outer-cap/point cap to evaluate"
        )
        return res
    if res["status"] == "SAT":
        kind = "nonrational" if res["witness_nonrational"] else "rational-only"
        print(
            f"  component result: SAT ({len(res['witnesses'])} verified "
            f"witness(es) shown, {kind} period halves)"
        )
        for avals, bvals in res["witnesses"]:
            print(f"  A={avals} B={bvals}")
    else:
        print(f"  component result: UNSAT ({res['mechanism']})")
    return res


def print_summary(alg: MarginalOrbitAlgebra, show_structure: bool,
                  show_equations: bool, limit: int) -> None:
    print(
        f"q={alg.q} t={alg.t} t'={alg.tp} h={alg.h} "
        f"|V|={len(alg.V)} |V'|={len(alg.Vp)} #orbits={len(alg.orbits)}"
    )
    print(f"Vp={alg.Vp}")
    print("orbits:")
    for idx, orb in enumerate(alg.orbits):
        mark = " zero" if idx == alg.zero_orbit else ""
        print(f"  O{idx}{mark}: size={len(orb)} rep={min(orb)} values={compact(orb, limit)}")
    print("domains:")
    for idx in range(len(alg.orbits)):
        print(
            f"  O{idx}: A={compact(alg.a_domains[idx], limit)} "
            f"B={compact(alg.b_domains[idx], limit)}"
        )

    if show_structure:
        print("structure constants:")
        for i in range(len(alg.orbits)):
            for j in range(len(alg.orbits)):
                terms = [
                    f"{coeff}*E{q_idx}"
                    for q_idx, coeff in enumerate(alg.structure[i][j])
                    if coeff
                ]
                print(f"  E{i} E{j}^(-1) = {' + '.join(terms) if terms else '0'}")

    if show_equations:
        print("coefficient equations:")
        for q_idx, orb in enumerate(alg.orbits):
            rhs = alg.q if q_idx == alg.zero_orbit else 0
            terms = alg.equation_terms(q_idx)
            body = " + ".join(
                f"{c}*x{i}*x{j}" if i != j else f"{c}*x{i}^2"
                for c, i, j in terms
            )
            print(f"  Q{q_idx} rep={min(orb)} rhs={rhs}: A[{body}] + B[{body}]")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("q", type=int)
    parser.add_argument("--tp", type=int, required=True,
                        help="sub-torus order t' (must divide t=(q+1)/2)")
    parser.add_argument("--structure", action="store_true",
                        help="print all orbit-sum multiplication constants")
    parser.add_argument("--equations", action="store_true",
                        help="print the symmetrized quadratic coefficient equations")
    parser.add_argument("--two-orbit-rep-check", action="store_true",
                        help="run the exact two-orbit representation-pair "
                             "criterion (thm:two-orbit-reps) with a scalar "
                             "enumeration cross-check")
    parser.add_argument("--constant-check", action="store_true",
                        help="run the exact two-orbit/transitive scalar check")
    parser.add_argument("--integer-mitm", action="store_true",
                        help="run exact MITM over integer orbit-value domains")
    parser.add_argument("--integer-cap", type=int, default=3_000_000,
                        help="maximum assignments per side for --integer-mitm")
    parser.add_argument("--h3-support-paf-check", action="store_true",
                        help="run exact h=3 support/augmentation-filtered "
                             "orbit PAF MITM")
    parser.add_argument("--h3-support-paf-cap", type=int, default=5_000_000,
                        help="maximum filtered rows per side for "
                             "--h3-support-paf-check")
    parser.add_argument("--h3-support-paf-batch", type=int, default=50_000,
                        help="batch size for --h3-support-paf-check vectorized "
                             "side-vector evaluation")
    parser.add_argument("--u27-gaussian-check", action="store_true",
                        help="check the t'=27 full-unit case by rational Gaussian components")
    parser.add_argument("--u49-nested-check", action="store_true",
                        help="exact C_49 full-unit check by oriented nested "
                             "congruences with MITM cross-check")
    parser.add_argument("--u27-nested-check", action="store_true",
                        help="check the t'=27 full-unit case by oriented Gaussian congruences")
    parser.add_argument("--p3-gaussian-check", action="store_true",
                        help="check the t'=9 full-unit case by Gaussian component compatibility")
    parser.add_argument("--p5-sqrt5-check", action="store_true",
                        help="check the t'=25 lift case by Q(sqrt(5)) component compatibility")
    parser.add_argument("--p7-cubic-check", action="store_true",
                        help="check the t'=49 lift case by the real cubic "
                             "Q(zeta_7+zeta_7^-1) component compatibility")
    parser.add_argument("--c21-sqrt21-check", action="store_true",
                        help="check the t'=21 case by Q(sqrt(21)) component compatibility")
    parser.add_argument("--c57-check", action="store_true",
                        help="exact C_57 quadratic-component check "
                             "(three rational + one sqrt57 component) "
                             "with MITM cross-check")
    parser.add_argument("--c51-quartic-check", action="store_true",
                        help="check the t'=51 case by quartic-period component compatibility")
    parser.add_argument("--prime-subtorus-check", action="store_true",
                        help="check a prime t'=ell case by the Q x Q(zeta_ell)^H "
                             "Gaussian-period component join")
    parser.add_argument("--gluing-check", type=int, nargs=2,
                        metavar=("TPA", "TPB"),
                        help="exactly test whether solution-side sets for two "
                             "quotient marginals glue through this cover t'")
    parser.add_argument("--gluing-cap", type=int, default=3_000_000,
                        help="maximum assignments per side for --gluing-check")
    parser.add_argument("--box-outer-cap", type=int, default=20_000_000,
                        help="refuse the reduced period-lattice enumeration "
                             "above this predicted point count for "
                             "--prime-subtorus-check")
    parser.add_argument("--mod-check", type=int, nargs="*",
                        metavar="M",
                        help="run exact modular MITM checks for the listed moduli")
    parser.add_argument("--mod-cap", type=int, default=2_000_000,
                        help="maximum residue assignments per side for --mod-check")
    parser.add_argument("--chunk", type=int, default=200_000,
                        help="chunk size for modular enumeration")
    parser.add_argument("--json", action="store_true",
                        help="emit the full algebra as JSON after the summary")
    parser.add_argument("--limit", type=int, default=12,
                        help="maximum entries shown per long list")
    args = parser.parse_args(argv)

    alg = build_algebra(args.q, args.tp)
    print_summary(alg, args.structure, args.equations, args.limit)
    if args.constant_check:
        sols = constant_row_solutions(alg)
        if sols:
            print(f"constant-row scalar check: SAT ({len(sols)} solutions)")
            print(f"  first={sols[0]}")
        else:
            print("constant-row scalar check: UNSAT")
    if args.two_orbit_rep_check:
        two_orbit_representation_check(alg, args.limit)
    if args.integer_mitm:
        exact_integer_mitm(alg, args.integer_cap)
    if args.h3_support_paf_check:
        h3_support_paf_check(
            alg,
            args.h3_support_paf_cap,
            args.h3_support_paf_batch,
        )
    if args.u27_gaussian_check:
        u27_component_check(alg, args.limit)
    if args.u27_nested_check:
        u27_nested_congruence_check(alg, args.limit)
    if args.u49_nested_check:
        u49_nested_congruence_check(alg, args.limit)
    if args.p3_gaussian_check:
        p3_gaussian_component_check(alg, args.limit)
    if args.p5_sqrt5_check:
        p5_sqrt5_component_check(alg, args.limit)
    if args.p7_cubic_check:
        p7_cubic_component_check(alg, args.limit)
    if args.c21_sqrt21_check:
        c21_sqrt21_check(alg, args.limit)
    if args.c57_check:
        c57_sqrt57_check(alg, args.limit)
    if args.c51_quartic_check:
        c51_quartic_component_check(alg, args.limit)
    if args.prime_subtorus_check:
        prime_subtorus_component_check(alg, args.limit, args.box_outer_cap)
    if args.gluing_check:
        left_tp, right_tp = args.gluing_check
        projection_gluing_check(
            alg, left_tp, right_tp, args.gluing_cap, args.limit
        )
    if args.mod_check:
        for modulus in args.mod_check:
            modular_mitm(alg, modulus, args.mod_cap, args.chunk)
    if args.json:
        print(json.dumps(alg.to_jsonable(), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

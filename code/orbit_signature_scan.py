#!/usr/bin/env python3
"""Scan marginal orbit signatures for the arithmetic orbit-dichotomy program.

This is not a solver.  It classifies the orbit shapes forced by the composite
multiplier group M(q) on divisors t'|t, so structural obstruction families can
be studied by signature rather than by one q at a time.
"""
from __future__ import annotations

import argparse
import contextlib
import itertools
import math
import time
import os
import sys
from collections import Counter
from functools import lru_cache, reduce
from io import StringIO

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from composite_multiplier_scan import (  # noqa: E402
    crt2,
    cyclic_sub,
    divisors,
    factor,
    selfconj_kill,
    two_squares_fail,
)
from multiplier_reduced_decision import orbits, paf_vectors, v_group  # noqa: E402
from marginal_orbit_algebra import (  # noqa: E402
    C57_EXPECTED_VP,
    build_algebra as build_marginal_algebra,
    c49_boxed_join_exists,
    c51_inverse,
    c51_orbit_roles,
    cubic7_representations,
    exact_integer_mitm,
    inverse_c57_components,
    inverse_p7_components,
    format_point_prediction,
    prime_period_embedding_matrix,
    prime_period_lattice_prediction,
    prime_period_reduced_work,
    prime_period_values,
    prime_subtorus_cosets,
    prime_subtorus_join,
    quartic17_two_square_pairs,
    sqrt57_representations,
    two_orbit_rep_status,
)

# Prime sub-torus lanes are evaluated (and promoted to quantified firing) where
# the written criterion's emptiness predicate is actually affordable.  The old
# coordinate-box gate was too pessimistic for skew period bases; the active gate
# is now the true embedding-region lattice-point predictor
# (2*sqrt(q))^d/sqrt(ell^(d-1)), with the reduced enumerator enforcing the same
# cap before it allocates.  The q<=2000 proof ledger keeps the audited degree-5
# ceiling for high-degree prime-subtorus rows; the wider evidence sweep opens
# degree 6+ only when the predictor says the node is affordable.
PRIME_SUBTORUS_MAX_DEGREE = 30
PRIME_SUBTORUS_LEDGER_QMAX = 2_000
PRIME_SUBTORUS_LEDGER_MAX_DEGREE = 5
PRIME_SUBTORUS_POINT_CAP = 20_000_000
PRIME_SUBTORUS_HEAD_STATE_CAP = 100_000_000

# Full-torus prime-order rows have h=1, so the fiber boxes collapse to signs.
# The exact orbit-value MITM is then tiny for the finite panel even when the
# period-component embedding box is too large.
FULL_TORUS_INTEGER_CAP = 5_000_000

# Secondary marginal certificates are applied after the first quantified lane
# passes locally.  This cap is deliberately large enough for the q<=2000 local
# branch marginals such as 1937@57, but still refuses huge panel certificates
# that remain recorded separately.
SECONDARY_INTEGER_CAP = 3_000_000

# The h=3 support/augmentation test is a theorem-level necessary condition,
# but the augmentation DP can grow quickly in wider evidence sweeps.  If this
# cap is exceeded, the predicate simply declines to fire for that divisor.
H3_AUGMENTATION_STATE_CAP = 1_000_000

# Pre-guard for the augmentation DP: decline before starting when the
# (#nonzero orbits) x (support target) product predicts a state grind.  The
# support-sum stage always runs (it is cheap and its fires stay valid); only
# the (support, row-sum) DP is refused.  Every q<=2000 node is far below
# this bound (max ~27K); the wide w=2 nodes at qmax=10000 (~640K) are the
# ones that previously ground for tens of minutes before hitting the state
# cap anyway.
H3_AUGMENTATION_NODE_GUARD = 100_000

# Wall-clock budget for one h=3 side-states DP.  The DP self-reports
# progress past 5 s and declines (with a printed reason) past this budget,
# so no single node can silently grind a sweep.
H3_NODE_TIME_BUDGET_S = 60.0

FINITE_CERTIFICATE_ROUTES = {"exact_orbit_mitm", "exhaustive_mitm", "milp"}

# Verified secondary exact obstructions for the former q<=2000 local-pass
# branch.  These are not first-lane failures: each q has an initial quantified
# lane that passes, then a second proper divisor whose exact marginal join is
# empty.  Keeping this table makes --existential-divisor-report stable and
# fast; the dynamic helpers below remain available for new q.
#
# 2026-07-06 promotion note: the rows for 685, 1665 (C_49 full-unit nested
# criterion), 1937 (C_57 sqrt57 component criterion), and 1885 (degree-4
# prime-subtorus period join) are now CONFIRMATIONS of promoted quantified
# firing criteria, not branch sources: the report reaches
# has_quantified_firing_divisor for these q before consulting this table.
# The exact kills recorded here remain the independent finite certificates
# for those criteria (regression targets), with lanes relabeled to the
# promoted lane names.
SECONDARY_EXACT_MARGINAL_OBSTRUCTIONS = {
    185: (31, "prime_subtorus_degree_5", "no_side_vector"),
    245: (41, "prime_subtorus_degree_4", "no_side_vector"),
    425: (71, "prime_subtorus_degree_7", "integer_orbit_join_unsat"),
    685: (49, "c49_full_unit", "integer_orbit_join_unsat"),
    725: (121, "compact_middle", "integer_orbit_join_unsat"),
    1145: (191, "prime_subtorus_degree_5", "integer_orbit_join_unsat"),
    1157: (193, "prime_subtorus_degree_6", "integer_orbit_join_unsat"),
    1665: (49, "c49_full_unit", "integer_orbit_join_unsat"),
    1685: (281, "prime_subtorus_degree_4", "no_side_vector"),
    1885: (41, "prime_subtorus_degree_4", "no_side_vector"),
    1937: (57, "c57_sqrt57", "integer_orbit_join_unsat"),
}

# Exact projection-image gluing obstructions.  These are local-pass cases whose
# quotient side-solution sets do not lift to boxed rows on the common cover.
# q -> (cover t', quotient t' pair, mechanism).
PROJECTION_GLUING_OBSTRUCTIONS = {
    441: (221, (13, 17), "linear_projection_unsat"),
}

# Recorded h=3 support/augmentation-filtered PAF obstructions.  These are
# exact finite joins over the reduced row set of prop:h3-support-paf, not the
# unrestricted orbit-value MITM.
H3_SUPPORT_PAF_OBSTRUCTIONS = {
    (1445, 241): "h3_support_paf_unsat",
}


# The 21 T3-unreachable panel kills (subtorus_gluing.md section 4): the
# blind-spot multi-prime composites q<=2000 that T3's orbit cap refuses, each
# closed at one sub-torus marginal.  q -> (kill t', #orbits per the panel
# table, proof route).  The route records how the kill is *proved*
# (CP-SAT-independent confirmation), which is a different axis from the
# orbit-shape family of the killing marginal; --dichotomy-report keeps the
# two separate on purpose, because best_signature() ranks shape only and
# often prefers a prettier divisor than the one that actually kills.
PANEL_KILLS = {
    377: (27, 4, "c27_boxed_firing"),
    425: (71, 8, "h3_support_augmentation_firing"),
    545: (21, 5, "c21_join_firing"),
    549: (25, 5, "p5_sqrt5_component"),
    629: (21, 5, "c21_join_firing"),
    909: (7, 2, "constant_row_rational"),
    1025: (27, 4, "c27_residue_firing"),
    1105: (79, 4, "prime_subtorus_join_firing"),
    1189: (17, 3, "prime_subtorus_join_firing"),
    1241: (23, 2, "constant_row_rational"),
    1325: (51, 10, "quartic_component"),
    1341: (11, 2, "constant_row_rational"),
    1385: (7, 2, "constant_row_rational"),
    1445: (241, 13, "h3_support_paf_firing"),
    1469: (49, 7, "p7_cubic_component"),
    1557: (19, 2, "constant_row_rational"),
    1625: (271, 16, "h3_support_augmentation_firing"),
    1649: (25, 5, "p5_sqrt5_component"),
    1769: (59, 2, "constant_row_rational"),
    1805: (7, 2, "constant_row_rational"),
    1937: (57, 5, "c57_join_firing"),
}

# Route levels for Step 5.  Routes are promoted to quantified_firing only when
# the manuscript has a written criterion whose emptiness predicate is evaluated
# by this report; finite MITM/MILP confirmations remain finite certificates.
ROUTE_LEVEL = {
    "constant_row_rational": "quantified_firing",
    "c27_nested_component": "component_criterion",
    "c27_residue_firing": "quantified_firing",
    "c27_boxed_firing": "quantified_firing",
    "p5_sqrt5_component": "quantified_firing",
    "p7_cubic_component": "quantified_firing",
    "c21_sqrt21_component": "component_criterion",
    "c21_join_firing": "quantified_firing",
    "c49_join_firing": "quantified_firing",
    "c57_join_firing": "quantified_firing",
    "quartic_component": "quantified_firing",
    "prime_subtorus_join_firing": "quantified_firing",
    "h3_support_augmentation_firing": "quantified_firing",
    "h3_support_paf_firing": "quantified_firing",
    "exact_orbit_mitm": "finite_certificate",
    "exhaustive_mitm": "finite_certificate",
    "milp": "finite_certificate",
}

ROUTE_KIND = {
    "constant_row_rational": "quantified firing (thm:t2-twoorbit, "
                             "thm:two-orbit-reps)",
    "c27_nested_component": "component criterion (prop:c27-nested)",
    "c27_residue_firing": "quantified firing (cor:c27-residue-pair)",
    "c27_boxed_firing": "quantified firing (cor:c27-arithmetic-firing)",
    "p5_sqrt5_component": "quantified firing (prop:p5-sqrt5)",
    "p7_cubic_component": "quantified firing (prop:p7-cubic)",
    "c21_sqrt21_component": "component criterion (prop:c21-sqrt21)",
    "c21_join_firing": "quantified firing (cor:c21-arithmetic-firing)",
    "c49_join_firing": "quantified firing (prop:c49-nested, cor:c49-residue-pair)",
    "c57_join_firing": "quantified firing (prop:c57-sqrt57)",
    "quartic_component": "quantified firing (prop:q1325-quartic)",
    "prime_subtorus_join_firing": "quantified firing (cor:prime-subtorus-firing)",
    "h3_support_augmentation_firing": "quantified firing (prop:h3-support-augmentation)",
    "h3_support_paf_firing": "quantified firing (prop:q1445-h3-paf)",
    "exact_orbit_mitm": "finite certificate (exact orbit-value MITM)",
    "exhaustive_mitm": "finite certificate (complete enumeration)",
    "milp": "finite certificate (HiGHS MILP, CP-SAT-independent)",
}


KNOWN_MARGINAL_OUTCOMES = {
    (305, 9): ("SAT", "p3 Gaussian; exact MITM"),
    (377, 9): ("SAT", "p3 Gaussian; exact MITM"),
    (485, 9): ("UNSAT", "p3 Gaussian; exact MITM"),
    (549, 25): ("UNSAT", "p5 sqrt5; exact MITM"),
    (845, 9): ("SAT", "p3 Gaussian; exact MITM"),
    (949, 25): ("UNSAT", "p5 sqrt5; exact MITM"),
    (1025, 9): ("SAT", "p3 Gaussian; exact MITM"),
    (1205, 9): ("SAT", "p3 Gaussian; exact MITM"),
    (1313, 9): ("SAT", "p3 Gaussian; exact MITM"),
    (1385, 9): ("UNSAT", "p3 Gaussian; exact MITM"),
    (1421, 9): ("UNSAT", "p3 Gaussian; exact MITM"),
    (1469, 49): ("UNSAT", "p7 cubic component"),
    (1565, 9): ("SAT", "p3 Gaussian; exact MITM"),
    (1649, 25): ("UNSAT", "p5 sqrt5"),
    (1745, 9): ("UNSAT", "p3 Gaussian; exact MITM"),
    (1781, 9): ("SAT", "p3 Gaussian; exact MITM"),
}


def fmt_factor(n: int) -> str:
    pieces = []
    for p, e in factor(n).items():
        pieces.append(str(p) if e == 1 else f"{p}^{e}")
    return "*".join(pieces)


def gaussian_representations(n: int) -> list[tuple[int, int]]:
    reps = []
    limit = math.isqrt(n)
    for x in range(-limit, limit + 1):
        y2 = n - x * x
        if y2 < 0:
            continue
        y = math.isqrt(y2)
        if y * y == y2:
            reps.append((x, y))
            if y:
                reps.append((x, -y))
    return sorted(set(reps))


def gaussian_eo(value: tuple[int, int]) -> bool:
    return value[0] % 2 == 0 and value[1] % 2 != 0


def gaussian_oe(value: tuple[int, int]) -> bool:
    return value[0] % 2 != 0 and value[1] % 2 == 0


def gaussian_residue(value: tuple[int, int], modulus: int) -> tuple[int, int]:
    return (value[0] % modulus, value[1] % modulus)


def inverse_u27(values: tuple[int, int, int, int]) -> tuple[int, int, int, int] | None:
    u1, u3, u9, u27 = values
    numerators = (
        u1 + 2 * u3 + 6 * u9 + 18 * u27,
        u1 - u3,
        u1 + 2 * u3 - 3 * u9,
        u1 + 2 * u3 + 6 * u9 - 9 * u27,
    )
    if any(value % 27 for value in numerators):
        return None
    return tuple(value // 27 for value in numerators)


def c27_boxed_join_exists(q: int, h: int, reps: list[tuple[int, int]]) -> bool:
    """Small-h exact boxed C_27 nested join check."""
    for z1 in reps:
        if not gaussian_eo(z1):
            continue
        for z3 in reps:
            if not gaussian_oe(z3) or gaussian_residue(z1, 27) != gaussian_residue(z3, 27):
                continue
            for z9 in reps:
                if not gaussian_oe(z9) or gaussian_residue(z1, 9) != gaussian_residue(z9, 9):
                    continue
                for z27 in reps:
                    if not gaussian_oe(z27) or gaussian_residue(z1, 3) != gaussian_residue(z27, 3):
                        continue
                    avec = inverse_u27((z1[0], z3[0], z9[0], z27[0]))
                    bvec = inverse_u27((z1[1], z3[1], z9[1], z27[1]))
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


def factor_residue_signature(n: int, modulus: int) -> str:
    pieces = []
    for p, e in factor(n).items():
        suffix = "" if e == 1 else f"^{e}"
        pieces.append(f"{p % modulus}{suffix}")
    return "*".join(pieces)


def sqrt21_representations(
    q: int,
) -> list[tuple[tuple[int, int], tuple[int, int]]]:
    """Pairs alpha,beta in Z[eta], eta^2=eta+5, with alpha^2+beta^2=q."""
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
                    out.append(((a, b), (c, d)))
    return sorted(set(out))


def inverse_c21_components(
    L1: int,
    L3: int,
    L7: int,
    comp21: tuple[int, int],
) -> tuple[int, int, int, int, int] | None:
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


def c21_side_candidates(
    domains: list[list[int]],
    reps_z: list[tuple[int, int]],
    reps_k: list[tuple[tuple[int, int], tuple[int, int]]],
) -> dict[tuple[int, int, int, tuple[int, int]], tuple[int, ...]]:
    z_mates: dict[int, list[int]] = {}
    for x, y in reps_z:
        z_mates.setdefault(x, []).append(y)
    k_halves = sorted({alpha for alpha, _beta in reps_k})
    domain_sets = [set(dom) for dom in domains]
    out: dict[tuple[int, int, int, tuple[int, int]], tuple[int, ...]] = {}
    for L1, L3, L7 in itertools.product(sorted(z_mates), repeat=3):
        for comp21 in k_halves:
            values = inverse_c21_components(L1, L3, L7, comp21)
            if values is None:
                continue
            if all(values[i] in domain_sets[i] for i in range(5)):
                out[(L1, L3, L7, comp21)] = values
    return out


def c21_boxed_join_status(q: int, h: int) -> tuple[bool, int, int, str]:
    """Return boxed join status for the C_21 sqrt21 component criterion."""
    reps_z = gaussian_representations(q)
    if not reps_z:
        return False, 0, 0, "no_integer_norm_rep"
    reps_k = sqrt21_representations(q)
    if not reps_k:
        return False, 0, 0, "no_sqrt21_norm_rep"

    a0_domain = [v for v in range(-(h - 1), h) if v % 2 == 0]
    odd = [v for v in range(-h, h + 1) if v % 2 != 0]
    a_domains = [a0_domain, odd, odd, odd, odd]
    b_domains = [odd, odd, odd, odd, odd]
    side_a = c21_side_candidates(a_domains, reps_z, reps_k)
    side_b = c21_side_candidates(b_domains, reps_z, reps_k)
    if not side_a or not side_b:
        return False, len(side_a), len(side_b), "no_side_vector"

    z_mates: dict[int, list[int]] = {}
    for x, y in reps_z:
        z_mates.setdefault(x, []).append(y)
    k_mates: dict[tuple[int, int], list[tuple[int, int]]] = {}
    for alpha, beta in reps_k:
        k_mates.setdefault(alpha, []).append(beta)
    for L1, L3, L7, alpha in side_a:
        for M1 in z_mates[L1]:
            for M3 in z_mates[L3]:
                for M7 in z_mates[L7]:
                    for beta in k_mates.get(alpha, []):
                        if (M1, M3, M7, beta) in side_b:
                            return True, len(side_a), len(side_b), "sat_boxed"
    return False, len(side_a), len(side_b), "component_join_unsat"


def two_orbit_scalar_status(q: int, tp: int, h: int) -> tuple[bool, str]:
    """Exact transitive two-orbit scalar firing status."""
    c_limit = min(h, math.isqrt(q // (tp - 1)))
    odd_c_values = [v for v in range(-c_limit, c_limit + 1) if v % 2 != 0]
    left: dict[tuple[int, int], list[tuple[int, int]]] = {}
    for c in odd_c_values:
        rem = q - (tp - 1) * c * c
        if rem < 0:
            continue
        a0_limit = min(h - 1, math.isqrt(rem))
        for a0 in range(-a0_limit, a0_limit + 1):
            if a0 % 2 != 0:
                continue
            paf_a = 2 * a0 * c + (tp - 2) * c * c
            sq_a = a0 * a0 + (tp - 1) * c * c
            left.setdefault((paf_a, sq_a), []).append((a0, c))
    for d in odd_c_values:
        rem = q - (tp - 1) * d * d
        if rem < 0:
            continue
        b0_limit = min(h, math.isqrt(rem))
        for b0 in range(-b0_limit, b0_limit + 1):
            if b0 % 2 == 0:
                continue
            paf_b = 2 * b0 * d + (tp - 2) * d * d
            sq_b = b0 * b0 + (tp - 1) * d * d
            if left.get((-paf_b, q - sq_b)):
                return False, "scalar_sat"
    return True, "scalar_unsat"


def two_orbit_scalar_tuples(q: int, tp: int, h: int) -> list[tuple[int, int, int, int]]:
    """All boxed/parity-valid scalar tuples witnessing two-orbit local SAT."""
    c_limit = min(h, math.isqrt(q // (tp - 1)))
    odd_c_values = [v for v in range(-c_limit, c_limit + 1) if v % 2 != 0]
    left: dict[tuple[int, int], list[tuple[int, int]]] = {}
    for c in odd_c_values:
        rem = q - (tp - 1) * c * c
        if rem < 0:
            continue
        a0_limit = min(h - 1, math.isqrt(rem))
        for a0 in range(-a0_limit, a0_limit + 1):
            if a0 % 2 != 0:
                continue
            paf_a = 2 * a0 * c + (tp - 2) * c * c
            sq_a = a0 * a0 + (tp - 1) * c * c
            left.setdefault((paf_a, sq_a), []).append((a0, c))

    out: list[tuple[int, int, int, int]] = []
    for d in odd_c_values:
        rem = q - (tp - 1) * d * d
        if rem < 0:
            continue
        b0_limit = min(h, math.isqrt(rem))
        for b0 in range(-b0_limit, b0_limit + 1):
            if b0 % 2 == 0:
                continue
            paf_b = 2 * b0 * d + (tp - 2) * d * d
            sq_b = b0 * b0 + (tp - 1) * d * d
            for a0, c in left.get((-paf_b, q - sq_b), []):
                out.append((a0, c, b0, d))
    return sorted(out)


def inverse_p3_components(values: tuple[int, int, int]) -> tuple[int, int, int] | None:
    r1, r3, r9 = values
    nums = (
        r1 + 2 * r3 + 6 * r9,
        r1 - r3,
        r1 + 2 * r3 - 3 * r9,
    )
    if any(num % 9 for num in nums):
        return None
    return (nums[0] // 9, nums[1] // 9, nums[2] // 9)


def p3_gaussian_status(q: int, h: int) -> tuple[bool, str]:
    """Exact p=3 full-unit Gaussian component firing status."""
    reps = gaussian_representations(q)
    if not reps:
        return True, "no_norm_rep"
    a_domains = [
        {v for v in range(-(h - 1), h) if v % 2 == 0},
        {v for v in range(-h, h + 1) if v % 2 != 0},
        {v for v in range(-h, h + 1) if v % 2 != 0},
    ]
    b_domains = [
        {v for v in range(-h, h + 1) if v % 2 != 0}
        for _ in range(3)
    ]
    for component_reps in itertools.product(reps, repeat=3):
        avec = inverse_p3_components(tuple(pair[0] for pair in component_reps))
        if avec is None:
            continue
        bvec = inverse_p3_components(tuple(pair[1] for pair in component_reps))
        if bvec is None:
            continue
        if all(avec[i] in a_domains[i] for i in range(3)) and all(
            bvec[i] in b_domains[i] for i in range(3)
        ):
            return False, "component_sat"
    return True, "component_unsat"


def sqrt5_representations(
    q: int,
) -> list[tuple[tuple[int, int], tuple[int, int]]]:
    """Pairs alpha,beta in Z[u], u^2+u-1=0, with alpha^2+beta^2=q."""
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


def p5_side_candidates(
    domains: list[list[int]],
    reps_z: list[tuple[int, int]],
    reps_k: list[tuple[tuple[int, int], tuple[int, int]]],
) -> dict[tuple[int, tuple[int, int], tuple[int, int]], tuple[int, ...]]:
    domain_sets = [set(dom) for dom in domains]
    z_halves = sorted({x for x, _y in reps_z})
    k_halves = sorted({alpha for alpha, _beta in reps_k})
    out: dict[tuple[int, tuple[int, int], tuple[int, int]], tuple[int, ...]] = {}
    for L in z_halves:
        for comp5 in k_halves:
            for comp25 in k_halves:
                values = inverse_p5_components(L, comp5, comp25)
                if values is None:
                    continue
                if all(values[i] in domain_sets[i] for i in range(5)):
                    out[(L, comp5, comp25)] = values
    return out


def p5_sqrt5_status(q: int, h: int) -> tuple[bool, str]:
    """Exact p=5 sqrt5 component firing status."""
    reps_z = gaussian_representations(q)
    if not reps_z:
        return True, "no_integer_norm_rep"
    reps_k = sqrt5_representations(q)
    if not reps_k:
        return True, "no_sqrt5_norm_rep"
    a0_domain = [v for v in range(-(h - 1), h) if v % 2 == 0]
    odd = [v for v in range(-h, h + 1) if v % 2 != 0]
    side_a = p5_side_candidates([a0_domain, odd, odd, odd, odd], reps_z, reps_k)
    side_b = p5_side_candidates([odd, odd, odd, odd, odd], reps_z, reps_k)
    if not side_a or not side_b:
        return True, "no_side_vector"

    z_mates: dict[int, list[int]] = {}
    for x, y in reps_z:
        z_mates.setdefault(x, []).append(y)
    k_mates: dict[tuple[int, int], list[tuple[int, int]]] = {}
    for alpha, beta in reps_k:
        k_mates.setdefault(alpha, []).append(beta)
    for L, comp5, comp25 in side_a:
        for M in z_mates[L]:
            for comp5_b in k_mates.get(comp5, []):
                for comp25_b in k_mates.get(comp25, []):
                    if (M, comp5_b, comp25_b) in side_b:
                        return False, "component_sat"
    return True, "component_join_unsat"


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


@lru_cache(maxsize=None)
def p7_cubic_status(q: int, h: int) -> tuple[bool, str]:
    """Exact p=7 cubic component firing status."""
    reps_z = gaussian_representations(q)
    if not reps_z:
        return True, "no_integer_norm_rep"
    reps_k = cubic7_representations(q)
    if not reps_k:
        return True, "no_cubic_norm_rep"
    a0_domain = [v for v in range(-(h - 1), h) if v % 2 == 0]
    odd = [v for v in range(-h, h + 1) if v % 2 != 0]
    side_a = p7_side_candidates(
        [a0_domain, odd, odd, odd, odd, odd, odd], reps_z, reps_k
    )
    side_b = p7_side_candidates([odd] * 7, reps_z, reps_k)
    if not side_a or not side_b:
        return True, "no_side_vector"

    z_mates: dict[int, list[int]] = {}
    for x, y in reps_z:
        z_mates.setdefault(x, []).append(y)
    k_mates: dict[tuple[int, int, int], list[tuple[int, int, int]]] = {}
    for alpha, beta in reps_k:
        k_mates.setdefault(alpha, []).append(beta)
    for L, comp7, comp49 in side_a:
        for M in z_mates[L]:
            for comp7_b in k_mates.get(comp7, []):
                for comp49_b in k_mates.get(comp49, []):
                    if (M, comp7_b, comp49_b) in side_b:
                        return False, "component_sat"
    return True, "component_join_unsat"


@lru_cache(maxsize=None)
def c51_quartic_status(q: int, tp: int) -> tuple[bool, str]:
    """Exact C_51 quartic component firing status for the written criterion."""
    with contextlib.redirect_stdout(StringIO()):
        alg = build_marginal_algebra(q, tp)
        roles = c51_orbit_roles(alg)
        reps_z = gaussian_representations(q)
        z_mates: dict[int, list[int]] = {}
        for x, y in reps_z:
            z_mates.setdefault(x, []).append(y)
        halves, k_mates = quartic17_two_square_pairs(q)
    if not reps_z:
        return True, "no_integer_norm_rep"
    if not halves:
        return True, "no_quartic_norm_rep"

    uniform = [half for half in halves if len({coord % 2 for coord in half}) == 1]

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
        out: dict[
            tuple[int, int, tuple[int, ...], tuple[int, ...]], tuple[int, ...]
        ] = {}
        for lam1, a, big_p in cand_a:
            key = (
                big_p % 3,
                tuple((a[k] + big_p) % 3 for k in range(4)),
            )
            for lam3, b, _big_c in buckets.get(key, []):
                values = c51_inverse(roles, lam1, lam3, a, b)
                if values is None:
                    continue
                if all(values[i] in domain_sets[i] for i in range(len(values))):
                    out[(lam1, lam3, a, b)] = values
        return out

    side_a = side_candidates(alg.a_domains)
    side_b = side_candidates(alg.b_domains)
    if not side_a or not side_b:
        return True, "no_side_vector"
    for lam1, lam3, a, b in side_a:
        for lam1_b in z_mates[lam1]:
            for lam3_b in z_mates[lam3]:
                for a_b in k_mates.get(a, []):
                    for b_b in k_mates.get(b, []):
                        if (lam1_b, lam3_b, a_b, b_b) in side_b:
                            return False, "component_sat"
    return True, "component_join_unsat"


def blind_spot_qs(qmax: int) -> list[int]:
    """Composite multi-prime q surviving two-squares and self-conjugacy."""
    return [
        q for q in range(5, qmax + 1, 4)
        if is_composite(q) and is_multi_prime(q)
        and not two_squares_fail(q) and not selfconj_kill(q, (q + 1) // 2)
    ]


def is_composite(n: int) -> bool:
    return sum(factor(n).values()) >= 2


def is_multi_prime(n: int) -> bool:
    return len(factor(n)) >= 2


def is_prime_number(n: int) -> bool:
    fac = factor(n)
    return len(fac) == 1 and next(iter(fac.values())) == 1


def divisor_shape(n: int) -> str:
    fac = factor(n)
    if len(fac) == 1:
        (_p, e), = fac.items()
        return "prime" if e == 1 else "prime_power"
    if all(e == 1 for e in fac.values()):
        return "squarefree_composite"
    return "mixed_composite"


def prime_square_base(n: int) -> int | None:
    fac = factor(n)
    if len(fac) != 1:
        return None
    (p, e), = fac.items()
    return p if e == 2 else None


@lru_cache(maxsize=None)
def cached_v_group(q: int) -> tuple[int, list[int], bool]:
    return v_group(q)


@lru_cache(maxsize=None)
def signed_multiplier_elements(q: int) -> tuple[tuple[int, int], ...]:
    """Elements of <M(q),(+1,-1)> as (eps, decimation mod t)."""
    t = (q + 1) // 2
    mod = 4 * t
    subs = [cyclic_sub(p, mod) for p in factor(q)]
    M = reduce(lambda a, b: a & b, subs)
    sym = crt2(1, 4, (t - 1) % t, t)
    Mp = M | {(s * sym) % mod for s in M}
    return tuple(
        sorted((-1 if s % 4 == 3 else 1, s % t) for s in Mp)
    )


def signed_r_patterns(t: int, elements: tuple[tuple[int, int], ...]) -> list[list[tuple[int, int]]] | None:
    """Signed nonzero orbits for r at the full torus.

    Returns None if an element fixes a nonzero index with negative sign, or if
    the same index is reached with both signs from one representative.
    """
    seen: set[int] = set()
    patterns: list[list[tuple[int, int]]] = []
    for rep in range(1, t):
        if rep in seen:
            continue
        values: dict[int, int] = {}
        for eps, u in elements:
            j = (u * rep) % t
            old = values.get(j)
            if old is not None and old != eps:
                return None
            values[j] = eps
        seen.update(values)
        patterns.append(sorted(values.items()))
    return patterns


@lru_cache(maxsize=None)
def signed_full_torus_status(q: int, cap: int = 22) -> tuple[bool, str] | None:
    """Exact signed full-torus sign join.

    At h=1 the boxes force r_j,s_j in {+-1} off the r-origin.  The signed
    multiplier equations give signed orbits for r and ordinary decimation
    orbits for s.  Returns True when the exact join is empty.
    """
    t, V, all_plus = cached_v_group(q)
    if all_plus:
        return None
    elements = signed_multiplier_elements(q)
    r_patterns = signed_r_patterns(t, elements)
    if r_patterns is None:
        return True, "negative_stabilizer"
    s_orbits = orbits(t, V)
    kr = len(r_patterns)
    ks = len(s_orbits)
    if kr > cap or ks > cap:
        return None
    reps = sorted({min(o) for o in s_orbits if o != [0]})

    nr = 1 << kr
    r_bits = ((np.arange(nr)[:, None] >> np.arange(kr)[None, :]) & 1)
    r_signs = np.where(r_bits == 1, 1, -1).astype(np.int8)
    R = np.zeros((nr, t), dtype=np.int8)
    for col, pattern in enumerate(r_patterns):
        for j, eps in pattern:
            R[:, j] = eps * r_signs[:, col]
    Pr = paf_vectors(R, t, reps)

    ns = 1 << ks
    s_bits = ((np.arange(ns)[:, None] >> np.arange(ks)[None, :]) & 1)
    s_signs = np.where(s_bits == 1, 1, -1).astype(np.int8)
    S = np.zeros((ns, t), dtype=np.int8)
    for oi, orbit in enumerate(s_orbits):
        for j in orbit:
            S[:, j] = s_signs[:, oi]
    Ps = paf_vectors(S, t, reps)

    rset = {row.astype(np.int32).tobytes() for row in Pr}
    for row in Ps:
        if (-row).astype(np.int32).tobytes() in rset:
            return False, "signed_full_torus_sat"
    return True, "signed_full_torus_join_unsat"


def signature(q: int, tp: int) -> dict:
    t, V, all_plus = cached_v_group(q)
    h = t // tp
    Vp = sorted({v % tp for v in V})
    orbit_list = orbits(tp, Vp)
    sizes = sorted((len(o) for o in orbit_list), reverse=True)
    return {
        "q": q,
        "t": t,
        "tp": tp,
        "h": h,
        "all_plus": all_plus,
        "V_size": len(V),
        "Vp": Vp,
        "Vp_size": len(Vp),
        "n_orbits": len(orbit_list),
        "sizes": sizes,
    }


def prime_square_pm1_lift_base(sig: dict) -> int | None:
    """Return p for the prime-square lift pattern V'={u: u=+-1 mod p}.

    For t'=p^2 this orbit shape has (p-1)/2 unit orbits of size 2p,
    (p-1)/2 nonzero p-multiple orbits of size 2, and the zero orbit.
    The q=549, t'=25 certificate is the p=5 member of this family.
    """
    p = prime_square_base(sig["tp"])
    if p is None or p == 2 or not sig["all_plus"]:
        return None
    if len(sig["Vp"]) != 2 * p:
        return None
    if sorted({u % p for u in sig["Vp"]}) != [1, p - 1]:
        return None
    expected = sorted(
        [1] + [2 * p] * ((p - 1) // 2) + [2] * ((p - 1) // 2),
        reverse=True,
    )
    return p if sig["sizes"] == expected else None


def family(sig: dict) -> str:
    if not sig["all_plus"]:
        return "signed"
    if sig["n_orbits"] == 2:
        return "two_orbit"
    if prime_square_pm1_lift_base(sig) is not None:
        return "prime_square_pm1_lift"
    if sig["h"] == 1:
        return "full_torus"
    if sig["n_orbits"] <= 12:
        return "compact_middle"
    if sig["h"] <= 3:
        return "small_fiber_many_orbits"
    if sig["sizes"] and sig["sizes"][0] >= 16:
        return "large_orbit"
    return "wide_middle"


def candidates(q: int, proper: bool) -> list[dict]:
    t, _V, _all_plus = cached_v_group(q)
    out = []
    for tp in divisors(t):
        if tp <= 1:
            continue
        if proper and tp == t:
            continue
        out.append(signature(q, tp))
    return out


def best_signature(q: int, proper: bool) -> dict | None:
    sigs = candidates(q, proper)
    if not sigs:
        return None
    # Prefer theorem-shaped signatures, then fewer orbits, then smaller h.
    rank = {
        "two_orbit": 0,
        "prime_square_pm1_lift": 1,
        "compact_middle": 2,
        "small_fiber_many_orbits": 3,
        "large_orbit": 4,
        "wide_middle": 5,
        "full_torus": 6,
        "signed": 7,
    }
    return min(sigs, key=lambda s: (rank[family(s)], s["n_orbits"], s["h"], s["tp"]))


def compact_symbolic_flag(sig: dict, route: str) -> str:
    """Heuristic label for the next exact component-enumeration laboratory."""
    if route == "exact_orbit_mitm":
        return "exact orbit certificate"
    if route in {
        "quartic_component",
        "p5_sqrt5_component",
        "c21_sqrt21_component",
        "c21_join_firing",
        "c27_nested_component",
        "c27_residue_firing",
        "c27_boxed_firing",
        "prime_subtorus_join_firing",
    }:
        return "model"
    if sig["n_orbits"] <= 5:
        return "small exact-join target"
    if (
        divisor_shape(sig["tp"]) in {"prime", "prime_power"}
        and sig["n_orbits"] <= 8
    ):
        return "component target"
    return "inspect"


def fmt_list(values: list[int] | tuple[int, ...]) -> str:
    return ",".join(str(v) for v in values)


def compact_component_ladder(q: int, tp: int) -> str:
    """Research ladder suggested by the component field cut out by V'."""
    if (q, tp) in {(377, 27), (1025, 27)}:
        return "u27_rational"
    if (q, tp) in {(545, 21), (629, 21)}:
        return "sqrt21_pair"
    if (q, tp) == (1189, 17):
        return "quadratic"
    if (q, tp) in {(1105, 79), (1937, 57)}:
        return "cubic"
    if (q, tp) == (425, 71):
        return "degree_7"
    if (q, tp) == (1325, 51):
        return "quartic_model"
    return "unclassified"


def signature_lane(sig: dict) -> str:
    """The theorem-facing lane for a signature, finer than the broad family.

    Family-level accounting is too coarse once only some compact-middle
    signatures have quantified firing criteria.  This lane is used only for
    coverage bookkeeping; it does not assert that the criterion fires for the
    particular q.
    """
    if (
        sig["tp"] == 27
        and sig["Vp_size"] == 18
        and sig["sizes"] == [18, 6, 2, 1]
    ):
        return "c27_full_unit"
    if (
        sig["tp"] == 21
        and sig["Vp"] == [1, 4, 5, 16, 17, 20]
        and sig["sizes"] == [6, 6, 6, 2, 1]
    ):
        return "c21_sqrt21"
    if (
        sig["tp"] == 49
        and sig["Vp_size"] == 42
        and sig["sizes"] == [42, 6, 1]
    ):
        return "c49_full_unit"
    if (
        sig["tp"] == 57
        and sig["Vp"] == C57_EXPECTED_VP
        and sig["sizes"] == [18, 18, 18, 2, 1]
    ):
        return "c57_sqrt57"
    if sig["n_orbits"] == 2 and sig["all_plus"]:
        return "two_orbit"
    p = prime_square_pm1_lift_base(sig)
    if p in {3, 5, 7}:
        return f"prime_square_pm1_lift_p{p}"
    if (
        divisor_shape(sig["tp"]) == "prime"
        and sig["all_plus"]
        and sig["n_orbits"] > 2
    ):
        return f"prime_subtorus_degree_{sig['n_orbits'] - 1}"
    if (
        sig["tp"] == 51
        and sig["Vp"] == [1, 4, 13, 16, 35, 38, 47, 50]
        and sig["sizes"] == [8, 8, 8, 8, 4, 4, 4, 4, 2, 1]
    ):
        return "c51_quartic"
    return family(sig)


LANE_LEVEL = {
    "c27_full_unit": "quantified_firing",
    "c21_sqrt21": "quantified_firing",
    "c49_full_unit": "quantified_firing",
    "c57_sqrt57": "quantified_firing",
    "two_orbit": "quantified_firing",
    "prime_square_pm1_lift_p3": "quantified_firing",
    "prime_square_pm1_lift_p5": "quantified_firing",
    "prime_square_pm1_lift_p7": "quantified_firing",
    "c51_quartic": "quantified_firing",
}


@lru_cache(maxsize=None)
def prime_subtorus_point_prediction(q: int, tp: int) -> tuple[float, int]:
    """Predicted true embedding-region point count and degree at (q, ell)."""
    t, V, _all_plus = cached_v_group(q)
    Vp = sorted({v % tp for v in V})
    cosets, _index = prime_subtorus_cosets(tp, Vp)
    degree = len(cosets)
    return prime_period_lattice_prediction(q, tp, degree), degree


@lru_cache(maxsize=None)
def prime_subtorus_reduced_head_states(q: int, tp: int) -> int:
    """Reduced coordinate-walk head states at (q, ell), no enumeration."""
    t, V, _all_plus = cached_v_group(q)
    Vp = sorted({v % tp for v in V})
    cosets, _index = prime_subtorus_cosets(tp, Vp)
    emb = prime_period_embedding_matrix(prime_period_values(tp, cosets))
    _red, _transform, _caps, _solve_idx, n_heads = prime_period_reduced_work(q, emb)
    return n_heads


@lru_cache(maxsize=None)
def prime_subtorus_promotable(q: int, tp: int, degree: int) -> bool:
    """Honest evaluability gate for the prime sub-torus period join.

    True exactly when the report will evaluate (and therefore may promote)
    the written criterion at this node: degree within the evidence ceiling
    and predicted true embedding-region point count within the enumeration cap.
    Nodes that fail the point-count gate decline once with a printed reason.
    """
    if degree > PRIME_SUBTORUS_MAX_DEGREE:
        return False
    if q <= PRIME_SUBTORUS_LEDGER_QMAX and degree > PRIME_SUBTORUS_LEDGER_MAX_DEGREE:
        return False
    predicted, checked_degree = prime_subtorus_point_prediction(q, tp)
    assert checked_degree == degree
    if predicted <= PRIME_SUBTORUS_POINT_CAP:
        n_heads = prime_subtorus_reduced_head_states(q, tp)
        if n_heads > PRIME_SUBTORUS_HEAD_STATE_CAP:
            print(
                f"  [prime-subtorus] q={q} ell={tp} degree={degree} "
                f"DECLINED: reduced head states={n_heads:,} > cap "
                f"{PRIME_SUBTORUS_HEAD_STATE_CAP:,}",
                file=sys.stderr,
                flush=True,
            )
            return False
        return True
    print(f"  [prime-subtorus] q={q} ell={tp} degree={degree} DECLINED: "
          f"predicted lattice points~{format_point_prediction(predicted)} "
          f"> cap {PRIME_SUBTORUS_POINT_CAP:,}",
          file=sys.stderr, flush=True)
    return False


def lane_level_name(lane: str, q: int | None = None,
                    tp: int | None = None) -> str | None:
    """Proof level of a lane; (q, tp) context enables the degree-4/5 box gate.

    Without context, prime sub-torus degrees 4..PRIME_SUBTORUS_MAX_DEGREE are
    conservatively reported as component criteria, because their promotion is
    per-instance (the box gate), not per-lane.
    """
    if lane.startswith("prime_subtorus_degree_"):
        degree = int(lane.rsplit("_", 1)[1])
        if degree <= 3:
            return "quantified_firing"
        if (
            degree <= PRIME_SUBTORUS_MAX_DEGREE
            and q is not None
            and tp is not None
            and prime_subtorus_promotable(q, tp, degree)
        ):
            return "quantified_firing"
        return "component_criterion"
    return LANE_LEVEL.get(lane)


@lru_cache(maxsize=None)
def prime_subtorus_status(q: int, tp: int) -> tuple[bool, str] | None:
    """Exact prime sub-torus component firing status (cor:prime-subtorus-firing).

    Returns None when the period embedding box is refused, in which case the
    lane stays an unevaluated component criterion for this (q, t').
    """
    with contextlib.redirect_stdout(StringIO()):
        alg = build_marginal_algebra(q, tp)
        res = prime_subtorus_join(alg, PRIME_SUBTORUS_POINT_CAP)
    if res["status"] == "REFUSED":
        print(f"  [prime-subtorus] q={q} ell={tp} degree={res['degree']} "
              f"REFUSED: predicted lattice points~"
              f"{format_point_prediction(res['predicted_lattice_points'])} "
              f"> cap {PRIME_SUBTORUS_POINT_CAP:,}",
              file=sys.stderr, flush=True)
        return None
    return res["status"] == "UNSAT", res["mechanism"]


@lru_cache(maxsize=None)
def full_torus_rowsum_status(q: int, tp: int) -> tuple[bool, str] | None:
    """Prime-t full-torus trivial-character firing.

    At h=1 the trivial-character equation on V-invariant sign rows reduces
    to w*(sA^2+sigma^2) = 2*(d-sigma) with sA = sigma = d (mod 2) and
    |sA|,|sigma| <= d.  Above the threshold w >= d+2, equivalently
    (w-1)^2 >= t, no solution exists (thm:full-torus-rowsum, mechanism
    rowsum_unsat); below it, exact emptiness of the O(d) solution set
    still fires (cor:full-torus-exact-char, mechanism trivial_char_unsat).
    Returns None only when an admissible solution exists.
    """
    t, V, all_plus = cached_v_group(q)
    if tp != t or not all_plus or not is_prime_number(t):
        return None
    w = len({v % t for v in V})
    if (w - 1) ** 2 >= t:
        return True, "rowsum_unsat"
    d = (t - 1) // w
    for sigma in range(-d, d + 1):
        if (sigma - d) % 2:
            continue
        rhs = 2 * (d - sigma)
        if rhs < 0 or rhs % w:
            continue
        rem = rhs // w - sigma * sigma
        if rem < 0:
            continue
        s = math.isqrt(rem)
        for cand in (s, s + 1):
            if cand * cand == rem and (cand - d) % 2 == 0 and cand <= d:
                return None
    return True, "trivial_char_unsat"


def full_torus_integer_status(q: int, tp: int) -> tuple[bool, str] | None:
    """Exact full-torus orbit-value firing status.

    This is used only for h=1 all-plus full-torus branches.  In that case the
    marginal boxes force sign rows, so complete orbit-value MITM is the
    appropriate finite criterion even when the period embedding box is too
    broad for prime_subtorus_join().
    """
    with contextlib.redirect_stdout(StringIO()):
        alg = build_marginal_algebra(q, tp)
        res = exact_integer_mitm(alg, FULL_TORUS_INTEGER_CAP)
    if res is None:
        return None
    return (False, "integer_orbit_join_sat") if res else (
        True,
        "integer_orbit_join_unsat",
    )


@lru_cache(maxsize=None)
def exact_integer_status(
    q: int,
    tp: int,
    cap: int = SECONDARY_INTEGER_CAP,
) -> tuple[bool, str] | None:
    """Exact orbit-value marginal status under an assignment cap."""
    with contextlib.redirect_stdout(StringIO()):
        alg = build_marginal_algebra(q, tp)
        res = exact_integer_mitm(alg, cap)
    if res is None:
        return None
    return (False, "integer_orbit_join_sat") if res else (
        True,
        "integer_orbit_join_unsat",
    )


def h3_side_states(
    nonzero_sizes: tuple[int, ...],
    origin_values: tuple[int, ...],
    target_support: int,
    count_origin_support: bool,
    label: str = "",
) -> dict[int, set[int]] | None:
    """Possible (support -> row sums) for an h=3 marginal side.

    Support means the number of fiber cells whose orbit value has magnitude 3.
    For the A side, the origin value is forced to +-2 and does not contribute
    to this support.  For the B side, the origin value is odd, so +-3
    contributes one support cell.

    Visibility contract: this DP is the only stage that can grind for
    minutes, so it self-reports.  When a run exceeds 5 s it prints progress
    (step, state count, elapsed) to stderr every ~5 s, and it DECLINES with
    a printed reason on the state cap or the wall-clock budget -- a None
    return is therefore always attributable, and no node can run unbounded.
    """
    start = time.monotonic()
    next_report = start + 5.0
    states: set[tuple[int, int]] = set()
    for value in origin_values:
        support = 1 if count_origin_support and abs(value) == 3 else 0
        if support <= target_support:
            states.add((support, value))
    for step, size in enumerate(nonzero_sizes, 1):
        next_states: set[tuple[int, int]] = set()
        for support, row_sum in states:
            for value in (-3, -1, 1, 3):
                next_support = support + (size if abs(value) == 3 else 0)
                if next_support <= target_support:
                    next_states.add((next_support, row_sum + size * value))
        if len(next_states) > H3_AUGMENTATION_STATE_CAP:
            print(f"  [h3-dp]{label} DECLINED at step "
                  f"{step}/{len(nonzero_sizes)}: states="
                  f"{len(next_states):,} > cap {H3_AUGMENTATION_STATE_CAP:,}",
                  file=sys.stderr, flush=True)
            return None
        now = time.monotonic()
        if now - start > H3_NODE_TIME_BUDGET_S:
            print(f"  [h3-dp]{label} DECLINED at step "
                  f"{step}/{len(nonzero_sizes)}: exceeded time budget "
                  f"{H3_NODE_TIME_BUDGET_S}s (states={len(next_states):,})",
                  file=sys.stderr, flush=True)
            return None
        if now >= next_report:
            rate = step / (now - start)
            eta = (len(nonzero_sizes) - step) / rate if rate else float("inf")
            print(f"  [h3-dp]{label} step {step}/{len(nonzero_sizes)} "
                  f"states={len(next_states):,} elapsed={now - start:.0f}s "
                  f"eta>={eta:.0f}s (state growth may extend this)",
                  file=sys.stderr, flush=True)
            next_report = now + 5.0
        states = next_states
    by_support: dict[int, set[int]] = {}
    for support, row_sum in states:
        by_support.setdefault(support, set()).add(row_sum)
    return by_support


def h3_support_sets(
    nonzero_sizes: tuple[int, ...],
    target_support: int,
    count_origin_support: bool,
) -> set[int]:
    """Support totals possible before considering row-sum augmentation."""
    states = {1} if count_origin_support else {0}
    if count_origin_support:
        states.add(0)
    for size in nonzero_sizes:
        next_states = set(states)
        for support in states:
            next_support = support + size
            if next_support <= target_support:
                next_states.add(next_support)
        states = next_states
    return states


@lru_cache(maxsize=None)
def h3_node_sizes(q: int, tp: int) -> tuple[int, ...] | None:
    """Nonzero V'-orbit sizes at (q, t'), without structure constants.

    The h=3 status checks only need the fiber size and orbit sizes;
    building the full marginal algebra (n^3 structure table) for them is
    prohibitively slow and memory-heavy at large t'.  Returns None unless
    h == 3 and the multiplier signs are all +1.
    """
    t, V, all_plus = cached_v_group(q)
    if not all_plus or tp <= 1 or t % tp or t // tp != 3:
        return None
    Vp = sorted({v % tp for v in V})
    return tuple(
        len(orb) for orb in orbits(tp, Vp) if 0 not in orb
    )


@lru_cache(maxsize=None)
def h3_support_augmentation_status(q: int, tp: int) -> tuple[bool, str] | None:
    """Necessary h=3 support and augmentation obstruction.

    When h=3, the zero-shift energy equation forces A_0=+-2 and exactly
    (t'-1)/2 cells among A off the origin and all of B to have magnitude 3.
    The trivial-character equation then requires row sums X,Y with X^2+Y^2=q.
    If either finite join is empty, the marginal cannot exist.
    """
    nonzero_sizes = h3_node_sizes(q, tp)
    if nonzero_sizes is None:
        return None
    target_support = (tp - 1) // 2
    a_supports = h3_support_sets(
        nonzero_sizes,
        target_support,
        count_origin_support=False,
    )
    b_supports = h3_support_sets(
        nonzero_sizes,
        target_support,
        count_origin_support=True,
    )
    support_possible = any(
        (target_support - a_support) in b_supports
        for a_support in a_supports
    )
    if not support_possible:
        return True, "h3_support_sum_impossible"

    if len(nonzero_sizes) * target_support > H3_AUGMENTATION_NODE_GUARD:
        print(f"  [h3-dp] q={q} t'={tp} DECLINED by pre-guard: "
              f"orbits x target = {len(nonzero_sizes) * target_support:,} "
              f"> {H3_AUGMENTATION_NODE_GUARD:,}",
              file=sys.stderr, flush=True)
        return None

    a_states = h3_side_states(
        nonzero_sizes,
        origin_values=(-2, 2),
        target_support=target_support,
        count_origin_support=False,
        label=f" q={q} t'={tp} A",
    )
    b_states = h3_side_states(
        nonzero_sizes,
        origin_values=(-3, -1, 1, 3),
        target_support=target_support,
        count_origin_support=True,
        label=f" q={q} t'={tp} B",
    )
    if a_states is None or b_states is None:
        return None

    for a_support, a_sums in a_states.items():
        b_sums = b_states.get(target_support - a_support)
        if not b_sums:
            continue
        for a_sum in a_sums:
            remaining = q - a_sum * a_sum
            if remaining < 0:
                continue
            b_abs = math.isqrt(remaining)
            if b_abs * b_abs == remaining and (
                b_abs in b_sums or -b_abs in b_sums
            ):
                return False, "h3_support_augmentation_possible"
    return True, "h3_support_augmentation_impossible"


def h3_support_augmentation_detail(q: int, tp: int) -> dict | None:
    """Diagnostic detail for the h=3 support/augmentation obstruction."""
    nonzero_sizes = h3_node_sizes(q, tp)
    if nonzero_sizes is None:
        return None
    target_support = (tp - 1) // 2
    a_states = h3_side_states(
        nonzero_sizes,
        origin_values=(-2, 2),
        target_support=target_support,
        count_origin_support=False,
    )
    b_states = h3_side_states(
        nonzero_sizes,
        origin_values=(-3, -1, 1, 3),
        target_support=target_support,
        count_origin_support=True,
    )
    a_supports = h3_support_sets(
        nonzero_sizes,
        target_support,
        count_origin_support=False,
    )
    b_supports = h3_support_sets(
        nonzero_sizes,
        target_support,
        count_origin_support=True,
    )
    support_pairs = sum(
        1 for a_support in a_supports
        if (target_support - a_support) in b_supports
    )
    witness = None
    if a_states is not None and b_states is not None:
        for a_support, a_sums in sorted(a_states.items()):
            b_sums = b_states.get(target_support - a_support)
            if not b_sums:
                continue
            for a_sum in sorted(a_sums):
                remaining = q - a_sum * a_sum
                if remaining < 0:
                    continue
                b_abs = math.isqrt(remaining)
                if b_abs * b_abs == remaining:
                    for b_sum in (b_abs, -b_abs):
                        if b_sum in b_sums:
                            witness = (a_support, a_sum, target_support - a_support, b_sum)
                            break
                if witness:
                    break
            if witness:
                break
    status = h3_support_augmentation_status(q, tp)
    fires, mechanism = status if status is not None else (
        False,
        "h3_augmentation_capped",
    )
    return {
        "q": q,
        "tp": tp,
        "h": alg.h,
        "n_orbits": len(alg.orbits),
        "nonzero_sizes": sorted(nonzero_sizes, reverse=True),
        "target_support": target_support,
        "a_support_counts": None if a_states is None else len(a_states),
        "b_support_counts": None if b_states is None else len(b_states),
        "support_pairs": support_pairs,
        "fires": fires,
        "mechanism": mechanism,
        "witness": witness,
    }


def secondary_marginal_status(sig: dict) -> tuple[bool, str] | None:
    """Secondary exact obstruction for local-pass q.

    These checks do not say the first local lane fires; they search another
    divisor for an exact marginal obstruction supplied by the same written
    marginal-algebra theorem.
    """
    lane = signature_lane(sig)
    if lane.startswith("prime_subtorus_degree_"):
        status = prime_subtorus_status(sig["q"], sig["tp"])
        if status is not None and status[0]:
            return status
    status = exact_integer_status(sig["q"], sig["tp"])
    if status is not None and status[0]:
        return status
    return None


def panel_finite_certificate(q: int) -> tuple[int, str] | None:
    """Return the existing finite panel certificate for q, when applicable."""
    row = PANEL_KILLS.get(q)
    if row is None:
        return None
    tp, _doc_orbits, route = row
    if route in FINITE_CERTIFICATE_ROUTES:
        return tp, route
    return None


def c27_firing_status(q: int, h: int) -> tuple[bool, str]:
    """Return whether the written C_27 firing criterion applies."""
    reps = gaussian_representations(q)
    eo_residues = {gaussian_residue(z, 27) for z in reps if gaussian_eo(z)}
    oe_residues = {gaussian_residue(z, 27) for z in reps if gaussian_oe(z)}
    residue_hits = eo_residues & oe_residues
    if not reps:
        return True, "no_norm_rep"
    if not residue_hits:
        return True, "no_residue_pair"
    if h >= 57:
        return False, "sat_auto_box"
    boxed = c27_boxed_join_exists(q, h, reps)
    return (False, "sat_boxed") if boxed else (True, "small_h_box_cut")


def c21_firing_status(q: int, h: int) -> tuple[bool, str]:
    """Return whether the written C_21 firing criterion applies."""
    boxed, _n_a, _n_b, mechanism = c21_boxed_join_status(q, h)
    return not boxed, mechanism


def c49_firing_status(q: int, h: int) -> tuple[bool, str]:
    """Return whether the written C_49 full-unit firing criterion applies.

    Same shape as the C_27 criterion at t'=49: nested congruences
    z1 == z7 (mod 49), z1 == z49 (mod 7), orientation z1 in G_eo(q) and
    z7, z49 in G_oe(q), fiber boxes.  Boxes are automatic for h >= 101
    (q = 98h-1 <= (h-1)^2), where a common eo/oe residue mod 49 already
    yields a witness via z7 = z49.
    """
    reps = gaussian_representations(q)
    if not reps:
        return True, "no_norm_rep"
    eo_residues = {gaussian_residue(z, 49) for z in reps if gaussian_eo(z)}
    oe_residues = {gaussian_residue(z, 49) for z in reps if gaussian_oe(z)}
    if not (eo_residues & oe_residues):
        return True, "no_residue_pair"
    if h >= 101:
        return False, "sat_auto_box"
    boxed = c49_boxed_join_exists(q, h, reps)
    return (False, "sat_boxed") if boxed else (True, "small_h_box_cut")


def c57_side_candidates(
    domains: list[list[int]],
    reps_z: list[tuple[int, int]],
    reps_k: list[tuple[tuple[int, int], tuple[int, int]]],
) -> dict[tuple[int, int, int, tuple[int, int]], tuple[int, ...]]:
    z_mates: dict[int, list[int]] = {}
    for x, y in reps_z:
        z_mates.setdefault(x, []).append(y)
    k_halves = sorted({alpha for alpha, _beta in reps_k})
    domain_sets = [set(dom) for dom in domains]
    out: dict[tuple[int, int, int, tuple[int, int]], tuple[int, ...]] = {}
    for L1, L3, L19 in itertools.product(sorted(z_mates), repeat=3):
        for comp57 in k_halves:
            values = inverse_c57_components(L1, L3, L19, comp57)
            if values is None:
                continue
            if all(values[i] in domain_sets[i] for i in range(5)):
                out[(L1, L3, L19, comp57)] = values
    return out


def c57_boxed_join_status(q: int, h: int) -> tuple[bool, int, int, str]:
    """Return boxed join status for the C_57 sqrt57 component criterion."""
    reps_z = gaussian_representations(q)
    if not reps_z:
        return False, 0, 0, "no_integer_norm_rep"
    reps_k = sqrt57_representations(q)
    if not reps_k:
        return False, 0, 0, "no_sqrt57_norm_rep"

    a0_domain = [v for v in range(-(h - 1), h) if v % 2 == 0]
    odd = [v for v in range(-h, h + 1) if v % 2 != 0]
    a_domains = [a0_domain, odd, odd, odd, odd]
    b_domains = [odd, odd, odd, odd, odd]
    side_a = c57_side_candidates(a_domains, reps_z, reps_k)
    side_b = c57_side_candidates(b_domains, reps_z, reps_k)
    if not side_a or not side_b:
        return False, len(side_a), len(side_b), "no_side_vector"

    z_mates: dict[int, list[int]] = {}
    for x, y in reps_z:
        z_mates.setdefault(x, []).append(y)
    k_mates: dict[tuple[int, int], list[tuple[int, int]]] = {}
    for alpha, beta in reps_k:
        k_mates.setdefault(alpha, []).append(beta)
    for L1, L3, L19, alpha in side_a:
        for M1 in z_mates[L1]:
            for M3 in z_mates[L3]:
                for M19 in z_mates[L19]:
                    for beta in k_mates.get(alpha, []):
                        if (M1, M3, M19, beta) in side_b:
                            return True, len(side_a), len(side_b), "sat_boxed"
    return False, len(side_a), len(side_b), "component_join_unsat"


def c57_firing_status(q: int, h: int) -> tuple[bool, str]:
    """Return whether the written C_57 firing criterion applies."""
    boxed, _n_a, _n_b, mechanism = c57_boxed_join_status(q, h)
    return not boxed, mechanism


def quantified_firing_status(
    sig: dict,
    evaluate_full_torus: bool = True,
    evaluate_h3: bool = True,
) -> tuple[bool, str] | None:
    if evaluate_h3:
        h3_status = h3_support_augmentation_status(sig["q"], sig["tp"])
        if h3_status is not None and h3_status[0]:
            return h3_status
        h3_paf_mechanism = H3_SUPPORT_PAF_OBSTRUCTIONS.get(
            (sig["q"], sig["tp"])
        )
        if h3_paf_mechanism is not None:
            return True, h3_paf_mechanism

    lane = signature_lane(sig)
    if lane == "two_orbit":
        return two_orbit_scalar_status(sig["q"], sig["tp"], sig["h"])
    if lane == "prime_square_pm1_lift_p3":
        return p3_gaussian_status(sig["q"], sig["h"])
    if lane == "prime_square_pm1_lift_p5":
        return p5_sqrt5_status(sig["q"], sig["h"])
    if lane == "prime_square_pm1_lift_p7":
        return p7_cubic_status(sig["q"], sig["h"])
    if lane == "c27_full_unit":
        return c27_firing_status(sig["q"], sig["h"])
    if lane == "c21_sqrt21":
        return c21_firing_status(sig["q"], sig["h"])
    if lane == "c49_full_unit":
        return c49_firing_status(sig["q"], sig["h"])
    if lane == "c57_sqrt57":
        return c57_firing_status(sig["q"], sig["h"])
    if lane == "c51_quartic":
        return c51_quartic_status(sig["q"], sig["tp"])
    if lane.startswith("prime_subtorus_degree_"):
        if sig["h"] == 1 and sig["all_plus"]:
            rowsum_status = full_torus_rowsum_status(sig["q"], sig["tp"])
            if rowsum_status is not None:
                return rowsum_status
        if evaluate_full_torus and sig["h"] == 1 and sig["all_plus"]:
            full_status = full_torus_integer_status(sig["q"], sig["tp"])
            if full_status is not None:
                return full_status
        if sig["h"] == 1 and not evaluate_full_torus:
            return None
        degree = int(lane.rsplit("_", 1)[1])
        if prime_subtorus_promotable(sig["q"], sig["tp"], degree):
            return prime_subtorus_status(sig["q"], sig["tp"])
        return None
    return None


def route_level(route: str) -> str:
    return ROUTE_LEVEL[route]


def family_proof_levels() -> dict[str, set[str]]:
    out: dict[str, set[str]] = {}
    for q, (kill_tp, _doc_orbits, route) in PANEL_KILLS.items():
        out.setdefault(family(signature(q, kill_tp)), set()).add(route_level(route))
    return out


def best_family_level(families: set[str], levels_by_family: dict[str, set[str]]) -> str:
    if not families:
        return "no_proper"
    if any("quantified_firing" in levels_by_family.get(fam, set()) for fam in families):
        return "quantified_firing"
    if any("component_criterion" in levels_by_family.get(fam, set()) for fam in families):
        return "component_criterion"
    if any("finite_certificate" in levels_by_family.get(fam, set()) for fam in families):
        return "finite_certificate"
    return "uncovered"


def best_lane_level(sigs: list[dict]) -> str:
    if not sigs:
        return "no_proper"
    levels = {
        level for sig in sigs
        if (level := lane_level_name(
            signature_lane(sig), sig["q"], sig["tp"]
        )) is not None
    }
    if "quantified_firing" in levels:
        return "quantified_firing"
    if "component_criterion" in levels:
        return "component_criterion"
    return "uncovered"


def dichotomy_report(qmax: int) -> int:
    """Step-5 census: panel kills (route levels) vs signature families.

    This is bookkeeping for the arithmetic orbit dichotomy, not a proof: it
    shows which signature families already carry a kill, by which route, and
    which families have no killing marginal at all.
    """
    print("== Step 5: quantified route-accounting census ==")
    print("panel: the 21 T3-unreachable blind-spot multi-prime composites "
          "q<=2000 (subtorus_gluing.md section 4)")
    print()

    kill_fam_counts: Counter = Counter()
    route_counts: Counter = Counter()
    best_agree = 0
    print("q      kill t' h    orb kill family             "
          "route                  best t' (family)")
    for q, (kill_tp, doc_orbits, route) in sorted(PANEL_KILLS.items()):
        sig = signature(q, kill_tp)
        fam = family(sig)
        if sig["n_orbits"] != doc_orbits:
            print(f"  WARNING: q={q} t'={kill_tp}: computed #orbits="
                  f"{sig['n_orbits']} != panel table value {doc_orbits}")
        best = best_signature(q, proper=True)
        best_str = f"{best['tp']} ({family(best)})"
        if best["tp"] == kill_tp:
            best_agree += 1
        else:
            best_str += "  <- differs"
        kill_fam_counts[fam] += 1
        route_counts[route] += 1
        print(f"{q:<6} {kill_tp:<7} {sig['h']:<4} {sig['n_orbits']:<3} "
              f"{fam:<23} {route:<22} {best_str}")
    print()

    print("proof route counts:")
    for route, count in route_counts.most_common():
        print(f"  {route}: {count}   [{ROUTE_LEVEL[route]}: {ROUTE_KIND[route]}]")
    finite_kills = sum(
        count for route, count in route_counts.items()
        if ROUTE_LEVEL[route] == "finite_certificate"
    )
    component_kills = sum(
        count for route, count in route_counts.items()
        if ROUTE_LEVEL[route] == "component_criterion"
    )
    quantified_kills = sum(
        count for route, count in route_counts.items()
        if ROUTE_LEVEL[route] == "quantified_firing"
    )
    print("route-level totals:")
    print(f"  finite certificates: {finite_kills}/{len(PANEL_KILLS)}")
    print(f"  component/scalar criteria: {component_kills}/{len(PANEL_KILLS)}")
    print(f"  quantified firing theorems: {quantified_kills}/{len(PANEL_KILLS)}")
    print("  component criteria still need arithmetic hypotheses before they "
          "count as quantified firing routes; only written firing corollaries "
          "are promoted")
    print()

    print("killing-marginal family counts:")
    for fam, count in kill_fam_counts.most_common():
        print(f"  {fam}: {count}")
    print()

    compact_rows = []
    compact_groups: dict[tuple, list[str]] = {}
    for q, (kill_tp, _doc_orbits, route) in sorted(PANEL_KILLS.items()):
        sig = signature(q, kill_tp)
        if family(sig) != "compact_middle":
            continue
        shape = divisor_shape(kill_tp)
        key = (shape, sig["h"], tuple(sig["sizes"]), sig["Vp_size"], sig["n_orbits"])
        compact_groups.setdefault(key, []).append(f"{q}@{kill_tp}")
        compact_rows.append((q, sig, shape, route))

    print("compact-middle laboratory:")
    print("q      t'      component       shape                  h    |V'| "
          "orb sizes        route                  target")
    for q, sig, shape, route in compact_rows:
        sizes = fmt_list(sig["sizes"])
        target = compact_symbolic_flag(sig, route)
        component = compact_component_ladder(q, sig["tp"])
        print(f"{q:<6} {sig['tp']:<7} {component:<15} {shape:<22} "
              f"{sig['h']:<4} {sig['Vp_size']:<4} {sig['n_orbits']:<3} "
              f"{sizes:<12} {route:<22} {target}")
        print(f"       V'={fmt_list(sig['Vp'])}")
    print("compact-middle signature groups:")
    for key, labels in sorted(
        compact_groups.items(), key=lambda item: (item[0], item[1])
    ):
        shape, h, sizes, vp_size, n_orbits = key
        print(f"  shape={shape} h={h} |V'|={vp_size} orb={n_orbits} "
              f"sizes={fmt_list(sizes)} -> {', '.join(labels)}")
    non_theorem_compact = sum(
        1 for _q, _sig, _shape, route in compact_rows
        if ROUTE_LEVEL[route] == "finite_certificate"
    )
    print("  finite-certificate compact-middle targets: "
          f"{non_theorem_compact}/{len(compact_rows)}")
    print()

    qs = blind_spot_qs(qmax)
    census: Counter = Counter()
    for q in qs:
        for sig in candidates(q, proper=True):
            census[family(sig)] += 1
    print("census: all proper-divisor signatures, blind-spot multi-prime "
          f"panel, qmax={qmax}")
    print(f"  distinct q={len(qs)} marginals={sum(census.values())} "
          f"(the 21 panel q are the T3-unreachable subset)")
    uncovered = []
    for fam, count in census.most_common():
        mark = ""
        if fam not in kill_fam_counts:
            mark = "   <- no panel kill in this family"
            uncovered.append(fam)
        print(f"  {fam}: {count}{mark}")
    print()

    coverage_counts: Counter = Counter()
    coverage_examples: dict[str, list[str]] = {
        "quantified_firing": [],
        "component_criterion": [],
        "uncovered": [],
        "no_proper": [],
    }
    lane_counts: Counter = Counter()
    wide_large = []
    for q in qs:
        sigs = candidates(q, proper=True)
        families = {family(sig) for sig in sigs}
        lanes = {signature_lane(sig) for sig in sigs}
        for lane in lanes:
            lane_counts[lane] += 1
        level = best_lane_level(sigs)
        coverage_counts[level] += 1
        if len(coverage_examples[level]) < 8:
            coverage_examples[level].append(str(q))
        if families & {"wide_middle", "large_orbit"}:
            wide_large.append(
                f"{q}({','.join(sorted(families & {'wide_middle', 'large_orbit'}))})"
            )
    print("per-q lane coverage:")
    print(f"  quantified-firing lane available: {coverage_counts['quantified_firing']}")
    print(f"  component-criterion lane available: {coverage_counts['component_criterion']}")
    print(f"  uncovered proper-divisor lanes only: {coverage_counts['uncovered']}")
    print(f"  no proper divisor marginal: {coverage_counts['no_proper']}")
    print("  lane counts across q:")
    for lane, count in lane_counts.most_common():
        level = lane_level_name(lane) or "uncovered"
        print(f"    {lane}: {count} [{level}]")
    for level in ("uncovered", "no_proper"):
        if coverage_examples[level]:
            print(f"  first {level} examples: {', '.join(coverage_examples[level])}")
    if wide_large:
        print(f"  q with wide/large marginals also present: {len(wide_large)}")
        print(f"    first examples: {', '.join(wide_large[:8])}")
    if coverage_counts["uncovered"] == 0:
        print("  every census q with at least one proper divisor has a divisor "
              "in a recognized theorem-facing lane; this is still not a proof "
              "that the lane fires for that q.")
    print()

    print("notes:")
    print(f"  - best_signature() picks the killing divisor in only "
          f"{best_agree}/{len(PANEL_KILLS)} panel kills; 'best signature' "
          f"ranks compression shape and is NOT a proof route.")
    if uncovered:
        print(f"  - uncovered families ({', '.join(uncovered)}) need either "
              f"a firing criterion or a proof that they never have to fire.")
    print("  - a complete dichotomy must cover every signature family the "
          "multiplier group can force, not just the families that already "
          "carry kills.")
    print("  - a route is counted as quantified_firing only after the "
          "manuscript states a firing corollary quantified over q; exact "
          "component criteria alone are not promoted.")
    return 0


def existential_divisor_report(
    qmax: int,
    summary_only: bool = False,
    dynamic_secondary: bool = True,
    dynamic_full_torus: bool = True,
    dynamic_h3_augmentation: bool = True,
) -> int:
    """Start the existential divisor theorem by classifying actual branches.

    Unlike --dichotomy-report, this mode does not count a q as covered merely
    because a quantified lane is present.  It evaluates the written firing
    predicates on every proper divisor and records the remaining q in named
    exception branches.
    """
    qs = blind_spot_qs(qmax)
    print("== Existential divisor theorem scaffold ==")
    print(
        "classification: composite multi-prime q surviving two-squares and "
        f"self-conjugacy, qmax={qmax}"
    )
    print(
        "A q is in the first branch only if some proper divisor actually "
        "fires by a written quantified criterion, not merely because a "
        "matching lane exists."
    )
    if not dynamic_secondary:
        print(
            "Dynamic secondary exact checks are disabled; only recorded "
            "secondary certificates are consumed.  Use this for wider "
            "evidence sweeps, not for the q<=2000 proof ledger."
        )
    if not dynamic_full_torus:
        print(
            "Dynamic full-torus sign joins are disabled; all-plus h=1 "
            "prime-order branches are counted as full_torus_sign_lane "
            "unless another cheap criterion fires."
        )
    if not dynamic_h3_augmentation:
        print(
            "Dynamic h=3 support-augmentation checks are disabled; use this "
            "only for wider evidence sweeps, not for the q<=2000 proof ledger."
        )
    print()
    if not summary_only:
        print("q      branch                         firing/detail        lanes")

    branch_counts: Counter = Counter()
    branch_examples: dict[str, list[str]] = {}
    closure_mechanisms: Counter = Counter()
    branch_detail_counts: dict[str, Counter] = {}
    for q in qs:
        sigs = candidates(q, proper=True)
        lanes = sorted({signature_lane(sig) for sig in sigs})
        firing_rows = []
        local_pass = []
        for sig in sigs:
            status = quantified_firing_status(
                sig,
                evaluate_full_torus=dynamic_full_torus,
                evaluate_h3=dynamic_h3_augmentation,
            )
            if status is None:
                continue
            fires, mechanism = status
            if fires:
                firing_rows.append((sig["tp"], signature_lane(sig), mechanism))
            else:
                local_pass.append((sig["tp"], signature_lane(sig), mechanism))

        if firing_rows:
            firing_rows.sort()
            tp, lane, mechanism = firing_rows[0]
            branch = "has_quantified_firing_divisor"
            detail = f"{tp}@{lane}:{mechanism}"
            branch_detail = f"{lane}:{mechanism}"
            closure_mechanisms[mechanism] += 1
        elif q in PROJECTION_GLUING_OBSTRUCTIONS:
            cover_tp, quotient_tps, mechanism = PROJECTION_GLUING_OBSTRUCTIONS[q]
            left_tp, right_tp = quotient_tps
            branch = "has_projection_gluing_obstruction"
            detail = f"{cover_tp}@gluing({left_tp},{right_tp}):{mechanism}"
            branch_detail = f"gluing({left_tp},{right_tp}):{mechanism}"
            closure_mechanisms[mechanism] += 1
        elif not sigs:
            t = (q + 1) // 2
            full_sig = signature(q, t)
            lane = signature_lane(full_sig)
            status = quantified_firing_status(
                full_sig,
                evaluate_full_torus=dynamic_full_torus,
                evaluate_h3=dynamic_h3_augmentation,
            )
            if status is not None:
                fires, mechanism = status
                detail = f"{t}@{lane}:{mechanism}"
                if fires:
                    branch = "has_quantified_full_torus"
                    branch_detail = f"{lane}:{mechanism}"
                    closure_mechanisms[mechanism] += 1
                else:
                    branch = "full_torus_local_pass"
                    branch_detail = f"{lane}:{mechanism}"
            elif (
                not dynamic_full_torus
                and full_sig["h"] == 1
                and full_sig["all_plus"]
                and lane.startswith("prime_subtorus_degree_")
            ):
                branch = "full_torus_sign_lane"
                detail = f"{t}@{lane}:not_evaluated"
                branch_detail = lane
            elif lane_level_name(lane) == "component_criterion":
                branch = "prime_t_full_torus_component"
                detail = f"{t}@{lane}"
                branch_detail = lane
            else:
                branch = "no_proper_divisor"
                detail = f"{t}@{lane}"
                branch_detail = lane
        elif local_pass:
            if q in SECONDARY_EXACT_MARGINAL_OBSTRUCTIONS:
                secondary_rows = [SECONDARY_EXACT_MARGINAL_OBSTRUCTIONS[q]]
            elif dynamic_secondary:
                secondary_rows = []
                for sig in sigs:
                    status = secondary_marginal_status(sig)
                    if status is None:
                        continue
                    fires, mechanism = status
                    if fires:
                        secondary_rows.append(
                            (sig["tp"], signature_lane(sig), mechanism)
                        )
                        break
            else:
                secondary_rows = []
            if secondary_rows:
                secondary_rows.sort()
                tp, lane, mechanism = secondary_rows[0]
                branch = "has_secondary_exact_marginal_obstruction"
                detail = f"{tp}@{lane}:{mechanism}"
                branch_detail = f"{lane}:{mechanism}"
                closure_mechanisms[mechanism] += 1
            else:
                finite = panel_finite_certificate(q)
                if finite is not None:
                    tp, route = finite
                    branch = "has_finite_certificate_obstruction"
                    detail = f"{tp}@{route}"
                    branch_detail = route
                else:
                    local_pass.sort()
                    tp, lane, mechanism = local_pass[0]
                    branch = "local_pass_quantified_lane"
                    detail = f"{tp}@{lane}:{mechanism}"
                    branch_detail = f"{lane}:{mechanism}"
        elif any(
            lane_level_name(signature_lane(sig), q, sig["tp"])
            == "component_criterion"
            for sig in sigs
        ):
            branch = "component_criterion_only"
            detail = ",".join(sorted({
                signature_lane(sig) for sig in sigs
                if lane_level_name(signature_lane(sig), q, sig["tp"])
                == "component_criterion"
            }))
            branch_detail = detail
        else:
            branch = "unnamed_proper_divisor_lane"
            detail = ",".join(lanes)
            branch_detail = detail

        branch_counts[branch] += 1
        branch_detail_counts.setdefault(branch, Counter())[branch_detail] += 1
        branch_examples.setdefault(branch, [])
        if len(branch_examples[branch]) < 10:
            branch_examples[branch].append(str(q))
        if not summary_only:
            print(f"{q:<6} {branch:<30} {detail:<20} {','.join(lanes)}")

    print()
    print("branch counts:")
    for branch, count in branch_counts.most_common():
        print(f"  {branch}: {count}")
        print(f"    first examples: {', '.join(branch_examples[branch])}")
    if closure_mechanisms:
        print("closure mechanisms:")
        for mechanism, count in closure_mechanisms.most_common():
            print(f"  {mechanism}: {count}")
    open_branches = [
        branch for branch in branch_detail_counts
        if not branch.startswith("has_")
    ]
    if open_branches:
        print("open branch detail counts:")
        for branch in sorted(open_branches):
            print(f"  {branch}:")
            for detail, count in branch_detail_counts[branch].most_common(8):
                print(f"    {detail}: {count}")
            extra = len(branch_detail_counts[branch]) - 8
            if extra > 0:
                print(f"    ... {extra} more")
    print()
    print("next theorem obligation:")
    print("  prove from M(q) that every q enters has_quantified_firing_divisor")
    print("  or has_quantified_full_torus, or replace the remaining named")
    print("  branches by sharper firing/gluing criteria.  The proof must")
    print("  quantify over all divisors t'|t, not over the shape-ranked")
    print("  best_signature() divisor.")
    return 0


def signed_guard_report(qmax: int) -> int:
    """Audit where eps=-1 multipliers occur relative to the converse target.

    The marginal/component solvers in this file are all-plus engines.  This
    report keeps the sign branch visible: it checks whether any multi-prime
    composite q that survives the classical filters would actually need signed
    marginal algebra.
    """
    print("== Signed multiplier guard audit ==")
    print(f"composite q == 1 mod 4, qmax={qmax}")
    print(
        "A signed row has some eps=-1 element in <M(q),(+1,-1)>.  The "
        "all-plus solvers refuse those rows; the signed marginal algebra "
        "in the paper is the theorem-level replacement."
    )
    print()

    counts: Counter = Counter()
    examples: dict[str, list[str]] = {}
    signed_survivors = []
    unresolved_signed_survivors = []

    for q in range(5, qmax + 1, 4):
        if not is_composite(q):
            continue
        t, _V, all_plus = cached_v_group(q)
        multi = is_multi_prime(q)
        if all_plus:
            if multi and not two_squares_fail(q) and not selfconj_kill(q, t):
                branch = "multi_prime_classical_survivor_all_plus"
            elif multi:
                branch = "multi_prime_classically_closed_all_plus"
            else:
                branch = "prime_power_all_plus"
        else:
            if not multi:
                branch = "prime_power_signed"
            elif two_squares_fail(q):
                branch = "multi_prime_signed_twosquares_fail"
            elif selfconj_kill(q, t):
                branch = "multi_prime_signed_selfconj_kill"
            elif is_prime_number(t) and len(_V) == t - 1:
                branch = "multi_prime_signed_full_unit_prime_fire"
                signed_survivors.append(q)
            else:
                status = signed_full_torus_status(q)
                if status is not None and status[0]:
                    _fires, mechanism = status
                    branch = f"multi_prime_{mechanism}"
                    signed_survivors.append(q)
                else:
                    branch = "multi_prime_signed_classical_survivor"
                    signed_survivors.append(q)
                    unresolved_signed_survivors.append(q)
        counts[branch] += 1
        examples.setdefault(branch, [])
        if len(examples[branch]) < 12:
            examples[branch].append(str(q))

    for branch, count in counts.most_common():
        print(f"  {branch}: {count}")
        print(f"    first examples: {', '.join(examples[branch])}")
    print()
    if unresolved_signed_survivors:
        print("WARNING: unresolved signed multi-prime classical survivors found:")
        print("  " + ", ".join(str(q) for q in unresolved_signed_survivors[:40]))
        if len(unresolved_signed_survivors) > 40:
            print(f"  ... {len(unresolved_signed_survivors) - 40} more")
    elif signed_survivors:
        print("signed multi-prime classical survivors are all closed by the "
              "signed full-torus criteria:")
        print("  " + ", ".join(str(q) for q in signed_survivors[:40]))
        if len(signed_survivors) > 40:
            print(f"  ... {len(signed_survivors) - 40} more")
    else:
        print(
            "no signed multi-prime composite survives the two-squares and "
            "self-conjugacy filters in this range"
        )
    print(
        "notes: prime_power_signed rows are the classical p == 3 mod 4 "
        "prime-power sign-alternating multiplier cases; they are construction "
        "cases, not non-prime-power converse targets."
    )
    return 0


def side_assignment_counts(sig: dict) -> tuple[int, int]:
    """Side assignment counts for the orbit-value MITM boxes/parities."""
    h = sig["h"]
    n_orbits = sig["n_orbits"]
    return h * (h + 1) ** (n_orbits - 1), (h + 1) ** n_orbits


def predicate_status_label(status: tuple[bool, str] | None) -> str:
    if status is None:
        return "unavailable"
    fires, mechanism = status
    return f"{'FIRE' if fires else 'PASS'}:{mechanism}"


def format_scalar_tuple_rows(
    tuples: list[tuple[int, int, int, int]],
    limit: int,
) -> str:
    shown = tuples[:limit]
    body = ", ".join(f"({a0},{c},{b0},{d})" for a0, c, b0, d in shown)
    if len(tuples) > limit:
        body += f", ... {len(tuples) - limit} more"
    return body


def prime_subtorus_extra_check(
    sig: dict,
    max_degree: int,
    point_cap: int,
) -> dict | None:
    lane = signature_lane(sig)
    if not lane.startswith("prime_subtorus_degree_"):
        return None
    degree = int(lane.rsplit("_", 1)[1])
    if degree > max_degree:
        return {
            "checker": "prime_subtorus",
            "kind": "not_run",
            "detail": f"degree={degree}>max_degree={max_degree}",
        }
    with contextlib.redirect_stdout(StringIO()):
        alg = build_marginal_algebra(sig["q"], sig["tp"])
        res = prime_subtorus_join(alg, point_cap=point_cap)
    detail = (
        f"{res['mechanism']}; degree={res['degree']} "
        f"halves={res['n_halves']} A={res['n_side_a']} B={res['n_side_b']}"
    )
    if res["status"] == "UNSAT":
        kind = "fire"
    elif res["status"] == "SAT":
        kind = "pass"
    else:
        kind = "refused"
        detail = (
            f"{res['mechanism']}; degree={res['degree']} "
            f"point_cap={point_cap:,}"
        )
    return {"checker": "prime_subtorus", "kind": kind, "detail": detail}


def integer_mitm_extra_check(
    sig: dict,
    cap: int,
    max_orbits: int,
) -> dict | None:
    if cap <= 0:
        return None
    a_total, b_total = side_assignment_counts(sig)
    count_detail = f"A={a_total:,} B={b_total:,}"
    if sig["n_orbits"] > max_orbits:
        return {
            "checker": "integer_mitm",
            "kind": "not_run",
            "detail": f"orbits={sig['n_orbits']}>max_orbits={max_orbits}; {count_detail}",
        }
    if a_total > cap or b_total > cap:
        return {
            "checker": "integer_mitm",
            "kind": "refused",
            "detail": f"side_assignments_exceed_cap={cap:,}; {count_detail}",
        }
    with contextlib.redirect_stdout(StringIO()):
        alg = build_marginal_algebra(sig["q"], sig["tp"])
        result = exact_integer_mitm(alg, cap)
    if result is False:
        kind, mechanism = "fire", "exact_unsat"
    elif result is True:
        kind, mechanism = "pass", "exact_sat"
    else:
        kind, mechanism = "refused", f"cap={cap:,}"
    return {
        "checker": "integer_mitm",
        "kind": kind,
        "detail": f"{mechanism}; {count_detail}",
    }


def secondary_extra_checks(
    sig: dict,
    prime_degree: int,
    prime_outer_cap: int,
    integer_cap: int,
    integer_max_orbits: int,
) -> list[dict]:
    checks: list[dict] = []
    prime_check = prime_subtorus_extra_check(sig, prime_degree, prime_outer_cap)
    if prime_check is not None:
        checks.append(prime_check)
        if prime_check["kind"] in {"fire", "pass"}:
            return checks
    mitm_check = integer_mitm_extra_check(sig, integer_cap, integer_max_orbits)
    if mitm_check is not None:
        checks.append(mitm_check)
    return checks


def format_extra_checks(checks: list[dict]) -> str:
    if not checks:
        return "-"
    return "; ".join(
        f"{check['checker']}:{check['kind'].upper()}({check['detail']})"
        for check in checks
    )


def local_pass_report(
    qmax: int,
    limit: int,
    prime_degree: int,
    prime_outer_cap: int,
    integer_cap: int,
    integer_max_orbits: int,
) -> int:
    """Audit local-pass branches with secondary exact checks and witnesses."""
    print("== Local-pass / gluing audit ==")
    print(
        "classification: q in local_pass_quantified_lane for the written "
        f"proper-divisor predicates, qmax={qmax}"
    )
    print(
        "Secondary exact checks explain how the former local-pass branch "
        "splits inside --existential-divisor-report."
    )
    print(
        f"extra check caps: prime_subtorus degree<={prime_degree}, "
        f"point_cap={prime_outer_cap:,}; integer_mitm cap={integer_cap:,}, "
        f"max_orbits={integer_max_orbits}"
    )

    class_counts: Counter = Counter()
    class_examples: dict[str, list[str]] = {}
    local_count = 0

    for q in blind_spot_qs(qmax):
        sigs = candidates(q, proper=True)
        rows = []
        firing_rows = []
        pass_rows = []
        for sig in sigs:
            lane = signature_lane(sig)
            status = quantified_firing_status(sig)
            row = {"sig": sig, "lane": lane, "status": status, "extras": []}
            rows.append(row)
            if status is None:
                continue
            fires, mechanism = status
            if fires:
                firing_rows.append((sig["tp"], lane, mechanism))
            else:
                pass_rows.append((sig["tp"], lane, mechanism))
        if firing_rows or not pass_rows:
            continue

        local_count += 1
        t = (q + 1) // 2
        print()
        print(f"q={q} t={t} q_factor={fmt_factor(q)}")
        pass_bits = [
            f"{tp}@{lane}:{mechanism}"
            for tp, lane, mechanism in sorted(pass_rows)
        ]
        print(f"  passing predicates: {', '.join(pass_bits)}")
        print("  proper divisors:")

        extra_fires = []
        extra_passes = []
        extra_refusals = []
        for row in rows:
            sig = row["sig"]
            status = row["status"]
            if status is None:
                row["extras"] = secondary_extra_checks(
                    sig,
                    prime_degree,
                    prime_outer_cap,
                    integer_cap,
                    integer_max_orbits,
                )
                for check in row["extras"]:
                    if check["kind"] == "fire":
                        extra_fires.append((sig["tp"], row["lane"], check))
                    elif check["kind"] == "pass":
                        extra_passes.append((sig["tp"], row["lane"], check))
                    elif check["kind"] == "refused":
                        extra_refusals.append((sig["tp"], row["lane"], check))

            status_text = predicate_status_label(status)
            extra_text = format_extra_checks(row["extras"])
            a_total, b_total = side_assignment_counts(sig)
            print(
                f"    t'={sig['tp']:<5} h={sig['h']:<4} "
                f"lane={row['lane']:<30} predicate={status_text:<28} "
                f"orbits={sig['n_orbits']:<2} "
                f"assignments=A:{a_total:,}/B:{b_total:,} extra={extra_text}"
            )
            if (
                row["lane"] == "two_orbit"
                and status is not None
                and not status[0]
                and status[1] == "scalar_sat"
            ):
                tuples = two_orbit_scalar_tuples(q, sig["tp"], sig["h"])
                print(
                    "      scalar tuples (a0,c,b0,d), boxed/parity-valid: "
                    f"{len(tuples)}"
                )
                print(f"      {format_scalar_tuple_rows(tuples, limit)}")

        known = PANEL_KILLS.get(q)
        known_finite = None
        if known is not None:
            kill_tp, _doc_orbits, route = known
            if route_level(route) == "finite_certificate":
                known_finite = f"{kill_tp}@{route}"
                print(f"  known panel finite certificate: {known_finite}")
        known_gluing = None
        if q in PROJECTION_GLUING_OBSTRUCTIONS:
            cover_tp, quotient_tps, mechanism = PROJECTION_GLUING_OBSTRUCTIONS[q]
            left_tp, right_tp = quotient_tps
            known_gluing = (
                f"{cover_tp}@gluing({left_tp},{right_tp}):{mechanism}"
            )
            print(f"  known projection gluing obstruction: {known_gluing}")

        if extra_fires:
            classification = "secondary_divisor_fires"
        elif known_gluing:
            classification = "projection_gluing_obstruction"
        elif known_finite:
            classification = "known_finite_certificate"
        elif len(pass_rows) + len(extra_passes) >= 2 and not extra_refusals:
            classification = "still_locally_compatible"
        else:
            classification = "unresolved_after_affordable_checks"
        class_counts[classification] += 1
        class_examples.setdefault(classification, [])
        if len(class_examples[classification]) < 10:
            class_examples[classification].append(str(q))
        print(f"  classification: {classification}")

    print()
    print("classification counts:")
    print(f"  local-pass q audited: {local_count}")
    for classification, count in class_counts.most_common():
        print(f"  {classification}: {count}")
        print(f"    first examples: {', '.join(class_examples[classification])}")
    print(
        "notes: secondary_divisor_fires means an exact proper-divisor "
        "component join or orbit-value MITM is UNSAT under the printed caps. "
        "projection_gluing_obstruction records a passing-local case whose "
        "quotient side sets do not lift to the common cover. "
        "known_finite_certificate records the existing panel route; it remains "
        "the branch still needing quantified replacement.  still_locally_compatible means every "
        "evaluated local marginal passed and no affordable secondary "
        "incompatibility was found."
    )
    return 0


def h3_finite_report() -> int:
    """Report the h=3 support/augmentation obstruction on finite panel lanes."""
    targets = [
        (1445, 241, "exhaustive_mitm"),
        (1469, 245, "milp"),
        (1625, 271, "milp"),
    ]
    print("== h=3 support/augmentation report ==")
    print(
        "For q=6t'-1, the h=3 boxes and zero-shift energy force "
        "A_0=+-2 and exactly (t'-1)/2 magnitude-3 cells across A off "
        "the origin and all of B.  The row sums must also satisfy "
        "A(1)^2+B(1)^2=q."
    )
    print()
    print("q      t'   h  #orb target support_pairs status        mechanism")
    for q, tp, route in targets:
        detail = h3_support_augmentation_detail(q, tp)
        if detail is None:
            print(f"{q:<6} {tp:<4} not h=3")
            continue
        status = "UNSAT" if detail["fires"] else "PASS"
        print(
            f"{q:<6} {tp:<4} {detail['h']:<2} {detail['n_orbits']:<4} "
            f"{detail['target_support']:<6} {detail['support_pairs']:<13} "
            f"{status:<13} {detail['mechanism']}"
        )
        print(
            "       nonzero orbit sizes: "
            + ",".join(str(size) for size in detail["nonzero_sizes"])
        )
        if detail["witness"] is not None:
            a_support, a_sum, b_support, b_sum = detail["witness"]
            print(
                "       augmentation witness: "
                f"A_support={a_support}, A(1)={a_sum}, "
                f"B_support={b_support}, B(1)={b_sum}"
            )
        else:
            print(f"       no augmentation witness; old finite route={route}")
        paf = H3_SUPPORT_PAF_OBSTRUCTIONS.get((q, tp))
        if paf is not None:
            print(f"       recorded support/PAF obstruction: {paf}")
    return 0


def c27_arithmetic_report(qmax: int) -> int:
    print("== C_27 full-unit arithmetic report ==")
    print("q      h    q_factor        mod27_factors    reps eo oe res boxed mechanism")
    rows = []
    counts: Counter = Counter()
    group_counts: Counter = Counter()
    for h in range(1, (qmax + 1) // 54 + 2, 2):
        q = 54 * h - 1
        if q > qmax:
            continue
        if (
            q % 4 != 1
            or not is_composite(q)
            or not is_multi_prime(q)
            or two_squares_fail(q)
            or selfconj_kill(q, (q + 1) // 2)
        ):
            continue
        sig = signature(q, 27)
        if sig["Vp_size"] != 18 or sig["sizes"] != [18, 6, 2, 1]:
            continue
        reps = gaussian_representations(q)
        eo_residues = {gaussian_residue(z, 27) for z in reps if gaussian_eo(z)}
        oe_residues = {gaussian_residue(z, 27) for z in reps if gaussian_oe(z)}
        residue_hits = eo_residues & oe_residues
        if not reps:
            boxed = False
            mechanism = "no_norm_rep"
        elif not residue_hits:
            boxed = False
            mechanism = "no_residue_pair"
        elif h >= 57:
            boxed = True
            mechanism = "sat_auto_box"
        else:
            boxed = c27_boxed_join_exists(q, h, reps)
            mechanism = "sat_boxed" if boxed else "small_h_box_cut"
        counts[mechanism] += 1
        residue_sig = factor_residue_signature(q, 27)
        group_counts[(residue_sig, mechanism)] += 1
        rows.append((q, h, len(reps), len(eo_residues), len(oe_residues),
                     len(residue_hits), boxed, mechanism, residue_sig))

    for q, h, n_reps, n_eo, n_oe, n_res, boxed, mechanism, residue_sig in rows:
        print(
            f"{q:<6} {h:<4} {fmt_factor(q):<15} {residue_sig:<16} {n_reps:<4} "
            f"{n_eo:<2} {n_oe:<2} {n_res:<3} "
            f"{'SAT' if boxed else 'UNSAT':<5} {mechanism}"
        )
    print("counts:")
    for key, value in counts.most_common():
        print(f"  {key}: {value}")
    print("factor-residue groups mod 27:")
    for (residue_sig, mechanism), value in sorted(
        group_counts.items(), key=lambda item: (item[0][0], item[0][1])
    ):
        print(f"  {residue_sig:<16} {mechanism:<18} {value}")
    print(
        "notes: for h>=57, a nonempty residue-pair intersection "
        "G_eo(q) mod 27 intersect G_oe(q) mod 27 is equivalent to a "
        "C_27 marginal witness by the automatic-box corollary; "
        "no_residue_pair and small_h_box_cut are the quantified firing "
        "mechanisms recorded in the paper."
    )
    return 0


def c21_arithmetic_report(qmax: int) -> int:
    print("== C_21 sqrt21 arithmetic report ==")
    print("q      h    q_factor        mod21_factors    Zreps Kreps Aside Bside result mechanism")
    rows = []
    counts: Counter = Counter()
    group_counts: Counter = Counter()
    for h in range(1, (qmax + 1) // 42 + 2, 2):
        q = 42 * h - 1
        if q > qmax:
            continue
        if (
            q % 4 != 1
            or not is_composite(q)
            or not is_multi_prime(q)
            or two_squares_fail(q)
            or selfconj_kill(q, (q + 1) // 2)
        ):
            continue
        sig = signature(q, 21)
        if sig["Vp"] != [1, 4, 5, 16, 17, 20] or sig["sizes"] != [6, 6, 6, 2, 1]:
            continue
        reps_z = gaussian_representations(q)
        reps_k = sqrt21_representations(q)
        boxed, n_a, n_b, mechanism = c21_boxed_join_status(q, h)
        residue_sig = factor_residue_signature(q, 21)
        counts[mechanism] += 1
        group_counts[(residue_sig, mechanism)] += 1
        rows.append((
            q, h, len(reps_z), len(reps_k), n_a, n_b,
            boxed, mechanism, residue_sig,
        ))

    for q, h, n_z, n_k, n_a, n_b, boxed, mechanism, residue_sig in rows:
        print(
            f"{q:<6} {h:<4} {fmt_factor(q):<15} {residue_sig:<16} "
            f"{n_z:<5} {n_k:<5} {n_a:<5} {n_b:<5} "
            f"{'SAT' if boxed else 'UNSAT':<5} {mechanism}"
        )
    print("counts:")
    for key, value in counts.most_common():
        print(f"  {key}: {value}")
    print("factor-residue groups mod 21:")
    for (residue_sig, mechanism), value in sorted(
        group_counts.items(), key=lambda item: (item[0][0], item[0][1])
    ):
        print(f"  {residue_sig:<16} {mechanism:<22} {value}")
    print(
        "notes: no_side_vector and component_join_unsat are the quantified "
        "C_21 firing mechanisms recorded in the paper; SAT rows remain "
        "controls against treating the orbit shape as an automatic "
        "obstruction."
    )
    return 0


def prime_subtorus_report(qmax: int, max_degree: int) -> int:
    """Exact component-join census for prime sub-torus lanes of low degree.

    For every blind-spot q and every divisor t'|t (proper and full torus)
    whose signature is a prime_subtorus_degree_d lane with d <= max_degree,
    evaluate the exact Q x K period component join and classify the mechanism.
    This is the theorem-facing evidence report for cor:prime-subtorus-firing.
    """
    print("== Prime sub-torus component-join report ==")
    print(f"blind-spot multi-prime q<=qmax={qmax}, degree<= {max_degree}")
    print("q      ell    d  h    q_factor        mod_ell_factors  Zreps halves oddH evenH Aside Bside result mechanism")
    counts: Counter = Counter()
    degree_counts: dict[int, Counter] = {}
    full_torus_counts: Counter = Counter()
    sat_nonrational = 0
    for q in blind_spot_qs(qmax):
        for sig in candidates(q, proper=False):
            lane = signature_lane(sig)
            if not lane.startswith("prime_subtorus_degree_"):
                continue
            degree = int(lane.rsplit("_", 1)[1])
            if degree > max_degree:
                continue
            with contextlib.redirect_stdout(StringIO()):
                alg = build_marginal_algebra(q, sig["tp"])
                res = prime_subtorus_join(alg)
            mechanism = res["mechanism"]
            counts[mechanism] += 1
            degree_counts.setdefault(degree, Counter())[mechanism] += 1
            if sig["h"] == 1:
                full_torus_counts[mechanism] += 1
            if res["status"] == "SAT" and res["witness_nonrational"]:
                sat_nonrational += 1
            residue_sig = factor_residue_signature(q, sig["tp"])
            print(
                f"{q:<6} {sig['tp']:<6} {degree:<2} {sig['h']:<4} "
                f"{fmt_factor(q):<15} {residue_sig:<16} "
                f"{res['n_reps_z']:<5} {res['n_halves']:<6} "
                f"{res['n_odd_halves']:<4} {res['n_even_halves']:<5} "
                f"{res['n_side_a']:<5} {res['n_side_b']:<5} "
                f"{res['status']:<6} {mechanism}"
            )
    print("mechanism counts:")
    for key, value in counts.most_common():
        print(f"  {key}: {value}")
    for degree in sorted(degree_counts):
        parts = ", ".join(
            f"{mech}: {value}"
            for mech, value in degree_counts[degree].most_common()
        )
        print(f"  degree {degree}: {parts}")
    if full_torus_counts:
        parts = ", ".join(
            f"{mech}: {value}"
            for mech, value in full_torus_counts.most_common()
        )
        print(f"  full torus (h=1): {parts}")
    print(f"  SAT rows with a nonrational period witness: {sat_nonrational}")
    print(
        "notes: no_side_vector and component_join_unsat are the firing "
        "mechanisms of cor:prime-subtorus-firing; SAT rows are local passes "
        "and remain controls against treating the lane as an automatic "
        "obstruction.  Every h=1 UNSAT row excludes an all-plus V-invariant "
        "Turyn pair at the full torus."
    )
    return 0


def euler_phi(n: int) -> int:
    result = n
    for p in factor(n):
        result -= result // p
    return result


def divisor_lattice_audit(qmax: int, q_list: list[int] | None,
                          limit: int) -> int:
    """Machine verification of lem:orbit-census over the divisor lattice.

    For each selected q and every divisor t'|t (including the full torus),
    the constructed V'-orbit list is checked stratum by stratum against the
    census formula: the elements with gcd(j,t') = t'/f form phi(f)/|V_f|
    orbits of size |V_f|, where V_f is the image of V in (Z/f)^*.  The
    guaranteed criterion nodes of thm:divisor-selection(iii) are listed per
    q, together with the recorded certified empty node from the finite-panel
    accounting where one exists.
    """
    qs = sorted(set(q_list)) if q_list else blind_spot_qs(qmax)
    print("== Divisor lattice audit "
          "(lem:orbit-census / thm:divisor-selection) ==")
    print(f"orders audited: {len(qs)} (qmax={qmax})")
    nodes_checked = 0
    mismatches = 0
    skipped_signed: list[int] = []
    printed = 0
    for q in qs:
        t, V, all_plus = cached_v_group(q)
        if not all_plus:
            skipped_signed.append(q)
            continue
        node_summaries: list[tuple[int, int]] = []
        for tp in sorted(divisors(t)):
            if tp <= 1:
                continue
            Vp = sorted({v % tp for v in V})
            orbit_list = orbits(tp, Vp)
            nodes_checked += 1
            by_conductor: Counter = Counter()
            ok = True
            for orb in orbit_list:
                gcds = {math.gcd(j, tp) for j in orb}
                if len(gcds) != 1:
                    ok = False
                    break
                f = tp // gcds.pop()
                v_f = len({v % f for v in V})
                if len(orb) != v_f:
                    ok = False
                    break
                by_conductor[f] += 1
            if ok:
                for f in divisors(tp):
                    v_f = len({v % f for v in V})
                    phi_f = euler_phi(f)
                    if phi_f % v_f or by_conductor[f] != phi_f // v_f:
                        ok = False
                        break
            if not ok:
                mismatches += 1
                print(f"  CENSUS MISMATCH at q={q}, t'={tp}")
            node_summaries.append((tp, len(orbit_list)))
        guaranteed = []
        for ell in sorted(factor(t)):
            v_ell = len({v % ell for v in V})
            guaranteed.append(f"period@{ell}(d={(ell - 1) // v_ell})")
        if t % 3 == 0:
            guaranteed.append("two_orbit@3")
            if t // 3 > 1:
                guaranteed.append(f"h3@{t // 3}")
        guaranteed.append(f"top@{t}")
        recorded = None
        if q in PANEL_KILLS:
            kill_tp, _n_orb, route = PANEL_KILLS[q]
            recorded = f"{kill_tp}:{route}"
        elif q in SECONDARY_EXACT_MARGINAL_OBSTRUCTIONS:
            kill_tp, _lane, mech = SECONDARY_EXACT_MARGINAL_OBSTRUCTIONS[q]
            recorded = f"{kill_tp}:{mech}"
        elif q in PROJECTION_GLUING_OBSTRUCTIONS:
            kill_tp, pair, mech = PROJECTION_GLUING_OBSTRUCTIONS[q]
            recorded = f"{kill_tp}:{mech}{pair}"
        if printed < limit:
            profile = " ".join(f"{tp}:{n}" for tp, n in node_summaries)
            line = f"q={q:<5} t={t:<5} nodes[t':#orbits]= {profile}"
            print(line)
            tail = f"    guaranteed: {', '.join(guaranteed)}"
            if recorded:
                tail += f"  recorded_certified_node: {recorded}"
            print(tail)
            printed += 1
    print(f"divisor nodes checked: {nodes_checked}")
    print(f"census mismatches: {mismatches}")
    if skipped_signed:
        print(f"skipped signed-branch orders (eps=-1): {skipped_signed}")
    print("expected: 0 mismatches; every order lists a nonempty guaranteed "
          "node set ending at the top node, per thm:divisor-selection(iii).")
    return 0 if mismatches == 0 else 1


def two_orbit_rep_audit(qmax: int, q_list: list[int] | None,
                        limit: int) -> int:
    """Machine verification of the two-orbit firing theorems.

    Over every two-orbit node (all divisors including the full torus) of the
    selected orders, the representation-pair criterion of thm:two-orbit-reps
    is compared against the exact scalar enumeration; the corollaries are
    checked on their subfamilies (h=1 transitive full torus always fires for
    m>=5; the m=3 node is always feasible once h>=8).  For prime h=3 nodes,
    the closed-form support-sum condition of cor:h3-support-sum-prime is
    compared against the support stage of the h=3 DP.
    """
    qs = sorted(set(q_list)) if q_list else blind_spot_qs(qmax)
    print("== Two-orbit representation-criterion audit ==")
    print(f"orders audited: {len(qs)} (qmax={qmax})")
    nodes = 0
    disagreements = 0
    mechanism_counts: Counter = Counter()
    full_torus_violations = 0
    c3_violations = 0
    h3_nodes = 0
    h3_disagreements = 0
    skipped_signed: list[int] = []
    printed = 0
    m5_instances: list[str] = []
    for q in qs:
        t, V, all_plus = cached_v_group(q)
        if not all_plus:
            skipped_signed.append(q)
            continue
        for tp in sorted(divisors(t)):
            if tp <= 1:
                continue
            Vp = sorted({v % tp for v in V})
            orbit_list = orbits(tp, Vp)
            h = t // tp
            if len(orbit_list) == 2:
                nodes += 1
                scalar_fires, _ = two_orbit_scalar_status(q, tp, h)
                status, mechanism, detail = two_orbit_rep_status(q, tp, h)
                rep_fires = status == "UNSAT"
                key = f"{'h1' if h == 1 else 'proper'}:{mechanism}"
                if mechanism == "no_congruent_pair" and tp * tp > 4 * q:
                    key += ":parity_forced"
                mechanism_counts[key] += 1
                if scalar_fires != rep_fires:
                    disagreements += 1
                    print(f"  DISAGREEMENT q={q} t'={tp} h={h}: "
                          f"scalar={'UNSAT' if scalar_fires else 'SAT'} "
                          f"reps={status}")
                if h == 1 and (not rep_fires or tp < 5):
                    full_torus_violations += 1
                    print(f"  FULL-TORUS COROLLARY VIOLATION q={q} t={tp}")
                if tp == 3 and h >= 8 and rep_fires:
                    c3_violations += 1
                    print(f"  C3 COROLLARY VIOLATION q={q} h={h}")
                if tp == 5 and status == "UNSAT":
                    m5_instances.append(
                        f"q={q} h={h} mechanism={mechanism}"
                    )
                if mechanism == "box_cut":
                    print(f"  box-cut node: q={q} t'={tp} h={h} "
                          f"congruent={detail['congruent_pairs']}")
                if printed < limit:
                    print(f"q={q:<5} t'={tp:<5} h={h:<4} "
                          f"reps={detail['n_reps']:<3} "
                          f"congruent={detail['congruent_pairs']:<3} "
                          f"{status} ({mechanism})")
                    printed += 1
            if h == 3 and is_prime_number(tp):
                status3 = h3_support_augmentation_status(q, tp)
                if status3 is not None:
                    h3_nodes += 1
                    w = len({v % tp for v in V})
                    closed_fires = ((tp - 1) // 2) % w not in (0, 1)
                    dp_fires = status3[1] == "h3_support_sum_impossible"
                    if closed_fires != dp_fires:
                        h3_disagreements += 1
                        print(f"  H3 SUPPORT-SUM DISAGREEMENT q={q} ell={tp} "
                              f"w={w}: closed={closed_fires} dp={dp_fires}")
    print(f"two-orbit nodes audited: {nodes}")
    print("mechanism counts (h1 = full torus):")
    for key, value in mechanism_counts.most_common():
        print(f"  {key}: {value}")
    print(f"scalar/representation disagreements: {disagreements}")
    print(f"full-torus corollary violations: {full_torus_violations}")
    print(f"c3 corollary violations: {c3_violations}")
    print(f"prime h=3 support-sum nodes: {h3_nodes}, "
          f"closed-form disagreements: {h3_disagreements}")
    if m5_instances:
        print("m=5 firing instances: " + "; ".join(m5_instances))
    if skipped_signed:
        print(f"skipped signed-branch orders (eps=-1): {skipped_signed}")
    print("expected: 0 disagreements and 0 violations.")
    ok = disagreements == 0 and full_torus_violations == 0 \
        and c3_violations == 0 and h3_disagreements == 0
    return 0 if ok else 1


def full_torus_rowsum_audit(qmax: int, q_list: list[int] | None,
                            limit: int) -> int:
    """Machine verification of thm:full-torus-rowsum.

    For every all-plus blind-spot order with prime t, the row-sum verdict
    ((w-1)^2 >= t) is compared against an exact decision at the top node:
    the two-orbit scalar enumeration when d=1, else the complete integer
    sign join where affordable.  The theorem is one-directional, so the
    check is: rowsum fires ==> exact UNSAT.  Small-image rows (w <= d+1)
    are listed with their exact status; they are the residual regime that
    the theorem deliberately leaves open.
    """
    qs = sorted(set(q_list)) if q_list else blind_spot_qs(qmax)
    print("== Full-torus row-sum audit (thm:full-torus-rowsum) ==")
    print(f"orders audited: {len(qs)} (qmax={qmax})")
    prime_t_rows = 0
    fired = 0
    confirmed = 0
    unevaluable = 0
    mismatches = 0
    boundary_rows: list[str] = []
    small_image: list[str] = []
    skipped_signed: list[int] = []
    printed = 0
    for q in qs:
        t, V, all_plus = cached_v_group(q)
        if not all_plus:
            skipped_signed.append(q)
            continue
        if not is_prime_number(t):
            continue
        prime_t_rows += 1
        w = len({v % t for v in V})
        d = (t - 1) // w
        rowsum = full_torus_rowsum_status(q, t)
        predicted = rowsum is not None and rowsum[0]
        if d == 1:
            exact_fires, _ = two_orbit_scalar_status(q, t, 1)
            exact = "UNSAT" if exact_fires else "SAT"
        else:
            status = full_torus_integer_status(q, t)
            if status is None:
                exact = "UNEVALUATED"
            else:
                exact = "UNSAT" if status[0] else "SAT"
        if predicted:
            fired += 1
            if exact == "UNSAT":
                confirmed += 1
            elif exact == "UNEVALUATED":
                unevaluable += 1
            else:
                mismatches += 1
                print(f"  ROWSUM MISMATCH q={q} t={t} w={w} d={d}: "
                      f"theorem fires but exact join is SAT")
        else:
            tag = f"q={q} t={t} w={w} d={d} exact={exact}"
            small_image.append(tag)
            if w == d + 1:
                boundary_rows.append(tag)
        if printed < limit:
            print(f"q={q:<6} t={t:<5} w={w:<4} d={d:<4} "
                  f"rowsum={'fires' if predicted else 'silent':<7} "
                  f"exact={exact}")
            printed += 1
    print(f"prime-t all-plus rows: {prime_t_rows}")
    print(f"rowsum fires: {fired} "
          f"(exact-confirmed: {confirmed}, too wide to join: {unevaluable})")
    print(f"mismatches: {mismatches}")
    print(f"small-image rows (w<=d+1, theorem silent): {len(small_image)}")
    for tag in small_image:
        print(f"  {tag}")
    if boundary_rows:
        print("boundary rows (w=d+1, trivial character solvable by "
              "rem:rowsum-sharp):")
        for tag in boundary_rows:
            print(f"  {tag}")
    if skipped_signed:
        print(f"skipped signed-branch orders (eps=-1): {skipped_signed}")
    print("expected: 0 mismatches; every fired row that is affordable to "
          "join exactly must be UNSAT.")
    return 0 if mismatches == 0 else 1


def h3_achievable_sums(d: int, j: int) -> set[int]:
    """Exact sums of (d-j) values +-1 and j values +-3 (prop:h3-augmentation-reps)."""
    return {3 * (2 * k - j) + (2 * l - (d - j))
            for k in range(j + 1) for l in range(d - j + 1)}


def h3_prime_rep_status(q: int, ell: int) -> tuple[bool, str] | None:
    """Closed-form h=3 support-augmentation join at prime ell.

    prop:h3-augmentation-reps: with w = |V_ell| and d = (ell-1)/w, the join
    is nonempty iff some Gaussian representation q = X^2+Y^2 (X even, Y odd)
    splits as X in +-2 + w*Sigma(d,jA), Y in +-b* + w*Sigma(d,jB) with
    jA+jB = J.  Returns None for non-h3 or signed inputs.
    """
    t, V, all_plus = cached_v_group(q)
    if not all_plus or t != 3 * ell or not is_prime_number(ell):
        return None
    w = len({v % ell for v in V})
    d = (ell - 1) // w
    target = (ell - 1) // 2
    beta = target % w
    if beta not in (0, 1):
        return True, "h3_support_sum_impossible"
    J = (target - beta) // w
    b_star = 3 if beta == 1 else 1
    a_sums: dict[int, set[int]] = {}
    b_sums: dict[int, set[int]] = {}
    for j in range(d + 1):
        for s in h3_achievable_sums(d, j):
            for a0 in (2, -2):
                a_sums.setdefault(abs(a0 + w * s), set()).add(j)
            for b0 in (b_star, -b_star):
                b_sums.setdefault(abs(b0 + w * s), set()).add(j)
    for x in range(0, math.isqrt(q) + 1):
        y2 = q - x * x
        y = math.isqrt(y2)
        if y * y != y2:
            continue
        X, Y = (x, y) if x % 2 == 0 else (y, x)
        for j_a in a_sums.get(X, ()):
            if (J - j_a) in b_sums.get(Y, ()):
                return False, "h3_rep_witness"
    return True, "h3_augmentation_reps_impossible"


def h3_residue_relaxation_fires(q: int, ell: int) -> bool | None:
    """cor:h3-augmentation-residue: no rep with X=+-2, Y=+-b* mod w."""
    t, V, all_plus = cached_v_group(q)
    if not all_plus or t != 3 * ell or not is_prime_number(ell):
        return None
    w = len({v % ell for v in V})
    beta = ((ell - 1) // 2) % w
    if beta not in (0, 1):
        return True
    b_star = 3 if beta == 1 else 1
    for x in range(0, math.isqrt(q) + 1):
        y2 = q - x * x
        y = math.isqrt(y2)
        if y * y != y2:
            continue
        X, Y = (x, y) if x % 2 == 0 else (y, x)
        if X % w in (2 % w, (-2) % w) and \
                Y % w in (b_star % w, (-b_star) % w):
            return False
    return True


def h3_gcd_support_fires(q: int, tp: int) -> tuple[bool, int]:
    """cor:h3-support-sum-gcd: (t'-1)/2 mod gcd(sizes) not in {0,1}."""
    sizes = h3_node_sizes(q, tp)
    assert sizes is not None
    g = 0
    for n in sizes:
        g = math.gcd(g, n)
    return ((tp - 1) // 2) % g not in (0, 1), g


def h3_hierarchy_audit(qmax: int, q_list: list[int] | None,
                       limit: int) -> int:
    """Machine verification of the h=3 hierarchy closed forms.

    Prime nodes: prop:h3-augmentation-reps must agree exactly with the
    support-augmentation DP; cor:h3-augmentation-residue must be sound
    (fires => DP fires).  Composite nodes: cor:h3-support-sum-gcd must be
    sound against the DP support stage.  Survivors (nodes passing both
    stages) are listed: they are the PAF-layer residue of the hierarchy.
    """
    qs = sorted(set(q_list)) if q_list else blind_spot_qs(qmax)
    print("== h=3 hierarchy audit (prop:h3-augmentation-reps / "
          "cor:h3-support-sum-gcd) ==")
    print(f"orders audited: {len(qs)} (qmax={qmax})")
    prime_nodes = 0
    prime_agree = 0
    prime_fire = 0
    residue_fire = 0
    residue_unsound = 0
    composite_nodes = 0
    gcd_fire = 0
    gcd_unsound = 0
    dp_capped = 0
    survivors: list[str] = []
    mismatches = 0
    sweep_start = time.monotonic()
    for idx, q in enumerate(qs, 1):
        if idx % 50 == 0:
            elapsed = time.monotonic() - sweep_start
            eta = elapsed / idx * (len(qs) - idx)
            print(f"  [progress] {idx}/{len(qs)} orders, "
                  f"elapsed {elapsed:.0f}s, eta {eta:.0f}s", flush=True)
        t, V, all_plus = cached_v_group(q)
        if not all_plus or t % 3 or t // 3 <= 1:
            continue
        tp = t // 3
        node_start = time.monotonic()
        dp = h3_support_augmentation_status(q, tp)
        node_secs = time.monotonic() - node_start
        if node_secs > 3.0:
            sizes = h3_node_sizes(q, tp) or ()
            print(f"  [slow] q={q} t'={tp} DP took {node_secs:.1f}s "
                  f"(orbits={len(sizes)}, target={(tp - 1) // 2}, "
                  f"product={len(sizes) * ((tp - 1) // 2)})", flush=True)
        if dp is None:
            dp_capped += 1
            continue
        if is_prime_number(tp):
            prime_nodes += 1
            node_start = time.monotonic()
            cf = h3_prime_rep_status(q, tp)
            node_secs = time.monotonic() - node_start
            if node_secs > 3.0:
                print(f"  [slow] q={q} ell={tp} rep-criterion took "
                      f"{node_secs:.1f}s (d={(tp - 1) // 2})", flush=True)
            if cf is None:
                continue
            if cf[0] == dp[0]:
                prime_agree += 1
            else:
                mismatches += 1
                print(f"  AUGMENTATION MISMATCH q={q} ell={tp}: "
                      f"closed={cf} dp={dp}")
            if cf[0]:
                prime_fire += 1
            else:
                survivors.append(f"q={q} ell={tp} (prime)")
            rr = h3_residue_relaxation_fires(q, tp)
            if rr:
                residue_fire += 1
                if not dp[0]:
                    residue_unsound += 1
                    print(f"  RESIDUE UNSOUND q={q} ell={tp}")
        else:
            composite_nodes += 1
            fires_g, g = h3_gcd_support_fires(q, tp)
            if fires_g:
                gcd_fire += 1
                if dp[1] != "h3_support_sum_impossible":
                    gcd_unsound += 1
                    print(f"  GCD UNSOUND q={q} tp={tp} g={g} dp={dp}")
            if not dp[0]:
                survivors.append(f"q={q} tp={tp} (composite)")
    print(f"prime h=3 nodes: {prime_nodes}, closed-form/DP agree: "
          f"{prime_agree}, closed-form fires: {prime_fire}, "
          f"residue-corollary fires: {residue_fire}")
    print(f"composite h=3 nodes: {composite_nodes}, gcd-congruence fires: "
          f"{gcd_fire}")
    print(f"DP-capped nodes (unevaluated): {dp_capped}")
    print(f"mismatches: {mismatches}, residue unsound: {residue_unsound}, "
          f"gcd unsound: {gcd_unsound}")
    print(f"survivors passing to the PAF layer: {len(survivors)}")
    for tag in survivors[:limit if limit else len(survivors)]:
        print(f"  {tag}")
    print("expected: 0 mismatches and 0 unsound firings.")
    ok = mismatches == 0 and residue_unsound == 0 and gcd_unsound == 0
    return 0 if ok else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--qmax", type=int, default=2000)
    parser.add_argument("--q", type=int, nargs="*", default=None)
    parser.add_argument("--blind-spot", action="store_true",
                        help="only q passing two-squares and self-conjugacy")
    parser.add_argument("--multi-prime", action="store_true",
                        help="only q with at least two distinct prime factors")
    parser.add_argument("--include-full", action="store_true",
                        help="allow t'=t when choosing each q's best signature")
    parser.add_argument("--all-divisors", action="store_true",
                        help="print every divisor signature for each q instead of only the best")
    parser.add_argument("--prime-square-lift", action="store_true",
                        help="only print t'=p^2 signatures with V' the +-1 lift modulo p")
    parser.add_argument("--known-outcomes", action="store_true",
                        help="append known SAT/UNSAT/UNKNOWN labels for regression marginals")
    parser.add_argument("--dichotomy-report", action="store_true",
                        help="Step-5 route census: the 21 panel kills (q, kill t', "
                             "proof route) against all-divisor signature families; "
                             "ignores the other filter flags")
    parser.add_argument("--existential-divisor-report", action="store_true",
                        help="Step-5 scaffold for the existential divisor theorem: "
                             "test actual quantified firing predicates on all "
                             "proper divisors and name the remaining branches")
    parser.add_argument("--local-pass-report", action="store_true",
                        help="audit local_pass_quantified_lane cases: print all "
                             "proper-divisor predicate statuses, scalar SAT "
                             "tuples, and capped secondary exact checks")
    parser.add_argument("--summary-only", action="store_true",
                        help="with --existential-divisor-report, suppress per-q "
                             "rows and print only branch summaries")
    parser.add_argument("--no-dynamic-secondary", action="store_true",
                        help="with --existential-divisor-report, do not launch "
                             "new secondary exact MITM/component checks; consume "
                             "only recorded secondary certificates")
    parser.add_argument("--no-dynamic-full-torus", action="store_true",
                        help="with --existential-divisor-report, do not launch "
                             "new full-torus sign MITM checks; count h=1 "
                             "prime-order all-plus cases as a sign lane")
    parser.add_argument("--no-dynamic-h3-augmentation", action="store_true",
                        help="with --existential-divisor-report, do not launch "
                             "the h=3 support-augmentation DP; use this for "
                             "wide evidence sweeps, not the q<=2000 ledger")
    parser.add_argument("--c27-arithmetic-report", action="store_true",
                        help="classify C_27 full-unit candidates by Gaussian "
                             "residue-pair, factor residues, and boxed-join status")
    parser.add_argument("--c21-arithmetic-report", action="store_true",
                        help="classify C_21 sqrt21 candidates by component-join "
                             "status and factor residues")
    parser.add_argument("--prime-subtorus-report", action="store_true",
                        help="evaluate the exact prime sub-torus component join "
                             "on every low-degree prime t' lane")
    parser.add_argument("--divisor-lattice-audit", action="store_true",
                        help="Machine-verify the lem:orbit-census formula at "
                             "every divisor node and list the guaranteed "
                             "criterion nodes of thm:divisor-selection.")
    parser.add_argument("--full-torus-rowsum-audit", action="store_true",
                        help="Machine-verify thm:full-torus-rowsum against "
                             "exact top-node decisions and list the "
                             "small-image residual regime.")
    parser.add_argument("--h3-hierarchy-audit", action="store_true",
                        help="Machine-verify the h=3 closed forms "
                             "(prop:h3-augmentation-reps, residue and gcd "
                             "corollaries) against the DP on every h=3 "
                             "node; list PAF-layer survivors.")
    parser.add_argument("--two-orbit-rep-audit", action="store_true",
                        help="Machine-verify thm:two-orbit-reps against the "
                             "scalar enumeration on every two-orbit node, "
                             "plus its corollaries and the prime h=3 "
                             "support-sum closed form.")
    parser.add_argument("--h3-finite-report", action="store_true",
                        help="test the h=3 support/augmentation obstruction "
                             "against the remaining finite-certificate panel lanes")
    parser.add_argument("--signed-guard-report", action="store_true",
                        help="audit eps=-1 multiplier cases and whether any "
                             "multi-prime classical survivor needs signed "
                             "marginal algebra")
    parser.add_argument("--max-degree", type=int,
                        default=PRIME_SUBTORUS_MAX_DEGREE,
                        help="degree cap for --prime-subtorus-report")
    parser.add_argument("--local-pass-prime-degree", type=int, default=15,
                        help="degree cap for extra prime-subtorus checks in "
                             "--local-pass-report")
    parser.add_argument("--local-pass-prime-outer-cap", type=int, default=20_000_000,
                        help="reduced period-lattice point cap for extra "
                             "prime-subtorus checks in --local-pass-report")
    parser.add_argument("--local-pass-integer-cap", type=int, default=3_000_000,
                        help="side-assignment cap for extra integer MITM checks "
                             "in --local-pass-report; use 0 to disable")
    parser.add_argument("--local-pass-integer-max-orbits", type=int, default=13,
                        help="skip extra integer MITM above this orbit count in "
                             "--local-pass-report")
    parser.add_argument("--limit", type=int, default=80)
    args = parser.parse_args(argv)

    if args.dichotomy_report:
        return dichotomy_report(args.qmax)
    if args.existential_divisor_report:
        return existential_divisor_report(
            args.qmax,
            summary_only=args.summary_only,
            dynamic_secondary=not args.no_dynamic_secondary,
            dynamic_full_torus=not args.no_dynamic_full_torus,
            dynamic_h3_augmentation=not args.no_dynamic_h3_augmentation,
        )
    if args.local_pass_report:
        return local_pass_report(
            args.qmax,
            args.limit,
            args.local_pass_prime_degree,
            args.local_pass_prime_outer_cap,
            args.local_pass_integer_cap,
            args.local_pass_integer_max_orbits,
        )
    if args.c27_arithmetic_report:
        return c27_arithmetic_report(args.qmax)
    if args.c21_arithmetic_report:
        return c21_arithmetic_report(args.qmax)
    if args.prime_subtorus_report:
        return prime_subtorus_report(args.qmax, args.max_degree)
    if args.h3_finite_report:
        return h3_finite_report()
    if args.divisor_lattice_audit:
        return divisor_lattice_audit(args.qmax, args.q, args.limit)
    if args.two_orbit_rep_audit:
        return two_orbit_rep_audit(args.qmax, args.q, args.limit)
    if args.full_torus_rowsum_audit:
        return full_torus_rowsum_audit(args.qmax, args.q, args.limit)
    if args.h3_hierarchy_audit:
        return h3_hierarchy_audit(args.qmax, args.q, args.limit)
    if args.signed_guard_report:
        return signed_guard_report(args.qmax)

    if args.q:
        qs = sorted(set(args.q))
    else:
        qs = [q for q in range(5, args.qmax + 1, 4) if is_composite(q)]
    if args.multi_prime:
        qs = [q for q in qs if is_multi_prime(q)]
    if args.blind_spot:
        qs = [
            q for q in qs
            if not two_squares_fail(q) and not selfconj_kill(q, (q + 1) // 2)
        ]

    rows = []
    for q in qs:
        if args.all_divisors:
            for sig in candidates(q, proper=not args.include_full):
                rows.append((q, sig, family(sig)))
        else:
            sig = best_signature(q, proper=not args.include_full)
            if sig is None:
                continue
            rows.append((q, sig, family(sig)))
    if args.prime_square_lift:
        rows = [
            (q, sig, fam)
            for q, sig, fam in rows
            if prime_square_pm1_lift_base(sig) is not None
        ]

    counts = Counter(fam for _q, _sig, fam in rows)
    outcome_counts = Counter(
        KNOWN_MARGINAL_OUTCOMES.get((q, sig["tp"]), ("unrecorded", ""))[0]
        for q, sig, _fam in rows
    )
    print(
        f"q_count={len(rows)} qmax={args.qmax} blind_spot={args.blind_spot} "
        f"multi_prime={args.multi_prime} proper_only={not args.include_full} "
        f"all_divisors={args.all_divisors}"
    )
    print("family counts:")
    for fam, count in counts.most_common():
        print(f"  {fam}: {count}")
    if args.known_outcomes:
        print("known outcome counts:")
        for outcome, count in outcome_counts.most_common():
            print(f"  {outcome}: {count}")
    print()
    tp_header = "t'" if args.all_divisors else "best_t'"
    outcome_header = " outcome  evidence" if args.known_outcomes else ""
    print(
        f"q      q_factor        t_factor        {tp_header:<7} h   |V'| "
        f"orb family                  sizes{outcome_header}"
    )
    for q, sig, fam in rows[:args.limit]:
        sizes = ",".join(str(s) for s in sig["sizes"][:8])
        if len(sig["sizes"]) > 8:
            sizes += ",..."
        p = prime_square_pm1_lift_base(sig)
        fam_label = f"{fam}(p={p})" if p is not None else fam
        outcome = ""
        if args.known_outcomes:
            status, evidence = KNOWN_MARGINAL_OUTCOMES.get(
                (q, sig["tp"]), ("unrecorded", "")
            )
            outcome = f" {status:<8} {evidence}"
        print(
            f"{q:<6} {fmt_factor(q):<14} {fmt_factor(sig['t']):<15} "
            f"{sig['tp']:<7} {sig['h']:<3} {sig['Vp_size']:<4} "
            f"{sig['n_orbits']:<3} {fam_label:<27} {sizes}{outcome}"
        )
    if len(rows) > args.limit:
        print(f"... ({len(rows) - args.limit} more)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env bash
# Attempted per-q scanner example, per handoff spec:
#   python orbit_signature_scan.py --q 1469 --existential-divisor-report --summary-only
#
# ACTUAL BEHAVIOR (confirmed by running it and by reading the source): the
# --existential-divisor-report branch calls existential_divisor_report(qmax,
# ...) and never consumes --q. (The "ignores the other filter flags" note in
# --help belongs to the adjacent --dichotomy-report entry, not this one; the
# earlier version of this comment misattributed that string.) So --q 1469 does
# NOT restrict the run to q=1469: the command runs the full qmax=2000
# existential-divisor census, as it would with no --q flag at all. This is not a per-q report; per the handoff's own fallback
# instruction ("if it cannot produce per-q output in budget, log that and
# skip -- do not force"), we do not force a per-q variant and instead
# record the real, full-census behavior.
#
# The run completed in ~12.5s (well inside the 120s box). q=1469 itself
# does surface inside the run, in the internal period-lattice diagnostics
# (see scanner_existential_divisor_output.txt lines ~133-140: q=1469 is
# processed at ell=5 and ell=7), and separately appears in the paper's
# closed-order ledger for q<=2000. The --summary-only flag suppresses the
# per-q *branch* rows, not these lower-level diagnostic lines.

set -euo pipefail
cd "$(dirname "$0")/.."
python orbit_signature_scan.py --q 1469 --existential-divisor-report --summary-only

# Recorded real output (ran 2026-07-07, ~12.5s, from turyn-converse/code/):
# full 219-line transcript saved verbatim in
#   examples/scanner_existential_divisor_output.txt
# Tail (the branch-summary section actually gated by --summary-only):
#
# == Existential divisor theorem scaffold ==
# classification: composite multi-prime q surviving two-squares and self-conjugacy, qmax=2000
# A q is in the first branch only if some proper divisor actually fires by a written quantified criterion, not merely because a matching lane exists.
#
#
# branch counts:
#   has_quantified_firing_divisor: 81
#     first examples: 65, 153, 185, 221, 245, 265, 305, 365, 369, 377
#   has_quantified_full_torus: 29
#     first examples: 85, 145, 205, 225, 325, 445, 481, 565, 585, 697
#   has_projection_gluing_obstruction: 1
#     first examples: 441
# closure mechanisms:
#   scalar_unsat: 45
#   no_side_vector: 19
#   rowsum_unsat: 14
#   h3_support_sum_impossible: 11
#   h3_support_augmentation_impossible: 8
#   component_join_unsat: 5
#   component_unsat: 3
#   no_residue_pair: 3
#   small_h_box_cut: 1
#   linear_projection_unsat: 1
#   h3_support_paf_unsat: 1
#
# next theorem obligation:
#   prove from M(q) that every q enters has_quantified_firing_divisor
#   or has_quantified_full_torus, or replace the remaining named
#   branches by sharper firing/gluing criteria.  The proof must
#   quantify over all divisors t'|t, not over the shape-ranked
#   best_signature() divisor.

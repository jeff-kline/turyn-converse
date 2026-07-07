# code/

Verification and census scripts supporting the claims in `../paper/capstone.pdf`.
Copied verbatim from the source repo (`source-repo@2c02e32`,
`turyn_theory/python/`); see `../BUILD_LOG.md` for the provenance record.

## Setup

```
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

Only third-party dependency: numpy.

## Files

- `composite_multiplier_scan.py`, `multiplier_reduced_decision.py` — base
  multiplier-group and factorization utilities; imported by the scripts below.
- `marginal_orbit_algebra.py`, `orbit_signature_scan.py` — orbit/marginal
  algebra machinery and the main CLI scanner (`orbit_signature_scan.py --help`
  lists its report modes).
- `density_w_formula_probe.py`, `density_r3_goodset_probe.py`,
  `density_semiprime_census.py` — density/census probes used for the lane
  ($q=6\ell-1$) results in the paper.

Import graph (verified by direct `import` from this directory):
`composite_multiplier_scan` → (none of these) → `multiplier_reduced_decision`
→ `marginal_orbit_algebra` → `orbit_signature_scan` → the three
`density_*` probes. All resolve within this directory: the shipped `.py` set is
exactly the manifest named in the build handoff.

**Not shipped (diagnostic-table generators).** The paper additionally cites two
generators, `condition_r_realization.py` and `condition_c_absorption.py`, which
emit the two "(R)"/"(C)" *diagnostic* tables (rows marked "cond." are explicitly
not used as certified closures). These are retained in the source repo and are
**not** shipped here: they pull in the PARI/gp-driven layer-B subtree
(`ideal_norm_count`, `layer_b_ray_diagnostic`, `ray_defect_probe`, …) and would
break this directory's numpy-only footprint. Their machine-readable outputs are
shipped as data instead — see `data/`.

## Example invocations

See `examples/`:

- `density_probe.sh` — runs `density_w_formula_probe.py 100000`; recorded
  output inline.
- `scanner_existential_divisor.sh` — runs
  `orbit_signature_scan.py --q 1469 --existential-divisor-report --summary-only`;
  see the script's header comment for a caveat (`--existential-divisor-report`
  ignores `--q` and always runs the full qmax=2000 census — this is documented
  in the tool's own `--help` text). Full raw transcript in
  `scanner_existential_divisor_output.txt`.

## Transcription checker

`tools/check_transcription.py` extracts every theorem/lemma/proposition/
corollary/definition/remark/conjecture environment from `../paper/capstone.tex`
and checks it appears identically (whitespace-normalized) in
`../paper/companion/turyn_converse.tex`. See `../BUILD_LOG.md` for its output.

## data/

Machine-readable caches for two tables printed in the paper:
`condition_r_realization_qmax2000_degree40.jsonl` and
`condition_c_absorption_qmax2000_degree40.jsonl` — the diagnostic (R)/(C) tables
(their generators are not shipped; see "Not shipped" above).

## gp/

PARI/gp verification of the isolated imaginary-quadratic class-group inputs to
the Tier-1 fold-tower kills (q=5185, q=62305): `fold_tower_anchors.gp` plus the
recorded transcript `fold_tower_anchors.out.txt`. The full degree-40 fold-tower
class groups are computed by the source-repo scripts (gp-driven) and are stated
in the paper as explicit GRH hypotheses; this bundle reproduces the cheap
quadratic anchors they rest on (e.g. `h(-10372)=24`). Run: `gp -q fold_tower_anchors.gp`.

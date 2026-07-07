# Toward a converse of Turyn's theorem

Turyn pairs (symmetric circulants R,S of odd order t, R²+S²=(2t−1)I) exist
whenever q=2t−1 is a prime power; the conjecture is that they exist ONLY
then. This repo hosts a theorem program toward that converse: a selection
theorem reducing the conjecture to per-family firing criteria, written
criteria closing every self-conjugacy-blind multi-prime composite q≤2000
(apparently first determinations: 1469, 1937, 1325; under GRH: 5185,
62305; closed-table caveat — see STATUS.md), and unconditional lane
theorems at q=6ℓ−1 with an explicitly-hypothesized density program.

## Read this first

`paper/capstone.pdf` — the paper. `STATUS.md` — every principal claim with
its verification tier. `problems/` — open problems, stated to be worked on.

## Verify something in 60 seconds

```
python3 -m venv .venv
.venv/bin/pip install -r code/requirements.txt
cd code && ../.venv/bin/python density_w_formula_probe.py 100000
```

Recorded output (ran 2026-07-07, ~3.2s):
```
qmax=100000: members=718 not_all_plus=0 mismatches=0 omega_hist={2: 467, 3: 227, 4: 24}
w<4 members: [(9185, 1531, {5: 1, 11: 1, 167: 1})]
total 3.2s
```

## Layout

- `paper/capstone.tex` / `paper/capstone.pdf` — the paper.
- `paper/companion/turyn_converse.tex` — the unedited source paper this was
  assembled from, kept verbatim for transcription-checking.
  **Contributors:** any edit to a theorem-like environment
  (theorem/lemma/proposition/corollary/definition/remark/conjecture) in
  `paper/capstone.tex` must be mirrored here verbatim, or
  `code/tools/check_transcription.py` will fail.
- `code/` — the verification/census scripts backing the paper's claims
  (see `code/README.md`).
- `problems/` — open problems extracted from the paper and working notes,
  stated for others to attack.
- `STATUS.md` — tier (proof strength) of every principal claim.
- `BUILD_LOG.md` — how this repository was assembled from the source
  working repo, including every check run.

## Authorship

See `AUTHORSHIP.md`.

## License

This project is licensed under the GNU General Public License v3.0 — see
[`LICENSE`](LICENSE) for the full text.

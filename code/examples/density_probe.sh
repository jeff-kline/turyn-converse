#!/usr/bin/env bash
# Verified example: density_w_formula_probe.py, run from code/ against the
# venv used throughout this repo's provenance (source repo's .venv).
#
# Setup (once):
#   python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
#
# Then, from code/:
#   .venv/bin/python density_w_formula_probe.py 100000

set -euo pipefail
cd "$(dirname "$0")/.."
python density_w_formula_probe.py 100000

# Recorded real output (ran 2026-07-07, ~3.2s, from turyn-converse/code/):
#
# [cost] 0.63 ms/member after 100; crude ETA 13s
# qmax=100000: members=718 not_all_plus=0 mismatches=0 omega_hist={2: 467, 3: 227, 4: 24}
# w<4 members: [(9185, 1531, {5: 1, 11: 1, 167: 1})]
# total 3.2s

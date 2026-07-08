"""Atomically merge one batch of audit verdicts into code/audit/verdicts.json.

This is the CHECKPOINT mechanism. Each audit batch writes its result through
this tool the moment it finishes, so verdicts.json is a durable, resumable
checkpoint: an interruption loses at most the single in-flight batch, and
audit_worklist.py re-emits only what is still pending.

Safety:
  * Writes atomically (temp file + os.replace) so a crash never truncates.
  * Refuses to silently overwrite an existing DIFFERENT verdict for a key
    (protects e.g. a logged Opus-vs-Fable disagreement); use --force to
    override, which prints the old->new change.
  * Warns on any key that is not one of the 129 known environments (catches a
    hallucinated / mistyped label before it pollutes the ledger).

Usage:
  ~/.venvs/claude/bin/python code/tools/merge_verdicts.py batch.json
  ~/.venvs/claude/bin/python code/tools/merge_verdicts.py batch.json --force
  cat batch.json | ~/.venvs/claude/bin/python code/tools/merge_verdicts.py -

batch.json schema:  { "<label-or-num:X.Y>": {"verdict": "...", "note": "...",
                      "by": "...", "date": "..."}, ... }
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_audit_ledger import walk_environments, CAPSTONE, VERDICTS  # noqa: E402

VALID_VERDICTS = {"SOUND", "GAP", "OVERCLAIM", "UNVERIFIED", "FIXED", "FIXED-recommend"}


def known_keys() -> set[str]:
    keys = set()
    for number, _env, label, _title in walk_environments(CAPSTONE.read_text()):
        keys.add(label if label else f"num:{number}")
    return keys


def atomic_write(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(data, f, indent=2, sort_keys=True)
            f.write("\n")
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("batch", help="path to batch JSON, or '-' for stdin")
    ap.add_argument("--force", action="store_true",
                    help="overwrite an existing differing verdict (prints the change)")
    args = ap.parse_args()

    raw = sys.stdin.read() if args.batch == "-" else Path(args.batch).read_text()
    batch = json.loads(raw)
    if not isinstance(batch, dict):
        print("ERROR: batch must be a JSON object keyed by label", file=sys.stderr)
        return 2

    existing = json.loads(VERDICTS.read_text()) if VERDICTS.exists() else {}
    valid_keys = known_keys()

    added, updated, skipped, unknown, badverdict = 0, 0, 0, [], []
    for k, v in batch.items():
        if k not in valid_keys:
            unknown.append(k)
            continue
        if not isinstance(v, dict) or v.get("verdict") not in VALID_VERDICTS:
            badverdict.append(k)
            continue
        if k in existing and existing[k] != v:
            if not args.force:
                print(f"SKIP (differs, use --force): {k}: "
                      f"{existing[k].get('verdict')} -> {v.get('verdict')}")
                skipped += 1
                continue
            print(f"OVERWRITE: {k}: {existing[k].get('verdict')} -> {v.get('verdict')}")
            existing[k] = v
            updated += 1
        elif k in existing:
            skipped += 1  # identical, idempotent re-run
        else:
            existing[k] = v
            added += 1

    if badverdict:
        print(f"ERROR: {len(badverdict)} entries have a missing/invalid verdict "
              f"(allowed {sorted(VALID_VERDICTS)}): {badverdict}", file=sys.stderr)
        return 2
    if unknown:
        print(f"WARNING: {len(unknown)} keys are NOT known environments, dropped: "
              f"{unknown}", file=sys.stderr)

    atomic_write(VERDICTS, existing)
    total = len(valid_keys)
    print(f"merged: +{added} added, ~{updated} updated, ={skipped} unchanged. "
          f"verdicts.json now {len(existing)}/{total} environments.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

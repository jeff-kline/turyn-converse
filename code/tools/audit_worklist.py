"""Emit the PENDING audit worklist, partitioned by COUNT (not by section).

Section 4 alone holds 103 of the 129 theorem-like environments, so batching by
section would overload one agent. This tool walks the environments in document
order and chunks the ones WITHOUT a verdict yet into fixed-size batches, so:

  * partitioning is balanced by count (--batch-size), and
  * the run is RESUMABLE: anything already in code/audit/verdicts.json is
    skipped, so re-running after an interruption emits only what is left.

Run: ~/.venvs/claude/bin/python code/tools/audit_worklist.py --batch-size 10
     ~/.venvs/claude/bin/python code/tools/audit_worklist.py --json   (machine)
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_audit_ledger import walk_environments, CAPSTONE, VERDICTS, ENV_TITLE  # noqa: E402


def vkey(number: str, label: str) -> str:
    return label if label else f"num:{number}"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--batch-size", type=int, default=10)
    ap.add_argument("--json", action="store_true", help="emit machine-readable batches")
    args = ap.parse_args()

    rows = list(walk_environments(CAPSTONE.read_text()))
    verdicts = json.loads(VERDICTS.read_text()) if VERDICTS.exists() else {}

    pending = []
    done = 0
    for number, env, label, title in rows:
        k = vkey(number, label)
        if verdicts.get(k, {}).get("verdict"):
            done += 1
            continue
        pending.append(
            {
                "key": k,
                "number": number,
                "type": ENV_TITLE[env],
                "label": label or "",
                "title": title or "",
            }
        )

    size = max(1, args.batch_size)
    batches = [pending[i : i + size] for i in range(0, len(pending), size)]

    if args.json:
        print(json.dumps({"total": len(rows), "done": done, "pending": len(pending),
                          "batch_size": size, "batches": batches}, indent=2))
        return 0

    print(f"total={len(rows)}  done={done}  pending={len(pending)}  "
          f"batch_size={size}  batches={len(batches)}")
    if not pending:
        print("ALL ENVIRONMENTS HAVE A VERDICT — audit complete.")
        return 0
    for bi, batch in enumerate(batches, 1):
        keys = " ".join(r["number"] for r in batch)
        print(f"\n--- batch {bi}/{len(batches)}  ({len(batch)} envs: {keys}) ---")
        for r in batch:
            lab = r["label"] or "(unlabeled)"
            print(f"  {r['number']:>6}  {r['type']:<11}  {lab:<34}  {r['title']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

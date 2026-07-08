# Per-environment audit verdicts

`verdicts.json` maps a theorem-like environment's LaTeX `\label` to the verdict
an adversarial audit reached for that specific statement and proof. It is the
machine-readable backing for the `Audit verdict` column of `../../AUDIT_LEDGER.md`.

## Schema

```json
{
  "<label>": {
    "verdict": "SOUND | GAP | OVERCLAIM | UNVERIFIED | FIXED",
    "note":    "one-line justification (what was checked / what was found)",
    "by":      "model that signed the row off, e.g. claude-opus-4-8",
    "date":    "YYYY-MM-DD"
  }
}
```

Only `verdict` and `note` are rendered into the ledger; `by`/`date` are
provenance and are ignored by the generator.

### Verdict vocabulary

- **SOUND** — statement and proof reconstructed adversarially; no defect found.
- **GAP** — the proof does not establish the statement as written (missing step,
  unjustified inference, undischarged case). Must be logged in `AUDIT_LOG.md`.
- **OVERCLAIM** — statement claims more than the proof/evidence supports, or the
  tier is wrong. Must be logged.
- **UNVERIFIED** — could not be closed within the audit's power/budget (e.g. an
  external class-group input, an imported sieve constant); an honest limitation,
  not a pass.
- **FIXED** — a defect was found and corrected in this audit; note the change.

## Regenerate the ledger

```
~/.venvs/claude/bin/python code/tools/build_audit_ledger.py
```

Reads this file, merges verdicts by label, cross-validates every number against
`paper/capstone.aux`, and rewrites `AUDIT_LEDGER.md`. Never hand-edit the ledger;
edit `verdicts.json` and regenerate.

"""Build AUDIT_LEDGER.md: one row per theorem-like environment in capstone.tex.

Walks paper/capstone.tex in document order, assigning the shared
[section]-based theorem number to each of the 129 theorem-like environments
(the same 7 environment types check_transcription.py counts). Cross-validates
every computed number against paper/capstone.aux for the labeled environments;
aborts if any computed number disagrees with LaTeX's own numbering.

Merges an optional per-label verdict file (code/audit/verdicts.json) so an
adversarial audit can populate the "Audit verdict" column and re-generate the
ledger without losing the skeleton.

Run: ~/.venvs/claude/bin/python code/tools/build_audit_ledger.py
"""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CAPSTONE = ROOT / "paper" / "capstone.tex"
AUX = ROOT / "paper" / "capstone.aux"
VERDICTS = ROOT / "code" / "audit" / "verdicts.json"
OUT = ROOT / "AUDIT_LEDGER.md"

ENVIRONMENTS = [
    "theorem",
    "lemma",
    "proposition",
    "corollary",
    "definition",
    "remark",
    "conjecture",
]
ENV_TITLE = {
    "theorem": "Theorem",
    "lemma": "Lemma",
    "proposition": "Proposition",
    "corollary": "Corollary",
    "definition": "Definition",
    "remark": "Remark",
    "conjecture": "Conjecture",
}

# Prior-audit coverage per label, distilled from AUDIT_LOG.md. Anything not
# listed is covered ONLY by the aggregate 129/129 full-coverage pass, whose
# per-environment ledger was a private artifact not preserved in the repo.
PRIOR = {
    # --- named principal claims (STATUS.md table); bucket-level verdicts ---
    "thm:divisor-selection": "Principal (Selection thm), T0; baseline L2a SOUND at bucket level; rem:selection-open flags headline as near-tautology.",
    "thm:two-orbit-reps": "Principal (Two-orbit criterion), T0; baseline L2a SOUND at bucket level.",
    "prop:h3-augmentation-reps": "Principal (h=3 hierarchy head), T0; L2a SOUND at bucket level; Fable-pass claims reconstruction; code-pass (AUDIT_LOG:143) says NOT re-audited there.",
    "thm:full-torus-rowsum": "Principal (row-sum bound + sharpness), T0; L2a SOUND at bucket level.",
    "thm:semiprime-converse": "Principal (semiprime lane), T0; L2a SOUND at bucket level.",
    "prop:lane-kill": "Principal (lane collapse), T0; L2a SOUND at bucket level.",
    "thm:dickson-family": "Principal (Dickson family), T2; F2 (capstone-local) added bibitems + wired cites; byte-mirrored.",
    "rem:chen-input": "Principal (hyp-(C) inputs), T2; F2 added bibitems; no exact citation for hyp (C) (disclosed).",
    "prop:small-factor-sieve": "Principal (small-factor sieve), T2(EQ3); DISCLOSED UNVERIFIED (imported sieve constants); density program not GRH-complete.",
    # --- environments named in specific findings/fixes ---
    "rem:blindspot": "Finding F1 (code-correctness): prose characterization corrected + 80/31 split; FIXED + mirrored.",
    "prop:pe-full-unit-nested": "Findings baseline#3 (y_{-1}:=0) and Fix3 (phi(p^{e-j})): two real proof-typos; BOTH FIXED, Fix3 verified 3 ways.",
    "prop:Lstar": "Fix2: conj:->prop: label prefix corrected; FIXED + mirrored.",
    "cor:c49-nested": "Fix4: prop:->cor: relabel + removed dead trailing label; FIXED.",
    "cor:c27-auto-box": "Fix5: h>=57->55 HELD (bound correct-but-loose, not a bug; per user, left as-is).",
    "rem:parity-wall": "Finding baseline#6: member-list class scoping tightened; FIXED + mirrored.",
    "rem:lane-density-status": "Citation/wording touched (F-set); byte-mirror-checked capstone==companion.",
    "cor:h3-support-sum-gcd": "Deferred (baseline Open): candidate demote-to-remark (self-described coarse; superseded by prop above).",
    "prop:q549-fiveorbit": "Terminal kill certificate; L2a disclosed that individual finite emptiness certs were not each re-run.",
}


def load_aux_numbers() -> dict[str, tuple[str, str, str]]:
    """label -> (number, page, title) for theorem-counter labels only."""
    out = {}
    pat = re.compile(
        r"\\newlabel\{([^}]+)\}\{\{([^}]*)\}\{([^}]*)\}\{([^}]*)\}\{(theorem\.[^}]*)\}"
    )
    for m in pat.finditer(AUX.read_text()):
        label, number, page, title, _anchor = m.groups()
        out[label] = (number, page, title)
    return out


def walk_environments(tex: str):
    """Yield (number, env, label, title) in document order.

    Reproduces LaTeX's shared [section]-based theorem counter: reset on each
    numbered \\section, letters after \\appendix; incremented on every one of
    the 7 theorem-like \\begin{...}.
    """
    begin_re = re.compile(r"\\begin\{(" + "|".join(ENVIRONMENTS) + r")\}(\s*\[)?")
    section_re = re.compile(r"\\section\b(\*)?")
    appendix_re = re.compile(r"\\appendix\b")
    label_re = re.compile(r"\\label\{([^}]+)\}")
    title_re = re.compile(r"\A\s*\[")

    section_num = 0  # numeric section index before \appendix
    appendix_idx = 0  # 0 before \appendix; 1->A, 2->B after
    in_appendix = False
    theorem_n = 0

    # Tokenize by scanning for the three markers in order.
    events = []
    for m in section_re.finditer(tex):
        events.append((m.start(), "section", m.group(1) is not None))
    for m in appendix_re.finditer(tex):
        events.append((m.start(), "appendix", None))
    for m in begin_re.finditer(tex):
        events.append((m.start(), "env", m))
    events.sort(key=lambda e: e[0])

    for pos, kind, payload in events:
        if kind == "appendix":
            in_appendix = True
            appendix_idx = 0
            theorem_n = 0
        elif kind == "section":
            starred = payload
            if not starred:
                if in_appendix:
                    appendix_idx += 1
                else:
                    section_num += 1
                theorem_n = 0
        else:  # env
            m = payload
            env = m.group(1)
            theorem_n += 1
            if in_appendix:
                sec_label = chr(ord("A") + appendix_idx - 1) if appendix_idx >= 1 else "A"
            else:
                sec_label = str(section_num)
            number = f"{sec_label}.{theorem_n}"
            # grab the full block to find label + optional title
            block_m = re.compile(
                r"\\begin\{" + env + r"\}.*?\\end\{" + env + r"\}", re.DOTALL
            ).match(tex, pos)
            block = block_m.group(0) if block_m else tex[pos:pos + 400]
            lbl = label_re.search(block)
            label = lbl.group(1) if lbl else ""
            title = ""
            tm = re.match(r"\\begin\{" + env + r"\}\s*\[", block)
            if tm:
                # balanced-ish single-level bracket capture
                rest = block[tm.end() - 1:]
                depth = 0
                buf = []
                for ch in rest:
                    if ch == "[":
                        depth += 1
                        if depth == 1:
                            continue
                    elif ch == "]":
                        depth -= 1
                        if depth == 0:
                            break
                    buf.append(ch)
                title = "".join(buf).strip()
            yield number, env, label, title


def main() -> int:
    aux = load_aux_numbers()
    rows = list(walk_environments(CAPSTONE.read_text()))

    # validate computed numbers against aux for labeled rows
    mism = []
    for number, env, label, title in rows:
        if label and label in aux:
            aux_num = aux[label][0]
            if aux_num != number:
                mism.append((label, number, aux_num))
    if mism:
        print("NUMBERING MISMATCH vs aux (walker is wrong, aborting):")
        for label, comp, auxn in mism:
            print(f"  {label}: computed {comp} != aux {auxn}")
        return 1

    # warn on any PRIOR keys that don't correspond to a real label
    real_labels = {label for _, _, label, _ in rows if label}
    for k in PRIOR:
        if k not in real_labels:
            print(f"WARNING: PRIOR annotation key not a live env label: {k}")

    verdicts = {}
    if VERDICTS.exists():
        verdicts = json.loads(VERDICTS.read_text())

    def vkey(number: str, label: str) -> str:
        # verdicts are keyed by label; the 2 unlabeled environments fall back
        # to a stable number key so they are still checkpointable.
        return label if label else f"num:{number}"

    n = len(rows)
    covered = sum(1 for _, _, label, _ in rows if label in PRIOR)
    with_verdict = sum(
        1 for number, _, label, _ in rows if verdicts.get(vkey(number, label), {}).get("verdict")
    )

    lines = []
    lines.append("# Per-environment audit ledger")
    lines.append("")
    lines.append(
        f"One row per theorem-like environment in `paper/capstone.tex` "
        f"(**{n}** total: the same 7 environment types "
        "`code/tools/check_transcription.py` counts). Numbers are LaTeX's own "
        "shared `[section]` theorem counter, computed by walking the document "
        "and **cross-validated against `paper/capstone.aux`** (0 mismatches) — "
        "regenerate with `code/tools/build_audit_ledger.py`."
    )
    lines.append("")
    lines.append("**Columns.**")
    lines.append("")
    lines.append(
        "- *Prior coverage* — what `AUDIT_LOG.md` records about this specific "
        "environment. `aggregate-only` means it was covered solely by the "
        "129/129 full-coverage count, whose per-row ledger was a private "
        "artifact **not** preserved in the repo — i.e. no independently "
        "checkable per-environment record existed before this ledger."
    )
    lines.append(
        "- *Audit verdict* — populated by the complete adversarial audit "
        "(see the run recorded in `AUDIT_LOG.md`). `— pending` until that "
        "audit signs the row off. Sourced from `code/audit/verdicts.json`."
    )
    lines.append("")
    lines.append(
        f"**Status:** {n} environments · {covered} with a prior per-env note · "
        f"{with_verdict} with a new-audit verdict."
    )
    lines.append("")
    lines.append("| # | Type | Label | Title | Prior coverage | Audit verdict |")
    lines.append("|---|---|---|---|---|---|")
    for number, env, label, title in rows:
        typ = ENV_TITLE[env]
        lab = f"`{label}`" if label else "*(unlabeled)*"
        ttl = title if title else "—"
        prior = PRIOR.get(label, "aggregate-only")
        v = verdicts.get(vkey(number, label), {})
        verdict = v.get("verdict", "— pending")
        note = v.get("note", "")
        vcell = verdict if not note else f"{verdict} — {note}"
        # escape pipes in free text
        ttl = ttl.replace("|", "\\|")
        prior = prior.replace("|", "\\|")
        vcell = vcell.replace("|", "\\|")
        lines.append(
            f"| {number} | {typ} | {lab} | {ttl} | {prior} | {vcell} |"
        )
    lines.append("")
    OUT.write_text("\n".join(lines) + "\n")
    print(f"wrote {OUT} : {n} rows, {covered} prior-annotated, {with_verdict} verdicts")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

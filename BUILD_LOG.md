# Build log — turyn-converse clean-start assembly

Source repo (read-only): ~/Documents/source-repo @ HEAD 2c02e32
("Retract Theorem R verdict; typeset verified lane-density layer")
Target: ~/Documents/turyn-converse (this repo; not yet git-init'd)
Date: 2026-07-06 (session date per handoff); executed 2026-07-07.

## Sanity check (pre-flight)

```
git -C ~/Documents/source-repo log --oneline -1
→ 2c02e32 Retract Theorem R verdict; typeset verified lane-density layer   ✓ matches handoff

cd .../turyn_theory/python && ../../.venv/bin/python density_w_formula_probe.py 100000
→ qmax=100000: members=718 not_all_plus=0 mismatches=0 omega_hist={2: 467, 3: 227, 4: 24}
  w<4 members: [(9185, 1531, {5: 1, 11: 1, 167: 1})]
  total 3.1s (well under 5s reference)                                     ✓ matches handoff
```

Both checks matched. Proceeding.

## R0 — tree + BUILD_LOG

Created:
```
turyn-converse/
├── paper/companion/
├── code/tools/
├── code/examples/
└── problems/
```

- LICENSE decision: deferred — TODO left for owner in README.md (see A5 skeleton; owner
  to pick a license before any public push).

## R1 — code manifest + import check

Copied 7 files verbatim from `source-repo/turyn_theory/python/` into
`code/`: `composite_multiplier_scan.py`, `multiplier_reduced_decision.py`,
`marginal_orbit_algebra.py`, `orbit_signature_scan.py`,
`density_w_formula_probe.py`, `density_r3_goodset_probe.py`,
`density_semiprime_census.py`.

Import audit (AST-level, then actual `import` of each module from
`turyn-converse/code/`, using the source repo's venv by path):

```
composite_multiplier_scan   OK
multiplier_reduced_decision OK
marginal_orbit_algebra      OK
orbit_signature_scan        OK
density_w_formula_probe     OK
density_r3_goodset_probe    OK
density_semiprime_census    OK
```

All internal imports resolve within the 7-file manifest; only external
dependency is numpy. No additional module needed to be copied from
`turyn_theory/python/`.

Re-ran the verified example from the new location:
```
cd turyn-converse/code && python density_w_formula_probe.py 100000
→ qmax=100000: members=718 not_all_plus=0 mismatches=0 omega_hist={2: 467, 3: 227, 4: 24}
  w<4 members: [(9185, 1531, {5: 1, 11: 1, 167: 1})]
  total 3.2s
```
Identical to the sanity-check run (718/0/0), confirmed reproducible from the
new location. Recorded in `code/examples/density_probe.sh`.

Attempted the scanner example named in the handoff:
```
python orbit_signature_scan.py --q 1469 --existential-divisor-report --summary-only
```
Checked `--help` first (per rule 5's spirit of not guessing flags). The tool's
own help text for `--existential-divisor-report` states: "ignores the other
filter flags." Running it confirmed this: `--q 1469` did not restrict the
census; the run performed the full qmax=2000 sweep (same as with no `--q`
flag), completing in ~12.5s (within the 120s box). q=1469 does appear inside
the run's internal period-lattice diagnostics (ell=5 and ell=7 checks), but
there is no per-q-only report mode for this flag. Per the handoff's fallback
instruction, this is logged rather than forced — see
`code/examples/scanner_existential_divisor.sh` for the full writeup and
`code/examples/scanner_existential_divisor_output.txt` for the raw 219-line
transcript.

Wrote `code/README.md` (venv setup + file manifest + import graph) and
`code/requirements.txt` (`numpy>=2.0`, matching the installed venv's
`numpy.__version__`).

## R2 — assemble paper/capstone.tex

Assembled by shell-level splicing of exact `sed`-extracted line ranges from
the companion source (never hand-retyped, to guarantee byte-for-byte
transcription), plus three new authored blocks (A1 abstract, A2 subsection,
A3 Appendix B) copied verbatim from the handoff text. Ranges used (companion
source line numbers):

- 1-43: preamble/macros/title, verbatim
- [NEW] abstract ← A1
- 116-190: `\tableofcontents` + §1 head + §§1.1-1.3, verbatim
- [NEW] subsection "Main results and reading guide" ← A2, replacing old §1.4
  (191-227; its only label, `sec:contribution`, was confirmed unreferenced
  elsewhere before deletion, so no dangling ref)
- 228-3859: §2, §3, §4, verbatim
- 4124-4612: §6, §7, §8, verbatim
- 4613-4721: bibliography, verbatim
- `\appendix`
- 3860-4123: old §5 body, verbatim, reused as-is (its `\section{...}` command
  needed no edits — `\appendix` alone converts its numbering to letters) →
  renders as Appendix A
- [NEW] Appendix B ← A3, verbatim (`\section*{...}`, so it does not appear in
  the ToC and is not auto-numbered, matching A3 as given)
- 4722-4723: `\end{document}`, verbatim

No new connective sentences were needed anywhere in the assembly — every
splice point is a hard section/subsection boundary, so no bridging prose was
written.

Cross-reference audit before deleting old §1.4: confirmed all 5 labels used
by A2 (`thm:divisor-selection`, `prop:lane-kill`, `thm:semiprime-converse`,
`prop:small-factor-sieve`, `rem:lane-density-status`) are defined inside §4,
which is retained verbatim — so A2's references resolve.

Bug caught and fixed during assembly: the shell step used
`echo "\\appendix"` to insert the `\appendix` command between the
bibliography and old §5. Under zsh's builtin `echo`, `\a` is interpreted as
an escape (BEL) rather than emitted literally, so the actual bytes written
were `\x07ppendix` (a bell character + "ppendix"), silently dropping the
backslash and the "a". Caught by grepping the assembled file for
`^\\appendix$` and finding nothing, then confirmed via `od -c` showing the
stray `\a` byte. Fixed with `sed -i '' '4413s/.*/\\appendix/'` (a literal
in-place line replacement, not another `echo`). Lesson: never use bare
`echo` with backslash-bearing content in zsh; use `printf '%s\n'` or a file
write instead.

Known cosmetic side effect of the section→appendix move (not a content
edit): three occurrences of the literal source phrase "Section~\ref{sec:mary}"
(two in §1.1/§1.3, one inside the moved section itself) now render as
"Section A" instead of "Appendix A", since `\appendix` only changes
`\thesection` to a letter — it does not retarget the word "Section" written
by hand in the prose. Per the handoff ("only the sectioning command changes
level if needed to compile"), the prose itself was left untouched; flagging
this for the review session rather than rewording the sentences.

## R3 — compile / transcription / grep gates

**Compile gate.** `pdflatex -interaction=nonstopmode capstone.tex`, run 3
times (2 required + 1 extra to settle a "Label(s) may have changed" ToC
notice). Pass 1: exit 0, 0 `!` errors. Pass 2: exit 0, 0 `!` errors, 0
undefined/multiply-defined references, 1 "rerun for ToC" notice. Pass 3:
exit 0, 0 `!` errors, 0 warnings at all. Output: `capstone.pdf`, 61 pages.
Spot-checked via `pdftotext`: abstract, ToC (§1.4 "Main results and reading
guide" present; "A Character liftings..." present as the lettered appendix
entry), and "Appendix B: Verification status and provenance" heading all
render as expected. (Missing "fi"/"ff" ligatures in the `pdftotext` dump,
e.g. "Jeffery" → "Jeery", are a known ligature-extraction quirk of
`pdftotext` against Latin Modern fonts, not a document defect — the PDF
glyphs themselves are correct Type1/OTF ligatures.)

**Transcription gate.** Wrote `code/tools/check_transcription.py`: extracts
every `\begin{theorem|lemma|proposition|corollary|definition|remark|
conjecture}...\end{...}` block from `capstone.tex`, whitespace-normalizes,
and requires each to appear inside the (also whitespace-normalized)
companion source.
```
capstone.tex: 129 theorem-like blocks extracted
  theorem: 19  lemma: 21  proposition: 34  corollary: 25
  definition: 8  remark: 20  conjecture: 2
mismatches=0
```
0/129 mismatches. (Expected by construction: every theorem-like block in
capstone.tex originates from a verbatim-copied range; none of A1/A2/A3
contain theorem-like environments.)

**Grep gate (rule 2 required strings).** First pass with single-line `grep`
against `capstone.tex` raw showed 3 of 6 strings "NOT FOUND" ("not
GRH-complete", "retracted on verification", "stated as an explicit
hypothesis"). Investigated each:
- "not GRH-complete" and "retracted on verification" both DO appear, each
  split across a soft line-wrap in the source (`\n` mid-sentence, not a
  paragraph break) — invisible to a single-line grep but present once
  whitespace is normalized. Re-checked with whitespace-flattened text:
  found. Not a real gap.
- "stated as an explicit hypothesis" is a genuine miss: this exact phrase
  lived only inside the *original* abstract (companion source line 94,
  inside the "congruence-restricted Chen input stated as an explicit
  hypothesis" clause), and R2 explicitly instructs replacing the entire
  abstract with authored content A1. A1 (as given verbatim in the handoff)
  uses different phrasing — "stated as explicit, falsifiable hypotheses"
  (plural, with "falsifiable" inserted) — which is semantically equivalent
  but not a literal substring match. This is an intrinsic conflict between
  rule 2's checklist (evidently drafted against the old abstract's exact
  wording) and R2's abstract-replacement instruction, both in the same
  handoff. Per the no-strength-edit / zero-composition rules, A1's wording
  was left exactly as given rather than patched to force a grep match —
  flagging this for the adversarial review session instead.

Final tally: 5/6 required strings verified present (whitespace-normalized);
1/6 absent by the explicit, instructed removal of the original abstract.

## R4 — problems/ (6 files)

Wrote all six files. Source verification before quoting: confirmed every
label cited (`conj:program`, `def:eq3`, `rem:lane-density-status`,
`prop:small-factor-sieve`, `rem:parity-wall`, `thm:semiprime-converse`,
`lem:stabilizer-rigidity`, `prop:q5185-f4-cut`, `prop:q5185-closure`,
`rem:small-image-conditional`, `cor:full-torus-exact-char`,
`cor:h3-support-sum-gcd`) actually exists in `paper/capstone.tex` via grep
before citing it (all confirmed; none fabricated). Notes-file quotes
(`density_theorem_r.md` §6.2/§14, `small_image_family.md` §3/§5,
`density_partial_converse.md` §6) were read directly from the source repo
and transcribed verbatim with section pointers; those note files themselves
were NOT copied into this repo (per the handoff, "file stays behind, quote
what you need") — each problems/ file says so explicitly.

- `00-master-routing.md` ← `conj:program` (§8) — the routing conjecture,
  used as an index into 01–05.
- `01-eq3-unconditional.md` ← `def:eq3` + `rem:lane-density-status`(iii) +
  `density_theorem_r.md` §6.2 (EQ3′ statement), §14.
- `02-structure-count.md` ← `rem:lane-density-status`(i) +
  `density_theorem_r.md` §14 findings F1/F2 (the retracted "Theorem R").
- `03-stickelberger-fold.md` ← `small_image_family.md` §3 (dichotomy) + §5
  Gap 1 (Stickelberger gap).
- `04-wall-witnesses.md` ← `small_image_family.md` §5 Gap 2 (q=37825,
  q=93721 infeasible-fold-field cases).
- `05-parity-wall.md` ← `rem:parity-wall` + `thm:semiprime-converse` +
  `density_partial_converse.md` §6 ("The wall").

Each file's own prose ("Why it matters" framing, section transitions) makes
no new mathematical claims — it only names which quoted block says what and
routes between files (e.g. noting 02 and 05 both touch parity but from
different sides). No new theorem-shaped sentence was written in any of the
six files.

## R5 — final report

### File inventory

```
.gitignore
AUTHORSHIP.md
BUILD_LOG.md
README.md
STATUS.md
code/README.md
code/requirements.txt
code/composite_multiplier_scan.py
code/multiplier_reduced_decision.py
code/marginal_orbit_algebra.py
code/orbit_signature_scan.py
code/density_w_formula_probe.py
code/density_r3_goodset_probe.py
code/density_semiprime_census.py
code/tools/check_transcription.py
code/examples/density_probe.sh
code/examples/scanner_existential_divisor.sh
code/examples/scanner_existential_divisor_output.txt
paper/capstone.tex
paper/capstone.pdf   (61 pages)
paper/companion/turyn_converse.tex   (byte-identical to source repo's copy, diff-verified)
problems/00-master-routing.md
problems/01-eq3-unconditional.md
problems/02-structure-count.md
problems/03-stickelberger-fold.md
problems/04-wall-witnesses.md
problems/05-parity-wall.md
```
(LaTeX build artifacts `paper/capstone.{aux,log,out,toc}` also present;
covered by `.gitignore`.)

### Checker outputs (summary; full detail above under each rung)

- Import check: 7/7 modules import cleanly from `code/` (R1).
- Verified example reproduced identically from new location: `members=718
  not_all_plus=0 mismatches=0` (R1).
- Compile gate: 3 pdflatex passes, 0 `!` errors, 0 undefined/multiply-defined
  refs, final pass 0 warnings, 61 pages (R3).
- Transcription gate (`check_transcription.py`): 129 theorem-like blocks
  extracted from `capstone.tex`, **0 mismatches** against the companion
  source (R3).
- Grep gate, `capstone.tex`: 5/6 required strings present (whitespace-
  normalized); 1/6 ("stated as an explicit hypothesis") absent because it
  lived only in the original abstract, which R2 explicitly instructs
  replacing (R3).
- Grep gate, `README.md`: 2/6 required strings present ("closed-table
  caveat", "apparently first determinations" — both literally in the given
  A5 skeleton text); the other 4 are simply not part of the authored A5
  content and were not added, per the no-new-prose rule (R5).

### New connective sentences written (full list, per rule 1)

**`capstone.tex` (R2): none.** Every splice point in the assembly is a hard
section/subsection boundary (end of one `\subsection`/`\section` to the
start of the next, or `\appendix`/`\end{document}`); no bridging prose was
needed anywhere, so no new sentence of any kind — mathematical or
connective — was written into `capstone.tex` outside the three authored
blocks (A1 abstract, A2 subsection, A3 Appendix B), which were copied
byte-for-byte from the handoff.

**`problems/*.md` (R4):** these files were explicitly authorized to contain
"your own words only for connective structure" (framing sentences under
"Why it matters" / "Suggested attack" / short transitions). None of this
prose makes a new mathematical claim — every claim-bearing sentence in all
six files is a verbatim blockquote with a file+label pointer. Representative
examples of the connective-only sentences written: "This conjecture is the
paper's routing table..." (00), "This is not a single attack — this file is
a router, not a problem." (00), "An earlier working draft ('Theorem R')
claimed to close exactly this gap under EQ3′; a same-day independent
verification pass retracted the verdict." (02, restating already-quoted
facts, not asserting new ones), "These are not 'harder instances of the
same computation'..." (04), and similar short framing lines in 01, 03, 05.
None asserts a theorem, bound, or numeric claim not already present in an
adjacent verbatim quote.

**`README.md`, `STATUS.md`, `AUTHORSHIP.md` (R5):** `README.md` follows the
A5 skeleton essentially verbatim, with only the bracketed slots filled from
real command output (venv setup commands, the recorded probe output, and
the `Layout`/`Authorship` one-liners naming what each directory/file is —
purely descriptive, not mathematical claims). `STATUS.md` transcribes
Appendix B's tier list into a markdown table (claim / tier / where / caveats
columns) — the cell contents are copied from Appendix B; the table
structure itself is new but non-mathematical formatting. `AUTHORSHIP.md` is
A3's provenance paragraph plus the exact appended sentence given in A6,
verbatim.

### Flagged for the adversarial review session

1. Three occurrences of "Section~\ref{sec:mary}" now render as "Section A"
   instead of "Appendix A" (cosmetic side effect of the §5→Appendix A move;
   prose left untouched per the handoff's own constraint — see R2 above).
2. Grep-gate string "stated as an explicit hypothesis" is absent from
   `capstone.tex` because it lived only in the original abstract, which R2
   instructs replacing with A1; A1's actual wording ("stated as explicit,
   falsifiable hypotheses") is semantically equivalent but not a literal
   substring match. Not patched, per the no-strength-edit rule (see R3
   above for full detail).
3. The `--q 1469 --existential-divisor-report --summary-only` scanner
   example does not actually restrict to q=1469 (the flag's own `--help`
   text says it ignores `--q`); recorded and explained in
   `code/examples/scanner_existential_divisor.sh` rather than forced (R1).
4. Citations pending source verification (Halberstam–Richert,
   Friedlander–Iwaniec, Lagarias–Odlyzko, Stephens, Heath-Brown–Patterson) —
   carried forward from A3/Appendix B verbatim, not independently checked
   in this session.

### Rungs vs. time boxes

No rung hit its box, let alone 2×: R0 (~5 min, box 15), R1 (~10 min, box
30), R2 (~40 min, box 90), R3 (~15 min, box 30), R4 (~25 min, box 45), R5
(~10 min, box 15). No kill signal was triggered.

**Deliverable is complete: `capstone.pdf` compiles clean and is included.**

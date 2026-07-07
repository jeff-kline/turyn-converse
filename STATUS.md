# Status

Every principal claim in `paper/capstone.pdf` carries a verification tier.
This table transcribes Appendix B ("Verification status and provenance")
of the paper into markdown form.

## Tiers

| Tier | Meaning |
|------|---------|
| 0 | Unconditional, complete proof in the document. |
| 1 | Conditional on GRH. |
| 2 | Conditional on a named explicit hypothesis (EQ$_3$, hypothesis (C), Dickson). |
| 3 | Numerical evidence only, no theorem claimed. |

## Principal claims

| Claim | Tier | Where | Caveats |
|---|---|---|---|
| Selection theorem | T0 | `thm:divisor-selection` | — |
| Two-orbit criterion | T0 | `thm:two-orbit-reps` | — |
| $h=3$ hierarchy | T0 | `prop:h3-augmentation-reps` and corollaries | — |
| Row-sum bound and exact form | T0 | `thm:full-torus-rowsum` | Sharp exactly at Turyn's $q=25$. |
| Rigidity criterion | T0 | §"Quotient descent and the rigidity criterion" | — |
| $q\le2000$ closure, incl. first determinations $1469$, $1937$, $1325$ | T0 | §6 "Closed orders" | Closed-table novelty caveat (see paper text). |
| $q=5185$, $q=62305$ | T1 | small-image fold-tower kills | Conditional on GRH via a class-group computation; see `problems/03-stickelberger-fold.md`. |
| Semiprime lane theorem | T0 | `thm:semiprime-converse` | Infinitude of the lane is open — parity-blocked; see `problems/05-parity-wall.md`. |
| Lane collapse at general $\omega$ | T0 | `prop:lane-kill` | — |
| Dickson family and hypothesis-(C) dichotomy | T2 | `rem:chen-input` and surrounding text | Hypothesis (C) has no retrievable exact citation as of the 2026-07-06 literature audit. |
| Small-factor sieve count | T2 (EQ$_3$) | `prop:small-factor-sieve` | GRH implies EQ$_3(\theta)$ for $\theta<1/8$ (T1) but does not close the lane's remaining structure count — the density program is **not GRH-complete**. See `problems/01-eq3-unconditional.md`, `problems/02-structure-count.md`. **2026-07-07:** the natural sieve repairs of that structure count are now proven closed to the whole averaged-Chebotarev genus ($\beta(1/3)=1$; a cubic-symbol parity barrier) — see the Update in `problems/02`. |
| Census calibrations at $q\le10^4$–$10^7$ | T3 | throughout §4, §6 | Numerical evidence only. |

## Citations (source-verified 2026-07-07)

The bibliography entries for Halberstam–Richert, Friedlander–Iwaniec,
Lagarias–Odlyzko, Stephens, and Heath-Brown–Patterson were checked against
public records and are bibliographically accurate (Lagarias–Odlyzko
pp. 409–464; Stephens, *Mathematika* 16 (1969) 178–188; Heath-Brown–Patterson,
*J. Reine Angew. Math.* 310 (1979) 111–130). One in-text precision point
remains open: the chapter pointer for Halberstam–Richert could not be
independently confirmed, so the `\cite[Ch.7]{HR74}` references were relaxed to
chapter-less `\cite{HR74}` in the paper.

The hypothesis-(C) inputs named in `rem:chen-input` and the Dickson-family
theorem now carry `\bibitem`s (Chen 1973, Dickson 1904, Irving arXiv:1410.3333,
Lewulis arXiv:1601.02873); Irving and Lewulis were verified real and correctly
attributed.

## Provenance

This document was written by large language models (Claude) under human
direction, with machine-verified audits for the finite claims and
independent-session cross-verification for the theoretical ones; one
conditional theorem announced during development (a conditional infinite
family on the lane) was retracted after verification and does not appear in
this document. A 2026-07-07 follow-up ("Theorem R′") went further and showed
the natural repair routes for that theorem are themselves closed within the
averaged-Chebotarev genus, so the gap is a genuine research problem, not a
bookkeeping shortfall. The working record, including both the retraction and
this follow-up, is preserved in the companion notes (see
`problems/02-structure-count.md`, "Update"). See `AUTHORSHIP.md`, and
`AUDIT_LOG.md` for the dated, per-model log of correctness/adversarial audits.

## Changelog

- 2026-07-06: initial clean-start assembly from source-repo@2c02e32;
  capstone = companion re-fronted, §5 → Appendix A; no mathematical content
  altered (transcription-checked).
- 2026-07-07: recorded the "Theorem R′" follow-up (mainline-verified) in
  `problems/02-structure-count.md` (Update) and this file. Markdown apparatus
  only — no change to `paper/capstone.tex`, `.pdf`, or any transcription-checked
  claim; the paper body never asserted the now-closed route.
- 2026-07-07 (correctness audit): three-layer adversarial audit (Sonnet 5 +
  Opus 4.8) with mainline spot-verification; every principal claim verified —
  full record in `AUDIT_LOG.md`. Fixes: Appendix B made a numbered `\section`
  so it now appears in the TOC (`paper/capstone.tex`, rebuilt, 61 pp — a
  section-level structure change, no theorem environment or transcription-checked
  claim altered); corrected a misattributed `--help` caveat in
  `code/examples/scanner_existential_divisor.sh`. Two source-repo items (a stale
  "Theorem D unconditional" working note; the source paper's "genuine parity
  barrier" phrasing) were fixed in `source-repo`, not in this capstone.
- 2026-07-07 (capstone-local audit): adversarial audit with working dir = this
  capstone, testing claims from the capstone + its public references only
  (agent-run, mainline-verified). Tier-0 math clean; all findings were
  self-containment / citation-locatability (full record in `AUDIT_LOG.md`).
  Fixes to `paper/capstone.tex`: added `\bibitem`s for Chen/Dickson/Irving/Lewulis
  and wired `\cite`s; relabeled the HBP79 "cubic large sieve" mention as
  Kummer-sum equidistribution; relaxed the unconfirmed HR74 chapter pointer;
  disclosed the two diagnostic-table generators as source-repo/not-shipped and
  shipped their caches under `code/data/`; cleared the pending-citation flag.
  Added `code/gp/` (class-group anchor bundle) and `code/data/`. No Tier-0 or
  transcription-checked claim altered (bibliography + wording only).

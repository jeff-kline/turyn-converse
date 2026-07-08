# Audit log

Provenance record for correctness / adversarial audits of this capstone.
One entry per audit, **newest first**. Referenced by `STATUS.md` ("Provenance")
as the running record of the human-directed verification of the paper's claims.
Each audit is expected to append an entry; do not rewrite past entries.

## Entry format

- **Date** — ISO date.
- **Models** — mainline orchestrator/verifier + any subagents, each with its role.
  (Record the model *family*; subagent model is whatever the `Agent` call requested.)
- **Scope** — which claims / files were in scope.
- **Method** — how the audit ran; what "verified" means here; adversarial or not.
- **Findings** — ranked most-severe-first; each with file:line location and severity.
- **Fixes applied** — `file` : change, or "none".
- **Open / not done** — recommended-but-deferred items (human decision).

---

## 2026-07-07 — Privacy audit (2nd pass, independent); no fixes needed

**Models.** Haiku 4.5 (low effort) mechanical grep/list/tabulate pass; escalated to
Sonnet 5 for report synthesis. No deep-reasoning model needed — task was regex + git
plumbing, not judgment calls beyond one borderline severity call (repo owner's own
commit email).

**Scope.** Independent re-derivation (not a rely-on-prior-pass check) of exposed
private/sensitive data in this **public** repo, across two co-equal scopes: (1) the
working tree at HEAD, and (2) the entire git history — every ref/commit, plus anything
added-then-removed. Read-only: no edits, no `git rm`/`filter-repo`/rebase/force-push.

**Method.** Working tree: `git grep` for local paths/usernames, emails (excl. noreply),
secret/credential patterns (API keys, PEM blocks, OAuth/Slack tokens, password/secret
literals), and internal/private references (localhost, RFC1918 IPs, `.env`); PDF
metadata + `strings` inspection of `paper/capstone.pdf`. History: enumerated all
refs/branches/tags/remote (5 commits, single branch `main`, no tags); dumped
author/committer identities; grepped commit messages and full `git log --all -p`
content; checked added-then-deleted files; ranked all blobs by size for orphaned/large
objects; ran `git fsck --full --unreachable --dangling`. Cross-checked PDF metadata
across all 3 historical blob versions of `capstone.pdf`, not just HEAD. `gitleaks`/
`trufflehog` were not installed; relied on manual regex only.

**Findings.**
- **No secrets, no unintended local-path leakage into tracked content, no
  scrubbed-but-recoverable files, no dangling/orphaned objects.** History has zero
  added-then-deleted files (every file ever added is still present at HEAD); `git fsck`
  returned nothing; all blobs correspond to expected repo content at reasonable sizes.
- **Info/Low — real commit email.** All 5 commits' author/committer identity is
  `Jeff Kline <jeffery.kline@gmail.com>` (repo owner's real name + personal Gmail),
  present in every commit in history. Judged intentional/expected (matches the
  GitHub-linked identity), not a leak — flagged per protocol, not actionable without a
  human decision to scrub it retroactively.
- **Info — Claude co-author trailers.** 4 commits carry
  `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>` / `Claude Sonnet 5
  <noreply@anthropic.com>` — noreply address, expected Claude Code convention, no action.
- **N/A — not public.** `paper/capstone.log` (LaTeX build log) contains local
  `/Users/<user>/.texlive2021/...` paths, but the file is untracked and excluded by
  `.gitignore` (`*.log`); confirmed via `git ls-files` it was never committed. No action
  beyond not force-adding it.
- **Clean — PDF metadata.** All 3 historical blob versions of `paper/capstone.pdf`
  (not just HEAD) have empty Author field and only generic `pdfTeX`/`LaTeX with hyperref`
  Producer/Creator strings; no embedded `/Users/` or username strings in any version.
- False positives noted and dismissed: "password" match was GPL license boilerplate
  (`LICENSE:340`); "internal"/IP-like matches were English prose and an arXiv ID
  (`1410.3333`), not RFC1918 addresses or hostnames.

**Fixes applied.** None — read-only audit, no findings required a working-tree change.

**Open / not done.** Whether to retroactively scrub the repo owner's personal email from
commit history (history-rewrite via `git filter-repo` + force-push) is a human decision,
deferred — the address is already tied to the public GitHub identity, so scrubbing would
be largely cosmetic. `gitleaks`/`trufflehog` were unavailable in this environment; a
follow-up pass with those tools installed would strengthen secret-detection coverage
beyond manual regex.

---

## 2026-07-07 — Code-correctness validation (clean-room cross-check); F1/F2 prose fixes applied

**Models.** Sonnet 5 orchestrator (dispatch, code-quality read, merge); Haiku 4.5
Tier-M (ran shipped functions on samples, dumped raw output); **three fresh parallel
Opus 4.8** (`claude-opus-4-8`, high effort) clean-room instances, each writing
independent group/number-theory code from `capstone.tex`'s definitions before touching
the shipped scripts; Fable reserved, not fired (no contested mismatch). Mainline
verification of the findings + application of F1/F2: **Opus 4.8**. The agent's full
draft was reviewed by the mainline and its findings independently confirmed.

**Scope.** Not a proof audit — does the shipped `code/*.py` actually COMPUTE what the
paper claims (guarding against a self-consistent bug that emits paper-matching numbers)?
Method: clean-room reimplementation of each load-bearing computation from `capstone.tex`'s
definitions, cross-checked against shipped output on small tractable samples. Critical
coverage: T1 multiplier group (`v_group`/`orbits`), T2 classical obstructions
(`two_squares_fail`/`selfconj_kill`), T3 closure branch classifier (`candidates`/
`best_signature`/`existential_divisor_report`), T4 semiprime census/w-formula. T5
(`small_image_fe_tower.py`) is **not in this repo** (confirmed absent) — out of scope by
non-existence.

**Findings.**
- **No code-correctness defect** in any audited function. All clean-room cross-checks
  MATCH: T1 (~14 samples incl. full partitions for 65/45/185/441), T2 (all 352 composite
  q≤2000, 211/13/111 partition), T3 (34 divisor-lattice rows + 7 two-orbit firing
  decisions for q=549/425/1445/1469/1937/1325), T4 (5 w-values + a full census(2000)
  tally, 8/8 members). This closes the previously-unaudited gap of the scripts'
  *internal* correctness (prior audits checked reproducibility + proofs, not clean-room
  code equivalence).
- **F1 (paper prose, `rem:blindspot`) — CONFIRMED, FIXED.** The 111-member blind-spot
  count is correct, but the prose characterized it as "every composite q all of whose
  prime divisors ≡1 mod4," which holds for only **80** of the 111; the other **31**
  (e.g. q=245=5·7², 441=3²·7², 549=3²·61) carry a ≡3-mod-4 prime at even power. Mainline
  independently reproduced 80/31/111 via the shipped classifier. **Fixed**: rewrote
  `rem:blindspot` to state the correct characterization (every ≡3-mod-4 prime at even
  power + survives self-conjugacy) and the 80+31 split; mirrored to companion.
- **F2 (paper prose, capstone.tex:506) — CONFIRMED, FIXED.** "closes q=45 … and 13
  further" implied 14 self-conjugacy kills; the true count is **13**
  (`[45,117,261,333,477,765,833,981,1125,1225,1573,1773,1845]`), i.e. 45 + **12** further.
  **Fixed**: "13 further" → "12 further"; mirrored.
- **F3 (cosmetic) — CONFIRMED, not applied.** "Composite" is used two ways: `sweep()`
  counts Ω≥2 (352, incl. prime powers); `blind_spot_qs` requires ≥2 *distinct* primes
  (335). Both correct for their purpose. [Mainline hit this directly: a first pass using
  Ω≥2 gave 128/88/40, reconciling to 111/80/31 only under ≥2-distinct-primes — the correct
  in-scope definition, since prime powers are exactly where the converse *permits* pairs.]
  Code-readability only; no paper change.
- **F4 (cosmetic, code quality).** `candidates(q, proper=True)` for a single q triggers,
  via a lazily-built module-scoped cache in `marginal_orbit_algebra.py`, expensive
  period-lattice computation over unrelated q — undocumented on the docstring;
  deterministic and self-consistent, not a bug. Optional doc note.
- **Code-quality (Sonnet).** Scripts concise, deterministic, budget-guarded;
  `density_semiprime_census.py` embeds the paper's lemma as runtime `assert`s
  (self-checking). `orbit_signature_scan.py`'s `family()` shape-ranking bucket names are
  code-internal, not theorem branches — correctly disclaimed by the paper
  (`rem:selection-open`).

**Verification (post-fix).** Build 62 pp / 0 errors / 0 undefined; transcription
`mismatches=0` (F1 in the checked remark mirrored correctly).

**Fixes applied.** F1 (`rem:blindspot` characterization + 80/31 split), F2 ("12 further")
— capstone.tex + companion. F3/F4 code-quality notes not applied (optional).

**Residual doubt / not covered.** Small/tractable samples only (headline q≤2000/10⁷ counts
were cross-check targets, not re-derived at full scale). The `family()`/`best_signature()`
shape-ranking heuristic was out of scope (paper disclaims it as non-theorem-derived).
Deeper per-family certificates (h=3 hierarchy, C21/C27/C49/C57 joins, full-torus row-sum)
were covered by the prior Fable pass, not re-audited here. T5 not in repo.

---

## 2026-07-07 — Public-readiness & full-coverage review (Sonnet-orchestrated); fixes applied

**Models.** Sonnet 5 orchestrator; Haiku 4.5 mechanical; Opus 4.8 (high) deep
proof/coverage tier; Fable reserved (unused). Full report: private Claude Artifact
([private session link removed]). Mainline
verification of every proposed fix + application: **Opus 4.8** (`claude-opus-4-8`).

**Scope / verdict.** Full-coverage (129/129 environments, coverage ledger) +
self-containment + public-share readiness. Reported: 95/101 claim-bearing SOUND,
0 GAP, 0 OVERCLAIM, 2 disclosed UNVERIFIED (GRH class groups q=5185/62305; imported
sieve constants in `prop:small-factor-sieve`). Verdict GO-WITH-FIXES.

**Mainline verify-before-apply of the 7 proposed fixes.**
- **Fix 2 (APPLIED)** — label `conj:Lstar`→`prop:Lstar` (a proposition mislabeled with
  a `conj:` prefix); the single `\ref` updated; mirrored capstone↔companion. Verified:
  exactly 4 occurrences repo-wide, none in problems/STATUS.
- **Fix 3 (APPLIED — real math typo)** — in the `prop:pe-full-unit-nested` proof,
  numerator `\varphi(p^e)`→`\varphi(p^{e-j})` (capstone.tex:1815). Verified THREE ways:
  the orbit `O_j=p^j(\Z/p^{e-j})^\times` has size `\varphi(p^{e-j})` (stmt line 1791);
  the λ-formula weights `O_j` by `\varphi(p^{e-j})` (line 1796); and boundary
  consistency at m=j (with `\varphi(p^e)` the two case-formulas disagree, with the fix
  they agree). Distinct from the `y_{-1}:=0` typo fixed in a prior round. Mirrored.
- **Fix 4 (APPLIED)** — dead labels on the `C_{49}` corollary: renamed
  `prop:c49-nested`→`cor:c49-nested` (prefix fix) and removed the redundant trailing
  `cor:c49-residue-pair`. Verified both are zero-`\ref`; the live, referenced-twice
  `cor:pe-residue-pair` (capstone.tex:1833) left untouched. Mirrored.
- **Fix 6 (APPLIED)** — README Layout: added a contributor note stating the
  capstone↔companion mirror rule (out of any theorem-like environment; no mirror).
- **Fix 7 (APPLIED)** — `problems/00` companion line pointer `4316–4332`→`4318–4334`
  (verified: companion `\section{What remains}`=4318, `\end{conjecture}`=4334).
- **Fix 5 (HELD — did not pass as specified)** — `h\ge57`→`h\ge55` in
  `cor:c27-auto-box`. The observation is CORRECT (`\sqrt{54h-1}<h ⟺ h\ge54`; h odd ⟹
  tight bound `h\ge55`; `h=55`: √2969≈54.49<55 ✓, `h=53` fails) — but `h\ge57` is
  loose-yet-valid, NOT a bug, and the audit's edit touches only the corollary while
  `h\ge57` also appears in the proof (line 1719) and `cor:c27-residue-pair` (line 1734);
  applying just the corollary would make the statement claim more than its proof
  justifies. Held pending a decision to do the full consistent change (all 4 sites) or
  leave the correct-but-loose bound.
- **Fix 1 (PENDING AUTH)** — commit LICENSE (GPL v3) + README + these fixes and push to
  origin/main. Push is to the public remote; awaiting explicit go.

**Verification (post-fix).** Build 62 pp / 0 errors / 0 undefined; `\ref{prop:Lstar}`
resolves; transcription `mismatches=0`.

**Fixes applied.** Fixes 2, 3, 4, 6, 7 (capstone.tex + companion for 2/3/4; README;
problems/00).

**Open / not done.** Fix 5 (correct-but-loose bound; full consistent change offered);
Fix 1 commit/push (pending user authorization); the two disclosed UNVERIFIED items
(GRH class groups, sieve constants) remain honest research limitations, not bugs.

---

## 2026-07-07 — Multi-model adversarial self-containment & proof review (cold-start)

**Models.** Orchestrator + deep proof tier: **Fable 5** (`claude-fable-5`) — output
cleared the depth floor (reconstructed proof steps + independent re-execution of the
finite certificates, not bare verdicts). Mechanical tier: **Haiku 4.5** (sanity checks,
grep inventory). Citation/containment/onboarding tier: **Sonnet 5**. Findings
mainline-verified and all fixes applied by **Opus 4.8** (`claude-opus-4-8`).

**Scope / axis.** Full cold-start review from the capstone directory alone
(source-repo off-limits): (1) self-containment, (2) adversarial vetting of every
proof, (3) sufficiency for a cold third party to reach high confidence. Prior AUDIT_LOG
entries were re-derived, not inherited.

**Findings (mainline-verified).**
- **1 (Medium, D2):** T1 class groups Cl(F₄), Cl(k₃(i)) not recomputable in-repo — only
  the quadratic anchors ship. Disclosed; the honest content of T1. **No fix.**
- **2 (Medium, D2):** the "Theorem R′" closure in `problems/02` cites a source-repo
  deliverable not shipped; a plausible claim, not a checkable proof, from here. Disclosed.
  **No fix.**
- **3 (Minor, D1 — the only real math defect in 129 environments):** `prop:pe-full-unit-nested`
  proof parenthetical `y_{-1}:=y_e` should be `y_{-1}:=0`. Mainline corroborated
  independently — the parity line (capstone.tex:1824) treats `λ₁≡y_e` as a base case,
  consistent only with `y_{-1}=0`. In a `proof` (not transcription-checked); no downstream
  effect (C₂₇/C₄₉ inverses verified independently). **FIXED** (capstone.tex + companion).
- **4 (Minor, D3):** `problems/00` said "§8 What remains"; the section is §7. **FIXED**
  (problems/00, three spots). [Fable's causal note "shifted when Appendix B was numbered"
  is incorrect — it was §7 before; the "§8" is the source paper's numbering mis-quoted.]
- **5 (Minor, D2):** `def:eq3-family` dangling pointer (`problems/02:119`; label is
  `def:eq3`). **FIXED** → "EQ3-family (def:eq3)".
- **6 (Cosmetic, D1):** `rem:parity-wall` "first Theorem members" list scoped imprecisely.
  Census (`density_semiprime_census.py`) confirms: the list `65,185,785,905,1073` is
  exactly the first five {1,5}-class (new-content) members, and `473=11·43`, `497=7·71`
  are {7,11} (classical two-squares) members. **FIXED** — added "in the blind-spot
  {1,5} class (the two-squares members, e.g. q=473,497, fall to the classical
  obstruction)" (capstone.tex + companion).
- **7 (Cosmetic, D2):** `Hall67` was the only genuinely uncited bibitem (Tier-M's
  FI10/LS16/LS19 "unused" flags were grep false-positives — bracketed-optional cites,
  adjudicated correctly). **FIXED** — cited at "classical multiplier theory"
  (capstone.tex:333, the canonical home for Hall's multiplier theorem) + companion.
- **8 (Note, D1):** hypothesis (C) has no external citation and the sieve inputs are
  cited without chapter/verse — both correctly priced at T2 and self-flagged. **No fix.**

**Verdict (Fable, mainline-endorsed).** Every principal claim verified at its stated tier;
no overclaim; the T0 mathematics survived full adversarial reconstruction and every
attacked finite certificate reproduced exactly by independent re-implementation (q=549
MITM 0 joins; q=1469 256 Z[u] reps / 0 side vectors; q=1937 0 mates; q=1325 400,753 box
pts / 0 mates; scanner branch split 81/29/1). Residual doubt confined to the two disclosed
T1 class-group inputs and the off-repo R′ deliverable.

**Fixes applied.** #3 (math typo), #4 (§7 pointer), #5 (dangling pointer), #6 (list
scoping), #7 (Hall67 citation). #3/#6/#7 mirrored capstone↔companion. Post-fix
verification: build 62 pp / 0 errors / 0 undefined; `Hall67` now cited; transcription
`mismatches=0`. Two-token math change (#3) in a proof; #6 the only checked-environment
edit (mirrored).

**Open / not done.** Findings 1, 2, 8 are disclosed walls (no action). q=1445's full
2.1M×2.3M support-PAF join not independently re-executed (residue stage + scanner route
were). Appendix A's 59-pair machine sweep taken as stated after proof-level verification.

---

## 2026-07-07 — Validation of the capstone-local audit fixes (adversarial)

**Models.** Independent, read-only validation by **Opus 4.8** (`claude-opus-4-8`),
single session, no subagents. Local-only (source-repo off-limits); public
sources used only to re-check bibliographic detail.

**Scope.** Confirm the six fixes closing the capstone-local audit (F1–F6, entry
below) were applied correctly and introduced no new self-containment gap,
overclaim, or broken reference — not a rubber-stamp; PASS only on evidence.

**Method.** Rebuilt the paper; re-ran the transcription checker and the shipped gp
script (byte-diffed against its committed transcript); diffed the three
citation-touched environments capstone-vs-companion; re-derived that every `\cite`
resolves to a `\bibitem` in both files; re-verified the four new + five previously
flagged bibitems against public records.

**Results — all six items PASS.**
- **A (build/refs).** 0 `^!` errors, 62 pp (61→62, the added bibitems), 0 undefined;
  `\bibcite{Chen73,Dickson04,Irving14,Lewulis16}` = entries 34–37 in `capstone.aux`;
  `appendix.B` in the TOC.
- **B (transcription/mirror).** `mismatches=0`; `thm:dickson-family`,
  `rem:chen-input`, `rem:lane-density-status` byte-identical in capstone & companion
  — edits are `\cite`/wording only, no equation or statement altered; companion
  independently consistent.
- **C (F4).** `Ch.~7]{HR74}`=0 and `large sieve`=0 in both files; "cubic Kummer-sum
  equidistribution" at `\cite{HBP79}`; bare `\cite{HR74}` retained (3219/3226/3232).
- **D (F1).** Both `.jsonl` caches in `code/data/`; paper sentences (3638, 3794) point
  there; `code/README.md` replaces the old completeness line with an accurate
  "Not shipped (diagnostic generators)" disclosure; no Tier-0 closure depends on the
  two "cond." tables.
- **E (F3).** `gp code/gp/fold_tower_anchors.gp` genuinely computes (bnfinit/
  bnfisprincipal, not literals) — h(−10372)=24, Cl=[24], kronecker(D,17)=+1,
  kronecker(D,5)=kronecker(D,61)=−1, ord[P₁₇]=12, 2593/31153 prime — **byte-identical**
  to the committed transcript; scoped honestly to the quadratic anchors (full
  Cl(F₄)/Cl(k₃(i)) remain source-repo GRH hypotheses; no overclaim).
- **F (F2/F5).** New bibitems verified: Dickson (Messenger of Math. 33 (1904) 155–161),
  Irving (arXiv:1410.3333, 2014), Lewulis (arXiv:1601.02873, 2016) exact; Chen
  (Sci. Sinica 16 (1973) 157–176) correct bar a trivial title variant ("larger"→"large").
  Five formerly-pending entries re-confirmed; cleared-flag text (STATUS.md:33,
  capstone.tex:4718) accurate and honestly keeps the HR74-chapter caveat.
- **G (regression).** Every `\cite` resolves to a `\bibitem` in both `.tex` files;
  no new referenced-but-absent file; the only unshipped referenced scripts
  (`condition_*.py`) are now explicitly disclosed.

**Verdict.** The capstone-local fixes are **complete and regression-free.** The two
residuals (HR74 chapter number unconfirmable; full fold-tower class groups not
shipped) are honest, documented limitations of the sources and the T1/GRH tier, not
defects introduced by the fixes. One cosmetic nit: Chen73 title "larger"→"large".

**Fixes applied.** None — read-only validation.

**Open / not done.** Cosmetic: correct the Chen73 title word ("larger"→"large").
Otherwise nothing outstanding from this validation.

---

## 2026-07-07 — Capstone-local adversarial audit (self-containment + citations)

**Models.** Adversarial audit run with working dir = this capstone (agent
per the run), tested against the capstone + its public references only —
**source-repo deliberately off-limits**. Findings mainline-verified and
fixes applied by **Opus 4.8** (`claude-opus-4-8`).

**Scope / axis.** Orthogonal to the baseline: instead of following proofs into
the source repo, this pass asks whether each claim is (A) self-contained in the
capstone, (B) supported by locatable public citations, (C) locally provable from
the capstone's own text. So a claim can be baseline-SOUND yet flagged here for
locatability.

**Findings (agent, mainline-verified).**
- **F1 (Moderate, self-containment).** `capstone.tex` cited two table generators
  (`condition_r_realization.py`, `condition_c_absorption.py`) + `.jsonl` caches
  absent from `code/`; `code/README.md` implied manifest-completeness. Both tables
  are diagnostic ("cond." rows, not certified closures) — no Tier-0 dependency.
- **F2 (Moderate, citation support).** Hypothesis-(C) support (`rem:chen-input`)
  and the Dickson theorem named Chen/Dickson/Irving/Lewulis with **no `\bibitem`**.
  Irving (arXiv:1410.3333) and Lewulis (arXiv:1601.02873) verified real + correctly
  attributed, but uncitable from the capstone.
- **F3 (Low–Mod, self-containment).** No gp artifact shipped for the T1 fold-tower
  class groups; the exhaustive rescue-set check lives in the source scripts.
  Mainline note: the source enumeration is **exhaustive** (`small_image_fe_tower.py`
  enumerates all weight vectors, asserting the space ≤10⁷), so the paper's
  "15 sampled" *undersells* it — not an overclaim.
- **F4 (Low, precision).** (a) `\cite[Ch.7]{HR74}` chapter unconfirmable;
  (b) HBP79 mislabeled "cubic large sieve" (it is the Kummer-sum equidistribution
  paper).
- **F5 (Positive).** All five "pending" bib entries verify accurate against public
  records (LO77 pp.409–464; Stephens *Mathematika* 16 (1969) 178–188; HBP *Crelle*
  310 (1979) 111–130; HR74; FI10).
- **F6 (By design).** `problems/01–05` cite source-repo notes, but those back
  open-problem statements, not paper claims. No action.
- **(C) Tier-0 integrity — CLEAN locally.** No Tier-0 step needed external material.

**Fixes applied (this session).**
1. **F2** — added `\bibitem{Chen73,Dickson04,Irving14,Lewulis16}` and wired `\cite`s
   into `rem:chen-input` and `thm:dickson-family`. Rebuilt: `\bibcite` for all four
   resolves (entries 34–37), 0 undefined citations. The three edited environments
   were **mirrored into `paper/companion/turyn_converse.tex`** so the transcription
   invariant holds (`mismatches=0`); the invariant now certifies capstone ≡ companion
   with the 2026-07-07 citation edits.
2. **F4** — (a) relaxed both `\cite[Ch.7]{HR74}` to chapter-less `\cite{HR74}`;
   (b) relabeled "cubic large sieve" as "cubic Kummer-sum equidistribution".
3. **F1** — corrected `code/README.md`'s completeness wording; disclosed the two
   generators as source-repo/gp-dependent/not-shipped (diagnostic tables); **shipped
   their caches** to `code/data/`; repointed the paper's two table-source sentences
   at `code/data/`.
4. **F3** — added `code/gp/fold_tower_anchors.gp` + recorded transcript, which the
   mainline **ran and verified** reproduces every quadratic anchor exactly:
   `h(-10372)=24`, `Cl=[24]`, 17 splits, 5 & 61 inert, `ord([P_17])=12`, fold primes
   2593/31153 prime. Degree-40 fold-tower class groups remain source-repo (gp-driven),
   stated in-paper as GRH hypotheses (documented in `code/gp/README.md`).
5. **F5** — cleared the "pending" flag in `STATUS.md` and Appendix B (with the one
   remaining HR74-chapter caveat).

**Verification.** `capstone.tex` rebuilds clean (62 pp, 0 errors, 0 undefined);
transcription `mismatches=0`; gp transcript reproduced live.

**Open / not done.**
- F3 wording: recommend the paper say "complete enumeration of the N rescue weights"
  rather than "15 sampled" (the source check is exhaustive) — deferred, needs a close
  read of the exact count; not forced.
- Prior deferred items still stand: `cor:h3-support-sum-gcd` demotion; `C₄₉` label
  hygiene.
- A full gp recomputation of the degree-40 fold-tower class groups is not shipped
  (would require the source gp-driven subtree); only the quadratic anchors are.

---

## 2026-07-07 — Full correctness audit (baseline)

**Models.**
- Mainline orchestration + independent spot-verification — **Opus 4.8** (`claude-opus-4-8`).
- Layer 1, reproducibility — **Sonnet 5** (`claude-sonnet-5`), subagent.
- Layer 2a, structural-proof soundness (Tier-0) — **Opus 4.8**, subagent.
- Layer 2b, analytic/conditional + negative-result soundness (Tier-1/2) — **Opus 4.8**, subagent.

**Scope.** All principal claims in `paper/capstone.tex` (per `STATUS.md`), the
supporting scripts in `code/`, and — for the proofs whose full argument lives
outside the capstone — the source notes in the companion repo
(`source-repo/turyn_theory/*.md`). Three layers: (1) reproducibility,
(2) Tier-0 structural theorems, (3) Tier-1/2 analytic + the negative results
(Theorem R retraction, Theorem R′ closure).

**Method.** Each layer ran **adversarially** (instructed to hunt for gaps and
overclaims, not to confirm; "unable to verify" preferred over false assurance).
The mainline did **not** accept subagent verdicts unchecked: it independently
re-ran the load-bearing checks against disk before recording them —
re-ran the transcription checker (`mismatches=0`); reproduced the structural
proofs' numeric anchors (`ord₄₃(17)=21`, `5²¹≡5³⁶≡−1`, q=1445 outside the
ℓ≡3 lane since 241≡1 mod 4, q=25 → ⟨5,−1⟩ mod 13 has w=4); reproduced
`h(−10372)=24` and disc-factor primality via PARI/gp; and located both
flagged phrases on disk.

**Findings.**

- **Layer 1 (reproducibility): CLEAN.** 14/14 substantive checks pass.
  Transcription checker: 129 theorem-like environments, `mismatches=0`
  (capstone.tex ≡ companion/turyn_converse.tex). PDF recompiles clean
  (3 pdflatex passes, 0 errors, 0 undefined refs/citations). Density/census
  probes reproduce: `density_w_formula_probe.py` → `not_all_plus=0,
  mismatches=0`, and the `w=2` set is **exactly {9185, 117185}** to 2·10⁵
  (matches `rem:lane-density-status`(iii)); the existential-divisor census
  diffs byte-for-byte against the recorded transcript. STATUS tiers match
  Appendix B; all `problems/*.md` label pointers resolve.
  One FAIL, documentation-only: `code/examples/scanner_existential_divisor.sh`
  misattributed a `--help` caveat string to the wrong flag (behavior claim
  still true, verified from source). **[fixed below]**

- **Layer 2a (Tier-0 structural): CLEAN.** 8/8 SOUND (selection, two-orbit,
  h=3 hierarchy, row-sum bound+sharpness, rigidity, lane-collapse, semiprime
  lane, q≤2000 closure incl. first determinations 1469/1937/1325). Not a
  rubber-stamp: the review itself flagged the selection theorem's headline as
  a near-tautology (paper says so in `rem:selection-open`) and confirmed the
  q≤2000 closure is honestly framed as a *conjecture* (`conj:program`),
  per-member Tier-0, "not a general theorem." Only limitation: individual
  finite emptiness certificates (MITM UNSATs, the 256-/48-rep joins) were not
  each re-run — disclosed and cross-checked in the source.

- **Layer 2b (Tier-1/2 analytic + negatives): CLEAN for the capstone
  deliverable.** Fold-tower kills q=5185, q=62305 reproduce every GRH class
  group via gp (`Cl(F₃)=C₂₁×C₂₁` certified **unconditional** `bnfcertify=1`;
  `Cl(F₄)` order 1632; `Cl(k₃(i))=C₅₇₉₉`); GRH-conditionality correctly scoped.
  EQ₃ density formula `δ_d=(1/4)∏1/(3φ(pᵢ))` correctly derived; the
  "not certified nonexistence orders" disclaimer is accurate. R-retraction
  findings F1 (s=1 ⇒ `f₁(1)=0`) and F2 (dropped two-sieve independence) are
  correct reasons to retract. R′ closure: the §5.3 malicious-prime
  impossibility (no plain-remainder lower-bound sieve is positive at s<1, any
  dimension) is rigorous; the salvage's parity obstruction is real. Two items,
  **both in the source repo, not in the capstone**:
  - ① `source-repo/.../density_partial_converse.md` called the Dickson/Chen
    dichotomy "Theorem D (unconditional dichotomy — Chen)"; the paper's
    `rem:chen-input` is right that no retrievable citation covers exactly
    hypothesis (C). Note overclaimed. **[fixed below]**
  - ② `source-repo/.../turyn_converse.tex` (source paper only; NOT in
    `capstone.tex`) called the R′ salvage obstruction a "genuine parity
    barrier." Sound as written (scoped "within the averaged-Chebotarev genus";
    the attached claim is non-expressibility, which *is* proved), but the full
    Selberg-parity extremal construction is explicitly "a lemma-sized project
    and is NOT claimed here" (`density_theorem_rprime.md`). Wording ran ahead
    of the completed content. **[softened below]**

- **Unused-claims / lemmas pass (capstone.tex, 161 labels).** No genuinely
  dead lemma or proposition: every unreferenced *lemma* feeds the next result
  in prose (`lem:per-character-unit`→`lem:coherence`; `lem:coverage`→`thm:normalform`;
  `lem:quadratic-two-square`→the quadratic-lane props), and the unreferenced
  theorems/props are terminal results/certificates (e.g. `prop:q549-fiveorbit`
  is a self-contained kill). Corollaries never `\ref`'d are reader-facing
  restatements (`cor:orbits`, `cor:exact-secondary-marginal`, `cor:trivialdefect`).
  Two nits recorded under "Open" below.

- **Structure / TOC.** Appendix B was declared `\section*` (unnumbered), so it
  was absent from the capstone TOC while Appendix A (a numbered `\section`
  under `\appendix`) was present. **[fixed below]**

**Fixes applied (this session).**
1. `paper/capstone.tex` — Appendix B `\section*{Appendix B: Verification status
   and provenance}` → `\section{Verification status and provenance}`; now
   auto-numbers "B" and appears in the TOC. Rebuilt: 61 pp, 0 errors, TOC line
   `\numberline{B}…appendix.B` present.
2. `source-repo/.../paper/turyn_converse.tex` (source paper) — "genuine
   parity barrier" → "a parity-type obstruction". Rebuilt: 61 pp, 0 errors.
   *(Uncommitted in source-repo; not pushed.)*
3. `source-repo/.../density_partial_converse.md` (source note) — "Theorem D
   (unconditional dichotomy — Chen)" demoted to "conditional on hypothesis (C)",
   with the 2026-07-06 no-citation caveat, at both the summary bullet and the
   statement. *(Uncommitted.)*
4. `code/examples/scanner_existential_divisor.sh` — corrected the misattributed
   `--help` caveat (the "ignores the other filter flags" note belongs to
   `--dichotomy-report`, not `--existential-divisor-report`); behavior
   description unchanged (it was correct).

**Open / not done (recommended; deferred to human decision — no content removed
from a verified paper without a go-ahead).**
- `cor:h3-support-sum-gcd` (`capstone.tex:896`): self-described as "deliberately
  coarse … the criterion is silent," superseded by the exact `prop:h3-support-augmentation`
  above it. Candidate to demote to a remark or cut. Not wrong; harmless.
- `C₄₉` corollary (`capstone.tex:1851`): a `corollary` environment carrying a
  `prop:`-prefixed label (`prop:c49-nested`) plus a redundant trailing second
  label (`cor:c49-residue-pair`, line 1863); both unreferenced. Label hygiene
  only — removing a truly unreferenced `\label` is safe, but left for a batch.
- Five bibliography entries (Halberstam–Richert, Friedlander–Iwaniec,
  Lagarias–Odlyzko, Stephens, Heath-Brown–Patterson) remain pending source
  verification (see `STATUS.md`).

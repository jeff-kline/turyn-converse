# 00 — Master routing: what a full converse still requires

## Statement

The paper's own summary of the remaining gap, quoted verbatim from
`paper/capstone.tex` (§7 "What remains", surviving verbatim from the
companion source at `turyn_converse.tex` lines 4316–4332):

> Conjecture~\ref{conj:converse} is open. The hierarchy above closes every
> self-conjugacy-blind multi-prime composite $q\le2000$, but the proof status
> is not simply ``the finite search got bigger.'' The present state separates
> into three parts: the prime-quotient conceptual layers that are now exact
> criteria, the finite-panel branch accounting for the field-free
> multiplier/marginal layers, and the uniform theorem obligations still
> needed for a full converse.

> \begin{conjecture}[Marginal-complete obstruction program]\label{conj:program}
> Let $q=2t-1$ be composite. Then at least one holds: \emph{(1)} a classical
> two-squares or self-conjugacy obstruction fires; \emph{(2)} the full T3
> multiplier-reduced system is infeasible; \emph{(3)} for some proper divisor
> $t'\mid t$, the $V'$-invariant marginal system of
> Proposition~\ref{prop:t2-marginal} is infeasible; \emph{(4)} all such
> finite marginals pass, but their data do not glue to one element of
> $\Z[C_t]$.
> \end{conjecture}

(Source: `paper/capstone.tex`, label `conj:program`, §7.)

## Why it matters

This conjecture is the paper's routing table: it asserts that every
composite $q$ is caught by one of four named mechanisms. The finite closure
at $q\le2000$ (Appendix B, Tier 0/1) is evidence for each of the four
branches firing in every case checked so far, not a proof that they must.
Problems 01–05 in this directory attack specific, named pieces of that
routing table where a firing criterion is currently either conditional,
missing, or blocked.

## What is known

Branches (1)–(2) are closed-form and unconditional (Tier 0, per
`STATUS.md`). Branch (3)/(4) — the marginal and gluing obstructions — are
where the $q\le2000$ closure lives, and where the open problems below sit:
01–02 concern the conditional density program on the lane $q=6\ell-1$
($\ell\equiv3\bmod4$ prime); 03–04 concern the small-image fold-tower family
(Tier 1, GRH); 05 concerns the unconditional-infinitude question that the
lane's semiprime theorem leaves open.

## Suggested attack

Not a single attack — this file is a router, not a problem. Pick a lane:

- **01-eq3-unconditional.md** — remove the conditionality of the density
  program's analytic input.
- **02-structure-count.md** — the sieve-interaction gap inside that same
  density program (why "Theorem R" was retracted). **Note (2026-07-07):** the
  natural sieve repairs are now proven closed too — see that file's Update
  before investing here.
- **03-stickelberger-fold.md** — turn the per-instance class-group
  computation behind the fold-tower kills into a checkable-in-advance
  criterion.
- **04-wall-witnesses.md** — the two concrete composite $q$ (37825, 93721)
  where even the fold-tower method cannot currently be attempted.
- **05-parity-wall.md** — the parity-problem obstruction to unconditional
  infinitude on the semiprime lane.

## Pointers

- `paper/capstone.tex`: `conj:program`, `conj:converse`, §7 "What remains".
- `STATUS.md` for the tier of every claim this conjecture routes through.

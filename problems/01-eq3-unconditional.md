# 01 — Remove the conditionality of EQ3 (the lane's analytic input)

## Statement

The density program on the lane $q=6\ell-1$ ($\ell\equiv3\bmod4$ prime)
rests on one named, explicit hypothesis, quoted verbatim from
`paper/capstone.tex` (label `def:eq3`):

> \begin{definition}[Cubic Kummer average]\label{def:eq3}
> For squarefree $d=p_1\cdots p_r$ with $(d,6)=1$ let
> \[
>   M_d=\Q\bigl(\zeta_3,\;p_1^{1/3},\dots,p_r^{1/3},\;\zeta_{12d}\bigr),
>   \qquad G_d=\Gal(M_d/\Q),
> \]
> and let $C_d\subseteq G_d$ be the union of conjugacy classes cut out by
> the conditions: $\ell\equiv7\pmod{12}$, and for each $i$,
> $\ell\equiv6^{-1}\pmod{p_i}$ and $p_i$ a cubic residue mod $\ell$ (for
> $\ell\equiv1\bmod3$ the latter says $\ell$ splits completely in
> $\Q(\zeta_3,p_i^{1/3})$). Its density is an \emph{exact} product,
> \[
>   \delta_d:=\frac{|C_d|}{|G_d|}
>   =\frac14\prod_{i=1}^{r}\frac1{3\,\varphi(p_i)},
> \]
> [...] For fixed $\theta\in(0,\tfrac12)$, \emph{Hypothesis}
> $\mathrm{EQ}_3(\theta)$ asserts: for every $A>0$,
> \[
>   \sum_{\substack{d\le x^{2\theta}\\ d\ \text{squarefree},\ (d,6)=1}}
>   \Bigl|\,\pi_{C_d}(x;M_d)-\delta_d\operatorname{Li}(x)\Bigr|
>   \ \ll_A\ \frac{x}{(\log x)^{A}}\,.
> \]
> \end{definition}

The version actually needed for the sieve to run (a strengthening of the
above, uniform over the *number* of Kummer factors $r$, not just $r=1,2$) is
`EQ3′(θ)`, from the (not-yet-typeset-in-the-paper) working note, quoted
verbatim (source: `turyn_theory/density_theorem_r.md` §6.2, in the
source-repo repo — kept behind, not copied into this repo):

> **EQ3′(θ).** For every `A > 0`,
>
>     Σ_{d ≤ x^{2θ}, d squarefree, p|d ⟹ p ∉ {2,3}}
>         max_{C ⊂ G_d, C a union of conjugacy classes}
>             | π_C(x; M_d) - (|C|/|G_d|) Li(x) |   ≪_A   x / (log x)^A.   (6.2)
>
> `EQ3′(θ)` reduces to `EQ3(θ)`'s named sum at `r=1` ... and to its "pairs"
> clause at `r=2` ... the correction is that the same bound is now asserted
> **for every `r` simultaneously, uniformly**, at the *same* level `x^{2θ}`.

## Why it matters

Per `paper/capstone.tex` Appendix B: "Small-factor sieve count
(Proposition~\ref{prop:small-factor-sieve}), T2 (EQ$_3$); GRH implies
EQ$_3(\theta)$ for $\theta<1/8$ (T1) but does not close the lane's remaining
structure count, so the lane density program is not GRH-complete." EQ3 (in
its corrected EQ3′ form) is the single named, falsifiable analytic input the
whole conditional layer of the density program depends on. Proving it (or
finding it false) directly resolves the conditionality of Tier-2 claims
built on it — though not, by itself, the structure-count gap of
**02-structure-count.md** (which, per that file's 2026-07-07 Update, is now
known to be closed to every averaged-Chebotarev route: proving EQ3 removes the
Tier-2 conditionality of `prop:small-factor-sieve`, but by no known route
yields the infinite family).

## What is known

From `rem:lane-density-status`(iii) ("Placement"), `paper/capstone.tex`:

> \emph{(iii) Placement.} $\mathrm{EQ}_3$ is a level-of-distribution
> statement --- Bombieri--Vinogradov for cubic Kummer splitting, averaged
> over the base --- with no parity obstruction; the nearest technology is
> the average-Artin theorem of Stephens~\cite{Stephens69} and the cubic
> large sieve / Kummer-on-average results of
> Heath-Brown--Patterson~\cite{HBP79}, neither directly sufficient.
> Calibration through $q\le2\cdot10^5$: the lane has exactly two members
> with $w=2$ ($q=9185$ and $q=117185$), and the $\omega$-stratified
> frequencies of the cubic-non-residue conditions match the exact
> Chebotarev densities of Definition~\ref{def:eq3}.

From the verification note (`density_theorem_r.md` §14, "What survives
verification"):

> The EQ3′(θ) statement itself (§6.2), well-posed; the paper states the
> summed-family variant over classes `C_{d,v}` ... §6.4's dimension-1/3
> sieve and §8's character algebra, **when run on the full sub-lane** with
> no step (i): under EQ3′(θ) this yields
> `#{ℓ ≤ x sub-lane : every p ≤ x^θ dividing 6ℓ-1 is a cubic non-residue}
> ≥ c(θ)·x/(log x)^{4/3}` — a correct and nontrivial conditional bound, but
> its members are NOT certified nonexistence orders ... so it is a technical
> proposition, not the family theorem.

## Suggested attack

Quoted directly from the same note's closing assessment (§14):

> Next-session target if resumed: formulate the minimal joint hypothesis and
> check whether ANY plausible conjecture-tier input (short of
> primes-in-short-intervals-strength) delivers the family.

The named nearby technology — Stephens' average-Artin theorem and the
Heath-Brown–Patterson cubic large sieve — is explicitly flagged as "neither
directly sufficient"; closing this gap likely means either strengthening
one of those two results to the uniform-in-$r$ form EQ3′ demands, or finding
a genuinely different route to the same bound.

## Pointers

- `paper/capstone.tex`: `def:eq3`, `prop:small-factor-sieve`,
  `rem:lane-density-status`.
- (source repo, not included here) `turyn_theory/density_theorem_r.md` §6.2
  (EQ3′ statement), §14 (verification note, retraction of "Theorem R").

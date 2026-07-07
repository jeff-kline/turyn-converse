# 02 — The structure-count gap (why "Theorem R" was retracted)

> **⚠ UPDATE (2026-07-07): the "β(1/3) < 1" / unified-sieve route quoted below
> is now CLOSED — do not spend cycles on it.** A follow-up attempt ("Theorem
> R′", a unified dimension-1/3 sieve) resolved this question *negatively* for
> the entire averaged-Chebotarev genus: `β(1/3) = 1` exactly, so a lower-bound
> sieve at `s < 1` is provably impossible, and the one variant that does run
> is killed by a cubic-symbol parity barrier. Full, accurate account in the
> **Update** section at the end of this file. The verbatim quotes below are
> preserved as the historical record that prompted R′; read the Update first.

## Statement

Even granting EQ3 (see **01-eq3-unconditional.md**), converting the lane's
small-factor obstruction count into an infinite nonexistence family requires
one more, currently open, structure count. Quoted verbatim from
`paper/capstone.tex`, `rem:lane-density-status`(i):

> \emph{(i) What is not yet proved.} Members of the set in
> Proposition~\ref{prop:small-factor-sieve} are not certified nonexistence
> orders: $q$ may have prime factors in $(x^\theta,\sqrt q\,]$ about which
> the proposition says nothing, and only the at-most-one factor above
> $\sqrt q$ is pinned by Lemma~\ref{lem:character-pinning}. Converting the
> count into an infinite family of Proposition~\ref{prop:lane-kill} kills
> requires exactly (a) a structure count --- sub-lane primes with
> $6\ell-1=(x^\theta\text{-smooth})\cdot(\text{prime})$ --- which the linear
> sieve at Bombieri--Vinogradov level does not reach (sifting the middle
> range to $\sqrt{6x}$ at level $x^{1/2-\varepsilon}$ has $s=1$, below the
> linear sieving limit; per fixed smooth cofactor the count is a
> two-linear-forms prime pair, a parity-type problem), and (b) a joint
> (vector-sieve) average running the Kummer conditions relative to the
> structured set, which $\mathrm{EQ}_3$ as stated does not supply. A
> 2026-07-06 bookkeeping attempt at (a)+(b) was retracted on verification,
> gapped at both points [...]

## Why it matters

An earlier working draft ("Theorem R") claimed to close exactly this gap
under EQ3′; a same-day independent verification pass retracted the verdict.
The two fatal findings are a precise diagnosis of why this is hard, quoted
verbatim from `turyn_theory/density_theorem_r.md` §14:

> **F1 — §4.1's sieve threshold is arithmetically false.** Step 1 sifts the
> middle range `(x^θ, x^{1/2-ε}]` at BV level `D = x^{1/2-ε}`, so `s = log D
> / log z = 1`; the text claims the Jurkat–Richert threshold `s > 2` is
> "cleared" ... but the honest ratio is `s = 1`, where the linear
> lower-bound sieve gives `f_1(1) = 0` — no positive lower bound. [...] the
> underlying object — primes `ℓ` with `6ℓ-1 = (x^θ-smooth)·(single prime)` —
> is, per fixed smooth cofactor `m`, a two-linear-forms-simultaneously-prime
> problem (parity-blocked for lower bounds) [...]
>
> **F2 — the step-(i)/(ii) interaction is dropped.** (6.1) defines `A_d`
> over the *step-(i) survivor set* ... but §6.1 then identifies `E_p` with
> `π_{C_p}(x; M_p)` and §6.4 bounds the remainder by EQ3′ — which controls
> full sub-lane class counts, not counts inside an already-sifted set.
> Equivalently, §10.2's assembly multiplies the step-(i) constant `c_1(θ)`
> by the step-(ii) sieve factor as if the two events were independent; that
> independence is precisely what a joint (vector-sieve) remainder hypothesis
> would have to supply, and EQ3′ as stated does not.

## What is known

The retraction is total, not partial — quoted from the same note:

> **Status of Theorem R.** Unproved under any hypothesis stated so far. The
> missing ingredient is control of the factors of `6ℓ-1` above the sieve
> level jointly with the Kummer conditions — either a beyond-`x^{1/2}`
> hybrid average (BFI-flavored, NOT known to follow from GRH by the
> per-modulus bound: the `p`-sum of `x^{1/2}`-size errors over `p ≤ x^{1/2}`
> is already `x^{1-o(1)}`), or a unified dimension-1/3 sieve to level near
> `x^{1/2}` exploiting `β(1/3) < 1` with a shrinking window — both research
> projects, not bookkeeping.

## Suggested attack

Quoted directly, same source: the note names two concrete non-classical
routes, neither yet attempted:

> either (i) a parity-breaking input for semiprime values of `6ℓ-1` at
> prime arguments — current analytic number theory does not provide it —
> or (ii) a unified dimension-1/3 sieve to level near `x^{1/2}` exploiting
> `β(1/3) < 1` with a shrinking window.

Note the overlap with **05-parity-wall.md**: route (i) here is the same
parity obstruction discussed there, approached from the sieve-bookkeeping
side rather than the Chen/Dickson side.

## Update (2026-07-07): the suggested sieve route is now closed

The routes quoted in "What is known" and "Suggested attack" were attempted
after this file was written, in a follow-up called **Theorem R′** — a
*unified dimension-1/3 sieve*: one sieve run straight to `z = (6x)^{1/2}` with
no Buchstab step, so F1's structure count and F2's two-sieve interaction both
vanish by construction. The result closes the question negatively for the
whole averaged-Chebotarev (EQ3 / EQ_r) genus. Verified against disk by the
mainline session 2026-07-07; full deliverable (source repo, not included here)
`turyn_theory/density_theorem_rprime.md`, §§5 and 8.

- **The "unified dimension-1/3 sieve exploiting `β(1/3) < 1`" route (route (ii)
  above) is provably impossible.** `β(1/3) = 1` exactly (Iwaniec, *Rosser's
  sieve*, Acta Arith. 36 (1980), p. 173); more strongly, *no* lower-bound
  sieve of *any* dimension is positive below `s = 1`, by a self-contained
  impossibility (rprime §5.3): redefine one prime's event in `(D, z]` to equal
  the level-`D` survivor set — the sieve collapses to `0` while every level-`D`
  remainder stays untouched, because a plain-remainder hypothesis at level `D`
  carries no information about primes in `(D, z]`. The unified sieve has
  `s = log D / log z = 4θ − o(1)`; the family needs `θ ≤ 1/4`, hence `s ≤ 1`
  — dead at the sifting limit. The `β(1/3) < 1` premise was an unverified guess
  in the old §14 note quoted above; it is false.

- **The one variant that runs is killed by a parity barrier.** For
  `θ ∈ (1/4, 1/2)` the sieve does run (`s → 4θ > 1`, and `f(1) = B > 0` in
  dimension `< 1/2`), and its remainder *is* EQ3's sum verbatim — but at level
  `x^{2θ} ∈ (x^{1/2}, x)`, i.e. Elliott–Halberstam-analogue strength with an
  **empty GRH tier**. The endgame then fails structurally (rprime §8.4): the
  kill needs `χ(m) ≠ 1`, where `χ(m) = ∏_{p | m} χ(p)` couples
  `~(2/3)log log x` cubic symbols, so detecting it requires joint
  prescribed-symbol equidistribution at moduli `x^{c·log log x}` — beyond what
  *any* EQ3-family (def:eq3) hypothesis expresses, at *any* level. This is the cubic
  analogue of Selberg's parity problem.

- **The other routes named above do not rescue a conditional family.** The
  "parity-breaking input for semiprime `6ℓ-1` at prime arguments" and the
  "beyond-`x^{1/2}` BFI-flavored hybrid" were left untouched by R′ (out of
  scope), but both are strictly-stronger-than-GRH inputs that current analytic
  number theory does not provide — so neither yields a family conditional on
  EQ3 or on GRH. They belong to the "new mathematics" bucket, overlapping
  **05-parity-wall.md**.

**Net.** Every route to the infinite family through an averaged-Chebotarev
hypothesis (EQ3, EQ3′, or an EQ_r extension) is now closed, at every `θ`: one
branch by a genuine sieve impossibility, the other by non-expressibility of
the parity-type endgame. A repair needs genuinely *new* mathematics — a
dispersion / Barban–Davenport–Halberstam theory for cubic symbols over sifted
sets, or a designed bilinear structure — not a sharper sieve or a stronger
hypothesis name. The same barrier, in its `r`-analogue, also blocks the
almost-all route; see **05-parity-wall.md**. The family and its `2/3`
survival constant remain numerically solid — what is closed is every *proof*
route from this genus, not the truth of the statement.

## Pointers

- `paper/capstone.tex`: `rem:lane-density-status`, `prop:small-factor-sieve`,
  `prop:lane-kill`, `lem:character-pinning`.
- (source repo, not included here) `turyn_theory/density_theorem_r.md` §14
  (the full retraction note, findings F1–F3).
- (source repo, not included here) `turyn_theory/density_theorem_rprime.md`
  (Theorem R′, 2026-07-07): §5 (Gate 0, `β(1/3) = 1`, the impossibility
  proof), §8 (Gate 3, the parity barrier), §9 (assembly and the collateral
  findings on old §8 and the almost-all route).

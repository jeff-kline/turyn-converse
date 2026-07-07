# 04 — The two orders the fold-tower method cannot yet reach: q=37825, q=93721

## Statement

Within the small-image frontier (the four $q\le100000$ survivors of the
census — $5185$, $37825$, $62305$, $93721$ — of which $5185$ and $62305$
are killed, GRH tier), the remaining two are blocked not by the Stickelberger
gap of **03-stickelberger-fold.md** but by something more basic: no
fold field small enough to compute is even available. Quoted verbatim
(source: `turyn_theory/small_image_family.md` §5, "Gap 2 — infeasible fold
fields / surviving amplified levels"):

> The dichotomy cannot even be attempted at the other two survivors:
>
> - `q = 37825 = 5²·17·89`: the only nontrivial-U targets are p'=17 (fold
>   degree 2364, disc ~1e10813) and p'=89 (degree 48, ~1e211, and an
>   amplified level survives at w'=16); p'=5 has U = 1 (and 5² || q needs
>   the valuation-vector normal form).
> - `q = 93721 = 17·37·149` (w = 2, the minimal image): p'=37 has the only
>   small fold field (k_5(i), degree 10, disc ~1e40, beyond calibration) and
>   its amplified levels survive at w' ∈ {10, 20, 30, 60} — so even a
>   perfect fold cut there cannot close it; p'=17/149 folds are degree
>   284/66, infeasible.

## Why it matters

These are not "harder instances of the same computation" — the note is
explicit that the required class-group computations are out of reach at any
foreseeable computational budget (discriminants from $10^{40}$ to
$10^{10813}$), and in the $q=93721$ case, even a hypothetically free class-
group computation at the one small-ish fold field available would not
suffice ("even a perfect fold cut there cannot close it"). These two orders
are concrete witnesses that the fold-tower method, as currently formulated,
has a real ceiling — not just an inconvenience.

## What is known

$q=37825$ has one prime ($5$) whose associated target subgroup is trivial
($U=1$), which the dichotomy's amplification step needs to be nontrivial;
that prime also appears squared ($5^2 \| q$), which the note flags as
needing an unformalized generalization ("the valuation-vector normal
form"). $q=93721$ has the minimal possible image ($w=2$) and its one
computationally-approachable fold field still has surviving amplified
levels that a fold cut alone cannot rule out.

## Suggested attack

Quoted verbatim, the note's own proposed refinement direction:

> a *partial-fold* variant — at an intermediate level `k_{e'}(i)`, `e' | e`
> small, forcing the folded weights to the extremes {0, n_fold} forces the
> pattern constant on fold fibers, amplifying by (fiber kernel) ∩
> U-analogue. This would give 37825/93721 feasible fold fields (e.g. e' =
> 2, 3 at p'=17), at the price of a stronger firing condition; whether it
> can fire anywhere is untested.

This is explicitly untested, not merely unproven — a first useful step
would be to test whether the partial-fold construction fires at all, before
attempting to prove it does so in general.

## Pointers

- `paper/capstone.tex`: `lem:stabilizer-rigidity`, `cor:full-torus-exact-char`
  (the underlying unconditional machinery these two orders still satisfy up
  to the fold step).
- (source repo, not included here) `turyn_theory/small_image_family.md` §2
  (census producing the four-member frontier), §5 (Gap 2, quoted above).

# 05 — The parity wall: unconditional infinitude on the semiprime lane

## Statement

Quoted verbatim from `paper/capstone.tex`, `rem:parity-wall`:

> \begin{remark}[The parity wall, and the lane's calibration]
> \label{rem:parity-wall}
> Unconditional infinitude of the composite members is a parity-problem
> instance: ``$\Omega(6\ell-1)=2$ for infinitely many primes $\ell$'' is of
> the same class as ``$p+2$ is a semiprime infinitely often,'' open despite
> Chen's theorem, and the standard $E_2$/GPY technology does not apply
> because $\ell$ itself must be prime. For $\omega(q)\ge3$ the
> deterministic collapse fails structurally: the product relation
> $\prod p_i^{e_i}\equiv-1\pmod\ell$ constrains the join of the cyclic
> groups $\langle p_i\rangle$, never their intersection. Calibration at
> $q\le10^7$ ($62{,}929$ lane primes $\ell$): $18.7\%$ of lane members are
> Theorem~\ref{thm:semiprime-converse} kills, $18.5\%$ die classically,
> $17.9\%$ have $q$ prime, and $41.4\%$ sit behind the parity wall --- of
> which $99.98\%$ pass the gcd-of-orders proxy for $w\ge4$, so the
> obstruction to closing them is proof technology, not truth.
> \end{remark}

Theorem~\ref{thm:semiprime-converse} referenced above, also verbatim:

> \begin{theorem}[Semiprime partial converse on the lane
> $q\equiv5\pmod6$]\label{thm:semiprime-converse}
> Let $\ell\equiv3\pmod4$ be prime and let $q=6\ell-1$ be composite with
> $\Omega(q)=2$. Then no Turyn pair of order $t=3\ell$ exists.
> \end{theorem}

## Why it matters

This theorem is unconditional and exact, but only for $q$ that already have
exactly two prime factors ($\Omega(q)=2$). Whether there are *infinitely
many* such $q$ on the lane is exactly as hard as knowing whether $p+2$ is a
semiprime infinitely often — a question open despite Chen's theorem, and
blocked by Selberg's parity barrier, not by any gap in this paper's own
machinery. The calibration figure above — 41.4% of lane members "sit behind
the parity wall" with 99.98% of those otherwise passing every other
criterion — says the remaining obstruction is close to purely this one
analytic-number-theory question, not an accumulation of many smaller gaps.

## What is known

The working note's fuller account of why standard technology does not
apply, quoted verbatim (source: `turyn_theory/density_partial_converse.md`
§6, in the source-repo repo — kept behind, not copied into this repo):

> The task anticipated the crux at decoupling order conditions on the
> `ell`-dependent primes `p | 6*ell - 1` from `ell`. **That coupling is
> eliminated**: on the lane `ell ≡ 3 (mod 4)`, for `omega(q) = 2` the
> conditions (`w >= 4`, `d` odd) hold *deterministically* ... The wall has
> moved to pure factor-counting:
>
> > **Open analytic input for unconditional T1**: infinitely many primes
> > `ell ≡ 3 (mod 4)` with `Omega(6*ell - 1) = 2` (`q` composite).
>
> This is a parity-problem instance. Sieve methods cannot distinguish
> `Omega = 1` from `Omega = 2` in the P_2 output of Chen's theorem
> (Selberg's parity barrier ...); the same barrier blocks "`p + 2` is a
> semiprime infinitely often" ... The known parity-breaking results
> (Friedlander–Iwaniec `x^2 + y^4`, Heath-Brown `x^3 + 2y^3`, GGPY
> E_2-tuples) do not apply: our shape needs `ell` *prime* ... so the
> E_2-pair technology (which succeeds precisely by avoiding primes) is
> structurally unavailable.

The same note records four rejected routes (anchored factor, two-variable
quadratic families, $\omega\ge3$ forced structure, Sophie-Germain-shaped
$\ell$) and notes GRH/Elliott–Halberstam "neither breaks parity; no help."

## Suggested attack

Quoted verbatim, the note's own escalation assessment:

> unconditional T1 through this (fixed) route requires either (i) a
> parity-breaking input for semiprime values of `6*ell - 1` at prime
> arguments — current analytic number theory does not provide it — or (ii)
> a new firing criterion at *composite* `t'` strong enough to exploit
> E_2-technology on `ell` ... strengthening `cor:h3-support-sum-gcd` ...
> Both are outside this task's scope; Theorems C/D are the honest maxima.

Route (ii) is the more paper-native option: it asks whether the paper's own
$h=3$ machinery (`cor:h3-support-sum-gcd`) can be strengthened enough at
composite $t'$ to let E$_2$-style technology apply to $\ell$ after all,
rather than waiting on a new analytic-number-theory input for semiprimality
of $6\ell-1$ directly.

## Pointers

- `paper/capstone.tex`: `rem:parity-wall`, `thm:semiprime-converse`,
  `cor:h3-support-sum-gcd`.
- (source repo, not included here) `turyn_theory/density_partial_converse.md`
  §6 ("The wall"), which also documents the rejected routes in full.

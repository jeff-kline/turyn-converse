# Per-environment audit ledger

One row per theorem-like environment in `paper/capstone.tex` (**129** total: the same 7 environment types `code/tools/check_transcription.py` counts). Numbers are LaTeX's own shared `[section]` theorem counter, computed by walking the document and **cross-validated against `paper/capstone.aux`** (0 mismatches) — regenerate with `code/tools/build_audit_ledger.py`.

**Columns.**

- *Prior coverage* — what `AUDIT_LOG.md` records about this specific environment. `aggregate-only` means it was covered solely by the 129/129 full-coverage count, whose per-row ledger was a private artifact **not** preserved in the repo — i.e. no independently checkable per-environment record existed before this ledger.
- *Audit verdict* — populated by the complete adversarial audit (see the run recorded in `AUDIT_LOG.md`). `— pending` until that audit signs the row off. Sourced from `code/audit/verdicts.json`.

**Status:** 129 environments · 18 with a prior per-env note · 0 with a new-audit verdict.

| # | Type | Label | Title | Prior coverage | Audit verdict |
|---|---|---|---|---|---|
| 1.1 | Definition | `def:turyn-pair` | — | aggregate-only | — pending |
| 1.2 | Theorem | `thm:turyn` | Turyn 1972~\cite{Turyn72} | aggregate-only | — pending |
| 1.3 | Conjecture | `conj:converse` | Turyn's converse | aggregate-only | — pending |
| 3.1 | Theorem | `thm:multiplier` | Frobenius multiplier, exact signs | aggregate-only | — pending |
| 3.2 | Lemma | `lem:per-character-unit` | — | aggregate-only | — pending |
| 3.3 | Lemma | `lem:coherence` | — | aggregate-only | — pending |
| 3.4 | Corollary | `cor:orbits` | — | aggregate-only | — pending |
| 3.5 | Definition | `def:composite-M` | — | aggregate-only | — pending |
| 3.6 | Lemma | `lem:composite-coherence` | Composite coherence | aggregate-only | — pending |
| 3.7 | Theorem | `thm:composite-multiplier` | Composite multiplier | aggregate-only | — pending |
| 3.8 | Remark | *(unlabeled)* | — | aggregate-only | — pending |
| 4.1 | Proposition | `prop:twosquares` | — | aggregate-only | — pending |
| 4.2 | Lemma | `lem:signed-branch-reduction` | Signed branch after two squares | aggregate-only | — pending |
| 4.3 | Proposition | `prop:selfconj` | — | aggregate-only | — pending |
| 4.4 | Remark | `rem:blindspot` | The blind spot | Finding F1 (code-correctness): prose characterization corrected + 80/31 split; FIXED + mirrored. | — pending |
| 4.5 | Proposition | `prop:t3-decision` | Orbit-reduced decision | aggregate-only | — pending |
| 4.6 | Definition | `def:marginal-orbit-algebra` | Marginal orbit algebra | aggregate-only | — pending |
| 4.7 | Lemma | `lem:marginal-algebra` | Marginal algebra lemma | aggregate-only | — pending |
| 4.8 | Definition | `def:signed-marginal-module` | Signed marginal module | aggregate-only | — pending |
| 4.9 | Proposition | `prop:signed-marginal` | Signed marginal obstruction | aggregate-only | — pending |
| 4.10 | Corollary | `cor:signed-full-torus-sign` | Signed full-torus sign criterion | aggregate-only | — pending |
| 4.11 | Corollary | `cor:signed-full-unit-prime` | Signed full-unit prime-torus obstruction | aggregate-only | — pending |
| 4.12 | Proposition | `prop:t2-marginal` | Sub-torus marginal obstruction | aggregate-only | — pending |
| 4.13 | Corollary | `cor:exact-secondary-marginal` | Exact secondary marginal certificate | aggregate-only | — pending |
| 4.14 | Proposition | `prop:h3-support-augmentation` | $h=3$ support-augmentation obstruction | aggregate-only | — pending |
| 4.15 | Corollary | `cor:h3-support-paf` | $h=3$ support-PAF firing criterion | aggregate-only | — pending |
| 4.16 | Corollary | `cor:h3-support-sum-prime` | Prime support-sum closed form | aggregate-only | — pending |
| 4.17 | Corollary | `cor:h3-support-sum-gcd` | Composite support congruence | Deferred (baseline Open): candidate demote-to-remark (self-described coarse; superseded by prop above). | — pending |
| 4.18 | Proposition | `prop:h3-augmentation-reps` | $h=3$ augmentation representation criterion | Principal (h=3 hierarchy head), T0; L2a SOUND at bucket level; Fable-pass claims reconstruction; code-pass (AUDIT_LOG:143) says NOT re-audited there. | — pending |
| 4.19 | Corollary | `cor:h3-augmentation-residue` | $h=3$ augmentation residue criterion | aggregate-only | — pending |
| 4.20 | Proposition | `prop:q1445-h3-paf` | Closure of $q=1445$ at $t'=241$ | aggregate-only | — pending |
| 4.21 | Proposition | `prop:component-join` | Component join criterion | aggregate-only | — pending |
| 4.22 | Corollary | `cor:full-torus-sign` | Full-torus sign firing criterion | aggregate-only | — pending |
| 4.23 | Theorem | `thm:full-torus-rowsum` | Full-torus row-sum bound | Principal (row-sum bound + sharpness), T0; L2a SOUND at bucket level. | — pending |
| 4.24 | Remark | `rem:rowsum-sharp` | Sharpness and the small-image regime | aggregate-only | — pending |
| 4.25 | Corollary | `cor:full-torus-exact-char` | Exact trivial-character firing | aggregate-only | — pending |
| 4.26 | Lemma | `lem:stabilizer-rigidity` | Stabilizer rigidity | aggregate-only | — pending |
| 4.27 | Proposition | `prop:q5185-f4-cut` | The $F_4$ class-group cut at $q=5185$ | aggregate-only | — pending |
| 4.28 | Proposition | `prop:q5185-closure` | Closure of $q=5185$, conditional on $\Cl(F_4)$ | aggregate-only | — pending |
| 4.29 | Remark | `rem:small-image-conditional` | Conditionality ledger and the general mechanism | aggregate-only | — pending |
| 4.30 | Proposition | `prop:fold-dichotomy` | Fold-amplification dichotomy | aggregate-only | — pending |
| 4.31 | Proposition | `prop:q62305-closure` | Closure of $q=62305$, conditional on
$\Cl(k_3(i))$ | aggregate-only | — pending |
| 4.32 | Remark | `rem:fold-gaps` | The two named gaps, and the wall witnesses | aggregate-only | — pending |
| 4.33 | Proposition | `prop:prime-subtorus-component` | Prime sub-torus component criterion | aggregate-only | — pending |
| 4.34 | Proposition | `prop:prime-subtorus-periods` | Prime sub-torus period transform | aggregate-only | — pending |
| 4.35 | Corollary | `cor:prime-subtorus-firing` | Prime sub-torus firing criterion | aggregate-only | — pending |
| 4.36 | Lemma | `lem:quadratic-two-square` | Quadratic two-square parametrization | aggregate-only | — pending |
| 4.37 | Proposition | `prop:c27-component` | $C_{27}$ full-unit component criterion | aggregate-only | — pending |
| 4.38 | Proposition | `prop:c27-nested` | $C_{27}$ nested congruence criterion | aggregate-only | — pending |
| 4.39 | Corollary | `cor:c27-auto-box` | Automatic boxes for large $C_{27}$ marginals | Fix5: h>=57->55 HELD (bound correct-but-loose, not a bug; per user, left as-is). | — pending |
| 4.40 | Corollary | `cor:c27-residue-pair` | $C_{27}$ residue-pair firing criterion | aggregate-only | — pending |
| 4.41 | Corollary | `cor:c27-arithmetic-firing` | $C_{27}$ arithmetic firing alternatives | aggregate-only | — pending |
| 4.42 | Proposition | `prop:pe-full-unit-nested` | Full-unit prime-power nested criterion | Findings baseline#3 (y_{-1}:=0) and Fix3 (phi(p^{e-j})): two real proof-typos; BOTH FIXED, Fix3 verified 3 ways. | — pending |
| 4.43 | Corollary | `cor:pe-residue-pair` | Residue-pair collapse at $p^e$ | aggregate-only | — pending |
| 4.44 | Corollary | `cor:c49-nested` | $C_{49}$ full-unit nested criterion | Fix4: prop:->cor: relabel + removed dead trailing label; FIXED. | — pending |
| 4.45 | Theorem | `thm:t2-twoorbit` | Transitive two-orbit marginal obstruction | aggregate-only | — pending |
| 4.46 | Theorem | `thm:two-orbit-reps` | Two-orbit representation criterion | Principal (Two-orbit criterion), T0; baseline L2a SOUND at bucket level. | — pending |
| 4.47 | Corollary | `cor:two-orbit-parity` | Parity firing for large nodes | aggregate-only | — pending |
| 4.48 | Corollary | `cor:transitive-full-torus` | Transitive full torus | aggregate-only | — pending |
| 4.49 | Corollary | `cor:c3-feasible` | The $C_3$ node never fires | aggregate-only | — pending |
| 4.50 | Remark | `rem:two-orbit-arithmetic` | Arithmetic form, and the audit | aggregate-only | — pending |
| 4.51 | Definition | `def:prime-square-lift` | Prime-square lift marginal | aggregate-only | — pending |
| 4.52 | Theorem | `thm:prime-square-lift` | Prime-square lift marginal certificate | aggregate-only | — pending |
| 4.53 | Proposition | `prop:p3-gaussian` | The $p=3$ Gaussian component criterion | aggregate-only | — pending |
| 4.54 | Proposition | `prop:p5-sqrt5` | The $p=5$ quadratic-component criterion | aggregate-only | — pending |
| 4.55 | Proposition | `prop:p7-cubic` | The $p=7$ cubic-component criterion | aggregate-only | — pending |
| 4.56 | Proposition | `prop:q1469-p7-cubic` | Closure of $q=1469$ at $t'=49$ | aggregate-only | — pending |
| 4.57 | Proposition | `prop:c21-sqrt21` | $C_{21}$ quadratic-component criterion | aggregate-only | — pending |
| 4.58 | Corollary | `cor:c21-arithmetic-firing` | $C_{21}$ arithmetic firing criterion | aggregate-only | — pending |
| 4.59 | Proposition | `prop:c57-sqrt57` | $C_{57}$ quadratic-component criterion | aggregate-only | — pending |
| 4.60 | Proposition | `prop:q549-fiveorbit` | The $p=5$ prime-square lift certificate at
\texorpdfstring{$q=549$}{q=549} | Terminal kill certificate; L2a disclosed that individual finite emptiness certs were not each re-run. | — pending |
| 4.61 | Proposition | `prop:c51-quartic` | The quartic-component criterion at $t'=51$ | aggregate-only | — pending |
| 4.62 | Proposition | `prop:q1325-quartic` | Closure of $q=1325$ at the $t'=51$ marginal | aggregate-only | — pending |
| 4.63 | Lemma | `lem:lattice-functoriality` | Lattice functoriality | aggregate-only | — pending |
| 4.64 | Lemma | `lem:orbit-census` | Orbit census | aggregate-only | — pending |
| 4.65 | Lemma | `lem:top-exact` | Exactness at the top node | aggregate-only | — pending |
| 4.66 | Theorem | `thm:divisor-selection` | Existential divisor selection | Principal (Selection thm), T0; baseline L2a SOUND at bucket level; rem:selection-open flags headline as near-tautology. | — pending |
| 4.67 | Corollary | `cor:projection-image` | Projection-image criterion | aggregate-only | — pending |
| 4.68 | Remark | `rem:selection-open` | What the selection theorem does and does not provide | aggregate-only | — pending |
| 4.69 | Lemma | `lem:anchor-pm1` | Anchor: no $\pm1$ factors at composite shifted primes | aggregate-only | — pending |
| 4.70 | Lemma | `lem:semiprime-image` | Semiprime multiplier image | aggregate-only | — pending |
| 4.71 | Theorem | `thm:semiprime-converse` | Semiprime partial converse on the lane
$q\equiv5\pmod6$ | Principal (semiprime lane), T0; L2a SOUND at bucket level. | — pending |
| 4.72 | Theorem | `thm:omega2-converse` | Two-prime-support extension | aggregate-only | — pending |
| 4.73 | Theorem | `thm:dickson-family` | Conditional infinitude | Principal (Dickson family), T2; F2 (capstone-local) added bibitems + wired cites; byte-mirrored. | — pending |
| 4.74 | Theorem | `thm:chen-dichotomy` | Dichotomy under a congruence-restricted Chen
input | aggregate-only | — pending |
| 4.75 | Remark | `rem:chen-input` | Status of hypothesis (C) | Principal (hyp-(C) inputs), T2; F2 added bibitems; no exact citation for hyp (C) (disclosed). | — pending |
| 4.76 | Remark | `rem:parity-wall` | The parity wall, and the lane's calibration | Finding baseline#6: member-list class scoping tightened; FIXED + mirrored. | — pending |
| 4.77 | Lemma | `lem:lane-image` | Multiplier image on the lane at general $\omega$ | aggregate-only | — pending |
| 4.78 | Proposition | `prop:lane-kill` | Deterministic kill at general $\omega$ | Principal (lane collapse), T0; L2a SOUND at bucket level. | — pending |
| 4.79 | Lemma | `lem:lane-residue` | Residue reformulation of the bad set | aggregate-only | — pending |
| 4.80 | Lemma | `lem:character-pinning` | Character pinning | aggregate-only | — pending |
| 4.81 | Definition | `def:eq3` | Cubic Kummer average | aggregate-only | — pending |
| 4.82 | Proposition | `prop:small-factor-sieve` | Small-factor obstruction count | Principal (small-factor sieve), T2(EQ3); DISCLOSED UNVERIFIED (imported sieve constants); density program not GRH-complete. | — pending |
| 4.83 | Remark | `rem:lane-density-status` | From the small factors to a family: status | Citation/wording touched (F-set); byte-mirror-checked capstone==companion. | — pending |
| 4.84 | Definition | `def:rigid` | — | aggregate-only | — pending |
| 4.85 | Theorem | `thm:rigidity` | Rigidity | aggregate-only | — pending |
| 4.86 | Remark | `rem:escapes` | — | aggregate-only | — pending |
| 4.87 | Corollary | `cor:allrigid` | All-rigid obstruction | aggregate-only | — pending |
| 4.88 | Corollary | `cor:primet` | Prime order | aggregate-only | — pending |
| 4.89 | Theorem | `thm:4373` | — | aggregate-only | — pending |
| 4.90 | Remark | `rem:consistency` | Consistency | aggregate-only | — pending |
| 4.91 | Remark | `rem:sharp` | Sharpness | aggregate-only | — pending |
| 4.92 | Lemma | `lem:recon` | Reconstruction | aggregate-only | — pending |
| 4.93 | Lemma | `lem:idealunit` | Ideal/unit layer | aggregate-only | — pending |
| 4.94 | Lemma | `lem:raygluing` | Parity and ray gluing | aggregate-only | — pending |
| 4.95 | Theorem | `thm:realization` | Uniform realization criterion | aggregate-only | — pending |
| 4.96 | Theorem | `thm:descent` | Prime-quotient descent | aggregate-only | — pending |
| 4.97 | Remark | `rem:box` | The identity-coefficient bound | aggregate-only | — pending |
| 4.98 | Definition | `def:defect` | Ray defect | aggregate-only | — pending |
| 4.99 | Lemma | `lem:localfactor` | Local factor lemma | aggregate-only | — pending |
| 4.100 | Proposition | `prop:fieldfree` | Ray criterion up to the defect | aggregate-only | — pending |
| 4.101 | Corollary | `cor:trivialdefect` | Trivial-defect product formula | aggregate-only | — pending |
| 4.102 | Proposition | `prop:imq` | — | aggregate-only | — pending |
| 4.103 | Theorem | `thm:absorbedC` | Absorbed ray criterion | aggregate-only | — pending |
| 5.1 | Remark | `rem:closed-restated` | What ``closed'' asserts, restated | aggregate-only | — pending |
| 7.1 | Conjecture | `conj:program` | Marginal-complete obstruction program | aggregate-only | — pending |
| A.1 | Remark | `rem:maryscope` | Notation for this section | aggregate-only | — pending |
| A.2 | Lemma | `lem:coverage` | Coverage | aggregate-only | — pending |
| A.3 | Lemma | `lem:orth` | Orthogonality | aggregate-only | — pending |
| A.4 | Theorem | `thm:normalform` | Normal form | aggregate-only | — pending |
| A.5 | Corollary | `cor:turyn2` | Turyn 1972, the case $m=2$ | aggregate-only | — pending |
| A.6 | Theorem | `thm:dichotomy` | Fillability dichotomy | aggregate-only | — pending |
| A.7 | Remark | `rem:quat` | Quaternionic completion, and the exact boundary | aggregate-only | — pending |
| A.8 | Proposition | `prop:twosquaresm4` | — | aggregate-only | — pending |
| A.9 | Proposition | `prop:Lstar` | The quartic $2$-adic refinement | Fix2: conj:->prop: label prefix corrected; FIXED + mirrored. | — pending |
| A.10 | Remark | *(unlabeled)* | — | aggregate-only | — pending |
| A.11 | Proposition | `prop:dictionary` | Twisted-circulant form | aggregate-only | — pending |
| A.12 | Remark | `rem:unroll` | Single-sequence unrolling | aggregate-only | — pending |
| A.13 | Remark | `rem:maryfurther` | Further directions on the construction side | aggregate-only | — pending |


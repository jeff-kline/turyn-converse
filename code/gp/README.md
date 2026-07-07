# code/gp/

PARI/gp verification of the isolated imaginary-quadratic class-group inputs to
the Tier-1 fold-tower kills (q=5185, q=62305).

- `fold_tower_anchors.gp` — the script.
- `fold_tower_anchors.out.txt` — recorded transcript (`gp -q fold_tower_anchors.gp`).

Scope: the full degree-40 fold-tower class groups (`Cl(F_3)=C_21 x C_21` with
`bnfcertify`, `Cl(F_4)`, `Cl(k_3(i))=C_5799`) are computed by the source-repo
scripts (`small_image_fe_tower.py`, `q5185_*.py`; gp-driven) and are stated in
the paper as explicit GRH hypotheses. This bundle reproduces only the cheap,
unconditional quadratic anchors those computations rest on (e.g. `h(-10372)=24`).
Requires PARI/gp (tested with 2.17).

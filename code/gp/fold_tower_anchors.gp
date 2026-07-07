\\ ============================================================================
\\ fold_tower_anchors.gp
\\ PARI/gp verification of the isolated imaginary-quadratic class-group inputs
\\ to the Tier-1 fold-tower nonexistence kills (q = 5185, q = 62305).
\\
\\ The full degree-40 fold-tower class groups (Cl(F_3) = C_21 x C_21 with
\\ bnfcertify, Cl(F_4), Cl(k_3(i)) = C_5799) are computed by the source-repo
\\ scripts (small_image_fe_tower.py, q5185_*.py; gp-driven) and are stated in
\\ the paper as explicit GRH hypotheses. This script reproduces the isolated
\\ quadratic anchors those computations rest on -- cheap and unconditional here.
\\ Run:  gp -q fold_tower_anchors.gp
\\ ============================================================================

D = -10372;    \\ = -4 * 2593; disc of Q(sqrt(-2593)); 2593 is an F_4 fold prime
print("field: Q(sqrt(-2593)),  disc D = ", D, " = -4 * 2593");
print("2593 prime?   ", isprime(2593));
print("31153 prime?  ", isprime(31153), "   (an F_3 / k_3(i) fold prime for q=62305)");

bnf = bnfinit(x^2 - D);
print("h(D)            = ", bnf.no,  "     (paper/audit: 24)");
print("Cl(D) structure = ", bnf.cyc);

\\ splitting behaviour of 17, 5, 61 (from the constant-17-pattern analysis)
print("kronecker(D,17) = ", kronecker(D,17), "   (+1 => 17 splits)");
print("kronecker(D, 5) = ", kronecker(D, 5), "   (-1 =>  5 inert)");
print("kronecker(D,61) = ", kronecker(D,61), "   (-1 => 61 inert)");

\\ order of the class of a prime above 17 in Cl(D)
P17 = idealprimedec(bnf, 17)[1];
e   = bnfisprincipal(bnf, P17)[1];
ord = 1;
for(i = 1, #bnf.cyc, if(e[i] != 0, ord = lcm(ord, bnf.cyc[i] / gcd(bnf.cyc[i], e[i]))));
print("ord([P_17]) in Cl(D) = ", ord, "   (paper/audit: 12)");

quit;

# DKLLW chart conventions implemented by HFPSS Studio

This document records the display contract used by the Studio. It is a
presentation contract, not a replacement for the proposition graph or for a
proof of a differential.

## Published class glyphs

The published version of [DKLLW24], Table 11 uses:

| Glyph | Meaning |
| --- | --- |
| dot | \(k\) |
| fat dot | \(k[[j]]\) |
| circle | \(k[[j]]\{j\}\) |
| square | \(\mathbb W(k)\) |

Here \(k=\mathbb F_2\) for the \(SD_{16}\) and \(G_{48}\) charts, and
\(k=\mathbb F_4\) for the \(Q_8\) and \(G_{24}\) charts. The symbol \(j\)
depends on the chart: \(j=v_1^{12}D^{-3}\) for \(G_{24}\) and \(G_{48}\), and
\(j=v_1^4D^{-1}\) otherwise.

The arXiv source also contains an older blue/red-dot palette. The Studio may
retain those colors for compatible imports, but color is treated as a module
pattern. It must not be inferred from whether a class supports or receives a
differential.

## Published multiplication lines

The published version of [DKLLW24], Table 10 uses:

| Line | Meaning |
| --- | --- |
| vertical | multiplication by \(2\) |
| slope \(1\) | multiplication by \(h_1\) |
| slope \(1/3\) | multiplication by \(h_2\) |
| dashed (2BSS only) | hidden extension |

A vertical line may join two marks in the same spectral-sequence bidegree.
The small visual offset separates the marks; it is not a second filtration
coordinate. In particular, the upper mark is twice the lower generator.

Multiplication edges and differentials are separate record types. A slope
alone may provide a suggested display style, but the Studio stores the
multiplier explicitly and does not promote an arbitrary line to a theorem.

## Page and differential semantics

A class record stores its first page of appearance. A differential \(d_r\)
belongs to page \(E_r\), and its homology is \(E_{r+1}\). Thus the \(d_3\)
arrows are drawn on \(E_3\) and their images are quotiented out on \(E_4\),
not on \(E_3\). When \(d_2=0\), the additive input \(E_2=E_3\) does not
change this indexing convention.

Class glyph/module-pattern metadata is independent of class fate. Fate records
whether a class is live, supports a differential, receives a differential, or
survives; it controls page visibility and annotations but not the Table 11
glyph.

## Period cycles

A user may select a class live on \(E_r\) and record it as a period cycle on
that page. The display expands its translates virtually within the visible
viewport. It does not persist one class record per translated dot.

The same cycle is available as a period on earlier pages \(E_s\), \(s<r\).
It may continue to \(E_{r+1}\) only when it neither supports nor receives a
nonzero \(d_r\). This is a page-eligibility rule; it does not independently
prove that multiplication is an isomorphism or certify a claimed differential.

## Differential-table contract

Tables 8 and 9, not the figures, are the primary differential ledger: 24
integer-graded rows and 22 single-sign rows. Their printed columns are
\((s,f),x,r,d_r(x),\mathrm{Proof}\). The Studio keeps these 46 original rows
separate from checked Leibniz and hidden-extension descendants. Each original
row retains its table ordinal, equation, bidegree, page and complete Proof
field, including the proof-method parentheticals. Table 8 row 3's printed
\(8\nu=\eta^3\) is retained only as source text, not an algebra rewrite rule.

The displayed **Derived repeat (stem)** is application metadata, not a
printed column in those tables. It describes repetition of the nonzero map
pattern; a short repeat need not assert an invertible permanent multiplier
or equality of unit coefficients. In particular, \(d_7(4D)\) and
\(d_7(2D^2)\) have 32-stem repeats, whereas \(d_7(D^4)\) has a 64-stem
repeat. Giving the latter a 32-stem repeat would incorrectly kill the unit
and \(D^8\).

This does not mean the user's local tables have no Period column.
`REU projects/table_Q8.tex:355,422,488` explicitly includes it in the
2-sigma, 3-sigma and mixed-grading summaries. These are distinct from the
published Tables 8/9. The older 2-sigma summary is captioned "Need
Correction!"; the mixed summary also records specific coefficient choices
and higher-page candidates. Their Period is a stem displacement of the
stated family, not a certificate that the bare D-power survives. Related
source records are displayed with the formal claims for review; neither
those coefficients nor those candidates override `formal_notes.tex`.

The permanent \(D^8\) translation is bidirectional. The HFPSS \(g=kD^3\)
families use nonnegative powers of \(g\). An inverse-\(g\) Tate comparison
requires a separate positive-filtration comparison certificate; it does not
make \(g\) globally invertible in HFPSS. These rules transport the arrows as
well as their source and target coefficient submodules. Reaching a vanishing
line must follow from those maps, never from a filtration-height cutoff.

Review status is not a drawing omission: provisional formulas remain visible
but cannot delete canonical classes. In particular, `formal_notes.tex` remains
the primary notes source, while its mixed-grading TBD formulas corresponding
to historical Propositions 6.5 and 6.6 also retain the explicit rejection in
`Note/record/note.tex:1409-1413`. The latter factorization has a checkable unit
mismatch: for \(B=(x+y)u\), \(Bx^2=By^2=x^3u\) implies
\(B(x^2+\zeta^2y^2)=\zeta x^3u\). An unresolved premise unit cannot be
silently replaced by 1. These source and coefficient caveats are displayed in
the Review proposition list and carried through atlas transports.

The six derived `3sigma_i` d9 rows in the D2 and D6 blocks have two separately
recorded nonzero residue-field parameters. Within each block the P, Q and C
rows share a parameter, conditionally on the notes' P+Q normalization. The
isolated six-row calculation does not identify the two block parameters.
These are review rows modulo D8, not additional printed table rows and not a
claim that D4 survives d7.

Four further review d9 families, on BD4, BD8, CD3 and CD7, carry independent
Euler-product/detection certificates referencing Table 8 rows 12--13 and
20--21. Their existence is not inferred by deleting everything above a
desired vanishing line. When the full formal d23 families FN-3I-010 and the
stated multiplicative bases are also admitted, Leibniz compatibility forces
all six named d9 parameters to agree. That conditional constraint is checked
before forming the E10 quotient; a d19 row with the same fact id does not
substitute for the required d23 premise. The displayed integer maps fix this
common value to 1. Assigning a common zeta or zeta-squared only in the twisted
sector now also blocks the quotient: the Studio has not implemented a global
rescaling of all integer maps and cross-graded products. No test admission is
persisted.

The FN-3I-010 d23 proof has a concrete Euler-preimage gap. In the same
displayed normalization, `formal_notes.tex:770-774` gives
\(a_{\sigma_i}(xh_1^2D^4u_{2\sigma_i})
=x^2h_1^2D^4u_{3\sigma_i}=2v_1^2kD^4u_{3\sigma_i}=z\),
whereas lines 833--848 exclude this very candidate by its E2 product.
The candidate lies at (33,3), with image (32,4). Admitting the current
two-sigma formulas only in a test copy leaves its I13 direction present
on E24. FN-2I-020 instead kills I13 at (1,3); its D8 repeat cannot be
replaced by a D4 repeat to eliminate this candidate. Thus the conditional
three-sigma convergence test is not an independent proof of FN-3I-010.
An additional lifting obstruction or a corrected argument is required;
the d23 and d19 formulas are retained, not declared false. The separate
Euler permanent-cycle claim FN-3I-010-pc has its own restriction proof
and is not rejected by this issue. This source conflict is visible in Review
and travels with every three-sigma atlas image.

The audit now checks cross-grading naturality, not just convergence of each
separate quotient. The other proposed preimage, x^2 h2 D4 u_2sigma, also
maps to z by the actual group-cohomology hidden h2 extension in DKLLW
`main.tex:1094-1123`. In the conditional runtime, the possible d23 target of
either preimage at (32,26) is already a d5 **source** killed by FN-2I-006.
Thus a nonzero d23(z) contradicts d23(a A)=a d23(A)=0 under those premises.
An earlier problem appears at g^3: g^3 A is an FN-2I-018 d13 boundary, but
the present three-sigma hypotheses still retain g^3 z on E14. After the
permanent D^-8 shift this is Z=(28,16). Finite incoming-source enumeration,
conditional on the separate Ck permanence and early multiplication premises,
retains the d11 candidate (29,5)->(28,16). This neither admits that candidate
nor proves the historical Option 2's whole 32-period family or its unit.
The tests preserve all original source rows and unassigned coefficients;
a separately consistent page quotient is not a proof of naturality.

There is a separate subgroup error in the Euler permanent-cycle proof
`formal_notes.tex:799-809`. DKLLW defines `ker(sigma_i)=C4<i>`
(`main.tex:515-520`), hence restriction to that subgroup sends `3sigma_i`
to three trivial real lines and sends its Euler class to zero, not to the
nontrivial sign Euler class `a_3sigma`. Switching to `C4<j>` or `C4<k>`
could repair that part of the argument, but the cited detector and its
filtration must be verified for the chosen subgroup. The code records this
as `euler-restriction-uses-kernel-subgroup` on FN-3I-010-pc, separately
from the d23 preimage conflict, without rejecting the printed permanence
statement or silently changing the source's subgroup. The cofiber sequence
in the d23 proof really does use the kernel `C4<i>`; that role is distinct.

In the mixed sector, put \(A=(x^2+y^2)u\) and
\(T=(x+y)h_1^2u=Ah_2\). FN-MIX-002 and its positive-filtration
pullback FN-MIX-003 share one unresolved coefficient \(c\in\mathbb F_4^\times\).
Leibniz gives \(d_5(AD)=cTkD\), but
\(d_5(AD^2)=(c+1)TkD^2\). The latter is an explicitly linked review
family, not a new printed row or an independent arbitrary coefficient.
Its coefficient is zero when \(c=1\); in that branch there is no arrow
and no class death from this map. Frobenius is applied to the whole
expression, \((c+1)^2\), using the same source-field assignment in every
atlas image. Unknown coefficients never default to the zero branch.

The red d9 premise of FN-MIX-002 is the omega image of FN-2I-010,
not FN-2I-016. It forces a nonzero earlier map but does not set \(c=1\).
The red d5 premise of FN-MIX-004 comes from FN-2I-004; its source and
target have equal omega scaling. These transport certificates and the
original `[TBD]` warnings remain visible together. Tests of all nonzero
\((c,b)\) in the mixed d5 blocks do not determine the coefficients; in
particular, killing \(P+bQ\) does not kill both basis vectors.

The production FN-MIX-005 records now carry the shared parameter
`mixed_d5_B`. The odd-D row uses `target_component: S22H`: only Q's
coefficient changes, giving P+bQ rather than b(P+Q). The even-D row uses
the same parameter on its whole target bQ. The printed unit-1 equations,
matrix, and target vectors remain source records; resolved endpoint vectors
are evaluated without mutating them. In a psi image the effective targets
are P+b²Q and b²Q in the transported basis. When b is unassigned, an
explicitly admitted candidate blocks the E6 quotient instead of assuming 1.
Even the legacy fate timeline does not label the printed P+Q as hit when
the effective boundary is P+bQ for b other than 1.

Two additional review zero-map records close the mixed d5 block under
explicit premises: P-even follows from FN-MIX-004 and P h2=x³D u;
Q-zero follows from nonzero b, d5²=0, and injectivity of multiplication
by kD² on Q's candidate target line. The latter is not the three-sigma
empty-target proof for C: mixed C does not survive d3. Merely obtaining a
consistent numerical quotient does not admit these claims or select b.

Two mixed d9 Euler-image candidates are conditional review rows.
With B=(x+y)u, P=B h2 and T=B h1², the omega image of
FN-2I-016 (`formal_notes.tex:520-526`), multiplied by permanent a_sigma_i,
gives d9(PD^m)=gamma_m T k²D^(m+1), m=2,6. The anchors are
(18,2)->(17,11) and (50,2)->(49,11). Their targets are nonzero on E9 only
in the c=1 branch: otherwise d5(AkD³)=(c+1)Tk²D³, and its D4-pattern
counterpart, already make them boundaries on E6. An Euler image that is zero
in the page quotient is not a nonzero differential and cannot kill its source.
The finite target-survival audit uses the empty d3/d7 source bidegrees and
the two d5 source directions (A and the previously killed positive-j
direction); it is not a visual inference from an empty patch of the chart.
Each candidate has a separate unresolved unit gamma_m=zeta² lambda_m in
the named target basis and a safe D8 repeat of 64, plus forward g repeats.
The paired 32-stem pattern does not by itself identify the two units or
make D4 an E9 cycle. This is a pending conditional consequence, not an
additional published table row or an admission of the cited premises.
The shared source-field predicate is stored as `coefficient_condition`.
Unknown c blocks an admitted quotient; c=1 also requires the row's gamma;
c=zeta or zeta² gives a certified zero image without assigning gamma.
The zero branch draws no arrow and creates no source or target death.
Atlas transport preserves the predicate and conjugates only the effective
unit. Neither the source equations nor immutable fate history are rewritten.

The same two blocks now include the Q direction with coefficient gamma_m/b,
not a separately selected unit. The d5 boundary g(P+bQ)D^m and the finite
target-line g-injection certificate give this ratio when c=1; otherwise the
target line is already zero. `inverse_parameter_id` names the shared b, and
the engine divides before Frobenius, so psi(gamma/b)=psi(gamma)/psi(b).
The positive-j Q ideal is a separate zero-d9 record. Its certificate is the
negative-source Tate differential
d3(g^-1 D^(m+2) j^(n-1) U h1³)=j^n QD^m (n>=1), from filtration -1 to 2.
By DKLLW Lemma 2.6 and its Tate method this is an HFPSS cycle, not an HFPSS
boundary to delete. Consequently the low-filtration c=1 kernel retains
P+bQ and jQ even though P and Q individually support nonzero d9. All these
records retain review status and explicit premises.

The next old mixed rows still have a specific source gap, not permission to
force convergence. `Note/record/note.tex:762-795` marks the first proposed
d9(B h1 D) proof "wrong proof"; its replacement requires checking the
Euler product through the 3sigma_k sector and the exact norm/Thom basis.
Its proposed d11(A h1 D²) depends on that argument. Moreover, applying
omega and a_sigma_i to FN-2I-021 gives a conditional E22 cutoff for
P k7 D5 at (14,30); the d5 image P+bQ then gives the same cutoff for Q
when b is nonzero. That is not yet a unique-source proof of the old table's
d19, and it does not distinguish c=zeta from c=zeta². These implications
must not be implemented as filtration clipping or new accepted deaths.

A corrected route for the next mixed d9 can be identified without the
old diagram's degree error. Write \(B=(x+y)u\),
\(R=(x^2+y^2)h_1u=x^2h_1u\), and let \(\nu_7,\nu_3\) denote
the source three-sigma parameters `three_sigma_d9_CD7/CD3`. Conditional
on those source rows and the permanent Tate period \(\Phi\) declared in
`formal_notes.tex:875` and `record/note.tex:776-779`, the corrected equations are
\[
d_9(Bh_1D)=\nu_7Rk^2D^2,\qquad
d_9(Bh_1D^5)=\nu_3Rk^2D^6.
\]
They have anchors (8,2)->(7,11) and (40,2)->(39,11), separately modulo
D8. Apply omega squared to the three-sigma C D7 and C D3 rows, then
Phi inverse (stem +16), then a_sigma_j; the first row also uses D^-8.
The finite-line identities a_sigma_j C_k=zeta B_i h1 and
a_sigma_j B_k h1=R make the scalar cancel. A common filtration-zero
Thom-normalization unit cancels on both finite j-annihilated lines as well.
These are installed as the review rows `DER-MIX-PHI-D9-D1/D5`, with shared
cross-workspace `source_parameter` references, not independent mixed assignments.
They require an admitted source differential and an explicitly resolved source
unit; the transported occurrence applies Frobenius only after that resolution.
Missing or conflicting source information blocks the quotient without deleting
endpoints. The source formula, its proof status, and admission remain distinct.

The same corrected transport also supplies two **conditional** even blocks:
\[
d_9(Bh_1)=\lambda_6Rk^2D,\qquad
d_9(Bh_1D^4)=\lambda_2Rk^2D^5.
\]
Their anchors are (0,2)->(-1,11) and (32,2)->(31,11), with period 64,
and their source parameters are `three_sigma_d9_D6/D2`, linked to the
three-sigma C D6/C D2 rows. These use the separate Ck Euler permanence
premise FN-3I-010-pc and Table 8 rows 6--7, **not** the disputed final
FN-3I-010 d19/d23 proof. The subgroup restriction issue on that permanence
premise remains explicit. All four Phi rows stay review; no coefficient or
admission is filled in by the transport. Tests cover c=1,zeta,zeta-squared,
unknown/invalid source assignments and all six mixed atlas images. The two
new rows kill the prospective high incoming d19 directions only when their
premises are explicitly admitted. A possible outgoing d21 still prevents an
unconditional mixed d11 forcing argument unless the separate, disputed
FN-MIX-006 hypotheses in both D8 blocks are established.

The source's earlier d3 target is empty and its d5 target is already the
d3 image of U kD^m. Its d7-cycle condition follows from the naturality
construction. The target's incoming d3 slot is S00 (v1^4 k^2 D^m u), but
that map is zero: the primitive terms cancel and the extra Thom term
x^2 h1 v1^4 is zero. Its incoming d5 slot is empty. The only incoming d7
slot is the 4-torsion S40 (U kD^m): its odd layer supports d3 and its
remaining 2U layer is hit by d3(CD^m), so this entire slot is zero on E4.
Thus these are not zero Euler images depending on the unresolved c or b.
This does not repair the old d11 proof: its (19,23)->(18,34) equation
reduces under g and D8 to the RD6 block, not the printed RD2 block.
An independent 32-pattern proof or separate forcing in both 64-blocks
is still required. Nor is the literal old k7D5->k5D5 identification a
valid Phi map: it shifts (+8,-8), not (-16,0).

`conclusion.coefficient_parameter` names a stable source-field parameter;
`settings.coefficient_assignments` may explicitly assign its nonzero value.
The psi image keeps that identity and assignment and changes only its
Frobenius power. Unknown or inconsistent assignments never default to 1.
If such a row is admitted without resolving its parameter, computation stops
at that page's quotient with an explicit conflict. Later displayed classes
are provisional and cannot be used as known sources of further maps.

## Source locators

- [DKLLW24], published PDF, Tables 10 and 11 and Remarks 6.1--6.2.
- [DKLLW24], published PDF, Table 8 (PDF page 39) and Table 9 (PDF page 49),
  with the proofs referenced in each row and their stated Leibniz closures.
- Local source archive: `arXiv-2209.01830v3/main.tex`.

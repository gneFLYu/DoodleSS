# DKLLW24 coefficient and argument audit

## Verdict

Qualified yes. DKLLW24 keeps the relevant coefficient layers separate:

\[
\mathbb F_4
\quad\longrightarrow\quad
W(\mathbb F_4)
\quad\longrightarrow\quad
W(\mathbb F_4)[[u_1]][u^{\pm1}].
\]

Its group-cohomology and HFPSS differential patterns therefore do respect the
\(\mathbb F_4\) residue coefficients and their Witt lifts. The qualification is
that several restriction and degree arguments identify a class only up to a
unit in \(W(\mathbb F_4)\). Those arguments determine non-vanishing, the
one-dimensional target line, and the differential pattern, but not a canonical
nonzero scalar without an additional normalization.

This audit covers the coefficient-sensitive backbone of the paper. It is not a
formal line-by-line verification of every proposition.

## Source-backed findings

| Claim | Source | Audit result |
| --- | --- | --- |
| \(\pi_*E_2=W(\mathbb F_4)[[u_1]][u^{\pm1}]\) | `main.tex` 631–649 | The ambient theory is 2-adic/Witt, not an \(\mathbb F_4\)-algebra alone. |
| The 2-BSS begins with \(H^*(Q_8,\mathbb F_4[v_1,u^{-1}])[D^{-1}]\) and reconstructs the Witt-valued cohomology | `main.tex` 887–892, 965–1040 | The paper explicitly retains the \(2\), \(4\), and \(8\) extensions that would disappear after reduction to characteristic two. |
| The \(1,D,D^2\) decomposition is an eigenspace decomposition | `main.tex` 898–919 | This genuinely uses that \(\mathbb F_4\) contains \(1,\zeta,\zeta^2\); it is not an unchanged \(\mathbb F_2\) argument. |
| Galois does not change the integer-graded differential pattern after Witt base change | `main.tex` 619–629 | Correct within the displayed base-change lemma and its hypothesis \(F/F_0\cong\operatorname{Gal}\). It is a semilinear/base-change comparison, not a blanket mixed-\(RO(Q_8)\) symmetry. |
| Restrictions are used up to units | `main.tex` 1573–1579 | Exact unit coefficients are intentionally not fixed. Downstream software must preserve this ambiguity. |
| Chart dots for \(Q_8\) and \(G_{24}\) use \(k=\mathbb F_4\) | `main.tex` 2500–2518 | Scalar multiples in a one-dimensional \(\mathbb F_4\)-line should not be materialized as distinct chart classes unless a normalization is part of the record. |

There is a typographical omission in source line 918 (the displayed list of
eigenvalues is truncated), but lines 915–918 make the intended three
eigenvalues \(1,\zeta,\zeta^2\) unambiguous.

## Topological scope guard

DKLLW24 distinguishes

\[
Q_8,G_{24}\subset \mathbb S_2
\qquad\text{from}\qquad
SD_{16},G_{48}\subset \mathbb G_2.
\]

The cited Galois lemma is written for the integer grading \(\pi_*\). The paper
also computes the single \((*-\sigma_i)\) grading and explains why this case is
handled with \(Q_8\) and \(SD_{16}\) (`main.tex` 1935–1936). It does not construct
a pagewise Galois reflection between arbitrary mixed gradings such as

\[
2\sigma_i+\sigma_j
\quad\text{and}\quad
\sigma_i+2\sigma_j.
\]

Consequently, the project must not promote that mixed-grading identification
from an algebraic \(\operatorname{Gal}(\mathbb F_4/\mathbb F_2)\) formula alone.

## Danus-style fact DAG in Studio

The existing typed logic graph now applies the following admission rule:

1. A proposition must have status `established`, `verified`, or
   `source-verified`.
2. Every proposition named in `premise_ids` must itself be admitted.
3. Proposition dependencies must be acyclic.
4. A hypothesis of the form `coefficient-context:<id>` creates a visible
   `requires-coefficients` edge from the coefficient context to the
   proposition.
5. Claims that fail admission remain visible in the review queue and cannot
   silently support an admitted fact.

The installed DKLLW24 audit chain culminates in
`prop_dkllw_f4_audit_conclusion`. Its incoming dependencies expose the residue
field, Witt lift, \(C_3\)-eigenspace, unit-normalization, and topological-scope
checks separately.

This mirrors the useful part of Danus's fact graph: verified facts, explicit
logical dependencies, dependency depth, and a separate unverified memory
queue. Studio does not claim to provide Danus's automated mathematical
verifier; admission is an explicit review status backed by recorded checks and
source locators.

# Record of classes, relations, and differentials

## 0. Scope and source policy

This is the proposition-level record extracted from the current local Overleaf source
REU Projects/Note/formal_notes.tex. It records what that source states; it does not promote every
displayed proposition to an admitted theorem.

- Authoritative text: formal_notes.tex, modified 2026-08-17 22:59 (local time).
- Rendered audit copy: formal_notes.pdf, compiled 2026-08-17 17:11. The PDF is older than the TeX,
  so line locators and formula text below follow the TeX if they could diverge.
- Scope: Sections 3 and 4.1--4.5. Section 4.6 (Summary tables) is empty.
- Red annotations, missing references, contradictory proof text, and [TBD] premises are retained as
  review blockers.
- The source does not give a complete additive presentation of every \(E_2\)-cell. This record
  declares its explicit bases and all class occurrences used by its claims, but does not invent
  missing cyclic summands or exponents.

## 1. Record schema

### 1.1 Class occurrence

Each occurrence has sector, page_first_seen, displayed Adams bidegree (stem, filtration), exact
algebraic name, coefficient_context, role, source_locator, and status. An explicit
\(\mathbb F_4\)-coefficient such as \(\zeta\) is never discarded. Multiplication adds displayed
bidegrees. A name denotes an occurrence in one sector and period block; the same printed monomial
in another sector is not automatically the same object.

### 1.2 Differential

Each differential record has page \(r\), source and target occurrences, a per-generator formula or
a target-row-by-source-column matrix, premises and consequences, status, locator, and the rule

\[
(s_{\rm target},f_{\rm target})-(s_{\rm source},f_{\rm source})=(-1,r).
\]

An explicit zero formula means its source is an \(r\)-cycle, not a nonzero arrow. A missing
differential is unknown, not zero.

### 1.3 Two status axes

The source status answers “what does formal_notes itself say?”; the admission status answers
“may this fact determine a canonical fate?”. They must not be collapsed into one field. The
period-first machine ledger uses the following admission statuses.

| Admission status | Meaning |
|---|---|
| admitted | Statement, coefficient convention, and premise chain are reviewed. |
| admitted-pattern | The nonzero family and its period pattern are admitted; this may determine death even if a display normalization remains separate. |
| verified-pattern | Non-vanishing and the family are verified, while an exact \(\mathbb F_4^\times\) or \(W(\mathbb F_4)^\times\) unit remains under review. It certifies fate, but receives a unit-review badge. |
| source-proved | The active TeX supplies an argument, but Danus review has not admitted the node. It appears only in Researching mode. |
| review | A premise, coefficient, comparison certificate, or completeness check remains open. |
| rejected | A contradiction or later correction excludes the node from canonical reasoning. |

The older labels asserted-proved, needs-review, blocked, disputed, and rejected-commented below
are retained as source-audit annotations. Their current admission values are centralized in the
machine ledger rather than inferred from typography.

## 2. Global grading, bases, and period constraints

### 2.1 Reduction of \(RO(Q_8)\)-gradings

FN-GLOBAL-001 (structural, needs-review; formal_notes.tex:241-245) records

\[
RO(Q_8)/\!\sim\;\cong
\mathbb Z/64\{1\}\oplus\mathbb Z/4\{1-\sigma_i\}
\oplus\mathbb Z/4\{1-\sigma_j\}\oplus\mathbb Z/2\{12-\mathbb H\}.
\]

Orientable cycles are said to identify some \(E_2\)-pages and reduce the calculation to nine cases
up to symmetry. This outline cites DKLLW24 but is not proved here.

### 2.2 Display convention and declared rank-two cell

In the \((*-2\sigma_i)\)-sector, displayed \((s,f)\) denotes
\(E_r^{f,s+f+2-2\sigma_i}\), and figures omit \(u_{2\sigma_i}\). At
\((-2+8m,2+4n)\), the ordered basis is

\[
e_1=k^nD^m\{x^2+y^2\}u_{2\sigma_i},\qquad
e_2=k^nD^my^2u_{2\sigma_i}=k^nD^mD^{-1}h_2^2u_{2\sigma_i}.
\]

It replaces, rather than identifies termwise with, the integer-page basis
\((k^nD^mx^2,k^nD^my^2)\) (formal_notes.tex:277-280). Same-coordinate legacy dots remain separate
unless an explicit declaration joins them.

### 2.3 Period language

- “8-, 16-, or 32-periodic” below usually means a repeated differential pattern, not an invertible
  HFPSS class.
- FN-3I-010 distinguishes its \(D^4\)-shifted 32-pattern from the genuine permanent
  \(D^8\)-translate (formal_notes.tex:799-845).
- Cancellation by \(g=kD^3\) is a TateSS argument and needs a comparison certificate before it is
  pulled back to HFPSS. This applies at lines 909-915 and 1000-1006.

The following correction was adopted as project policy on 2026-09-10. A short drawn tower is not
evidence that a bo-pattern is confined to low filtration. In the DKLLW chart convention, a line of
slope one is multiplication by \(h_1\); many such towers are drawn short because their classes
support or receive early differentials. Their algebraic type is instead visible in the colored
glyphs: with

\[
j=v_1^4D^{-1},
\]

blue and red glyphs denote modules such as \(\mathbb F_4[\![j]\!]\) and
\(j\mathbb F_4[\![j]\!]\) (with the appropriate Witt or torsion refinement when declared), not a
finite list of dots. DKLLW's displayed \(d_3\)-families already contain \(g^s\) for \(s\ge0\).
Therefore bo families also participate in the forward \(g=kD^3\) repetition. The phrase
“v1-local classes in low filtration” in the chart caption is treated as a lower-bound/invertibility
warning, not as a definition of bo-pattern and not as a reason to remove bo classes from the
forward \(g\)-period family.

Accordingly, the record distinguishes algebraic module kind from periodic position:

- `finite-2-primary`: a finite residue/torsion cell on which killed rank is computed by finite
  linear algebra;
- `witt-2-adic`: a \(W(\mathbb F_4)\)-type cell, which is not silently reduced modulo 2;
- `j-adic-formal-power-series`: an \(\mathbb F_4[\![j]\!]\)-, \(j\mathbb F_4[\![j]\!]\)-, or
  declared Witt/torsion analogue, stored separately as one named family with its fixed
  differential and permanent-cycle templates.

Module kind is never inferred from filtration height or the number of drawn dots.

### 2.4 Stable period-class identifiers

There are three identifiers because “same HFPSS object”, “same forward HFPSS period family”, and
“same class after Tate comparison” have different hypotheses.

1. The unconditional HFPSS identifier has the form

   \[
   \mathtt{pc.<sector>.d8.<shape>-c<coefficient>-k<k\_power>-d<D\_power\bmod 8>}.
   \]

   It quotients only by multiplication by \(D^8\). Thus
   \(h_1^2k^2D^3u_{2\sigma_i}\) and its \(D^8\)-translate have the same id
   pc.2i.d8.h1sq-cone-k2-d3, while the \(D^4\)-sibling has a different id.

2. Every applicable HFPSS family, including a bo family, receives a semiperiod-family id

   \[
   \mathtt{pc.<sector>.gd8semi.<shape>-c<coefficient>-r\rho},\qquad
   \rho\equiv \deg_D-3\deg_k\pmod 8.
   \]

   Its concrete occurrences carry a translation \((s,q)\in\mathbb N\times\mathbb Z\), meaning
   multiplication by \(g^sD^{8q}\). Sharing this id means “same periodic family”; it does not
   assert that multiplication by \(g\) is invertible in HFPSS. This is the half of the
   \(g,D^8\) biperiodicity that applies uniformly to bo and non-bo families.

3. A positive-filtration occurrence may additionally receive the conditional Tate-comparison id

   \[
   \mathtt{pc.<sector>.gd8.<shape>-c<coefficient>-r\rho},\qquad
   \rho\equiv \deg_D-3\deg_k\pmod 8.
   \]

   For example, \(h_1^2k^2D^3u\) and \(h_1^2k^6D^7u\) both have
   \(\rho=5\), so—with the positive-filtration HFPSS-to-TateSS certificate—they share
   pc.2i.gd8.h1sq-cone-r5. In this certified region the \(g\)-coordinate may be translated in
   both directions. This id is unavailable at uncertified filtration-zero endpoints or under an
   uncertified mixed-sector transport, but bo membership is not an exclusion.

The sector, coefficient/torsion tag, and a high-rank vector's coordinates are part of the id.
Consequently, \(A\), \(B\), and \(A+B\) have different shape ids, and the two mixed
\(C_3\)-orbit pages remain distinct.

The complete period-first index is the review-only JSON file
backend/data/review/formal_notes_periodic_fate_ledger.v1.json. Its 37 fact-family records are
keyed by the existing FN-* ids; each source and target is referenced through a period-class id.
The prose tables below remain the provenance view, while the JSON is the grouping and
machine-rendering view.

## 3. Extension and relation ledger

| ID | Exact relation / extension | Consequence | Status and locator |
|---|---|---|---|
| REL-2I-001 | \(a_{2\sigma_i}=\{x^2+y^2\}u_{2\sigma_i}=(\{x+y\}u_{\sigma_i})^2\). | Permanent-cycle premise for FN-2I-001 and FN-2I-003. | asserted-proved; lines 299-304, 344-351. |
| REL-2I-002 | \(y^2=h_2^2D^{-1}\), and \(Dxh_1^2=h_2^3\) where used. | Alternate target names and rank-two basis. | asserted-proved as \(E_2\)-relations used by the source; lines 280, 491-493. |
| REL-2I-003 | Multiplication by \(h_1\) from the FN-2I-009 target to FN-2I-010 is called a hidden \(h_1\)-extension. | Intended to imply FN-2I-010. | blocked with its premise; lines 472-482. |
| REL-2I-004 | The target \(h_1\)-extension of FN-2I-011 forces FN-2I-012. | Links the same 32-period block. | blocked; lines 487-499. |
| REL-3I-001 | \(x^2\{h_1+xv_1\}u_{\sigma_i}=\{x^2+y^2\}h_1u_{\sigma_i}\). | First cancellation in the zero \(d_3\) of FN-3I-001. | asserted-proved; lines 693-698. |
| REL-3I-002 | \(h_1\{x^2+y^2\}h_1u_{\sigma_i}=2v_1^2ku_{\sigma_i}\). | Hidden \(h_1\)-extension in that cancellation. | asserted-proved; lines 693-698. |
| REL-3I-003 | \(h_2\{x+y\}u_{\sigma_i}=\{yh_2+xh_1v_1\}u_{\sigma_i}\). | Pulls a \(d_5\) through the Euler class in FN-3I-003. | needs-review because the supporting label is missing; lines 730-742. |
| REL-3I-004 | \(x^2h_1^2u_{3\sigma_i}=2v_1^2ku_{3\sigma_i}\). | Identifies the target in FN-3I-007. | blocked with FN-3I-007; lines 769-775. |
| REL-MIX-001 | \(a_{\sigma_i}=\{x+y\}u_{\sigma_i}\) is used as a permanent Euler class. | Common mixed-sector premise. | imported DKLLW24 premise; lines 894, 923-934, 962-972. |

## 4. The \((*-2\sigma_i)\)-sector

| ID | Kind and exact datum | Degree / period | Premises, consequences, status, locator |
|---|---|---|---|
| FN-2I-001 | differential: \(d_3(u_{2\sigma_i})=x^2h_1u_{2\sigma_i}\). | \((0,0)\to(-1,3)\). | Restriction and REL-2I-001 rule out survival to \(E_5\). asserted-proved; lines 283-305. |
| FN-2I-002 | \(d_3(v_1^6u)=h_1^3Du\), \(d_3(h_1v_1^6u)=h_1^4v_1^2u=h_1^4Du\). | \((12,0)\to(11,3)\), \((13,1)\to(12,4)\); 8-pattern. | DKLLW24 Prop. 4.10, Leibniz, \(h_1\)-extension. asserted-proved; lines 308-320. |
| FN-2I-003 | \(d_5(\{x^2+y^2\}Du)=k\{x^2+y^2\}h_2Du\); \(d_5(\{x^2+y^2\}D^2u)=0\). | \((6,2)\to(5,7)\); \((14,2)\) is a 5-cycle; 16-pattern. | REL-2I-001 and integer-page \(d_5(D),d_5(D^2)\). asserted-proved; lines 334-353. |
| FN-2I-004 | \(d_5(h_2Du)=kh_2^2Du\). | \((11,1)\to(10,6)\); 16-pattern. | \(C_4\langle i\rangle\)-restriction; red note says no \(\zeta\) without completed coefficient proof. needs-review; lines 357-379. |
| FN-2I-005 | \(d_5(2Du)=2kh_2Du\); \(d_5(2D^2u)=0\). | \((8,0)\to(7,5)\); \((16,0)\) is a 5-cycle; 16-pattern. | Transfer proves first; red coefficient question and no proof of zero formula. needs-review; lines 382-399. |
| FN-2I-006 | \(d_5(xh_1u)=kh_1^3u\). | \((0,2)\to(-1,7)\); 8-pattern. | Proof asks whether transfer of a permanent cycle is permanent. needs-review; lines 401-420. |
| FN-2I-007 | \(\operatorname{Res}^{Q_8}_{C_4\langle j\rangle}(\{x^2+y^2\}u)=a_{2\sigma}=\operatorname{Res}^{Q_8}_{C_4}(x^2)u_{2\sigma}\). | Restriction, not differential. | Input for FN-2I-009; no proof, and “Moreover” is flagged. needs-review; lines 424-433. |
| FN-2I-008 | \(k\{x^2+y^2\}D^nu\notin\operatorname{im}(\operatorname{Tr})\). | All \(n\) claimed. | Proof says \(x^3D^nu\) survives to \(E_\infty\), then says \(x^3D^4u\) supports \(d_{13}\). disputed; lines 435-446. |
| FN-2I-009 | \(d_{11}(\{x^2+y^2\}D^2u)=k^3h_1D^3u\), \(d_{11}(\{x^2+y^2\}D^6u)=k^3h_1D^7u\). | \((14,2)\to(13,13)\), \((46,2)\to(45,13)\); 32-pattern. | Depends on FN-2I-007; red coefficient note. blocked; lines 450-470. |
| FN-2I-010 | \(d_9(2kh_2D^2u)=k^3h_1^2D^3u\), \(d_9(2kh_2D^6u)=k^3h_1^2D^7u\); equivalently \(d_9(2h_2D^3u)=k^2h_1^2D^4u\). | \((15,5)\to(14,14)\), \((47,5)\to(46,14)\), \((27,1)\to(26,10)\); 32-pattern. | REL-2I-003 from FN-2I-009; red coefficient note. blocked; lines 472-482. |
| FN-2I-011 | \(d_9(h_1^2D^3u)=k^2D^3h_2^3u\). | \((26,2)\to(25,11)\); 32-pattern. | Uses FN-2I-009 and an integer-page formula; implies FN-2I-012. blocked; lines 487-494. |
| FN-2I-012 | \(d_7(h_1D^3u)=2k^2D^4u\). | \((25,1)\to(24,8)\); 32-pattern. | Forced by REL-2I-004 from FN-2I-011. blocked; lines 496-499. |
| FN-2I-013 | \(d_7(h_1D^4u)=4k^2D^5u\). | \((33,1)\to(32,8)\); 32-pattern. | Contradiction using imported \(d_{23}\); red \(\zeta\)-note. needs-review; lines 501-506. |
| FN-2I-014 | \(d_7(h_1Du)=2k^2D^2u\). | \((9,1)\to(8,8)\); 32-pattern. | Proof writes a shifted source and uses period cancellation; red coefficient note. needs-review; lines 508-516. |
| FN-2I-015 | FN-2I-012 and FN-2I-014 combine into a 16-periodic \(d_7\) pattern. | Pattern only. | One premise blocked and one needs review. blocked; lines 517-519. |
| FN-2I-016 | \(d_9(h_2D^2u)=h_1^2k^2D^3u\). | \((19,1)\to(18,10)\); 32-pattern. | Unique-source argument uses FN-2I-009; red coefficient note. blocked; lines 520-526. |
| FN-2I-017 | \(d_9(2h_2Du)=k^2h_1^2D^2u\). | \((11,1)\to(10,10)\); 32-pattern. | Unique source plus \(kD^3,D^8\) shifts; depends generically on prior families. needs-review; lines 529-536. |
| FN-2I-018 | \(d_{13}(\{x^2+y^2\}D^4u)=h_2^3k^3D^4u\). | \((30,2)\to(29,15)\). | DKLLW24 \((*-\sigma_i)\)-formula and REL-2I-002. asserted-proved; lines 540-555. |
| FN-2I-019 | \(d_{21}(h_2kD^7u)=\{x^2+y^2\}k^6D^{10}u\). | \((55,5)\to(54,26)\). | Vanishing line and unique source; implies FN-2I-020. asserted-proved; lines 558-563. |
| FN-2I-020 | \(d_{21}(h_2^3D^{-1}u)=4k^6D^3u\). | \((1,3)\to(0,24)\). | Shifted unique-source argument using FN-2I-019. asserted-proved; lines 565-570. |
| FN-2I-021 | \(d_{21}(4k^2D^3u)=h_2k^7D^5u\). | \((16,8)\to(15,29)\). | Vanishing line and unique source. asserted-proved; lines 572-577. |

The “Moreover” clause of FN-2I-007 asserts \(d_{13}\)'s on \(2h_2D^3u\) and \(2h_2D^7u\)
(lines 431-433). Because the source says these do not seem correct, both are disputed and unused.

## 5. The \((*-3\sigma_i)\)-sector

| ID | Kind and exact datum | Degree / period | Premises, consequences, status, locator |
|---|---|---|---|
| FN-3I-001 | \(d_3(v_1^2u_{3\sigma_i})=h_1^3u_{3\sigma_i}\); \(d_3(\{h_1+xv_1\}u_{3\sigma_i})=0\). | \((4,0)\to(3,3)\); \((1,1)\) is a 3-cycle; 8-pattern. | Leibniz, FN-2I-001, REL-3I-001--002. Text says these exhaust nonzero \(d_3\)'s. asserted-proved; lines 678-705. |
| FN-3I-002 | \(d_5(k^2\{x^2+y^2\}D^3u)=k^3\{x+y\}h_1^2D^3u\). | \((14,10)\to(13,15)\). | Uses blocked FN-2I-010. blocked; lines 707-718. |
| FN-3I-003 | \(d_5(\{yh_2+xh_1v_1\}Du)=kx^3D^2u\). | \((10,2)\to(9,7)\). | REL-3I-003 and nonexistent label prop:2sig d5-2. blocked; lines 730-742. |
| FN-3I-004 | \(d_5(x^3D^2u)=2v_1^2k^2D^2u\). | \((13,3)\to(12,8)\). | \(h_2\)-extension from FN-3I-003; printed target omits \(u_{3\sigma_i}\). blocked; lines 744-746. |
| FN-3I-005 | \(d_5(\{x+y\}D^2u)=\{h_1+xv_1\}h_1kD^2u\). | \((15,1)\to(14,6)\). | Degree argument using FN-3I-003--004. blocked; lines 748-753. |
| FN-3I-006 | \(d_5(\{x+y\}Du)=A+B=k\{yh_2+h_1^2\}Du\), \(A=\{yh_2+xh_1v_1\}kDu\), \(B=\{h_1+xv_1\}h_1kDu\). | \((7,1)\to(6,6)\). Target basis \((A,B)\); matrix \(\begin{bmatrix}1\\1\end{bmatrix}\). | Port [1:1] kills only \(\langle A+B\rangle\), not \(A,B\) separately. Uses FN-3I-003--005, so blocked; lines 755-762. |
| FN-3I-007 | \(d_9(\{x+y\}h_1^2D^3u)=2v_1^2k^3D^4u\). | \((25,3)\to(24,12)\). | Uses blocked FN-2I-011 and REL-3I-004. blocked; lines 764-775. |
| FN-3I-008 | \(d_9(\{x+y\}h_1D^3u)=x^2h_1k^2D^4u\). | \((24,2)\to(23,11)\). | \(h_1\)-extension and same \(\mathbb F_4\)-coefficient as FN-3I-007. blocked; lines 777-780. |
| FN-3I-009 | \(d_{11}(\{x^2+y^2\}D^4u)=\{h_1+xv_1\}k^3D^5u\); \(d_{11}(x^2h_1D^4u)=\{h_1+xv_1\}h_1k^3D^5u\). | \((30,2)\to(29,13)\), \((31,3)\to(30,14)\). | “Corrected restriction” has no checkable locator; second is \(h_1\)-extension with same coefficient. needs-review; lines 782-796. |
| FN-3I-010 | \(\{h_1+xv_1\}ku_{3\sigma_i}\) is permanent and detects \(a_{3\sigma_i}\); \(d_{19}(\{x^2+y^2\}D^2u)=\{h_1+xv_1\}k^5D^4u\); \(d_{23}(2v_1^2Du)=x^2h_1k^5D^4u\). | Permanent class \((-3,5)\); \((14,2)\to(13,21)\), \((12,0)\to(11,23)\). Differential pattern 32; actual permanent translate \(D^8\). | Restriction detects Euler class; vanishing-line matching forces families. asserted-proved; lines 799-845. |

## 6. The \((*-\sigma_i-2\sigma_j)\)-sector

Here \(\zeta\in\mathbb F_4\) is exact: \(1+\zeta=\zeta^2\ne0\).

| ID | Kind and exact datum | Degree / period | Premises, consequences, status, locator |
|---|---|---|---|
| FN-MIX-001 | \(d_3(v_1^2u)=h_1^3u\); \(d_3(\{h_1+xv_1\}u)=2\zeta v_1^2ku\). | \((4,0)\to(3,3)\), \((1,1)\to(0,4)\). | Leibniz with FN-2I-001, imported formulas, exact \(\mathbb F_4\). asserted-proved; lines 865-885. |
| FN-MIX-002 | \(d_5(\{x^2+y^2\}k^2D^3u)=\{x+y\}h_1^2k^3D^3u\). | \((14,10)\to(13,15)\). | Uses [TBD] \(d_9(2\zeta kh_2D^2u_{2\sigma_j})=h_1^2k^3D^3u_{2\sigma_j}\). blocked; lines 887-900, TBD 896. |
| FN-MIX-003 | \(d_5(\{x^2+y^2\}Du)=\{x+y\}h_1^2kDu\). | \((6,2)\to(5,7)\). | From FN-MIX-002, then TateSS cancellation of \((kD^3)^2\); pullback certificate missing. blocked; lines 902-916. |
| FN-MIX-004 | \(d_5(\{yh_2+xh_1v_1\}Du)=x^3kD^2u\). | \((10,2)\to(9,7)\). | Uses [TBD] \(d_5(h_2Du_{2\sigma_j})=ky^2D^2u_{2\sigma_j}\). blocked; lines 918-935, TBD 925. |
| FN-MIX-005 | \(d_5(\{x+y\}Du)=\{yh_2+h_1^2\}kDu\); \(d_5(\{x+y\}D^2u)=\{h_1^2+xh_1v_1\}kD^2u\). | \((7,1)\to(6,6)\), \((15,1)\to(14,6)\). | Hidden \(h_2\)-extension and [TBD] permanence of \(h_1D^2u_{2\sigma_j}\). blocked; lines 937-954, TBD 949. |
| FN-MIX-006 | \(d_{11}(x^3D^2u)=\{x+y\}h_1k^3D^3u\). | \((13,3)\to(12,14)\); claimed 32-pattern. | Uses [TBD] \(d_{11}(\{x^2+\zeta^2y^2\}D^2u_{2\sigma_j})=h_1k^3D^3u_{2\sigma_j}\). blocked; lines 956-975, TBD 964. |

FN-MIX-STRUCT-001 (needs-review; lines 851-860) recommends \(u_{2\sigma_j}u_{\sigma_i}\)
using orientability of \(2\sigma_j\), and warns that its pattern differs from the reversed sector.

## 7. Reversed \((*-2\sigma_i-\sigma_j)\)-sector

FN-REV-001 (structural-warning; formal_notes.tex:979-986) says the \(C_3\)-action does not identify
this page with \((*-\sigma_i-2\sigma_j)\). Its example can give \(2=0\) in one ordering but
\(\zeta+\zeta^{-1}\ne0\) in the other. Thus sectors remain distinct, Galois-related names do not
authorize copying a differential, and a \(C_3\)-orbit is metadata rather than page equality.

## 8. The \((*-\mathbb H)\)-sector

FN-H-001 (structural conjecture, needs-review; formal_notes.tex:997-1007) proposes a
\(20+\mathbb H\) period represented by \((kD^3)^{-1}a_{\mathbb H}\), combined with the norm period
\(1+\sigma_i+\sigma_j+\sigma_k+\mathbb H\). It uses invertibility of \(k\) in TateSS to conclude
that \(g=kD^3\) “does not change fates” in HFPSS. Without a comparison certificate, it is not an
admitted HFPSS period.

## 9. Rejected and excluded draft material

The block formal_notes.tex:579-673 is commented out after “Seems to be wrong”.

| ID | Excluded claim | Status and reason |
|---|---|---|
| FN-REJ-001 | \(d_9(k^2h_1^2D^3u)=k^4xh_1^2D^4u\). | rejected-commented; lines 581-592. |
| FN-REJ-002 | \(d_7(k^2h_1D^3u)=2k^4D^4u\). | rejected-commented; lines 594-599; depends on FN-REJ-001. |
| FN-REJ-003 | The \(P_0\cup P_1\) matching and candidate higher differentials. | rejected-commented; lines 601-672 also say “need to be proofread”. |

## 10. Period-first fact organization and vanishing audit

### 10.1 Machine record

The normative machine index is
backend/data/review/formal_notes_periodic_fate_ledger.v1.json. It contains:

- six period mechanisms: genuine \(D^8\) object identity, the all-family
  \(g^{\mathbb N}D^{8\mathbb Z}\) HFPSS semiperiod, the guarded bidirectional Tate lattice, and the
  three explicitly pattern-only multipliers \(D,D^2,D^4\);
- three module kinds separating finite 2-primary, Witt 2-adic, and \(j\)-adic formal-power-series
  cells independently of filtration;
- all 37 active sector fact families, retaining their existing FN-* ids;
- source_period_class_ids and target_period_class_ids for every fact;
- conditional comparison-class aliases whose invariant is
  \(\rho=\deg_D-3\deg_k\bmod 8\);
- finite-domain vanishing obligations, a separate formal-series family registry, and a rendering
  contract.

The read-only endpoint
/api/v2/review/periodic-fate-ledger returns both the ledger and a computed audit. It never writes
to project.json and cannot admit a research claim.

The same audit is visible without calling the API: open `/review` and inspect the **HIGH
FILTRATION FATE AUDIT** panel above the logic graph. It shows the aggregate status and counts, the
separately registered formal-series families, and every unresolved obligation with its current
reason.

### 10.2 What counts as a proof that a high-filtration cell dies

DKLLW24's strong horizontal vanishing line of filtration \(23\) imposes an obligation on every
class of filtration \(f\ge23\). For a cell \(V\), “there is an arrow touching this dot” is
insufficient. On each page the checker must compute

\[
V_{r+1}=\ker(d_r^{\mathrm{out}}\colon V_r\to W_r)/
\operatorname{im}(d_r^{\mathrm{in}}\colon U_r\to V_r).
\]

A vanishing certificate is complete only if:

1. the \(E_2\)-basis is enumerated in every relevant periodic fundamental domain;
2. every identity used to reduce the infinite chart has an admitted period/comparison certificate;
3. each admitted complete matrix is applied page by page;
4. image is contained in kernel, and the final quotient has rank zero for every \(f\ge23\) cell;
5. the result is invariant under the admitted period translations;
6. a rejected, source-proved, partial, or missing map contributes no canonical killed rank.

For a finite 2-primary cell, “rank” is the exact finite-field/subspace rank already implemented by
the checker. A \(j\)-adic formal-power-series family is not sent through that rank audit. It is
stored separately under `formal_series_families`, together with the fixed differential and
permanent-cycle templates supplied by the source. A future vanishing obligation for such a family
points to one `fixed_differential_family_id`; it is resolved only when that admitted template
explicitly records `vanishing_outcome: killed`. We do not require a separate
continuous/complete-module certificate and we ignore finite killed-vector counts for this module
kind.

For a rank-two target with incoming image \(\langle A+B\rangle\), the killed rank is one. The
remaining quotient rank is one until another admitted map or relation removes it.

### 10.3 Current computed audit

The initial ledger deliberately returns underdetermined rather than claiming a false completion.
The current status can be read directly in Reviewing mode at `/review` (or as JSON from the API
above). It has five explicit finite-rank obligations; the integer and \(\sigma_i\) bo formal-series
families are listed separately and do not inflate this obligation count:

| Obligation | Period class | Current result |
|---|---|---|
| Enumerate all nine \(RO(Q_8)/P\) sectors | fundamental-domain obligation | unresolved: formal_notes does not list every \(E_2\)-basis cell. |
| \(h_1^2k^6D^7u_{2\sigma_i}\), filtration 26 | pc.2i.gd8.h1sq-cone-r5 | covered by the verified nonzero FN-2I-016 family. |
| \(\{x^2+y^2\}k^6D^{10}u_{2\sigma_i}\), filtration 26 | pc.2i.gd8.a2-cone-r0 | unresolved: FN-2I-019 remains review because “only source” is not chart-complete. |
| \(x^2h_1k^6D^7u_{3\sigma_i}\), filtration 27 | pc.3i.gd8.x2h1-cone-r5 | unresolved: FN-3I-010 is source-proved but not Danus-admitted. |
| The rank-two \((A,B)\) target cell | pc.3i.d8.target-cell-line11-cone-k1-d1 | unresolved: FN-3I-006 is under review and its incoming line has rank one, not two. |

Thus this version implements the checker and names the exact gaps, but does not yet prove that all
high-filtration classes in every shifted page die.

### 10.4 Drawing from period classes

A renderer should use semiperiod_class_id plus a concrete \((g,D^8)\) translation vector as the
visual occurrence key, while retaining the D8 object-orbit id for equality checks. It materializes
only translates intersecting the viewport. A differential edge is keyed by fact_id plus source
translation. Pattern-only \(D^4\) siblings are drawn as separate anchors with a shared pattern
badge; they are not deduplicated. High-rank images target projective ports, and zero maps are
metadata rather than arrows to a fake zero node. A \(j\)-adic cell is drawn as one module glyph
with an expandable \(j\)-tower and a link to its fixed differential-family record, not as an eagerly
enumerated infinity of basis dots.

### 10.5 Legacy source dependency snapshot

    FN-2I-001 + imported integer / (*-sigma_i) facts
    ├─ FN-2I-002, FN-2I-003
    ├─ FN-2I-004 ─┐
    ├─ FN-2I-005  │ coefficient/transfer review required
    └─ FN-2I-006 ─┘

    FN-2I-007 (restriction review required)
    └─ FN-2I-009
       ├─ FN-2I-010 ──> FN-3I-002
       ├─ FN-2I-011 ──> FN-2I-012 ──> FN-2I-015
       │                 └──────────> FN-3I-007 ──> FN-3I-008
       └─ FN-2I-016

    REL-3I-003 + intended FN-2I-004 (broken label)
    └─ FN-3I-003 ──> FN-3I-004 ──> FN-3I-005 ──> FN-3I-006 [matrix 1;1]

    four independent [TBD] premises
    ├─ line 896 ──> FN-MIX-002 ──> FN-MIX-003
    ├─ line 925 ──> FN-MIX-004
    ├─ line 949 ──> FN-MIX-005
    └─ line 964 ──> FN-MIX-006

Source-clean terminal claims are FN-2I-018--021, FN-3I-001, FN-3I-010, and FN-MIX-001. They may
be proposed for Danus review, but asserted-proved still means “proved in this draft”. Blocked,
disputed, and rejected-commented records remain outside canonical page-transition computations.

## 11. Completeness and consistency audit

- Every active theorem-like environment in Sections 4.1--4.5 is represented, including zero maps
  and the permanent cycle in FN-3I-010.
- Every displayed nonzero differential with stated coordinates satisfies \((-1,r)\).
- All four [TBD] premises are preserved at lines 896, 925, 949, and 964.
- Claims inside the “Seems to be wrong” block are not admitted.
- The target at lines 756-761 is one vector with matrix \([1,1]^T\), not two killed basis vectors.
- The exact \(2\zeta\) coefficient is retained; the reversed-sector warning prevents a false orbit
  identification.
- No claim treats \(D^4\) as the same HFPSS object. The explicit genuine permanent translate in the
  source is the \(D^8\)-translate of FN-3I-010.

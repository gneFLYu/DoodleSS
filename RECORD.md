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

## 12. Pure-sector normalization correction (2026-09-20)

The user's chosen psi-fixed generators and Thom classes fix every nonzero F4
coefficient in the pure `*-n sigma_i` sectors to 1: equivariance gives c^2=c.
This supersedes earlier pure-sector unit-review cautions, including those in
`REU_LATEST_FACT_CHAIN.md`. It does not replace Witt factors 2 or 4 by 1, or
normalize independent mixed-sector coefficients.

FN-3I-001's two d3 equations and three h1 products have been independently
verified using FN-2I-001 and the actual DKLLW hidden h1 product (main.tex
1094–1111), with the mod-2 injection checks at 2782–2784 and 2868. Their
8-stem repetition uses d3(D)=0. This admission does not extend to the later
d5-zero, completeness of all d3 families, or the claim at formal_notes:704
that every survivor is 2-torsion: filtration-zero 2W kernels remain.

The Jan29 proof of FN-3I-010 and its Euler-detector premise remains withdrawn
as an authority; the earlier “source-clean” summary above is historical.
The independent Table 9 / Euler / Tate outgoing-cycle certificate for
2v1^2 D u_3sigma is stored separately. It does not insert a negative-source
Tate arrow into HFPSS or declare forward g-multiples immune to incoming maps.

### 12.1 Independent early-page proofs admitted after normalization

The following admissions have separate product/degree/transfer certificates;
they do not follow merely from fixing an F4 unit, and do not restore Jan29:

- FN-3I-003--006: the four d5 families, together with d5(P)=0 (16-stem
  repeat) and d5(Q)=0 (8-stem repeat), where P=h2(x+y)u and Q=h1(h1+xv1)u.
  The P+Q target kills one line, not both basis columns. P, Q and P+zeta Q
  remain nonzero in the resulting one-dimensional quotient. Sources:
  formal_notes:357--378,730--762; DKLLW main.tex:1094--1123,1179--1190,
  1336--1342,1451--1453. The d5(Q)=0 certificate uses its independent
  empty-target/product argument, not the invalid implication d3(C)=0 => d5(C)=0.
- FN-MIX-001: d3(U)=h1^3u and d3(C)=2 zeta kU. The second map affects the
  constant j layer only. Its unscaled target stores Witt valuation 1 and its
  F4 map scalar stores zeta (encoding 2); the reflected atlas uses zeta^2
  (encoding 3). Field encodings are not integer coefficients. Sources:
  formal_notes:881--901; DKLLW main.tex:638--647,937--949,1094--1111,
  1183--1185,2817--2839,2868. Other mixed coefficients remain separate.
- FN-2I-005 and its even-D zero: the kernel subgroup is C4<i>=ker(sigma_i).
  The restricted unit transfers to 2u_2sigma, with trace 1+1=2 and trivial
  determinant action for 2sigma_i. This gives zero outgoing differentials;
  Leibniz gives d5(2D^m u)=2m k h2 D^m u and a 16-stem pattern. Sources:
  DKLLW main.tex:520,1021,1384--1389,1451--1453. This does not promote
  FN-2I-006 or use the swapped-subgroup sentence in formal_notes:411--414.

Production-runtime tests check the new arrows and quotients, including atlas
copies, without forcibly admitting review claims. The historical d23 fixture
now expects the independent Tate-cycle contradiction instead of suppressing it.
Researching was checked in the browser on 3sigma E5/E6 and mixed E3/E4;
arrows disappear on the following page and no console warnings/errors appeared.

Verification for this admission update: 113 focused tests passed across the
normalization, proof certificates, real page quotients, ledger and all-atlas
checks. The wide all-atlas check still covers all 16 sectors on E3/E9/E23/E24;
each workspace now has its own bounded Node invocation, avoiding one aggregate
timeout for 64 page computations. Ten JS syntax checks passed and all five
backend/public helper pairs are byte-identical. The earlier full-suite run was
772 passed, 7 failed, 2 errors while files were changing; it is not a clean
certificate for this version. Its reported failures have focused passing
reruns, but a new unchanged-source full run is still required.

### 12.2 Mixed P d5 and the distinct three-sigma Euler-image gap

The unchanged-source full suite following section 12.1 finished successfully:
796 passed in 994.73 seconds. This is the baseline before the following update,
not a claim that every mathematical differential has been established.

FN-MIX-004 and its even-P zero now have an independent certificate. Transport
FN-2I-004 by omega: h2 and k are fixed, and the source and target have the same
D scaling, so the relative unit is 1. Multiplication by permanent a_sigma_i,
with P=h2(x+y)u and R=x^3u, gives d5(PD)=kRD^2 and P*h2=RD. The target's
incoming d3 cell is empty; its outgoing cell is not empty and its cycle property
must instead follow from this product. Leibniz and 2P=0 give the even-P zero
and the 16-stem repetition. No other mixed parameter, Q-zero, or D2 permanence
is inferred. Sources: formal_notes:357--379,934--951; record/note:713,725;
DKLLW main.tex:915,1094--1123,1179--1190,1972--1976,2868.

For three-sigma P D2 and P D6, the Euler-image E9 equations follow independently
from FN-2I-016 and the actual Euler product. Their targets might already be d5
boundaries: the finite incoming direction is A k D^(m+1)=g A D^(m-2), where
A=(x2+y2)u_3sigma. Proving d5(A)=0, or the complementary FN-3I-002 nonzero map,
remains necessary. This is not a relative-zeta ambiguity. The P metadata no
longer depends on the withdrawn Ck/Jan29 proof; Q/C retain their own unresolved
dependencies. Refresh explicitly clears P's stale withdrawn-dependency field,
without changing user annotations or promoting the nonzero arrow. The nested
verified certificate certifies only an equation, not target nonvanishing.

New focused checks: 25 production-runtime tests cover all six mixed atlases on
E3--E6, the original/+16/+64/forward-g arrows, the S53 target quotient, and the
unresolved Q/jQ directions. Four tests cover the three-sigma equation-only
certificate, all three atlas copies, repeated refresh and E9/E10 non-admission.
No tests force admission of review claims to obtain these results.

Browser verification at localhost:5078 checked mixed E5/E6 and both Review
certificates. Accepted arrows are solid, review arrows remain previews, and
the new family alone changes the next-page quotient; no console warnings or
errors were observed. Ten JS syntax checks passed; the five backend/public JS
pairs remain identical. Post-update regression passed all 177 tests in 351.88
seconds across the formal-chart, periodic-fate, mixed d5/d9/transport, new mixed
P d5, three-sigma d9, pure normalization, all-atlas and table-ledger suites.
The full 796-test certificate above predates this small update; the 177-test
run includes the 29 new focused checks. An obsolete test expecting even-P to
remain review was updated to require verified P while keeping Q review.

Next independent source audit, not yet a code admission: the C4 restriction
argument for FN-2I-009 may be repaired using BBHS Propositions 5.25/5.28 and
the genuine (14+2sigma) C4 period, followed by the DKLLW Tate comparison for
h1D2u/h1D6u. This provides a candidate proof chain for FN-2I-011 and FN-2I-010.
FN-2I-006 still needs independent verification of the specific Thom-coefficient
transfer exact sequence; do not use an E-infinity transfer criterion on every
Er page. FN-2I-012/013 and the higher vanishing argument are not promoted by
this audit. Original source and quotient checks are required before coding it.

### 12.3 Independent two-sigma transfer, restriction, and Tate certificates

The follow-up audit repairs FN-2I-006 and verifies FN-2I-009/010/011. Their
production rows and the periodic fate ledger now use `verified`; no unknown
coefficient assignment or imposed vanishing line is used to obtain the maps.

For FN006, the short exact sequence of Thom coefficient modules is used only
on group cohomology E2. The Euler target is zero because the central element
acts negatively on the 2-torsion-free pi6 coefficient and Tate cohomology is
four-periodic. BBHS Propositions 5.21/5.25/5.27 identify the C4 d7 and show that
its preimage cell loses its positive mu tail by d3. The normalized transfer
from C4<j> is 2u, while C4<i> (the kernel of sigma_i) transfers 1 to this same
zero-outgoing class. This contradicts survival of kh1^3u to E7 and forces
the d5. The i/j labels printed in formal_notes:411-413 were interchanged.
Nonzero follows from this argument; unit 1 separately uses the user's chosen
pure-sigma-i Galois-fixed basis. No arbitrary-Er transfer exactness is asserted.

For FN009, the independently checked BBHS Propositions 5.25/5.28 give the
permanent C4 unit P=Delta^2/u_2sigma of degree 14+2sigma and the nonzero d13 on
Delta^3 nu^2. After restriction, finite earlier-target exclusion forces the
Q8 d11 on AD2 and AD6. Their source is I62X+I62Y, not either summand. The two
32-separated blocks repeat under Q8 D8; C4 Delta4 permanence is not imported
as Q8 D4 permanence.

Translating that d11 by g^-3 D8 in Tate gives H2/H6 zero-outgoing certificates.
They do not prevent incoming deaths of forward-g images. Separate negative-
source primitive d3 certificates cover positive-j D2/D6, not their constant
terms. FN010's forced earlier incoming differential acts on two_valuation=1
of I31; FN011's d9 kills only the constant I22H line and leaves its j tail.
Its I13/I13X target is already a common rank-one quotient, not two targets.

New production tests: `test_verified_two_sigma_d9.py` (9 passed, 22.16 s) and
`test_verified_two_sigma_transfer.py` (13 passed, 52.87 s). They cover all three
pure-two-sigma atlas representatives, both 32-stem blocks, forward-g/D8
translates, exact Witt/series ports, actual live arrow endpoints, and the
outgoing-only/allowed-incoming distinction. A preexisting page21 partial map
on I13+I13X remains explicitly unknown (rank2, definedRank1); no zero map was
invented to remove it. The first larger regression had 147 passes and one
obsolete all-mixed-d5-review assertion; that assertion now distinguishes the
independently verified FN-MIX-004 from the still-review mixed families.

Browser verification at localhost:5078 confirms the new E9 arrows, their
absence on E10, and the d11/E12 lifecycle. Review displays the new admitted
source references. Console warnings/errors are empty. Ten JavaScript syntax
checks pass and all five backend/public pairs are identical. A full pytest
run is in progress; these focused results do not certify global convergence.

Next independently checked chain (not yet promoted in code): with repaired
FN006, FN012/FN013 can be forced from FN011. If H3/H4 had no d7, their d9
targets are FN006 d5 sources and already empty, contradicting the nonzero d9
on h1*H3=(D^-1*h1)*H4. The exact E7 target quotients are respectively the
2-layer of k2D4u and the 4-layer of k2D5u. Positive-j source tails must remain.
The latter integer factor is already a 13-cycle by DKLLW main:1694-1702; its
final d23 is not needed as a premise. The +32 sibling arguments use D7/D8
separately, followed by permanent D8 repetition.

FN-MIX-002/003's former TBD nonzero premise can now use the verified FN010:
omega gives d9(2*zeta*k*h2D2u_2sigma_j)=k3*h1^2D3u_2sigma_j. Multiplication
by permanent a_sigma_i has zero source (2-torsion), forcing the target to
vanish before E9. The possible d3/d7 source cells vanish; the other d5 source
direction S62V and its series were already primitive-d3 sources, leaving A.
This proves nonzero c but does not choose c or rule out c=1. In particular,
both FN010 Euler images test the same odd-D family; they do not constrain
the even c+1 family. Keep this distinction when updating mixed admission.

Review-only legacy summaries also need reconciliation: reu_fact_chain.py's
prop_reu_d11_corrected_pattern still says up-to-unit, and its admitted
prop_reu_d7_corrected_pattern omits the FN012 premise for combining two
32-pattern branches into 16. These summaries do not feed chart maps but do
feed Review/article TeX. The existing-ID early return means seed-text edits
alone would not refresh saved projects. A scoped refresh must preserve user
additions and cite the current canonical certificates. The old normalization
summary and test_reu_fact_chain.py assertions likewise predate the user's
pure-sigma-i Galois normalization declaration.

### 12.4 Exact two-sigma d7 quotients and normalization refresh

FN-2I-012/013 now have independent verified certificates, using the chain
outlined above. Production-runtime tests distinguish their actual E7 target
quotients: FN003*h2 removes the four-layer at (24,8), leaving two; FN005's
outgoing d5 removes the two-layer at (32,8), leaving four. Both targets vanish
on E8, while the positive-j source ideals remain. Eight focused tests passed
in 20.79 seconds, covering all three pure-two-sigma atlas representatives,
both 32-separated blocks, D8 translates and forward-g images without forcing
review admission. Browser checks on E7/E8 in all three atlas representatives
confirmed accepted arrows only on E7, with no console warnings or errors.

The two managed Review normalization facts now refresh existing saved projects
as well as new seeds. They use the researcher's chosen psi-fixed pure-sector
bases and the exact nonzero F4 unit 1, while retaining Witt 2/4 and mixed-sector
parameters. The scoped refresh preserves custom notes, references, premises
and additional conclusion fields. Three tests cover this normalization and
idempotent preservation; together with formal-closure tests, 11 passed in
18.38 seconds. Browser inspection confirms the refreshed verified statements.
Other old Review d11/d9/d7 summaries are still separately awaiting correction.

The monolithic full regression was deliberately interrupted after the host
reported only 137864 KB free virtual memory, pagefile exhaustion and Node
allocation failures. It had no final pytest result and is not a certificate.
A new run collected 856 tests and executes each collected test file in a
separate Python process. At this checkpoint, 33 completed files report 440
tests, zero failures and zero errors; the same run remains live. Do not treat
this partial result as a complete-suite pass. Reports are under the ignored
tmp/pytest-isolated-2026-09-21 directory.

Read-only audit for FN014 repairs its transfer proof using BBHS Proposition
5.28 (printed pp.3466-3467), not the Jan29 note. Use C4<i>=ker(sigma_i), and
the actual C4 source Delta*nu*varpi. At E2 its transfer lies in the Euler
kernel spanned by P=(x2+y2)h2D2u: eP=0, whereas the other source line E=h2^3Du
has eE=2kv1^2D2u_3sigma nonzero, by the actual hidden h2 product and W/4
calculation (DKLLW main:1094-1118,2831-2839). FN003 supplies an independent
negative-source Tate certificate for P's zero outgoing maps. Naturality then
forces 2k4D4u to be zero by E13; exact early quotients exclude later incoming
possibilities and force d7. The C4 Delta4 sibling must be proved separately
before translating by permanent Q8 D8 and g; do not invert Q8 D4. This audit
has not yet promoted FN014 or added its cycle certificates at this checkpoint.

### 12.5 Independent FN014/FN016 proofs and exact Review summaries

The isolated baseline above completed: all 72 collected files, 856 tests,
zero failures and errors. This is the pre-increment baseline; the additional
tests below were not part of that original collection.

FN014 is now verified in both the formal chart and the admission ledger, using
the repaired C4<i> transfer/E2 Euler-kernel proof from section 12.4. Added
outgoing-only Tate certificates for (x2+y2)h2D^(2,6)u. These are genuinely
coupled I13X+I13 vectors, not two independent zero maps. Initial focused tests
correctly exposed a proper-subspace warning when only the sum was specified.
The missing independent I13 certificates follow from the already verified
FN011: its D7 block times g^-2 gives a Tate d9 (18,-6)->(17,3), and its D3
block times g^-2D8 gives (50,-6)->(49,3). Their targets are h2^3D^(1,5)u.
These complement the coupled vectors to a full zero-outgoing map without
relaxing tests, fabricating a negative-filtration HFPSS arrow, or protecting
classes from incoming differentials. In particular, their g^2 images are
FN011 d9 targets, not immortal points.

FN016 now has an independent verified certificate as well. For m=2,6,
multiply FN009's appropriate d11 block by D^-1h1, a published 13-cycle.
The source product Ah1k3D^(m+4)u is d3(k3D^(m+4)u); hence the target
T=h1^2k6D^(m+5)u is already zero on E11. Earlier incoming-source exclusion
leaves d9 from h2k4D^(m+4)u. Primitive d3 hits jT, not its constant; the
d5 source cell is empty; the prospective d7 source was already an FN006
d5 target. The high source's double is an FN005 boundary: k3 is not a
5-cycle, so bare D parity is insufficient. Use g3D^-8(2D5u) and g3(2Du)
explicitly. Tate translation by g^-4D8 gives the low FN016 row.
Its W/4 source retains the two-layer after d9; only the odd constant dies.
This proof needs neither a final d23 nor a vanishing-line/Jan29 premise.

Three legacy Review summaries now refresh saved projects as well as fresh
seeds: d11 cites canonical FN009, d9 cites canonical FN016, and the combined
16-stem d7 pattern cites both FN014 and FN012. They state the exact nonzero
F4 scalar 1 in the researcher's chosen psi-fixed bases, preserve Witt 2/4,
and distinguish repeated patterns from permanent D8. Scoped refresh removes
the obsolete managed d23/hidden-2 dependencies while retaining additional
researcher notes, references, premises and conclusion fields; mixed facts
are not rewritten.

After adding the independent complement certificates, 74 focused/regression
tests passed in 228.75 seconds, including the three two-sigma atlas images,
the new FN014/FN016/Review tests, the earlier d7/d9/transfer proofs and pure
Galois normalization. The initial 20-pass/4-failure run is not treated as a
success; its proper-subspace failures were resolved by the independent
mathematical certificates, without weakening assertions. Browser checks
confirmed FN014 on E7, FN016 on E9, neither on E8/E10 in all three atlas
images, with no console warning/error. Published integer and sigma_i d23
families were also visually checked on E23 and absent on E24.
Eight JavaScript syntax checks passed; all six backend/public static pairs
match. Further isolated checks now include the exact five published d23
source/target ports and the new I13 incoming-death regression.

The follow-up isolated run also completed: 11 files, 160 tests, zero failures
or errors (reports: tmp/pytest-increment-2026-09-21). This includes all five
published d23 rows at their anchor, +D8 and +g positions, on E22/E23/E24,
and the I13 g^2 incoming deaths described above. Together with the preceding
74-test run these cover 226 distinct post-change cases; eight FN016 cases
were deliberately rerun. The present suite collects 888 cases, but the
entire 888-case suite has not been rerun after this increment. Browser Review
also visibly confirms the three exact-unit summaries and their canonical
premises. No research TeX was modified or saved project reset.

This does not resolve the remaining reviewed FN017/high two-sigma rows,
three-sigma or mixed claims. Fixing pure-sector F4 normalization does not
prove their nonzero differentials or source survival.

### 12.6 Independent two-sigma and three-sigma quotient certificates

FN-2I-017, FN-2I-018 and FN-3I-002 now have independent certificates in
formal_notes_chart.py and verified ledger entries. FN017 uses the published
Table 8 d23 product obstruction: the product is zero already on E23, so an
incoming d23 is too late. Finite earlier-source exclusion forces its d9;
the odd source layer has already died by d5, leaving precisely the double.
FN018 is the Table 9 d13 Euler image. Its target is a rank-one quotient in
which the earlier d5 kills K+L, not K and L separately. FN002 is forced by
the zero Euler image of FN010's source, with finite incoming-source exclusion;
the low seed is an independent Tate translate, not the commented corollary.
None of these certificates uses the withdrawn Jan29 three-sigma proof.

The six DER-3I-D9-P/Q/C rows at D2 and D6 are now independently verified.
Writing A=(x^2+y^2)u, B=(x+y)u, C=(h1+xv1)u, P=Bh2, Q=Ch1,
R=Bh1 and T=Bh1^2, the actual finite product Ah2=T and verified FN002
d5(AD)=kTD imply d5(A D^(2l))=0. The E5 inverse of D is used only
on that page. FN016's Euler image gives d9(PD^m)=T k2 D^(m+1).
The only possible earlier finite d5 source is an even-A translate and has
zero differential; the other direction was a primitive d3 source.
FN006 makes g(P+Q)D^m a boundary, and a separate finite-target check
shows g is injective on this particular E9 target, forcing Q's same map.
After verifying C's d3/d5/d7 are zero, h1 multiplication forces its d9
to R k2 D^(m+1). This replaces the old Ck-permanence/Jan29 dependency.
D2 and D6 remain separate blocks with permanent D8 and forward g repeats;
D4 is not declared an E9 unit.

Exact zero-map records accompany these arrows: even A at d5; C at d5/d7;
Q at d7; and positive-j C/Q at d9 in the two blocks. The first runtime
check exposed a missing P d7 certificate (a proper-subspace map, not a
permission to assume the rest zero). It is now supplied independently:
for even m, h2D^m u2 has zero d3/d5, no earlier incoming, and empty d7
target (8m+2,8); permanent Euler multiplication gives d7(PD^m)=0.
The positive-j d9 zeros use negative-source primitive Tate d3 images.
They do not resurrect the forward-g copies that are actual HFPSS d3
boundaries. Low P/Q retains the constant P+Q kernel and the positive-j Q
ideal; high g(P+Q) was already killed by FN006 and is not copied back in.

Targeted verification: test_two_sigma_euler_d13.py passed all 8 cases;
test_three_sigma_verified_even_d9.py and test_three_sigma_d9_closures.py
passed all 21 cases after the missing P zero certificate was added.
Earlier failing runs are not counted as successes. The latter tests use
unmodified production admission for the new six maps, check all three atlas
images, both blocks, D8/forward-g copies, exact kernels/tails and rendered
arrows with live endpoints. Saved-project refresh removes managed stale
conditional/withdrawn metadata while preserving researcher annotations.
Ten JS syntax checks passed and all six backend/public static pairs match.

Browser checks on the local service show accepted FN017 at E9 and FN018
at E13, absent at E10/E14 respectively, in all three two-sigma atlas images.
The even-D three-sigma P/Q/C maps appear at E9 and disappear at E10 in
S30, S03 and the Picard-translated S11; S33 belongs to the sigma orbit,
not this three-sigma orbit. Console warning/error output is empty.
No research TeX was edited and the saved project was not reset.

A complete isolated-per-file regression is running, with reports under
tmp/pytest-e9-2026-09-21; its completion has not yet been asserted here.
The late two-sigma, remaining three-sigma and mixed-sector claims still
require their independent quotient/vanishing checks. This increment is
not a claim that the full research calculation or all sixteen E-infinity
charts are correct.

### 12.7 Even-source Phi transport to the six mixed atlas charts

The researcher's psi-fixed choice removes the earlier relative-zeta
objection on pure *-n sigma_i pages: equivariance forces a nonzero F4
coefficient to equal its Frobenius square, hence to be 1. This does not
discard Witt 2/4 layers or normalize mixed-sector coefficients. Admission
still requires independent source, target and product certificates.

At the group-element level, the literal map i->i, j->k, k->j is not a
Q8 automorphism (it contradicts ij=k). Central signs are needed for a
lift. The invariant statement used here is that <i> is fixed and <j>,
<k> are exchanged; thus sigma_i is fixed and sigma_j, sigma_k are
exchanged. This notation correction does not affect the chosen-basis
coefficient conclusion or the existing RO action implementation.

DER-MIX-PHI-D9-D0 and D4 are now verified, linked respectively to the
independently proved three-sigma C-D6 and C-D2 maps. The permanent Tate
unit Phi=N_C4^Q8(dbar)*u_4sigma_k*g^-1*a_H has normalized stem -16.
After omega^2, multiply by Phi^-1 and a_sigma_j; only the D0 block needs
a final permanent D^-8. The exact finite products a_sigma_j*C_k=zeta*B*h1
and a_sigma_j*B_k*h1=R cancel the omega factor and the common Thom unit.
This uses the finite j-annihilated order-two lines, not an arbitrary
coefficient choice on a Witt module. D4 is not treated as an E9 unit.

The finite S73 target is distinct from the same-cell S73V primitive d3
source. Its potential incoming d3 source is itself the entire primitive
d3 image (including local j_order=0), so d3 squared is zero there. The
incoming d5 source cell is empty. The incoming d7 S40 slot loses its odd
U layer by primitive d3 and its even 2U layer by verified mixed d3(C).
These exclusions do not depend on the unresolved mixed d5 parameters.
Two scoped page-seven zero claims record the Phi/Euler image of the
verified source 9-cycle. They do not assert permanence or prevent actual
incoming deaths. D8 and forward-g translates retain the same proof.

Mixed coefficients remain external source-parameter links, not local
assignments. Their runtime value is 1 because the referenced pure map is
verified and normalized; reflected atlas images still apply Frobenius to
that link. D1/D5 Phi rows and other unproved mixed claims remain review.
The source-link tooltip now states that distinction explicitly.

Local-browser checks covered all six mixed atlas charts: the two accepted
Phi families are present on E9 and absent on E10, with no console warning
or error. The local service was restarted on 127.0.0.1:5078 without a
saved-project reset. test_mixed_phi_d9.py passed all 23 cases. A new
eight-case production-data test covers the exact finite ports, all six
images, D8/g repeats, live endpoints and source-linked coefficients; its
final run passed all eight cases in 31.33 seconds. Its first run passed
seven and failed one: the test incorrectly demanded a complete quotient
for unrelated mixed P/Q d5 blocks. The final assertion explicitly requires
those known proper-subspace warnings, scoped only to page-five S22H+S22Y
blocks with defined rank strictly below rank; it rejects other conflicts.
No zero on Q or jQ was invented to make the test pass.

The full serial run completed: 80 files, 916 cases, 908 passed, four failed
and four errored. It exposed stale review/count assertions in four files
and a Node process resource failure in the eighteen-project mixed-d5
parameter batch. The assertions now check actual independent certificates,
and that batch runs one candidate per Node process while retaining all
eighteen cases. All five affected files passed their isolated reruns:
mixed_d5_parameters 7, pure_galois_normalization 16, smoke 12,
thom_formal_chart 21 and three_sigma_verified_d5 5 (61 total).
The fourteen atlas_transport tests also passed against the final code.
Together with the final eight new tests, this is 83 passing targeted cases.
The full run was started before this Phi increment was finished; these
results must not be described as one fresh 924-case run of a single final
snapshot. Original failing reports are retained under
tmp/pytest-e9-2026-09-21 and tmp/pytest-phi-rerun-2026-09-21; the final new
test report is tmp/pytest-phi-final-2026-09-21.xml.

Ten JavaScript syntax checks passed and six backend/public static pairs
match. No research TeX, static implementation or saved-project reset is
part of this increment. Independently audited odd-three-sigma, d11 and
late-two-sigma arguments remain separate next-step work, not silently
admitted here.

### 12.8 Independent odd-three-sigma d9 and restriction-detected d11

The pure-sector Galois normalization from Section 12.7 is retained. It
fixes residue-field units, not proof admission or Witt valuations. The
remaining eight three-sigma d9 anchors now have independent certificates:
T D3/D7, B D3/D7/D4/D8 and C D3/D7, where
T=(x+y)h1^2 u, B=(x+y)h1 u and C=(h1+xv1)u.
Together with the six even-block P/Q/C anchors, all fourteen recorded
three-sigma d9 anchors are verified. Each anchor uses permanent D8 and
forward g=kD^3; the D4 siblings have separate proofs, not a presumed
invertible D4 at E9.

For T, multiply independently verified FN-2I-011 by the Euler class.
The actual hidden product h1*(x^2 h1 u)=2k v1^2 u identifies the target
as the finite constant Witt two-layer of S40, not its odd layer or its
positive-j ideal. Its potential incoming d3 source is a 3-cycle, its
incoming d5 source is itself the FN003 d5 image (so d5 squared is zero),
and its incoming d7 source already died by primitive d3. Multiplication
by h1 detects the B D3/D7 rows. The separately published 13-cycle
D^-1 h1 detects B D4/D8 from those rows. This replaces the withdrawn
Ck-permanence/high-filtration-cutoff argument and needs neither d11 nor
the Jan29 d19/d23 proof. Managed migration removes the obsolete cutoff
and inverse-g comparison fields from those two B claims.

The C D3/D7 rows instead use the Euler image, DKLLW Table 8 rows 12/13,
and the permanent u4sigma class. New outgoing-only B d5/d7 zero
certificates record actual empty or already-dead targets. Positive-j C
has separate page-nine zero constraints in the D3/D7 blocks, proved by
the same negative-source Tate comparison as the D2/D6 constraints.
They preserve the low j-tail without reviving high translates that were
already primitive d3 boundaries. There are now 22 scoped zero records
across the two- and three-sigma source workspaces.

Both FN-3I-009 d11 rows are independently verified by C4 restriction.
Writing A=(x^2+y^2)u and R=x^2 h1 u, the A D4/D8 restrictions are a
constant permanent Witt unit times Delta^(p-1) nu^2, p=4,8. DKLLW's
restriction formula and BBHS20 Proposition 5.28 detect a nonzero d13
on those images. Direct exclusions of d3,d5,d7,d9,d13 in Q8 leave d11
as the only possibility; this is not merely an upper bound on death.
The BBHS Delta4-linear second block does not assert Q8 D4 permanence.
The paired 32-stem d11 pattern is retained and explicitly noninvertible.

The first d11 target is the finite constant C line. The h1 multiple
targets Q=C h1. At this latter cell, primitive d3 removes positive-j Q
and FN006 d5 removes only P+Q, P=(yh2+xh1v1)u, leaving the nonzero
common class [P]=[Q]. The d11 therefore kills that rank-one quotient,
not two independent initial basis columns. The source R survives by
the nonzero h1 detection argument, without guessing a filtration-zero
incoming map. Neither odd d9 nor withdrawn FN-3I-010 is a premise.
The BBHS PDF was checked visually at printed pages 3465-3466 as well as
against the local DKLLW/formal-notes source formulas.

New production-data regressions (no test admission/coefficient overrides)
passed: test_three_sigma_verified_odd_d9.py, 8 cases in 100.30 seconds;
test_three_sigma_verified_d11.py, 8 cases in 28.86 seconds. They cover
S30/S03/S11, D8 and forward-g translates, live arrow endpoints, exact
E9->E10 and E11->E12 quotient changes, Witt-layer separation and low/high
positive-j behavior. The nine-file focused regression initially finished
with 96 passes and four fixture errors: the six-atlas mixed-Phi runtime
batch exceeded its 180-second timeout, with no mathematical assertion
failure. Its fixture now runs one chart per Node process, sequentially,
retaining the complete project for external coefficient links, all six
charts, all four pages, bounds, probes, assertions and the same timeout.
The isolated rerun passed all eight cases in 13.76 seconds. The final
targeted results therefore cover 116 passing cases across eleven files,
including all fourteen atlas-transport tests (all sixteen charts).
This is a focused regression plus rerun, not a new full-suite result.
The original reports remain under tmp/pytest-odd-d11-regression-2026-09-21;
the final rerun is tmp/pytest-odd-d11-phi-isolated-2026-09-21.xml.

Local browser verification covered E9/E10/E11/E12 on all three images.
All fourteen d9 families appear accepted on E9; no d9 arrows remain on
E10. Both d11 families appear accepted on E11 and disappear on E12.
Console warnings/errors are empty. A transient browser timeout during
the mixed-Phi batch recovered; the final visible page is three-sigma E11.
Ten JS syntax checks passed and all
six backend/public static pairs match. The local service is available
at 127.0.0.1:5078. The saved project SHA256 stayed unchanged throughout
this check; no reset, research-TeX edit or static implementation edit was
needed. Mixed Phi D1/D5 and withdrawn FN-3I-010/pc remain review, and
this increment does not certify all late pages or E-infinity.

### 12.9 Local table_Q8 comparison and verified two-sigma d21 (2026-09-21)

Read the entire local `REU Projects/table_Q8.tex`, SHA256
`b5923f0328b9cbf71866779b74af49518e035c7d1584d4dd662f937db0df5bac`.
The source is a local summary, not an automatically superseded document.
Its two-sigma caption says `Need Correction!`; that warning does not reject
every formula or apply indiscriminately to the other sections. The new
`backend/data/review/table_q8_source_audit.v1.json` inventories all 49 active
RO differential rows: 18 two-sigma, 16 three-sigma, 15 mixed. Commented
two-sigma lines 374-375 are excluded explicitly. Published integer/sigma
rows remain in the separate DKLLW table inventory. This crosswalk is not
a production loader or a certificate that all 49 equations are proved.

FN-2I-019/020/021 are now independently verified. Each proof uses the
published integer Table 8 d23(D^-1 h1)=g6 D^-16 and an explicit finite
earlier-page quotient audit. The target is forced zero ON E23, so one
must enumerate incoming lengths below 23, not use a possible d23 as its
incoming arrow. No Jan29 or imposed vanishing-line premise is used.
Only permanent D8 (64 stems) and forward g=kD3 repetition are admitted.
There is no new D4 unit or inverse-g HFPSS period.

For FN019, multiply the integer d23 by the permanent Euler square.
Its source is already a Thom d3 boundary. At the target (54,26), primitive
d3 removes I62V and d5 leaves the kernel line I62X+I62Y, not a quotient
identifying X with Y. The sole surviving incoming source is the odd
h2kD7u constant at (55,5); FN005 already killed its double.

For FN021, an independent finite target audit proves H=h2u is a cycle
through d23, without asserting permanence. Multiplication by gH forces
h2k7D5u to be zero on E23. Its only earlier incoming map is d21 from
4k2D3u. Only the four constant maps, not its entire coefficient module.
The positive-filtration Tate seed 4ku -> h2k6D2u is now verified too.

For FN020, F=4Du is likewise independently checked through d23.
Its possible d21 target has only FN019's odd source left, so d21 squared
rules out that outgoing map; this is the sole late dependency, not a
circular use of FN020. The published d23 times gF forces the four
constant at (20,28) to be an earlier boundary. The r13 candidate is the
actual Euler image of the published permanent Q_sigma D3. Reduction
mod 2 is injective in its exponent-two cell, so the Euler product is
an actual identity, not merely a 2-BSS associated-graded assertion.
At low (1,3), the resulting d21 on X=x2h2u and Y=y2h2u has matrix [1,1].
Its kernel X+Y=e2h2 remains on E22. The high g translate had already
quotiented by X+Y; those two situations are not interchangeable.

The table supplies useful low representatives, now present in production:
line 407 is h2D4u (35,1) -> (x2+y2)k5D7u (34,22), and line 409 is
4D5u (40,0) -> h2k5D7u (39,21). Each source is separately checked through
E21 and then detected by its forward g or g2 product. In particular the
filtration-zero row does not use a blanket Tate-lifting assertion.
Retain the low h2D4u double, higher Witt layers of 4D5u, and its positive-j
ideal. Table line 408 is exactly FN020 by Dy2=h2^2, not an extra family.

The comparison also preserves genuine unresolved issues. Two-sigma line
373 omits the j factor in the primitive d3 target. Mixed lines 511-512
choose c=zeta and c+1=zeta^2, whereas formal_notes line 920 prints c=1.
Neither is silently assigned by this comparison. Five additional mixed
rows (528,533,537,538,541; lengths 11,17,19,19,21) are recorded with
formulas, degrees and periods as review-only inventory, not canonical
arrows. The three-sigma d23 at table line 474 has CORRECT bidegree
(12,0)->(11,23) and agrees with formal_notes; its issue is the withdrawn
proof, not transcription or degree. The same applies to the disputed
d19 dependency. Four stale mixed source-reference ranges and the grouped
FN-3I-010 range were repaired without admitting those claims.

Browser inspection exposed duplicate SVG strokes where high and low
anchors describe the identical certified map. `periodicDifferentials`
still returns every source claim. An SVG-only grouping step now requires
the same verified fact/certificate, resolved coefficient, exact endpoint
vectors, Witt/j ports, context and occurrence grades. It never merges
by geometry alone. Primary selection IDs remain; JSON alias IDs and all
source equations/proof references are retained. A real-browser check
caught missing HTML attribute quote escaping that a text-escaping test
double had masked. The fix and HTMLParser-based regression now check the
actual attribute semantics; both static copies match.

Final focused results cover 126 passing cases across 12 files, not a fresh
full-suite run. The quotient/admission set has 64 passes (153.11 seconds),
including ten new production-only d21 tests. The render/atlas/normalization/
crop/smoke set has 59 passes (193.34 seconds). After the final alias-escaping
fix and 49-row inventory expansion, both affected suites were rerun:
17 passes (7.16 seconds). Earlier four failures were stale review/conflict
and row-count expectations; their original report is retained. No test
admits review formulas or deletes maps in the new production fixtures.
All three two-sigma atlas images pass E22/E24 checks on a full D8 strip
through filtration 64: no surviving points at filtration >=23, no quotient
barriers or dangling endpoints. The separate no-arrow control restores
high-filtration points, excluding imposed clipping as the explanation.
All 14 atlas-transport tests (all sixteen charts) also pass.

Final local browser checks cover S20/S02/S22 at E21/E22/E24. At the same
fitted view E21 has 314 glyphs and 94 independent accepted arrows, retaining
182 source occurrences; E22/E24 each have 156 glyphs and no arrows. The
low Euler-product kernel was explicitly observed. Every displayed d21
period is 64, and the console has no warnings/errors. Ten JS syntax checks,
Python compilation, whitespace checks, and all six static mirror pairs pass.
The service remains on 127.0.0.1:5078. Saved `backend/data/project.json`
SHA256 remains `AC42D987D1707C981AFC2B0B8C429250D75E1B180A12EFA4F7D1D11390153805`;
no research TeX, saved project, commit or remote was changed in this increment.
Mixed coefficients and later claims, and the withdrawn three-sigma late
proof, still require independent resolution; the overall goal remains open.

### 12.10 Local table comparison: all four mixed Phi d9 blocks (2026-09-21)

Continued the user's explicit `REU Projects/table_Q8.tex` comparison. The
49-row RO crosswalk still covers 18 two-sigma, 16 three-sigma and 15 mixed
active rows; matching a printed formula is not itself mathematical admission.

Table lines 520-521 now have all four independently verified mixed Phi
anchors, rather than only the even D blocks. Write B=(x+y)u_mix and
R=x2h1u_mix. The newly admitted maps are d9(Bh1D)=Rk2D2 and
d9(Bh1D5)=Rk2D6, at (8,2)->(7,11) and (40,2)->(39,11). They link to the
already verified pure-three-sigma C D7 and C D3 maps, respectively.
omega2(D)=zeta D contributes one relative zeta regardless of the D
exponent; a_sigma_j*C_k=zeta*B*h1 and a_sigma_j*B_k*h1=R cancel it.
The common invertible Thom unit acts by the same scalar on the two
order-two, j-annihilated lines. The source coefficients resolve to one
from the pure-sector basis, not a new mixed-local coefficient assignment.

Each Phi map retains its live external source-admission/parameter gate,
permanent inverse-Phi comparison and exact finite target-survival proof.
The S73V bo direction has supported d3; it is not the surviving finite
S73 target. The possible incoming S00 d3 is zero by d3 squared, the d5
source is empty, and both layers of the incoming S40 d7 slot die by d3.
The odd sources now also have scoped outgoing d7=0 certificates. These
do not make them permanent or protect them from incoming maps. D0/D4
and D1/D5 are separate D8 families with forward g; together they give the
table's 32-stem repetition without treating D4 as an E9 or permanent unit.
No Jan29, Ck permanence, vanishing-line clipping or historical wrong Phi
identity is used. All six mixed atlas images inherit the change.

The coefficient audit does NOT settle c or b. Formal's annihilator
argument now has the independently verified omega(FN-2I-010) d9 premise,
but only forces c nonzero. Table511/512 chooses c=zeta and c+1=zeta2;
formal920 prints c=1, which would make the even map zero by Leibniz.
For b, formal961's two choices P or P+Q omit P+zeta Q and P+zeta2 Q in
the mixed F4 basis. Its H2-cycle subpremise can now be independently
repaired by FN-2I-009, the negative-source Tate d11 translated by
g^-3 D8, and omega. This does not select b=1 or admit FN-MIX-005.
The live proof metadata and table inventory distinguish that verified
subpremise from the unresolved whole claim. Five additional table-only
d11/d17/d19/d19/d21 rows remain review-only; no new arbitrary deaths.

Changed files in this increment: backend/domain/formal_notes_chart.py;
backend/data/review/table_q8_source_audit.v1.json; tests/test_mixed_phi_d9.py;
tests/test_verified_mixed_phi_d9.py; tests/test_table_q8_source_audit.py;
tests/test_thom_formal_chart.py; and this RECORD.md. No static implementation
changed; all six backend/public mirror pairs remain identical.

Validation: 178 distinct passing cases across ten focused test files, not
a fresh full-suite run. The Phi/table/formal set passed 63 tests in
78.81s; the atlas/Galois/mixed/table-ledger/smoke set passed 125 in 253.76s.
The source audit expanded from ten to twelve cases during this increment;
after the final live mixed-subpremise assertions, table/formal metadata
were rerun together: 33 passed in 15.96s. Reports are
tmp/pytest-mixed-phi-table-2026-09-21.xml,
tmp/pytest-mixed-phi-regression-2026-09-21.xml, and
tmp/pytest-mixed-table-metadata-final-2026-09-21.xml. The unmodified
production runtime tests cover all four exact finite source/target pairs,
each D8/forward-g translate, all six mixed images and E9-to-E10 quotient.
Negative tests still reject missing source admission, conflicting pure
coefficient assignments and mixed-local overrides. The separate P/Q/jQ
uncertainty is retained, not silently closed by the Phi certificates.

The computer-use workflow reloaded the local service and inspected all
six mixed atlas images. At the same fitted E9 view each showed the four
Phi branch counts 28/27/28/28; at E10 no Phi arrows remained. The base
chart's glyph count changed from 1594 to 1385 at that fitted view. Console
warning/error output was empty. The tab is left at the base mixed E9 in
normal 100-percent view for manual checking. Ten JS syntax checks, Python
compilation and whitespace checks passed. Source table SHA256 remains
b5923f0328b9cbf71866779b74af49518e035c7d1584d4dd662f937db0df5bac.
Saved project SHA256 remains
AC42D987D1707C981AFC2B0B8C429250D75E1B180A12EFA4F7D1D11390153805.

No research TeX, saved project, commit or remote was changed. The overall
goal remains open pending the mixed coefficients/later rows and the
withdrawn-proof late three-sigma claims.

### 12.11 Corrected mixed d11 coefficient and two independent D8 branches (2026-09-21)

FN-MIX-006 is independently verified with coefficient zeta^2, not the
printed coefficient 1: d11(x^3 D^p u_mix) = zeta^2 (x+y)h1 k^3 D^(p+1)
u_mix for p=2,6. The rotated pure FN-2I-009 source and target have the
same omega unit; the finite Euler product E A_j = zeta x^3 u_mix supplies
the inverse source unit. The two seeds are (13,3)->(12,14) and
(45,3)->(44,14), each with its own D8 period. Their pairing at stem32
does not assert that D4 is a permanent unit. Source and target survival
are separately checked through E11, including the incoming d3/d5/d7/d9
cells; the proof does not require a mixed c or b assignment. The printed
formula and its conflict remain in the source audit, not overwritten.

The extra table_Q8 row528 remains review-only. On c=1,b nonzero its
proposed target is already a d9 boundary; this does not assert the same
conclusion on every other coefficient branch. Added source proof and
coefficient provenance in formal_notes_chart.py, the periodic fate ledger
and table_Q8 source audit, plus tests/test_verified_mixed_d11.py. Updated
the existing formal, closure, Galois and table tests. A misleading tooltip
that called this fixed unit unresolved was corrected.

Validation before the subsequent UI increment: 102 passing focused tests
in tmp/pytest-mixed-d11-regression-2026-09-21.xml, then 50 passing atlas,
Phi, smoke, render-alias and d11 checks in
tmp/pytest-mixed-d11-atlas-final-2026-09-21.xml (199.80s), with eight cases
rerun: 144 distinct tests across eleven files. This was not a full-suite
claim. Saved project hash remained
AC42D987D1707C981AFC2B0B8C429250D75E1B180A12EFA4F7D1D11390153805.

### 12.12 Explicit atlas labels, uncluttered controls, and selected period copies (2026-09-21)

The five computed representatives and eleven transported pages are now
separate workspace groups. Atlas paths use compact gradings, with omega
and psi composed right to left. S11 is the forward omega-squared image
of S30 followed by stem +16 (the user's reverse comparison has -16).
S32 is obtained from S12 by psi and stem -32; the reverse comparison is
+32. Under psi=(j k), the proposed intermediate S21-to-S12 step is
omega psi, not psi alone. Source-declared 20+H normalization obligations
remain recorded; this display change proves no additional Picard theorem.

actions.py and atlas_transport.py now expand supported expressions rather
than placing omega/psi wrappers on point names. Scalars use zeta^3=1,
psi applies Frobenius once, and integer/Witt factors 2 and 4 are retained.
The path-induced Thom basis and original Picard multipliers are recorded
separately. Unknown source placeholders are not given invented formulas.
Differential.display_coefficient records presentation-only basis changes;
runtime matrices and shared parameter assignments are not rewritten.
Mid-arrow coefficients refer to unscaled expanded generators, while point
labels retain the full transported elements. Equal endpoint units cancel;
1 is omitted. Unresolved scalars display ?, and component maps display
vector rather than a spurious overall scalar. Matrix-backed maps require
their effective image, not merely a raw target-label unit.

Removed the unused page-period, vanishing-line and legacy-period drawing
panels and the 4-by-4 badge. Advanced commands sit under More. The 21-file
archive is retained as collapsed reference material. Show Differentials
counts and displays all stored chart differential records, including the
formal-note entries, with source/status evidence retained inside the list.
Class labels and formula-bearing lists use escaped, trust-disabled KaTeX.

Point radius is now uniform at a given chart scale, including anchors and
virtual copies; finite 2-tower levels use the same ordinary dot radius.
Packing reserves their complete glyph envelope. The small triple in the
reported screenshot came from that finite-tower rendering branch, not a
different class of smaller generators. A selected periodic occurrence now
stores its own label, grade and instance key. Only that occurrence receives
the full high-k/D label and bidegree; family highlighting remains intact.
The inspector's Grade uses the selected occurrence, and unchanged basis
provenance is explicitly labelled Family anchor. Changing workspace/page
does not reuse a stale occurrence as the current point.

Browser checks on localhost: all sixteen E3 tiles render without action
wrappers or KaTeX errors, with correct active tile/page. All six mixed E11
images show the corrected coefficient (zeta^2, or zeta after reflection);
E12 does not draw E11 arrows. Research/Review lists render math without
console errors. The actual selected integer point k^2 v1^2 h1^2 D^(-1)
at (-10,10) displays that name and grade, while its family remains selected.
The local tab remains available for manual inspection.

The full initial run completed with 1041 passed and 4 failed in 7459.22s
(tmp/pytest-atlas-display-full-2026-09-21.xml). Two failures exposed the
same migration regression: a second migration generated 31 redundant
E2-import source claims. Cleanup now requires an exact deterministic
transport ID, Thom rule and managed endpoints; manual/unmanaged records
are preserved. The other failures expected obsolete omega wrappers and
the old packing-options string. Those tests now check explicit names,
original provenance, unchanged runtime coordinates and uniform packing.
On the final code, all 146 targeted cases passed in 30.42s, including all
four original failures and the new idempotence/selection cases; report:
tmp/pytest-atlas-display-final-2026-09-21.xml. This includes the complete
expanded-actions, display-conventions (35), UI-cleanup (6), table-ledger
and interactions files. The entire suite was not rerun after those fixes.
All seven mirrored static pairs match; all twelve JS syntax checks and
git diff --check pass. Saved project SHA256 is unchanged:
AC42D987D1707C981AFC2B0B8C429250D75E1B180A12EFA4F7D1D11390153805.
No research TeX, saved project, commit or remote was changed.

Files for this UI/action increment: backend/domain/{actions.py,
atlas_transport.py,models.py}; backend/templates/index.html;
backend/static/{app.js,cell-layout.js,style.css,table-ledger.js} and their
public/static counterparts; tests/{test_expanded_atlas_actions.py,
test_chart_display_conventions.py,test_chart_ui_cleanup.py,
test_table_ledger.py,test_interactions.py,test_thom_formal_chart.py};
and this record. Earlier uncommitted research/backend changes are retained.

### 12.13 Conditional mixed numerator and hybrid endpoint check (2026-09-21)

The two PD2/PD6 Euler-image equations no longer introduce an independent
unknown gamma. FN-2I-016 has independently verified coefficient 1 in each
pure block. Omega contributes the ratio zeta^(2m+2)/zeta^(2m)=zeta^2;
the common transported Thom unit cancels. Exact Euler multiplication gives
P=(yh2+xh1v1)u and T=(x+y)h1^2u without another unit. Thus the conditional
P numerator is zeta^2 (encoded 3), and the Q coefficient is zeta^2/b.
The two blocks remain separately sourced, not inferred by a permanent D4.
Neither c nor b is assigned: c=1 is still the finite-target condition;
for c=zeta or zeta^2 that target is already a d5 boundary. Their review
status remains unchanged. A conflicting override of the proved numerator
blocks the conditional computation rather than silently replacing it.

The local table audit records this numerator proof, the resulting
conditional obstruction to row528, and partial row537/541 information.
Row537 is NOT forced by the vanishing line: h1k5D6u_2j equals
g5D^-16(h1D7u_2j), whose pure source supports d7. Its Euler image has
no such d7 output, but this does not prove every later output zero.
For gT=(48,26), a possible d9 to Rk8D10=(47,35) remains unresolved;
the proposed incoming d19 source (49,7) also has a possible prior d5
from the QD6 direction (50,2), unless its nonzero-b premise is established.
The row541 Euler-product calculation certifies outgoing behavior only,
not the proposed unique incoming differential. All five late historical
rows retain runtime_admission=false.

The 3sigma D5 d23 block also remains review-only. Although earlier
outgoing maps of 2UD5=(44,0) can be excluded independently, its target
Rk5D8=(43,23) has two still-unexcluded incoming ports: d7 from
2Uk4D7=(44,16), and d9 from Bh1k3D7=(44,14). A proposed cofiber proof
must additionally rule out hidden Euler extensions from positive-j
filtration-one preimages; an E2-zero Euler product does not suffice.
The D1 cycle certificate does not settle the distinct D5 block. The old
3sigma d19 target at filtration 21 is not above the filtration-23 line.
No new late arrow or disappearance is inferred from an omitted table row.

A separate renderer regression was reproduced and fixed: a review arrow
with one untyped/manual endpoint bypassed the typed endpoint's quotient
check. It could therefore still be drawn on E23 when that endpoint was
already a boundary on E4. Hybrid endpoints now receive independent
same-grade checks across all surviving 2/j layers; two typed endpoints
keep their paired map check. Surviving positive-j ideals are not confused
with their absent constant, and legal manual arrows remain available.
The regression suite checks both endpoint directions, scalar/vector
types, page transitions, unknown/known/Frobenius coefficients and D8
copies. Its sixteen grading shells are synthetic tests, not a proof of
every production atlas computation.

130 targeted tests passed in 58.16s, including mixed d9 closures, pure
normalization, coefficient runtime, published d23 ports, arrow cropping,
admission status and display conventions; report:
tmp/pytest-gamma-endpoint-regression-2026-09-21.xml.
In the actual browser, all sixteen production atlas pages were opened
at E23. Every arrow endpoint inside the visible chart coincided with a
displayed point; there were no stale selected-copy labels or KaTeX errors.
This is a rendering check, not resolution of the mathematical gaps above.

### 12.14 Selection geometry and current periodic names (2026-09-21)

The screenshot's small stacked dots are finite 2-tower levels. The
previous radius fix still allowed CSS hover/selection scale(1.24) to
enlarge the entire glyph beyond its reserved envelope. Highlighting now
changes color only, including the tower's currentColor children. It does
not change scale or stroke width, and semantic hollow/solid marks remain.
Ordinary points and finite-tower levels also share the same white 0.6px
stroke, including selection. A periodic copy no longer overrides its
anchor's stroke width, so equal radii have equal visible size.

Periodic names now multiply the WHOLE expression. A label xD+yD translated
by D8 is displayed as D^8(xD+yD), not the incorrect xD^9+yD. Numeric
outer D/k factors are combined when safe; factors inside grouped sums,
commands or symbolic exponents are not rewritten speculatively. Integer
coefficients remain at the front, unit 1 disappears, and no spacing macro
is introduced. Existing exact omega/Frobenius scalar handling is retained.

After a same-page project refresh, the selected occurrence is looked up
again at its actual bidegree. Its formula and instance key are refreshed
from the new model, or cleared if it no longer exists. The inspector no
longer keeps an old cached label while the chart shows a renamed class.
The selected occurrence and family highlighting remain separate.

Browser checks selected k^2 v1^2 h1^2 D^-1 at (-10,10), and the finite
tower k^3 h2 D at (-1,13). The latter's two same-family occurrences had
blue children, transform:none and the same circle radius as ordinary
dots. Both labels were rendered by KaTeX, with the actual bidegree below.
The selected-point focused run passed 182 cases in 5.05s, including the
new expression/refresh and CSS tests, interactions, hybrid endpoint tests
and table-source audit; report tmp/pytest-selected-point-final-2026-09-21.xml.
The combined final run on the completed code passed 266 tests in 60.16s:
tmp/pytest-verified-gamma-selection-final-2026-09-21.xml. Final browser
computed styles confirm ordinary and selected tower dots both have radius
1.659px and white stroke 0.6px at that view, with transform:none; the
selected k^3 h2 D label and (-1,13) remain open for manual inspection.
Browser console warnings/errors and KaTeX errors were absent.
The whole suite has not been rerun since the initial run in section 12.12.
Seven static mirrors and all twelve JS syntax checks pass. Saved project
SHA256 remains AC42D987D1707C981AFC2B0B8C429250D75E1B180A12EFA4F7D1D11390153805.

Final browser handoff is integer E2 with the actual periodic occurrence
k^2 x^2 D selected at (-2,10). The visible KaTeX label shows that product
and bidegree, rather than the base representative. No KaTeX errors or
console warnings/errors were found. The local tab remains available.
No research TeX, saved project, commit or remote was changed.

### 12.15 Euler cycle images and the mixed nonzero parameter (2026-09-21)

Four new independently sourced outgoing-only certificates are installed:
DER-3I-EULER-H2/H6-cycle and DER-MIX-EULER-H2/H6-cycle. They multiply the
previously verified pure H2/H6 cycles by the permanent Euler class; the
mixed pair first uses omega. The exact product is the finite S02 port
(x+y)h1D^m u at (8m,2), m=2,6. Each has its own D8/forward-g certificate,
not a permanent D4 identification. The resulting eighteen atlas claims
constrain only outgoing maps. The existing 3sigma d9 and mixed d11 maps
into forward-g images remain valid; no zero arrow or extra independent
generator is introduced. In particular the possible d9 from Bh1k3D7 at
(44,14) into the disputed 3sigma D5 d23 target is now excluded. The
separate d7 source 2Uk4D7 at (44,16) remains unresolved; no late d23 is
promoted and the Jan.29 proof is still withdrawn.

The mixed b proof now starts with the entire F4 target space:
d5(B)=k(alpha P+beta Q), not the old binary list. The independent P map,
P=B h2, Qh2=0 and the surviving finite x3kDu target force alpha=0.
Assuming b=beta=0 makes B a 9-cycle. At W=Rk2D3=(15,11), the complete
earlier incoming inventory consists of d3 from (16,8), an entire
primitive d3 image; the empty d5 source (16,6); and the d7 source (16,4),
whose two S40 layers are already absent after primitive d3. Thus W is
nonzero in this branch. But V=Bh1D2 is the independent H2 Euler cycle,
while integer Table 8 and Leibniz give d9(V)=W. This proves b nonzero,
not its exact value. FN-MIX-005 remains review, b remains unassigned in
{1,zeta,zeta2}, and its coupled P+bQ quotient is not silently resolved.

This does independently verify FN-MIX-005-Q-zero: d5 squared gives
kD2*d5(Q)=0, and multiplication by kD2 is injective on the one-dimensional
candidate target x3kDu, not on the whole HFPSS. The extra Leibniz term
vanishes by Qh2=0, without declaring kD2 a 5-cycle. The zero claim extends
over all D exponents, positive j and forward g. Low-filtration positive-j
Q tails remain HFPSS classes; their negative-filtration Tate preimages
are not HFPSS arrows. Their positive-g images have genuine positive-
filtration primitive d3 preimages. The local table audit records the
nonzero-b repair while retaining the printed unit-1 equations for review.
It also closes row537's earlier incoming d5 from QD6, but the proposed
target's outgoing d9 remains unresolved; no d19 is forced.

The untouched production two-sigma audit passed 3 tests in 30.23s:
three atlas images, E22/E24, three D8 windows and filtration through 96,
including scalar ports/vector ranks, low Witt/j tails and a no-clipping
control. It retains production FN003's admitted status and leaves both
FN002 rows unadopted; this is not a new proof of those premises or an
automatic check of the entire multiplicative Leibniz algebra. The mixed
nonzero/Q-zero regression passed 40 tests in 111.82s. An isolated Euler
test fixture initially omitted the chart-algebra settings; retaining its
real settings fixed the fixture, and its counterfactual regression passed.

Browser checks opened all six mixed atlas images at E6 and all three
3sigma images at E9. No stale selection or KaTeX error appeared. A probe
of the actual local API data confirmed Q and jQ at (10,2) are live and
known cycles on E6, with no algebra conflict or barrier. Their CSS
unknown state describes unresolved final fate, not an unknown E6
quotient. The selected integer occurrence k3h2D with actual bidegree
(-1,13) is left open for inspection; family highlighting remains.

Final combined regression: 281 passed in 209.57s; report
tmp/pytest-euler-b-final-2026-09-21.xml. Seven static mirrors and twelve
JS syntax checks pass. This is a focused regression, not a new full-suite
run. Saved-project SHA256 remains
AC42D987D1707C981AFC2B0B8C429250D75E1B180A12EFA4F7D1D11390153805.
No research TeX, saved-project content, commit or remote was changed.

### 12.16 Exact-occurrence UI handoff (2026-09-21)

The selected ordinary/periodic occurrence and a read-only quotient
representative now have mutually exclusive selection state. Selecting
a quotient clears the former family/occurrence and its inspector;
selecting an ordinary occurrence clears the former quotient label.
Both static app.js copies contain the same change. The new async VM
regression follows ordinary -> quotient -> ordinary, checks the actual
k/D products and bidegrees, and verifies that model records are unchanged.

The local browser confirmed a three-level finite 2-tower at k^3D,
(-4,12): its individual circles and ordinary dots both have radius
1.659px and white stroke 0.6px at this view. These levels occupy one
bidegree; their on-screen vertical offsets are not filtration changes.
After reloading the updated app, the selected visible occurrence is
k^3x^2D^2 at (2,14), with one occurrence label and its two visible family
members highlighted. No KaTeX errors or console warnings/errors were seen.

Final focused display/selection/refresh regression: 132 passed in 4.55s,
tmp/pytest-current-selected-occurrence-2026-09-21.xml. Both app.js syntax
checks pass. This is not a full-suite or a new mathematical validation.
Saved-project SHA256 remains
AC42D987D1707C981AFC2B0B8C429250D75E1B180A12EFA4F7D1D11390153805.

### 12.17 Candidate maps, not placeholder coefficients (2026-09-21)

The frontend now queries candidateState against the actual current-page
quotient. An unresolved P+bQ is tested over its jointly legal finite F4
assignments, including affine/ratio parameters, Frobenius and linked-source
admission gates. It is no longer tested only as the placeholder P+Q. This
query does not assign parameters, admit review equations, or compute an
extra quotient. Conditional arrows stay review and their tooltip lists
surviving coefficient values. The renderer anchors them in an actual
surviving target branch; a factor on one vector summand is still labelled
as a vector parameter, never as a global arrow scalar.

Verified zero-outgoing certificates are compared with actual quotient
source vectors and their specified 2/j layers. A candidate may be
contradicted even though its source remains a genuine point. Such an
occurrence is not drawn as a viable differential, and the page explains
that the source and historical record were retained. Missing endpoints,
zero maps, unknown coefficients/quotients and contradicted candidates are
distinct states. A constraint on a linear combination does not constrain
each summand separately. Existing accepted-map conflict barriers remain.

The independent FN007 D3 and D7 rows also give two new outgoing-only
certificates, DER-3I-TATE-U-D3-cycle and DER-3I-TATE-U-D7-cycle. Only in
TateSS, multiplication by g^-3 D8 gives d9 sources at (29,-9) and (61,-9)
with targets 2UD3 at (28,0) and 2UD7 at (60,0). They repeat separately by
D8. Their positive-g images may receive genuine FN007 incoming maps;
they are not declared non-boundaries, and no inverse-g cancellation is
used in HFPSS. The previous section 12.15 unresolved d7 from 2Uk4D7
is now excluded by the first certificate. All eight U-cycle tests pass,
including three actual atlas images, E7/E9/E10, and preservation of the
original FN007 arrows and their forward-g images.

The saved-project E23 audit computes all sixteen real atlas workspaces,
not synthetic grading shells. Twelve d23 definitions occur in seven
charts. All nine published rows across the integer/sigma orbit retain
their 27 tested anchor/D8/g occurrences. The three transported withdrawn
FN010 rows retain their live finite 1:0 source at those translates but
are excluded by DER-3I-TATE-W-cycle; their other unproved D5-block
occurrences remain review. Nine charts have no d23 definitions and no
invented d23 arrows. Four actual-atlas tests pass in 28.36s. Browser
checks confirmed the three 3sigma images at E23 and conditional mixed
E5 arrows, without KaTeX errors. This does not settle all late claims.

Two stale REU Review summaries were also reconciled with the existing
implementation: C3 alone is insufficient, while omega psi transports
the mixed charts semilinearly; mixed formulas are individually verified
or reviewed, not blanket admitted. Exact legacy text is refreshed while
researcher custom text and fields are preserved. Thirteen summary/fact
chain/refresh tests passed in 20.71s.

Next mathematical item, audited but NOT registered in this turn:
for integer Z=xh1D5 and J=x2h1k2D6, M=g2D^-8 sends Z to
d9(h1D2) and sends the unique finite candidate target J to a nonzero
E9 line. This yields d9(Z)=0 by square-zero and finite target injection.
The product J=d*g2D^-8(h1D6) proves only its r<9 outgoing equations
vanish: h1D6 itself supports a NONZERO d9 (main1744-1753).
Euler detection then gives pure d9(CD5)=0, and the permanent
omega2/Phi^-1/a_sigma_j path gives mixed d9(Bh1D7)=0. Phi is the
actual unit N(dbar)*u4sigma_k*g^-1*aH of degree
-15+sigma_i+sigma_j-3sigma_k, not a bare graphical shift. Before adding
the mixed certificate, preserve all finite incoming inventories and do
not infer row537 d19 merely from this one outgoing obstruction.

The vector quotient now retains every valid target basis column used by
an active differential matrix, including coupled columns not listed in
the target's original e2_components. Invalid, unused, archived or
dimensionally inconsistent matrices do not expand the basis. Thirteen
focused matrix tests cover those controls.

Final combined regression: 266 passed in 167.05s; report
tmp/pytest-candidate-u-cycle-final-2026-09-21.xml. Six JS syntax checks
pass, and app.js, page-algebra.js and vector-page-algebra.js have matching
backend/public copies. This is a focused regression, not a full-suite
run or a proof of the unresolved late 3sigma/mixed claims. Saved-project
SHA256 remains AC42D987D1707C981AFC2B0B8C429250D75E1B180A12EFA4F7D1D11390153805.

### 12.18 Finite d9 zero maps and exact coefficient scope (2026-09-21)

The previous section's proposed CD5 / mixed BH-D7 obstruction now has a
shorter independently checked proof, also covering the separate CD1 /
mixed BH-D3 block. Put V=(x+y)h1u, C=(h1+xv1)u, R=x2h1u, U=v1^2u.
For m=1,5 separately, the independently verified V D^(m+3) d9, multiplied
by permanent M=g2D^-8, gives a nonzero d9 from V k2D^(m+1) to
Rk4D^(m+2). The former is the sole finite candidate target of CD^m.
Thus d9 squared forces d9(CD^m)=0. This does not use D4 permanence,
the Jan29 argument, clipping, or an inverse-g cancellation in HFPSS.

The nonzero R target is detected using the published 13-cycle
L=D^-1h1, with image W=2Uk5D^(m+1). The finite incoming-source inventory
for W is stored in the proof. In particular the potential incoming d7
source 2Uk3D^(m+1) at (8m,12) is NOT a missing class or a d5 boundary:
L sends it to zero, while L sends its proposed R target nontrivially to W.
The same finite detector excludes the possible outgoing d7 from R.
The runtime baseline confirms that both of these constant two-layers
remain on E7 and E9. The proof excludes their proposed map, not their dot.

Permanent omega2/Phi^-1/a_sigma_j transport then gives mixed
d9((x+y)h1D^3u)=d9((x+y)h1D^7u)=0. Phi is the actual norm/Thom/Euler
unit recorded in section 12.17; comparison is used at target filtration
11, not as unjustified low-filtration injectivity. Its unknown common
Thom unit does not affect a zero equation. Four source certificates
produce eighteen records across the three pure and six mixed atlas
images. Each is page-nine-only, exact-port two0/j0, D8 with forward g,
not a permanent-cycle or a new nonzero arrow. Existing incoming maps,
positive-j families, coefficients and source records are retained.

A separate backend bug was found: zero-differential exact-port matching
ignored coefficient_scope and could cover unrelated higher two/j layers.
The fate guard now honors exact/constant/all scopes, including same-ID
endpoint copies and their actual grades. The JS guard now also honors
an explicit scope without a cycle_constraint field. Legacy zero maps
with neither field retain their existing module closure. The new scope
tests plus existing fate/candidate/cycle regressions passed 150 tests.

The first source/atlas regression ran 61 tests: 58 passed, three older
test expectations required review (two added pure zero records, and two
stale claims that the repaired nonzero-b premise was still TBD).
No mathematical assumption or coefficient was changed to satisfy them.
Final regression results are recorded below when complete.

Final mathematical/source/scope regression: 228 passed in 161.42s;
tmp/pytest-finite-square-zero-final-2026-09-21.xml. This includes the
new actual-atlas tests (17 passed separately in 53.79s) and the repaired
21-test formal-chart expectations. It is a focused run, not a full-suite
or a proof of the remaining late differentials. The live local API
contains all eighteen new records. Browser checks opened all six mixed
and all three pure atlas images on E9 without KaTeX or console errors;
CD remained visible through E10. The selected forward-g/D8 image of
CD5 has the actual label k(h1+xv1)u_3sigma_i and grade(-3,5).

Next item, read-only audit and NOT registered in this turn: local table
row533 may now be forced with a nonzero unknown F4 unit, not printed 1.
Put V=(x+y)h1u, T=Vh1, X=x3u and S=g6D^-16(VD3)=Vk6D5 at(16,26).
The proposed low equation is d17(VD3)=lambda Rk4D5, lambda nonzero.
Incoming odd-page sources to S, at(17,26-r), are excluded as follows:
r3 Xk5D5 zero3; r5 Uh1k5D4 primitive3 source; r7 Tk4D4 is c*d5 image;
r9 Ck4D4 constant3 source and positive-j3 image; r11 Xk3D4 is d5 image;
r13 Uh1k3D3 primitive3 source; r15 Tk2D3 is a (c+1)d5 image if c!=1,
or the independently proved gamma=zeta2 PD2 d9 image if c=1;
r17 Ck2D3 constant3 source and positive-j3 image; r19 XkD3=gX is
permanent because X=a_i*a_j^2; r21 Uh1kD2 primitive3 source;
r23 TD2 is the Euler-H2 cycle times h1. Even pages are empty by parity.
Outgoing r3/11/19 have empty targets; r5/13/21 target primitive3 images;
r7/15/23 target finite B classes supporting nonzero d5 (only b!=0 is
needed); r9 is zero by the new certificate. Only d17 remains, to
Rk10D7 at(15,43). The RO strong vanishing line would force it nonzero.
Before implementing, recheck the conditional c=1 Euler premise and every
finite inventory against the sources; do not infer them merely from the
partial runtime quotient. Source anchors: table_Q8.tex:533,
formal_notes.tex:881-951, DKLLW main.tex:1179-1198,1311-1315,1972-1976.
Row537 is still not forced: the independent VD7 d17 residue, at(56,2)
to Rk4D9 at(55,19), remains possible. Do not transport row533 by D4 or
use the unproved row538 to remove its target.

Selected-label browser follow-up: fixed the remaining right-edge clipping
in both app.js copies. After KaTeX, the full name and bidegree are measured
in local SVG layout units. Labels switch sides and stay inside all four
viewport edges; only an oversized label is scaled, never the point.
Repeated layout clears the previous scale so resizing cannot accumulate
shrinkage. No class, differential, selection family or saved data changes.
The 148 display/selection/refresh/bounds tests passed in 6.12s; report
tmp/pytest-selected-label-bounds-final-2026-09-21.xml. Both app.js syntax
checks and git diff --check passed (existing project CRLF warning only).
Browser verification placed CD at (9,1) to the left of its right-edge
point, with its complete typeset name and bidegree visible. The final
integer E2 view selects k^3 h2 D at (-1,13), retaining family highlighting.
Its finite two-tower circles and ordinary dots share radius 1.659 and
white stroke 0.6px at this scale; selected transforms are none. Tower
offsets remain within one bidegree, not additional filtration levels.
No KaTeX errors or console warnings/errors were observed. Saved-project
SHA256 remains AC42D987D1707C981AFC2B0B8C429250D75E1B180A12EFA4F7D1D11390153805.

### 12.19 A verified mixed d17 with an unassigned nonzero unit (2026-09-21)

The row533 proposal in section 12.18 is now independently checked and
implemented as DER-MIX-D17-V-D3 / formal_diff_mixed_d17_v_D3_forced:
d17(VD3)=lambda_17 Rk4D5, V=(x+y)h1u, R=x2h1u,
u=u_(sigma_i+2sigma_j). Source/target are (24,2)/(23,19), both finite
two0/j0 lines. lambda_17 is in F4* and remains unassigned. The historical
printed coefficient 1 in table_Q8.tex:533 is NOT thereby verified.
Its source-audit entry links the independently proved nonzero statement
without promoting the old printed equation or any other late mixed row.

The complete proof is stored with the claim. It uses the actual high
source S=g6D^-16(VD3)=Vk6D5 at (16,26), the incoming inventory in
section 12.18, and exclusions of every outgoing odd length except 17.
The c=1 branch was rechecked against formal_notes.tex:450-470,520-526,
734-739,881-951: omega and a_sigma_i give d9(PD2)=zeta2 Tk2D3,
independently of b, row533 and Jan29. For c!=1 the same finite target
is already the (c+1)d5 image. No actual c or b is selected.
The strong RO vanishing line then forces the nonzero d17. The high
target is Rk10D7 at (15,43); its other S73V direction is a primitive
d3 source, not a second target. The multiplier g6D^-16 is itself the
integer d23(D^-1h1) target, so it is not treated as an HFPSS unit.
Survival of S is established separately. High nonzero forward translates
are detected by positive-filtration Tate comparison (filtrations 26/43
are above the E17 comparison threshold 16); lower translates are detected
by the high one. The separate VD7 residue is not inferred using D4.

JS page algebra now exposes unitInvariant(diff) for an accepted,
certified, isolated finite one-dimensional F4 map. This permits its
kernel/image calculation while coefficientState still reports the unit
as unresolved. The representative unit used internally for that isolated
kernel/image is not persisted or presented as the coefficient. The gate
rejects coupled parameters, affine/component/linked expressions, vector
or matrix incidence, nonfinite ports, invalid coefficients and actual
same-page periodic endpoint collisions; earlier zero-outgoing and
square-zero guards remain in force. The backend fate guard applies the
same narrow principle and requires project period-family context.
Neither path generalizes this to Witt towers or j-adic modules.

The chart retains a solid accepted d17 and typesets lambda_17 at its
midpoint. The six mixed atlas images retain their actual transported
point labels; midpoint labels are respectively lambda_17, zeta lambda_17,
zeta2 lambda_17^2, zeta2 lambda_17, zeta lambda_17^2, lambda_17^2
for S12,S13,S21,S23,S31,S32 in that order. No scalar assignment is made.
Backend/public copies of app.js and page-algebra.js remain identical.

Validation: the combined source/quotient/fate/candidate/actual-atlas d23
and 2sigma regression passed 359 tests in 121.21s, report
tmp/pytest-mixed-d17-integration-2026-09-21.xml. The new actual-model
backend integration separately passed 12 tests in 2.07s. The existing
actual mixed chart test covers 60 source/target pairs (six atlas images,
ten D8/forward-g translates), E17/E18/E24, independent VD7 and positive-j
controls. Browser checks opened all six mixed atlas images: the exact
representative source and target appear at E17 and are absent at E18;
coefficients have the expected conjugation and basis factors, with no
KaTeX or console errors. Four JS syntax checks and git diff --check pass
(only the pre-existing saved-project CRLF warning). Full-suite results
are recorded separately when that run finishes; these focused tests do
not establish the unresolved late 3sigma/mixed convergence claims.

Read-only user-annotation follow-up: the two 3sigma E9 arrows at source
(-14,2) really share target(-15,11). They are the independent P/Q D6
rows translated by permanent D^-8, not duplicate labels. At low
filtration the constant-layer matrix is [1 1], retaining
(P+Q)D^-2=(yh2+h1^2)D^-2u plus the separate positive-j Q ideal on E10.
The actual user browser and seven even-d9 regressions confirm that
quotient. Only at forward-g higher filtration does an earlier d5 make
P=Q, so that high case must not be substituted for the low source cell.
No source data was changed for this annotation; its E9 view was restored.

Saved-project SHA256 remains
AC42D987D1707C981AFC2B0B8C429250D75E1B180A12EFA4F7D1D11390153805.

#### Follow-up finite 3sigma audit (read-only; not yet materialized)

Write u=u_(3sigma_i), T=(x+y)h1^2u, V=(x+y)h1u,
R=x^2h1u, U=v1^2u and g=kD^3. For m=1 and m=5 separately,
TD^m=(VD^(m-1))(Dh1). The independently verified V-D0/V-D4 d9
rows and Table 8 d9(Dh1)=xh1*k^2*D^2, together with the actual
products R*h1=V*xh1=2kU, give two equal Leibniz terms
2Uk^3D^(m+1). Their sum is zero. This proves only the outgoing
d9(TD)=d9(TD5)=0 on the finite S13:0:0 line; it neither assigns
permanence nor removes the possible S40:1:0 target. The two proofs
do not assume D4 permanence. Eventual materialization should use
separate D8 blocks and forward g, with exact-port regression tests.

For W5=2UD5 at (44,0), the finite audit excludes outgoing r<23
and filtration zero excludes incoming maps. This is not a proof of
nonzero d23. The high class Z=g^6D^-16 W5=2Uk^6D7 at (36,24)
still has two unexcluded earlier incoming possibilities:
d11(Ck^3D6)=Z and d21(XD5)=Z, where C=(h1+xv1)u and X=x^3u.
The first corresponds to d11(CD5)=2Uk^3D6. The vanishing line
therefore does not select d23(W5) uniquely. The proposed target
Y=Rk^5D8 at (43,23) reaches E19, but its possible outgoing d19
to [P]=[Q]k^10D10 and d23 to Ak^11D11 also remain unexcluded.
Do not mark Y permanent or restore the withdrawn January premise.

Sources rechecked: formal_notes.tex:678-705,730-780 and DKLLW24
main.tex:1095-1111,1179-1190,1694-1702,1889. These are research
audit results, not changes to the live model or research TeX.

A further detector check does not exclude d11(CD5)=lambda*2Uk3D6.
Euler multiplication into 4sigma sends the source to xh1D5u4sigma
(equivalently cD4u4sigma), but sends the entire finite target line
to zero. Multiplication by h1 or h2 also sends the target to zero.
For ordinary C4 restriction, write the target as (Xh2)k2D6 and
X=a_sigma_i*x2u2sigma_i. The kernel-subgroup restriction of Euler
is zero. At the other two C4 subgroups, the order-two part of
H2(C4,pi0 E)=W[[mu]]/(4,2mu){a_lambda/u_lambda} is annihilated
by a_sigma, using 2a_sigma=mu*a_sigma=0. Thus these restrictions
do not inject on the candidate target. This is an E2 statement,
not a claim about exotic restriction. Sources: main.tex:715-721,
869-878,1095-1111,1179-1190; existing Euler product certificate
in formal_notes_chart.py. No additional d11 is admitted.

#### Completed full integration and expectation repair

The unchanged-source full serial run completed with 1472 passed,
2 failed, 0 errors and 0 skipped in 2157.83s (35m57s), report
tmp/pytest-full-d17-integration-2026-09-21.xml. It includes all
12 actual-model mixed-d17 backend tests. The failures were two
old expectations after the independent nonzero-b/Q-zero repair:
test_formal_closures.py still required literal '[TBD]' in the
blocker text, and test_verified_mixed_phi_d9.py still required a
proper-subspace d5 barrier on Q after its zero map was proved.

Only those two test files were changed after the full snapshot.
The replacements require the actual verified nonzero-b certificate,
domain [1,2,3], no assigned value, the printed FN-MIX-005 equations
remaining review, and the independent finite-target-injection
certificate for zero d5(Q). They retain the exact Phi-arrow page,
source/target and source-linked coefficient assertions. The rerun
of both complete modules plus test_mixed_b_nonzero_certificate.py
passed 25 tests in 34.74s; report
tmp/pytest-d17-full-followup-2026-09-21.xml. Runtime source files
did not change between these runs. This is a full run followed by
a focused repair/rerun, not a second all-green full-suite run.

All four app.js/page-algebra.js syntax checks and mirrored-file
hashes pass, as does git diff --check apart from the pre-existing
saved-project line-ending warning. The saved-project hash remains
the value recorded above. The independent audit tab is left on
mixed E17 with lambda_17 midpoint labels and no console warnings
or errors; the user's 3sigma E9 tab was not changed. The finite
TD/TD5 zero-d9 certificates above remain the next materialization
step, and late 3sigma/mixed convergence is not declared complete.

### 12.20 Finite TD zero maps, an independent XD5 cycle, and committed-page display (2026-09-21)

The preceding read-only TD/TD5 audit is now materialized. The two
independent facts DER-3I-LEIBNIZ-TD1-D9-zero and TD5-D9-zero constrain
only the finite S13:0:0 outgoing d9. Both Leibniz terms are retained in
the evidence, and their sum is zero by 4kU=0. Each repeats by D8 and
forward g, not by assuming D4 permanent. All three 3sigma atlas images
carry the facts; no fake zero arrows are drawn and the potential
S40:1:0 target is not removed. Nonzero TD3/TD7 remain controls.

An independent Euler argument now certifies DER-3I-EULER-XD5-cycle,
the low finite X*D5=x^3D5u_(3sigma_i) at (37,3). The complete C4
stem-36 calculation uses BBHS20 pp.3454-3457,3464-3471, Propositions
5.21,5.24,5.27,5.28 and Tables 4/5, not visual extraction of a chart:

- The positive-filtration E2 families are b_n=epsilon^n*kappa_bar*
  Delta1^(2-n) in filtration 4+8n and the eta^2 family in 8+8n.
  The latter has injective d3. The former has E6 terms W/4{b0},
  F4{2b_n} for odd n, and F4{b_n mod 2} for even n>=2.
- After d7 only 2b0 and b_(2+4r) remain. The permanent-multiplier
  translates of d13(Delta1*nu*varpi)=epsilon^2 account for every
  b_(2+4r). Thus the only positive-filtration E-infinity detector
  is 2*varpi^2*Delta1^3 in filtration 4; separated convergence gives
  F5 pi36(C4)=0. In particular, varpi^6 is not an exotic receiver.
- The integer detector 4kD5=g*(4D2) is nonzero. Its only possible
  incoming d3 covers the positive-j ideal j*kD5, not the constant
  four-layer. Its ordinary restriction is zero in gr4, and the
  complete C4 filtration bound excludes a higher-filtration image.
- The index-two representation-sphere cofiber gives the exact
  groups pi_(40-3sigma_i) -> pi_(40-4sigma_i) -> pi36(C4<i>).
  The Thom unit has filtration zero and restricts to a unit, not
  necessarily 1. A preimage of the nonzero gr4 Euler image must
  have filtration <=3. At stem 37 the other low-filtration column
  S51 is the full j-series U*h1*D4 and has injective primitive d3;
  the sole remaining direction is the finite S53:0:0 line XD5.

This certificate excludes outgoing d21(XD5) without a January
premise. It is outgoing-only, not immunity from incoming maps:
g*XD5 at (57,7) remains the genuine d5(PD7) target and is absent
from E6 onward. There is no cancellation of g in HFPSS and no
claim that k separately survives. D8 translates and all three
atlas images are tested. The values of d11(CD5) and d23(2UD5)
are still unresolved; this does not establish late convergence.

The existing two-sigma hidden-h2 proof now records the actual
identity x^2*h2^2=4kD, separately from associated-graded relations.
The only candidate hidden y^2*h2^2 product has a different C3
weight from 4kD, so it is zero. Tests retain the target's actual
four-layer and this evidence through all two-sigma atlas images.

Display repairs: a single surviving finite Witt two-layer now
contributes its missing factor 2 to the actual periodic name,
without duplicating factors already in aliases or modifying F4
units, free Witt modules, multiple ports, or positive-j ideals.
Page changes are coalesced outside the select handler; pending
caption/status distinguish the requested page from the retained
SVG. The real page/workspace markers and final caption/status
are committed only after SVG replacement succeeds. Failure and
stale-workspace cases are covered by the scheduling tests.

Scheduling limitation: the pending state is written to the DOM,
but a single requestAnimationFrame does not guarantee that it is
painted before the synchronous calculation. Mock-RAF tests check
the state machine, not paint timing. Large-view calculations may
still block the main thread; this repair establishes correct final
commit state, not elimination of rendering stalls.

Serial integration passed 277 tests in 250.88s, report
tmp/pytest-euler-xd5-page-display-integration-2026-09-21.xml.
The earlier 244-pass/one-failure run exposed a stale exact count
of zero claims (24 rather than 26); its repair asserts both new
finite certificates in detail rather than relaxing the check.
New modules cover 14 Euler-cycle tests, 17 page-scheduling tests,
10 finite TD-zero tests and 32 surviving-port label tests.
The subsequent serial certificate/table/atlas run passed 165
tests in 533.17s, report
tmp/pytest-euler-xd5-certificate-table-atlas-2026-09-21.xml.
Together these are 442 passing targeted integration tests on
this source snapshot, not another complete-suite run.

Actual browser checks used a separate audit tab, leaving the
user's tab untouched. All three 3sigma atlas images were checked
at E9/E10 with the TD1/TD5 zero sources, their two potential
targets and the TD3/TD7 nonzero controls. Each actual SVG had the
matching committed page/workspace and aria-busy=false. XD5 was
present at E24 in all three images and its g-image absent; the
base image was also checked at E21. Selected labels showed
2k^3*v1^2*D6*u_(3sigma_i) at (40,12) and the transported
zeta^2*x^3*D7*u_(sigma_i+sigma_j) at (53,3). No console errors,
warnings or KaTeX errors remained. Initial refresh overlapped
the Flask debug reloader and was retried after /api/project
returned 200. Long Fit-view operations can exceed the browser
tool's command timeout; their committed DOM was verified rather
than blindly repeating the action.

Changed files in this integration: backend/domain/formal_notes_chart.py,
backend/static/app.js, public/static/app.js,
tests/test_three_sigma_td_zero.py, tests/test_surviving_port_labels.py,
tests/test_page_render_scheduling.py, tests/test_three_sigma_euler_xd5_cycle.py,
tests/test_thom_formal_chart.py and RECORD.md. Research TeX and
the saved project were not changed. The saved-project SHA256
remains AC42D987D1707C981AFC2B0B8C429250D75E1B180A12EFA4F7D1D11390153805.
Both app.js and page-algebra.js mirrors match, all four Node
syntax checks pass, and git diff --check reports only the prior
saved-project line-ending warning. The unlimited goal remains active.

### 12.21 Adjusted CD5 Euler cycle and an independent D5-block d23 (2026-09-21)

An independent certificate now treats C*D5=(h1+xv1)D5u_(3sigma_i)
at (41,1) as a completed F4[[j]] cycle. This is not the withdrawn
January Ck proof. Table 8 d9(D2h1), translated in Tate by D8*g^-2,
maps from (41,-7) to cD4 at (40,2); comparison proves zero HFPSS
outgoing, and low filtration excludes HFPSS incoming. The complete
BBHS20 C4 stem-40 calculation gives F2=F8=F4{epsilon*Delta1^4}
and F9=0. This detector is res(g^2)=kappa_bar^2. Subtract an
appropriate unspecified W(F4) multiple of g^2 from an actual
representative of cD4 to make its actual restriction zero without
changing gr2. Thus no exotic restriction coefficient is guessed.
The Euler cofiber, with the filtration-zero Thom unit restricting
to an unspecified unit, supplies a leading CD5 cycle. Its constant
term is nonzero because the Euler product annihilates the positive-j
ideal. Independently the Tate d3 from (42,-2) has image jCD5;
continuity includes that entire ideal. Subtracting it proves that
the constant CD5 and the whole completed series have zero outgoing.

The C4 enumeration uses BBHS20 pp.3454-3457,3464-3471, Propositions
5.21,5.24,5.27,5.28 and Tables 4/5. The positive-filtration stem-40
families are b_n=epsilon^(n+1)*Delta1^(4-n) in filtration 8+8n and
the eta^2 family in 4+8n. The latter has injective d3. On E6 the
former has b_n mod2 for even n and 2b_n for odd n. After d7 only
b_(4r) remain; permanent translates of the published d13 remove
all r>=1, leaving b0 in filtration8. This completes the filtration
argument, rather than inferring actual restriction from an E2 map.

DER-3I-EULER-CD5-cycle is outgoing-only, D8-periodic with forward g.
It does not restore incoming boundaries: g*jCD5 at (61,5) is an
actual primitive d3 image. Its two low ports survive, but only the
constant survives at that forward translate. One initial synthetic
test incorrectly mapped a finite j-annihilated source nontrivially
into F4[[j]]. That violated j-linearity. Replacing only that mock
source with a completed module repaired the test: a whole-series
image removes both ports, while a positive-j image leaves the
constant. The prior 119-pass/2-failure run is not an all-green run;
the two corrected tests subsequently passed, without a production
change made to accommodate the invalid mock.

Write U=v1^2u, C=(h1+xv1)u, a=(x+y)u, A=(x^2+y^2)u,
V=ah1, T=ah1^2, X=x^3u, R=x^2h1u, P=ah2, Q=Ch1 and g=kD3.
The separately proved equation is

    d23(2UD5) = R*k5*D8,  (44,0) -> (43,23).

It is DER-3I-LEIBNIZ-W5-D23, not a readmission of the old D1/32-period
claim. Put W=2UD5, Y=Rk5D8, L=D^-1h1, M=g7D^-16 and G=MW
at (56,28). The finite outgoing inventory proves W survives to E23:
the doubled d3 vanishes; the d5,d13,d21 targets have nonzero d5;
the d7 target is detected by L as the nonzero finite two-layer
2Uk2D5 at (36,8), whereas LW=0; the d15 target is already the
forward-g FN008 d9 image; d9/d17 targets are empty and d11/d19
target columns are full primitive d3 images. Even targets are empty.

Permanence of M gives zero outgoing on G before d23. Its independent
incoming inventory is complete: at r=3,9,11 use respectively zero
d3 on C, the finite TD5 zero-d9 certificate, and the CD5 cycle;
r=5 has the zero d5 X-row (also a same-page d5 image); r=7,15,23
have full S51 columns supporting primitive d3; r=13 has a nonzero
d5 source; r=17 and21 are genuine earlier d5 images; r=19 supports
the verified even-C d9. Thus G is nonzero on E23 before using the
new equation. In particular the r23 incoming source is Uh1*kD7
at (57,5), not an extra Witt two-layer.

Table 8 row22 gives d23(gL)=M. Since 2h1=0, (gL)W=0, so
Leibniz gives 0=G+(gL)d23(W). The sole remaining finite target
direction is Y; this forces its E23 presence instead of assuming it.
The actual hidden product Rh1=2kU gives (gL)Y=G, hence the equation
forces coefficient 1 in F4. Sources are DKLLW main.tex:1095-1111,
1914-1915 and the earlier formal_notes.tex:678-780 equations.
Two independent agents checked the noncircular order and the
outgoing direction of the translated equation. The runtime tests
check real finite inventories and earlier quotients; they are not
an independent implementation of the hidden multiplication proof.

The exact new map removes only source port 1:0 (the constant
two-layer); E24 retains 4W(F4)[[j]]+2jW(F4)[[j]]. Its finite target
is a boundary on E24. G itself supports an outgoing d23 to (55,51),
even when that target is outside the viewport. Multiplication by
the noncycle gL must not be used to invent an incoming arrow to G.
Only D8 (stem64) and nonnegative powers of g propagate this row.
The three relevant atlas images include the Picard stem+16 shift
and the explicitly expanded C3 coefficient factors. The D1 source
and its outgoing-zero certificate remain intact; the old D1 d23,
old FN010 d19 family and broad Ck assertion remain under review.
This is not a proof of all late 3sigma or mixed convergence.

SVG-only repair: the new proof explicitly authorizes FN010 as a
historical equation alias. A review occurrence shares a line only
with a unique verified owner having the same page, exact source
and target vectors, Witt/j ports, coefficient contexts, grades and
resolved scalar. Different sources with the same target are not
merged. Raw rows and mathematical admission are unchanged. The
verified line retains both IDs and clearly marks the old proof as
under review in its title. Conditional, component-parameter,
manual, different-equation and unadmitted cases stay separate.

Browser checks on an independent tab verified E23/E24 in *-3i,
*-3j and *-i-j, including low CD5, gCD5, W, Y and high G. Each
fit-view E23 chart now has 40 accepted lines, each retaining its
historical alias, instead of 40 accepted plus 40 review duplicates.
E24 has no such arrows, retains the exact Witt/j kernel and the
low CD5 series, and does not restore the positive-g j boundary.
Rendered page/workspace markers match and aria-busy is false;
there are no KaTeX errors or console warnings/errors. The user's
own tab was left untouched. A stale E12-only sidebar message was
also replaced, when later verified rows exist, with the recorded
differential range and an explicit non-completeness disclaimer.

Completed targeted results on this integration:

- 25 passed in 25.49s: independent inventory with the new conclusion
  and row removed from all images; report
  tmp/pytest-w5-d23-independent-inventory-2026-09-21.xml.
- 45 passed in 133.51s: new d23, CD5, strict SVG aliases and actual
  atlas d23 candidates; report
  tmp/pytest-w5-d23-cd5-render-atlas-integration-2026-09-21.xml.
- 30 passed in 3.24s: updated page-range text and page-commit
  scheduling; report tmp/pytest-w5-page-status-coverage-2026-09-21.xml.

A full serial pytest run is in progress, report target
tmp/pytest-full-w5-d23-integration-2026-09-21.xml. No full-suite
success is claimed here. The page-status wording and its new tests
were added after that run started; their separate focused result
above is therefore required even after the full run completes.

Files changed in this integration: backend/domain/formal_notes_chart.py;
backend/static/app.js and public/static/app.js; RECORD.md;
tests/test_three_sigma_euler_cd5_cycle.py;
tests/test_three_sigma_forced_d23.py;
tests/test_three_sigma_d23_inventory.py;
tests/test_actual_atlas_d23_candidates.py;
tests/test_differential_render_aliases.py; tests/test_page_status_coverage.py.
Both app.js syntax checks and mirror hashes pass; diff --check
has only the pre-existing saved-project line-ending warning.
The saved-project SHA256 is still
AC42D987D1707C981AFC2B0B8C429250D75E1B180A12EFA4F7D1D11390153805.
No research TeX, saved project, Git commit or remote was changed.

Remaining explanatory gap: the proof also forces zero outgoing
d19/d23 on Y, but these are not separately registered zero-map
certificates. Current quotients are correct; a future candidate
query can still need a more precise explanation. Do not convert
this observation into an unsupported global permanent-cycle claim.

### 12.22 Euler13 forces CD1 d11; exact dependent zero constraints

The preceding W5 explanatory gap is now closed by two separate outgoing-only
constraints, d19(Y)=0 and d23(Y)=0, on the exact S73 constant port. They depend
on the independently verified W5 d23 proposition in their own atlas workspace.
They do not certify permanence: Y is still its genuine incoming d23 image and
is absent on E24. Backend and browser cycle admission now recursively checks
explicit premise IDs, failing closed for missing/review/foreign/duplicate IDs,
dependency cycles and tombstones. Changes to premise IDs or proposition kinds
invalidate the page-algebra cache. Legacy certificates without declared
premises retain their previous behavior; ordinary differential admission is
not broadened by this change.

An independent source audit and a second mathematical review now force

    d11(CD)=2Uk3D2, (9,1)->(8,12),

where C=(h1+xv1)u_3sigma_i, U=v1^2u_3sigma_i and g=kD3. This is registered
as DER-3I-EULER-CD1-D11, not as admission of a historical graph-matching option.
The proof uses the actual Table 9 equation d13(eD4)=Theta, with e=a_sigma_i
and Theta=k3 C_sigma h1 D5, together with actual E2 products e^3=0 and
e^2 C_sigma h1=2kU. It follows that K=e^2Theta=2Uk4D5 at (28,16) is zero
already ON E13. Before E13 it has zero outgoing, being a product of cycles.
The sign-Euler cube has independent normalized-bar and integral-resolution
tests; the hidden h1 product is DKLLW main.tex:1094-1111.

All possible incoming sources for K before E13 are enumerated:

| Page | Source | Independent disposition |
| --- | --- | --- |
| 3 | Ck3D5 at (29,13) | d3(C)=0 |
| 5 | Xk2D5 at (29,11) | coefficient 1+5-6=0; also the same-page d5(PkD4) image |
| 7 | Uh1k2D4 at (29,9) | full primitive d3 source, not an extra Witt layer |
| 9 | TkD4=gTD at (29,7) | independently proved two-term Leibniz zero |
| 11 | CkD4=gCD at (29,5) | sole remaining source |

Even-page source cells are empty. Thus K is nonzero on E11 but must be an
incoming d11 boundary. The low CD source reaches E11 independently; its only
finite target W'=2Uk3D2 is nonzero because gW'=K is nonzero. This uses no
global cancellation or inverse of g. Naturality then gives nonzero d11(CD),
and the chosen psi-fixed pure bases force its F4 unit to be 1. The Witt
scalar 2 remains part of the target, not a field unit to discard.

Only the constant coefficient maps. Tate d3(k^-1 Uh1^2)=jCD has negative
source filtration (10,-2), so the positive-j HFPSS ideal has zero outgoing.
The independent exact-port zero DER-3I-CD1-D11-J-zero records that kernel.
Low jF4[[j]]{CD} remains on E12; forward-g positive-j images already bound
by primitive d3 are not restored. CD5 retains its separate full-series
outgoing-cycle certificate. Only permanent D8 and nonnegative g translate
the new equation; neither D4 nor an arbitrary negative g is inferred.

Consequently B6=Ck5D8=g5D^-8 CD at (45,21) supports d11 to (44,32).
It is absent from E12, including when its target is outside the viewport.
DER-3I-AD6-D19-zero therefore records d19(AD6)=0 at (46,2), with an actual
premise ID linking to the new d11 in each atlas. This does not decide the
distinct AD2 block. The old d19/d23 source records remain review: the
unresolved coefficient in d19(AD2)=epsilon Ck5D4 is not fixed by a high-g
vanishing argument, because d23(QD4)=g(Ck5D4) is an alternative possible
late incoming path. No January 29 proof or imposed vanishing-line truncation
is used by the new row.

Browser verification on the private localhost audit tab checked E11/E12 in
*-3i, *-3j, and *-i-j. The source/target are respectively (9,1)/(8,12),
(9,1)/(8,12), and (25,1)/(24,12). The latter two retain their transported
zeta weights. At E12 each target is absent and each low source retains only
its positive-j ideal. No KaTeX or console errors were observed. The preceding
W5 E23/E24 check also retained 4W[[j]]+2jW[[j]] and removed only Y's finite
incoming direction, with no duplicate historical/verified arrows. The user's
own browser tab was not changed.

Tests so far: premise-gate regressions passed 41 in 1.23s. A separate batch
of metadata, normalization, Euler-product and premise tests returned 90
passed/1 stale count failure in 56.96s; the corrected count test separately
passed in 2.82s. The new total is 40 source rows plus 41 derived rows, and
30 zero constraints in the two pure shifted source workspaces. This is not
a claim that a fresh combined batch passed. The independent CD1 inventory,
three-atlas runtime, W5 target consequences and naturality regression batch
is running as tmp/pytest-cd1-target-zero-integration-2026-09-21.xml.
The earlier full-suite run is still live; its eventual result does not by
itself cover these subsequently added rows and tests.

Files touched for this follow-up: backend/domain/formal_notes_chart.py;
backend/domain/fate.py; backend/static/page-algebra.js and its public copy;
tests/test_cycle_premise_admission.py; tests/test_three_sigma_target_zeros.py;
tests/test_three_sigma_d23_inventory.py; tests/test_three_sigma_cd1_inventory.py;
tests/test_three_sigma_euler_cd1_d11.py; tests/test_thom_formal_chart.py;
tests/test_pure_galois_normalization.py; tests/test_three_sigma_naturality.py;
tests/test_three_sigma_euler_cutoff.py; RECORD.md. Both page-algebra JS syntax
checks and mirror hashes pass. Saved-project SHA256 remains
AC42D987D1707C981AFC2B0B8C429250D75E1B180A12EFA4F7D1D11390153805.
No research TeX, saved project, commit or remote was changed.

#### Follow-up: complete same-page contradiction diagnostics

The CD1 integration batch finished with 95 passes and four failures in old
counterfactual/naturality expectations. Three assertions were updated to the
actual new d11 quotient. The remaining failure exposed a production problem:
validateKnownSources short-circuited the independent scalar-cycle and
square-zero validators, hiding additional contradictions on the same page.
Both static page-algebra copies now execute all three read-only validators
before rejecting the page. No invalid-page quotient is committed. Absent-port
diagnostics also identify their page explicitly.

The full old January assumptions are retained in counterfactual tests. Their
three independently checked obstructions are: the AD6 d19 target is absent
after CD1 d11; higher forward-g W1 d23 sources are already d11 boundaries;
and the surviving low W1 still contradicts its independent outgoing-cycle
certificate. IDs, degrees, coefficient ports, periods and atlas shifts are
checked, not replaced by a generic expectation of any conflict.

Validation at that revision: eight new synthetic diagnostic tests passed in
1.27s; convergence/naturality/Euler-cutoff tests passed 24 in 121.41s;
metadata, pure coefficient normalization and premise admission passed 79 in
34.21s. The preceding full run terminated with 1605 passed and two failures
in 4137.16s. Those two were stale derived-row counts and a d9-only coefficient
test that included the newly added W5 d23. Both are covered by the passing
79-test batch; the older full run does not cover subsequent production
changes or new tests. It is no longer running.

Browser reloaded the private localhost audit tab with the new JS, displayed
the verified W5 arrows on E23, and changed to E24 without page reset or
KaTeX/console errors. The user's own tab was not changed. Both JS syntax
checks and static mirror SHA256 comparisons passed. Changes for this
diagnostic follow-up: backend/static/page-algebra.js, public/static/page-algebra.js,
tests/test_page_validation_diagnostics.py, tests/test_three_sigma_convergence.py,
tests/test_three_sigma_euler_cutoff.py, and this record.

### 12.23 AD2 Euler-cofiber d19 and explicit late-source checks (2026-09-22)

The distinct AD2 branch now has its own source-backed record:

    d19((x^2+y^2)D^2u_3sigma_i) = (h1+xv1)k^5D^4u_3sigma_i,
    (14,2) -> (13,21).

Its ID is DER-3I-EULER-AD2-D19 / formal_diff_three_d19_a_D2_euler_forced.
Only the finite constant S62 -> S11 ports are involved. The positive-j
target ideal is already the primitive d3 image, not an additional d19
target. There are now 40 source rows and 42 derived rows. The original
FN010 d19/d23 family remains review; its same-equation AD2 occurrence may
share a rendered line, but its AD6 sibling is not admitted. Periods are
bilateral D8 (stem64) and nonnegative g=kD3, not a permanent D4.

The argument uses the Euler cofiber for ker(sigma_i)=C4<i>. BBHS20 Table 4
(upper integer-degree table, p3470) gives the entire pi13(E^hC4)=0, not just
an associated-graded entry. With the coefficient-base-change justification
recorded in the certificate, Euler multiplication from degree 16-3sigma_i
to 16-4sigma_i is injective. DKLLW Corollary 2.22 supplies the filtration-zero
unit u_4sigma_i and its inverse. In integer stem12, the sole filtration22
class xh1k5D4 is the genuine Table 8 d9 image of h1k3D3; higher filtrations
vanish by the strong vanishing theorem. Hence the whole F22 subgroup is
zero. If the finite class Ck5D4 survived, its Euler image would be zero,
contradicting injectivity. Enumeration of every earlier incoming source
leaves only AD2 d19. This is separate from the withdrawn January argument
and does not use global cancellation of g or a display cutoff.

The h1-product does not produce another nonzero arrow: its target
Qk5D4 at (14,22) is already d5(a k4D4), whose source is (15,17).
AD6 remains distinct because its possible d19 target supports the new
CD1 d11. No complete E-infinity or mixed-sector convergence is asserted.

Validation from the preceding implementation: the independent inventory
passed 21 tests in 18.72s after removing the new conclusion and structured
dependents from all three atlas images; the integration tests passed 20
in 31.53s; metadata/normalization/CD1 neighbors passed 61 in 73.59s.
The inventory verifies real finite quotients and witnesses, not the
topological cofiber or an infinite vanishing bound by itself. Browser
E19/E20 checks in *-3i, *-3j and *-i-j found the correct source/target
changes and transported arrow coefficients (1, zeta^2, zeta), without
KaTeX or console errors. Source summaries preserve the separate AD6 branch.

A subsequent six-file diagnostic-consumer run is terminal: 49 passed and
two stale expectations failed in 235.25s (tmp/pytest-ad2-diagnostic-consumers-2026-09-21.xml).
They concern the retained S62 family when an obsolete AD6 arrow has no
target, and an E24 expectation that would restore the CD1 d11 boundary.
These failures are being checked by exact occurrences, not waived. Thus
neither that batch nor the current full tree is claimed entirely green.

The user's E9 shared-target question was independently checked on the
negative D8 translate: P,Q at (-14,2) both map to T at (-15,11). The
constant matrix is [1 1]; E10 keeps P+Q and the positive-j Q tail, and
T is absent. Browser DOM confirmed that exact negative-stem kernel.
Two focused production tests passed in 14.83s; this read-only check did
not change the user's chart data or promote any mathematical claims.

Files for the AD2 increment: backend/domain/formal_notes_chart.py;
tests/test_three_sigma_ad2_inventory.py; tests/test_three_sigma_euler_ad2_d19.py;
tests/test_three_sigma_euler_cd1_d11.py; tests/test_thom_formal_chart.py;
tests/test_formal_closures.py; tests/test_three_sigma_d9_closures.py;
tests/test_three_sigma_forcing.py; and this record. Existing unrelated
worktree changes are preserved. No research TeX, saved project, commit
or remote was changed.

#### Exact-branch regressions and remaining mixed obstruction

The two failed expectations were repaired with exact witnesses, not by
relaxing the full counterfactual. The retained high S62 constants are
precisely (38,26), (58,30), (14,34), (34,38), the AD6 branch with only
port 0:0 and the matching absent-target d19 diagnostic. The actual CD1
d11 (29,5)->(28,16) removes only its finite Witt two-layer from E12.
The D5 sibling (60,16) remains. Another masked stale assertion also
incorrectly copied AD2's d19 at (26,30) to AD6 at (58,30); the revised
test distinguishes these. The two focused tests passed in 35.40s.

The saved-project E23 audit now checks all sixteen actual atlas workspaces,
not just demo or synthetic shells. In each three-sigma image it adds g3
and g4 observations: the old W1 sources are actual CD1 d11 boundaries,
while the low W1 sources remain and contradict the outgoing d23 claim.
The separate verified W5 d23 still has its exact live Witt two-layer and
finite target at all five tested translations. Earlier boundaries are
linked to real d11 edges, not arbitrary deletion flags. Neither status
assignments nor the saved project were modified by these audits.

An independent AD2 proof review reconfirmed the Euler degrees, BBHS Table4
upper table, finite source inventory and entire F22 subgroup argument.
The certificate now explicitly separates its completed base-change
auxiliary argument from the published Table4 result: equivariant coefficient
extension, finite-level completed cochains, Mittag-Leffler passage, and
uniform finite separated filtration are all required. Ordinary tensor or
an unrestricted interchange with infinite totalization is not claimed.
The S11 image remains conditional on the declared exceptional 20+H Picard
comparison already stored on the atlas; this proof does not promote that
comparison to a new theorem. A dedicated test retains its obligations and
checks normalized display units zeta^2 on *-3j and zeta on *-i-j while
the runtime transported coefficient remains 1. Browser E19 checks confirm
both midpoint labels and no KaTeX or console errors; the user's tab is
unchanged. Changing workspace restores that workspace's own saved page,
so the browser check explicitly selected E19 separately in each image.

The next genuine mathematical gap is TQ8-MIX-L0537, not an unrecorded
copy of VD3 d17. Its printed source (x+y)h2^2D3u equals x^3D4u at (29,3),
by DKLLW main.tex:943,949 and the finite module product. Its g-translated
proposed d19 target is (48,26), but that finite line may still support an
outgoing d17 to (47,43). The current mixed E24 quotient has both ports.
Note/record/note.tex:854-858 depends on graph matching and the preceding
argument's coefficient-sensitive P=Q assertion at line851. Formal notes
do not supply an independent late mixed proof, and published Table8 has
no d19 to transfer directly. Thus neither alternative has been admitted.

Updated the review JSON to move outgoing d9 of (48,26) to resolved
obligations, citing DER-MIX-PHI-BH-D7-D9-zero, and to record the real
remaining d17 alternative. Also corrected FN-MIX-004's stale scope text:
Q's zero d5 is now independently justified by FN-MIX-005-Q-zero, not by
applying a pure-sector argument to the mixed C class. These are provenance
corrections, not new nonzero differentials. A read-only source audit found
84 filtration>=23 points in mixed E24, stem40..64 and filtration0..44;
this is evidence of incompleteness, not permission to clip them.

Combined validation passed 87 in 99.59s, report
tmp/pytest-ad2-all-atlas-scope-2026-09-22.xml: actual sixteen-atlas d23,
AD2 integration and independent inventory, table-source audit, and mixed
d5 tests. A separate source/transport audit passed three tests in 100.68s;
neither result proves complete mixed convergence. The six-file late
diagnostic regression is still running under its existing handle at this
point. Both app.js copies and both page-algebra.js copies pass syntax
checks; the page-algebra mirrors match. Saved-project SHA256 is unchanged.

Files changed in this continuation: backend/domain/formal_notes_chart.py;
backend/data/review/table_q8_source_audit.v1.json;
tests/test_actual_atlas_d23_candidates.py;
tests/test_three_sigma_d9_closures.py; tests/test_three_sigma_forcing.py;
tests/test_three_sigma_euler_ad2_d19.py; tests/test_table_q8_source_audit.py;
RECORD.md. No research TeX, saved-project write, commit or push was made.

#### Mixed VD7 cycle and independently forced d19 (2026-09-22)

The previously running six-file diagnostic batch finished: 51 passed in
225.38s (tmp/pytest-late-diagnostics-final-2026-09-22.xml). It is no longer
an outstanding run.

Resolved the specific outgoing-d17 alternative for table_Q8:537 without
using that historical proof. Let C=(h1+xv1)u_3i and V=(x+y)h1u_(i+2j).
The independent CD5 outgoing-cycle certificate transports in TateSS by
a_j Phi^-1 omega^2, where Phi is the permanent norm/Thom/Euler unit, not
an asserted HFPSS 20+H equivalence. omega^2(D)=zeta D and a_j C_k=zeta V
give alpha zeta^6 VD7=alpha VD7. The unknown Thom constant alpha is nonzero;
jV=0 removes its higher-series terms. Target filtration r+2 is in the
HFPSS-to-Tate comparison's injective range. This proves all outgoing
maps of VD7 are zero, without asserting protection from incoming maps.
The older page9-only certificate remains separately scoped.

Added DER-MIX-PHI-CD5-VD7-cycle with an explicit workspace-qualified
dependency on ws_3sigma_i / DER-3I-EULER-CD5-cycle. The finite incoming
inventory at H=Vk6D9, (48,26), leaves only d19 from XkD7, (49,7), where
X=x^3u. Its low source XD4, (29,3), and its forward-g source both reach
E19 by separately recorded incoming/outgoing inventories. The strong
vanishing line forces d19(XD4)=lambda19 Vk5D6, target (28,22), with
lambda19 in F4 nonzero, not an assigned value of 1. The conditional
length15 alternative is excluded for both c!=1 and c=1, without fixing
c or b. Only D8 and forward g repeat the new map. The printed table537
row remains historical-review: the new proof, not its graph matching or
printed coefficient, supplies admission.

The actual saved-project mixed E24 viewport, stem40..64 and filtration0..44,
has 79 filtration>=23 points after this map, versus 84 when only the new
d19 is omitted. The five removed high occurrences are S02(48,26),
S53(41,31), S53(61,35), S02(44,38), S02(64,42). All have genuine incoming
or outgoing d19 witnesses. This is progress, not complete convergence;
the remaining high classes are not clipped to the vanishing line.

Initial independent tests passed: new d19 22 in 48.31s, VD7 28 in64.75s,
cross-workspace cycle dependencies 89 in1.56s, source audit15 in0.61s.
The first combined batch was terminal with171 passed and6 failed in164.90s
(tmp/pytest-mixed-phi-d19-integration-2026-09-22.xml). All six failures
were in the new d17-neighbor witness assertion: actual grades also retain
their representation dictionary, so whole-dictionary comparison to only
stem/filtration failed. The test now checks exact coordinates plus equal
source/target representations. This batch is not described as green.

Browser verification in a private tab confirmed E19 sources (29,3),(49,7)
and targets (28,22),(48,26), midpoint lambda19, and their absence from E20;
no console/KaTeX errors. The user's tab was not changed. Additional audit
found and is correcting proof-revocation admission: adding a DAG premise
alone did not prevent the ordinary map from quotienting after that premise
was withdrawn. The new row has an explicit opt-in dependency gate mirrored
in its serializable Differential record, so a missing claim can also fail
closed; existing claimless manual rows retain their prior behavior.

External-proof cache signatures now retain full conclusions, including
nested edits (91 dependency tests passed in1.80s at that stage). Atlas
transport preserves qualified external IDs even if a local record has the
same ID; its new collision regression passed1 in2.85s. Final integration
and proof-revocation checks are still in progress. The full-suite run
started before these edits remains live under its original handle85638;
it is a baseline run, not validation of the final current tree.

The integration batch is now terminal: 300 passed in374.44s
(tmp/pytest-mixed-d19-final-gates-2026-09-22.xml). This covers the new d19,
VD7, six atlas dependency withdrawals/restorations, rank-one and parameter
guards, and the Review logic graph. The final persistent-event increment
was added after that batch imported its modules; its focused gate/rank-one/
parameter suite passed227 in3.14s, and an actual-d19 backend/schema follow-up
is running separately. The neighbor batch passed52 with1 explicitly
deselected long all-arrow fate test in189.84s; the full graph suite passed10
in34.29s. No deselected test is counted as a pass.

The opt-in is mirrored in Differential and DifferentialEvent. An old event
records that it required evidence even if both its row and proposition are
removed after JSON roundtrip. It can no longer masquerade as unqualified
legacy evidence; the record is retained. Zero-outgoing certificates still
do not restore incoming boundaries. Backend S53 finite rank-one eligibility
now matches the frontend d19 qualification, with the prior incidence
exclusion unchanged. An empty or malformed required-premise list is also
rejected by the Review graph rather than accepted as an independent fact.

Browser checks after the frontend gate change additionally verified the
psi-derived *-2i-j image: the E19 midpoint coefficient is
zeta^2*(lambda19)^2 in the displayed normalized basis. Both low and forward-g
source/target occurrences are present on E19 and absent on E20; the arrows
also disappear on E20. No KaTeX or console errors occurred. Saved-project
SHA256 remains AC42D987D1707C981AFC2B0B8C429250D75E1B180A12EFA4F7D1D11390153805.

Remaining mixed E24 audit: in stem0..63, filtration23..43, the saved project
has212 high points grouped into40 D8/forward-g families: S71 all8 residues
(40points), S62 all8(40), S13 all8(48), S22H all8(40), S22Y even4(20),
S53 X residue(6), and S73 R D2/D5/D6(18). These are not declared survivors
at infinity, and there is no vanishing-line clipping. Table541 really prints
QD4, whereas the omega/Euler image of FN-2I-019 gives the P direction. The
two must not be conflated. The remaining earlier alternative for the Euler
target Xk5D7 at(33,23) was a d17 from gAD2 at(34,6) when c=1.

A subsequent two-agent independent calculation finds that the existing
pure-three-sigma B d5 determines c in the current convention. This result
has NOT yet been written as a parameter assignment or admitted new d5 row:
its implementation must preserve proof revocation and historical table
provenance, rather than overwrite user coefficient settings.

With B=(x+y)u_3i, P=(yh2+xh1v1)u_3i, Q=(h1^2+xh1v1)u_3i and
F=a_j Phi^-1 omega^2, exact products give a_j B_k=A and a_j Q_k=zeta T,
where A=(x2+y2)u_mix and T=(x+y)h1^2u_mix. Thus F(B)=alpha AD2 and
F(Q)=alpha*zeta*T D2. Pure d5(B)=kQ, with coefficient1 independently
detected by x2 d5(B)=2k2U=x2(kQ) nonzero, gives
d5(AD2)=zeta*TkD2. In the existing parameter convention c+1=zeta, hence
c=zeta^2. Pure d5(BD)=kD(P+Q) cross-checks the odd coefficient zeta^2.

Sources checked: formal_notes.tex:697,730-762,875; record/note.tex:685;
DKLLW main.tex:833-878,943,1179-1185; Beaudry Appendix A, Lemma A.1 and
A.14 (PDFpp52-53,57) for omega(k)=k. The same Thom unit acts on both sides.
Its higher-j and higher-two terms disappear because the selected A/T lines
are j-annihilated and2-torsion, not because the whole E2 cell is one-dimensional:
AD2's E2 cell also has a separate S62V bo column. Actual saved E5 has live
pure B(-1,1),kQ(-2,6) with the coefficient1 arrow, and mixed AD2(14,2),
TkD2(13,7) as finite0:0 directions. The mixed target has no prior d3 source
at(14,4). The table511/512 printed zeta,zeta^2 order is reversed relative
to this current omega/basis convention and must remain visibly documented.

Files for this increment: backend/domain/formal_notes_chart.py;
backend/data/review/table_q8_source_audit.v1.json; backend/domain/models.py;
backend/domain/fate.py; backend/domain/logic_graph.py;
backend/domain/atlas_transport.py; backend/static/page-algebra.js;
public/static/page-algebra.js; tests/test_mixed_phi_vd7_cycle.py;
tests/test_mixed_d19_forced.py; tests/test_mixed_d17_forced.py;
tests/test_cycle_premise_admission.py; tests/test_table_q8_source_audit.py;
tests/test_atlas_transport.py; tests/test_logic_graph_ui.py; RECORD.md.
No research source TeX, saved-project content, commit or push was changed.

Latest persistent-event mirror follow-up completed: 244 passed,24 deselected
in32.81s (tmp/pytest-mixed-d19-event-mirror-2026-09-22.xml). This covers the
current backend event/schema gate plus parameterized and rank-one fate;
the24 actual-six-atlas cases were covered by the preceding300-test batch.

The earlier full-suite baseline has now terminated: 1772 passed,3 failed
in3035.96s (tmp/pytest-full-ad2-mixed-scope-2026-09-22.xml). It began before
the VD7/d19 changes and is not a current-tree all-green result. Its two
table-source failures used the old imported assertions against the updated
row537 audit data; the remaining smoke assertion still expected two d11
rows instead of including the independently proved CD1 Euler d11. A fresh
source-audit/even-d9 check and an exact smoke-row identity check follow.

Read-only browser recheck of the user's shared-target annotation confirms
the actual E9 source cell(-14,2) contains separate P D^-2 and Q D^-2
constant ports plus the positive-j Q ideal. Both constant ports map to
T k2 D^-1 at(-15,11). E10 contains the computed P+Q representative and
the positive-j ideal, not the target; no d9 arrows or KaTeX/console errors
remain. The latter ideal's existing tooltip explicitly says its displayed
name denotes the E2 module, not each surviving generator. No mathematical
data was removed or modified to answer this annotation. Static page-algebra
copies remain identical; both app.js and both page-algebra.js syntax checks
pass. The saved-project SHA256 remains unchanged.

The fresh source-audit/even-d9 batch completed22 passed in22.82s
(tmp/pytest-user-shared-d9-target-2026-09-22.xml). The precise smoke update
in tests/test_smoke.py preserves the two FN-3I-009 rows and checks the new
DER-3I-EULER-CD1-D11 row, its(9,1)->(8,12) exact ports, D8/forward-g
scope and independent Euler13 certificate:1 passed in5.27s. The two old
source-audit baseline failures do not reproduce. A new current-tree full
suite was started with tmp/pytest-full-current-vd7-d19-2026-09-22.xml
(live terminal session15035); no all-green full-suite claim is made before
it terminates. Production files are frozen during this run. The private
browser audit tab is restored to pure3sigma E9; the user's tab was untouched.

The follow-up coefficient audit is now recorded separately in
backend/data/review/mixed_phi_a_coefficient.v1.json. It is deliberately not
loaded by production: c=zeta^2 needs a live proof-bound parameter, not a
settings assignment or a raw value that survives withdrawal of its proof.
The new tests/test_mixed_phi_a_coefficient_source.py passed15 tests in8.37s
(tmp/pytest-mixed-c-source-audit-2026-09-22.xml). It checks the real F4/action
implementation, finite numerator products, actual E5 ports and source d5,
common-unit cancellation, odd/even coefficients, and unchanged six-image
admission. D2 is not asserted to be a5-cycle: main.tex:1508 has
d5(D2)=2kD2h2, whose product with the selected order-two B direction is zero.

The subsequent mixed d21 source audit distinguishes P=(yh2+xh1v1)u_mix
from Q=(h1^2+xh1v1)u_mix. Conditional on the independently checked c=zeta^2
and existing nonzero b, the finite target Y=x3k5D7u_mix at(33,23) has the
constant-layer matrix[1,b^-1] from(PD4,QD4). The kernel is P+bQ, not a
separate unknown relative coefficient. The incoming inventories for Y and
gY are being recorded before runtime integration; table541's printed unit1
remains historical and does not determine b.

The positive-j tail needs a genuine permanent Witt lift, not a claim that
the literal coefficient polynomial v1^4/D is invariant. DKLLW
main.tex:1391-1400, prop:inftybo, with m=-1,l=1 provides the permanent
integer HFPSS class J with mod-two action j. The displayed Tate d3 has
source(1,-3) and target(0,0); main.tex:488-510 supplies the comparison.
main.tex:674 only asserts the norm congruence modulo2. On the selected
order-two Q and Y directions, different lifts differing by2 act identically.
Table6 main.tex:1179 gives B v1^4=0; with X=B x2 this gives JY=0. Hence
d21(J^n QD4)=0 for n>=1 once the constant-layer formula is established.
This is a source-audit result, not a new production d21 admission yet.

### 2026-09-22: bounded document-baseline delivery

The user narrowed the remaining task to minimal changes, completion within
one real-time hour, and provisional reliance on the documents for unresolved
differentials. The delivery window starts at 2026-09-21 18:01:43 UTC and ends
at 19:01:43 UTC. This supersedes the proposed additional proof-bound parameter
framework above; that framework is not part of this delivery.

The two separate source-audit files now pass 33 combined tests in 26.52s
(tmp/pytest-mixed-c-d21-source-audits-2026-09-22.xml). They remain audit records,
not independent runtime proof certificates. The application document baseline
will distinguish document-adopted maps from independently verified maps and
preserve established corrections and explicit user coefficient assignments.

Before that baseline integration, a read-only audit of the actual saved
project checked all 16 atlas workspaces at E23, E24, and E23 again (48 chart
evaluations). All 744 displayed E23 arrows had live rendered endpoints and
ports; there were no dangling dead-key arrows, dead anchors, or page conflicts.
E24 displayed no residual arrows, all 16 return-to-E23 results were stable,
and migration preserved all 16 selected page numbers. This is a renderer
check, not a claim of full mathematical convergence: high-filtration classes
remained in the three-sigma and mixed charts pending further input.
The saved project SHA256 remained
AC42D987D1707C981AFC2B0B8C429250D75E1B180A12EFA4F7D1D11390153805.

The minimal application profile is now implemented in
backend/domain/document_baseline.py and called immediately before atlas
transport in migrations.py. Flask load_project enables it only for the named
Studio project unless an explicit false flag is stored. Core strict migration
still does not opt in. The UI displays a short document-baseline notice.
Its changes are limited to the existing five mixed d5 rows (admitted, not
verified), parameter defaults c=zeta^2, b=1, lambda17=1, lambda19=1, and four
new document-adopted rows:

- table_Q8.tex:528, R D2 d11 to Q k3D3, repeated period32;
- table_Q8.tex:538, R D5 d19 to Q k5D7, period64;
- P D4 and Q D4 d21 to X k5D7, coefficients1 and b^-1, period64.

Here R=(x2+y2)h1 u_mix, P=(yh2+xh1v1)u_mix,
Q=(h1^2+xh1v1)u_mix, and X=x3u_mix. The positive-j Q tail has a separate
outgoing-zero certificate. Only the declared coefficient ports are affected;
no inverse g is introduced, period32 is not promoted to an invertible D4,
and known contradictory historical branches remain excluded. Explicit user
assignments are preserved and incompatible assignments remain visible as
unresolved rather than being overwritten. Disabling a saved profile restores
owned statuses/defaults, removes its owned rows/certificates and automatic
events, and retains all existing class nodes.

Validation of this profile: tests/test_document_baseline.py passed32 tests
in65.52s, including actual E5/E6/E11/E12/E19/E20/E21/E22 runtime, shared-target
rank-one d21, low P+Q kernel, positive-j Q, all16 page-preserving idempotent
transports, single Frobenius on six mixed images, and enable/disable roundtrip.
The API/UI suite passed22 in109.97s
(tmp/pytest-document-baseline-api-ui-2026-09-22.xml); the source/UI/scheduling
delta suite passed69 in27.15s
(tmp/pytest-document-baseline-delta-2026-09-22.xml). These are123 focused tests
across three invocations, not a new complete-suite run.

A second actual-saved-project audit with document_baseline=True checked all16
atlas workspaces at E23/E24/E23, using stem[-64,127] plus each atlas shift and
filtration[0,64]. All48 views have no conflicts, blocked pages, dangling
arrows, empty displayed ports, or dead anchors. All744 E23 arrows have live
endpoints; E24 has no residual arrows; page preservation and return-to-E23
results are stable16/16. Each of the six mixed images changes from2079 to258
points and from1236 to0 points of filtration>=23 in this window. The other10
images are unchanged. Each of the three 3sigma images still has63 high-
filtration E24 points: this delivery does not claim full convergence and does
not suppress those points by a visual cutoff.

The real local browser was reloaded and checked at mixed E5/E11/E19/E21/E22,
the omega-psi mixed image E5, and pure3sigma E23. The document notice is
visible, the new R rows are drawn on E11/E19, E22 has no d21 arrows and shows
the P+Q quotient label, and the transported chart has rendered zeta/zeta^2
arrow coefficients with no KaTeX errors. Browser console errors are absent.
Backend/public static files match byte-for-byte; both app.js and both
page-algebra.js copies pass node --check. The user's saved project is unchanged.

The already-running full suite terminated at approximately18:27 UTC with
1932 passed and1 failed in3377.51s (56m17s), recorded in
tmp/pytest-full-current-vd7-d19-2026-09-22.xml. Its collection preceded this
document profile. The sole failure was the stale global derived-arrow count
in test_thom_formal_chart.py:336:42 expected versus43 actual after the
independent mixed XD4 d19 was added. The test now expects43 and explicitly
checks DER-MIX-D19-X-D4/formal_diff_mixed_d19_x_D4_forced, retaining all
endpoint, coefficient-pattern, status, and evidence assertions. No production
mathematics was changed to satisfy that failure. A focused rerun of the
entire affected file, mixed d19, and document baseline replaces a second
56-minute full run to respect the user's one-hour limit.

Exact files changed for this bounded delivery: backend/app.py,
backend/domain/migrations.py, backend/domain/document_baseline.py (new),
backend/templates/index.html, backend/static/app.js, public/static/app.js,
tests/test_document_baseline.py (new), tests/test_thom_formal_chart.py,
and this RECORD.md. Earlier source-audit files and other pre-existing worktree
changes were preserved. No research TeX, saved project data, or remote Git
state was changed by this delivery.

Final targeted regression finished at18:31:47 UTC:95 passed in237.34s
(tmp/pytest-document-baseline-final-regression-2026-09-22.xml), covering the
whole affected Thom/formal chart test file, mixed d19, and the32 document-
baseline tests. The earlier22 API/UI and69 source/UI/scheduling tests plus
this95-test run cover186 distinct focused tests, all passing. The sole full-
suite count failure is therefore corrected and rechecked; a second full run
was intentionally not started. The bounded document-baseline delivery ends
about30 minutes after the user's one-hour window began. Unresolved research
questions and the recorded 3sigma high-filtration residuals remain explicit;
completion here is the requested minimal implementation and validation, not
an assertion that all mathematical convergence has been independently proved.

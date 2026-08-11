# HFPSS Studio: previous-work collection

This is a source-scoped index of the work presently available to the project.
It separates published theorems, algebraic calculations, and prospective
imports, so it can be used safely as a proof-graph starting point.

## Available work

| Item | Available result | Evidence | Studio status |
| --- | --- | --- | --- |
| Integer-graded 2-BSS | The D-localised, completed Q8 group cohomology is calculated from an F4 input; 2-power extensions are retained. | arXiv-2209.01830v3/main.tex, lines 886--1043; charts/2BSSE1.pdf, charts/integer2BSS.pdf | Finite source-backed E2 representatives only. |
| (*-sigma_i)-graded 2-BSS | A mod-2 orientation supplies an E1-level comparison with the integer calculation; Bockstein differentials and extensions remain essential. | main.tex, lines 1045--1150; charts/sigma2BSS.pdf | Finite source-backed E2 representatives only. |
| Cyclic signed-permutation cohomology | For a \(C_{2^n}\)-action on a polynomial monomial basis by signed permutations, the draft gives cycle-wise kernels, norms, Smith normal forms, representatives, and a cup-product algorithm. | Duan Notes/main.pdf, dated 26 Jan 2026 | Reusable algebraic algorithm; not itself a \(Q_8\)-HFPSS computation. |
| RO(C4)-graded C4-HFPSS | Mackey-valued calculation, restrictions, transfers, norms, and SliceSS-to-HFPSS comparison range. | main.tex, lines 689--783; BBHS20f and HHR17f PDFs | Evidence must be attached to each downstream claim. |
| Q8-HFPSS | D8 is the source-scoped 64-periodicity class; G24 yields the C3 eigenspace/summand comparison. | main.tex, lines 1230--1269; integer HFPSS chart PDFs | Implemented with provenance, fate, and conservative periodicity checks. |
| Coefficient audit | Separates F4, W(F4), and 2-adic data; records unit and mixed-RO(Q8) limits. | DKLLW_F4_ARGUMENT_AUDIT.md | Admitted fact chain. |
| S3 normalizer transport | The \(C_3\) part is in the small stabilizer and the order-two reflection is Galois-semilinear in the extended stabilizer. Both are realised by maps of \(E_\infty\)-ring spectra. | Bea17b, pp. 4, 10, 12, 61; main.tex, lines 619--642; proposition below | Normalizer transport is source-verified. Individual class aliases still require normalisation checks. |
| Legacy final presentation | Records the periodicity quotient \(\mathbb Z/64\oplus\mathbb Z/4\oplus\mathbb Z/4\oplus\mathbb Z/2\), nine grading representatives, and a historical \((*-2\sigma_i)\) differential list. | Notes/Final Presentation/final report.tex | Index only: it contains typographical errors and differential arguments superseded by later correction notes. |
| Hyperelliptic-curve isomorphism | No artifact with this name or matching theorem was found here or in the parent research directory. The nearest source is the elliptic-curve choice of Q8 coordinates. | main.tex, line 631, citing Bea17, Section 2 | Unlocated; not imported. |

## Coefficient backbone

The integer Bockstein spectral sequence is

\[
H^*(Q_8,\mathbb F_4[v_1,u^{-1}])[D^{-1}][h_0]\Longrightarrow H^*(Q_8,W(\mathbb F_4)[v_1,u^{-1}])[D^{-1}],
\]

where \(h_0\) detects \(2\). The \(1,D,D^2\) splitting uses the three
\(C_3\)-eigenvalues \(1,\zeta,\zeta^2\) in \(\mathbb F_4\). Its abutment is
Witt-valued, however, so \(2\), \(4\), and \(8\) extensions must not be
erased after reading the residue-field chart. See E2_IMPORT_AUDIT.md and
DKLLW_F4_ARGUMENT_AUDIT.md for the rules already applied by Studio.

## Where the topological S3 comes from

Set \(E=\mathbf E_2\), \(H=Q_8\), and \(N=G_{48}\). DKLLW24 states that the
extended stabilizer action lifts to an \(\mathbb E_\infty\)-action on \(E\),
and describes \(G_{48}\cong G_{24}\rtimes\operatorname{Gal}(\mathbb F_4/\mathbb F_2)\),
with \(G_{24}=Q_8\rtimes C_3\). Thus

\[
Q_8\triangleleft G_{48},\qquad G_{48}/Q_8\cong S_3.
\]

The topological source is therefore the normalizer action
\(G_{48}\to\operatorname{Aut}_{\mathbb E_\infty}(E)\), not merely a
coefficient-ring automorphism. Taking \(Q_8\)-homotopy fixed points leaves a
residual, homotopy-coherent \(S_3\)-action on \(E^{hQ_8}\), and the same
naturality acts on the filtered HFPSS tower.

### Normalizer-transport proposition

If a finite group \(N\) acts on a genuine \(N\)-spectrum \(X\),
\(H\triangleleft N\), and \(g\in N\), then \(g\) gives a filtered equivalence
of the \(H\)-HFPSS towers and pagewise maps

\[
g_*:E_r^{s,t-V}(H;X)\xrightarrow{\cong}E_r^{s,t-gV}(H;X),\qquad
g_*d_r=d_rg_*.
\]

Here \(gV\) is the \(H\)-representation obtained by conjugation. On group
cochains, the \(E_2\)-map is

\[
(g\cdot c)(h_1,\ldots,h_s)=g_*c(g^{-1}h_1g,\ldots,g^{-1}h_sg).
\]

This follows by functoriality of \(F(EH_+,-)\) under \(h\mapsto ghg^{-1}\)
and preserves the skeletal filtration of \(EH\). For a Morava \(E\)-theory
given initially as a naive stabilizer spectrum, use its Borel-complete genuine
model in this statement. For \(N=G_{48}\) and \(H=Q_8\), it then yields the
required \(S_3\)-transport. A Galois element
\(\tau\) acts Frobenius-semi-linearly:

\[
\tau_*(a x)=\operatorname{Frob}(a)\tau_*(x),\qquad a\in W(\mathbb F_4).
\]

## Qualification and use

This is not a \(W(\mathbb F_4)\)-linear automorphism of one fixed graded
sector: it sends \(V\) to \(\tau V\). It can relate
\(2\sigma_i+\sigma_j\) with \(\sigma_i+2\sigma_j\) as different
\(RO(Q_8)\)-graded pieces, but does not determine a coordinate formula such
as \(\tau(D)=uD\) without a selected lift, orientation, and unit
normalisation.

The small-stabilizer \(C_3=G_{24}/Q_8\) is the direct, W(F4)-linear cyclic
symmetry used in the \(1,D,D^2\) calculation. The order-two reflection uses
the extended group and is topological but Frobenius-semi-linear. DKLLW24's
displayed Galois base-change lemma is only an integer-graded comparison; it
does not itself document every mixed-RO coordinate formula.

With the normalizer construction recorded, topology can transport known
differentials, permanent-cycle statements, products, and hidden extensions
between conjugate sectors. It reduces duplicated work; it does not generate a
differential without a known source, settle units, or replace the published
C4 restriction/transfer/norm and HFPSS--Tate arguments.

### What “algebraically in Galois, but not topologically” can correctly mean

Taken literally, that sentence is false. Beaudry states that the action of
\(S_C=\operatorname{Aut}(F_C)\) on the universal deformation is realised, by
Goerss--Hopkins--Miller, through maps of \(E_\infty\)-ring spectra. Since
\(F_C\) is defined over \(\mathbb F_2\), Frobenius extends this to

\[
G_C=S_C\rtimes\operatorname{Gal}(\mathbb F_4/\mathbb F_2),
\]

again acting topologically on \(E_C\). The defensible meaning of the warning
is narrower:

1. Frobenius is not an element of the *small* stabilizer and it is not
   \(W(\mathbb F_4)\)-linear. It belongs to the extended stabilizer and acts
   semilinearly, sending \(\zeta\) to \(\zeta^2\).
2. A pagewise formula in a mixed \(RO(Q_8)\)-grading requires the normalizer
   action on the representation and on the chosen class representative. An
   abstract Galois base-change statement in integer grading is not, by itself,
   that formula.
3. An equality of displayed class names is stronger than a normalizer
   transport. Thom classes and generators must be normalised before an exact
   scalar can be read off.

Thus there *is* a topological reflection, but its topology comes from the
Goerss--Hopkins--Miller action of the extended stabilizer, not from pretending
that Frobenius is an \(\mathbb F_4\)-linear automorphism in the small
stabilizer.

### The explicit semidihedral reflection

Beaudry chooses the supersingular curve \(C:y^2+y=x^3\) and automorphisms

\[
a(x,y)=(\zeta^2x,y),\qquad
b(x,y)=(x+1,y+x+\zeta^2),
\]

then sets

\[
\omega=a^{-1},\qquad i=b^{-1},\qquad
j=\omega i\omega^2,\qquad k=\omega^2i\omega.
\]

Apply Frobenius coefficientwise, \(\zeta\mapsto\zeta^2\). Direct substitution
in these displayed formulas gives

\[
\psi(i)=-i,\qquad \psi(j)=-k,\qquad \psi(k)=-j.
\]

The central signs disappear in the one-dimensional quotient
representations. Consequently

\[
\psi(\sigma_i)=\sigma_i,\qquad
\psi(\sigma_j)=\sigma_k,\qquad
\psi(\sigma_k)=\sigma_j.
\]

The subgroup generated by \(Q_8\) and this reflection is the semidihedral
group of order \(16\), usually denoted \(SD_{16}\). Together with the
\(C_3\)-rotation it lies in \(G_{48}\), and the quotient by \(Q_8\) is \(S_3\).
Changing the initial labels may exchange \(j\) and \(k\), but it does not
change the fixed-\(\sigma_i\)/transposed-\(\sigma_j,\sigma_k\) content.

### How topology supplies an HFPSS argument

Suppose degree reasons first give only

\[
d_3(u_{2\sigma_i})=c\,x^2h_1u_{2\sigma_i},
\qquad c\in\mathbb F_4^\times.
\]

Beaudry proves that \(v_1,\Delta,k,h_1(=\eta),h_2(=\nu),x,y\) are Galois
invariant. The semidihedral reflection fixes the representation
\(2\sigma_i\); with the Thom generator normalised by
\(\psi(u_{2\sigma_i})=u_{2\sigma_i}\), naturality of the filtered HFPSS gives

\[
\begin{aligned}
d_3(u_{2\sigma_i})
 &=d_3(\psi u_{2\sigma_i})
  =\psi d_3(u_{2\sigma_i})\\
 &=\psi(c)\,x^2h_1u_{2\sigma_i}
  =c^2x^2h_1u_{2\sigma_i}.
\end{aligned}
\]

Hence \(c=c^2\). Since \(c\ne0\), \(c=1\). This is the precise content of
the 5 August 2026 note: topology contributes filtered naturality, while
Galois semilinearity removes the residual \(\mathbb F_4^\times\)-ambiguity.
The conclusion is exact only after the displayed Thom normalisation has been
recorded; without it, the argument remains an up-to-unit statement.

The same normalizer action can transport a known differential from the
\(\sigma_i\)-sector to the \(\sigma_j\)- and \(\sigma_k\)-sectors, but the
transported aliases acquire the chosen \(C_3\)- and Galois scalars. This is
why topology provides more HFPSS arguments without licensing blind symbol
replacement.

## Chronological audit of the 2026 computation notes

Later notes are used as corrections of earlier notes only when they either
give a new proof or explicitly mark an older argument invalid. The date alone
does not promote a claim to the admitted fact graph.

The source artifacts are Duan Notes/笔记 2026年4月13日 15_16_29.pdf,
Duan Notes/笔记 2026年4月21日 11_36_15.pdf,
Duan Notes/笔记 2026年6月3日 10_22_52.pdf,
Duan Notes/笔记 2026年7月24日 10_59_26.pdf, and
Duan Notes/笔记 2026年8月5日 20_24_50.pdf. The typed correction log is
Notes/Note/record/note.tex, especially its April 16 and April 27 entries.

| Date/source | Main mathematical content | Relation to earlier work | Admission status |
| --- | --- | --- | --- |
| 17 Mar 2026 handwritten note | Rejects the earlier identification of the three Euler aliases: although the underlying \(C_3\)-symmetry permutes \(x,y,x+y\), the Bockstein representatives \(a_{\sigma_i},a_{\sigma_j},a_{\sigma_k}\) do not all have the same displayed name. | First explicit warning against uniform symbol transport. | The rejection is admitted; its tentative replacement names are superseded by 13 April. |
| 19 Mar 2026 handwritten note | Lists checks: the three Bockstein names, the \(d_3\) on \(u_{2\sigma_i}\), two mixed \(d_3\)-calculations, ring relations, and the \(C_3\)-permutation. | A research checklist, not a proof. | Task provenance only; no mathematical fact is admitted from the checklist alone. |
| 2 Apr 2026 handwritten note | Points to Beaudry's Appendix A/Theorem A.22 and asks for a comparison between \(G_{24}\)-cohomology with mod-\(2\) coefficients and the project's \(Q_8\) calculation. | This is the origin of the Moore-spectrum/\(2\)-BSS source bridge developed later in this report. | Bibliographic lead admitted; no cross-spectral-sequence differential transport. |
| 10 Apr 2026 internal PDF | Gives a general signed-permutation algorithm for \(H^*(C_{2^n};M(n,k))\): for each monomial orbit it computes \(\ker(R-1)/\operatorname{im}N\), \(\ker N/\operatorname{im}(R-1)\), SNF representatives, and products. | Supplies reusable exact algebra, but its group is cyclic and its module is the specially defined \(M(n,k)\). | Admit the cycle-wise algebra after tests; require a separate module-identification edge before using it for a \(Q_8\) or \(C_4\) HFPSS page. |
| 13 Apr 2026 handwritten note | Corrects the \(C_3\)-transport of degree-one generators and the aliases of Euler/Bockstein classes. In particular the \(j\)-sector alias is recorded as \(a_{\sigma_j}=\{\zeta^2x+y\}u_{\sigma_j}\), not \(\{x+y\}u_{\sigma_j}\). | Supersedes same-name transport across the three sectors. It explains why \(\zeta\)-coefficients appear in later mixed products. | Source-backed as a project correction; exact generator convention remains tied to the chosen \(\omega\). |
| 21 Apr 2026 handwritten note | Uses the Leibniz rule to force a nonzero mixed \(d_3\) after multiplying a known \((*-\sigma_i)\)-class by \(u_{2\sigma_j}\). | Depends on the corrected \(C_3\)-aliases and the exact differential on \(u_{2\sigma_j}\). | Review queue until those two premises are admitted with the same convention. |
| 3 Jun 2026 handwritten note | Records a higher-differential/periodicity argument in a mixed grading. | The handwriting does not determine every source and target unambiguously. | Transcription required; do not import automatically. |
| 14 Jul 2026 typed record | Explicitly says that the checked material through Section 6.4 is acceptable, while Sections 6.5 and 6.6 do not hold; warns that transporting a \((*-2\sigma_i)\)-differential to terms involving \(u_{2\sigma_j}u_{\sigma_i}\) changes names and may introduce \(\zeta\)-coefficients. | Rejects the earlier uniform-pattern assumption and supplies the governing correction rule. | The rejection and warning are admitted; individual replacement differentials remain review facts. |
| 24 Jul 2026 handwritten note | Proposes conjugate coefficients \(\zeta,\zeta^2\) for the \(j\)- and \(k\)-sector \(d_3(u_{2\sigma})\) formulas and expands two mixed Leibniz calculations. | Refines the typed mixed-sector computation, but the assignment of \(\zeta\) versus \(\zeta^2\) depends on whether \(\omega\) or \(\omega^{-1}\) sends \(i\) to the sector named \(j\). | Nonzero conjugate pair admitted only up to convention; exact label assignment stays in review. |
| 5 Aug 2026 handwritten note | Starts from \(d_3(u_{2\sigma_i})=c x^2h_1u_{2\sigma_i}\), applies the \(SD_{16}\) Galois reflection, and proves \(c=1\). | Closes the unit ambiguity left implicit in the earlier “degree reasons” proof. | Admitted with explicit premises: Galois invariance of \(x,h_1\), fixed \(2\sigma_i\), fixed Thom normalisation, and HFPSS naturality. |

The typed research record contains a particularly important negative fact:
“up to 6.4 is fine; 6.5, 6.6 do not hold.” Those rejected sections must not
remain hidden premises of a later proposition. In Danus-style terms, every
descendant depending on them is blocked until re-proved from the corrected
\(C_3\)-action.

The legacy final presentation should be treated the same way. It contains,
for example, the typographical assertion that both \(\sigma_i\) and
\(\sigma_k\) have kernel \(\langle i\rangle\), and several displayed
periodic families repeat an unshifted target where a power of \(D\) should
change. These defects do not invalidate its Smith-normal-form index, but they
prevent the document as a whole from being an admitted source for exact
differentials. The later typed record, corrected charts, and dated
handwritten notes take precedence claim by claim.

### Danus-style dependency payload for the August result

| Fact id | Statement | Required premises | Status |
| --- | --- | --- | --- |
| beaudry-topological-galois | \(G_C=S_C\rtimes\mathrm{Gal}\) acts on \(E_C\) through \(E_\infty\)-maps. | Beaudry 2017, pp. 4 and 12; Goerss--Hopkins--Miller. | source-verified |
| beaudry-psi-q8 | Frobenius sends \(i,j,k\) to \(-i,-k,-j\), hence fixes \(\sigma_i\) and swaps \(\sigma_j,\sigma_k\). | Beaudry 2017, pp. 10 and 12; explicit substitution in the curve automorphisms. | verified (source-derived) |
| beaudry-galois-generators | \(h_1,x\) are Galois invariant. | Beaudry 2017, p. 61; DKLLW24 identification \(h_1=\eta\). | source-verified |
| aug-thom-normalisation | \(\psi(u_{2\sigma_i})=u_{2\sigma_i}\). | Fixed representation plus the selected Thom generator. | established project-normalisation; must be stored explicitly |
| aug-d3-unit | \(d_3(u_{2\sigma_i})=x^2h_1u_{2\sigma_i}\). | All four preceding facts and the already established nonzero \(d_3\)-line. | verified (admitted) |
| uniform-s3-symbol-renaming | Every mixed-sector formula follows by replacing \(i,j,k\) in its displayed name. | Would require invariant aliases and scalar-free transport, contradicted by the April/July corrections. | rejected |

## Next additions

1. Provide the path and exact claim for the intended hyperelliptic-curve
   isomorphism work.
2. Fix one convention for whether \(\omega\) or \(\omega^{-1}\) sends the
   \(i\)-sector to the sector named \(j\), then settle the exact
   \(\zeta/\zeta^2\) assignment in the 24 July formulas.
3. Transcribe the 3 June higher-differential note and audit every premise
   against the corrected \(C_3\)-action.
4. Store the August dependency chain in the Studio logic graph, keeping the
   Thom normalisation as a visible premise rather than implicit notation.

## Detailed provenance: Beaudry 2017, the Moore spectrum, and the 2-BSS

### The two calculations have related input but different abutments

Let \(V(0)\) be the mod-\(2\) Moore spectrum, defined by the cofiber sequence

\[
S^0\xrightarrow{2}S^0\longrightarrow V(0).
\]

Since \(\pi_*\mathbf E_2\) is \(2\)-torsion free, smashing with \(\mathbf
E_2\) gives the coefficient short exact sequence

\[
0\longrightarrow\pi_*\mathbf E_2\xrightarrow{2}\pi_*\mathbf E_2
\longrightarrow\pi_*(\mathbf E_2\wedge V(0))\longrightarrow0,
\qquad
\pi_*(\mathbf E_2\wedge V(0))\cong\mathbb F_4[[u_1]][u^{\pm1}].
\]

This is the bridge to the project 2-BSS: applying \(Q_8\)-cohomology to the
\(2\)-adic filtration produces its Bockstein exact couple, with residue input
\(H^*(Q_8;\mathbb F_4[v_1,u^{-1}])[D^{-1}]\) and abutment the corresponding
Witt-valued cohomology. Thus the Moore calculation controls the mod-\(2\)
coefficient layer and its Bocksteins; the project must still retain all
\(2\)-extensions when returning to \(\mathbf E_2\).

Beaudry's target is different. In Bea17b, Section 1.1, the algebraic duality
spectral sequence computes an associated graded for
\(H^*(\mathbb S_2^1;(\mathbf E_C)_*V(0))\). After Galois fixed points, it
feeds a descent spectral sequence for \(\mathbf E_2^{hG_2^1}\wedge V(0)\);
the cited fibre sequence makes this a first step toward
\(L_{K(2)}V(0)\). In contrast, the Studio 2-BSS is auxiliary to

\[
Q_8\text{-HFPSS}(\mathbf E_2)\Longrightarrow\pi_*(\mathbf E_2^{hQ_8}).
\]

Consequently, there is no map of spectral sequences that permits an ADSS
differential for the Moore spectrum to be entered as a \(Q_8\)-HFPSS
differential. The permitted common material is the explicitly cited
coefficient module, group cohomology, and named restriction/Galois
comparison.

### What Beaudry supplies to the project

The relevant source chain is:

1. Bea17b, Appendix A, Lemma A.1 begins with
   \(H^*(Q_8;\mathbb F_4)\), diagonalises the residual \(C_3\)-action over
   \(\mathbb F_4\), and explains why the two degree-one eigenvectors are
   Galois conjugate. This is the coefficient-level reason that the project
   uses three \(C_3\) eigencharacters rather than an \(\mathbb F_2\)-linear
   splitting.
2. The same lemma gives the \(G_{24}\) cohomology presentation after taking
   \(C_3\)-fixed points. Bea17b, Remark A.2 and equation (A.3), says that the
   \(Q_8\)-invariant discriminant-like class is a \(C_3\)-eigenvector with
   eigenvalue \(\zeta^2\). DKLLW24 uses this as
   \(\omega_*(D)=\zeta^2D\).
3. Bea17b, Theorem A.14 computes the \(G_{24}\)-cohomology of the symmetric
   algebra over \(\mathbb F_4[v_1,k]\); Theorem A.20 then obtains
   \(G_{48}\)-cohomology by Galois invariants and recovers the \(G_{24}\)
   answer after extension of scalars from \(\mathbb F_2\) to \(\mathbb F_4\).
   This is the direct source for the coefficient comparison invoked in
   DKLLW24, Section 3.2.

The exact logical direction is therefore

\[
\text{Bea17b mod-2 cohomology and \(C_3\)-action}
\Longrightarrow
\text{DKLLW24 2-BSS \(E_1\)-input}
\Longrightarrow
\text{Witt-valued \(Q_8\)-HFPSS \(E_2\)-page}.
\]

It is not a reverse implication, and it does not identify the abutment with
\(L_{K(2)}V(0)\).

### Danus-style admission nodes for this portion

| Proposed fact id | Statement | Premises that must be admitted | Status |
| --- | --- | --- | --- |
| beaudry-v0-cofiber | \(\mathbf E_2\wedge V(0)\) supplies the mod-\(2\) coefficient quotient used by the 2-BSS. | The Moore cofiber sequence; torsion-freeness of \(\pi_*\mathbf E_2\). | source-verified |
| beaudry-c3-eigenspaces | The \(\mathbb F_4\) \(C_3\)-eigenspace decomposition is valid and distinguishes \(1,D,D^2\). | Bea17b Appendix A, Lemma A.1 and (A.3); chosen \(\zeta\). | source-verified |
| beaudry-g48-basechange | The \(G_{48}\)/\(G_{24}\) relation is Galois invariant/base-change data. | Bea17b Theorem A.20; stated coefficient field. | source-verified |
| moore-to-q8-differential | A Moore-spectrum ADSS differential becomes a Q8-HFPSS differential. | A filtered comparison map with the named groups, spectra, and classes. | rejected unless such a map is supplied |

The last row is deliberately rejected. It prevents a visually similar
differential from becoming an admitted fact through a shared symbol alone.

## Detailed provenance: HHR 2016/2017 and the C4-HFPSS

### What the HHR machinery actually gives

HHR16 constructs the genuine equivariant norm. For \(H\subseteq G\), a
\(G\)-equivariant commutative ring gives a norm on RO-graded homotopy groups

\[
N_H^G:\pi_V^H R\longrightarrow\pi_{\operatorname{Ind}_H^G V}^G R.
\]

Its orientation and Euler-class formulas identify
\(N_H^G(a_V)=a_{\operatorname{Ind}V}\), with the corresponding orientation
formula after the necessary degree correction. This is why the project treats
restriction, transfer, and norm as genuine \(RO(G)\)-graded operations rather
than as edges between ordinary integer charts.

HHR16, Theorem 9.9 is the Slice Differentials Theorem. HHR17 applies it to
the \(C_4\) analogue of real \(K\)-theory, and its Theorem 4.7 gives the
norm-of-a-differential formula. For an index-two inclusion, a differential
\(d_r(x)=y\) produces a normed differential on page
\(2(r-1)+1\), with the Euler correction prescribed by the theorem. In
particular, HHR17, Section 11 uses the \(C_2\) differentials to generate
the \(C_4\) \(d_5\) and \(d_{13}\) information.

HHR17, Theorem 4.4 supplies the second route: a differential is equivalent,
under stated permanent-cycle hypotheses, to an exotic restriction or transfer
with a specified filtration jump. It is not merely graphical decoration. The
corresponding claim must include the subgroup, representation, map direction,
and filtration jump.

The project-relevant topological chain is therefore

\[
\text{HHR16 Slice Differential and genuine norm}
\Longrightarrow
\text{HHR17 \(C_4\) SliceSS differential/exotic-Mackey data}
\Longrightarrow
\text{a named comparison and orientation map}
\Longrightarrow
\text{\(C_4\)-HFPSS evidence for \(\mathbf E_2\)}
\Longrightarrow
\text{restriction/transfer/norm evidence in the \(Q_8\)-HFPSS}.
\]

The final three arrows are not automatic. DKLLW24 makes particular instances
using the orientation map from \(MU_{\mathbb R}\) to \(\mathbf E_2\), its
\(C_4\)-norm, and the HFPSS comparison range. Each instance needs its own
source locator.

### Alias ledger: same typography does not mean the same class

HHR17, Remark 4.1 explicitly warns that after \(d_r(x)\ne0\), expressions
such as \(2x\), \(x^2\), and \(\alpha x\) may survive but are no longer the
products denoted by those symbols. Brackets, for example \([2x]\) and
\([x^2]\), mark an indecomposable survivor. They must not be simplified by an
algebra engine as though \(x\) still existed.

The following examples must be stored as aliases, not equalities.

| Displayed label | Source context | Safe meaning | Prohibited inference |
| --- | --- | --- | --- |
| \(u_{2\sigma}\) | HHR17 \(C_4\)-SliceSS for \(k_{[2]}\) or \(K_{[2]}\) | A slice-page representative; HHR17 records \(d_5(u_{2\sigma})=a_\sigma^3a_\lambda\bar d_1\). | It is automatically the identically named \(\mathbf E_2\)-HFPSS representative. |
| \(u_{2\sigma}\) | DKLLW24 \(C_4\)-HFPSS discussion | A class named with slice terminology after a separately justified comparison. DKLLW24 warns that the corresponding HFPSS differential is \(d_7\), not the SliceSS \(d_5\). | Page number and differential may be copied unchanged from HHR17. |
| \([2x]\), \([x^2]\) | HHR17, Remark 4.1 | A surviving indecomposable notation after the death of \(x\). | Expand it as a product or reuse \(x\) as a live factor. |
| \(a_\sigma,a_\lambda,u_\sigma,u_\lambda\) | HHR16/HHR17 genuine \(RO(C_4)\)-graded notation | Euler/orientation classes with an explicit group, representation, and Mackey level. | Identify a \(C_2\) restriction, a \(C_4\) class, and a \(Q_8\) class solely by typography. |
| \(\nu,\eta,\bar r_1,\bar d_1\) | HHR17 tables and Hurewicz discussion | Named classes whose definition includes page, Mackey level, or Hurewicz/transfer construction. | Treat a matching label in a different chart as a canonical equality. |

### Required graph payload for an imported C4 argument

An admitted \(C_4\)-derived proposition must contain:

1. the source paper, theorem/table/figure, and spectral sequence type;
2. the spectrum, group, subgroup level, page, and full \(RO(G)\)-degree;
3. a declaration of whether a displayed label is a representative, alias,
   post-differential bracket class, restriction, transfer, norm, or Hurewicz
   image;
4. the comparison map to the \(\mathbf E_2\)-HFPSS and its isomorphism range;
5. for an exotic map, its filtration jump and the HHR17 Theorem 4.4 condition;
6. for a normed differential, the input differential and the HHR17 Theorem
   4.7 page formula.

Without these fields, the record belongs in the review queue. This is the
Danus-style distinction between a source-labelled candidate and an admitted
fact; it also prevents the HHR aliases from contaminating the project algebra.

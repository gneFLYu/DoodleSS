# Doodle HFPSS: Agent Development Brief

## Standing instruction

This document is the working specification for agents extending HFPSS Studio. It is intentionally conservative: the application may *organize, render, check local consistency, and suggest* HFPSS claims, but it must never present a suggested or imported differential as a theorem without a traceable proposition, source, and review state.

All code, schema fields, UI copy, generated documentation, and commits must be written in English. Keep the mathematical notation in the source convention of the chart being represented. Do not add, import, or depend on a spectral-sequence-specific LaTeX package. The approved rendering dialect is the custom TikZ dialect in `E:\课程\PACE2025_fly\HFPSS Q_8\Notes\Charts\2Sigma_corrected_E11above.tex`.

The canonical running application is this directory. The files in `frontEnd_lty/` and `QuickDemo/` are valuable prototypes and migration sources, not authoritative computation engines.

## 1. Source authority and review discipline

Use sources in the following order when a statement conflicts with a seed file, an experiment, or another statement.

| Level | Source | Permitted role |
| --- | --- | --- |
| A | DKLLW24, *RO(G)-Graded Homotopy Fixed Point Spectral Sequence for Height 2 Morava E-Theory* | Published chart conventions, computed HFPSS data, comparison results, and stated theorems. |
| A  | The attached v4.2 thesis, especially the computation chapters | Detailed proof patterns, data-model requirements, and its cited source locators. Check each numerical claim against its stated reference. |
| B | `Notes/Charts/2Sigma_corrected_E11above.tex` | The visual source of truth for the current chart dialect and notation. It is not by itself a proof of every displayed arrow. |
| B | Curated project notes and seed propositions | Working hypotheses with provenance. Preserve their status, including corrections and warnings. |
| C | `QuickDemo/`, `frontEnd_lty/`, old JSON, and scripts | Experimental behavior and migration examples only. Never turn a heuristic result into an established claim merely because the prototype produced it. |

Important local caveats:

- The project notes explicitly warn that the \(C_3\)-action (while it's not sure whether the action is from \(C_3\) or \(S_3\), corresponding to \(G_{24}\) or \(G_{48}\), respectively) can introduce \(\zeta\)-coefficients and that part of the mixed \(\sigma\) convention was corrected. Treat affected imported formulae as `under-review` until recertified.
- DKLLW24 proves a sharp strong horizontal vanishing line at filtration 23 for the RO(Q8)-graded Q8 HFPSS for E2 (Theorem 4.8; §6.1.2). This certificate is Q8-HFPSS-specific: it must remain source-scoped and must not be applied to C4, TateSS, or a new custom workspace by default.
- A graph edge is evidence, not a theorem. Every edge records its source locator, hypotheses, convention, and reviewer status.

Suggested bibliography identifiers:

- `DKLLW24`: [arXiv:2209.01830](https://arxiv.org/abs/2209.01830), published in PMJ (2024).
- `DLS22`: [Duan--Li--Shi, *Vanishing lines in chromatic homotopy theory*](https://arxiv.org/abs/2204.08600).
- `HHR16`: [Hill--Hopkins--Ravenel, *On the nonexistence of elements of Kervaire invariant one*](https://annals.math.princeton.edu/2016/184-1/p01).
- `HHR17`:
- `ThesisV42`: `E:\课程\本科毕业论文\Submission edition\[v4.2] 于沣林 RO(G)-分次同伦不动点谱序列计算及其程序化展望.pdf`.

## 2. Mathematical preliminaries the software must preserve

### 2.1 HFPSS, group cohomology, and coordinates

For a finite group \(G\) acting on a spectrum \(E\), the usual cohomological HFPSS has the form

\[
E_2^{s,t}=H^s(G;\pi_tE) \Longrightarrow \pi_{t-s}(E^{hG}),
\]

with \(RO(G)\)-graded refinements carrying a representation shift as well. This formula is conceptual only: the chart must declare its own plotting map, axis orientation, and differential convention. In the local thesis convention a \(d_r\) sends a plotted source \((s,f)\) to \((s-1,f+r)\). Store that convention as data; do not assume it for every imported chart.

The computation begins with a *module-aware* group-cohomology input, not with a cloud of drawn dots:

1. choose \(G\), the coefficient spectrum, and the graded coefficient module;
2. state the action of \(G\) and any auxiliary action such as \(C_3\);
3. compute or import \(H^s(G;M)\) together with products, restrictions, transfers, and generators;
4. use this as the typed \(E_2\)-page; and
5. record page-turning differentials, extensions, and permanent cycles as propositions with proof dependencies.

The current Q8 workspace should retain the representation basis

\[
1,\ \sigma_i,\ \sigma_j,\ \sigma_k,\ H.
\]

A grade is therefore more than `(stem, filtration)`: it has an integral representation vector in that basis and a declared convention. All equality, periodicity, restriction, and renderer code must carry this vector rather than flattening it into a label.

### 2.2 The coefficient layers: \(\mathbb F_4\), \(W(\mathbb F_4)\), and 2-adic towers

For the height-2 Q8 setting, the residue field is

\[
\mathbb F_4=\{0,1,\zeta,\zeta^2\},\qquad
\zeta^2+\zeta+1=0,\qquad \zeta^3=1.
\]

Represent a field element as \(a+b\zeta\), with \(a,b\in\mathbb F_2\). Addition is componentwise XOR and

\[
(a+b\zeta)(c+d\zeta)=(ac+bd)+(ad+bc+bd)\zeta.
\]

The complete table should be a unit test, not a hand-written UI special case:

| + | 0 | 1 | ζ | ζ² |
| --- | --- | --- | --- | --- |
| 0 | 0 | 1 | ζ | ζ² |
| 1 | 1 | 0 | ζ² | ζ |
| ζ | ζ | ζ² | 0 | 1 |
| ζ² | ζ² | ζ | 1 | 0 |

| · | 0 | 1 | ζ | ζ² |
| --- | --- | --- | --- | --- |
| 0 | 0 | 0 | 0 | 0 |
| 1 | 0 | 1 | ζ | ζ² |
| ζ | 0 | ζ | ζ² | 1 |
| ζ² | 0 | ζ² | 1 | ζ |

Do **not** equate this field with the full coefficient ring. The deformation coefficient ring is of the form

\[
\pi_*E_2\cong W(\mathbb F_4)[[u_1]][u^{\pm1}],
\]

so \(W(\mathbb F_4)\), its 2-adic information, and the residue field must remain distinguishable. In particular, `2` is not globally zero. A dot or box representing a higher 2-primary tower cannot be modeled by a bare `F4Element`.

Create these separate concepts:

```text
CoefficientContext
  residue_field: FiniteField4
  coefficient_ring: WittF4 | explicitly specified quotient
  bockstein_stage: optional 2-BSS stage
  scalar_mode: residue | 2_adic | formal

Scalar
  field_part: F4 element, when defined
  two_adic_valuation: optional integer
  presentation: exact | quotient | unknown
```

The 2-Bockstein spectral sequence is the bridge that exposes lifting and 2-torsion behavior from the mod-2/residue picture. Its inputs and conclusions must name the short exact sequence or filtered coefficient object being used. A 2-BSS page is not permission to reduce every later coefficient to \(\mathbb F_4\).

The symbol `v1` requires the same care. The formal parameter in the standard deformation-ring presentation is commonly written \(u_1\), while charts may use `v1` with a source-specific degree and normalization. Store `SymbolDefinition` records with an alias, degree, coefficient context, and source. Never silently identify `v1` with `u1`.

### 2.3 Actions, products, modules, and algebraic cycles

Labels must become parsed expressions before using Leibniz, restriction, or periodicity. Use a small algebra AST rather than string matching:

```text
Expr = Scalar | Symbol | Product[Expr] | Sum[Expr] | Power[Expr, int]
     | Inverse[Expr] | FormalSeries[parameter, coefficients]

ClassTerm = {
  expression: Expr,
  grade: Grade,
  page_interval: [born, dies_or_infinity],
  module_basis_id: optional,
  coefficient_context_id: string
}
```

Define a multiplication table and module action for each workspace. A product is valid only when its coefficient contexts, representation shifts, and page liveness are compatible. Keep relations such as hidden extensions distinct from literal equality of scalars; an example relation involving \(4kD\) is a statement about a 2-adic tower presentation, not ordinary arithmetic inside \(\mathbb F_4\).

The \(C_3\)-action is data, not a renderer decoration. Project notes include conventions of the form

\[
\omega_\*(D)=\zeta^2D,\quad \omega_\*(x)=\zeta x,\quad
\omega_\*(y)=\zeta^2y.
\]

An action specification must declare the chosen \(\omega\), the symbols it acts on, the \(\mathbb F_4\) automorphism, and the source. The evaluator then expands sums such as \(\omega_*(x+y)\) using the actual field arithmetic. This prevents a display that accidentally drops a \(\zeta\) coefficient.

### 2.4 Periodicity, TateSS, and representation grading

Periodicity is an *action certified on a page*, not merely a pair of numbers copied onto many dots. A `PeriodFamily` has one or more independent shift vectors. TateSS can supply a rank-two lattice of periods, but some workspaces have rank zero or one; do not force a double period universally.

For Q8, record period vectors in all grading coordinates. The local material includes an integer-graded \(E_3\) 8-periodicity and a Tate-derived period involving a permanent Euler class and an invertible \(kD^3\), represented as a \(20+H\)-type shift under the stated convention. Their exact directions and sign conventions must be stored with source evidence, not inferred from their display position.

The implementation must support:

- a period lattice with independent generators, relations, and a finite rendering window;
- an anchor permanent cycle proposition for every usable period;
- a page interval on which the period action is valid;
- a multiplier expression and its inverse requirement, when applicable;
- translation of classes, differentials, relations, and proof obligations; and
- a comparison of the full grade vector, not only `(stem, filtration)`.

Representation-period data such as the Q8 quotient description of \(RO(Q_8)/P\), the norm-related class, or a \(20+H\) Tate period must be represented as sourced `RepresentationRelation` / `PeriodCertificate` records. It is unsafe to encode them as universal arithmetic rules.

### 2.5 Page turns, survival, and extensions

Each class has a lifecycle. On page \(r\), a class is `live` only if no accepted incoming or outgoing differential has killed it on an earlier applicable page. A page turn computes a new visible page from accepted claims; it does not erase the historical class or its proof.

Model separately:

- an \(E_r\)-class and its displayed representative;
- a differential claim and its source/target representatives;
- a permanent-cycle claim;
- an additive, multiplicative, or hidden extension; and
- a presentation/tower relation.

This separation matters because a chart glyph may depict several 2-adic layers at one bidegree, while a page differential acts on a specific represented class.

### 2.6 Class fate: HFPSS lifecycle and Tate-only evidence

Every algebraic class requires a **fate record**. A single mutable `state` such as `live`, `killed`, or `target` is insufficient: a class can support a differential, be the target of another, have different behavior in the TateSS, and still be a permanent cycle in the HFPSS.

Store individual events first, then derive the current fate from accepted events:

```text
DifferentialEvent
  id, spectral_sequence: hfpss | tate
  page: positive integer r
  role: supports | receives
  class_id, counterpart_class_id, differential_claim_id
  source_filtration, target_filtration
  source_exists_in_hfpss: true | false | unknown
  comparison_status:
      transports_to_hfpss | tate_only_negative_source | outside_comparison_range | unknown
  proposition_id, source_refs[], status

ClassFate
  class_id
  appears_from_page: 2 | imported value
  hfpss_outgoing_events[]
  hfpss_incoming_events[]
  tate_outgoing_events[]
  tate_incoming_events[]
  first_hfpss_death: {page, role, claim_id} | null
  last_hfpss_live_page: integer | infinity | unknown
  conclusion: supports_differential | is_hit | permanent_cycle |
              survives_to_page | unresolved
  conclusion_page: integer | infinity | null
  justification_ids[]
```

For an accepted \(d_r\), both its source and its HFPSS-valid target cease to represent a surviving class on \(E_{r+1}\). A class only receives the conclusion `permanent_cycle` after all possible HFPSS differentials have been excluded by page bounds, degree arguments, source propositions, or a named comparison theorem. The UI should display this history as, for example, “supports \(d_5\)”, “receives \(d_{13}\)”, “survives through \(E_{11}\)”, and “HFPSS permanent cycle”.

The HFPSS-to-Tate comparison is a special required case. In the working Q8 convention, positive filtration is identified and differentials with a non-negative source have the relevant correspondence; the TateSS additionally has negative filtration. Thus a Tate event

\[
d_r^{\mathrm{Tate}}(z)=x,\qquad \mathrm{filtration}(z)<0,
\]

is **not** an incoming HFPSS differential on \(x\). Record it as `tate_only_negative_source`, retain the Tate source and page, and visibly state why it does not kill \(x\) in the HFPSS. It may be used as evidence for an HFPSS permanent-cycle conclusion only through a proposition applying the comparison range. Never flatten that situation into “\(x\) is hit” without the `tate` qualifier.

### 2.7 Cross-graded products and the finite Q8 grading atlas

“Cross-graded pages” means different \(RO(Q_8)\)-grading workspaces, not different spectral-sequence page numbers. Multiplication is permitted only between classes on the same \(E_r\)-page unless an explicit page-transition/proposition provides another comparison. For

\[
x\in E_r^{s,V},\qquad y\in E_r^{t,W},
\]

the product engine creates a candidate in \(E_r^{s+t,V+W}\), resolves \(V+W\) into a stored grading sector, and carries the normalization/period proof with it. In particular, it must support the operation

\[
(*-\sigma_i)\ \times\ (*-2\sigma_j)
\longrightarrow (*-\sigma_i-2\sigma_j),
\]

with typed coefficients, module actions, full representation vectors, page liveness, and the applicable Leibniz formula. It must not multiply rendered labels.

```text
CrossGradedProduct
  left_class_id, right_class_id, page
  left_sector_id, right_sector_id
  raw_representation_sum
  result_sector_id
  normalization_path: [period_translation_ids...]
  resulting_expression, coefficient_context_id
  leibniz_sign_convention_id
  proposition_id | generated_obligation_id
```

The chosen computational atlas is the full 4-by-4 tile

\[
\mathcal S_{a,b}=(*-a\sigma_i-b\sigma_j),\qquad
0\leq a,b\leq3.
\]

It is obtained as the working normal-form tile after the registered norm/period relations, the \(20+\mathbb H\)-type periodicity, and the integer \(D^8\) periodicity (a 64-shift in the cited integer convention) are applied. The local reduction record is `Notes/Note/record/note.tex` around its \(20+\mathbb H\) discussion; the larger periodic-relation matrix is recorded in `Notes/charts.tex`; DKLLW Corollary 2.22 remains the primary mathematical reference. The exact relation matrix, normal-form convention, and permanent-cycle certificates remain source-scoped; a normalization is invalid without its `PeriodCertificate` / `RepresentationRelation` path. The tile is deliberately **not** further quotiented by symmetry: all 16 sectors are stored and displayed so that cross-graded Leibniz calculations have concrete inputs.

The 16 stored representatives, in row-major \((a,b)\) order, are

\[
\begin{gathered}
(*),\quad (*-\sigma_j),\quad (*-2\sigma_j),\quad (*-3\sigma_j),\\
(*-\sigma_i),\quad (*-\sigma_i-\sigma_j),\quad (*-\sigma_i-2\sigma_j),\quad (*-\sigma_i-3\sigma_j),\\
(*-2\sigma_i),\quad (*-2\sigma_i-\sigma_j),\quad (*-2\sigma_i-2\sigma_j),\quad (*-2\sigma_i-3\sigma_j),\\
(*-3\sigma_i),\quad (*-3\sigma_i-\sigma_j),\quad (*-3\sigma_i-2\sigma_j),\quad (*-3\sigma_i-3\sigma_j).
\end{gathered}
\]

| \(a\backslash b\) | 0 | 1 | 2 | 3 |
| --- | --- | --- | --- | --- |
| 0 | `q8-ro-a0-b0` : \(*\) | `q8-ro-a0-b1` : \(*-\sigma_j\) | `q8-ro-a0-b2` : \(*-2\sigma_j\) | `q8-ro-a0-b3` : \(*-3\sigma_j\) |
| 1 | `q8-ro-a1-b0` : \(*-\sigma_i\) | `q8-ro-a1-b1` : \(*-\sigma_i-\sigma_j\) | `q8-ro-a1-b2` : \(*-\sigma_i-2\sigma_j\) | `q8-ro-a1-b3` : \(*-\sigma_i-3\sigma_j\) |
| 2 | `q8-ro-a2-b0` : \(*-2\sigma_i\) | `q8-ro-a2-b1` : \(*-2\sigma_i-\sigma_j\) | `q8-ro-a2-b2` : \(*-2\sigma_i-2\sigma_j\) | `q8-ro-a2-b3` : \(*-2\sigma_i-3\sigma_j\) |
| 3 | `q8-ro-a3-b0` : \(*-3\sigma_i\) | `q8-ro-a3-b1` : \(*-3\sigma_i-\sigma_j\) | `q8-ro-a3-b2` : \(*-3\sigma_i-2\sigma_j\) | `q8-ro-a3-b3` : \(*-3\sigma_i-3\sigma_j\) |

Persist these as `GradingSector` records at workspace creation, rather than generating an ephemeral list:

```text
GradingSector
  id: q8-ro-a{0..3}-b{0..3}
  normal_form: {sigma_i: -a, sigma_j: -b, sigma_k: 0, H: 0, trivial: 0}
  display_label
  period_reduction_context_id
  workspace_id
  classes[], products_in[], products_out[]
  c3_orbit_id, c3_position
  symmetry_status: distinct | transported | equivalent_by_certificate
```

The backend must materialize all 16 sectors even when only the integer, \(*-\sigma_i\), \(*-2\sigma_i\), and \(*-\sigma_i-2\sigma_j\) calculations currently contain imported classes. An empty sector means “not computed,” not “zero.”

#### \(C_3\) synchronization is not a transposition symmetry

Fix the declared generator convention

\[
\omega(\sigma_i)=\sigma_j,\qquad
\omega(\sigma_j)=\sigma_k,\qquad
\omega(\sigma_k)=\sigma_i.
\]

Each `C3Action` must act simultaneously on the representation vector, expressions, \(\mathbb F_4\)/Witt coefficients, classes, differential claims, fate evidence, and product propositions. It creates a transported copy only after the action formula and coefficient transformation are recorded. The target is then normalized back into the 16-sector atlas with an auditable period path.

Crucially, \(C_3\) alone does **not** identify \(\sigma_i+2\sigma_j\) and \(2\sigma_i+\sigma_j\):

\[
\begin{aligned}
\operatorname{Orb}_{C_3}(\sigma_i+2\sigma_j)
 &=\{\sigma_i+2\sigma_j,\ \sigma_j+2\sigma_k,\ \sigma_k+2\sigma_i\},\\
\operatorname{Orb}_{C_3}(2\sigma_i+\sigma_j)
 &=\{2\sigma_i+\sigma_j,\ 2\sigma_j+\sigma_k,\ 2\sigma_k+\sigma_i\}.
\end{aligned}
\]

They are separate \(C_3\)-orbits before period reduction. A transposition such as \(\sigma_i\leftrightarrow\sigma_j\) would relate them, but that is a different `SymmetryAction` (for example one arising from an explicitly supplied \(S_3\) / automorphism action) and may also act nontrivially on coefficients. Do not create that equivalence, propagate differentials between these two sectors, or merge their data unless an `ROEqualityCertificate` and the corresponding coefficient-action proposition are present. The existing project uncertainty about whether a relevant action is \(C_3\) or \(S_3\) therefore remains visible in the data model.

## 3. Frontend history and target interaction model

For a concrete historical and interaction reference, the public chart at https://spectral-sequences.pages.dev/?sseq=BPC4-1 should be treated as an external example of the target experience: a browsable spectral-sequence page with selectable classes, visible differentials, and chart-oriented navigation. Use it only as a UI and workflow reference, not as an authoritative source for HFPSS claims.

### 3.1 Evolution from `sseq ver15.*.html`

| Version | What it introduced | What must not become authoritative math |
| --- | --- | --- |
| `sseq ver15.html` | Canvas chart, toolbar, add/select/differential/relation/delete/rename/extension tools, zoom/pan, JSON save/load, periodicity editor. | Generator labels and connections are untyped manual records. |
| `sseq ver15.1.html` | Page selector and live-class behavior after a differential. | Page liveness has no proof/certificate model. |
| `sseq ver15.2.html` | Undo/redo and more inclusive periodic connection generation. | Regex-like multiplication and broad replication do not establish a period. |
| `sseq ver15.3.html` | Backend bootstrap/state endpoints, UUID normalization, defaults for the legacy state. | Its page/range defaults and JSON compatibility code are UI plumbing, not HFPSS validation. |
| Current `HFPSS-Studio` | Flask project/workspace model, SVG chart, class/differential/proposition APIs, source/rule/confidence/status fields, rule suggestions, persisted project JSON. | Provenance is still mostly flat; algebra, typed maps, real graph layout, and proof validation remain to be built. |

`ver15.3` is visually and interaction-wise the closest legacy reference. Preserve the immediate chart workflow: direct placement, a concise tool bar, wheel zoom, middle-button pan, page navigation, undoable edits, save/load, and visible periodic propagation. Replace its fragile data semantics, not its productive interaction rhythm.

### 3.2 Current Studio interfaces and gaps

The current Flask application exposes project/workspace data, a proof-tree endpoint, workspace settings, class and differential edits, suggestions, and propositions. The SVG frontend already supports editing and viewing a class chart. The present proof tree is a list of cards; it is not a traversable graph. Current periods are optional integer pairs attached to classes/differentials and several old differential periods are migrated by a hard-coded table.

The target UI should have five synchronized panes:

```text
16-sector grading atlas  <---->  Chart canvas  <---->  Inspector / fate timeline
          |                         |                         |
          v                         v                         v
  C3/symmetry transports  <--> Period-family controls <--> Logic graph / evidence
```

Required behavior:

- Selecting a differential highlights its proposition, anchor proposition, period family, translated siblings, source evidence, and unresolved obligations.
- Selecting a period family highlights the permanent-cycle certificate and shows the lattice shifts that generated each displayed instance.
- Selecting a logic-graph edge highlights the exact chart classes/arrows involved.
- The grading atlas always displays all 16 \(\mathcal S_{a,b}\) sectors. A cell shows its calculation status, imported class count, unresolved obligations, and its \(C_3\)-transport links; it does not disappear because it is presently empty.
- Selecting a class opens a two-track fate timeline: HFPSS supports/receives events above, TateSS events below. A Tate-only negative-filtration incoming differential is visibly distinct from an HFPSS hit.
- Selecting two live classes from any two sectors offers a typed product preview, including the resulting sector, reduction path, and a Leibniz obligation; it never auto-creates a class from display text.
- The atlas must show \(*-\sigma_i-2\sigma_j\) and \(*-2\sigma_i-\sigma_j\) as different cells. A user sees a proposed \(C_3\) transport only inside its true orbit and sees a separate, source-gated control for any transposition symmetry.
- A user can hide unreviewed candidates, period images, or specific proposition kinds without mutating data.
- Every edit is undoable and records a revision/audit entry. A differential and its proposition/events, or a relation and its proposition, enter Undo/Redo as one transaction; `Ctrl+Z` and `Ctrl+Y` invoke the same backend history as the toolbar controls. Importing legacy data is an explicit migration action with a report.
- Delete archives immediately without a confirmation dialog, remains undoable, and never erases differential/relation evidence. Select mode pans the canvas with an ordinary left-button drag; middle-button panning remains available in every mode.
- Dot colors describe derived HFPSS fate, never algebraic order or coefficient size: green is a certified permanent cycle, gray is unresolved, rose supports an accepted differential, and purple receives one. Solid charcoal arrows are accepted differentials; amber dashed arrows are candidate or under-review claims.

Keep the current `/api/project` shape backward-readable while adding versioned endpoints such as `/api/v2/period-families`, `/api/v2/logic-graph`, `/api/v2/claims`, and `/api/v2/render-jobs`. Do not overload a display-only `label` field with semantic algebra.

## 4. Backend design

### 4.1 Canonical entities

Add a schema version and stable UUIDs. The following objects are the minimum canonical layer; their JSON can be normalized into the present dataclasses during migration.

```json
{
  "differentialClaim": {
    "id": "diff-q8-e3-d3-u2sigma",
    "page": 3,
    "sourceClassId": "class-u2sigma",
    "targetClassId": "class-x2h1u2sigma",
    "conventionId": "q8-thesis-plotted-v1",
    "propositionId": "prop-q8-e3-d3-u2sigma",
    "periodFamilyId": "period-q8-integer-e3-8",
    "periodTranslation": [0],
    "anchorDifferentialId": "diff-q8-e3-d3-u2sigma",
    "status": "under-review"
  },
  "periodFamily": {
    "id": "period-q8-integer-e3-8",
    "rank": 1,
    "generators": [{"gradeShift": {"stem": 8, "filtration": 0, "representation": {}}, "multiplierExpr": "D"}],
    "validFromPage": 3,
    "certificatePropositionId": "prop-q8-integer-e3-8-permanent",
    "status": "reviewed"
  }
}
```

The example names are identifiers, not assertions that the displayed formula has already been re-proved in this repository.

Enforce these invariants:

1. Every differential has exactly one `propositionId`; creating a differential creates a draft proposition in the same transaction.
2. Every propagated differential has a `periodFamilyId`, an anchor differential, and an explicit lattice translation.
3. A period family has exactly one anchoring certificate proposition and may have supporting propositions.
4. A differential can be unperiodic only when it explicitly says `periodFamilyId: null` and explains why.
5. The source, target, page, full grade, and displayed coordinates are distinct fields.
6. A `reviewed` or `established` claim is immutable except through a superseding revision; never silently mutate a historical proof.
7. Every class has one derived `ClassFate` record and zero or more immutable HFPSS/Tate `DifferentialEvent` records. A renderer may cache its state but may not be the source of truth for fate.
8. A cross-graded product names two source sectors, one same-page result sector, and its complete period-normalization path. Its result is `unknown` if that path cannot be certified.
9. Every Q8 project that enables the finite atlas persists exactly the 16 `q8-ro-a{0..3}-b{0..3}` sectors. Empty sectors are valid and must not be coalesced.
10. A \(C_3\) transport and an \(S_3\)/automorphism transport are different edge types. The latter requires its own action and coefficient certificate.

### 4.2 Logic graph, not a flat proof tree

Replace `premise_ids`-only presentation with a directed, typed multigraph. Nodes include propositions, assumptions, source excerpts, algebraic identities, map facts, period certificates, differential claims, contradiction witnesses, and renderer artifacts. Edges include `uses`, `proves`, `certifies`, `transports`, `restricts-to`, `transfers-to`, `contradicts`, `renders`, and `supersedes`.

```text
PeriodCertificate proposition --certifies--> PeriodFamily
Differential proposition      --asserts----> DifferentialClaim
DifferentialClaim             --belongs-to-> PeriodFamily
Anchor differential           --transports-> translated differential
HFPSS/Tate DifferentialEvent  --updates----> ClassFate
CrossGradedProduct             --lands-in---> GradingSector
C3Action                       --transports-> orbit class / product / fate evidence
Restriction fact / Leibniz fact / vanishing fact --uses--> Differential proposition
Assumption                    --contradicts-> ContradictionWitness --rejects--> Assumption
```

The graph renderer may use a layered DAG layout with a small force-layout fallback for crosslinks. It must retain edge direction and allow cycles only through explicitly named equivalence/period relations. A visual cycle must never cause recursive proof traversal without a visited-set and an explanation of the equivalence.

Recommended proposition fields:

```text
id, kind, statement, conclusion, status, confidence,
source_refs[], convention_id, workspace_id, premise_ids[],
hypotheses[], verification_checks[], reviewer, reviewed_at,
supersedes_id, notes
```

Use statuses such as `draft`, `candidate`, `derived`, `under-review`, `reviewed`, `established`, `rejected`, and `superseded`. Map existing statuses explicitly during migration; do not collapse uncertainty into `known`.

### 4.3 Validation pipeline

Run these stages when a user creates or imports a claim:

1. **Structural check** — valid IDs, page number, configured differential bidegree, and nonempty proposition/source reference.
2. **Grade check** — source grade plus the configured \(d_r\) shift equals target grade, including representation coordinates.
3. **Page/liveness check** — the source is live on the claimed page and the target represents the appropriate page object; accepted events update `ClassFate` on \(E_{r+1}\).
4. **HFPSS/Tate comparison check** — a Tate event with negative source filtration must be tagged `tate_only_negative_source`, not inserted into `hfpss_incoming_events`; a permanent-cycle inference must cite its comparison-range proposition.
5. **Algebra and cross-grade check** — parsed coefficients, product/module legality, same-page requirement, sector addition, normal-form reduction, and action conventions agree. Return `unknown` rather than guessing a coefficient outside the supported ring.
6. **Period check** — certificate is live/permanent on the required page; the multiplier is valid; the translated source, target, and arrow agree with the same lattice shift.
7. **Symmetry check** — a \(C_3\) transport matches its declared cyclic action and coefficient map. A swap of \(i\) and \(j\) is rejected unless an independent automorphism action/certificate is supplied.
8. **Evidence check** — all dependent propositions have allowed statuses; source locators and hypotheses are present.
9. **Review gate** — automatic success can mark a claim `locally-consistent`, never `established`.

The validator produces a list of machine-checkable obligations and a separate list of mathematical obligations requiring a human/source review. Store both in the graph.

### 4.4 Differential strategies as explicit rule handlers

Implement each strategy as a rule handler that returns proposed graph nodes and obligations, not a magic mutation of the page.

| Rule | Required inputs | Valid output |
| --- | --- | --- |
| Leibniz | Parsed product, known factor differentials, sign/convention, page | Derived differential proposition with its parent claims. |
| Cross-graded Leibniz | Two same-page sector classes, product normal form, period path, known factor differentials | A result in the certified third sector, with all reduction/transport obligations retained. |
| Restriction | Typed map, source/target group, map effect on generators, known target result | A restriction-compatible candidate or a stated obstruction. |
| Transfer / Frobenius | Mackey data, transfer convention, `tr(res(x)y)=x tr(y)` applicability | A transfer-related proposition with hypotheses. Transfer is not treated as a ring map. |
| Norm / HHR-style input | Subgroup inclusion, norm model, Euler class and cited theorem hypotheses | A candidate with the exact theorem/source and page formula, never an unconditional arrow. |
| Vanishing line | Source-scoped bound, current page, target candidates, finite matching assumptions | An elimination or a set of possible arrows; never automatic selection of one arrow. |
| Contradiction / permanent cycle | Explicit temporary assumption, products/restrictions/differentials used, impossible consequence | A rejected assumption and a derived survival/differential consequence linked to the witness. |

For the HHR/norm technique, record the theorem in the source convention. The familiar norm differential pattern changes page length according to the subgroup index and has hypotheses; it must be parameterized rather than copied into all workspaces. Likewise, the HHR fact used locally that an Euler class kills transfers after restriction data is established belongs in a `MapTheorem` record with its conditions.

### 4.5 Algebra, tower, and cycle representation

Current QuickDemo heuristically infers 2-tower levels from names and assumes selected named families are ℤ/8. Replace this with explicit, source-backed presentation data:

```text
TowerPresentation
  generator_class_id
  layers: [{multiple: 1, glyph: dot}, {multiple: 2, glyph: dot}, ...]
  additive_order: 2 | 4 | 8 | unknown
  coefficient_context_id
  hidden_extensions: proposition IDs
```

Use the chart conventions documented by DKLLW:

- a dot denotes the \(k\)-type presentation;
- a blue/red dot distinguishes the cited \(k[[j]]\) presentations;
- a square denotes the \(W(k)\)-type presentation;
- stacked dots/boxes at one bidegree show a 2-adic presentation, with higher layers denoting twice the generator in the stated convention;
- a vertical line represents multiplication by 2; specified slopes represent multiplication by the named cohomology generators; dashed lines denote the source-specific hidden-extension convention.

These are visual semantics. Their mathematical meaning belongs in `GlyphLegend` and `TowerPresentation`, not in CSS class names or hard-coded colors.

### 4.6 Migration of the experimental code

`QuickDemo` is useful for CLI experimentation and legacy JSON bridging, but it has known limitations: integer coefficients instead of \(\mathbb F_4/W(\mathbb F_4)\), fixed differential shifts, incomplete period translation, auto-validation, default vanishing value 23, name-based tower inference, and simplified torsion rules. Preserve it as an `experimental` test harness. Do not import its conclusions into the production workspace unless they pass the validation pipeline and receive a proposition/source record.

## 5. LaTeX and article renderer contract

### 5.1 Template preservation

Register `2Sigma_corrected_E11above.tex` as a versioned template asset with a source path and SHA-256 hash. The currently inspected source has SHA-256 `34D7DB0836272806E841401360AAF44D27629611CD0B928C2BB170487F70D115`; recompute it whenever the source asset changes. Preserve its custom TikZ preamble, grid, scale, style names, offsets, labels, arrows, comments, and hand-authored drawing order. Generated output must use that dialect; it must not replace it with a package-generated chart.

The renderer maps semantic data to the styles already used by the template:

| Semantic item | Template output pattern |
| --- | --- |
| Class glyph | `\node[dot|sq|tower|...] at (x,y) {...};` with an optional label. |
| 2-adic tower | A sequence of explicit glyph nodes using the registered tower convention. |
| Multiplication relation | `\draw[multx|multh1|multtwo|multnu|...] ...;` |
| Differential | `\draw[d1|d2|...|d23] ...;` using only a style declared in the template. |
| Periodic/higher copy | Explicit translated node/arrow plus source metadata; do not rely on TeX loops that hide semantics. |
| Nonsemantic annotation | Preserved `raw_tikz` fragment, excluded from semantic inference. |

Generate stable node names and append machine-readable comments, for example:

```tex
% HFPSS-STUDIO node=class-u2sigma grade=(...,...) source=prop-...
\node[sq, label=$u_{2\sigma}$] (class_u2sigma) at (3.00,1.16) {};
% HFPSS-STUDIO differential=diff-... prop=prop-... family=period-... translate=(1)
\draw[d3] (class_u2sigma) -- (class_x2h1u2sigma);
```

The actual styling remains the template's styling. These comments give import/export a stable identity without changing how the chart looks.

### 5.2 Import scope

Implement a restricted importer, not a general TeX interpreter. It may parse the stable comments and a deliberately small grammar for supported `\node[...] at (...)` and `\draw[...]` forms. It must preserve anything else as opaque `raw_tikz`, warn about unsupported macros, and never infer a theorem from an unannotated arrow.

The importer returns a migration report:

```text
recognized semantic nodes: N
recognized relations/differentials: M
opaque fragments: K
missing proposition IDs: ...
coordinate/style warnings: ...
```

### 5.3 Article-style export

Provide an article renderer in addition to a chart renderer. It takes an accepted snapshot and produces a self-contained `.tex` source that includes:

1. title, workspace, group, grading convention, coefficient context, and source revision;
2. a chart figure generated with the registered custom TikZ template;
3. a class/tower legend;
4. a differential table with page, source, target, scalar, period family, proposition ID, status, and citation;
5. a period-family table with lattice shifts, multiplier, valid pages, and certificate proposition;
6. a compact proof appendix in topological order; and
7. a review appendix listing unresolved assumptions and imported opaque fragments.

Do not emit a polished article that hides `candidate` or `under-review` status. The same structured snapshot should be able to render JSON, custom TikZ, and article TeX deterministically.

## 6. Implementation sequence and acceptance tests

### Phase A — Stabilize data and conventions

- Add `schemaVersion`, `GradingConvention`, `CoefficientContext`, `SymbolDefinition`, and explicit class expression fields.
- Add the \(\mathbb F_4\) value type and its full arithmetic tests. Keep Witt/2-adic behavior separate and initially conservative.
- Materialize the 16 `GradingSector` records and a provenance-preserving normal-form reducer for the \(4\times4\) atlas. Do not apply a symmetry quotient.
- Migrate current classes/differentials/propositions without deleting user data. Attach `legacy-import` provenance where a fact is not yet certified.
- Make the vanishing-line setting source-scoped and show its source/caveat in the UI.

### Phase B — Period families and proof graph

- Add `PeriodFamily`, `PeriodCertificate`, `DifferentialClaim.propositionId`, anchor links, and translations.
- Add immutable HFPSS/Tate `DifferentialEvent` records, derived `ClassFate`, and the two-track fate inspector before replacing existing state badges.
- Migrate existing `period_stem` / `period_filtration` fields into one-generator provisional families, clearly marked for review.
- Replace the proof-card list with a graph endpoint and linked graph visualization.
- Implement structural, grade, HFPSS/Tate comparison, liveness, and period validators first. Do not enable automatic theorem status.

### Phase C — Algebraic inference and map rules

- Add expression parsing/evaluation, same-page cross-graded multiplication, \(C_3\)-action records, and exact coefficient-context checks.
- Implement rule handlers for Leibniz, restriction, transfer, vanishing, contradiction, cited norm/HHR patterns, and certified cross-grade product transport.
- Add the 4-by-4 grading-atlas UI; synchronize only declared \(C_3\) orbits and require a separate certificate for every transposition/automorphism action.
- Make each handler create propositions and obligations; a human approves conclusions.

### Phase D — Rendering and interoperability

- Register the supplied custom TikZ template and build deterministic custom-TikZ export.
- Add annotated restricted import, article export, and snapshot tests.
- Add legacy v15 JSON import as a separate migration route; preserve unrecognized extensions as opaque metadata.

### Mandatory tests

1. \(\mathbb F_4\) addition/multiplication tables, distributivity, \(\zeta^3 = 1\), and the \(C_3\) action examples.
2. A scalar in `W(F4)` cannot accidentally be treated as a residue-field scalar with `2 = 0`.
3. Differential bidegree validation changes when the workspace convention changes.
4. A differential cannot be saved without a proposition ID.
5. A periodic image cannot be created without a family certificate, anchor, and translation.
6. A rejected premise invalidates dependent automatic suggestions but does not delete the historical graph.
7. Restriction/transfer handlers reject missing map hypotheses.
8. A vanishing line produces candidate obligations, not a fabricated selected arrow.
9. Rendering a known snapshot yields stable TikZ comments/styles and compiles with the template's ordinary TikZ setup only.
10. Importing the rendered snapshot returns the same semantic IDs and reports opaque hand-authored fragments rather than discarding them.
11. Existing Studio project JSON and all `sseq ver15.*` fixture imports remain readable or produce a precise migration report.
12. Every accepted HFPSS differential produces the correct source/target fate transition on \(E_{r+1}\); every negative-filtration Tate source remains a Tate-only event and cannot mark an HFPSS class `is_hit`.
13. The sector registry contains exactly the displayed 16 normal forms, including empty sectors, and every cross-graded product lands in one canonical sector with a reproducible period-normalization path.
14. \(\omega\) transports \(\sigma_i+2\sigma_j\) only through \(\sigma_j+2\sigma_k\) and \(\sigma_k+2\sigma_i\). It must not identify it with \(2\sigma_i+\sigma_j\) unless an independently registered transposition action is enabled and certified.

## 7. Definition of done for an agent task

Before claiming an HFPSS feature complete, an agent must answer these questions in the pull request or work log:

1. What source/convention defines the coordinates, coefficients, and notation?
2. Does every created differential point to a proposition, and does every periodic copy point to its family and anchor?
3. Which statements were machine-checked, which were imported, and which still require mathematical review?
4. Does the change preserve \(\mathbb F_4\), Witt/2-adic, tower, and representation-grade distinctions?
5. Does the custom TikZ renderer preserve the supplied chart dialect without new spectral-sequence LaTeX dependencies?
6. Which automated tests and representative render/import snapshots were run?
7. Does each affected class expose distinct HFPSS and Tate fate evidence, including the reason for any permanent-cycle conclusion?
8. For every cross-graded product, is the result one of the 16 stored sectors with an explicit normal-form/period path?
9. Is every symmetry transport genuinely declared? In particular, was \(\sigma_i+2\sigma_j\) kept separate from \(2\sigma_i+\sigma_j\) unless a transposition certificate was supplied?

If any answer is unknown, create an explicit `unknown` / `under-review` proposition or obligation. Do not conceal the gap in a label, color, or implicit default.

# Algebra engine contract

Status: design contract plus an implemented, read-only first slice. No algebra
backend described here is a source of mathematical truth.

This document defines how HFPSS Studio should represent and check algebraic
expressions. It deliberately separates formal commutative-algebra computation
from the source-backed mathematics of group cohomology, spectral sequences,
Witt vectors, equivariant norm/restriction/transfer maps, and
\(RO(Q_8)\)-graded periodicity.

## 1. Source ledger and scope

The following sources were checked for this contract.

### 1.1 Primary mathematical source

`../../[Formal DKLLW] s42543-024-00087-7.pdf` is the primary source for the
claims below.

- Section 2.3, PDF page 13, fixes
  \(W=W(\mathbb F_4)\), \(G_{24}=Q_8\rtimes C_3\), the coefficient ring
  \(W[[u_1]][u^{\pm1}]\), and explicit \(G_{24}\)-action formulas. In
  particular, the \(C_3\)-generator acts on coefficients and algebra
  generators; it is not a textual renaming operation.
- Corollary 2.22, beginning on PDF page 17, gives source-backed
  \(RO(Q_8)\)-periods obtained using norm arguments. A representation shift is
  therefore not a free symbolic equality.
- Proposition 3.2, PDF page 20, supplies the displayed bigradings of
  \(v_1,D,k,h_1,h_2,x,y\) and a source-scoped presentation.
- Theorem 3.3 and Tables 2 and 3, PDF pages 20–21, describe the associated
  graded object of the 2-Bockstein spectral sequence and its torsion data.
  These tables must not be flattened into an equality in an ordinary
  \(\mathbb F_4\)-polynomial ring. The hidden extensions discussed immediately
  after the theorem are separate semantic records.
- Tables 5 and 6, PDF page 24, give module generators and module relations in
  the \((*-\sigma_i)\)-grading. A module-basis class such as
  \(\{x+y\}u_{\sigma_i}\) is not a new polynomial-ring variable unless a
  source-scoped presentation explicitly declares it to be one.
- Proposition 4.1, PDF page 25, proves the integer-graded 64-periodicity
  detected by \(D^8\). Symbolic multiplication by the text `D^8` is not a
  replacement for its invertibility and norm proof.

References in API records should point to the section/proposition/table and
page, not merely to the PDF filename.

### 1.2 Project mathematical notes

The files below are useful secondary evidence but are working notes, not a
uniformly reviewed authority.

- `../../Notes/Note/formal_notes.tex:241` records the local periodicity
  quotient convention.
- `../../Notes/Note/formal_notes.tex:255` records the preferred displayed
  factor order, exemplified by
  \(\{x+y\}h_1h_2v_1^t k^mD^n u_{\sigma_i+\sigma_j+\mathbb H}\).
- `../../Notes/Note/formal_notes.tex:275` documents an omitted-orientation-class
  display convention and a still-incomplete basis discussion.
- `../../Notes/Note/formal_notes.tex:666` discusses the chosen
  \((*-\sigma_i-2\sigma_j)\) calculation.
- `../../Notes/Note/record/note.tex` contains working \(C_3\)-transport and
  differential arguments, including warnings that transport can introduce
  nontrivial \(\zeta\)-coefficients.

Every imported relation from these notes must retain a locator and review
status. Comments, TODOs, and tentative arguments must enter the application as
`candidate` or `under-review`, never as established algebra.

### 1.3 Interaction and prototype sources

- `../frontEnd_lty/sseq ver15.3.html:362` contains `multiplyTerms`. It parses a
  label with a regular expression, merges integer exponents, and alphabetizes
  the result. This is a useful interaction reference, but it loses
  coefficients, sums, coefficient contexts, grades, and provenance.
- `../QuickDemo/algebra/generator.py:32` models \(RO(Q_8)\) in a fixed basis,
  and `generator.py:177` models an integer coefficient times a commutative
  monomial. This is the closest prototype for the requested
  coefficient-times-symbol-times-power editor.
- `../QuickDemo/algebra/torsion.py:74` uses a demonstration heuristic based on
  the occurrence of `k` and `D`. That heuristic is not a source-backed torsion
  theorem and must not be copied into the production engine.
- `DOODLE_HFPSS_AGENT_BRIEF.md` section 2.4 already requires expression trees,
  coefficient contexts, full grades, typed multiplication, and source-scoped
  period actions. This document makes that requirement executable.

## 2. Current Studio audit

The current implementation is appropriately conservative in several places,
but it has no shared algebra semantics.

| Area | What exists | Contract gap |
| --- | --- | --- |
| Classes and symbols | `Grade`, `CoefficientContext`, `ScalarValue`, and `SymbolDefinition` records exist. | `ClassNode.expression` is still a string. There is no canonical AST, expression digest, or grade check tied to the expression. |
| E2 presentations | `backend/domain/e2_presentation.py` implements a terminating, pairwise-confluent, monic integral rewriter and explicitly rejects \(\mathbb F_4\)/Witt input. | It is a separate integer-only term format, not a common expression service. It cannot encode torsion, hidden extensions, localizations, or module presentations from Tables 3 and 6. |
| Structured algebra preview | `POST /api/v2/algebra/preview` now provides registered-generator integer/F4 arithmetic, bounded SymPy expansion/collection, full term grades, explicit rewrite checks, and provenance without persistence. | It is intentionally request-scoped: no shared presentation record, module basis, LogicGraph candidate, Groebner endpoint, Witt scalar, or algebra editor exists yet. |
| Products | `backend/domain/products.py` checks page liveness, coefficient-context equality, grade addition, and sector normalization. | The result is string concatenation. Scalar multiplication, symbol multiplication, relation reduction, and expression-grade validation are absent. |
| \(C_3\) actions | `backend/domain/actions.py` structurally rotates representation coordinates and blocks uncertified materialization. | Expression transport only replaces displayed \(\sigma\)-strings. It does not evaluate registered symbol images or the coefficient automorphism. |
| Periodicity | Period families and source-scoped certificates exist; legacy periods remain under review. | Multipliers are strings, and no expression service checks multiplication, invertibility scope, or the grade of a period multiplier. |
| Logic graph | Sources, propositions, differentials, fates, periods, sectors, products, and actions are nodes. | There are no algebra-presentation, relation, computation, or unresolved-obligation nodes. Formal calculation cannot yet expose its premises or support a candidate proposition. |
| UI | Class expressions and product results are visible; the E2 tool accepts structured JSON terms. | Ordinary class editing still uses a free-text expression. Users cannot inspect scalar context, factors, canonical form, grade derivation, relation scope, or calculation obligations together. |

The integral E2 rewriter should remain available during migration. It is a
safe, explicitly limited backend, not a failed version of the future engine.

## 3. Mathematical trust boundary

### 3.1 Operations SymPy may perform

Within a fully declared commutative presentation, a SymPy adapter may:

- parse a restricted grammar into application-owned expression records;
- combine coefficients and exponent vectors;
- canonicalize sums and commutative monomials;
- perform exact arithmetic over \(\mathbb Z\), \(\mathbb Q\), and prime fields;
- compute Gröbner bases and polynomial remainders for supported ground
  domains and monomial orders;
- check ideal membership and equality modulo an explicitly supplied ideal;
- check that polynomial relations are homogeneous in the supplied additive
  grade;
- compute supported Hilbert-series or finite-dimensional consistency checks;
- compare a submitted relation with a normal form in the same presentation;
  and
- return an explicit trace containing the presentation, relation IDs, backend
  version, order, and input digest.

SymPy documents polynomial reduction and Gröbner bases in its
[polynomial reference](https://docs.sympy.org/latest/modules/polys/reference.html)
and quotient rings/modules in its
[AGCA reference](https://docs.sympy.org/latest/modules/polys/agca.html).

### 3.2 Important SymPy limits

SymPy's `GF(n)` must not be used as `GF(4)`. The documented domain is a field
only for prime order, and prime-power extension fields are not implemented as
ground domains. See the official
[polynomial-domain introduction](https://docs.sympy.org/latest/modules/polys/domainsintro.html#finite-fields).

For the narrow \(\mathbb F_4\) use case, a reviewed adapter may encode
\[
\mathbb F_4 \cong \mathbb F_2[\zeta]/(\zeta^2+\zeta+1)
\]
as a quotient presentation and normalize the \(\zeta\)-coordinate itself.
That adapter must have exhaustive four-element arithmetic tests. It must not
call `GF(4)` or claim that this models \(W(\mathbb F_4)\).

Laurent monomials may use negative powers only for symbols with an active,
source-scoped invertibility declaration. An implementation may translate a
finite Laurent calculation to an auxiliary polynomial presentation, but the
translation and its scope must appear in the trace.

Truncated formal series, modules over quotient rings, non-monic integral
relations, and 2-adic calculations are backend capabilities to be negotiated,
not silently coerced into a field calculation.

### 3.3 Operations no symbolic backend may infer

SymPy, Sage, and Macaulay2 do not by themselves establish:

- \(Q_8\)- or \(G_{24}\)-group cohomology;
- an HFPSS or TateSS differential, page liveness, fate, or permanent cycle;
- a restriction, transfer, norm, comparison, or orientation theorem;
- a hidden additive or multiplicative extension;
- a Witt-vector or 2-adic identity without a separately implemented exact or
  precision-tracked coefficient domain;
- an \(RO(Q_8)\) equality or period not supplied by a reviewed relation and
  certificate;
- the action of \(\omega\) on a symbol or coefficient not registered in a
  reviewed action record;
- equality between two expressions that live on different pages, in different
  coefficient contexts, or in different module presentations; or
- the truth of a source claim merely because a formal reduction returns zero.

A successful formal computation can support a `candidate` proposition. It
cannot set a differential to `accepted`, a class fate to `permanent_cycle`, or
a period/action to `established`.

## 4. Canonical expression contract

### 4.1 Principle

The stored expression is application-owned JSON, not a pickled SymPy object
and not a rendered label. SymPy is an interchangeable evaluator.

The simple editing unit is exactly:

\[
\text{coefficient}\times\prod
  (\text{registered symbol})^{\text{integer power}}
  \times(\text{optional module basis}).
\]

This preserves the useful old-Generator workflow. A "letter" is a stable
`symbol_id`, not one character or a piece of LaTeX. A "unit" is a property
declared by a scoped invertibility proposition, not an implication of the
symbol's spelling.

### 4.2 `algebra-expression-v1`

```json
{
  "schema": "algebra-expression-v1",
  "kind": "sum",
  "coefficient_context_id": "q8-residue-f4",
  "terms": [
    {
      "coefficient": {
        "encoding": "f4-polynomial-basis",
        "coordinates": [0, 1],
        "basis": ["1", "zeta"]
      },
      "factors": [
        {"symbol_id": "h1", "power": 1},
        {"symbol_id": "D", "power": 2}
      ],
      "module_basis_id": "u-sigma-i"
    }
  ]
}
```

Normative rules:

1. `kind` is `sum`; zero is an empty `terms` array.
2. Every term has one scalar and an ordered array of factors.
3. `symbol_id` and `module_basis_id` resolve through the active presentation.
   Display names and LaTeX are metadata and never participate in equality.
4. `power` is an integer. Negative powers require an applicable invertibility
   proposition ID. Zero powers are omitted in canonical output.
5. A term has at most one module-basis ID. Ring expressions use `null`.
   Multiplying two module-basis terms is unsupported unless a source-scoped
   bilinear product map is registered.
6. All terms share one coefficient context and one presentation.
7. Canonical factor order comes from the presentation, not ASCII sorting.
8. The response contains both `input_expression` and `canonical_expression`;
   the input is not destructively overwritten.
9. A rendered LaTeX/Unicode/plain-text triple is derived output and can be
   regenerated.
10. In rendered products, scalar `1` is omitted when other factors exist:
    `1 * D` renders as `D`. LaTeX factors are juxtaposed directly (`Dk`), not
    separated with `\,`.

Nested products and powers in a parser may use an input AST, but they must
normalize to the sum-of-terms storage form when the selected backend supports
that expression. `FormalSeries`, noncommutative products, and unexpanded
operations remain typed AST nodes with `normalization_status:
"unsupported-for-selected-backend"`.

### 4.3 Scalar encodings

Each coefficient is interpreted only through its `CoefficientContext`.

| Encoding | Required data | Initial engine status |
| --- | --- | --- |
| `integer` | JSON integer | exact in the existing rewriter and SymPy |
| `rational` | numerator, nonzero denominator | exact in SymPy, only in contexts declaring \(\mathbb Q\) |
| `prime-field` | prime and canonical residue | exact in SymPy |
| `f4-polynomial-basis` | two \(\mathbb F_2\) coordinates and the registered polynomial for \(\zeta\) | exact only in the reviewed four-element adapter |
| `witt-truncated` | precision, Teichmüller digits, convention ID | opaque until a tested Witt backend exists |
| `two-adic-truncated` | precision and digits/value | opaque until a tested precision-aware backend exists |
| `opaque` | display and source locator | display-only; never used in equality |

Every computation response includes a digest of the coefficient-context
definition. Two equal-looking scalars from different contexts do not combine.
Reduction from \(W(\mathbb F_4)\) to \(\mathbb F_4\) requires a named map and a
proposition; it is not an automatic context cast.

### 4.4 Grades and presentations

Every symbol and module basis has one declared additive grade in a named
convention:

```json
{
  "stem": 8,
  "filtration": 0,
  "representation": {
    "trivial": 0,
    "sigma_i": 0,
    "sigma_j": 0,
    "sigma_k": 0,
    "H": 0
  },
  "convention_id": "q8-thesis-plotted-v1"
}
```

The zero entries may be omitted in storage but are filled before comparison.
The engine returns:

```json
{
  "declared_grade": {"stem": 16, "filtration": 0, "representation": {}},
  "computed_grade": {"stem": 16, "filtration": 0, "representation": {}},
  "grade_check": "equal-before-period-reduction",
  "normalization_path": []
}
```

Allowed grade outcomes are:

- `equal-before-period-reduction`;
- `equal-by-certified-representation-path`;
- `mismatch`;
- `unknown-symbol-grade`; and
- `different-convention`.

Period reduction is a separate service. It returns the exact
`RepresentationRelation`/`PeriodCertificate` IDs used. An algebra normal form
must never quietly reduce an \(RO(Q_8)\) coordinate.

An `AlgebraPresentation` must specify:

- stable ID, version, digest, scope, and review status;
- coefficient-context ID;
- ordered ring symbols and their grades;
- module bases and their grades;
- relation records and relation kind;
- declared units/localizations and their page/grade scope;
- monomial order;
- source-reference IDs; and
- compatible spectral sequence, page range, grading sector, and convention.

Relation kinds are distinct:

- `polynomial-equality`;
- `module-equality`;
- `annihilator-or-torsion`;
- `hidden-extension`;
- `action-formula`;
- `invertibility`;
- `representation-period`; and
- `display-alias`.

Only the first two kinds enter ordinary quotient normalization, and only when
the backend advertises the required coefficient/module capability.
Annihilator data may be checked as an equation but must retain its torsion
meaning. Hidden extensions, action formulas, invertibility, and representation
periods are never mixed into the polynomial ideal.

### 4.5 Provenance and calculation records

A source reference is structured:

```json
{
  "id": "src-dkllw-table-3",
  "document_id": "DKLLW24",
  "locator": {
    "pdf_page": 21,
    "section": "3",
    "theorem": "3.3",
    "table": "3"
  },
  "assertion_scope": "Associated graded of the 2-Bockstein calculation",
  "review_status": "primary-source-checked"
}
```

Each relation and symbol cites one or more source-reference IDs. A formal
calculation is stored as an immutable `AlgebraComputation`:

```json
{
  "id": "algcalc-...",
  "operation": "normal-form",
  "backend": {
    "adapter": "sympy",
    "version": "recorded-at-runtime",
    "capability": "commutative-polynomial-groebner"
  },
  "presentation_id": "q8-bss-associated-graded-v1",
  "presentation_digest": "sha256:...",
  "coefficient_context_id": "q8-residue-f4",
  "coefficient_context_digest": "sha256:...",
  "input_expression": {},
  "canonical_expression": {},
  "relation_ids_used": ["rel-D-y2"],
  "trace": [],
  "formal_status": "formal-check-passed",
  "mathematical_status": "candidate-only",
  "warnings": [],
  "obligation_ids": ["obligation-source-scope", "obligation-page-liveness"]
}
```

`formal_status` is one of:

- `formal-check-passed`;
- `formal-check-failed`;
- `invalid-input`;
- `not-applicable`; or
- `indeterminate-resource-limit`.

No response uses the unqualified words `proved`, `true`, or `certified`.

## 5. UI contract

### 5.1 Class editor

Replace the expression text box, without removing an Advanced mode, with:

1. a coefficient-context selector;
2. a scalar editor appropriate to that context;
3. a factor table with symbol selector, integer power, add, and remove;
4. an optional module-basis selector;
5. an Add term action for sums;
6. a read-only calculated-grade preview;
7. source locator and review status; and
8. side-by-side input and canonical rendering.

The editor may offer the old fast entry style, such as `zeta*h1*D^2`, but it
must tokenize against the symbol registry and show the parsed structure before
save. Ambiguous juxtaposition such as `xy` is rejected unless `xy` is a
registered symbol or the user explicitly chooses `x * y`.

Save is disabled for an unknown symbol, coefficient-context mismatch, grade
mismatch, or unsupported negative power. The user may save an unsupported
formal expression only as `manual-unverified`; it receives an obligation and
is not treated as a normal form.

### 5.2 Inspector

The class/product inspector shows:

- display label;
- original structured expression;
- canonical expression and backend;
- coefficient context and scalar encoding;
- declared and computed full grade;
- sector-normalization path;
- presentation and relation IDs;
- source locators and review statuses;
- formal status versus mathematical status; and
- linked LogicGraph candidates and unresolved obligations.

Color or marker shape must continue to encode fate/proof status, not an
algebra-backend result.

### 5.3 Product and \(C_3\) previews

A product preview has three independent panels:

1. page liveness and spectral-sequence applicability;
2. raw and normalized \(RO(Q_8)\) grade with certificate path; and
3. raw and algebra-normalized expression with coefficient context.

Failure in any panel leaves the result a candidate or blocks persistence.
Leibniz propagation additionally requires the registered sign convention and
accepted differential premises.

An \(\omega\)-preview separately displays:

- the representation-coordinate action;
- every registered symbol image;
- the coefficient automorphism;
- the expression after scalar and symbol normalization; and
- the period path used to return to the atlas.

If any component lacks a reviewed action formula, the preview remains
`candidate` and creates an obligation. Cyclic \(C_3\) transport must not imply
the transposition \(\sigma_i\leftrightarrow\sigma_j\).

### 5.4 Advanced presentation editor

The existing E2 JSON editor remains available as Advanced input. A future form
view should edit the same structured payload, not a second data model. Each
relation row must show relation kind, coefficient context, homogeneous-grade
check, locator, review status, and backend capability.

## 6. API contract

The expanded endpoint family in this section is a proposed versioned contract.
It does not replace the current `/api/v2/e2-presentations/*` endpoints until
migration tests prove equivalent behavior for the formal-integer slice. The
narrow preview endpoint below is already implemented.

### 6.0 Implemented structured preview

`POST /api/v2/algebra/preview`

The request contains `operation`, a source locator, an explicit coefficient
context, a registry of generators, and structured polynomial terms. Supported
operations are `canonicalize`, `add`, `multiply`, `collect`, `expand`, and
`normal-form`. Formal-integer collection/expansion uses private SymPy symbols
constructed only after validation. F4 uses Studio's exact four-element field;
`q8-witt-f4` is rejected.

The response reports term grades, coefficient context, backend/version,
source/generator/relation provenance, rewrite validation where applicable,
`persisted: false`, and `claims_created: 0`. It never parses expression text.
Resource ceilings cover generators, input/intermediate/relation terms,
products, exponents, rewrite steps, and pairwise critical-pair checks. The
exact schema, example, and live limits are covered by
`tests/test_structured_algebra.py` and `backend/domain/structured_algebra.py`.

### 6.1 Capabilities

`GET /api/v2/algebra/capabilities`

Returns adapters, exact domains, supported operations, size limits, versions,
and whether each adapter is local, Vercel in-process, WSL, or remote. UI
controls are enabled from this response, never from hard-coded backend names.

### 6.2 Parse

`POST /api/v2/algebra/parse`

```json
{
  "syntax": "zeta*h1*D^2",
  "presentation_id": "q8-bss-associated-graded-v1",
  "coefficient_context_id": "q8-residue-f4"
}
```

This is read-only. It returns the input AST, canonical
`algebra-expression-v1`, rendered forms, parse ambiguities, and warnings. It
does not apply quotient relations.

### 6.3 Normalize

`POST /api/v2/algebra/normalize`

```json
{
  "expression": {},
  "presentation_id": "q8-bss-associated-graded-v1",
  "operation": "normal-form",
  "expected_grade": {},
  "page": 3,
  "workspace_id": "ws_integer",
  "limits": {"max_terms": 256}
}
```

The response is an unpersisted `AlgebraComputation` plus the grade check.
Server policy may lower user-requested limits. A resource limit returns
`indeterminate-resource-limit`, never a partial equality.

### 6.4 Check a relation or presentation

`POST /api/v2/algebra/check-relation` compares two structured expressions in
one presentation and returns both normal forms and their difference.

`POST /api/v2/algebra/check-presentation` checks schema, symbol uniqueness,
relation homogeneity, coefficient capability, declared monomial order, and
backend-specific consistency information. Passing this endpoint establishes
only a formally usable presentation; source review is a separate status.

### 6.5 Attach a candidate to the LogicGraph

`POST /api/v2/workspaces/<workspace_id>/algebra-candidates`

```json
{
  "expected_revision": 42,
  "computation": {},
  "statement": "Source-scoped formal reduction proposed for review.",
  "conclusion": {"kind": "product-normal-form", "product_id": "product-..."},
  "premise_proposition_ids": ["prop-source-relation"],
  "source_ref_ids": ["src-dkllw-table-3"]
}
```

This mutation stores the immutable calculation, a `candidate` proposition,
and explicit obligations. It does not edit a class expression, accept a
product, create a differential, or change a fate. All such later actions must
reference the candidate and satisfy their own domain rules.

## 7. LogicGraph integration

Add these node kinds when the persistence model is ready:

- `algebra-presentation`;
- `algebra-relation`;
- `algebra-computation`; and
- `algebra-obligation`.

Add typed edges:

- source `supports` relation;
- presentation `contains` relation;
- computation `uses-presentation` presentation;
- computation `uses-relation` relation;
- computation `requires` obligation;
- computation `supports-candidate` proposition; and
- proposition `acts-on` product/class/action/period record.

An obligation has a machine code, human description, affected record IDs,
resolution requirements, and status. Initial codes include:

- `coefficient-context-unsupported`;
- `coefficient-map-uncertified`;
- `symbol-action-missing`;
- `source-scope-unreviewed`;
- `page-liveness-required`;
- `representation-normalization-required`;
- `unit-certificate-required`;
- `module-product-map-required`; and
- `hidden-extension-not-polynomial`.

LogicGraph validation must reject a persisted algebra computation whose
presentation/digest, coefficient context/digest, relations, or obligations
are missing.

## 8. Pluggable backend plan

All adapters implement:

```text
capabilities() -> versioned capability document
validate(presentation) -> formal validation result
normalize(expression, presentation, limits) -> AlgebraComputation
check_equal(left, right, presentation, limits) -> AlgebraComputation
hilbert_query(presentation, query, limits) -> AlgebraComputation | not-applicable
```

The adapter receives validated JSON and returns JSON. It cannot read or mutate
the project directly.

### Phase 0 — common model and manual semantics

- Add the expression/presentation schemas and validators.
- Migrate no existing expression automatically.
- Parse legacy labels only into a preview requiring user confirmation.
- Surface source, grade, context, and obligations in the UI and LogicGraph.
- Keep the current integral E2 rewriter as adapter
  `explicit-integral-rewriter-v1`.

### Phase 1 — bounded SymPy preview (first slice implemented)

- The implemented endpoint provides exact formal-integer and native F4
  polynomial operations; SymPy is pinned and lazily used only for bounded
  formal-integer expansion/collection.
- Add later adapters for rational, prime-field, and reviewed
  \(\mathbb F_4\)-quotient Groebner calculations.
- Record SymPy version and deterministic monomial order.
- Enforce server-side limits on syntax size, variables, degree, terms,
  relations, Gröbner work, and output trace.
- Cache by input, presentation, context, backend-version, and limits digest.
- Run only read-only preview operations at first.
- Differential, fate, action, and period statuses remain unchanged.

### Phase 2 — source-scoped candidates

- Materialize reviewed presentations and immutable calculation records.
- Connect formal results to candidate propositions and obligations.
- Upgrade products to structured expressions.
- Implement coefficient-aware \(\omega\)-preview only after the action and
  \(\mathbb F_4\) adapters pass exhaustive tests.
- Preserve the old integral E2 API through a compatibility adapter.

### Phase 3 — SageMath/Macaulay2 workers

SageMath is a candidate for stronger finite-field, localization, and
arithmetic-domain support. Macaulay2 is a candidate for polynomial/module
Gröbner bases, syzygies, resolutions, and Hilbert calculations. Macaulay2's
official documentation exposes Gröbner bases for ideals and modules and
[module Hilbert operations](https://macaulay2.com/doc/Macaulay2/share/doc/Macaulay2/Macaulay2Doc/html/___Module.html).

These engines use the same JSON contract and do not receive Python or
Macaulay2 source supplied by a browser. Their result is still a formal
calculation with a source obligation, not a spectral-sequence proof.

## 9. Vercel, WSL, and cloud execution boundary

### 9.1 Vercel

The current deployment is a Flask application in Vercel's Python runtime.
Vercel installs Python dependencies from `pyproject.toml`/`requirements.txt`
and bundles reachable files; its official
[Python runtime documentation](https://vercel.com/docs/functions/runtimes/python)
and [function limits](https://vercel.com/docs/functions/limitations) should be
rechecked before dependency or timeout changes.

The repository exposes `api/index.py:app`, includes `backend/**` in the
function bundle, and commits matching browser assets under `public/static`.
No custom build script is configured. SymPy is pinned to `1.14.0`, imported
lazily, and the project currently constrains Python to `>=3.10,<3.14` so
Vercel does not select a newer interpreter before this CAS version is tested
against it.

Architectural rule:

- small, deterministic SymPy previews may run in-process after deployment-size
  and cold-start measurements;
- every request has strict application-level work and output limits;
- no request may launch SageMath, Macaulay2, or arbitrary shell input;
- no long-running job is persisted only in a function's temporary filesystem;
  and
- a timeout/resource error returns an indeterminate result without a
  candidate claim.

Platform limits can change, so this contract intentionally does not encode a
plan-specific duration or bundle-size constant.

### 9.2 Local WSL worker

A local researcher may configure a WSL worker for SageMath or Macaulay2.

- The Flask app sends canonical JSON to a fixed worker command.
- The worker uses a generated job directory and fixed script template.
- User strings are data; they are never interpolated into shell or evaluator
  source.
- The response records executable path, engine/package version, input digest,
  elapsed time, exit status, and truncated logs.
- Local availability is advertised through `capabilities()`.
- Results imported into the project retain `execution_environment:
  "local-wsl"` and are never relabeled as Vercel-reproducible.

### 9.3 Cloud worker

Large calculations use an authenticated job service:

1. Vercel validates and hashes the JSON job.
2. The worker receives a versioned presentation and resource budget.
3. Results are content-addressed and returned with engine/container version.
4. Studio verifies the input digest before attaching a result.
5. A completed job appears as a preview; explicit user action is required to
   attach a candidate to the LogicGraph.

Network failure, worker disagreement, or backend-version drift produces an
obligation. It never selects a convenient answer.

## 10. Acceptance examples

These are contract tests, not a substitute for reviewing the cited sources.

### A. Generator-style monomial

Input: scalar \(\zeta\), factors \(D^2,h_1\), basis \(u_{\sigma_i}\), in the
\(\mathbb F_4\) residue context.

Expected:

- the parser resolves stable symbol IDs;
- factors are ordered by the presentation's preferred order;
- grade is computed additively, including the module basis;
- the displayed output is
  \(\zeta h_1D^2u_{\sigma_i}\);
- input spelling does not affect equality; and
- no torsion or fate is inferred.

### B. \(\mathbb F_4\) versus Witt context

In the reviewed \(\mathbb F_4\) adapter,
\(\zeta^2+\zeta+1\) normalizes to zero.

Expected:

- the same request in a \(W(\mathbb F_4)\) context returns
  `not-applicable` until a Witt adapter exists;
- `GF(4)` is never constructed in SymPy; and
- no automatic cast changes the coefficient context.

### C. Source-scoped Table 3 reduction

Using a presentation explicitly scoped to DKLLW Table 3's associated graded
object, test the supplied relation represented by
\(D y^2-h_2^2\).

Expected:

- the difference reduces to zero in that presentation;
- the computation cites the Table 3 relation ID and source locator;
- the result says `formal-check-passed` and `candidate-only`; and
- the relation is not promoted to an equality in a full Witt-valued ring or a
  hidden extension.

### D. Module basis from Tables 5 and 6

Represent \(\{x+y\}u_{\sigma_i}\) as a sum of ring terms sharing the module
basis `u-sigma-i`.

Expected:

- `x`, `y`, and `u-sigma-i` remain distinct registered objects;
- a Table 6 module relation is evaluated only in its module presentation;
- multiplying two module-basis terms is blocked without a bilinear product
  map; and
- the source locator remains visible.

### E. Cross-graded product

Multiply a live class in \((*-\sigma_i)\) by a live class in
\((*-2\sigma_j)\) on the same \(E_r\)-page.

Expected:

- coefficient contexts must match or have a named certified map;
- raw grades add to \((*-\sigma_i-2\sigma_j)\);
- atlas reduction returns its certificate path separately;
- algebra normalization returns its relation trace separately; and
- \((*-\sigma_i-2\sigma_j)\) is not identified with
  \((*-2\sigma_i-\sigma_j)\) merely by the \(C_3\)-action.

### F. \(\omega\)-transport

Transport an expression containing \(D\), a residue-field scalar, and a module
basis.

Expected:

- representation, symbols, and scalar are transformed independently;
- every formula comes from the selected action record;
- a missing coefficient or module-basis action creates an obligation;
- cyclic transport does not provide a transposition; and
- no transported differential is accepted automatically.

### G. Negative power

Input `D^-1*h2`.

Expected:

- it is accepted only when the selected presentation contains an applicable
  source-backed invertibility declaration for `D`;
- the unit proposition ID appears in the trace; and
- an E2-only or page-limited declaration cannot be used outside its scope.

### H. No differential discovery

Normalize source and target expressions of a possible \(d_r\).

Expected:

- the engine may report grade compatibility and formal equality of a proposed
  Leibniz expansion;
- it creates at most a candidate plus liveness/source obligations; and
- it never creates, accepts, transports, or rules out the differential.

## 11. Backend implementation review checklist

Before merging an algebra-engine implementation, verify:

- [ ] Existing backend/domain records and APIs were migrated explicitly; no
      raw expression string was silently reinterpreted.
- [ ] Application JSON, not SymPy/Sage/Macaulay2 serialization, is canonical.
- [ ] Symbol IDs are separate from display labels and LaTeX.
- [ ] Coefficient context and its digest participate in every operation and
      cache key.
- [ ] `GF(4)` is not used as an extension field.
- [ ] \(\mathbb F_4\) arithmetic has exhaustive tests; Witt/2-adic values
      remain opaque until their own tested adapter exists.
- [ ] Negative exponents require a scoped invertibility proposition.
- [ ] Module bases and module relations are not flattened into ring symbols.
- [ ] Relation kind, source locator, scope, and review status are preserved.
- [ ] Associated-graded relations and hidden extensions remain distinct.
- [ ] Full `(stem, filtration, representation, convention)` grades are checked.
- [ ] Period/representation normalization records every certificate ID.
- [ ] Product checks page liveness before algebra normalization.
- [ ] \(\omega\) acts on representation, symbols, and coefficients separately.
- [ ] Missing action data creates an obligation and blocks materialization.
- [ ] Formal success creates at most a `candidate`; it cannot accept a
      differential, fate, action, or period.
- [ ] LogicGraph contains the computation, presentation, relations, sources,
      candidate, and unresolved obligations.
- [ ] Backend/version/order/input/presentation/context digests are recorded.
- [ ] Work, output, and trace sizes are bounded; resource exhaustion is
      indeterminate rather than false.
- [ ] Vercel requests do not execute arbitrary code or external CAS commands.
- [ ] WSL/cloud workers accept validated JSON data only and report reproducible
      environment metadata.
- [ ] UI keeps original input, canonical output, formal status, mathematical
      status, source scope, and obligations visibly separate.
- [ ] Acceptance examples A–H and legacy integral E2 compatibility tests pass.

## 12. Implemented-slice verification status

The current read-only preview satisfies the following subset of the review
checklist:

- application-owned structured JSON and registered symbol IDs;
- separate formal-integer, exact native F4, and rejected Witt/2-adic contexts;
- no `eval`, `sympify`, `parse_expr`, or SymPy `GF(4)` on request data;
- unit-only negative exponents and additive full RO grades;
- source locators for the request, coefficient context, used generators, and
  applied rewrite relations;
- monic homogeneous decreasing rewrite rules with bounded pairwise critical
  checks and bounded evaluation;
- no project mutation or mathematical claim creation; and
- a Vercel-discoverable Flask WSGI entrypoint with synchronized public assets.

The focused suite has eight tests, and the complete repository suite has 119.
The remaining unchecked items above are roadmap work, especially shared
presentations/digests, modules, Groebner endpoints, structured UI,
LogicGraph candidates/obligations, C3/omega scalar action, and external CAS
workers.

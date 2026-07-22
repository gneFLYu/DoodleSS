# Explicit finite E2-presentation API

This API is a conservative calculation aid for a presentation that a researcher
has already specified. It is **not** a group-cohomology calculator, a
2-Bockstein solver, or an arbitrary-differential discovery engine.

## Coefficient boundary

The evaluator accepts exactly this coefficient declaration:

```json
{
  "coefficient_context_id": "formal-integer-presentation",
  "coefficient_domain": "integers"
}
```

It rejects F4, Witt-vector, residue-field, and 2-adic contexts. In
particular, the implementation never interprets the integer `2` as zero.
Relations such as `2x = 0` are not oriented rewrite rules in this slice and
are rejected rather than divided by or reduced modulo 2.

## Input contract

`POST /api/v2/e2-presentations/preview` consumes this JSON object:

```json
{
  "workspace_id": "ws_integer",
  "name": "Source-cited finite E2 presentation",
  "source_ref": "Author, document, section/page/theorem",
  "scope": "Which grading and coefficient convention this finite input covers.",
  "convention_id": "q8-thesis-plotted-v1",
  "coefficient_context_id": "formal-integer-presentation",
  "coefficient_domain": "integers",
  "generators": [
    {
      "id": "x",
      "label": "x",
      "expression": "x",
      "grade": {"stem": 1, "filtration": 1, "representation": {"sigma_i": 1}}
    },
    {
      "id": "y",
      "label": "y",
      "expression": "y",
      "grade": {"stem": 2, "filtration": 2, "representation": {"sigma_i": 2}}
    }
  ],
  "relations": [
    {
      "id": "x-square",
      "lhs": {"coefficient": 1, "factors": {"x": 2}},
      "rhs": [{"coefficient": 1, "factors": {"y": 1}}],
      "source_ref": "Author, section/page for this relation"
    }
  ],
  "polynomial": {
    "terms": [{"coefficient": 1, "factors": {"x": 2}}]
  }
}
```

Each term is an integer coefficient times a commutative monomial. `rhs: []`
denotes zero. Generator IDs are identifiers within this presentation, while
`label` and `expression` are preserved separately for display and provenance.

The service requires every relation to be:

- monic, with a nonconstant left-hand monomial;
- homogeneous in the supplied `(stem, filtration, representation)` grade;
- strictly decreasing in degree-lex order on the supplied generator order; and
- compatible with every pairwise critical-pair reduction.

If any check fails, preview and materialization fail rather than selecting a
rule priority or silently changing coefficients.

## Preview and materialize

`POST /api/v2/e2-presentations/preview` validates the payload and, if
`polynomial` is supplied, returns its exact normal form. It writes nothing.

`POST /api/v2/e2-presentations` validates the same payload and persists only:

- the explicitly listed generators as E2 class nodes, retaining grade,
  convention, source context, expression, and label; and
- source-cited `presentation-generator` and `presentation-relation`
  propositions.

It never draws all monomials, creates an arbitrary product, marks a permanent
cycle, or proposes/accepts a differential.

`GET /api/v2/e2-presentations` lists the materialized presentations.

## Read-only differential candidates

`POST /api/v2/workspaces/<workspace_id>/differential-candidates` accepts:

```json
{"source_id": "class_...", "page": 3}
```

It returns unpersisted `candidate` propositions only for targets satisfying
the displayed chart convention `d_r: (-1, +r)`, unchanged representation
coordinate, class existence, and page liveness. It cannot create or accept an
arrow.

With an optional `comparison_id`, it additionally returns
`comparison_candidates`. Such a result exists only when the selected source
in the target workspace is the shifted image of an already accepted source
workspace differential and both transported endpoints exist and are live. The
response includes the comparison record, source claim, and map applicability
as hypotheses for review; it is still not a transport theorem.

## Browser workflow

Open the app, choose a workspace, then use **Advanced E2 presentation** in the
left sidebar. The prefilled JSON is a syntactically valid toy example. Replace
its placeholder locators and grades, choose **Preview**, inspect the exact
normal form and validation response, then choose **Materialize explicit data**
only when it is appropriate to save the supplied generators and relations.

For a Chinese-language operational guide, including PowerShell examples, see
[USER_GUIDE.zh-CN.md](USER_GUIDE.zh-CN.md).

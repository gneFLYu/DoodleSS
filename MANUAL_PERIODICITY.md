# Manual drawing periodicity

This beta feature records requested chart copies. It is deliberately separate
from source-backed periodicity rules: a manual vector, copy, relation, or
differential is always `manual-unverified` / `candidate`, and never proves a
period theorem or a nonzero differential.

## Named rules

Define any number of named integer chart vectors:

`POST /api/v2/workspaces/<workspace_id>/drawing-periodicity/rules`

```json
{
  "name": "P",
  "p": 20,
  "q": 4,
  "basis": "Requested local drawing convention; requires later review.",
  "source_ref": "Notebook, 2026-07-22"
}
```

`(0,0)`, non-integers, empty names, and duplicate active name/vector pairs are
rejected before a history checkpoint is made. Rules live in the canonical
top-level `manual_periodicity_rules` project array, not workspace settings.
Deleting a rule archives it; it never deletes existing copies.

## Batch applications

All batch endpoints first return a non-mutating preview. Apply recomputes that
preview under the project lock and writes all resulting records in **one**
Undo/Redo checkpoint.

| Operation | Preview | Apply | Semantics |
| --- | --- | --- | --- |
| All rules to a box | `POST .../drawing-periodicity/box/preview` | `POST .../drawing-periodicity/box/apply` | Compounds the currently active named rules and copies visible non-manual base classes plus drawn relations/differentials into `p_min..p_max`, `q_min..q_max`. |
| Differentials only | `POST .../drawing-periodicity/differentials/preview` | `POST .../drawing-periodicity/differentials/apply` | Uses one explicit `(p,q)` vector. If both translated endpoints are absent it skips; if exactly one exists it creates only the missing endpoint; if both exist it joins them. |

Both payloads accept `page` (E2 or later), `basis`, and `source_ref`. The box
payload also has integer `p_min`, `p_max`, `q_min`, `q_max`; the
differential-only payload has integer `p`, `q`.

Preview items expose `action: create | reuse | conflict`. A conflict is not
silently merged: Apply rejects it. Multiple unrelated classes at the same
grade are preserved as distinct dots. The idempotence key is the generated
operation id plus base class/differential and full exponent vector, rather than
the displayed grade. Thus linearly dependent named vectors with equal total
shift remain distinguishable when their expressions differ.

Every generated class, candidate relation, and candidate differential has its
own ID, a manual-periodicity declaration, a source/basis note, and a linked
candidate proposition. The declaration retains `mode`, `rule_ids`, bounds or
vector, and IDs of generated records. These fields are included in full
project JSON export/import and survive Undo/Redo.

## Limits

- This is a rendering and bookkeeping tool, not a group-cohomology solver or
  a differential-discovery engine.
- It does not certify periodicity, accept copied differentials, or infer
  algebraic equality from two dots sharing a cell.
- A differential-only application refuses ambiguous translated cells with more
  than one visible dot; use the explicit selected-anchor operation for a
  reviewed manual choice.
- E2 is permitted only as a manual drawing page. Source-backed Q8 D8
  propagation remains separately restricted to its documented scope.

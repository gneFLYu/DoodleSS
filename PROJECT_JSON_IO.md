# Project JSON import/export contract

This is the backend-only beta contract for exchanging a complete HFPSS Studio
project. It is deliberately different from a screenshot or a render-only chart
export: the JSON includes workspaces, gradings, classes, differentials,
propositions, source locators, comparisons, periodicity rules, and explicit
algebra presentations.

## Export

`GET /api/project/export` returns a downloadable `application/json` document.
The body is the complete serialized Studio `Project` object and can be sent,
unchanged, to the preview endpoint below.

```powershell
Invoke-WebRequest http://127.0.0.1:5078/api/project/export `
  -OutFile .\hfpss-studio-project.json
```

The old `frontEnd_lty/sseq ver15.3.html` browser format is accepted through the
staged Preview endpoint. Its `{ generators, connections, periodicityRules }`
shape can be converted into the selected existing workspace and current page; it
never replaces or merges an existing workspace during Preview. Because that
format does not contain coefficient, representation, or proof semantics, all
converted claims remain `candidate` and all named period vectors remain
`manual-unverified`.

## Reviewed replacement workflow

Replacement is two-stage and local-first:

1. `POST /api/project/import/preview` with a raw Studio project or legacy
   ver15.3 object.
   This does not write the project or change history. It validates the input,
   migrates supported legacy Studio schemas, rebuilds derived fate/event caches,
   and returns the post-migration `project`, `preview_sha256`,
   `current_revision`, and `would_revision`.
2. Review the response and then `POST /api/project/import/apply`. A full Studio
   project sends `preview.project`; a legacy preview sends the original compact
   legacy canvas as `legacy_canvas`, plus `source_name`, `target_workspace_id`,
   and `target_page`. Both paths
   send the returned digest and current revision. A stale revision or changed
   document receives `409 Conflict` and must be previewed again.

Example preview:

```powershell
$project = Get-Content .\hfpss-studio-project.json -Raw | ConvertFrom-Json
$preview = Invoke-RestMethod http://127.0.0.1:5078/api/project/import/preview `
  -Method Post -ContentType 'application/json' `
  -Body ($project | ConvertTo-Json -Depth 100)
$preview.project | ConvertTo-Json -Depth 100 | Set-Content .\reviewed-project.json -Encoding utf8
```

Example apply (use the same raw file that was previewed):

```powershell
$apply = @{
  project = $preview.project
  preview_sha256 = $preview.preview_sha256
  expected_revision = $preview.current_revision
  imported_workspace_id = $preview.imported_workspace_id
}
Invoke-RestMethod http://127.0.0.1:5078/api/project/import/apply `
  -Method Post -ContentType 'application/json' `
  -Body ($apply | ConvertTo-Json -Depth 100)
```

On success, the replacement is written by atomic file replacement. The prior
project is recorded as the single history checkpoint **“Import and replace
validated project JSON”**, so normal `/api/history/undo` and
`/api/history/redo` remain available.

## Validation and mathematical status

The import must have a nonempty project id/name and workspace array; IDs and
references must be internally consistent. It rejects broken differential
endpoints or bidegrees, invalid grade coordinates, missing comparison or
periodicity references, malformed lists, future schemas, duplicate IDs, and
accepted imported propositions without a source locator. An accepted imported
differential also needs a matching cited differential proposition.

The importer preserves a claim's existing status only as a **cited assertion
from the imported file**. It does not prove or independently verify claims,
promote candidate arrows, discover differentials, or reclassify any imported
mathematics. Fates and differential events are derived caches and are rebuilt
from the validated primary records; they are not treated as imported evidence.

This endpoint is local JSON exchange, not a collaborative merge service. It
replaces the complete current project after review; it does not merge two
collaborators' changes.

## Legacy ver15.3 response contract

Optional query parameters on Preview are `source_name` and `workspace_name`.
The response keeps the normal `project`, `preview_sha256`, `current_revision`,
and `would_revision` fields and adds:

```json
{
  "imported_workspace_id": "ws_integer",
  "import": {
    "format": "legacy-sseq-ver15.3",
    "operation": "merge-current-page",
    "imported_workspace_id": "ws_integer",
    "workspace_id": "ws_integer",
    "target_page": 5,
    "warnings": [],
    "legacy_summary": {}
  }
}
```

Legacy Apply sends `legacy_canvas`, `source_name`, `target_workspace_id`, `target_page`, and
`imported_workspace_id` with the Preview digest/revision. The server repeats the
conversion against the unchanged current project, verifies the exact digest and
workspace ID, then writes one Undo checkpoint. This avoids re-uploading the much
larger converted Studio project. Its compact response intentionally omits the
full project; the UI reloads it and switches directly to the echoed workspace.

Conversion maps `p -> stem` and `q -> filtration`. Every generator gets a new
ID; same-grade dots are never merged. `xOffset`, `yOffset`, original ID, and
`isBaseGenerator` are retained in class style/notes, while adaptive packing
controls rendering. Relations and bidegree-valid differentials become
source-labelled candidates. A line marked differential with incompatible
`d_r` bidegree is retained as an anomaly proposition and reported in warnings,
not promoted to a `Differential`. Legacy periodicity rules become canonical
`manual_periodicity_rules` with `manual-unverified` status.

# Safe workspace canvas clear

`POST /api/workspaces/<workspace_id>/clear-canvas` clears one workspace's
visible canvas by **archiving all currently active class dots**. It does not
physically delete classes, differentials, propositions, evidence, or source
locators. Archived records retain an explicit reason and remain in the local
project JSON.

The operation creates exactly one history checkpoint when it archives one or
more dots, rebuilds the workspace fate cache, and returns the archived count
and IDs. It can be restored with the normal `POST /api/history/undo`; redo is
also supported. Calling it on an already empty canvas is a non-mutating no-op.

This beta endpoint is deliberately backend-only; it has no browser button yet.

```powershell
$workspaceId = 'ws_integer'
Invoke-RestMethod "http://127.0.0.1:5078/api/workspaces/$workspaceId/clear-canvas" -Method Post

# Restore the whole clear operation, including every dot that was active.
Invoke-RestMethod 'http://127.0.0.1:5078/api/history/undo' -Method Post
```

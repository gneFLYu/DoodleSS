# Codex Project Memory: Current State

Last updated: 2026-07-24 09:53:25 +0800

## Current Project Goal

- Deliver a stable, Vercel-deployable HFPSS Studio that visualizes auditable Q_8-HFPSS page data with safe algebra support.

## Active Branch

- main

## Recent Decisions

- Render periodic copies virtually from the active page and viewport; do not persist bulk periodic copies.
- Treat class label as the semantic algebra expression, normalize away scalar 1, and expose detected generators without evaluating user text.
- Use explicit DKLLW glyph and multiplication metadata; render unclassified legacy classes as unknown rather than inferring a module type.
- A page period at E_r applies downward and advances only when it neither supports nor receives d_r.
- Legacy JSON merges into the current workspace/page; Legacy export intentionally forgets all elements to dots.

## Known Issues

- The integer E2 catalogue is finite and source-backed but is not a complete machine transcription of DKLLW24 Figure 5.
- Legacy saves cannot preserve DKLLW glyph, algebra, source, or proof semantics.
- SymPy support remains a safe structured preview layer; genuine Witt arithmetic and Macaulay2/Sage workers are not implemented.

## Open Tasks

- Transcribe remaining DKLLW24 Figure 5 classes from source data with per-class source locators and reviewed glyph/module metadata.
- Redeploy on Vercel and smoke-test the production URL after the current working tree is intentionally committed.
- Benchmark SymPy cold start on Vercel before expanding structured algebra operations.

## Latest Log References

- .codex/logs/20260724T095301+0800.md
- .codex/logs/20260724T050845+0800.md
- .codex/logs/20260723T112945+0800.md
- .codex/logs/20260722T153507+0800.md

## Collaboration Notes

- Read this file before starting Codex-assisted work.
- Read `AGENTS.md` if present.
- Read only the most recent 3 to 10 logs from `.codex/logs/`.
- Do not store chain-of-thought, hidden reasoning, JSON memory, or external database state.
